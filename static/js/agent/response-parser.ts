/**
 * response-parser.js  -  LLM response parsing for agent turns
 *
 * Extracts structured fields (inner_monologue, action, speech, emote, memory)
 * from raw LLM text responses. Uses repairJSON() from shared/json-utils.js
 * to handle common LLM formatting failures before parsing.
 *
 * Load AFTER shared/json-utils.js, BEFORE agent-engine.js.
 *
 * @module agent/response-parser  -  LLM response parsing
 * @contributes ResponseParser: extract inner_monologue/action/speech/emote/memory via repairJSON()
 * @powers LLM calls  -  turning messy model output into structured action fields
 * @relates depends on shared/json-utils.js; used by agent-engine
 * @docs docs/virtualWorld/AI & Narration/Agent Engine.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

interface ResponseParserWindowSurface {
    ResponseParser: unknown;
    __repairStats: { repaired?: boolean };
    // shared/json-utils.js (converted, so not yet in globals.d.ts) publishes
    // these as bare globals on a classic script. Read off `window` rather than
    // re-declared, so this file stays correct either way.
    repairJSON: (raw: string) => string;
    extractAssistantText: (raw: unknown) => string;
}

// Type declarations live below the first value statement on purpose: tsc drops
// a file's leading JSDoc when the first statement is type-only, which would
// strip the `@module` header from the emitted .js. They stay inside the IIFE
// body because this is a classic script (no imports), so a top-level `declare`
// would leak a global that collides with the owning modules.

(window as unknown as ResponseParserWindowSurface).ResponseParser = (() => {
    'use strict';

    /** The structured memory block a model may declare on a turn. */
    interface ExtractedMemory {
        text: string;
        importance: number;
        tags: string[];
        emotions?: { who: string; why: string; data: unknown } | null;
    }

    /** Normalized affect impulse declared on a turn. */
    interface ExtractedEmotion {
        label: string;
        intensity: number;
        toward: string | null;
    }

    /** The structured fields both parsers return. `action` only on parseReaction. */
    interface ParsedReaction {
        inner: string;
        speech: string | null;
        speechVolume: string;
        target?: string | null;
        emote: string | null;
        memory: ExtractedMemory | null;
        emotion: ExtractedEmotion | ExtractedEmotion[] | null;
        learnedNames: string[];
        parseError: string | null;
        action?: unknown;
    }

    interface ParsedCommunication {
        inner: string;
        action: 'read_chat' | 'send_chat' | 'start_dm' | 'start_group' | 'think' | 'edit_message' | 'delete_message';
        channelId: string | null;
        recipient: string | null;
        groupName: string | null;
        recipients: string[];
        text: string;
        readMode: 'latest' | 'all' | 'range';
        n: number;
        fromId: number | null;
        toId: number | null;
        messageId: number | null;
        memory: ExtractedMemory | null;
        parseError: string | null;
    }

    /** Extract subjective memory: {text, importance, tags} or plain string. */
    function extractMemory(m: unknown): ExtractedMemory | null {
        if (!m) return null;
        if (typeof m === 'string') return { text: m.trim(), importance: 5, tags: [] };
        if (typeof m === 'object') {
            const rec = m as Record<string, unknown>;
            const text = String(rec.text || '').trim();
            if (!text) return null;
            const imp = parseInt(String(rec.importance), 10);
            const tags = Array.isArray(rec.tags) ? rec.tags.map((t: unknown) => String(t).trim().toLowerCase()).filter(Boolean).slice(0, 5) : [];
            // task-350: a memory may carry a structured feelings block toward a
            // person {who, why, data:{dim:delta}} -> forwarded to the backend
            // which resolves who, canonicalizes it, and folds it into the
            // derived relationship profile.
            const emo = rec.emotions && typeof rec.emotions === 'object' ? rec.emotions as Record<string, unknown> : null;
            const emotions = emo ? {
                who: String(emo.who || '').trim(),
                why: String(emo.why || '').trim(),
                data: (emo.data && typeof emo.data === 'object') ? emo.data : {}
            } : null;
            return { text, importance: Number.isNaN(imp) ? 5 : Math.max(1, Math.min(10, imp)), tags, emotions };
        }
        return null;
    }

    /** Normalize raw model output before JSON repair. */
    function normalizeRawResponse(raw: unknown): string {
        const extract = (window as unknown as ResponseParserWindowSurface).extractAssistantText;
        return typeof extract === 'function'
            ? extract(raw)
            : String(raw || '').trim();
    }

    /** Normalize a single LLM-declared feeling: {label, intensity 1-10, toward?}. */
    function extractSingleEmotion(raw: unknown): ExtractedEmotion | null {
        if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
        const rec = raw as Record<string, unknown>;
        const label = String(rec.label || '').trim().toLowerCase();
        if (!label) return null;
        const rawInt = rec.intensity;
        const intensity = (rawInt === null || rawInt === undefined || rawInt === '')
            ? 5
            : parseFloat(String(rawInt));
        if (!Number.isFinite(intensity)) return null;
        const toward = typeof rec.toward === 'string' ? rec.toward.trim() : '';
        return { label, intensity: Math.max(1, Math.min(10, intensity)), toward: toward || null };
    }

    /** Normalize an optional LLM-declared feeling (single object or array of impulses). */
    function extractEmotion(raw: unknown): ExtractedEmotion | ExtractedEmotion[] | null {
        if (!raw) return null;
        if (Array.isArray(raw)) {
            const list = raw.map(extractSingleEmotion).filter((e): e is ExtractedEmotion => e !== null);
            return list.length ? list : null;
        }
        return extractSingleEmotion(raw);
    }

    /** Normalize an optional list of names learned/confirmed this turn. */
    function extractLearnedNames(raw: unknown): string[] {
        if (!Array.isArray(raw)) return [];
        return raw.map((s: unknown) => String(s || '').trim()).filter(Boolean).slice(0, 5);
    }

    /** Extract an optional speech target (person addressed or whispered to, bug-581). */
    function extractSpeechTarget(p: Record<string, unknown>): string | null {
        if (!p || typeof p !== 'object') return null;
        const cleanRef = (v: unknown): string => {
            if (typeof v !== 'string') return '';
            const t = v.trim();
            return (t === '...' || /^<[^>]+>$/.test(t) || t.toLowerCase() === 'none' || t.toLowerCase() === 'null') ? '' : t;
        };
        const explicitTarget = cleanRef(p.speech_target);
        if (explicitTarget) return explicitTarget;
        const speechStr = cleanRef(p.speech) || cleanRef(p.whisper);
        if (!speechStr) return null;
        const rawTarget = cleanRef(p.target);
        if (!rawTarget) return null;
        const rawItem = cleanRef(p.item);
        if (rawItem) {
            const tLow = rawTarget.toLowerCase();
            const iLow = rawItem.toLowerCase();
            if (tLow === iLow || iLow.includes(tLow) || tLow.includes(iLow)) return null;
            const tToks = tLow.split(/[^a-z0-9]+/).filter(w => w.length >= 3);
            if (tToks.some(w => iLow.includes(w))) return null;
        }
        const rawAction = typeof p.action === 'string' ? p.action.trim().toLowerCase() : '';
        const isWhisper = String(p.volume || '').trim().toLowerCase() === 'whisper' ||
            Boolean(cleanRef(p.whisper));
        if (!rawAction || rawAction === 'wait' || rawAction === 'none' || Boolean(rawItem) || isWhisper) {
            return rawTarget;
        }
        return null;
    }

    /** Clean speech or emote string, rejecting schema placeholders like "..." or "<tool>". */
    function cleanProseField(val: unknown): string | null {
        if (typeof val !== 'string') return null;
        const t = val.trim();
        if (!t || t === '...' || /^<[^>]+>$/.test(t)) return null;
        return t;
    }

    /**
     * Detect a malformed `action` field BEFORE it can become a command.
     *
     * Two shapes reach us from real models:
     *   - `{"action": {"action":"take","item":"x"}}` - the action nested one
     *     level deep. Recoverable: the normalizer unwraps it.
     *   - `{"action": {"item":"x"}}` or `{"action": "[object Object]"}` - no
     *     action to recover. NOT recoverable, and it must never be executed.
     *
     * The second case returns a schema error so the caller's one-shot retry
     * fires, instead of the malformed payload reaching the world as a command.
     */
    function detectActionSchemaError(p: Record<string, unknown>): string | null {
        const raw = p.action;
        if (raw === undefined || raw === null) return null;
        if (typeof raw === 'object') {
            const nested = raw as Record<string, unknown>;
            if (typeof nested.action === 'string' && nested.action.trim()) return null;
            return 'schema_invalid: "action" must be a action string, but it was an object with no "action" field';
        }
        if (typeof raw === 'string') {
            if (ActionNormalizer.looksStringifiedObject(raw)) {
                return 'schema_invalid: "action" was a stringified object instead of a action';
            }
            return null;
        }
        return 'schema_invalid: "action" must be a action string';
    }

    /** Parse a reaction/decision response  -  returns full structured object with parseError on failure. */
    function parseReaction(r: unknown): ParsedReaction {
        if (!r) return { inner: '', speech: null, speechVolume: 'say', target: null, action: '', emote: null, memory: null, emotion: null, learnedNames: [], parseError: null };
        try {
            const repair = (window as unknown as ResponseParserWindowSurface).repairJSON as (raw: string) => string;
            const c = repair(normalizeRawResponse(r));
            // N1: an easy repair is still a truncated response  -  surface it so
            // the stream says "salvaged" instead of silently dropping fields.
            const repaired = !!(window as unknown as ResponseParserWindowSurface).__repairStats?.repaired;
            if ((window as unknown as ResponseParserWindowSurface).__repairStats) (window as unknown as ResponseParserWindowSurface).__repairStats.repaired = false;
            const p = JSON.parse(c) as Record<string, unknown>;
            const { speech, volume } = ActionNormalizer.extractSpeechVolume(p);
            const schemaError = detectActionSchemaError(p);
            return {
                inner: cleanProseField(p.inner_monologue) || '',
                speech: cleanProseField(speech),
                speechVolume: volume,
                target: extractSpeechTarget(p),
                action: ActionNormalizer.normalizeStructuredAction(p),
                emote: cleanProseField(p.emote),
                memory: extractMemory(p.memory),
                emotion: extractEmotion(p.emotion || (typeof p.emote === 'object' ? p.emote : null)),
                learnedNames: extractLearnedNames(p.learned_names),
                parseError: schemaError
                    || (repaired ? 'JSON repaired (truncated response)  -  fields after the break were lost' : null)
            };
        } catch (e) {
            return {
                inner: '', speech: null, speechVolume: 'say', target: null, action: '', emote: null, memory: null, emotion: null, learnedNames: [],
                parseError: `Failed to parse LLM response as JSON: ${e instanceof Error ? e.message : String(e)}`
            };
        }
    }

    /** Parse a result-reaction response  -  same shape as parseReaction, no action field. */
    function parseResultReaction(r: unknown): ParsedReaction {
        if (!r) return { inner: '', speech: null, speechVolume: 'say', target: null, emote: null, memory: null, emotion: null, learnedNames: [], parseError: null };
        try {
            const repair = (window as unknown as ResponseParserWindowSurface).repairJSON as (raw: string) => string;
            const c = repair(normalizeRawResponse(r));
            const p = JSON.parse(c) as Record<string, unknown>;
            const { speech, volume } = ActionNormalizer.extractSpeechVolume(p);
            return {
                inner: cleanProseField(p.inner_monologue) || '',
                speech: cleanProseField(speech),
                speechVolume: volume,
                target: extractSpeechTarget(p),
                emote: cleanProseField(p.emote),
                memory: extractMemory(p.memory),
                emotion: extractEmotion(p.emotion || (typeof p.emote === 'object' ? p.emote : null)),
                learnedNames: extractLearnedNames(p.learned_names),
                parseError: null
            };
        } catch (e) {
            return {
                inner: '', speech: null, speechVolume: 'say', target: null, emote: null, memory: null, emotion: null, learnedNames: [],
                parseError: `Failed to parse LLM response as JSON: ${e instanceof Error ? e.message : String(e)}`
            };
        }
    }

    /** Parse the communication adapter using the agent's JSON repair and memory normalization. */
    function parseCommunication(r: unknown): ParsedCommunication {
        const empty: ParsedCommunication = {
            inner: '', action: 'think', channelId: null, recipient: null, text: '',
            groupName: null, recipients: [],
            readMode: 'all', n: 5, fromId: null, toId: null, messageId: null, memory: null, parseError: null,
        };
        if (!r) return empty;
        try {
            const repair = (window as unknown as ResponseParserWindowSurface).repairJSON;
            const parsed = JSON.parse(repair(normalizeRawResponse(r))) as Record<string, unknown>;
            const raw = parsed.communication && typeof parsed.communication === 'object'
                ? parsed.communication as Record<string, unknown>
                : {};
            const allowedActions = ['read_chat', 'send_chat', 'start_dm', 'start_group', 'think', 'edit_message', 'delete_message'];
            const allowedModes = ['latest', 'all', 'range'];
            const integerOrNull = (value: unknown): number | null => {
                const number = Number(value);
                return Number.isInteger(number) && number > 0 ? number : null;
            };
            const count = Number(raw.n);
            return {
                inner: String(parsed.inner_monologue || ''),
                action: allowedActions.includes(String(raw.action))
                    ? String(raw.action) as ParsedCommunication['action'] : 'think',
                channelId: String(raw.channel_id || '').trim() || null,
                recipient: String(raw.recipient || '').trim() || null,
                groupName: String(raw.group_name || '').trim() || null,
                recipients: Array.isArray(raw.recipients)
                    ? [...new Set(raw.recipients.map((name: unknown) => String(name || '').trim()).filter(Boolean))]
                    : [],
                text: String(raw.text || '').trim(),
                readMode: allowedModes.includes(String(raw.read_mode))
                    ? String(raw.read_mode) as ParsedCommunication['readMode'] : 'all',
                n: Number.isFinite(count) ? Math.max(1, Math.min(50, Math.trunc(count))) : 5,
                fromId: integerOrNull(raw.from_id),
                toId: integerOrNull(raw.to_id),
                messageId: integerOrNull(raw.message_id || raw.id),
                memory: extractMemory(parsed.memory),
                parseError: null,
            };
        } catch (error) {
            return {
                ...empty,
                parseError: `Failed to parse LLM response as JSON: ${error instanceof Error ? error.message : String(error)}`,
            };
        }
    }

    return {
        parseReaction,
        parseResultReaction,
        parseCommunication,
        extractMemory,
        extractEmotion
    };
})();
