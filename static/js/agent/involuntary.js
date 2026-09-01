/**
 * involuntary.js — task-166: involuntary actions (hiccups, burps, yelps,
 * stutters) injected into agent speech/emotes.
 *
 * Non-blocking flavor only: these methods return a possibly-modified string
 * and NEVER replace the intended action. Injection is driven by active
 * character conditions (frightened → stutter, cold → shiver, sick/poisoned
 * → cough) plus a low random baseline so life happens even without a
 * trigger condition.
 */
window.Involuntary = (() => {
    'use strict';

    // Configurable odds. Boosted substantially when a trigger condition is
    // active so flavor is noticeable in the situations that call for it.
    const RANDOM_SPEECH_CHANCE = 0.06;
    const RANDOM_EMOTE_CHANCE = 0.04;

    // condition_id -> {type, chance} for speech interruptions.
    const SPEECH_TRIGGERS = {
        frightened: { type: 'stutter', chance: 0.50 },
        hypothermia: { type: 'shiver', chance: 0.40 },
        sick: { type: 'cough', chance: 0.35 },
        poisoned: { type: 'cough', chance: 0.40 },
        social_breakdown: { type: 'ramble', chance: 0.25 },
    };

    // condition_id -> emote suffixes (also used for random generic flavor).
    const EMOTE_TRIGGERS = {
        frightened: [
            '*a small gasp escapes*',
            '*an involuntary shudder runs through {them}*',
            '*a nervous flinch twitches {their} hands*',
        ],
        hypothermia: [
            '*{they} shiver violently, teeth chattering*',
            '*a long shiver runs down {their} spine*',
        ],
        sick: [
            '*a rattling cough escapes*',
            '*{they} cough into {their} hand*',
        ],
        poisoned: [
            '*a wracking cough doubles {them} over*',
            '*{they} sway, green about the gills*',
        ],
        social_breakdown: [
            '*{they} mutter to no one in particular*',
            '*a laugh escapes that sounds hollow*',
        ],
        itch: [
            '*{they} scratch at an itch, annoyed*',
            '*a restless scratch at {their} arm*',
        ],
        goosebumps: [
            '*goosebumps prickle over {their} skin*',
            '*{they} rub {their} arms against the goosebumps*',
        ],
    };

    const GENERIC_SPEECH = ['hic', 'burp', 'yelp'];
    const GENERIC_EMOTES = [
        '*a small hiccup escapes*',
        '*a hiccup catches {them} off guard*',
        '*{they} burp softly, startled by it*',
        '*a short yelp escapes*',
    ];

    function _hasCondition(player, cid) {
        const conds = player?.conditions;
        if (!conds) return false;
        if (Array.isArray(conds)) return conds.includes(cid);
        if (typeof conds === 'object') return !!conds[cid];
        return false;
    }

    function _pronoun(player, form) {
        const tags = player?.tags || [];
        const male = tags.includes('male') || /he\b/i.test(JSON.stringify(player?.pronouns || ''));
        const female = tags.includes('female') || /she\b/i.test(JSON.stringify(player?.pronouns || ''));
        if (form === 'subj') return male ? 'he' : (female ? 'she' : 'they');
        if (form === 'obj') return male ? 'him' : (female ? 'her' : 'them');
        if (form === 'poss') return male ? 'his' : (female ? 'her' : 'their');
        return male ? 'he' : (female ? 'she' : 'they');
    }

    function _render(text, player) {
        return String(text)
            .replace(/\{them\}/g, _pronoun(player, 'obj'))
            .replace(/\{their\}/g, _pronoun(player, 'poss'))
            .replace(/\{they\}/g, _pronoun(player, 'subj'))
            .replace(/\{he\}/g, _pronoun(player, 'subj'))
            .replace(/\{her\}/g, _pronoun(player, 'poss'));
    }

    /**
     * Stutter the first word: "What..." → "W-what...", "I can't" → "I-I can't".
     */
    function _stutter(text) {
        const m = /^(\s*)([A-Za-z]+)(.*)$/.exec(text || '');
        if (!m) return text;
        const [, ws, word, rest] = m;
        const letter = word[0];
        const tail = word.length > 1 ? word.slice(1) : '';
        const lc = letter.toLowerCase();
        const head = letter === 'I' ? `${letter}-${letter}` : `${letter}-${lc}`;
        return `${ws}${head}${tail}${rest}`;
    }

    function _interrupt(text, kind) {
        const t = (text || '').trim();
        if (!t) return text;
        if (kind === 'stutter' || kind === 'shiver') {
            return _stutter(text);
        }
        if (kind === 'cough') {
            return `${t} ...*cough*...`;
        }
        // hic / burp / yelp / ramble: splice a flavor fragment at a pause.
        const pauseIdx = t.search(/[.!?,;]/);
        if (pauseIdx === -1) return `${t} ...*${kind}*...`;
        return `${t.slice(0, pauseIdx + 1)} ...*${kind}*... ${t.slice(pauseIdx + 1).trim()}`;
    }

    /**
     * Return a possibly-modified speech string (or null when nothing fires).
     */
    function speech(speech, player) {
        if (!speech || typeof speech !== 'string') return null;
        // Condition-driven injection takes precedence over random flavor.
        for (const cid of Object.keys(SPEECH_TRIGGERS)) {
            if (_hasCondition(player, cid)) {
                const { type, chance } = SPEECH_TRIGGERS[cid];
                if (Math.random() < chance) return _interrupt(speech, type);
            }
        }
        if (Math.random() < RANDOM_SPEECH_CHANCE) {
            const kind = GENERIC_SPEECH[Math.floor(Math.random() * GENERIC_SPEECH.length)];
            return _interrupt(speech, kind);
        }
        return null;
    }

    /**
     * Return a possibly-modified emote string (or null when nothing fires).
     */
    function emote(emoteText, player) {
        if (!emoteText || typeof emoteText !== 'string') return null;
        for (const cid of Object.keys(EMOTE_TRIGGERS)) {
            if (_hasCondition(player, cid)) {
                const pool = EMOTE_TRIGGERS[cid];
                const pick = pool[Math.floor(Math.random() * pool.length)];
                return `${emoteText} ${_render(pick, player)}`.trim();
            }
        }
        if (Math.random() < RANDOM_EMOTE_CHANCE) {
            const pool = GENERIC_EMOTES;
            const pick = pool[Math.floor(Math.random() * pool.length)];
            return `${emoteText} ${_render(pick, player)}`.trim();
        }
        return null;
    }

    return { speech, emote };
})();