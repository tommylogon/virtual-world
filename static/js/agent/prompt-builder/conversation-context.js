/**
 * prompt-builder/conversation-context.js — Speech salience + conversation instinct.
 *
 * Split from room-context.js (2026-08-21). Holds the logic for how a character
 * reads spoken dialogue: which lines are aimed at THEM (salience) vs just
 * overheard, plus a soft guard against repeating their own recent lines.
 *
 * The guiding principle is "weighted emphasis, never a command." Classifying a
 * line as `addressed to you` raises its salience so the character NOTICES it, but
 * the decision to speak stays theirs. Overheard and group lines carry no respond
 * directive at all.
 *
 * Exports merge into window.PromptBuilder.
 *
 * Cross-file calls use PromptBuilder.<fn>(...).
 */

window.PromptBuilder = window.PromptBuilder || {};
(() => {
    'use strict';

    const GROUP_WORDS = [
        'everyone', 'everybody', 'everyone here', 'anyone', 'anybody',
        'you all', 'you two', 'you both', 'you guys', 'folks', 'everybody here'
    ];

    // ────────────────────────── Salience classification ─────────────────────

    /**
     * Classify how directly a line of spoken text seems aimed at the listener.
     * @param {string} text - The spoken line (no wrapping narration).
     * @param {string} charName - Listener's name/best name.
     * @param {Object} player - Listener player object (may carry aliases).
     * @returns {'overheard'|'addressed_to_you'|'to_you'|'to_group'}
     *   - addressed_to_you: the listener's name (or an alias) appears.
     *   - to_you: a clear second-person pronoun targets them, no name needed.
     *   - to_group: group-open wording ("everyone/anyone/you all", ...).
     *   - overheard: nothing marks it as being for the listener.
     */
    function classifySpeechType(text, charName, player) {
        const lower = String(text || '').toLowerCase().replace(/\s+/g, ' ').trim();
        if (!lower) return 'overheard';

        // Names/aliases the listener answers to — name call is the strongest mark.
        const nameParts = [charName, player?.name]
            .filter(Boolean)
            .map(n => String(n).toLowerCase().trim());
        for (const candidate of nameParts) {
            if (!candidate) continue;
            const boundary = candidate.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const re = new RegExp(`(?:^|[^a-z0-9])${boundary}(?:$|[^a-z0-9])`);
            if (re.test(lower)) return 'addressed_to_you';
        }

        // Group-open wording — spoken to a room, not one person.
        for (const word of GROUP_WORDS) {
            if (lower.includes(word)) return 'to_group';
        }

        // A clear second-person pronoun pointing at the listener (you / your /
        // you're / yours / you've). Ambiguous third-person talk stays overhead.
        if (/\b(you|your|yours|you're|you've|you'll|you'd)\b/.test(lower)) return 'to_you';

        return 'overheard';
    }

    /**
     * Render a human label for a classification tag ('' for overheard).
     * @param {string} type - One of the classifySpeechType results.
     * @returns {string} e.g. "addressed to you", or '' when not notable.
     */
    function salienceLabel(type) {
        switch (type) {
            case 'addressed_to_you': return 'addressed to you';
            case 'to_you': return 'to you';
            case 'to_group': return 'to the group';
            default: return '';
        }
    }

    /**
     * Wrap a WITNESSED line so its direction is visible at a glance, e.g.
     *   "[Heard] a voice said: "hey lyrie, watch out!""  (overheard → unchanged)
     *   "[Heard → addressed to you] a voice said: "hey lyrie, watch out!""
     * @param {string} line - The already-built WITNESSED line.
     * @param {string} text - The plain spoken text being marked.
     * @param {string} charName - Listener's name.
     * @param {Object} player - Listener player object.
     * @returns {string} Marked line, or the original if the line isn't notable.
     */
    function markSpeechLine(line, text, charName, player) {
        const type = classifySpeechType(text, charName, player);
        const label = salienceLabel(type);
        if (!label || !line) return line;
        // Insert the marker right after the leading [Heard]/[anon] bracket.
        if (line.indexOf(']') !== -1) {
            const close = line.indexOf(']');
            return line.slice(0, close) + ' → ' + label + line.slice(close);
        }
        return `[${label}] ${line}`;
    }

    /**
     * Collect the lines this character recently SAID themselves (for a soft
     * anti-repeat guard). `recent_hearing` includes the speaker's own lines, so
     * filter for rows whose speaker is this character, last few, deduped.
     * @param {Object} player - Listener player object (has recent_hearing).
     * @param {string} charName - The character's name.
     * @returns {string[]} Recent unique quoted lines the character spoke.
     */
    function ownRecentSpeech(player, charName) {
        const hearing = player?.recent_hearing || [];
        const mine = hearing.filter(h => h.type !== 'sound_source' && h.speaker === charName);
        const seen = new Set();
        const out = [];
        for (const h of mine.slice(-5)) {
            const text = String(h.text || '').trim();
            if (!text) continue;
            const key = text.toLowerCase();
            if (seen.has(key)) continue;
            seen.add(key);
            out.push(`"${text}"`);
        }
        return out;
    }

    /**
     * A short per-turn "conversation disposition" hint derived from existing
     * state (never a mandate — just how the character currently feels about
     * speaking). Reuses `vitals.social` and conditions like exhaustion/fear to
     * nudge talkativeness up or down without a stored per-character value.
     * @param {Object} player - The character's player object.
     * @returns {string} A disposition phrase, or '' when neutral.
     */
    function talkinessHint(player) {
        if (!player) return '';
        const social = parseInt(player.vitals?.social) || 50;
        const conditions = player.conditions || {};
        const hindered = ['exhausted', 'unconscious', 'frightened', 'anxious', 'stunned', 'pain', 'sick']
            .some(c => (conditions[c] || []).length > 0);
        if (hindered && social < 40) return 'You feel worn down and quiet — you speak only if you must.';
        if (social >= 75) return 'You feel sociable right now — inclined to speak up.';
        if (social <= 25) return 'You feel withdrawn right now — you\'re not inclined to speak unless something needs saying.';
        return '';
    }

    /**
     * Assemble the conversation instinct note for the context: what the character
     * recently said themself (anti-repeat) plus a soft inclination hint.
     * @param {Object} player - The character's player object.
     * @param {string} charName - The character's name.
     * @returns {string} Multi-line block, or '' when there's nothing notable.
     */
    function buildConversationInstinct(player, charName) {
        const own = ownRecentSpeech(player, charName);
        const vibe = talkinessHint(player);
        const parts = [];
        if (own.length) parts.push(`You recently said: ${own.join('; ')}` + '\nDo not repeat a line you already said, unless you are genuinely insisting.');
        if (vibe) parts.push(vibe);
        return parts.length ? '\n\n=== CONVERSATION ===\n' + parts.join('\n') : '';
    }

    Object.assign(window.PromptBuilder, {
        classifySpeechType,
        salienceLabel,
        markSpeechLine,
        ownRecentSpeech,
        talkinessHint,
        buildConversationInstinct
    });
})();