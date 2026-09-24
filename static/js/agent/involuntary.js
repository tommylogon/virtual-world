/**
 * involuntary.js — task-166: involuntary actions (hiccups, burps, yelps,
 * stutters) injected into agent speech/emotes.
 *
 * Non-blocking flavor only: these methods return a possibly-modified string
 * and NEVER replace the intended action. Injection is driven by active
 * character conditions (frightened → stutter, cold → shiver, sick/poisoned
 * → cough), a situational startle (a sudden loud sound → yelp), the `jittery`
 * trait, plus a low random baseline so life happens even without a trigger
 * condition.
 *
 * This is a LIVEGAME layer: it runs where a character's line is emitted
 * (agent-engine), for the attended/LLM-agent set. Background and simple NPCs
 * have no speech/emote emission path, so they intentionally never reach it —
 * the cheap tier stays cheap. The roll is per emitted line, not per turn, so
 * it stays correct under the timeframe-and-flow model (task-436/437).
 *
 * @module agent/involuntary — involuntary speech/emote flavour
 * @contributes Involuntary: hiccup/burp/yelp/stutter injection from conditions + a small random baseline
 * @powers the "*a hiccup catches her off guard*" moments in agent output
 * @relates called by agent-engine when framing speech/emotes; never replaces the intended action
 * @docs docs/virtualWorld/AI & Narration/Agent Engine.md
 */
window.Involuntary = (() => {
    'use strict';

    // Configurable odds. Boosted substantially when a trigger condition is
    // active so flavor is noticeable in the situations that call for it.
    const RANDOM_SPEECH_CHANCE = 0.06;
    const RANDOM_EMOTE_CHANCE = 0.04;

    // A sudden loud sound (shout/scream) makes a yelp much more likely than
    // the ambient random baseline. The agent engine reports this per line via
    // the `startled` flag; it never fires on its own.
    const STARTLE_SPEECH_CHANCE = 0.35;
    const STARTLE_EMOTE_CHANCE = 0.70;

    // Traits that make involuntary reactions more likely (task-166: "a clumsy
    // or nervous trait could raise the chance"). `jittery` is the library id;
    // the aliases are defensive so authored/label variants still count.
    const NERVOUS_TRAITS = ['jittery', 'nervous', 'clumsy'];
    const NERVOUS_BOOST = 1.8;

    // condition_id -> {type, chance} for speech interruptions.
    const SPEECH_TRIGGERS = {
        frightened: { type: 'stutter', chance: 0.50 },
        hypothermia: { type: 'shiver', chance: 0.40 },
        sick: { type: 'cough', chance: 0.35 },
        poisoned: { type: 'cough', chance: 0.40 },
        social_breakdown: { type: 'ramble', chance: 0.25 },
        paranoid: { type: 'stutter', chance: 0.40 },
        hallucinating: { type: 'ramble', chance: 0.45 },
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
        paranoid: [
            '*{they} glance around, eyes darting*',
            '*a nervous glance over {their} shoulder*',
            '*{they} grip {their} weapon tighter, knuckles white*',
        ],
        hallucinating: [
            '*{they} stare at something no one else can see*',
            '*{they} mutter to an empty corner of the room*',
            '*{their} gaze slides past the person in front of them*',
        ],
    };

    const GENERIC_SPEECH = ['hic', 'burp', 'yelp'];
    const GENERIC_EMOTES = [
        '*a small hiccup escapes*',
        '*a hiccup catches {them} off guard*',
        '*{they} burp softly, startled by it*',
        '*a short yelp escapes*',
    ];

    // A sudden loud sound lands on a character who did not expect it. These
    // are stronger than the ambient hiccup/burp pool on purpose.
    const STARTLE_EMOTES = [
        '*{they} flinch hard, a sharp yelp escaping*',
        '*{they} jolt upright, heart hammering*',
        '*a startled gasp catches in {their} throat*',
        '*{they} spin toward the noise, eyes wide*',
    ];

    function _hasTrait(player, traitId) {
        return !!(player?.traits && player.traits[traitId]);
    }

    /** Multiplier applied to every involuntary roll for nervous characters. */
    function _traitBoost(player) {
        return NERVOUS_TRAITS.some(t => _hasTrait(player, t)) ? NERVOUS_BOOST : 1.0;
    }

    /** True when the caller reports a startle this line (a sudden loud sound). */
    function _startled(context) {
        return !!(context && context.startled);
    }

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
     * @param {string} speech - The intended line
     * @param {Object} player - Player data object
     * @param {Object} [context] - Optional signals, e.g. {startled:true}
     */
    function speech(speech, player, context) {
        if (!speech || typeof speech !== 'string') return null;
        const boost = _traitBoost(player);
        // A startle trumps everything: the yelp is the moment.
        if (_startled(context) && Math.random() < STARTLE_SPEECH_CHANCE) {
            return _interrupt(speech, 'yelp');
        }
        // Condition-driven injection takes precedence over random flavor.
        for (const cid of Object.keys(SPEECH_TRIGGERS)) {
            if (_hasCondition(player, cid)) {
                const { type, chance } = SPEECH_TRIGGERS[cid];
                if (Math.random() < Math.min(1, chance * boost)) return _interrupt(speech, type);
            }
        }
        if (Math.random() < Math.min(1, RANDOM_SPEECH_CHANCE * boost)) {
            const kind = GENERIC_SPEECH[Math.floor(Math.random() * GENERIC_SPEECH.length)];
            return _interrupt(speech, kind);
        }
        return null;
    }

    /**
     * Return a possibly-modified emote string (or null when nothing fires).
     * @param {string} emoteText - The intended emote
     * @param {Object} player - Player data object
     * @param {Object} [context] - Optional signals, e.g. {startled:true}
     */
    function emote(emoteText, player, context) {
        if (!emoteText || typeof emoteText !== 'string') return null;
        const boost = _traitBoost(player);
        if (_startled(context) && Math.random() < STARTLE_EMOTE_CHANCE) {
            const pick = STARTLE_EMOTES[Math.floor(Math.random() * STARTLE_EMOTES.length)];
            return `${emoteText} ${_render(pick, player)}`.trim();
        }
        for (const cid of Object.keys(EMOTE_TRIGGERS)) {
            if (_hasCondition(player, cid)) {
                const pool = EMOTE_TRIGGERS[cid];
                const pick = pool[Math.floor(Math.random() * pool.length)];
                return `${emoteText} ${_render(pick, player)}`.trim();
            }
        }
        if (Math.random() < Math.min(1, RANDOM_EMOTE_CHANCE * boost)) {
            const pool = GENERIC_EMOTES;
            const pick = pool[Math.floor(Math.random() * pool.length)];
            return `${emoteText} ${_render(pick, player)}`.trim();
        }
        return null;
    }

    // Exposed for tests and for callers that want the startle pool directly.
    const _internals = { STARTLE_EMOTES, NERVOUS_TRAITS, NERVOUS_BOOST };

    return { speech, emote, _internals };
})();