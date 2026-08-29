/**
 * embedding-client.js — Semantic memory embeddings (task-91)
 *
 * Thin OpenAI-compatible /embeddings caller. Config lives in browser config
 * (embedEnabled/embedUrl/embedModel/embedDims/embedApiKey); API keys never go
 * to the backend — the backend only ever receives finished vectors for storage
 * and cosine search.
 *
 * Exposed as `window.EmbeddingClient`. Every call degrades gracefully: any
 * failure returns null and callers fall back to keyword-only recall.
 */
(() => {
    'use strict';

    // Bounded in-memory dedupe: prompt/render pipelines embed the same text
    // repeatedly (e.g. the Agent Lens rebuilds on every state poll), so cache
    // identical inputs here instead of hammering the local model server.
    const _cache = new Map();
    const _CACHE_MAX = 512;

    function configured() {
        return !!(config?.embedEnabled && config?.embedUrl && config?.embedModel);
    }

    function headers() {
        const h = { 'Content-Type': 'application/json' };
        if (config.embedApiKey) h['Authorization'] = 'Bearer ' + config.embedApiKey;
        return h;
    }

    /**
     * Embed one string or an array of strings.
     * @param {string|string[]} input
     * @returns {Promise<number[]|number[][]|null>} vector(s), null on failure/disabled
     */
    async function embed(input) {
        if (!configured() || !input || (Array.isArray(input) && input.length === 0)) return null;
        const single = typeof input === 'string';
        const cacheKey = JSON.stringify(input);
        if (_cache.has(cacheKey)) return _cache.get(cacheKey);
        try {
            const url = config.embedUrl.replace(/\/+$/, '') + '/embeddings';
            const resp = await fetch(url, {
                method: 'POST',
                headers: headers(),
                body: JSON.stringify({ model: config.embedModel, input }),
                signal: AbortSignal.timeout(15000)
            });
            if (!resp.ok) return null;
            const data = await resp.json();
            const rows = (data.data || []).map(d => d.embedding).filter(Array.isArray);
            if (rows.length === 0) return null;
            rememberDims(rows[0].length);
            const result = single ? rows[0] : rows;
            if (_cache.size >= _CACHE_MAX) _cache.clear();
            _cache.set(cacheKey, result);
            return result;
        } catch (e) {
            return null;
        }
    }

    /** Persist detected dimensions so mismatches surface early. */
    function rememberDims(dims) {
        if (!dims || dims === config.embedDims) return;
        config.embedDims = dims;
        config.save();
    }

    /**
     * Connection test for the settings UI.
     * @returns {Promise<{ok: boolean, dims?: number, error?: string}>}
     */
    async function test() {
        if (!config?.embedUrl || !config?.embedModel) {
            return { ok: false, error: 'URL and model required' };
        }
        const vector = await embed('VirtualWorld embedding test');
        if (!vector) return { ok: false, error: 'request failed or disabled' };
        return { ok: true, dims: vector.length };
    }

    window.EmbeddingClient = { embed, test, configured };
})();
