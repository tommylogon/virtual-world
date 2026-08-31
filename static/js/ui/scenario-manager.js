/**
 * scenario-manager.js — Scenario Manager modal (task-374).
 *
 * Lists data/scenarios/*.json with stats (rooms/characters/size/age),
 * and per scenario: Open (load with undo), Audit (validator on the file),
 * Duplicate, Rename, Delete. Opened from the Game menu.
 */

window.ScenarioManager = (() => {
    'use strict';

    let _overlay = null;
    let _list = [];

    function fmtSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    function fmtAge(ts) {
        const mins = Math.floor((Date.now() / 1000 - ts) / 60);
        if (mins < 1) return 'just now';
        if (mins < 60) return mins + 'm ago';
        const h = Math.floor(mins / 60);
        if (h < 24) return h + 'h ago';
        return Math.floor(h / 24) + 'd ago';
    }

    async function loadList() {
        try {
            const resp = await fetch('/api/scenarios');
            _list = await resp.json();
        } catch (e) {
            _list = [];
        }
        return _list;
    }

    function open() {
        if (_overlay) { close(); return; }
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:15000;';
        const box = document.createElement('div');
        box.style.cssText = 'background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:18px;width:640px;max-height:85vh;display:flex;flex-direction:column;gap:10px;';
        overlay.appendChild(box);
        document.body.appendChild(overlay);
        _overlay = overlay;

        const header = document.createElement('div');
        header.style.cssText = 'display:flex;justify-content:space-between;align-items:center;';
        const title = document.createElement('h3');
        title.style.cssText = 'margin:0;font-size:15px;';
        title.textContent = '🗂 Scenarios';
        const closeBtn = document.createElement('button');
        closeBtn.className = 'btn btn-sm';
        closeBtn.textContent = '\u2715';
        closeBtn.onclick = close;
        header.appendChild(title);
        header.appendChild(closeBtn);
        box.appendChild(header);

        const list = document.createElement('div');
        list.style.cssText = 'overflow-y:auto;max-height:60vh;display:flex;flex-direction:column;gap:6px;';
        box.appendChild(list);
        box.appendChild(scaffoldFooter(box));

        renderList(list);
    }

    function scaffoldFooter() {
        const foot = document.createElement('div');
        foot.style.cssText = 'display:flex;justify-content:space-between;align-items:center;font-size:10px;color:var(--text-muted);';
        const hint = document.createElement('span');
        hint.textContent = 'Opening a scenario REPLACES the current world (↩ Undo restores).';
        const refresh = document.createElement('button');
        refresh.className = 'btn btn-sm';
        refresh.textContent = '⟳ Refresh';
        refresh.onclick = () => { const list = _overlay && _overlay.querySelector('div[style*="max-height:60vh"]'); if (list) renderList(list); };
        foot.appendChild(hint);
        foot.appendChild(refresh);
        return foot;
    }

    async function renderList(container) {
        container.textContent = 'Loading…';
        const items = await loadList();
        container.textContent = '';
        if (!items.length) {
            const none = document.createElement('div');
            none.style.cssText = 'font-size:12px;color:var(--text-muted);padding:12px;';
            none.textContent = 'No scenario files found. Commit the current world or load one to create the first.';
            container.appendChild(none);
            return;
        }
        for (const sc of items) {
            const row = document.createElement('div');
            row.style.cssText = 'border:1px solid var(--border);border-radius:8px;padding:8px;display:flex;flex-direction:column;gap:6px;';
            const top = document.createElement('div');
            top.style.cssText = 'display:flex;align-items:center;gap:8px;flex-wrap:wrap;';
            const name = document.createElement('strong');
            name.textContent = sc.name;
            name.style.cssText = 'font-size:13px;';
            const stats = document.createElement('span');
            stats.style.cssText = 'font-size:10px;color:var(--text-dim);';
            stats.textContent = `🏠 ${sc.areas} · 🧍 ${sc.players} · ${fmtSize(sc.size)} · ${fmtAge(sc.modified)}`;
            const actions = document.createElement('div');
            actions.style.cssText = 'display:flex;gap:4px;flex-wrap:wrap;';
            actions.appendChild(btn('▶ Open', 'btn-green', async () => {
                await openScenario(sc, row);
            }));
            actions.appendChild(btn('🔬 Audit', '', async () => {
                await auditScenario(sc, row);
            }));
            actions.appendChild(btn('📋 Copy', '', async () => {
                const r = await fetch(`/api/scenarios/${encodeURIComponent(sc.name)}/duplicate`, { method: 'POST' });
                const j = await r.json();
                if (j.error) toastError(j.error); else toastInfo('Copied to "' + j.name + '".');
                renderList(container);
            }));
            actions.appendChild(btn('✏️ Rename', '', async () => {
                const nn = prompt('New name:', sc.name);
                if (!nn || nn === sc.name) return;
                const r = await fetch(`/api/scenarios/${encodeURIComponent(sc.name)}/rename`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: nn })
                });
                const j = await r.json();
                if (j.error) toastError(j.error); else toastInfo('Renamed to "' + j.name + '".');
                renderList(container);
            }));
            actions.appendChild(btn('🗑 Delete', 'btn-red', async () => {
                if (!confirm(`Delete scenario "${sc.name}"?`)) return;
                const r = await fetch(`/api/scenarios/${encodeURIComponent(sc.name)}`, { method: 'DELETE' });
                const j = await r.json();
                if (j.error) toastError(j.error); else toastInfo('Deleted.');
                renderList(container);
            }));
            top.appendChild(name);
            top.appendChild(stats);
            row.appendChild(top);
            row.appendChild(actions);
            container.appendChild(row);
        }
    }

    function btn(label, cls, onclick) {
        const b = document.createElement('button');
        b.className = 'btn btn-sm' + (cls ? ' ' + cls : '');
        b.style.cssText = 'font-size:10px;';
        b.textContent = label;
        b.onclick = onclick;
        return b;
    }

    async function openScenario(sc, row) {
        btn_guard(row, async () => {
            const resp = await fetch(`/api/scenarios/${encodeURIComponent(sc.name)}`);
            const data = await resp.json();
            if (data.error) { toastError(data.error); return; }
            data._scenario_name = data._scenario_name || sc.name;
            data.persist = true;  // GUI open: keep the scenario file as the source
            const r = await fetch('/api/load', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const j = await r.json();
            if (j.error) { toastError('Load failed: ' + j.error); return; }
            document.body.dataset.scenarioName = data._scenario_name;
            try { events.clearAll(); } catch (e) {}
            worldState.fetch();
            toastInfo('Opened scenario "' + data._scenario_name + '". Undo restores the previous world.');
            close();
        });
    }

    async function auditScenario(sc, row) {
        btn_guard(row, async () => {
            const resp = await fetch(`/api/scenarios/${encodeURIComponent(sc.name)}`);
            const data = await resp.json();
            if (data.error) { toastError(data.error); return; }
            const ar = await fetch('/api/import/audit', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const j = await ar.json();
            if (j.error) { toastError(j.error); return; }
            const sev = j.severities || {};
            const issues = j.issues || [];
            const out = `Audit "${sc.name}": ${j.count} issues` +
                (sev.error ? ` · ${sev.error} errors` : '') +
                (sev.warning ? ` · ${sev.warning} warnings` : '') +
                (sev.info ? ` · ${sev.info} info` : '') +
                (j.count === 0 ? ' — clean ✅' : '');
            (issues.length ? console.info : console.log)('[scenario-audit]', out, issues.slice(0, 5));
            toastInfo(out);
        });
    }

    async function btn_guard(row, fn) {
        try { await fn(); } catch (e) { console.error(e); toastError((e && e.message) || 'Action failed'); }
    }

    function close() {
        if (_overlay && _overlay.parentNode) _overlay.parentNode.removeChild(_overlay);
        _overlay = null;
    }

    return { open, close };
})();
