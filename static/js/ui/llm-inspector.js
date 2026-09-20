/**
 * llm-inspector.js — raw LLM request/response inspector (task-405).
 *
 * Reads the `llm_raw_exchanges` store written by DatasetCollector.captureRaw
 * and shows the complete HTTP exchange: request headers + body, response
 * status/headers/body, usage (including reasoning tokens), duration, and
 * provider error shapes. Authorization headers are redacted at capture time.
 *
 * Capture is opt-in via Settings → "Show Raw LLM" (config.showRawLLM).
 */
(() => {
    let _btn = null;
    let _panel = null;
    let _entries = [];

    function _esc(s) {
        return String(s == null ? '' : s).replace(/[&<>"]/g, c => (
            { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]
        ));
    }

    function _json(o) {
        let text;
        try { text = JSON.stringify(o, null, 2); } catch (e) { text = String(o); }
        if (text == null) text = '';
        const MAX = 200000;
        if (text.length > MAX) text = text.slice(0, MAX) + '\n…truncated (' + text.length + ' chars)';
        return _esc(text);
    }

    function _usageLine(body) {
        const u = body && body.usage;
        if (!u) return '';
        const parts = [];
        if (u.prompt_tokens != null) parts.push('prompt ' + u.prompt_tokens);
        if (u.completion_tokens != null) parts.push('completion ' + u.completion_tokens);
        if (u.input_tokens != null) parts.push('in ' + u.input_tokens);
        if (u.output_tokens != null) parts.push('out ' + u.output_tokens);
        if (u.output_tokens_details?.reasoning_tokens != null) parts.push('reasoning ' + u.output_tokens_details.reasoning_tokens);
        if (u.total_tokens != null) parts.push('total ' + u.total_tokens);
        if (u.cost != null) parts.push('$' + u.cost);
        return parts.length
            ? `<div style="color:var(--text-dim,#999);font-size:11px;">usage: ${_esc(parts.join(' · '))}</div>`
            : '';
    }

    function ensureUI() {
        if (_btn) return;
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
        _panel.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <strong>LLM Inspector</strong>
                <span id="llm-inspector-count" style="color:var(--text-dim,#999);font-size:11px;"></span>
            </div>
            <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;">
                <input id="llm-inspector-label" placeholder="filter label" style="flex:1;min-width:80px;font-size:11px;padding:4px;background:var(--bg-input,#111);color:inherit;border:1px solid var(--border,#444);border-radius:4px;">
                <input id="llm-inspector-status" placeholder="status" style="width:56px;font-size:11px;padding:4px;background:var(--bg-input,#111);color:inherit;border:1px solid var(--border,#444);border-radius:4px;">
                <input id="llm-inspector-search" placeholder="search body" style="flex:1;min-width:80px;font-size:11px;padding:4px;background:var(--bg-input,#111);color:inherit;border:1px solid var(--border,#444);border-radius:4px;">
                <button id="llm-inspector-refresh">Refresh</button>
                <button id="llm-inspector-clear" style="color:#f66;">Clear</button>
            </div>
            <div id="llm-inspector-list"></div>`;
        document.body.appendChild(_panel);

        _panel.querySelector('#llm-inspector-refresh').addEventListener('click', render);
        _panel.querySelector('#llm-inspector-clear').addEventListener('click', async () => {
            await window.DatasetCollector?.clearRaw?.();
            render();
        });
        _panel.querySelector('#llm-inspector-label').addEventListener('input', render);
        _panel.querySelector('#llm-inspector-status').addEventListener('input', render);
        _panel.querySelector('#llm-inspector-search').addEventListener('input', render);
        _panel.querySelector('#llm-inspector-list').addEventListener('click', onListClick);
    }

    async function toggle() {
        ensureUI();
        const show = _panel.style.display === 'none';
        _panel.style.display = show ? 'block' : 'none';
        if (show) render();
    }

    async function onListClick(ev) {
        const btn = ev.target.closest('button[data-copy]');
        if (!btn) return;
        const entry = _entries.find(x => x.key === btn.dataset.key);
        if (!entry) return;
        const isReq = btn.dataset.copy === 'req';
        const payload = isReq
            ? { url: entry.request?.url, method: entry.request?.method, headers: entry.request?.headers, body: entry.request?.body }
            : { status: entry.response?.status, headers: entry.response?.headers, body: entry.response?.body };
        try {
            await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
            const original = btn.textContent;
            btn.textContent = 'Copied ✓';
            setTimeout(() => { btn.textContent = original; }, 1200);
        } catch (e) {
            btn.textContent = 'Copy failed';
        }
    }

    async function render() {
        ensureUI();
        _entries = (await window.DatasetCollector?.getAllRaw?.()) || [];
        const labelF = (_panel.querySelector('#llm-inspector-label').value || '').toLowerCase();
        const statusF = (_panel.querySelector('#llm-inspector-status').value || '').trim();
        const searchF = (_panel.querySelector('#llm-inspector-search').value || '').toLowerCase();

        const rows = _entries.filter(e => {
            if (labelF && !String(e.label || '').toLowerCase().includes(labelF)) return false;
            if (statusF && String(e.response?.status ?? '') !== statusF) return false;
            if (searchF) {
                const hay = (_json(e.request?.body) + _json(e.response?.body)).toLowerCase();
                if (!hay.includes(searchF)) return false;
            }
            return true;
        });

        const countEl = _panel.querySelector('#llm-inspector-count');
        if (countEl) countEl.textContent = `${rows.length}/${_entries.length}`;

        const list = _panel.querySelector('#llm-inspector-list');
        if (!rows.length) {
            list.innerHTML = '<div style="color:var(--text-dim,#999);">No exchanges captured. Enable “Show Raw LLM” in Settings and make a call.</div>';
            return;
        }
        list.innerHTML = rows.map(e => {
            const status = e.response?.status ?? '—';
            const color = (status >= 200 && status < 300) ? '#6c6' : '#f66';
            const dur = e.duration_ms != null ? ` · ${e.duration_ms}ms` : '';
            const preStyle = 'white-space:pre-wrap;word-break:break-word;max-height:180px;overflow:auto;background:var(--bg-input,#111);padding:6px;border-radius:4px;margin:4px 0;';
            return `<details style="margin-bottom:6px;border:1px solid var(--border,#333);border-radius:4px;padding:6px;">
                <summary style="cursor:pointer;"><span style="color:${color};">●</span> ${_esc(e.label)} · ${_esc(e.model)} · ${_esc(status)}${_esc(dur)}</summary>
                ${_usageLine(e.response?.body)}
                <div style="display:flex;gap:6px;margin:6px 0;">
                    <button data-copy="req" data-key="${_esc(e.key)}">Copy request</button>
                    <button data-copy="res" data-key="${_esc(e.key)}">Copy response</button>
                </div>
                <div style="color:var(--text-dim,#999);">Request: POST ${_esc(e.request?.url)}</div>
                <pre style="${preStyle}">${_json({ headers: e.request?.headers, body: e.request?.body })}</pre>
                <div style="color:var(--text-dim,#999);">Response: ${_esc(status)} ${_esc(e.response?.statusText)}</div>
                <pre style="${preStyle}">${_json({ headers: e.response?.headers, body: e.response?.body })}</pre>
            </details>`;
        }).join('');
    }

    if (typeof window !== 'undefined') {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', ensureUI);
        } else {
            ensureUI();
        }
    }
})();
