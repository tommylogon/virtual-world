"use strict";
/**
 * NL editor LLM budget — knobs, model-aware defaults, and clamping
 *
 * @module nl-editor/budget — LLM budget configuration for the natural-language editor
 * @contributes window.NlEditorBudget: pure budget helpers (defaults, clamp, model context windows)
 * @relates static/js/nl-editor/agent-loop — consumes the budget to size ContextWindowManager
 * @docs docs/virtualWorld/AI & Narration/Agent Engine.md
 */
(function () {
    'use strict';
    // Conservative context budget when the model window is unknown. A large
    // window must never be assumed: a local 8k model would overflow.
    const CONSERVATIVE_MAX_TOKENS = 6000;
    // First match wins, so specific names precede family names. Substring ->
    // context window in tokens. Unknown models fall through to null.
    const MODEL_CONTEXT_LENGTHS = [
        ['gpt-4.1', 1_000_000],
        ['gpt-4o', 128_000],
        ['o3', 200_000],
        ['o1', 200_000],
        ['claude', 200_000],
        ['gemini', 1_000_000],
        ['deepseek', 64_000],
        ['mixtral', 32_768],
        ['mistral', 32_768],
        ['llama-3.3', 128_000],
        ['llama3-70b-8192', 8_192],
        ['llama3-8b-8192', 8_192],
        ['gemma2', 8_192],
        ['qwen', 32_768],
        ['llama', 8_192]
    ];
    // Keys that persist the knobs, in the order the UI shows them.
    const BUDGET_KEYS = [
        'nl_max_iterations',
        'nl_max_tokens',
        'nl_max_messages',
        'nl_recent_turns',
        'nl_max_critical'
    ];
    /** Context window for a model name, or null when it is not known. */
    function contextLengthFor(model) {
        if (!model)
            return null;
        const m = String(model).toLowerCase();
        for (const [key, window] of MODEL_CONTEXT_LENGTHS) {
            if (m.indexOf(key) !== -1)
                return window;
        }
        return null;
    }
    /** The token budget to use for a model when nothing is saved. */
    function defaultMaxTokens(model) {
        const window = contextLengthFor(model);
        if (!window)
            return CONSERVATIVE_MAX_TOKENS;
        // Half the window, capped, so the reply and tool calls have room.
        return Math.min(60000, Math.floor(window / 2));
    }
    /** Defaults reproduce today's behaviour except maxTokens, which is model-aware. */
    function defaultBudget(model) {
        return {
            maxIterations: 100,
            maxTokens: defaultMaxTokens(model),
            maxMessages: 30,
            recentTurnCount: 8,
            maxCriticalMessages: 10
        };
    }
    /**
     * Integer clamp: missing/blank/garbage -> fallback, then bound to [lo, hi].
     * `Number('')` is 0, not NaN, so blank is checked before coercion or an
     * empty input would clamp to the floor instead of taking the default.
     */
    function _int(value, lo, hi, fallback) {
        if (value === undefined || value === null || value === '')
            return fallback;
        const n = Math.floor(Number(value));
        if (!isFinite(n))
            return fallback;
        if (n < lo)
            return lo;
        if (n > hi)
            return hi;
        return n;
    }
    /**
     * Clamp a (possibly partial, possibly absurd) persisted budget to sane
     * bounds. maxTokens is capped to the model window when it is known.
     */
    function clampBudget(raw, model) {
        const d = defaultBudget(model);
        const window = contextLengthFor(model);
        const ceil = window || 1_000_000;
        const r = raw || {};
        return {
            maxIterations: _int(r.maxIterations, 1, 1000, d.maxIterations),
            maxTokens: _int(r.maxTokens, 256, ceil, d.maxTokens),
            maxMessages: _int(r.maxMessages, 1, 1000, d.maxMessages),
            recentTurnCount: _int(r.recentTurnCount, 1, 100, d.recentTurnCount),
            maxCriticalMessages: _int(r.maxCriticalMessages, 1, 100, d.maxCriticalMessages)
        };
    }
    const api = {
        CONSERVATIVE_MAX_TOKENS,
        BUDGET_KEYS,
        MODEL_CONTEXT_LENGTHS,
        contextLengthFor,
        defaultMaxTokens,
        defaultBudget,
        clampBudget
    };
    window.NlEditorBudget = api;
})();
