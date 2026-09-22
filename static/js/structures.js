/**
 * Structure templates (task-357) — frontend.
 *
 * Capture a connected area group as a reusable, self-contained structure and
 * materialize saved structures into the running world. Backend:
 * GET/POST /api/structures*, engine/structures.py.
 *
 * Kept dependency-free (plain DOM) so it can be loaded before/after the Lit
 * modules without ordering constraints.
 */
(function () {
    'use strict';

    const BASE = '/api/structures';

    async function _req(url, options) {
        const resp = await fetch(url, options);
        let data = null;
        try { data = await resp.json(); } catch (e) { data = null; }
        if (!resp.ok) {
            throw new Error((data && data.error) || `${resp.status} ${resp.statusText}`);
        }
        return data;
    }

    function _log(text, cls) {
        if (window.events && typeof window.events.log === 'function') {
            window.events.log(text, cls || 'system-msg');
        }
    }

    function _el(tag, style, text) {
        const el = document.createElement(tag);
        if (style) el.setAttribute('style', style);
        if (text != null) el.textContent = text;
        return el;
    }

    function _overlay() {
        const overlay = _el('div',
            'position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:9000;display:flex;' +
            'align-items:center;justify-content:center;');
        overlay.addEventListener('click', (ev) => { if (ev.target === overlay) overlay.remove(); });
        document.body.appendChild(overlay);
        return overlay;
    }

    function _panel(title) {
        const panel = _el('div',
            'background:var(--bg-panel,#1e1e24);color:var(--text,#ddd);border:1px solid var(--border-light,#444);' +
            'border-radius:8px;min-width:340px;max-width:460px;padding:16px;font-size:13px;box-shadow:0 8px 30px rgba(0,0,0,0.5);');
        const h = _el('div', 'font-weight:600;font-size:14px;margin-bottom:10px;', title);
        panel.appendChild(h);
        return panel;
    }

    function _button(label, onClick) {
        const b = _el('button',
            'padding:5px 12px;border-radius:5px;border:1px solid var(--border-light,#555);' +
            'background:var(--bg-inset,#2a2a32);color:inherit;cursor:pointer;font-size:12px;', label);
        b.addEventListener('click', onClick);
        return b;
    }

    const Structures = {
        list() { return _req(BASE); },
        preview(areaId, opts) {
            return _req(`${BASE}/preview`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(Object.assign({ area_id: areaId }, opts || {})),
            });
        },
        save(areaId, name, opts) {
            return _req(`${BASE}/save`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(Object.assign({ area_id: areaId, name }, opts || {})),
            });
        },
        materialize(id, opts) {
            return _req(`${BASE}/${encodeURIComponent(id)}/materialize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(opts || {}),
            });
        },
        remove(id) { return _req(`${BASE}/${encodeURIComponent(id)}`, { method: 'DELETE' }); },

        /** Save dialog for one area (boundary graft point is hand-added later). */
        openSaveDialog(areaId, areaName) {
            if (!areaId) { _log('No area selected.', 'error-msg'); return; }
            const overlay = _overlay();
            const panel = _panel(`📦 Save structure — ${areaName || areaId}`);

            const nameRow = _el('div', 'margin-bottom:8px;');
            nameRow.appendChild(_el('div', 'font-size:11px;color:var(--text-muted);margin-bottom:3px;', 'Structure name'));
            const nameInput = document.createElement('input');
            nameInput.type = 'text';
            nameInput.value = areaName || 'structure';
            nameInput.setAttribute('style',
                'width:100%;padding:5px 8px;border-radius:5px;border:1px solid var(--border-light,#555);' +
                'background:var(--bg-inset,#2a2a32);color:inherit;font-size:12px;');
            nameRow.appendChild(nameInput);
            panel.appendChild(nameRow);

            const optsRow = _el('div', 'display:flex;gap:14px;margin:8px 0;font-size:12px;');
            const itemsWrap = _el('label', 'display:flex;align-items:center;gap:5px;cursor:pointer;');
            const itemsCb = document.createElement('input'); itemsCb.type = 'checkbox'; itemsCb.checked = true;
            itemsWrap.appendChild(itemsCb); itemsWrap.appendChild(document.createTextNode('Include items'));
            const charsWrap = _el('label', 'display:flex;align-items:center;gap:5px;cursor:pointer;');
            const charsCb = document.createElement('input'); charsCb.type = 'checkbox'; charsCb.checked = false;
            charsWrap.appendChild(charsCb); charsWrap.appendChild(document.createTextNode('Include residents'));
            optsRow.appendChild(itemsWrap); optsRow.appendChild(charsWrap);
            panel.appendChild(optsRow);

            const previewBox = _el('div',
                'background:var(--bg-inset,#2a2a32);border-radius:5px;padding:8px;min-height:38px;' +
                'font-size:11px;color:var(--text-muted);white-space:pre-wrap;margin-bottom:12px;', 'Preview…');
            panel.appendChild(previewBox);

            const buttons = _el('div', 'display:flex;justify-content:flex-end;gap:8px;');

            const runPreview = async () => {
                try {
                    const p = await Structures.preview(areaId, {
                        include_items: itemsCb.checked, include_characters: charsCb.checked,
                    });
                    const lines = [
                        `${p.areas} area(s), ${p.ways} way(s), ${p.items} item(s), ${p.residents} resident(s)`,
                    ];
                    if (p.boundary_exits && p.boundary_exits.length) {
                        lines.push(`Boundary exits (graft manually): ${p.boundary_exits.length}`);
                    }
                    previewBox.textContent = lines.join('\n');
                } catch (e) {
                    previewBox.textContent = `Preview failed: ${e.message}`;
                }
            };
            itemsCb.addEventListener('change', runPreview);
            charsCb.addEventListener('change', runPreview);

            buttons.appendChild(_button('Cancel', () => overlay.remove()));
            buttons.appendChild(_button('Preview', runPreview));
            buttons.appendChild(_button('Save', async () => {
                try {
                    const res = await Structures.save(areaId, nameInput.value.trim() || areaName, {
                        include_items: itemsCb.checked, include_characters: charsCb.checked,
                    });
                    _log(`📦 Saved structure "${res.name}" (${res.areas} areas, ${res.residents} residents).`, 'system-msg');
                    overlay.remove();
                } catch (e) {
                    previewBox.textContent = `Save failed: ${e.message}`;
                }
            }));
            panel.appendChild(buttons);
            overlay.appendChild(panel);
            runPreview();
        },

        /** Browse saved structures and materialize one into the live world. */
        async openBrowseDialog() {
            const overlay = _overlay();
            const panel = _panel('📦 Structures');
            const listBox = _el('div', 'max-height:320px;overflow:auto;margin-bottom:12px;', 'Loading…');
            panel.appendChild(listBox);

            const render = (entries) => {
                listBox.textContent = '';
                if (!entries.length) {
                    listBox.textContent = 'No structures saved yet. Right-click an area → “Save as Structure…”.';
                    listBox.setAttribute('style', 'font-size:12px;color:var(--text-muted);');
                    return;
                }
                listBox.setAttribute('style', 'max-height:320px;overflow:auto;margin-bottom:12px;');
                entries.forEach((entry) => {
                    const row = _el('div',
                        'display:flex;align-items:center;gap:8px;padding:6px 4px;border-bottom:1px solid var(--border-light,#333);');
                    const info = _el('div', 'flex:1;min-width:0;');
                    info.appendChild(_el('div', 'font-weight:600;font-size:12px;', entry.name || entry.id));
                    info.appendChild(_el('div', 'font-size:10px;color:var(--text-muted);',
                        `${entry.areas} areas · ${entry.ways} ways · ${entry.items} items · ${entry.residents} residents`));
                    row.appendChild(info);
                    row.appendChild(_button('Materialize', async () => {
                        try {
                            const report = await Structures.materialize(entry.id, {});
                            const m = report.materialized || {};
                            _log(`📦 Materialized "${entry.name}" — ${m.areas || 0} areas, ` +
                                 `${m.residents || 0} residents.`, 'system-msg');
                            (report.minted_residents || []).forEach((r) => {
                                _log(`⚠ Resident "${r.from}" imported as "${r.to}" (name already in world).`, 'system-msg');
                            });
                            if (window.worldSync && window.worldSync.refresh) window.worldSync.refresh();
                        } catch (e) {
                            _log(`Materialize failed: ${e.message}`, 'error-msg');
                        }
                    }));
                    row.appendChild(_button('🗑', async () => {
                        try { await Structures.remove(entry.id); render(await Structures.list()); }
                        catch (e) { _log(`Delete failed: ${e.message}`, 'error-msg'); }
                    }));
                    listBox.appendChild(row);
                });
            };

            panel.appendChild((() => {
                const row = _el('div', 'display:flex;justify-content:flex-end;');
                row.appendChild(_button('Close', () => overlay.remove()));
                return row;
            })());
            overlay.appendChild(panel);

            try { render(await Structures.list()); }
            catch (e) { listBox.textContent = `Failed to load: ${e.message}`; }
        },
    };

    window.VW = window.VW || {};
    window.VW.structures = Structures;
    window.structures = Structures;
})();
