/**
 * prompt-builder/contextual-actions.js — Per-turn action availability.
 *
 * Computes, from the current world state, the actions a character can take right
 * now, plus per-item action brackets. This is the "contextual" replacement for
 * the old static ACTIONS table: instead of a wall of verbs, the agent is told
 * exactly what it can do this turn, with concrete targets from the room.
 *
 * Gating is guidance, not enforcement — the backend still resolves verbs
 * leniently, so a missed gate only hides a verb from the prompt, never breaks
 * resolution.
 *
 * Splits into window.PromptBuilder; see helpers.js header for the pattern.
 * Load this file AFTER helpers.js (uses PromptBuilder.wayHandle/lightToLevel at
 * call time only) and BEFORE agent-engine.js in index.html.
 *
 * Cross-file calls use PromptBuilder.<fn>(...).
 */

window.PromptBuilder = window.PromptBuilder || {};
(() => {
    'use strict';

    // Canonical display order for item action brackets.
    const BRACKET_ORDER = ['take', 'use', 'use_on', 'open', 'close', 'eat', 'drink', 'read', 'wear', 'remove', 'toggle', 'drop', 'examine'];

    // Mirror of engine/item_actions.py:INVERSE_ACTIONS — an item that declares
    // one side of a pair is also credited with the other (take→drop, equip→
    // unequip, open→close). Kept in sync so the prompt agrees with the backend.
    const INVERSE_ACTIONS = {
        take: 'drop',
        drop: 'take',
        equip: 'unequip',
        unequip: 'equip',
        open: 'close',
        close: 'open',
    };

    /** Expand an action list with each declared action's inverse (idempotent). */
    function expandInverseActions(actions) {
        const out = [...actions];
        for (const action of [...out]) {
            const inverse = INVERSE_ACTIONS[action];
            if (inverse && !out.includes(inverse)) out.push(inverse);
        }
        return out;
    }

    /** Normalize an action/tags property that may be a string ("a,b") or array. */
    function asArray(value) {
        if (value == null) return [];
        if (Array.isArray(value)) return value.map(String);
        return String(value).split(',').map(s => s.trim()).filter(Boolean);
    }

    /** Chart the char node id for a character (matches world-state.js). */
    function charNodeId(charName) {
        return `player_${String(charName).replace(/\s+/g, '_')}`;
    }

    /** Trigger types on an item: trigger edges whose source is this item. */
    function itemTriggerTypes(itemId) {
        const types = new Set();
        for (const edge of worldState.graph?.edges || []) {
            if (edge.type !== 'triggers') continue;
            if (String(edge.source) !== String(itemId)) continue;
            const triggerNode = worldState.getNode(edge.target);
            if (!triggerNode) continue;
            const tt = triggerNode.properties?.trigger_type;
            (Array.isArray(tt) ? tt : [tt]).filter(Boolean).forEach(t => types.add(String(t)));
        }
        return [...types];
    }

    /** target_name of the first on_use_on trigger on an item, if any. */
    function useOnTargetName(itemId) {
        for (const edge of worldState.graph?.edges || []) {
            if (edge.type !== 'triggers') continue;
            if (String(edge.source) !== String(itemId)) continue;
            const triggerNode = worldState.getNode(edge.target);
            if (!triggerNode) continue;
            const tt = triggerNode.properties?.trigger_type;
            const list = Array.isArray(tt) ? tt : (tt ? [tt] : []);
            if (list.includes('on_use_on')) {
                const name = triggerNode.properties?.target_name;
                if (name) return String(name);
            }
        }
        return '';
    }

    /** All item nodes the character carries or has equipped. */
    function carriedItemNodes(charName) {
        const id = charNodeId(charName);
        const out = [];
        const seen = new Set();
        for (const edge of worldState.graph?.edges || []) {
            if (edge.target !== id) continue;
            if (edge.type !== 'carrying' && edge.type !== 'equipped') continue;
            if (seen.has(edge.source)) continue;
            seen.add(edge.source);
            const node = worldState.getNode(edge.source);
            if (node && node.type === 'item') {
                out.push({ id: edge.source, name: node.name, properties: node.properties, equipped: edge.type === 'equipped' });
            }
        }
        return out;
    }

    /** Whether a character has already examined/discovered an item by name. */
    function isDiscovered(player, itemName) {
        return new Set((player?.discovered_items || []).map(n => String(n).toLowerCase().trim()))
            .has(String(itemName || '').toLowerCase().trim());
    }

    /**
     * True when an item is an intrinsic ability (a spell/talent/power) rather
     * than a physical object. Mirrors engine/equipment.py:_is_intrinsic_ability.
     * Such items are known by definition (the character carries the knowledge),
     * never appear as "new", and are never droppable/wearable.
     */
    function isIntrinsicAbility(props) {
        const tags = asArray(props?.tags || []).map(t => String(t).toLowerCase());
        return ['spell', 'ability', 'innate', 'intrinsic', 'power'].some(t => tags.includes(t));
    }

    /**
     * The allowed action verbs for an item node in the given context.
     * Mirrors engine/trigger_system.py:_get_available_actions, client-side.
     *
     * @param {Object} item  - { id, name, properties } (as returned by getItemsInArea)
     * @param {Object} player - Player data (discovered_items)
     * @param {Object} [carry] - { equipped } when the item is carried/equipped
     * @returns {string[]} verbs in BRACKET_ORDER
     */
    function computeItemActions(item, player, carry) {
        const props = item?.properties || {};
        const actions = expandInverseActions(asArray(props.actions).map(s => s.toLowerCase()));
        const tags = asArray(props.tags).map(s => s.toLowerCase());
        const state = String(props.current_state || '').toLowerCase();
        const triggerTypes = itemTriggerTypes(item.id);
        const verbs = new Set();

        if (actions.includes('take') && !carry) verbs.add('take');

        if (actions.includes('use') || triggerTypes.includes('on_use') || triggerTypes.includes('on_use_on')) verbs.add('use');
        if (triggerTypes.includes('on_use_on')) verbs.add('use_on');

        if (actions.includes('open') && ['closed', 'normal', ''].includes(state)) verbs.add('open');
        if (actions.includes('close') && state === 'open') verbs.add('close');

        if (actions.includes('eat') || tags.includes('food')) verbs.add('eat');
        if (actions.includes('drink') || tags.includes('drink')) verbs.add('drink');
        if (actions.includes('read') || actions.includes('search') || tags.includes('readable') || tags.includes('read')) verbs.add('read');

        // wear/remove are the prompt display names for the equip/unequip pair.
        // Equippable when the item declares the pair, is tagged wearable, OR has
        // non-empty equip_slots (the engine's gate — equipment.py equips anything
        // with slots). An empty equip_slots array must never imply wearability.
        const intrinsic = isIntrinsicAbility(props);
        const slots = Array.isArray(props.equip_slots) ? props.equip_slots : [];
        const equippable = !intrinsic && (actions.includes('equip') || actions.includes('unequip') || actions.includes('wear') || actions.includes('remove') || tags.includes('wearable') || slots.length > 0);
        if (equippable && !(carry && carry.equipped)) verbs.add('wear');
        if (!intrinsic && carry && carry.equipped && (actions.includes('unequip') || actions.includes('remove') || slots.length > 0)) verbs.add('remove');

        if (triggerTypes.includes('on_toggle_on') || triggerTypes.includes('on_toggle_off')) verbs.add('toggle');

        if (carry && actions.includes('drop') && !isIntrinsicAbility(props)) verbs.add('drop');

        // examine — shown unless the character has already examined/discovered it,
        // or the item is an intrinsic ability the character always knows
        if (!isDiscovered(player, item?.name) && !isIntrinsicAbility(props)) verbs.add('examine');

        return BRACKET_ORDER.filter(v => verbs.has(v));
    }

    /** "[take, use]" style bracket from a verb list; '' when empty. */
    function formatActionBrackets(verbs) {
        if (!verbs || !verbs.length) return '';
        return `[${verbs.join(', ')}]`;
    }

    /**
     * Build the per-turn `=== AVAILABLE ACTIONS ===` block for a character.
     *
     * Only verbs whose gate is true are listed, each with concrete targets from
     * the current room. Mirrors the room-context exit/people/item data so the
     * block agrees with the rest of the character's surroundings.
     *
     * @param {Object} state - Full world state data (players / players_in_area / ...)
     * @param {string} charName - Character name
     * @param {Object} player - Player data
     * @param {Object} currentArea - Current area data object (exits, name)
     * @returns {string} The block ('' if nothing would be listed — never happens)
     */
    function buildAvailableActionsBlock(state, charName, player, currentArea) {
        const lines = [];
        const light = currentArea?.ambient_light ?? currentArea?.environment?.light ?? 50;
        const level = PromptBuilder.lightToLevel(light);
        const blind = !!(player?.conditions?.blind);
        const traits = player?.traits || {};
        const hasDarkVision = traits.dark_vision === true || traits.darkvision === true;
        const vitals = player?.vitals || {};
        // Items the character carries or has equipped — used to gate the
        // "give" action (you can only hand over something you're holding).
        const carried = carriedItemNodes(charName);

        // ---- Movement / exits ----
        const visibleExits = Object.entries(currentArea?.exits || {}).filter(([, ed]) => !ed.hidden);
        const exitHandles = [];
        for (const [dir, exitData] of visibleExits) {
            const doorNode = worldState.getNode(exitData.way_id);
            const handle = PromptBuilder.wayHandle({ ...exitData, label: dir }, doorNode, currentArea?.name) || dir;
            exitHandles.push(handle);

            const req = String(doorNode?.properties?.requires || '').toLowerCase();
            if (req === 'crawl') lines.push(`crawl — crawl through the ${handle}`);
            else if (req === 'climb') lines.push(`climb — climb the ${handle}`);
            else if (req === 'jump') lines.push(`jump — jump across the ${handle}`);
        }

        // ---- People ----
        const others = (state.players_in_area || []).filter(p => p && p.name && p.name !== charName);
        if (others.length) {
            const names = others.map(p =>
                PromptBuilder.anonymousName(charName, p.name, worldState.data?.players?.[p.name]?.description || p.description || '')
            ).filter(Boolean);
            const target = names.join(', ');
            lines.push(`attack — fight ${target}`);
            lines.push(`grab — seize ${target}`);
            lines.push(`lead — guide ${target}`);
            if (carried.length) lines.push(`give — hand an item to ${target}`);
            lines.push(`steal — take from ${target}`);
        }

        // ---- Self / needs / conditions ----
        if (player?.grappled_by) lines.push('escape — break free (you are being held)');
        if ((player?.state === 'prone') || !!(player?.conditions?.prone)) lines.push('stand — get back up (you are prone)');

        const energy = vitals.Energy;
        if (energy !== undefined && energy < 50) lines.push('rest — rest to recover energy (you are tired)');
        const bladder = vitals.Bladder;
        if (bladder !== undefined && bladder >= 65) lines.push('relieve — relieve yourself (your bladder is full)');

        if (blind) lines.push('listen — listen hard (you are blind)');
        if (!hasDarkVision && (blind || level === 'pitch_black' || level === 'dim')) lines.push('fumble — blind search in the darkness');

        if (currentArea?.name) lines.push(`examine — examine ${currentArea.name}`);

        if (!lines.length) return '';

        return `\n=== AVAILABLE ACTIONS ===\n${lines.join('\n')}\nAlways available: examine, look, inventory, stats, wait`;
    }

    Object.assign(window.PromptBuilder, {
        computeItemActions,
        formatActionBrackets,
        buildAvailableActionsBlock,
        carriedItemNodes,
        itemTriggerTypes,
        useOnTargetName
    });
})();