"use strict";
/**
 * response-parser.js — LLM response parsing for agent turns
 *
 * Extracts structured fields (inner_monologue, action, speech, emote, memory)
 * from raw LLM text responses. Uses repairJSON() from shared/json-utils.js
 * to handle common LLM formatting failures before parsing.
 *
 * Load AFTER shared/json-utils.js, BEFORE agent-engine.js.
 *
 * @module agent/response-parser — LLM response parsing
 * @contributes ResponseParser: extract inner_monologue/action/speech/emote/memory via repairJSON()
 * @powers LLM calls — turning messy model output into structured action fields
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
                why: String(emo.why || '').trim().slice(0, 200),
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
    /** Parse a reaction/decision response — returns full structured object with parseError on failure. */
    function parseReaction(r) {
        if (!r)
            return { inner: '', speech: null, speechVolume: 'say', action: '', emote: null, memory: null, emotion: null, learnedNames: [], parseError: null };
        try {
            const repair = window.repairJSON;
            const c = repair(normalizeRawResponse(r));
            // N1: an easy repair is still a truncated response — surface it so
            // the stream says "salvaged" instead of silently dropping fields.
            const repaired = !!window.__repairStats?.repaired;
            if (window.__repairStats)
                window.__repairStats.repaired = false;
            const p = JSON.parse(c);
            const { speech, volume } = ActionNormalizer.extractSpeechVolume(p);
            return {
                inner: (p.inner_monologue || ''),
                speech,
                speechVolume: volume,
                action: ActionNormalizer.normalizeStructuredAction(p),
                emote: (p.emote || null),
                memory: extractMemory(p.memory),
                emotion: extractEmotion(p.emotion),
                learnedNames: extractLearnedNames(p.learned_names),
                parseError: repaired ? 'JSON repaired (truncated response) — fields after the break were lost' : null
            };
        }
        catch (e) {
            return {
                inner: '', speech: null, speechVolume: 'say', action: '', emote: null, memory: null, emotion: null, learnedNames: [],
                parseError: `Failed to parse LLM response as JSON: ${e instanceof Error ? e.message : String(e)}`
            };
        }
    }
    /** Parse a result-reaction response — same shape as parseReaction, no action field. */
    function parseResultReaction(r) {
        if (!r)
            return { inner: '', speech: null, speechVolume: 'say', emote: null, memory: null, emotion: null, learnedNames: [], parseError: null };
        try {
            const repair = window.repairJSON;
            const c = repair(normalizeRawResponse(r));
            const p = JSON.parse(c);
            const { speech, volume } = ActionNormalizer.extractSpeechVolume(p);
            return {
                inner: (p.inner_monologue || ''),
                speech,
                speechVolume: volume,
                emote: (p.emote || null),
                memory: extractMemory(p.memory),
                emotion: extractEmotion(p.emotion),
                learnedNames: extractLearnedNames(p.learned_names),
                parseError: null
            };
        }
        catch (e) {
            return {
                inner: '', speech: null, speechVolume: 'say', emote: null, memory: null, emotion: null, learnedNames: [],
                parseError: `Failed to parse LLM response as JSON: ${e instanceof Error ? e.message : String(e)}`
            };
        }
    }
    return {
        parseReaction,
        parseResultReaction,
        extractMemory
    };
})();
