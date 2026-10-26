/**
 * dataset-collector.js — captures every LLM request/response pair so it can be
 * exported as a chat-format JSONL fine-tuning dataset.
 *
 * Hooks into llmClient.chat() (see llm-client.js) and persists each
 * { messages, response, label, model, parsed_ok, repaired } to IndexedDB via
 * the shared `storage` provider (store: llm_dataset). A small floating panel
 * offers export as JSONL (all / successes / failures) and clear.
 *
 * The point of capturing BOTH the raw response and whether it parsed is that
 * fine-tuning wants positive examples (clean JSON) AND negative ones (the
 * broken output + the corrected target) so a tiny model learns to emit valid
 * JSON in the exact shapes the app's prompts demand.
 *
 * @module shared/dataset-collector — dataset capture + raw exchange store
 * @contributes DatasetCollector.capture / captureRaw / getAll / getAllRaw / clearRaw + the 🧪 export panel
 * @powers the fine-tuning dataset export and the 🔬 LLM inspector's raw exchanges
 * @relates hooks llm-client.chat(); persists via storage (llm_dataset, llm_raw_exchanges)
 * @docs docs/virtualWorld/UI & Settings/Event Log Export.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

// The two capture sequences and the json-utils parsers are classic-script globals
// that globals.d.ts does not declare; reached through casts so this file compiles
// alone without touching the shared declaration hub.

(window as unknown as { DatasetCollector: DatasetCollectorApi }).DatasetCollector = (() => {
    const _seqWin = () => (window as unknown as { __datasetSeq?: number; __rawSeq?: number });
    const _jsonUtils = (window as unknown as {
        parseJSONFromResponse?(text: string): { json: unknown };
        repairJSON?(text: string): string;
    });
    const STORE = 'llm_dataset';

    /** Fire-and-forget persist; never throws. */
    async function capture(messages: unknown, response: string, label: string, meta: Record<string, unknown> | null | undefined): Promise<void> {
        try {
            if (typeof storage === 'undefined' || !storage) return;
            const text = String(response || '').trim();
            if (!text) return; // nothing usable
            const outcome = _outcome(text);
            const entry = {
                key: _nextKey(),
                ts: Date.now(),
                label: label || 'LLM',
                model: (typeof llmClient !== 'undefined' && llmClient.model) || '',
                messages: _cleanMessages(messages),
                response: text,
                parsed_ok: outcome.parsed_ok,
                repaired: outcome.repaired,
                response_format: (meta && meta.responseFormat) || null,
            };
            // Fire-and-forget; IndexedDB writes are async and we must not block the game.
            storage.set(STORE, entry.key, entry);
        } catch (e) { /* never break the game loop for dataset capture */ }
    }

    function _nextKey(): string {
        const win = _seqWin();
        const n = (win.__datasetSeq = (win.__datasetSeq || 0) + 1);
        return 'd' + Date.now() + '_' + n;
    }

    /** Try to parse; report whether it parsed cleanly or needed repair. */
    function _outcome(text: string): { parsed_ok: boolean; repaired: boolean } {
        let parsed_ok = false, repaired = false;
        try {
            const parse = _jsonUtils.parseJSONFromResponse;
            if (typeof parse === 'function') {
                const r = parse(text);
                parsed_ok = !!r.json;
            } else {
                parsed_ok = (() => { try { JSON.parse(text); return true; } catch (e) { return false; } })();
            }
            if (!parsed_ok && typeof _jsonUtils.repairJSON === 'function') {
                try { repaired = !!JSON.parse((_jsonUtils.repairJSON as (t: string) => string)(text)); } catch (e) { repaired = false; }
            }
        } catch (e) {}
        return { parsed_ok, repaired };
    }

    /** Keep only text system/user/assistant messages (drop tool calls/results). */
    function _cleanMessages(messages: unknown): ChatMessage[] {
        if (!Array.isArray(messages)) return [];
        return (messages as ChatMessage[])
            .filter(m => m && (m.role === 'system' || m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string')
            .map(m => ({ role: m.role, content: m.content }));
    }

    async function getAll(): Promise<DatasetEntry[]> {
        try {
            if (typeof storage === 'undefined' || !storage) return [];
            const map = await storage.getAll(STORE) as Record<string, DatasetEntry>;
            return Object.keys(map).map(k => map[k]);
        } catch (e) { return []; }
    }

    async function count(): Promise<number> {
        const all = await getAll();
        return all.length;
    }

    async function clear(): Promise<void> {
        try { if (typeof storage !== 'undefined' && storage) await storage.clear(STORE); } catch (e) {}
    }

    // ── Raw HTTP exchange capture (task-405, LLM Inspector) ──────────────
    // Separate store from the fine-tuning dataset: this keeps the full request
    // body and the raw response envelope (status, headers, usage, error shape)
    // so providers can be debugged. Authorization is redacted before storage.
    const RAW_STORE = 'llm_raw_exchanges';
    const RAW_MAX = 200;

    function _redactHeaders(headers: Record<string, unknown> | null | undefined): Record<string, unknown> {
        const out: Record<string, unknown> = {};
        try {
            Object.keys(headers || {}).forEach(k => {
                const headerValue = String(headers?.[k]);
                if (/^(authorization|api[-_]key|x-api[-_]key)$/i.test(k)) {
                    const prefix = /^Bearer\s+/i.test(headerValue) ? 'Bearer ' : '';
                    out[k] = prefix + headerValue.replace(/^Bearer\s+/i, '').slice(0, 6) + '…REDACTED';
                } else {
                    out[k] = headers?.[k];
                }
            });
        } catch (e) { /* ignore */ }
        return out;
    }

    function _nextRawKey(): string {
        const win = _seqWin();
        const n = (win.__rawSeq = (win.__rawSeq || 0) + 1);
        return 'r' + Date.now() + '_' + n;
    }

    /**
     * The best available name for an exchange that arrived without one
     * (task-593). Ordered by how much it actually tells you:
     *
     * 1. the caller's own `label` — the real answer, and what the call sites now
     *    pass;
     * 2. the model's name, so two providers are at least distinguishable;
     * 3. a shape-derived summary of the request, so a call site that forgets to
     *    label itself is still traceable to *what it asked* rather than becoming
     *    one more row of noise.
     *
     * It deliberately never returns the bare string 'LLM': that name carries no
     * information and its presence is indistinguishable from a capture that
     * failed, which is exactly the confusion this function exists to remove.
     */
    function _deriveLabel(x: RawExchange): string {
        if (x && x.label) return String(x.label);
        const model = (x && x.model) || (typeof llmClient !== 'undefined' && llmClient.model) || '';
        const body = ((x && x.requestBody) as Record<string, unknown> | undefined) || {};
        const shape = (() => {
            try {
                if (body.withTools || body.tools) return 'tools';
                if (body.stream) return 'streamed';
                if (body.response_format || body.responseFormat) return 'structured';
                return 'chat';
            } catch (e) { return 'chat'; }
        })();
        return model ? `unlabelled/${model}/${shape}` : `unlabelled/${shape}`;
    }

    /**
     * Persist a full exchange. Fire-and-forget; never throws, never blocks the
     * game loop. Only records when the `showRawLLM` opt-in is enabled.
     * @param {Object} x - { label, model, url, requestHeaders, requestBody,
     *                       status, statusText, responseHeaders, body, durationMs, parsedOk }
     */
    async function captureRaw(x: RawExchange): Promise<void> {
        try {
            if (typeof storage === 'undefined' || !storage) return;
            if (typeof config !== 'undefined' && config && !config.showRawLLM) return;
            const entry = {
                key: _nextRawKey(),
                ts: Date.now(),
                // An exchange with no label is **identified, not anonymous**
                // (task-593). The old fallback was the constant 'LLM', which is
                // what made eleven of seventeen call sites indistinguishable: the
                // inspector filled with identical entries and read as broken, when
                // the capture had in fact worked. Deriving from the request's own
                // `label` argument, and then from the messages' shape, means a
                // future call site that forgets to label itself still says where
                // it came from — and is visibly *missing* a name rather than
                // silently pretending to be the whole system.
                label: _deriveLabel(x),
                model: x.model || (typeof llmClient !== 'undefined' && llmClient.model) || '',
                request: {
                    url: x.url || '',
                    method: 'POST',
                    headers: _redactHeaders(x.requestHeaders || {}),
                    body: x.requestBody ?? null,
                },
                response: {
                    status: x.status ?? null,
                    statusText: x.statusText || '',
                    headers: _redactHeaders(x.responseHeaders || {}),
                    body: x.body ?? null,
                },
                duration_ms: x.durationMs ?? null,
                parsed_ok: x.parsedOk ?? null,
            };
            await storage.set(RAW_STORE, entry.key, entry);
            // Occasional trim (not every call) keeps the store bounded without
            // paying a full read on each capture.
            if ((_seqWin().__rawSeq! % 25) === 0) _trimRaw();
        } catch (e) { /* never break the game loop */ }
    }

    async function _trimRaw(): Promise<void> {
        try {
            const map = await storage.getAll(RAW_STORE) as Record<string, RawExchangeEntry>;
            const keys = Object.keys(map);
            if (keys.length <= RAW_MAX) return;
            keys.sort(); // 'r' + timestamp → chronological
            for (const k of keys.slice(0, keys.length - RAW_MAX)) {
                await storage.delete(RAW_STORE, k);
            }
        } catch (e) { /* ignore */ }
    }

    async function getAllRaw(): Promise<RawExchangeEntry[]> {
        try {
            if (typeof storage === 'undefined' || !storage) return [];
            const map = await storage.getAll(RAW_STORE) as Record<string, RawExchangeEntry>;
            return Object.keys(map).map(k => map[k]).sort((a, b) => b.ts - a.ts);
        } catch (e) { return []; }
    }

    async function clearRaw(): Promise<void> {
        try { if (typeof storage !== 'undefined' && storage) await storage.clear(RAW_STORE); } catch (e) {}
    }

    async function countRaw(): Promise<number> {
        return (await getAllRaw()).length;
    }

    /**
     * Build chat-format JSONL lines: [{role,content},...,{role:'assistant',
     * content: <response>}]. Optionally filter by outcome.
     * @param {string} filter - 'all' | 'ok' | 'fail'
     */
    async function buildJSONL(filter: string = 'all'): Promise<string> {
        const all = await getAll();
        const lines: string[] = [];
        for (const e of all) {
            if (filter === 'ok' && !e.parsed_ok) continue;
            if (filter === 'fail' && e.parsed_ok) continue;
            const msgs = (e.messages || []).map(m => ({ role: m.role, content: m.content }));
            msgs.push({ role: 'assistant', content: e.response });
            lines.push(JSON.stringify({ messages: msgs, meta: { label: e.label, model: e.model, parsed_ok: e.parsed_ok, repaired: e.repaired } }));
        }
        return lines.join('\n');
    }

    function _download(filename: string, text: string): void {
        const blob = new Blob([text], { type: 'application/x-ndjson' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }

    // --- Minimal floating panel UI ---
    let _panel: HTMLElement | null = null;
    function ensureUI(): void {
        if (_panel) return;
        const btn = document.createElement('button');
        btn.id = 'dataset-collector-btn';
        btn.textContent = '🧪 dataset';
        btn.title = 'LLM dataset collector — capture & export fine-tuning data';
        btn.style.cssText = 'position:fixed;right:14px;bottom:14px;z-index:12000;font-size:11px;padding:6px 10px;border-radius:6px;cursor:pointer;background:var(--bg-inset,#222);color:var(--text,#eee);border:1px solid var(--border,#444);';
        btn.addEventListener('click', togglePanel);
        document.body.appendChild(btn);

        _panel = document.createElement('div');
        _panel.id = 'dataset-collector-panel';
        _panel.style.cssText = 'position:fixed;right:14px;bottom:48px;z-index:12000;width:280px;padding:12px;border-radius:8px;background:var(--bg-inset,#1c1c1c);color:var(--text,#eee);border:1px solid var(--border,#444);font-size:12px;display:none;font-family:var(--font-mono,monospace);';
        _panel.innerHTML = `
            <div style="font-weight:bold;margin-bottom:8px;">LLM Dataset Collector</div>
            <div id="dataset-count" style="margin-bottom:8px;color:var(--text-dim,#999);">loading…</div>
            <div style="display:flex;flex-direction:column;gap:6px;">
                <button data-act="all">Export all (JSONL)</button>
                <button data-act="ok">Export parsed-OK only</button>
                <button data-act="fail">Export failures only</button>
                <button data-act="clear" style="color:#f66;">Clear dataset</button>
            </div>
            <div id="dataset-status" style="margin-top:8px;font-size:10px;color:var(--text-dim,#999);"></div>`;
        document.body.appendChild(_panel);
        _panel.querySelectorAll<HTMLElement>('button').forEach(b => b.addEventListener('click', () => onAction(b.dataset.act)));
        refreshCount();
    }

    async function togglePanel(): Promise<void> {
        ensureUI();
        _panel!.style.display = _panel!.style.display === 'none' ? 'block' : 'none';
        if (_panel!.style.display === 'block') refreshCount();
    }

    async function refreshCount(): Promise<void> {
        if (!_panel) return;
        const all = await getAll();
        const ok = all.filter(e => e.parsed_ok).length;
        const fail = all.filter(e => !e.parsed_ok).length;
        const el = _panel.querySelector('#dataset-count');
        if (el) el.textContent = `${all.length} captured · ${ok} parsed-OK · ${fail} failed`;
    }

    async function onAction(act: string | undefined): Promise<void> {
        const status = _panel!.querySelector('#dataset-status');
        const set = (t: string) => { if (status) status.textContent = t; };
        try {
            if (act === 'clear') {
                await clear();
                set('cleared');
                refreshCount();
                return;
            }
            const filter = act === 'ok' ? 'ok' : act === 'fail' ? 'fail' : 'all';
            const jsonl = await buildJSONL(filter);
            if (!jsonl) { set('no entries'); return; }
            _download(`virtual-world-llm-${filter}.jsonl`, jsonl);
            set(`exported ${jsonl.split('\n').length} examples`);
        } catch (e) { set('error: ' + (e instanceof Error ? e.message : e)); }
    }

    return {
        capture, getAll, count, clear, buildJSONL, ensureUI, togglePanel,
        captureRaw, getAllRaw, clearRaw, countRaw,
    };
})();

// Auto-show the floating button once the DOM is ready (no user action needed).
if (typeof window !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => (window as unknown as { DatasetCollector: DatasetCollectorApi }).DatasetCollector.ensureUI());
    } else {
        (window as unknown as { DatasetCollector: DatasetCollectorApi }).DatasetCollector.ensureUI();
    }
}

/*
 * Type declarations live below the first value statement on purpose: TypeScript
 * drops a file's leading JSDoc block when the first statement is type-only, and
 * `tools/js_module_index.py` reads `@module` out of the emitted `.js`.
 */

interface ChatMessage {
    role: 'system' | 'user' | 'assistant';
    content: string;
}

/** One captured fine-tuning example (store: llm_dataset). */
interface DatasetEntry {
    key: string;
    ts: number;
    label: string;
    model: string;
    messages: ChatMessage[];
    response: string;
    parsed_ok: boolean;
    repaired: boolean;
    response_format: unknown;
}

/** One captured raw HTTP exchange (store: llm_raw_exchanges). */
interface RawExchangeEntry {
    key: string;
    ts: number;
    [key: string]: unknown;
}

/** What llm-client.js hands captureRaw for one request/response pair. */
interface RawExchange {
    label?: string;
    model?: string;
    url?: string;
    requestHeaders?: Record<string, unknown>;
    requestBody?: unknown;
    status?: number | null;
    statusText?: string;
    responseHeaders?: Record<string, unknown>;
    body?: unknown;
    durationMs?: number | null;
    parsedOk?: boolean | null;
}

interface DatasetCollectorApi {
    capture(messages: unknown, response: string, label: string, meta: Record<string, unknown> | null | undefined): Promise<void>;
    getAll(): Promise<DatasetEntry[]>;
    count(): Promise<number>;
    clear(): Promise<void>;
    buildJSONL(filter?: string): Promise<string>;
    ensureUI(): void;
    togglePanel(): Promise<void>;
    captureRaw(x: RawExchange): Promise<void>;
    getAllRaw(): Promise<RawExchangeEntry[]>;
    clearRaw(): Promise<void>;
    countRaw(): Promise<number>;
}