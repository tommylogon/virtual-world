"use strict";
/**
 * prompt-builder/contextual-actions.js  -  Non-redundant action availability.
 *
 * Computes the === AVAILABLE ACTIONS === block: only the actions that aren't
 * already bracketed on doors/items/people in the room context (the universal
 * set: person interactions, conditional verbs, requirement passage verbs, and
 * the always-on examine-room/look/inventory/stats/wait). This is the
 * "contextual" replacement for the old static ACTIONS table.
 *
 * Gating is guidance, not enforcement  -  the backend still resolves verbs
 * leniently, so a missed gate only hides a verb from the prompt, never breaks
 * resolution.
 *
 * Splits into window.PromptBuilder; see helpers.js header for the pattern.
 * Load this file AFTER helpers.js (uses PromptBuilder.wayHandle/lightToLevel at
 * call time only) and BEFORE agent-engine.js in index.html.
 *
 * Cross-file calls use PromptBuilder.<fn>(...).
 *
 * @module prompt-builder/contextual-actions  -  the "=== AVAILABLE ACTIONS ===" block
 * @contributes computeItemActions, buildAvailableActionsBlock, carriedItemNodes, useOnTargetName, gating helpers
 * @powers The human turn  -  per-turn verb availability  -  only verbs not already bracketed in the room context
 * @relates uses helpers.js; complements room-context.js; gates are guidance, the backend resolves leniently
 * @docs docs/virtualWorld/AI & Narration/Agent Engine.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
window.PromptBuilder = window.PromptBuilder || {};
(() => {
    'use strict';
    // Canonical display order for item action brackets.
    const _registryBO = window.Actions?.BRACKET_ORDER;
    const BRACKET_ORDER = _registryBO || ['take', 'use', 'use_on', 'open', 'close', 'eat', 'drink', 'read', 'wear', 'remove', 'toggle', 'drop', 'examine'];
    // Mirror of engine/item_actions.py:INVERSE_ACTIONS  -  an item that declares
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
            if (inverse && !out.includes(inverse))
                out.push(inverse);
        }
        return out;
    }
    /** Normalize an action/tags property that may be a string ("a,b") or array. */
    function asArray(value) {
        if (value == null)
            return [];
        if (Array.isArray(value))
            return value.map(String);
        return String(value).split(',').map(s => s.trim()).filter(Boolean);
    }
    /** The generated client tier mirror (agent/action-tiers), if loaded. */
    function actionTiers() {
        return window.ActionTiers || null;
    }
    /**
     * task-352: can the remaining turn slots pay for *verb* on *props*?
     * Guidance only  -  the engine's `_slot_gate` is the enforcement. With no
     * budget published (older callers, no `turn_slots`) nothing is hidden, so
     * this degrades to the pre-budget rendering.
     */
    function affordable(verb, props, slots) {
        if (!slots)
            return true;
        const tiers = actionTiers();
        if (!tiers || typeof tiers.canAfford !== 'function')
            return true;
        return tiers.canAfford(verb, props, slots);
    }
    /** Chart the char node id for a character (matches world-state.js). */
    function charNodeId(charName) {
        return `player_${String(charName).replace(/\s+/g, '_')}`;
    }
    /** Trigger types on an item: trigger edges whose source is this item. */
    function itemTriggerTypes(itemId) {
        const types = new Set();
        for (const edge of worldState.graph?.edges || []) {
            if (edge.type !== 'triggers')
                continue;
            if (String(edge.source) !== String(itemId))
                continue;
            const triggerNode = worldState.getNode(edge.target);
            if (!triggerNode)
                continue;
            const tt = triggerNode.properties?.trigger_type;
            (Array.isArray(tt) ? tt : [tt]).filter(Boolean).forEach((t) => types.add(String(t)));
        }
        return [...types];
    }
    /** target_name of the first on_use_on trigger on an item, if any. */
    function useOnTargetName(itemId) {
        for (const edge of worldState.graph?.edges || []) {
            if (edge.type !== 'triggers')
                continue;
            if (String(edge.source) !== String(itemId))
                continue;
            const triggerNode = worldState.getNode(edge.target);
            if (!triggerNode)
                continue;
            const tt = triggerNode.properties?.trigger_type;
            const list = Array.isArray(tt) ? tt : (tt ? [tt] : []);
            if (list.includes('on_use_on')) {
                const name = triggerNode.properties?.target_name;
                if (name)
                    return String(name);
            }
        }
        return '';
    }
    /** All item nodes the character carries or has equipped. */
    function carriedItemNodes(charName) {
        const id = charNodeId(charName);
        const bySource = new Map();
        for (const edge of worldState.graph?.edges || []) {
            if (edge.target !== id)
                continue;
            if (edge.type !== 'carrying' && edge.type !== 'equipped')
                continue;
            const node = worldState.getNode(edge.source);
            if (!node || node.type !== 'item')
                continue;
            // Consistent worlds have exactly ONE edge per item (equip removes the
            // carrying edge). Legacy data can carry both; equipped is the
            // stronger state and wins  -  "wearing" is just equipped.
            const equipped = edge.type === 'equipped' || bySource.get(edge.source)?.equipped === true;
            bySource.set(edge.source, { id: edge.source, name: node.name, properties: node.properties, equipped });
        }
        return [...bySource.values()];
    }
    /** Visibly held item nodes in a character's hand_left / hand_right slots. */
    function heldItemNodes(targetName) {
        const id = charNodeId(targetName);
        const bySource = new Map();
        const handIds = new Set();
        const eq = worldState.data?.players?.[targetName]?.equipped;
        if (eq) {
            for (const slot of ['hand_right', 'hand_left']) {
                for (const raw of eq[slot] || []) {
                    if (!raw)
                        continue;
                    const s = String(raw);
                    handIds.add(s.startsWith('__multi_slot_') ? s.slice('__multi_slot_'.length) : s);
                }
            }
        }
        for (const edge of worldState.graph?.edges || []) {
            if (edge.target !== id || edge.type !== 'equipped')
                continue;
            const slot = edge.properties?.slot;
            if (slot !== 'hand_right' && slot !== 'hand_left' && !handIds.has(edge.source))
                continue;
            const node = worldState.getNode(edge.source);
            if (!node || node.type !== 'item')
                continue;
            if (node.properties?.concealed || isIntrinsicAbility(node.properties))
                continue;
            bySource.set(edge.source, { id: edge.source, name: node.name, properties: node.properties, equipped: true });
        }
        for (const itemId of handIds) {
            if (bySource.has(itemId))
                continue;
            const node = worldState.getNode(itemId);
            if (!node || node.type !== 'item')
                continue;
            if (node.properties?.concealed || isIntrinsicAbility(node.properties))
                continue;
            bySource.set(itemId, { id: itemId, name: node.name, properties: node.properties, equipped: true });
        }
        return [...bySource.values()];
    }
    /** All ability/spell item nodes the character knows (EDGE_KNOWN). */
    function knownAbilityNodes(charName) {
        const id = charNodeId(charName);
        const items = [];
        for (const edge of worldState.graph?.edges || []) {
            if (edge.target !== id || edge.type !== 'known')
                continue;
            const node = worldState.getNode(edge.source);
            if (!node || node.type !== 'item')
                continue;
            items.push({ id: edge.source, name: node.name, properties: node.properties });
        }
        return items;
    }
    /**
     * Whether a character has already examined/discovered an item by name or id.
     * Checks memory_index (subject_id -> memory_id) and observation memories (kind == "item").
     */
    function isDiscovered(player, itemNameOrId) {
        if (!player || !itemNameOrId)
            return false;
        const target = String(itemNameOrId).toLowerCase().trim();
        if (player.memory_index && player.memory_index[itemNameOrId])
            return true;
        if (Array.isArray(player.memories)) {
            for (const m of player.memories) {
                if (m && m.kind === 'item') {
                    if (String(m.subject_id || '').toLowerCase().trim() === target)
                        return true;
                    if (String(m.name || '').toLowerCase().trim() === target)
                        return true;
                }
            }
        }
        return false;
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
    /** True when an item node is a phone or long-distance comms device. */
    function isPhoneOrCommsDevice(item) {
        const props = item?.properties || {};
        const tags = asArray(props.tags).map(t => t.toLowerCase());
        const name = String(item?.name || '').toLowerCase();
        return tags.includes('phone')
            || tags.includes('communication')
            || tags.includes('comms')
            || tags.includes('radio')
            || name.includes('phone');
    }
    /** Client mirror of engine/long_distance_comms.py:is_device_active. */
    function isDeviceActive(item) {
        if (!item)
            return false;
        const props = item.properties || {};
        if (props.uses === 0)
            return false;
        const state = String(props.current_state || '').toLowerCase();
        if (['unlit', 'off', 'dead', 'spent'].includes(state))
            return false;
        const tags = asArray(props.tags).map(t => t.toLowerCase());
        let hasPowerSource = false;
        for (const edge of worldState.graph?.edges || []) {
            if (edge.type !== 'in' || String(edge.target) !== String(item.id))
                continue;
            const child = worldState.getNode(edge.source);
            if (!child)
                continue;
            const cprops = child.properties || {};
            const ctags = asArray(cprops.tags).map(t => t.toLowerCase());
            if (ctags.includes('power_source') || ctags.includes('battery')) {
                hasPowerSource = true;
                const cstate = String(cprops.current_state || '').toLowerCase();
                if (cprops.uses === 0 || ['unlit', 'off', 'dead', 'spent'].includes(cstate)) {
                    return false;
                }
            }
        }
        if ((tags.includes('requires_battery') || props.requires_battery) && !hasPowerSource) {
            return false;
        }
        return true;
    }
    /** Active phone/comms devices carried by or co-located with charName. */
    function activePhoneNodes(charName, currentArea) {
        const candidates = [...carriedItemNodes(charName)];
        const seen = new Set(candidates.map(c => String(c.id)));
        try {
            const areaNode = currentArea?.name ? worldState.getNodeByIdentifier(currentArea.name) : null;
            const areaId = areaNode ? areaNode.id : null;
            if (areaId) {
                for (const edge of worldState.graph?.edges || []) {
                    if (edge.target !== areaId || edge.type !== 'in')
                        continue;
                    const node = worldState.getNode(edge.source);
                    if (!node || node.type !== 'item' || seen.has(String(edge.source)))
                        continue;
                    seen.add(String(edge.source));
                    candidates.push({ id: edge.source, name: node.name, properties: node.properties });
                }
            }
        }
        catch { /* area scan is best-effort */ }
        return candidates.filter(item => isPhoneOrCommsDevice(item) && isDeviceActive(item));
    }
    /** True when an item node is hideable cover. */
    function isHideableCover(item) {
        if (!item)
            return false;
        const props = item.properties || {};
        if (props.hideable === true)
            return true;
        const tags = asArray(props.tags).map(t => t.toLowerCase());
        if (tags.includes('hideable') || tags.includes('cover'))
            return true;
        const actions = asArray(props.actions).map(a => a.toLowerCase());
        return actions.includes('hide');
    }
    /** Hideable cover item nodes present in currentArea. */
    function hideableCoverNodes(currentArea) {
        const out = [];
        const seen = new Set();
        const pushIfCover = (node) => {
            if (!node)
                return;
            const id = String(node.id || node.name || '');
            if (!id || seen.has(id))
                return;
            const candidate = {
                id,
                name: node.name || id,
                properties: node.properties || node,
            };
            if (isHideableCover(candidate)) {
                seen.add(id);
                out.push(candidate);
            }
        };
        try {
            if (currentArea?.name && typeof worldState.getItemsInArea === 'function') {
                for (const item of worldState.getItemsInArea(currentArea.name) || []) {
                    pushIfCover(item);
                }
            }
        }
        catch { /* optional */ }
        try {
            const areaNode = currentArea?.name
                ? (typeof worldState.getNodeByIdentifier === 'function'
                    ? worldState.getNodeByIdentifier(currentArea.name)
                    : worldState.getNode?.(`area_${String(currentArea.name).toLowerCase().replace(/\s+/g, '_')}`))
                : null;
            const areaId = areaNode?.id || (currentArea?.name ? `area_${String(currentArea.name).toLowerCase().replace(/\s+/g, '_')}` : null);
            if (areaId) {
                for (const edge of worldState.graph?.edges || []) {
                    if (edge.target !== areaId || (edge.type && edge.type !== 'in'))
                        continue;
                    const node = worldState.getNode?.(edge.source);
                    if (node && node.type === 'item')
                        pushIfCover(node);
                }
            }
        }
        catch { /* best-effort */ }
        return out;
    }
    /** True when charName is currently concealed (player.hidden, state, or 'hidden' edge). */
    function isCharacterHidden(charName, player) {
        if (!player && !charName)
            return false;
        if (player?.hidden === true)
            return true;
        const st = String(player?.state || '').toLowerCase();
        if (st === 'hidden' || st === 'stealthed')
            return true;
        const nodeId = charNodeId(charName).toLowerCase();
        const nameLower = String(charName || '').toLowerCase();
        for (const edge of worldState.graph?.edges || []) {
            if (edge.type !== 'hidden')
                continue;
            const src = String(edge.source || '').toLowerCase();
            if (src === nameLower || src === nodeId)
                return true;
        }
        return false;
    }
    /** True when threat or danger exists in the character's current room context. */
    function hasThreatOrDanger(state, charName, player, currentArea, others) {
        try {
            const td = window.ThreatDetector;
            if (td && typeof td.getThreats === 'function') {
                const threats = td.getThreats(charName, state?.turn_events, state);
                if (Array.isArray(threats) && threats.length > 0)
                    return true;
            }
        }
        catch { /* optional */ }
        if (player?.conditions?.frightened || player?.conditions?.terrified)
            return true;
        if (player?.recent_attackers && Object.keys(player.recent_attackers).length > 0)
            return true;
        if (currentArea?.danger || currentArea?.threat)
            return true;
        const turnEvents = state?.turn_events || worldState.data?.turn_events || [];
        if (Array.isArray(turnEvents) && turnEvents.some((ev) => ['combat', 'attack', 'disarm'].includes(String(ev?.action || '').toLowerCase()))) {
            return true;
        }
        for (const p of others) {
            const pName = p.name || '';
            const full = state.players?.[pName] || worldState.data?.players?.[pName] || p;
            if (!full)
                continue;
            const ptags = asArray(full.tags).map(t => t.toLowerCase());
            if (full.traits?.hostile || full.hostile === true || full.is_slasher === true)
                return true;
            if (ptags.includes('hostile') || ptags.includes('slasher') || ptags.includes('enemy'))
                return true;
            if (full.state === 'combat' || full.state === 'hostile')
                return true;
            const rel = full.relationships?.[charName]?.closeness;
            if (typeof rel === 'number' && rel < -20)
                return true;
        }
        return false;
    }
    /**
     * The allowed action verbs for an item node in the given context.
     * Mirrors engine/trigger_system.py:_get_available_actions, client-side.
     *
     * @param item  - { id, name, properties } (as returned by getItemsInArea)
     * @param player - Player data (memory_index, memories)
     * @param carry - { equipped } when the item is carried/equipped
     * @param slots - remaining turn_slots; when present, verbs the budget cannot pay for are dropped
     * @returns verbs in BRACKET_ORDER
     */
    function computeItemActions(item, player, carry, slots) {
        const props = item?.properties || {};
        const actions = expandInverseActions(asArray(props.actions).map(s => s.toLowerCase()));
        const tags = asArray(props.tags).map(s => s.toLowerCase());
        const state = String(props.current_state || '').toLowerCase();
        const triggerTypes = itemTriggerTypes(item.id);
        const verbs = new Set();
        if (actions.includes('take') && !carry)
            verbs.add('take');
        if (actions.includes('use') || triggerTypes.includes('on_use') || triggerTypes.includes('on_use_progressive') || triggerTypes.includes('on_use_on'))
            verbs.add('use');
        if (triggerTypes.includes('on_use_on'))
            verbs.add('use_on');
        if (actions.includes('open') && ['closed', 'normal', ''].includes(state))
            verbs.add('open');
        if (actions.includes('close') && state === 'open')
            verbs.add('close');
        if (actions.includes('eat') || tags.includes('food'))
            verbs.add('eat');
        if (actions.includes('drink') || tags.includes('drink'))
            verbs.add('drink');
        if (actions.includes('read') || actions.includes('search') || tags.includes('readable') || tags.includes('read'))
            verbs.add('read');
        // wear/remove are the prompt display names for the equip/unequip pair.
        // Equippable when the item declares the pair, is tagged wearable, OR has
        // non-empty equip_slots (the engine's gate  -  equipment.py equips anything
        // with slots). An empty equip_slots array must never imply wearability.
        const intrinsic = isIntrinsicAbility(props);
        const equipSlots = Array.isArray(props.equip_slots) ? props.equip_slots : [];
        const equippable = !intrinsic && (actions.includes('equip') || actions.includes('unequip') || actions.includes('wear') || actions.includes('remove') || tags.includes('wearable') || equipSlots.length > 0);
        if (equippable && !(carry && carry.equipped))
            verbs.add('wear');
        if (!intrinsic && carry && carry.equipped && (actions.includes('unequip') || actions.includes('remove') || equipSlots.length > 0))
            verbs.add('remove');
        if (triggerTypes.includes('on_toggle_on') || triggerTypes.includes('on_toggle_off'))
            verbs.add('toggle');
        if (carry && actions.includes('drop') && !isIntrinsicAbility(props))
            verbs.add('drop');
        // examine  -  shown unless the character has already examined/discovered it,
        // the item is an intrinsic ability the character always knows, or the item
        // is currently equipped/worn: the engine's item matcher only reaches
        // carrying + area items (matching._match_item_name), so an examine on
        // worn gear would always fail.
        if (!(carry && carry.equipped) && !isDiscovered(player, item?.name || '') && !isIntrinsicAbility(props))
            verbs.add('examine');
        const list = BRACKET_ORDER.filter(v => verbs.has(v));
        // task-352: drop verbs the remaining turn_slots cannot pay for. Guidance
        // only  -  the engine's `_slot_gate` still enforces. No budget → no hide.
        if (!slots)
            return list;
        return list.filter(v => affordable(v, props, slots));
    }
    /** "[take, use]" style bracket from a verb list; '' when empty. */
    function formatActionBrackets(verbs) {
        if (!verbs || !verbs.length)
            return '';
        return `[${verbs.join(', ')}]`;
    }
    /**
     * Build the per-turn `=== AVAILABLE ACTIONS ===` block for a character.
     *
     * Only NON-redundant actions are listed. The room context already brackets
     * what you can do with each door, item, person, and carried/worn thing, so
     * this block covers only self/universal actions: interacting with people,
     * per-turn conditional verbs (escape/stand/rest/relieve/listen/fumble),
     * requirement-gated passage verbs (crawl/climb/jump), and the always-on
     * examine-room/look/inventory/stats/wait set.
     *
     * @param state - Full world state data (players / players_in_area / ...)
     * @param charName - Character name
     * @param player - Player data
     * @param currentArea - Current area data object (exits, name)
     * @param slots - remaining turn_slots; when present, verbs the budget cannot pay for are dropped
     * @returns The block ('' if nothing would be listed  -  never happens)
     */
    /**
     * task-840: craftable-now recipe suggestions. Reads the known-recipes
     * cache (filled from GET /api/players/<n>/recipes, refreshed in the
     * background); matches ingredients against carried + area items the
     * same lenient way the backend does. Guidance only.
     */
    const _recipeCache = {};
    function knownRecipes(charName) {
        return (_recipeCache[charName] && _recipeCache[charName].list) || [];
    }
    function refreshKnownRecipes(charName) {
        const cached = _recipeCache[charName];
        if (cached && Date.now() - cached.at < 60000)
            return;
        _recipeCache[charName] = { at: Date.now(), list: cached ? cached.list : [] };
        if (typeof fetch !== 'function')
            return;
        ApiClient.getPlayerRecipes(charName)
            .then((data) => {
            _recipeCache[charName] = { at: Date.now(), list: data.recipes || [] };
        })
            .catch(() => { });
    }
    function craftableLines(charName, player, currentArea) {
        refreshKnownRecipes(charName);
        const known = knownRecipes(charName);
        if (!known.length)
            return [];
        const have = new Set();
        for (const item of carriedItemNodes(charName)) {
            have.add(String(item.name || '').toLowerCase());
        }
        try {
            const areaNode = currentArea?.name ? worldState.getNodeByIdentifier(currentArea.name) : null;
            const areaId = areaNode ? areaNode.id : null;
            for (const edge of (worldState.graph?.edges || [])) {
                if (areaId && edge.target === areaId && edge.type !== 'carrying' && edge.type !== 'equipped') {
                    const node = worldState.getNode(edge.source);
                    if (node && node.type === 'item') {
                        have.add(String(node.name || '').toLowerCase());
                    }
                }
            }
        }
        catch { /* area scan is best-effort */ }
        const out = [];
        for (const recipe of known) {
            const ingredients = Array.isArray(recipe.ingredients) ? recipe.ingredients : [];
            const missing = ingredients.filter((ing) => {
                const needle = String(ing.item || '').toLowerCase();
                return needle && ![...have].some((h) => h.includes(needle) || needle.includes(h));
            });
            if (missing.length)
                continue;
            const mins = Number(recipe.duration_min || 0);
            out.push(`make ${recipe.name}  -  cook ${String(recipe.name).toLowerCase()}${mins > 0 ? ` (${mins} min)` : ''}`);
            if (out.length >= 5)
                break;
        }
        return out;
    }
    function buildAvailableActionsBlock(state, charName, player, currentArea, slots) {
        const lines = [];
        const light = currentArea?.ambient_light ?? currentArea?.environment?.light ?? 50;
        const level = PromptBuilder.lightToLevel(light);
        const blind = !!(player?.conditions?.blind);
        const traits = player?.traits || {};
        const hasDarkVision = traits.dark_vision === true || traits.darkvision === true;
        const vitals = player?.vitals || {};
        const carried = carriedItemNodes(charName);
        const viewExits = (window.PromptBuilder?.viewerExits)
            ? window.PromptBuilder.viewerExits(state, charName, currentArea)
            : (currentArea?.exits || {});
        const visibleExits = Object.entries(viewExits).filter(([, ed]) => !ed.hidden);
        // task-352: `keep` drops a suggested verb the remaining turn_slots cannot
        // pay for (guidance only  -  the engine's `_slot_gate` enforces). No budget
        // published → nothing hidden. `wait` is exempt (see below): it is the
        // turn's exit.
        const keep = (verb, line) => {
            if (affordable(verb, null, slots))
                lines.push(line);
        };
        for (const [dir, exitData] of visibleExits) {
            const doorNode = worldState.getNode(exitData.way_id);
            const handle = PromptBuilder.wayHandle({ ...exitData, label: dir }, doorNode, currentArea?.name) || dir;
            const req = String(doorNode?.properties?.requires || '').toLowerCase();
            // Requirement-gated passage verbs aren't in the door's standard
            // bracket list, so they live here to stay visible.
            if (req === 'crawl')
                keep('crawl', `crawl  -  crawl through the ${handle}`);
            else if (req === 'climb')
                keep('climb', `climb  -  climb the ${handle}`);
            else if (req === 'jump')
                keep('jump', `jump  -  jump across the ${handle}`);
            else if (req === 'swim')
                keep('swim', `swim  -  swim through the ${handle}`);
            else if (req === 'dive')
                keep('dive', `dive  -  dive through the ${handle}`);
        }
        const others = typeof PromptBuilder.playersInAreaFor === 'function'
            ? PromptBuilder.playersInAreaFor(state, charName, currentArea?.name || player?.current_area)
            : (state.players_in_area || []).filter((p) => p && p.name && p.name !== charName);
        if (others.length) {
            const names = others.map((p) => 
            // The filter above guarantees p.name; `|| ''` is that same
            // narrowing expressed so the index type is a string.
            PromptBuilder.anonymousName(charName, p.name || '', worldState.data?.players?.[p.name || '']?.description || p.description || '')).filter(Boolean);
            const target = names.join(', ');
            keep('attack', `attack  -  fight ${target}`);
            keep('grab', `grab  -  seize ${target}`);
            const armedNames = others
                .filter((p) => heldItemNodes(p.name || '').length > 0)
                .map((p) => PromptBuilder.anonymousName(charName, p.name || '', worldState.data?.players?.[p.name || '']?.description || p.description || ''))
                .filter(Boolean);
            if (armedNames.length)
                keep('disarm', `disarm  -  wrest a held item from ${armedNames.join(', ')}`);
            const sleepingNames = others
                .filter((p) => {
                const st = String(worldState.data?.players?.[p.name || '']?.state || p.state || '').toLowerCase();
                const conds = worldState.data?.players?.[p.name || '']?.conditions || p?.conditions || {};
                return st === 'sleeping' || st === 'asleep' || st === 'unconscious' || Boolean(conds.unconscious || conds.sleeping);
            })
                .map((p) => PromptBuilder.anonymousName(charName, p.name || '', worldState.data?.players?.[p.name || '']?.description || p.description || ''))
                .filter(Boolean);
            if (sleepingNames.length)
                keep('wake', `wake  -  rouse ${sleepingNames.join(', ')}`);
            keep('lead', `lead  -  guide ${target}`);
            if (carried.length)
                keep('give', `give  -  hand an item to ${target}`);
            keep('steal', `steal  -  take from ${target}`);
        }
        if (carried.length && visibleExits.length) {
            keep('throw', 'throw <item> to/over <way>  -  throw a carried item through an open/see-through way or over a barrier');
        }
        if (player?.grappled_by)
            keep('escape', 'escape  -  break free (you are being held)');
        if ((player?.state === 'prone') || !!(player?.conditions?.prone))
            keep('stand', 'stand  -  get back up (you are prone)');
        const coverNodes = hideableCoverNodes(currentArea);
        const inDanger = hasThreatOrDanger(state, charName, player, currentArea, others);
        if (inDanger) {
            keep('flee', 'flee  -  disengage and retreat from danger');
        }
        if (isCharacterHidden(charName, player)) {
            keep('unhide', 'unhide  -  step out of hiding');
        }
        else if (coverNodes.length > 0 || inDanger) {
            if (coverNodes.length > 0) {
                const coverLabels = coverNodes.map(c => c.name || c.id).filter(Boolean).join(', ');
                keep('hide', `hide  -  hide in/behind/under ${coverLabels}`);
            }
            else {
                keep('hide', 'hide  -  hide in cover or shadows');
            }
        }
        const energy = vitals.Energy;
        if (energy !== undefined && energy < 50)
            keep('rest', 'rest  -  rest to recover energy (you are tired)');
        const bladder = vitals.Bladder;
        if (bladder !== undefined && bladder >= 65) {
            const RELIEF_RE = /\b(latrine|toilet|privy|restroom|bathroom|urinal|washroom)\b/i;
            const areaRef = currentArea?.id || currentArea?.area_id || currentArea?.name || '';
            const areaNode = areaRef ? worldState?.getNode?.(areaRef) : null;
            const areaTags = Array.isArray(areaNode?.properties?.tags) ? areaNode.properties.tags : [];
            const areaTagsLower = areaTags.map(t => String(t).toLowerCase());
            const areaHasFixture = RELIEF_RE.test(String(currentArea?.name || ''))
                || areaTagsLower.some(t => RELIEF_RE.test(t));
            const areaItems = (areaRef && typeof worldState?.getItemsInArea === 'function')
                ? (worldState.getItemsInArea(areaRef) || [])
                : [];
            const itemHasFixture = areaItems.some((it) => {
                const itTags = Array.isArray(it?.properties?.tags) ? it.properties.tags : [];
                return RELIEF_RE.test(String(it?.name || '')) || itTags.some(t => RELIEF_RE.test(String(t)));
            });
            const isOutdoor = areaTagsLower.includes('outdoor')
                || areaTagsLower.includes('exterior')
                || areaNode?.properties?.is_exterior === true;
            const hasOnlookers = (others || []).length > 0;
            if (areaHasFixture || itemHasFixture) {
                keep('relieve', 'relieve  -  use the restroom/toilet here (your bladder is full)');
            }
            else if (isOutdoor && !hasOnlookers) {
                keep('relieve', 'relieve  -  relieve yourself outdoors in the open here (no toilet here, though you are alone - find a restroom if one is nearby)');
            }
            else if (isOutdoor && hasOnlookers) {
                keep('relieve', 'relieve  -  relieve yourself right where you stand outdoors in front of others (NO toilet here - move somewhere private or find a restroom first)');
            }
            else if (!isOutdoor && !hasOnlookers) {
                keep('relieve', 'relieve  -  relieve yourself right on the indoor floor here (NO toilet here - leave and find a restroom first!)');
            }
            else {
                keep('relieve', 'relieve  -  relieve yourself right on the indoor floor in front of others (NO toilet here - leave and find a restroom first!)');
            }
        }
        if (blind)
            keep('listen', 'listen  -  listen hard (you are blind)');
        if (!hasDarkVision && (blind || level === 'pitch_black' || level === 'dim'))
            keep('fumble', 'fumble  -  blind search in the darkness');
        const activePhones = activePhoneNodes(charName, currentArea);
        if (activePhones.length) {
            keep('call', 'call  -  call a contact by phone (call <contact>)');
            keep('text', 'text  -  send a text message (text <contact|#channel> <message>)');
            const incomingFrom = player?.incoming_call_from
                || activePhones.map(p => p.properties?.incoming_call_from).find(Boolean);
            const onCall = !!(player?.conditions?.on_a_call)
                || !!(player?.call_partner)
                || activePhones.some(p => p.properties?.call_state === 'connected' || p.properties?.call_state === 'calling');
            if (incomingFrom) {
                keep('answer', `answer  -  answer incoming call from ${incomingFrom}`);
                keep('hangup', `hangup  -  dismiss incoming call from ${incomingFrom}`);
            }
            else if (onCall) {
                keep('hangup', 'hangup  -  end the current phone call');
            }
        }
        if (currentArea?.name)
            keep('examine', `examine <target>  -  inspect something closely (e.g. examine ${currentArea.name})`);
        keep('look', 'look  -  look around');
        keep('inventory', 'inventory  -  check your inventory');
        keep('stats', 'stats  -  check your stats');
        keep('schedule', 'schedule [add HH:MM <activity> [at <area>] | remove HH:MM]  -  check or update your daily routine (free action)');
        keep('plan', 'plan <intent>  -  form a grounded multi-step plan (free action)');
        // task-840: craftable-now recipes as guidance (backend resolves
        // leniently, so this only suggests  -  never gates).
        for (const line of craftableLines(charName, player, currentArea)) {
            keep('make', line);
        }
        // The turn's exit. Never hidden: with no slots left this is the only way
        // to end the turn, and hiding it would strand the character.
        lines.push('wait  -  wait or hold still');
        let note = '';
        if (slots && typeof slots.major === 'number' && slots.major <= 0) {
            if (typeof slots.minor === 'number' && slots.minor <= 0) {
                note = '\n(Major and minor actions exhausted this turn. Only free actions, speech, or wait remain.)';
            }
            else {
                note = '\n(Major actions exhausted this turn. You can still use minor/free actions, speak, or wait.)';
            }
        }
        const intro = 'Other than what you see around the room, what you are wearing or carrying, or who else is here, you can do these actions:';
        return `\n=== AVAILABLE ACTIONS ===\n${intro}\n${lines.join('\n')}${note}`;
    }
    Object.assign(window.PromptBuilder, {
        computeItemActions,
        formatActionBrackets,
        buildAvailableActionsBlock,
        carriedItemNodes,
        knownAbilityNodes,
        itemTriggerTypes,
        useOnTargetName,
        isDiscovered,
        isIntrinsicAbility
    });
})();
