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

    /** The structured fields both parsers return. `action` only on parseReaction. */
    interface ParsedReaction {
        inner: string;
        speech: string | null;
        speechVolume: string;
        emote: string | null;
        memory: ExtractedMemory | null;
        emotion: { label: string; intensity: number; toward: string | null } | null;
        learnedNames: string[];
        parseError: string | null;
        action?: unknown;
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
                why: String(emo.why || '').trim().slice(0, 200),
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

    /** Normalize an optional LLM-declared feeling: {label, intensity 1-10, toward?}. */
    function extractEmotion(raw: unknown): { label: string; intensity: number; toward: string | null } | null {
        if (!raw || typeof raw !== 'object') return null;
        const rec = raw as Record<string, unknown>;
        const label = String(rec.label || '').trim().toLowerCase();
        const intensity = parseFloat(String(rec.intensity));
        if (!label || !Number.isFinite(intensity)) return null;
        const toward = String(rec.toward || '').trim();
        return { label, intensity: Math.max(1, Math.min(10, intensity)), toward: toward || null };
    }

    /** Normalize an optional list of names learned/confirmed this turn. */
    function extractLearnedNames(raw: unknown): string[] {
        if (!Array.isArray(raw)) return [];
        return raw.map((s: unknown) => String(s || '').trim()).filter(Boolean).slice(0, 5);
    }

    /** Parse a reaction/decision response — returns full structured object with parseError on failure. */
    function parseReaction(r: unknown): ParsedReaction {
        if (!r) return { inner: '', speech: null, speechVolume: 'say', action: '', emote: null, memory: null, emotion: null, learnedNames: [], parseError: null };
        try {
            const repair = (window as unknown as ResponseParserWindowSurface).repairJSON as (raw: string) => string;
            const c = repair(normalizeRawResponse(r));
            // N1: an easy repair is still a truncated response — surface it so
            // the stream says "salvaged" instead of silently dropping fields.
            const repaired = !!(window as unknown as ResponseParserWindowSurface).__repairStats?.repaired;
            if ((window as unknown as ResponseParserWindowSurface).__repairStats) (window as unknown as ResponseParserWindowSurface).__repairStats.repaired = false;
            const p = JSON.parse(c) as Record<string, unknown>;
            const { speech, volume } = ActionNormalizer.extractSpeechVolume(p);
            return {
                inner: (p.inner_monologue || '') as string,
                speech,
                speechVolume: volume,
                action: ActionNormalizer.normalizeStructuredAction(p),
                emote: (p.emote || null) as string | null,
                memory: extractMemory(p.memory),
                emotion: extractEmotion(p.emotion),
                learnedNames: extractLearnedNames(p.learned_names),
                parseError: repaired ? 'JSON repaired (truncated response) — fields after the break were lost' : null
            };
        } catch (e) {
            return {
                inner: '', speech: null, speechVolume: 'say', action: '', emote: null, memory: null, emotion: null, learnedNames: [],
                parseError: `Failed to parse LLM response as JSON: ${e instanceof Error ? e.message : String(e)}`
            };
        }
    }

    /** Parse a result-reaction response — same shape as parseReaction, no action field. */
    function parseResultReaction(r: unknown): ParsedReaction {
        if (!r) return { inner: '', speech: null, speechVolume: 'say', emote: null, memory: null, emotion: null, learnedNames: [], parseError: null };
        try {
            const repair = (window as unknown as ResponseParserWindowSurface).repairJSON as (raw: string) => string;
            const c = repair(normalizeRawResponse(r));
            const p = JSON.parse(c) as Record<string, unknown>;
            const { speech, volume } = ActionNormalizer.extractSpeechVolume(p);
            return {
                inner: (p.inner_monologue || '') as string,
                speech,
                speechVolume: volume,
                emote: (p.emote || null) as string | null,
                memory: extractMemory(p.memory),
                emotion: extractEmotion(p.emotion),
                learnedNames: extractLearnedNames(p.learned_names),
                parseError: null
            };
        } catch (e) {
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
