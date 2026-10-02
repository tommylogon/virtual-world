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
 *
 * @module shared/embedding-client — embeddings for semantic memory
 * @contributes window.EmbeddingClient (OpenAI-compatible /embeddings); returns null on any failure
 * @powers meaning-based memory recall when Semantic Memory is enabled in Settings
 * @relates configured from config.embed*; the backend only ever receives finished vectors
 * @docs docs/virtualWorld/AI & Narration/Memory System.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
(() => {
    'use strict';

    // Bounded in-memory dedupe: prompt/render pipelines embed the same text
    // repeatedly (e.g. the Agent Lens rebuilds on every state poll), so cache
    // identical inputs here instead of hammering the local model server.
    const _cache = new Map<string, number[] | number[][] | null>();
    const _CACHE_MAX = 512;

    function configured(): boolean {
        return !!(config?.embedEnabled && config?.embedUrl && config?.embedModel);
    }

    function headers(): Record<string, string> {
        const h: Record<string, string> = { 'Content-Type': 'application/json' };
        if (config.embedApiKey) h['Authorization'] = 'Bearer ' + config.embedApiKey;
        return h;
    }

    /**
     * Embed one string or an array of strings.
     * @param input
     * @returns vector(s), null on failure/disabled
     */
    async function embed(input: string | string[]): Promise<number[] | number[][] | null> {
        if (!configured() || !input || (Array.isArray(input) && input.length === 0)) return null;
        const single = typeof input === 'string';
        const cacheKey = JSON.stringify(input);
        if (_cache.has(cacheKey)) return _cache.get(cacheKey) ?? null;
        try {
            const baseUrl = String(config.embedUrl).replace(/\/+$/, '');
            const resp = await fetch(baseUrl + '/embeddings', {
                method: 'POST',
                headers: headers(),
                body: JSON.stringify({ model: config.embedModel, input }),
                signal: AbortSignal.timeout(15000)
            });
            if (!resp.ok) return null;
            const data = (await resp.json()) as { data?: { embedding?: unknown }[] };
            const rows = (data.data || []).map(d => d.embedding).filter(Array.isArray) as number[][];
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
    function rememberDims(dims: number): void {
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

    const EmbeddingClient = { embed, test, configured };
    (window as unknown as { EmbeddingClient: typeof EmbeddingClient }).EmbeddingClient = EmbeddingClient;
})();
