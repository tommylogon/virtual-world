"use strict";
/**
 * llm-inspector.js - raw LLM request/response inspector (task-405).
 *
 * Reads the `llm_raw_exchanges` store written by DatasetCollector.captureRaw
 * and shows the complete HTTP exchange: request headers + body, response
 * status/headers/body, usage (including reasoning tokens), duration, and
 * provider error shapes. Authorization headers are redacted at capture time.
 *
 * Capture is opt-in via Settings → "Show Raw LLM" (config.showRawLLM).
 *
 * @module ui/llm-inspector - the raw LLM exchange inspector
 * @contributes the 🔬 floating panel: expand per entry, usage line, copy request/response, filters, clear
 * @powers LLM calls - debugging exactly what was sent to and returned by the provider (task-405)
 * @relates reads dataset-collector's llm_raw_exchanges store; gated by config.showRawLLM
 * @docs docs/virtualWorld/AI & Narration/LLM Providers.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
(() => {
    let _btn = null;
    let _panel = null;
    let _entries = [];
    function _esc(s) {
        const table = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' };
        return String(s == null ? '' : s).replace(/[&<>"]/g, c => table[c]);
    }
    function _json(o) {
        let text;
        try {
            text = JSON.stringify(o, null, 2);
        }
        catch (e) {
            text = String(o);
        }
        if (text == null)
            text = '';
        const MAX = 200000;
        if (text.length > MAX)
            text = text.slice(0, MAX) + '\n…truncated (' + text.length + ' chars)';
        return _esc(text);
    }
    function _usageLine(body, headers) {
        const b = body;
        const u = b?.usage;
        const parts = [];
        const provider = headers?.['x-openrouter-provider'] || b?.provider;
        if (provider)
            parts.push('provider: ' + provider);
        if (u) {
            if (u.prompt_tokens != null)
                parts.push('prompt ' + u.prompt_tokens);
            if (u.completion_tokens != null)
                parts.push('completion ' + u.completion_tokens);
            if (u.input_tokens != null)
                parts.push('in ' + u.input_tokens);
            if (u.output_tokens != null)
                parts.push('out ' + u.output_tokens);
            if (u.output_tokens_details?.reasoning_tokens != null)
                parts.push('reasoning ' + u.output_tokens_details.reasoning_tokens);
            if (u.total_tokens != null)
                parts.push('total ' + u.total_tokens);
            const cost = u.total_cost != null ? u.total_cost : u.cost;
            if (cost != null)
                parts.push('$' + Number(cost).toFixed(5));
        }
        return parts.length
            ? `<div style="color:var(--text-dim,#999);font-size:11px;">metadata: ${_esc(parts.join(' · '))}</div>`
            : '';
    }
    function ensureUI() {
        if (_btn)
            return;
        _btn = document.createElement('button');
        _btn.id = 'llm-inspector-btn';
        _btn.textContent = '🔬 LLM inspector';
        _btn.title = 'Raw LLM request/response inspector';
        _btn.style.cssText = 'position:fixed;right:14px;bottom:46px;z-index:12000;font-size:11px;padding:6px 10px;border-radius:6px;cursor:pointer;background:var(--bg-inset,#222);color:var(--text,#eee);border:1px solid var(--border,#444);';
        _btn.addEventListener('click', toggle);
        document.body.appendChild(_btn);
        _panel = document.createElement('div');
        _panel.id = 'llm-inspector-panel';
        _panel.style.cssText = 'position:fixed;right:14px;bottom:82px;z-index:12001;width:min(600px,94vw);max-height:72vh;overflow:auto;padding:10px;border-radius:8px;background:var(--bg-inset,#1c1c1c);color:var(--text,#eee);border:1px solid var(--border,#444);font-size:12px;display:none;font-family:var(--font-mono,monospace);';
        const topRow = document.createElement('div');
        topRow.style.cssText = 'display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;';
        const titleStrong = document.createElement('strong');
        titleStrong.textContent = 'LLM Inspector';
        const countSpan = document.createElement('span');
        countSpan.id = 'llm-inspector-count';
        countSpan.style.cssText = 'color:var(--text-dim,#999);font-size:11px;';
        topRow.append(titleStrong, countSpan);
        const filterRow = document.createElement('div');
        filterRow.style.cssText = 'display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;';
        const labelInput = document.createElement('input');
        labelInput.id = 'llm-inspector-label';
        labelInput.placeholder = 'filter label';
        labelInput.style.cssText = 'flex:1;min-width:80px;font-size:11px;padding:4px;background:var(--bg-input,#111);color:inherit;border:1px solid var(--border,#444);border-radius:4px;';
        const statusInput = document.createElement('input');
        statusInput.id = 'llm-inspector-status';
        statusInput.placeholder = 'status';
        statusInput.style.cssText = 'width:56px;font-size:11px;padding:4px;background:var(--bg-input,#111);color:inherit;border:1px solid var(--border,#444);border-radius:4px;';
        const searchInput = document.createElement('input');
        searchInput.id = 'llm-inspector-search';
        searchInput.placeholder = 'search body';
        searchInput.style.cssText = 'flex:1;min-width:80px;font-size:11px;padding:4px;background:var(--bg-input,#111);color:inherit;border:1px solid var(--border,#444);border-radius:4px;';
        const refreshBtn = document.createElement('button');
        refreshBtn.id = 'llm-inspector-refresh';
        refreshBtn.textContent = 'Refresh';
        const clearBtn = document.createElement('button');
        clearBtn.id = 'llm-inspector-clear';
        clearBtn.style.color = '#f66';
        clearBtn.textContent = 'Clear';
        filterRow.append(labelInput, statusInput, searchInput, refreshBtn, clearBtn);
        const listDiv = document.createElement('div');
        listDiv.id = 'llm-inspector-list';
        _panel.append(topRow, filterRow, listDiv);
        document.body.appendChild(_panel);
        const panel = _panel;
        panel.querySelector('#llm-inspector-refresh').addEventListener('click', render);
        panel.querySelector('#llm-inspector-clear').addEventListener('click', async () => {
            await _datasetCollector()?.clearRaw?.();
            render();
        });
        panel.querySelector('#llm-inspector-label').addEventListener('input', render);
        panel.querySelector('#llm-inspector-status').addEventListener('input', render);
        panel.querySelector('#llm-inspector-search').addEventListener('input', render);
        panel.querySelector('#llm-inspector-list').addEventListener('click', onListClick);
    }
    async function toggle() {
        ensureUI();
        const panel = _panel;
        const show = panel.style.display === 'none';
        panel.style.display = show ? 'block' : 'none';
        if (show)
            render();
    }
    async function onListClick(ev) {
        const btn = ev.target.closest('button[data-copy]');
        if (!btn)
            return;
        const entry = _entries.find(x => x.key === btn.dataset.key);
        if (!entry)
            return;
        const isReq = btn.dataset.copy === 'req';
        const payload = isReq
            ? { url: entry.request?.url, method: entry.request?.method, headers: entry.request?.headers, body: entry.request?.body }
            : { status: entry.response?.status, headers: entry.response?.headers, body: entry.response?.body };
        try {
            await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
            const original = btn.textContent;
            btn.textContent = 'Copied ✓';
            setTimeout(() => { btn.textContent = original; }, 1200);
        }
        catch (e) {
            btn.textContent = 'Copy failed';
        }
    }
    async function render() {
        ensureUI();
        const panel = _panel;
        _entries = (await _datasetCollector()?.getAllRaw?.()) || [];
        const labelF = (panel.querySelector('#llm-inspector-label').value || '').toLowerCase();
        const statusF = (panel.querySelector('#llm-inspector-status').value || '').trim();
        const searchF = (panel.querySelector('#llm-inspector-search').value || '').toLowerCase();
        const rows = _entries.filter((e) => {
            if (labelF && !String(e.label || '').toLowerCase().includes(labelF))
                return false;
            if (statusF && String(e.response?.status ?? '') !== statusF)
                return false;
            if (searchF) {
                const hay = (_json(e.request?.body) + _json(e.response?.body)).toLowerCase();
                if (!hay.includes(searchF))
                    return false;
            }
            return true;
        });
        const countEl = panel.querySelector('#llm-inspector-count');
        if (countEl)
            countEl.textContent = `${rows.length}/${_entries.length}`;
        const list = panel.querySelector('#llm-inspector-list');
        if (!rows.length) {
            const empty = document.createElement('div');
            empty.style.color = 'var(--text-dim,#999)';
            empty.textContent = 'No exchanges captured. Enable “Show Raw LLM” in Settings and make a call.';
            list.replaceChildren(empty);
            return;
        }
        const frag = document.createDocumentFragment();
        for (const e of rows) {
            const status = e.response?.status ?? '-';
            const color = (typeof status === 'number' && status >= 200 && status < 300) ? '#6c6' : '#f66';
            const dur = e.duration_ms != null ? ` · ${e.duration_ms}ms` : '';
            const preStyle = 'white-space:pre-wrap;word-break:break-word;max-height:180px;overflow:auto;background:var(--bg-input,#111);padding:6px;border-radius:4px;margin:4px 0;';
            const respHeaders = e.response?.headers;
            const provHeader = respHeaders?.['x-openrouter-provider'] || e.response?.body?.provider;
            const provBadge = provHeader ? ` · [${_esc(provHeader)}]` : '';
            const detailsHtml = `<details style="margin-bottom:6px;border:1px solid var(--border,#333);border-radius:4px;padding:6px;">
                <summary style="cursor:pointer;"><span style="color:${color};">●</span> ${_esc(e.label)} · ${_esc(e.model)} · ${_esc(status)}${_esc(dur)}${provBadge}</summary>
                ${_usageLine(e.response?.body, respHeaders)}
                <div style="display:flex;gap:6px;margin:6px 0;">
                    <button data-copy="req" data-key="${_esc(e.key)}">Copy request</button>
                    <button data-copy="res" data-key="${_esc(e.key)}">Copy response</button>
                </div>
                <div style="color:var(--text-dim,#999);">Request: POST ${_esc(e.request?.url)}</div>
                <pre style="${preStyle}">${_json({ headers: e.request?.headers, body: e.request?.body })}</pre>
                <div style="color:var(--text-dim,#999);">Response: ${_esc(status)} ${_esc(e.response?.statusText)}</div>
                <pre style="${preStyle}">${_json({ headers: e.response?.headers, body: e.response?.body })}</pre>
            </details>`;
            frag.appendChild(document.createRange().createContextualFragment(detailsHtml));
        }
        list.replaceChildren(frag);
    }
    if (typeof window !== 'undefined') {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', ensureUI);
        }
        else {
            ensureUI();
        }
    }
    /**
     * `window.DatasetCollector` (shared/dataset-collector.js) is not declared on
     * the Window interface in types/globals.d.ts, which is a shared hub under
     * concurrent edit, so it is read through a local cast.
     */
    function _datasetCollector() {
        return window.DatasetCollector;
    }
})();
