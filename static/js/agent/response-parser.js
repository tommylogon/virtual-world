"use strict";
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
// Type declarations live below the first value statement on purpose: tsc drops
// a file's leading JSDoc when the first statement is type-only, which would
// strip the `@module` header from the emitted .js. They stay inside the IIFE
// body because this is a classic script (no imports), so a top-level `declare`
// would leak a global that collides with the owning modules.
window.ResponseParser = (() => {
    'use strict';
    /** Extract subjective memory: {text, importance, tags} or plain string. */
    function extractMemory(m) {
        if (!m)
            return null;
        if (typeof m === 'string')
            return { text: m.trim(), importance: 5, tags: [] };
        if (typeof m === 'object') {
            const rec = m;
            const text = String(rec.text || '').trim();
            if (!text)
                return null;
            const imp = parseInt(String(rec.importance), 10);
            const tags = Array.isArray(rec.tags) ? rec.tags.map((t) => String(t).trim().toLowerCase()).filter(Boolean).slice(0, 5) : [];
            // task-350: a memory may carry a structured feelings block toward a
            // person {who, why, data:{dim:delta}} -> forwarded to the backend
            // which resolves who, canonicalizes it, and folds it into the
            // derived relationship profile.
            const emo = rec.emotions && typeof rec.emotions === 'object' ? rec.emotions : null;
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
    function normalizeRawResponse(raw) {
        const extract = window.extractAssistantText;
        return typeof extract === 'function'
            ? extract(raw)
            : String(raw || '').trim();
    }
    /** Normalize an optional LLM-declared feeling: {label, intensity 1-10, toward?}. */
    function extractEmotion(raw) {
        if (!raw || typeof raw !== 'object')
            return null;
        const rec = raw;
        const label = String(rec.label || '').trim().toLowerCase();
        const intensity = parseFloat(String(rec.intensity));
        if (!label || !Number.isFinite(intensity))
            return null;
        const toward = String(rec.toward || '').trim();
        return { label, intensity: Math.max(1, Math.min(10, intensity)), toward: toward || null };
    }
    /** Normalize an optional list of names learned/confirmed this turn. */
    function extractLearnedNames(raw) {
        if (!Array.isArray(raw))
            return [];
        return raw.map((s) => String(s || '').trim()).filter(Boolean).slice(0, 5);
    }
    /** Extract an optional speech target (person addressed or whispered to, bug-581). */
    function extractSpeechTarget(p) {
        if (!p || typeof p !== 'object')
            return null;
        const cleanRef = (v) => {
            if (typeof v !== 'string')
                return '';
            const t = v.trim();
            return (t === '...' || /^<[^>]+>$/.test(t) || t.toLowerCase() === 'none' || t.toLowerCase() === 'null') ? '' : t;
        };
        const explicitTarget = cleanRef(p.speech_target);
        if (explicitTarget)
            return explicitTarget;
        const speechStr = cleanRef(p.speech) || cleanRef(p.whisper);
        if (!speechStr)
            return null;
        const rawTarget = cleanRef(p.target);
        if (!rawTarget)
            return null;
        const rawItem = cleanRef(p.item);
        if (rawItem) {
            const tLow = rawTarget.toLowerCase();
            const iLow = rawItem.toLowerCase();
            if (tLow === iLow || iLow.includes(tLow) || tLow.includes(iLow))
                return null;
            const tToks = tLow.split(/[^a-z0-9]+/).filter(w => w.length >= 3);
            if (tToks.some(w => iLow.includes(w)))
                return null;
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
    function cleanProseField(val) {
        if (typeof val !== 'string')
            return null;
        const t = val.trim();
        if (!t || t === '...' || /^<[^>]+>$/.test(t))
            return null;
        return t;
    }
    /**
     * Detect a malformed `action` field BEFORE it can become a command.
     *
     * Two shapes reach us from real models:
     *   - `{"action": {"action":"take","item":"x"}}` - the action nested one
     *     level deep. Recoverable: the normalizer unwraps it.
     *   - `{"action": {"item":"x"}}` or `{"action": "[object Object]"}` - no
     *     verb to recover. NOT recoverable, and it must never be executed.
     *
     * The second case returns a schema error so the caller's one-shot retry
     * fires, instead of the malformed payload reaching the world as a command.
     */
    function detectActionSchemaError(p) {
        const raw = p.action;
        if (raw === undefined || raw === null)
            return null;
        if (typeof raw === 'object') {
            const nested = raw;
            if (typeof nested.action === 'string' && nested.action.trim())
                return null;
            return 'schema_invalid: "action" must be a verb string, but it was an object with no "action" field';
        }
        if (typeof raw === 'string') {
            if (ActionNormalizer.looksStringifiedObject(raw)) {
                return 'schema_invalid: "action" was a stringified object instead of a verb';
            }
            return null;
        }
        return 'schema_invalid: "action" must be a verb string';
    }
    /** Parse a reaction/decision response  -  returns full structured object with parseError on failure. */
    function parseReaction(r) {
        if (!r)
            return { inner: '', speech: null, speechVolume: 'say', target: null, action: '', emote: null, memory: null, emotion: null, learnedNames: [], parseError: null };
        try {
            const repair = window.repairJSON;
            const c = repair(normalizeRawResponse(r));
            // N1: an easy repair is still a truncated response  -  surface it so
            // the stream says "salvaged" instead of silently dropping fields.
            const repaired = !!window.__repairStats?.repaired;
            if (window.__repairStats)
                window.__repairStats.repaired = false;
            const p = JSON.parse(c);
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
        }
        catch (e) {
            return {
                inner: '', speech: null, speechVolume: 'say', target: null, action: '', emote: null, memory: null, emotion: null, learnedNames: [],
                parseError: `Failed to parse LLM response as JSON: ${e instanceof Error ? e.message : String(e)}`
            };
        }
    }
    /** Parse a result-reaction response  -  same shape as parseReaction, no action field. */
    function parseResultReaction(r) {
        if (!r)
            return { inner: '', speech: null, speechVolume: 'say', target: null, emote: null, memory: null, emotion: null, learnedNames: [], parseError: null };
        try {
            const repair = window.repairJSON;
            const c = repair(normalizeRawResponse(r));
            const p = JSON.parse(c);
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
        }
        catch (e) {
            return {
                inner: '', speech: null, speechVolume: 'say', target: null, emote: null, memory: null, emotion: null, learnedNames: [],
                parseError: `Failed to parse LLM response as JSON: ${e instanceof Error ? e.message : String(e)}`
            };
        }
    }
    /** Parse the communication adapter using the agent's JSON repair and memory normalization. */
    function parseCommunication(r) {
        const empty = {
            inner: '', action: 'think', channelId: null, recipient: null, text: '',
            groupName: null, recipients: [],
            readMode: 'all', n: 5, fromId: null, toId: null, messageId: null, memory: null, parseError: null,
        };
        if (!r)
            return empty;
        try {
            const repair = window.repairJSON;
            const parsed = JSON.parse(repair(normalizeRawResponse(r)));
            const raw = parsed.communication && typeof parsed.communication === 'object'
                ? parsed.communication
                : {};
            const allowedActions = ['read_chat', 'send_chat', 'start_dm', 'start_group', 'think', 'edit_message', 'delete_message'];
            const allowedModes = ['latest', 'all', 'range'];
            const integerOrNull = (value) => {
                const number = Number(value);
                return Number.isInteger(number) && number > 0 ? number : null;
            };
            const count = Number(raw.n);
            return {
                inner: String(parsed.inner_monologue || ''),
                action: allowedActions.includes(String(raw.action))
                    ? String(raw.action) : 'think',
                channelId: String(raw.channel_id || '').trim() || null,
                recipient: String(raw.recipient || '').trim() || null,
                groupName: String(raw.group_name || '').trim() || null,
                recipients: Array.isArray(raw.recipients)
                    ? [...new Set(raw.recipients.map((name) => String(name || '').trim()).filter(Boolean))]
                    : [],
                text: String(raw.text || '').trim(),
                readMode: allowedModes.includes(String(raw.read_mode))
                    ? String(raw.read_mode) : 'all',
                n: Number.isFinite(count) ? Math.max(1, Math.min(50, Math.trunc(count))) : 5,
                fromId: integerOrNull(raw.from_id),
                toId: integerOrNull(raw.to_id),
                messageId: integerOrNull(raw.message_id || raw.id),
                memory: extractMemory(parsed.memory),
                parseError: null,
            };
        }
        catch (error) {
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
        extractMemory
    };
})();
