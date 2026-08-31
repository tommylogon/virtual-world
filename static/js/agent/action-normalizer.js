/**
 * action-normalizer.js — Action schema translation and validation
 *
 * Converts structured LLM action fields {action, item, target, relation}
 * into the free-text command strings the backend expects, and validates
 * that the chosen verb is actually allowed.
 *
 * Load BEFORE agent-engine.js.
 */

window.ActionNormalizer = (() => {
    'use strict';

    const VALID_VERBS = new Set([
        'do', 'go', 'dash', 'crawl', 'climb', 'jump', 'grab', 'escape', 'struggle',
        'open', 'close', 'take', 'get', 'pickup', 'drop', 'put', 'place', 'give', 'hand',
        'steal', 'use', 'eat', 'drink', 'examine', 'speak', 'say', 'look', 'inventory',
        'i', 'inv', 'stats', 'status', 'rest', 'sleep', 'fumble', 'toggle', 'attack',
        'manifest', 'vanish', 'relieve', 'read', 'search', 'inspect', 'check', 'light',
        'ignite', 'grab', 'snatch', 'collect', 'hit', 'strike', 'punch', 'yell', 'shout',
        'whisper', 'scream', 'pick', 'wear', 'equip', 'remove', 'unequip', 'wait',
        'nothing', 'pause', 'stay', 'stand', 'listen', 'lead', 'approach',
        'stow', 'combine', 'split', 'craft', 'make', 'teach',
        'bind', 'enchant'
    ]);

    const MOVE_VERBS = new Set(['go', 'dash', 'crawl', 'climb', 'jump']);
    /** Check whether an action string uses a supported verb or matches a known exit name. */
    function isValidAction(action, charName) {
        if (typeof action !== 'string' || action.trim() === '') return false;
        const trimmed = action.trim();
        if (trimmed.includes('command from') || trimmed.includes('your ') || trimmed.includes('your_') || trimmed.includes('](')) return false;
        const verb = trimmed.split(/\s+/)[0].toLowerCase();
        if (VALID_VERBS.has(verb)) return true;
        if (charName) {
            const player = worldState.data?.players?.[charName];
            const area = player?.current_area ? worldState.areas?.[player.current_area] : null;
            if (area?.exits) {
                const exitNames = Object.keys(area.exits).map(exitName => exitName.toLowerCase());
                if (exitNames.includes(trimmed.toLowerCase())) return true;
            }
        }
        return false;
    }

    /** Convert structured {action, item, target, relation} into a backend command string. */
    function normalizeStructuredAction(p) {
        if (!p) return '';
        const verb = String(p.action || '').trim();
        if (!verb) return '';
        const item = String(p.item || '').trim();
        const target = String(p.target || '').trim();
        const relation = String(p.relation || '').trim().toLowerCase() || 'on';
        // The object being acted on may land in either "item" (e.g. the LLM wrote
        // {"action":"examine","item":"front_door"}) or "target". Fall back to item for
        // any verb whose object is a thing/place/person so a missing "target" doesn't
        // silently degrade the action to a bare verb.
        const obj = target || item;
        const isPlain = /\s/.test(verb) || /^(use .* on |go |take |open |close |examine |attack |whisper |say |shout |scream )/.test(verb);
        if (isPlain) return verb;
        switch (verb) {
            case 'use': return item ? `use ${item}` : 'use';
            case 'use_on': {
                // task-196: amount for quantity ("use 2 eggs on pan").
                const amount = parseInt(p.amount, 10);
                if (item && target && Number.isInteger(amount) && amount > 1) {
                    return `use ${amount} ${item} on ${target}`;
                }
                return item && target ? `use ${item} on ${target}` : (item ? `use ${item}` : 'use');
            }
            case 'go': case 'dash': case 'crawl': case 'climb': case 'jump': return obj ? `${verb} ${obj}` : verb;
            case 'approach': return obj ? `approach ${obj}` : verb;
            case 'open': case 'close': return obj ? `${verb} ${obj}` : verb;
            case 'take': case 'drop': case 'pickup': return item ? `${verb} ${item}` : verb;
            case 'put': case 'place': {
                const rel = ['on', 'under', 'beside', 'behind', 'at', 'in'].includes(relation) ? relation : 'on';
                return item && target ? `put ${item} ${rel} ${target}` : (item ? `put ${item}` : verb);
            }
            case 'give': case 'hand': return item && target ? `give ${item} to ${target}` : verb;
            case 'teach': return item && target ? `teach ${item} to ${target}` : verb;
            case 'eat': case 'consume': return obj ? `eat ${obj}` : 'eat';
            case 'drink': case 'quaff': return obj ? `drink ${obj}` : 'drink';
            case 'steal': return item && target ? `steal ${item} from ${target}` : (item ? `steal ${item}` : verb);
            case 'lead': return obj ? `lead ${obj}` : verb;
            case 'listen': case 'stand': return verb;
            case 'examine': case 'read': case 'search': case 'inspect': case 'check': return obj ? `examine ${obj}` : verb;
            case 'attack': {
                const where = String(p.where || '').trim();
                return where ? `attack ${obj} on ${where}` : (obj ? `attack ${obj}` : verb);
            }
            case 'grab': return obj ? `grab ${obj}` : verb;
            case 'escape': case 'struggle': return verb;
            case 'wear': case 'equip': return item ? `wear ${item}` : verb;
            case 'remove': case 'unequip': return item ? `remove ${item}` : verb;
            case 'rest': case 'sleep': {
                const dur = item && /^\d+$/.test(item) ? item : (target && /^\d+$/.test(target) ? target : '');
                return dur ? `${verb} ${dur}` : verb;
            }
            case 'whisper': case 'say': case 'shout': case 'scream': case 'speak': return verb;
            case 'look': case 'inventory': case 'i': case 'inv': case 'stats': case 'status': case 'wait': case 'nothing': case 'pause': case 'stay': case 'relieve': case 'fumble': case 'manifest': case 'vanish': case 'toggle': case 'light': case 'ignite': case 'grab': case 'snatch': case 'collect': case 'hit': case 'strike': case 'punch': case 'yell': return verb;
            case 'bind': case 'enchant': {
                // task-242: agent-authored item trigger. Schema:
                //   {action:"bind", item:"<name>", when:"on_use|on_take|...", effect:"message|...", effect_params:{...}}
                // Command: `bind <item> <when>:<effect> [json params]`
                const when = String(p.when || p.trigger_type || 'on_use').trim();
                const effect = String(p.effect || p.effect_type || 'message').trim();
                const extra = p.effect_params && Object.keys(p.effect_params).length
                    ? ' ' + JSON.stringify(p.effect_params)
                    : '';
                return item ? `bind ${item} ${when}:${effect}${extra}` : verb;
            }
            default: return verb;
        }
    }

    /** Extract speech text + volume from a parsed response object. */
    function extractSpeechVolume(p) {
        if (!p) return { speech: null, volume: 'say' };
        let speech = null;
        let volume = 'say';
        const normVol = (v) => {
            const s = String(v || '').toLowerCase();
            if (s === 'whisper' || s === 'shout' || s === 'scream') return s;
            if (s === 'speak' || s === 'talk') return 'say';
            return 'say';
        };
        if (p.speech != null && p.speech !== '') { speech = p.speech; volume = normVol(p.volume); }
        else if (p.whisper != null) { speech = p.whisper; volume = 'whisper'; }
        else if (p.say != null) { speech = p.say; volume = normVol(p.volume); }
        else if (p.shout != null) { speech = p.shout; volume = 'shout'; }
        else if (p.scream != null) { speech = p.scream; volume = 'scream'; }
        return { speech, volume };
    }

    /** Volume → verb for event stream labels. */
    function volVerb(volume) {
        return { whisper: 'whispers', say: 'says', shout: 'shouts', scream: 'screams' }[volume || 'say'] || 'says';
    }

    return {
        isValidAction,
        normalizeStructuredAction,
        extractSpeechVolume,
        volVerb
    };
})();
