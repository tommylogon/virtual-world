/**
 * prompt-builder/helpers.js — Leaf-level utility functions for prompt building.
 *
 * Split from the monolithic prompt-builder.js (2026-08-09). These are
 * side-effect-free helpers that only reference global state (worldState, VW)
 * at call time. Exports merge into the shared window.PromptBuilder namespace
 * via Object.assign — load order between the split files does not matter, and
 * nothing executes at load time.
 *
 * Cross-file internal calls use PromptBuilder.<fn>(...).
 */

window.PromptBuilder = window.PromptBuilder || {};
(() => {
    'use strict';

    /**
     * Convert a numeric light value (0-100) to a level string.
     * Mirrors engine/lighting.py:light_to_level.
     * @param {number} value - Light value 0-100
     * @returns {string} Level name: 'pitch_black' | 'dim' | 'normal' | 'bright' | 'blinding'
     */
    function lightToLevel(value) {
        const numValue = parseInt(value) || 50;
        if (numValue <= 20) return 'pitch_black';
        if (numValue <= 40) return 'dim';
        if (numValue <= 70) return 'normal';
        if (numValue <= 90) return 'bright';
        return 'blinding';
    }

    /**
     * Strip a leading article from a description fragment ("a tall man" → "tall man").
     */
    function stripLeadingArticle(text) {
        return text.replace(/^(a|an|the)\s+/i, '');
    }

    /**
     * Indefinite article for an item name ("a toy_box", "an Ink Pen").
     */
    function indefiniteArticle(name) {
        return /^[aeiou]/i.test(String(name || '')) ? 'an' : 'a';
    }

    /**
     * A reference handle for an exit/way: the exit label (direction) when set,
     * else a short name derived from the way node's name (strip the source area's
     * "Name - " prefix, underscores → spaces), else "door". Shared by room-context
     * and the contextual-actions block so both name a given exit the same way.
     * @param {Object} exitData - Exit entry (label, direction)
     * @param {Object} doorNode - The way node, or null
     * @param {string} areaName - Current area name, for stripping the node prefix
     * @returns {string} A display handle for the exit
     */
    function wayHandle(exitData, doorNode, areaName) {
        const label = String(exitData?.label ?? exitData?.direction ?? '').trim();
        if (label) return label;
        if (doorNode?.name) {
            let name = String(doorNode.name).trim();
            if (areaName && name.toLowerCase().startsWith(`${String(areaName).toLowerCase()} - `)) {
                name = name.slice(areaName.length + 3).trim();
            }
            name = name.replace(/_/g, ' ').trim();
            if (name) return name;
        }
        return 'door';
    }

    /**
     * Map item id → { prep, anchorName } for every item that sits in a spatial
     * relation (on/under/behind/beside/at/in) to an anchor item that is itself
     * present in the area. This lets the item listing tell the agent *where*
     * each object is, instead of a flat name list (task-105).
     *
     * Edges pointing at the area itself (e.g. table → room) are not spatial
     * relations to an anchor, so those items render flat.
     */
    function buildRelationMap(areaItems) {
        const relationMap = {};
        const spatialTypes = ['on', 'under', 'behind', 'beside', 'at', 'in'];
        const areaItemIds = new Set(areaItems.map(item => item.id));
        for (const edge of worldState.graph?.edges || []) {
            if (!spatialTypes.includes(edge.type)) continue;
            const anchorId = edge.target;
            if (!areaItemIds.has(anchorId)) continue;
            const sourceNode = worldState.getNode(edge.source);
            if (!sourceNode || sourceNode.type !== 'item') continue;
            const anchorNode = worldState.getNode(anchorId);
            relationMap[edge.source] = {
                prep: edge.type,
                anchorName: anchorNode?.name || anchorId
            };
        }
        return relationMap;
    }

    /**
     * Return how this character should refer to another.
     * Known characters are called by their real name. Strangers (no relationship
     * record yet) are labelled by their appearance so the character never
     * learns a name they haven't been told (task-154).
     */
    function anonymousName(charName, targetName, targetDesc) {
        const hasMet = worldState.hasMet(charName, targetName);
        if (hasMet) return targetName;
        // Authored `known` registry: a character flagged as known to the
        // viewer is never masked, regardless of meeting state.
        const viewer = worldState.data?.players?.[charName];
        const known = new Set((viewer?.known || []).map(String));
        const targetSlug = String(targetName || '').toLowerCase().replace(/\s+/g, '_');
        if (known.has(String(targetName || '')) || known.has('player_' + targetSlug) || known.has('character_' + targetSlug)) {
            return targetName;
        }
        const player = worldState.data?.players?.[targetName] || {};
        const tagMap = {
            female: 'the woman', male: 'the man', woman: 'the woman', man: 'the man',
            girl: 'a girl', boy: 'a boy', child: 'a child', animal: 'an animal'
        };
        for (const tag of (player.tags || [])) {
            const mapped = tagMap[String(tag).toLowerCase()];
            if (mapped) return mapped;
        }
        const firstSentence = (targetDesc || '').split(/[.!?]/)[0].trim();
        if (firstSentence) return `the ${stripLeadingArticle(firstSentence).toLowerCase()}`;
        return 'the stranger';
    }

    /**
     * How a character should refer to someone they can HEAR but not see
     * (cross-room speech). Physical appearance is useless through a wall —
     * use voice characteristics instead. Derives from the speaker's tags
     * (female/male/woman/man/girl/boy/child), falling back to pronouns in
     * their description, then a generic voice.
     */
    function voiceLabel(charName, targetName) {
        const hasMet = worldState.hasMet(charName, targetName);
        if (hasMet) return targetName;
        const player = worldState.data?.players?.[targetName] || {};
        const tagMap = {
            female: 'woman', male: 'man', woman: 'woman', man: 'man',
            girl: 'girl', boy: 'boy', child: 'child'
        };
        let gender = '';
        for (const tag of (player.tags || [])) {
            const mapped = tagMap[String(tag).toLowerCase()];
            if (mapped) { gender = mapped; break; }
        }
        if (!gender) {
            const desc = player.base_description || player.description || '';
            if (/\b(she|her|hers)\b/i.test(desc)) gender = 'woman';
            else if (/\b(he|him|his)\b/i.test(desc)) gender = 'man';
        }
        return gender ? `a ${gender}'s voice` : 'a voice';
    }

    /**
     * Check if a character has an active plan in the AgentEngine.
     * @param {string} charName - Character name
     * @returns {boolean} True if plan exists and has steps remaining
     */
    function hasPlan(charName) {
        const agentPlans = window.VW?.agent?._plans;
        const plan = agentPlans?.[charName];
        return !!plan && plan.length > 0;
    }

    /**
     * Re-frame a third-person appearance description into second person so the
     * character reads about THEMSELVES ("You are a woman who stands... your
     * slender frame...") instead of a stranger ("A woman stands... her... ").
     * Handles leading "A/An/The <noun> <verb>s", "She/He <verb>s", pronoun
     * swaps (she/her/his/him → you/your), and verb agreement ("you stands").
     */
    function secondPersonDesc(desc) {
        if (!desc) return '';
        let text = desc.trim();
        const subjectVerbs = 'stands?|sits?|lies?|rests?|leans?|kneels?|looks?|stares?|moves?|walks?|hangs?|awaits?|seems?';
        text = text.replace(new RegExp(`^(?:A|An|The)\\s+(.+?)\\s+(${subjectVerbs})\\b`, 'i'),
            (match, noun, verb) => {
                const article = match.startsWith('A ') ? 'a' : match.startsWith('An ') ? 'an' : match.startsWith('The ') ? 'the' : match.startsWith('a ') ? 'a' : match.startsWith('an ') ? 'an' : match.startsWith('the ') ? 'the' : '';
                return `You are ${article} ${noun} who ${verb}`;
            });
        text = text.replace(new RegExp(`^(She|He)\\s+(${subjectVerbs})\\b`, 'i'),
            (match, pronoun, verb) => `You ${verb.replace(/s$/, '')}`);
        text = text.replace(/\bshe\b/gi, 'you');
        text = text.replace(/\bher\b/gi, 'your');
        text = text.replace(/\bhers\b/gi, 'yours');
        text = text.replace(/\bhe\b/gi, 'you');
        text = text.replace(/\bhim\b/gi, 'you');
        text = text.replace(/\bhis\b/gi, 'your');
        // fix verb agreement after "you" (preserving case): "You stands" → "You stand"
        text = text.replace(new RegExp(`\\b(you)\\s+(${subjectVerbs})\\b`, 'gi'),
            (match, pronoun, verb) => `${pronoun} ${verb.replace(/s$/, '')}`);
        // fix plural possessive agreement: "your breasts rests" → "your breasts rest"
        // (nouns ending in s are treated as plural — regular plurals only)
        text = text.replace(/\byour\s+(\w+s)\s+(stands?|sits?|lies?|rests?|rises?|falls?|hangs?|looks?|moves?|seems?)\b/gi,
            (match, noun, verb) => `your ${noun} ${verb.replace(/s$/, '')}`);
        return text;
    }

    /**
     * Render a player's activity (task-131) as a short flavor string.
     * @param {object} activity - {type, target_item, ...}
     * @returns {string} e.g. "sleeping in the bed"
     */
    function describeActivity(activity) {
        if (!activity) return '';
        const type = activity.type || '';
        const target = activity.target_item;
        if (target && (type === 'sleeping' || type === 'bathing' || type === 'resting')) {
            return `${type} in the ${target}`;
        }
        return type;
    }

    /**
     * Re-frame an agent's own action-result text in first person.
     *
     * The engine logs a `say` as "[Name] says: ..." — when that raw line is
     * fed back to the same agent (JUST HAPPENED / WHAT HAPPENED / memories)
     * it reads like a *third party* in the room, which made agents invent
     * phantom companions ("Jane confirms it too...") from their own name.
     *
     * @param {string} charName - The agent's own character name
     * @param {string} text - Raw action result text
     * @returns {string} Text with the agent's own name re-framed in first person
     */
    function frameSelfSpeech(charName, text) {
        if (!text || !charName) return text || '';
        const escaped = charName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const nameRe = new RegExp(`\\[${escaped}\\]`, 'gi');
        if (!nameRe.test(text)) return text;
        return text
            .replace(new RegExp(`\\[${escaped}\\]\\s*says:`, 'gi'), 'You said:')
            .replace(nameRe, 'you');
    }

    Object.assign(window.PromptBuilder, {
        lightToLevel,
        stripLeadingArticle,
        indefiniteArticle,
        wayHandle,
        buildRelationMap,
        anonymousName,
        voiceLabel,
        hasPlan,
        secondPersonDesc,
        describeActivity,
        frameSelfSpeech
    });
})();
