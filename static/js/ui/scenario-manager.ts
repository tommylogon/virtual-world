/**
 * scenario-manager.js — Scenario Manager modal (task-374).
 *
 * Lists data/scenarios/*.json with stats (rooms/characters/size/age),
 * and per scenario: Open (load with undo), Audit (validator on the file),
 * Duplicate, Rename, Delete. Opened from the Game menu.
 *
 * @module ui/scenario-manager — the Scenario Manager modal
 * @contributes ScenarioManager: list / Open / Audit / Duplicate / Rename / Delete scenarios
 * @powers Scenario creation, Save / load — managing the files in data/scenarios (task-374)
 * @relates opened from the Game menu; Open follows the scenario-dropdown path
 * @docs docs/virtualWorld/Scenario Workflows & UI Audit.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

(window as unknown as { ScenarioManager: unknown }).ScenarioManager = (() => {
    'use strict';

    let _overlay: HTMLElement | null = null;
    let _list: ScenarioSummary[] = [];
    let _counter: HTMLElement | null = null;

    // task-598: filter state survives repaints and ⟳ Refresh, so the list does
    // not silently reset when an action re-renders it.
    let _filterText = '';
    let _filterOpts: Record<string, string> = { modified: 'any', health: 'any', characters: 'any', areas: 'any' };

    function filterActive() {
        return !!_filterText.trim() || Object.keys(_filterOpts).some(k => _filterOpts[k] !== 'any');
    }

    // Multi-strategy match, consistent with the library browser's search:
    // substring on name + source path first, then per-token, then a fuzzy
    // fallback for close spellings (reuses the browser's fuzzyRatio when it is
    // loaded, with a substring-only fallback otherwise).
    function scenarioSearchScore(sc: ScenarioSummary) {
        const needle = _filterText.trim().toLowerCase();
        if (!needle) return 1;
        const name = String(sc.name || '').toLowerCase();
        const path = String(sc.filename || '').toLowerCase();
        const tokens = needle.split(/\s+/).filter(Boolean);
        let s = 0;
        if (name.includes(needle) || path.includes(needle)) s += 6;
        // task-641 kept: a bare number finds a scenario by exact area or
        // character count ("23" -> the scenario with 23 areas).
        if (/^\d+$/.test(needle) && (String(sc.areas) === needle || String(sc.players) === needle)) s += 6;
        tokens.forEach((t: string) => {
            if (name.includes(t) || path.includes(t)) s += 3;
        });
if (s === 0) {
            // fuzzyRatio lives on window (library browser) and is not declared
            // in static/js/types/globals.d.ts; the cast is inline so the emitted
            // `typeof window.fuzzyRatio === 'function'` guard is unchanged — a
            // nullish fallback would use a non-function truthy value and throw.
            const w = window as unknown as { fuzzyRatio?: (a: string, b: string) => number };
            const fuzzy: (a: string, b: string) => number =
                (typeof w.fuzzyRatio === 'function')
                    ? w.fuzzyRatio
                    : (a, b) => (!a || !b ? 0 : (a === b ? 1 : (a.includes(b) ? 0.7 : 0)));
            const fr = Math.max(fuzzy(name, needle), fuzzy(path, needle));
            if (fr >= 0.6) s += Math.round(fr * 6);
        }
        return s;
    }

    function scenarioMatchesFilters(sc: ScenarioSummary) {
        if (scenarioSearchScore(sc) === 0) return false;
        const o = _filterOpts;
        if (o.modified !== 'any') {
            const ageDays = (Date.now() / 1000 - Number(sc.modified)) / 86400;
            if (o.modified === 'today' && ageDays > 1) return false;
            if (o.modified === 'week' && ageDays > 7) return false;
            if (o.modified === 'month' && ageDays > 30) return false;
            if (o.modified === 'old' && ageDays <= 30) return false;
        }
        const h = sc.health || {};
        if (o.health === 'clean' && !(h.ok && !h.issues)) return false;
        if (o.health === 'issues' && !(h.ok && (h.issues ?? 0) > 0)) return false;
        if (o.health === 'broken' && h.ok) return false;
        if (o.characters === 'none' && sc.players > 0) return false;
        if (o.characters === 'some' && !(sc.players > 0)) return false;
        if (o.areas === 'none' && sc.areas > 0) return false;
        if (o.areas === 'some' && !(sc.areas > 0)) return false;
        return true;
    }

    function fmtSize(bytes: number) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    function fmtAge(ts: number) {
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

        // task-598: a text search over name + source path, plus dimension
        // filters, matching the library browser's search affordance rather than
        // a bare name filter. task-641 added the first text filter.
        const filterRow = document.createElement('div');
        filterRow.style.cssText = 'display:flex;gap:6px;align-items:center;';
        const filter = document.createElement('input');
        filter.type = 'text';
        filter.placeholder = 'Search name or source path…';
        filter.setAttribute('aria-label', 'Search scenarios by name or source path');
        filter.style.cssText = 'flex:1;font-size:12px;padding:5px 8px;background:var(--bg-input,transparent);color:inherit;border:1px solid var(--border);border-radius:6px;';
        filter.value = _filterText;
        const counter = document.createElement('span');
        counter.style.cssText = 'font-size:10px;color:var(--text-dim);white-space:nowrap;';
        _counter = counter;
        filter.addEventListener('input', () => { _filterText = filter.value; renderList(list); });
        filterRow.appendChild(filter);
        filterRow.appendChild(counter);
        box.appendChild(filterRow);

        // Dimension filters: each is a value the manager already knows.
        const controls = document.createElement('div');
        controls.style.cssText = 'display:flex;gap:6px;flex-wrap:wrap;align-items:center;';
        const mkSelect = (key: string, label: string, options: Array<[string, string]>) => {
            const wrap = document.createElement('label');
            wrap.style.cssText = 'font-size:10px;color:var(--text-dim);display:flex;align-items:center;gap:3px;';
            wrap.textContent = label + ':';
            const sel = document.createElement('select');
            sel.style.cssText = 'font-size:11px;padding:3px 6px;background:var(--bg-input,transparent);color:inherit;border:1px solid var(--border);border-radius:6px;';
            sel.setAttribute('aria-label', label);
            options.forEach(([value, text]) => {
                const o = document.createElement('option');
                o.value = value;
                o.textContent = text;
                sel.appendChild(o);
            });
            sel.value = _filterOpts[key];
            sel.addEventListener('change', () => { _filterOpts[key] = sel.value; renderList(list); });
            wrap.appendChild(sel);
            return wrap;
        };
        controls.appendChild(mkSelect('modified', 'Modified', [
            ['any', 'any time'], ['today', 'today'], ['week', 'last 7 days'],
            ['month', 'last 30 days'], ['old', 'older than 30 days']]));
        controls.appendChild(mkSelect('health', 'Health', [
            ['any', 'any'], ['clean', 'clean'], ['issues', 'has issues'], ['broken', "won't parse"]]));
        controls.appendChild(mkSelect('characters', 'Characters', [
            ['any', 'any'], ['none', 'none'], ['some', 'has characters']]));
        controls.appendChild(mkSelect('areas', 'Areas', [
            ['any', 'any'], ['none', 'none'], ['some', 'has areas']]));
        const reset = document.createElement('button');
        reset.className = 'btn btn-sm';
        reset.style.cssText = 'font-size:10px;';
        reset.textContent = 'Reset';
        reset.onclick = () => {
            _filterText = '';
            _filterOpts = { modified: 'any', health: 'any', characters: 'any', areas: 'any' };
            filter.value = '';
            controls.querySelectorAll<HTMLSelectElement>('select').forEach(s => { s.value = 'any'; });
            renderList(list);
        };
        controls.appendChild(reset);
        box.appendChild(controls);

        box.appendChild(scaffoldFooter(box));

        renderList(list);
        // Keep typing focused when the list repaints, so filtering does not
        // steal the caret on every keystroke.
        filter.focus();
    }

    function scaffoldFooter(_box: HTMLElement) {
        const foot = document.createElement('div');
        foot.style.cssText = 'display:flex;justify-content:space-between;align-items:center;font-size:10px;color:var(--text-muted);';
        const hint = document.createElement('span');
        hint.textContent = 'Opening a scenario REPLACES the current world (↩ Undo restores).';
        const refresh = document.createElement('button');
        refresh.className = 'btn btn-sm';
        refresh.textContent = '⟳ Refresh';
        refresh.onclick = () => { const list = _overlay && _overlay.querySelector<HTMLElement>('div[style*="max-height:60vh"]'); if (list) renderList(list); };
        foot.appendChild(hint);
        foot.appendChild(refresh);
        return foot;
    }

    async function renderList(container: HTMLElement) {
        container.textContent = 'Loading…';
        const all = await loadList();
        const items = all.filter(scenarioMatchesFilters);
        if (_counter) {
            _counter.textContent = filterActive()
                ? `${items.length} of ${all.length}`
                : `${all.length} scenario${all.length === 1 ? '' : 's'}`;
        }
        container.textContent = '';
        if (!all.length) {
            const none = document.createElement('div');
            none.style.cssText = 'font-size:12px;color:var(--text-muted);padding:12px;';
            none.textContent = 'No scenario files found. Commit the current world or load one to create the first.';
            container.appendChild(none);
            return;
        }
        if (!items.length) {
            // The registry is populated but nothing matched the filter. Say so
            // distinctly from "no scenarios exist", or the list looks broken.
            const none = document.createElement('div');
            none.style.cssText = 'font-size:12px;color:var(--text-muted);padding:12px;';
            none.textContent = _filterText.trim()
                ? `No scenario matches “${_filterText}”.`
                : 'No scenario matches the current filters.';
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
            stats.style.cssText = 'font-size:10px;color:var(--text-dim);display:flex;gap:8px;align-items:center;';
            // task-641: these counts were ONE flat string, so the row read
            // '<house glyph> 23 <dot> <sprout glyph> 21 <dot> 376.3 KB <dot> 1d ago' and the two
            // numbers had to be decoded from glyphs alone. The top bar already discloses
            // by title ('Next forecast change', 'Scenario source'), so each count becomes
            // its own element carrying the same affordance. Glyphs are taken from the
            // original bytes so the mojibake in this file is preserved exactly.
const stat = (glyph: string, value: unknown, label: string): HTMLSpanElement => {
                        const s = document.createElement('span');
                        s.title = label;
                        s.textContent = glyph ? glyph + ' ' + String(value) : String(value);
                        return s;
                    };
            const HOUSE = String.fromCharCode(0xD83C, 0xDFE0);
            const SPROUT = String.fromCharCode(0xD83C, 0xDF3F);
            stats.appendChild(stat(HOUSE, sc.areas, sc.areas + ' area' + (sc.areas === 1 ? '' : 's')));
            stats.appendChild(stat(SPROUT, sc.players, sc.players + ' character' + (sc.players === 1 ? '' : 's')));
            stats.appendChild(stat('', fmtSize(Number(sc.size)), 'File size on disk'));
            stats.appendChild(stat('', fmtAge(Number(sc.modified)), 'Last modified'));
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

    function btn(label: string, cls: string, onclick: () => void) {
        const b = document.createElement('button');
        b.className = 'btn btn-sm' + (cls ? ' ' + cls : '');
        b.style.cssText = 'font-size:10px;';
        b.textContent = label;
        b.onclick = onclick;
        return b;
    }

    async function openScenario(sc: ScenarioSummary, row: HTMLElement) {
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

    async function auditScenario(sc: ScenarioSummary, row: HTMLElement) {
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

    async function btn_guard(_row: HTMLElement, fn: () => Promise<void>) {
        try { await fn(); } catch (e) {
            console.error(e);
            toastError((e instanceof Error ? e.message : String(e)) || 'Action failed');
        }
    }

    function close() {
        if (_overlay && _overlay.parentNode) _overlay.parentNode.removeChild(_overlay);
        _overlay = null;
    }

    return { open, close };
})();


// NOTE: this declaration sits AFTER the first value statement on purpose. A
// leading `interface`/`type` makes TypeScript drop the file's leading JSDoc
// block from the emitted .js, and tools/js_module_index.py reads the `@module`
// tag out of that emitted .js.

/** One row of GET /api/scenarios. */
interface ScenarioSummary {
    name: string;
    filename?: string;
    size?: number | string;
    modified?: number | string;
    areas: number;
    players: number;
    health?: { ok?: boolean; issues?: number };
}
