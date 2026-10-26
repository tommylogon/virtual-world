/**
 * action-normalizer.js  -  Action schema translation and validation
 *
 * Converts structured LLM action fields {action, item, target, relation}
 * into the free-text command strings the backend expects, and validates
 * that the chosen verb is actually allowed.
 *
 * Load BEFORE agent-engine.js.
 *
 * @module agent/action-normalizer  -  LLM action → backend command translation
 * @contributes ActionNormalizer: field→command-string mapping plus verb validation
 * @powers Use / use on  -  turning the LLM's structured action JSON into a command the engine can execute
 * @relates used by agent-engine; mirrors the verb list advertised in the system prompt
 * @docs docs/virtualWorld/AI & Narration/Agent Engine.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

// Local name differs from the global (`ActionNormalizer` is declared in
// types/globals.d.ts) so the two do not collide in the build's scope.
const ActionNormalizerModule = (() => {
    'use strict';

    const _registry = (window as unknown as { ActionVerbs?: { VALID_VERBS?: string[]; MATURE_VERBS?: string[]; VALID_SET?: Set<string>; MATURE_SET?: Set<string>; allVerbs?: (m: boolean) => Set<string> } }).ActionVerbs;
    const VALID_VERBS = _registry?.VALID_SET || new Set(_registry?.VALID_VERBS || [
        'do', 'go', 'dash', 'crawl', 'climb', 'jump', 'grab', 'escape', 'struggle',
        'open', 'close', 'take', 'get', 'pickup', 'drop', 'put', 'place', 'give', 'hand',
        'steal', 'use', 'eat', 'drink', 'examine', 'speak', 'say', 'look', 'inventory',
        'i', 'inv', 'stats', 'status', 'rest', 'sleep', 'fumble', 'toggle', 'attack',
        'manifest', 'vanish', 'relieve', 'read', 'search', 'inspect', 'check', 'light',
        'ignite', 'snatch', 'collect', 'hit', 'strike', 'punch', 'yell', 'shout',
        'whisper', 'scream', 'pick', 'wear', 'equip', 'remove', 'unequip', 'wait',
        'nothing', 'pause', 'stay', 'stand', 'listen', 'lead', 'approach',
        'stow', 'combine', 'split', 'craft', 'make', 'teach',
        'bind', 'enchant', 'fear', 'interest', 'write', 'inscribe',
        'use_on', 'consume', 'quaff', 'release', 'wake'
    ]);

    // task-211: intimacy verbs are only valid actions in mature worlds. Kept
    // out of the base set so non-mature scenarios never accept/emit them.
    const MATURE_VERBS = _registry?.MATURE_SET || new Set(_registry?.MATURE_VERBS || ['kiss', 'caress', 'lick', 'suck', 'bite', 'pinch', 'blow', 'tickle']);
    const INTENSITY_ADVERBS: Record<string, string> = { light: 'gently', firm: 'firmly' };

    function matureEnabled() {
        // MUST stay `window.config`, not bare `config`: the bare form throws
        // ReferenceError when config.js has not loaded (the unit sandbox never
        // loads it), where `window.config` is simply undefined. Rewriting it to
        // satisfy the type checker is what broke test_fear_verbs.
        const cfg = (window as unknown as { config?: { matureContent?: boolean } }).config;
        return !!(cfg && cfg.matureContent);
    }

    let _matureCache: Set<string> | null = null;
    function allVerbs() {
        if (_registry && _registry.allVerbs) {
            return _registry.allVerbs(matureEnabled());
        }
        if (!matureEnabled()) return VALID_VERBS;
        if (!_matureCache) _matureCache = new Set([...VALID_VERBS, ...MATURE_VERBS]);
        return _matureCache;
    }

    /**
     * Why an action was refused. The categories are NOT interchangeable and
     * must never collapse into one generic failure:
     *
     *   - `schema_invalid`  - the model emitted a malformed payload. An
     *     ENGINE-side interface failure. Never reported as something the world
     *     did to the character.
     *   - `unknown_verb`    - the command was well-formed but used a verb the
     *     engine does not implement. Also engine-side.
     *   - `empty`           - no action was chosen (speech-only turn).
     *
     * A well-formed command that the WORLD refuses (a locked door, a missing
     * item) is not in this list: that comes back from the backend as an
     * action result, not as a skip.
     */
    type ActionFailureCategory = 'schema_invalid' | 'unknown_verb' | 'empty';

    interface ActionVerdict {
        ok: boolean;
        category: ActionFailureCategory;
        detail: string;
    }

    /**
     * A stringified object - the fingerprint of a model that nested its action
     * ("action": {"action":"take", ...}) before the normalizer could unwrap it.
     * It must never reach the world as a command.
     */
    function looksStringifiedObject(value: unknown): boolean {
        if (typeof value !== 'string') return false;
        const t = value.trim();
        return t === '[object Object]' || (t.startsWith('{') && t.endsWith('}'));
    }

    /**
     * Classify an action string. Distinguishes the three ways an action can
     * fail so the caller can report each honestly (task: the engine was
     * telling characters the house had supernatural rules when the real cause
     * was a malformed command).
     */
    function classifyAction(action: unknown, charName?: string): ActionVerdict {
        if (typeof action !== 'string' || action.trim() === '') {
            return { ok: false, category: 'empty', detail: 'no action given' };
        }
        const trimmed = action.trim();
        if (looksStringifiedObject(trimmed)) {
            return {
                ok: false,
                category: 'schema_invalid',
                detail: 'the action payload was a nested object, not a command string',
            };
        }
        if (trimmed.includes('command from') || trimmed.includes('your ') || trimmed.includes('your_') || trimmed.includes('](')) {
            return { ok: false, category: 'schema_invalid', detail: 'the action text was prose, not a command' };
        }
        const verb = trimmed.split(/\s+/)[0].toLowerCase();
        if (!allVerbs().has(verb)) {
            return { ok: false, category: 'unknown_verb', detail: `"${verb}" is not an action you know how to take` };
        }
        if (charName) {
            const player = worldState.data?.players?.[charName];
            const area = player?.current_area ? worldState.areas?.[player.current_area] : null;
            if (area?.exits) {
                const exitNames = Object.keys(area.exits).map((exitName: string) => exitName.toLowerCase());
                if (exitNames.includes(trimmed.toLowerCase())) return { ok: true, category: 'empty', detail: '' };
            }
        }
        return { ok: true, category: 'empty', detail: '' };
    }

    /** Check whether an action string uses a supported verb or matches a known exit name. */
    function isValidAction(action: unknown, charName?: string) {
        if (typeof action !== 'string' || action.trim() === '') return false;
        const trimmed = action.trim();
        if (trimmed.includes('command from') || trimmed.includes('your ') || trimmed.includes('your_') || trimmed.includes('](')) return false;
        const verb = trimmed.split(/\s+/)[0].toLowerCase();
        if (allVerbs().has(verb)) return true;
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
    function normalizeStructuredAction(p: StructuredAction | null | undefined) {
        if (!p) return '';
        // Schema recovery: some models nest the action as an object
        // {"action": {"action":"take","item":"lighter"}} instead of a string.
        // Unwrap one level so the verb/item/target are recovered instead of
        // becoming "[object Object]".
        let src: Record<string, unknown> = p as Record<string, unknown>;
        if (p && typeof p.action === 'object' && p.action !== null) {
            const nested = p.action as Record<string, unknown>;
            if (typeof nested.action === 'string') {
                src = { ...p, ...nested };
            } else {
                // A nested object with no verb in it is not recoverable. Return
                // an empty command so the caller reports a schema error rather
                // than stringifying the object into the world.
                return '';
            }
        }
        const verb = String(src.action || '').trim();
        if (!verb) return '';
        const item = String(src.item || '').trim();
        const target = String(src.target || '').trim();
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
            case 'use_on':
            case 'write':
            case 'inscribe': {
                // task-433: a text payload becomes a quoted inscription
                // ("use ink pen on \"parchment\" \"hello\""), which is the only
                // form the command parser carries as `params`.
                const text = String(src.text || '').trim();
                if (item && target && text) {
                    const t = target.replace(/"/g, "'");
                    const x = text.replace(/"/g, "'");
                    return `use ${item} on "${t}" "${x}"`;
                }
                // task-196: amount for quantity ("use 2 eggs on pan").
                const amount = parseInt(String(src.amount ?? ''), 10);
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
                const where = String(src.where || '').trim();
                return where ? `attack ${obj} on ${where}` : (obj ? `attack ${obj}` : verb);
            }
            case 'kiss': case 'caress': case 'lick': case 'suck':
            case 'bite': case 'pinch': case 'blow': case 'tickle': {
                // task-211: intimacy verbs carry body part + intensity.
                // Schema: {action:"kiss", target:"lydia", where:"neck", intensity:"light|normal|firm"}
                if (!matureEnabled()) return 'look';
                if (!obj) return verb;
                const where = String(src.where || '').trim();
                const intensity = String(src.intensity || 'normal').trim().toLowerCase();
                const adv = INTENSITY_ADVERBS[intensity] || '';
                const parts = [];
                if (adv) parts.push(adv);
                parts.push(verb, obj);
                if (where) parts.push('on', where);
                return parts.join(' ');
            }
            case 'grab': return obj ? `grab ${obj}` : verb;
            // task-610: person-directed verbs the scene menu now drafts. Without
            // these cases the target was silently dropped (bare "wake"/"release").
            case 'wake': return obj ? `wake ${obj}` : verb;
            case 'release': return obj ? `release ${obj}` : verb;
            case 'fear': case 'interest': return obj ? `${verb} ${obj}` : verb;
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
                const when = String(src.when || src.trigger_type || 'on_use').trim();
                const effect = String(src.effect || src.effect_type || 'message').trim();
                const extra = src.effect_params && Object.keys(src.effect_params).length
                    ? ' ' + JSON.stringify(src.effect_params)
                    : '';
                return item ? `bind ${item} ${when}:${effect}${extra}` : verb;
            }
            default: return verb;
        }
    }

    /**
     * The text a character is told when their command was refused.
     *
     * This is POLICY, and it lives next to the classifier that produces the
     * category so the two cannot drift. The wording matters: a malformed
     * command is an ENGINE-side refusal, and the old blanket "You try to X,
     * but you can't do that" made characters invent supernatural barriers to
     * explain a malformed JSON payload. The character is told what actually
     * happened - the command never reached the world.
     *
     * A well-formed command the WORLD refuses (a locked door) is not here:
     * that comes back from the backend as an action result.
     */
    function rejectionText(category: string, rejectedAction: string): string {
        if (category === 'schema_invalid') {
            return 'Your command was malformed, so it never reached the world. Nothing happened.';
        }
        if (category === 'empty') {
            return 'You did not act.';
        }
        return `You tried to ${rejectedAction}, but that is not something you know how to do. Nothing happened.`;
    }

    /** Extract speech text + volume from a parsed response object. */
    function extractSpeechVolume(p: StructuredAction | null | undefined): { speech: unknown; volume: string } {
        if (!p) return { speech: null, volume: 'say' };
        let speech: unknown = null;
        let volume = 'say';
        const normVol = (v: unknown) => {
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
    function volVerb(volume: string): string {
        return VOL_VERBS[volume || 'say'] || 'says';
    }

    return {
        isValidAction,
        classifyAction,
        looksStringifiedObject,
        rejectionText,
        normalizeStructuredAction,
        extractSpeechVolume,
        volVerb
    };
})();

(window as unknown as { ActionNormalizer: typeof ActionNormalizerModule }).ActionNormalizer = ActionNormalizerModule;

const VOL_VERBS: Record<string, string> = { whisper: 'whispers', say: 'says', shout: 'shouts', scream: 'screams' };

// Declared below the first value statement on purpose: TypeScript drops a
// file's leading JSDoc block when the first statement is type-only, which would
// strip the `@module` header tools/js_module_index.py reads.
interface StructuredAction {
    action?: unknown;
    item?: unknown;
    target?: unknown;
    relation?: unknown;
    text?: unknown;
    amount?: unknown;
    where?: unknown;
    intensity?: unknown;
    when?: unknown;
    trigger_type?: unknown;
    effect?: unknown;
    effect_type?: unknown;
    effect_params?: Record<string, unknown>;
    speech?: unknown;
    volume?: unknown;
    whisper?: unknown;
    say?: unknown;
    shout?: unknown;
    scream?: unknown;
    [key: string]: unknown;
}
