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
window.DatasetCollector = (() => {
    const STORE = 'llm_dataset';

    /** Fire-and-forget persist; never throws. */
    async function capture(messages, response, label, meta) {
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

    function _nextKey() {
        const n = (window.__datasetSeq = (window.__datasetSeq || 0) + 1);
        return 'd' + Date.now() + '_' + n;
    }

    /** Try to parse; report whether it parsed cleanly or needed repair. */
    function _outcome(text) {
        let parsed_ok = false, repaired = false;
        try {
            if (typeof parseJSONFromResponse === 'function') {
                const r = parseJSONFromResponse(text);
                parsed_ok = !!r.json;
            } else {
                parsed_ok = (() => { try { JSON.parse(text); return true; } catch (e) { return false; } })();
            }
            if (!parsed_ok && typeof repairJSON === 'function') {
                try { repaired = !!JSON.parse(repairJSON(text)); } catch (e) { repaired = false; }
            }
        } catch (e) {}
        return { parsed_ok, repaired };
    }

    /** Keep only text system/user/assistant messages (drop tool calls/results). */
    function _cleanMessages(messages) {
        if (!Array.isArray(messages)) return [];
        return messages
            .filter(m => m && (m.role === 'system' || m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string')
            .map(m => ({ role: m.role, content: m.content }));
    }

    async function getAll() {
        try {
            if (typeof storage === 'undefined' || !storage) return [];
            const map = await storage.getAll(STORE);
            return Object.keys(map).map(k => map[k]);
        } catch (e) { return []; }
    }

    async function count() {
        const all = await getAll();
        return all.length;
    }

    async function clear() {
        try { if (typeof storage !== 'undefined' && storage) await storage.clear(STORE); } catch (e) {}
    }

    // ── Raw HTTP exchange capture (task-405, LLM Inspector) ──────────────
    // Separate store from the fine-tuning dataset: this keeps the full request
    // body and the raw response envelope (status, headers, usage, error shape)
    // so providers can be debugged. Authorization is redacted before storage.
    const RAW_STORE = 'llm_raw_exchanges';
    const RAW_MAX = 200;

    function _redactHeaders(headers) {
        const out = {};
        try {
            Object.keys(headers || {}).forEach(k => {
                const headerValue = String(headers[k]);
                if (/^(authorization|api[-_]key|x-api[-_]key)$/i.test(k)) {
                    const prefix = /^Bearer\s+/i.test(headerValue) ? 'Bearer ' : '';
                    out[k] = prefix + headerValue.replace(/^Bearer\s+/i, '').slice(0, 6) + '…REDACTED';
                } else {
                    out[k] = headers[k];
                }
            });
        } catch (e) { /* ignore */ }
        return out;
    }

    function _nextRawKey() {
        const n = (window.__rawSeq = (window.__rawSeq || 0) + 1);
        return 'r' + Date.now() + '_' + n;
    }

    /**
     * Persist a full exchange. Fire-and-forget; never throws, never blocks the
     * game loop. Only records when the `showRawLLM` opt-in is enabled.
     * @param {Object} x - { label, model, url, requestHeaders, requestBody,
     *                       status, statusText, responseHeaders, body, durationMs, parsedOk }
     */
    async function captureRaw(x) {
        try {
            if (typeof storage === 'undefined' || !storage) return;
            if (typeof config !== 'undefined' && config && !config.showRawLLM) return;
            const entry = {
                key: _nextRawKey(),
                ts: Date.now(),
                label: x.label || 'LLM',
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
            if ((window.__rawSeq % 25) === 0) _trimRaw();
        } catch (e) { /* never break the game loop */ }
    }

    async function _trimRaw() {
        try {
            const map = await storage.getAll(RAW_STORE);
            const keys = Object.keys(map);
            if (keys.length <= RAW_MAX) return;
            keys.sort(); // 'r' + timestamp → chronological
            for (const k of keys.slice(0, keys.length - RAW_MAX)) {
                await storage.delete(RAW_STORE, k);
            }
        } catch (e) { /* ignore */ }
    }

    async function getAllRaw() {
        try {
            if (typeof storage === 'undefined' || !storage) return [];
            const map = await storage.getAll(RAW_STORE);
            return Object.keys(map).map(k => map[k]).sort((a, b) => b.ts - a.ts);
        } catch (e) { return []; }
    }

    async function clearRaw() {
        try { if (typeof storage !== 'undefined' && storage) await storage.clear(RAW_STORE); } catch (e) {}
    }

    async function countRaw() {
        return (await getAllRaw()).length;
    }

    /**
     * Build chat-format JSONL lines: [{role,content},...,{role:'assistant',
     * content: <response>}]. Optionally filter by outcome.
     * @param {string} filter - 'all' | 'ok' | 'fail'
     */
    async function buildJSONL(filter = 'all') {
        const all = await getAll();
        const lines = [];
        for (const e of all) {
            if (filter === 'ok' && !e.parsed_ok) continue;
            if (filter === 'fail' && e.parsed_ok) continue;
            const msgs = (e.messages || []).map(m => ({ role: m.role, content: m.content }));
            msgs.push({ role: 'assistant', content: e.response });
            lines.push(JSON.stringify({ messages: msgs, meta: { label: e.label, model: e.model, parsed_ok: e.parsed_ok, repaired: e.repaired } }));
        }
        return lines.join('\n');
    }

    function _download(filename, text) {
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
    let _panel = null;
    function ensureUI() {
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
        _panel.querySelectorAll('button').forEach(b => b.addEventListener('click', () => onAction(b.dataset.act)));
        refreshCount();
    }

    async function togglePanel() {
        ensureUI();
        _panel.style.display = _panel.style.display === 'none' ? 'block' : 'none';
        if (_panel.style.display === 'block') refreshCount();
    }

    async function refreshCount() {
        if (!_panel) return;
        const all = await getAll();
        const ok = all.filter(e => e.parsed_ok).length;
        const fail = all.filter(e => !e.parsed_ok).length;
        const el = _panel.querySelector('#dataset-count');
        if (el) el.textContent = `${all.length} captured · ${ok} parsed-OK · ${fail} failed`;
    }

    async function onAction(act) {
        const status = _panel.querySelector('#dataset-status');
        const set = (t) => { if (status) status.textContent = t; };
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
        } catch (e) { set('error: ' + (e.message || e)); }
    }

    return {
        capture, getAll, count, clear, buildJSONL, ensureUI, togglePanel,
        captureRaw, getAllRaw, clearRaw, countRaw,
    };
})();

// Auto-show the floating button once the DOM is ready (no user action needed).
if (typeof window !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => window.DatasetCollector.ensureUI());
    } else {
        window.DatasetCollector.ensureUI();
    }
}