/**
 * response-parser.js — LLM response parsing for agent turns
 *
 * Extracts structured fields (inner_monologue, action, speech, emote, memory)
 * from raw LLM text responses. Uses repairJSON() from shared/json-utils.js
 * to handle common LLM formatting failures before parsing.
 *
 * Load AFTER shared/json-utils.js, BEFORE agent-engine.js.
 */

window.ResponseParser = (() => {
    'use strict';

    /** Extract subjective memory: {text, importance, tags} or plain string. */
    function extractMemory(m) {
        if (!m) return null;
        if (typeof m === 'string') return { text: m.trim(), importance: 5, tags: [] };
        if (typeof m === 'object') {
            const text = (m.text || '').trim();
            if (!text) return null;
            const imp = parseInt(m.importance, 10);
            const tags = Array.isArray(m.tags) ? m.tags.map(t => String(t).trim().toLowerCase()).filter(Boolean).slice(0, 5) : [];
            return { text, importance: Number.isNaN(imp) ? 5 : Math.max(1, Math.min(10, imp)), tags };
        }
        return null;
    }

    /** Normalize raw model output before JSON repair. */
    function normalizeRawResponse(raw) {
        return typeof extractAssistantText === 'function'
            ? extractAssistantText(raw)
            : String(raw || '').trim();
    }

    /** Parse an observation response — returns inner_monologue string or null on failure. */
    function parseObservation(r) {
        if (!r) return '';
        try {
            const c = repairJSON(normalizeRawResponse(r));
            const p = JSON.parse(c);
            return p.inner_monologue || '';
        } catch (e) {
            return null;
        }
    }

    /** Normalize an optional LLM-declared feeling: {label, intensity 1-10}. */
    function extractEmotion(raw) {
        if (!raw || typeof raw !== 'object') return null;
        const label = String(raw.label || '').trim().toLowerCase();
        const intensity = parseFloat(raw.intensity);
        if (!label || !Number.isFinite(intensity)) return null;
        return { label, intensity: Math.max(1, Math.min(10, intensity)) };
    }

    /** Parse a reaction/decision response — returns full structured object with parseError on failure. */
    function parseReaction(r) {
        if (!r) return { inner: '', speech: null, speechVolume: 'say', action: '', emote: null, memory: null, emotion: null, parseError: null };
        try {
            const c = repairJSON(normalizeRawResponse(r));
            const p = JSON.parse(c);
            const { speech, volume } = ActionNormalizer.extractSpeechVolume(p);
            return {
                inner: p.inner_monologue || '',
                speech,
                speechVolume: volume,
                action: ActionNormalizer.normalizeStructuredAction(p),
                emote: p.emote || null,
                memory: extractMemory(p.memory),
                emotion: extractEmotion(p.emotion),
                parseError: null
            };
        } catch (e) {
            return {
                inner: '', speech: null, speechVolume: 'say', action: '', emote: null, memory: null, emotion: null,
                parseError: `Failed to parse LLM response as JSON: ${e.message}`
            };
        }
    }

    /** Parse a result-reaction response — same shape as parseReaction, no action field. */
    function parseResultReaction(r) {
        if (!r) return { inner: '', speech: null, speechVolume: 'say', emote: null, memory: null, emotion: null, parseError: null };
        try {
            const c = repairJSON(normalizeRawResponse(r));
            const p = JSON.parse(c);
            const { speech, volume } = ActionNormalizer.extractSpeechVolume(p);
            return {
                inner: p.inner_monologue || '',
                speech,
                speechVolume: volume,
                emote: p.emote || null,
                memory: extractMemory(p.memory),
                emotion: extractEmotion(p.emotion),
                parseError: null
            };
        } catch (e) {
            return {
                inner: '', speech: null, speechVolume: 'say', emote: null, memory: null, emotion: null,
                parseError: `Failed to parse LLM response as JSON: ${e.message}`
            };
        }
    }

    /** Parse a decision-with-speech response (legacy path). */
    function parseDecisionWithSpeech(r) {
        if (!r) return { finalAction: '', decisionSpeech: null, speechVolume: 'say', emote: null };
        try {
            const c = repairJSON(normalizeRawResponse(r));
            const p = JSON.parse(c);
            const { speech, volume } = ActionNormalizer.extractSpeechVolume(p);
            return {
                finalAction: (p.action || '').trim(),
                decisionSpeech: speech,
                speechVolume: volume,
                emote: p.emote || null
            };
        } catch (e) {
            return null;
        }
    }

    return {
        parseObservation,
        parseReaction,
        parseResultReaction,
        parseDecisionWithSpeech,
        extractMemory
    };
})();
