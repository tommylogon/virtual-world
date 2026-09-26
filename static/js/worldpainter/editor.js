/**
 * editor.js — WorldPainter 3-mode grid editor (task-495).
 *
 * A plain-DOM overlay (no Lit, no ordering constraints) that renders one world
 * scope's authoring grid at its own resolution and lets the author:
 *   - select a scope and drill into its children (recursive scope grids);
 *   - set/resize the grid and pick its mode (world / town / interior);
 *   - paint cells on the biome / road / elevation layers;
 *   - place, move, and remove feature (child-scope) placements.
 *
 * Backend: `routes/world_grid_ops.py` (`GET/POST /api/world/scopes/<id>/grid*`).
 * The pure view-model lives in `static/js/worldpainter/grid-model.js`; every
 * mutation POSTs and re-renders from the server response so the editor never
 * holds a divergent copy of the manifest.
 *
 * Overlap follows the documented rule (`engine/world_grid.py`): forbidden by
 * default, with an explicit "displace" confirmation.
 *
 * @module worldpainter/editor — WorldPainter grid editing overlay
 * @contributes the 3-mode scope grid editor UI: paint, feature place/move/remove, drill-down
 * @powers WorldPainter authored worlds (task-495) feeding the grid-to-graph compiler (task-496)
 * @relates static/js/worldpainter/grid-model.js; routes/world_grid_ops.py; engine/world_grid.py
 * @docs docs/design/worldpainter-knowledge-and-fog.md
 */
(function () {
    'use strict';

    const BASE = '/api/world/scopes';
    const CELL = 22;           // base px per cell at scale 1
    const MIN_SCALE = 0.12;
    const MAX_SCALE = 6;
    // main.js reloads the VW namespace last, so prefer the bare global it keeps.
    const GM = () => window.gridModel || window.VW.gridModel;

    const state = {
        scopeId: null,
        payload: null,
        tool: 'paint',
        layer: 'biome',
        value: 'sparse_forest',
        brush: 1,
        paintAlpha: 0.75,
        stroke: [],
        stroking: false,
        strokeLayer: null,
        strokeValue: null,
        spaceDown: false,
        vocab: null,
        backgrounds: null,
        refImage: null,
        refNode: null,
        refEdit: false,       // adjust mode: move/resize/crop the reference image
        refDrag: null,        // {kind, key, start, rect, crop} during a ref edit
        selectedChild: null,
        merge: false,
        view: null,            // {scale} — Konva owns the live transform
        route: [],             // waypoints for the route/trail tool
        stage: null,
        shapes: null,
        gridHolder: null,
        routeInfoEl: null,
        overlay: null,
        body: null,
        status: '',
        statusError: false,
    };

    // ───────────────────────────── dom/net ─────────────────────────────

    function _el(tag, style, text) {
        const el = document.createElement(tag);
        if (style) el.setAttribute('style', style);
        if (text != null) el.textContent = text;
        return el;
    }

    function _btn(label, onClick, style, title) {
        const b = _el('button', 'cursor:pointer;border:1px solid var(--border,#444);' +
            'background:var(--bg-card,#2a2a32);color:var(--text,#ddd);border-radius:5px;' +
            'padding:3px 8px;font-size:12px;' + (style || ''), label);
        if (title) b.title = title;
        b.addEventListener('click', onClick);
        return b;
    }

    async function _req(url, options) {
        const resp = await fetch(url, options);
        let data = null;
        try { data = await resp.json(); } catch (e) { data = null; }
        if (!resp.ok) throw new Error((data && data.error) || `${resp.status} ${resp.statusText}`);
        return data;
    }

    function _log(text, cls) {
        if (window.events && typeof window.events.log === 'function') {
            window.events.log(text, cls || 'system-msg');
        }
    }

    function _notify(worldChanged) {
        if (worldChanged && window.worldSync && typeof window.worldSync.refresh === 'function') {
            window.worldSync.refresh();
        }
    }

    const _post = (path, body) => _req(BASE + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {}),
    });

    // ───────────────────────────── open/close ──────────────────────────

    async function ensureVocab() {
        if (state.vocab) return state.vocab;
        try {
            state.vocab = await _req('/api/world/painter/vocabulary', { cache: 'no-store' });
        } catch (e) {
            // The editor still works without it (free-text values), just no dropdown.
            state.vocab = { biomes: [], features: [], layers: GM().PAINT_LAYERS, modes: GM().MODES };
        }
        return state.vocab;
    }

    async function ensureBackgrounds() {
        if (state.backgrounds) return state.backgrounds;
        try {
            state.backgrounds = (await _req('/api/world/painter/backgrounds',
                { cache: 'no-store' })).images || [];
        } catch (e) {
            state.backgrounds = [];
        }
        return state.backgrounds;
    }

    function _layerOptions(layer) {
        if (!state.vocab) return [];
        if (layer === 'biome') return state.vocab.biomes || [];
        if (layer === 'road') return state.vocab.features || [];
        return [];
    }

    function _defaultValueForLayer(layer) {
        if (layer === 'elevation') return '0.5';
        const options = _layerOptions(layer);
        if (!options.length) return '';
        const preferred = { biome: 'sparse_forest', road: 'road' }[layer];
        if (preferred && options.some((o) => o.id === preferred)) return preferred;
        return options[0].id;
    }

    async function open(scopeId) {
        if (state.overlay && document.body.contains(state.overlay)) {
            state.overlay.remove();
        }
        const overlay = _el('div',
            'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9500;display:flex;' +
            'align-items:center;justify-content:center;');
        overlay.addEventListener('click', (ev) => { if (ev.target === overlay) close(); });
        const panel = _el('div',
            'background:var(--bg-panel,#1b1b21);color:var(--text,#ddd);border:1px solid ' +
            'var(--border,#444);border-radius:10px;width:min(1000px,94vw);max-height:92vh;' +
            'display:flex;flex-direction:column;padding:14px;font-size:13px;box-shadow:0 12px 40px rgba(0,0,0,0.55);');
        panel.setAttribute('data-role', 'worldpainter');
        state.overlay = overlay;
        state.body = panel;
        overlay.appendChild(panel);
        document.body.appendChild(overlay);
        _bindKeys();

        await ensureVocab();
        await ensureBackgrounds();
        if (scopeId) {
            state.scopeId = scopeId;
            load(scopeId);
        } else {
            showChooser();
        }
    }

    function close() {
        _unbindKeys();
        if (state.overlay) state.overlay.remove();
        state.overlay = null;
        state.payload = null;
    }

    /** Space = pan, so left-drag is free for painting. */
    function _bindKeys() {
        _unbindKeys();
        state._keyDown = (e) => {
            if (e.code !== 'Space' || state.spaceDown) return;
            state.spaceDown = true;
            if (state.stage) state.stage.draggable(true);
            e.preventDefault();
        };
        state._keyUp = (e) => {
            if (e.code !== 'Space') return;
            state.spaceDown = false;
            if (state.stage) state.stage.draggable(!_isPaintTool());
        };
        document.addEventListener('keydown', state._keyDown);
        document.addEventListener('keyup', state._keyUp);
    }

    function _unbindKeys() {
        if (state._keyDown) document.removeEventListener('keydown', state._keyDown);
        if (state._keyUp) document.removeEventListener('keyup', state._keyUp);
        state._keyDown = null;
        state._keyUp = null;
        state.spaceDown = false;
    }

    // ───────────────────────────── loading ─────────────────────────────

    async function showChooser() {
        state.scopeId = null;
        state.payload = null;
        const box = _renderShell('🗺️ WorldPainter');
        box.appendChild(_el('div', 'color:var(--text-muted,#999);margin-bottom:10px;',
            'Choose a scope to open its grid.'));
        const list = _el('div', 'display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;', 'Loading…');
        box.appendChild(list);
        box.appendChild(_btn('➕ New root scope', () => _promptNewScope(null)));
        try {
            const root = await _req(BASE, { cache: 'no-store' });
            list.textContent = '';
            const scopes = root.children || [];
            if (!scopes.length) {
                list.appendChild(_el('div', 'color:var(--text-muted,#999);',
                    'No scopes yet. Create one to start painting.'));
                return;
            }
            scopes.forEach((card) => list.appendChild(_scopeCard(card)));
        } catch (e) {
            list.textContent = `Failed to load scopes: ${e.message}`;
        }
    }

    function _scopeCard(card, onOpen) {
        const el = _el('div',
            'border:1px solid var(--border,#444);border-radius:8px;padding:8px 10px;' +
            'min-width:150px;cursor:pointer;background:var(--bg-card,#24242b);');
        const head = _el('div', 'display:flex;align-items:center;gap:6px;');
        head.appendChild(_el('span', 'font-weight:600;flex:1 1 auto;', card.name || card.id));
        head.appendChild(_iconBtn('✏️', 'Rename scope', () => renameScope(card.id, card.name)));
        head.appendChild(_iconBtn('🗑', 'Delete scope', () => deleteScope(card.id, card.name)));
        el.appendChild(head);
        el.appendChild(_el('div', 'font-size:10px;color:var(--text-muted,#999);',
            `${card.kind || 'scope'} · ${card.state || ''}${card.mode ? ' · ' + card.mode : ''}`));
        el.addEventListener('click', () => (onOpen ? onOpen(card) : load(card.id)));
        return el;
    }

    /** Small icon button that doesn't trigger the card's own click. */
    function _iconBtn(label, title, onClick) {
        const b = _el('button',
            'cursor:pointer;border:1px solid var(--border,#444);background:transparent;' +
            'color:var(--text,#ddd);border-radius:5px;padding:1px 5px;font-size:11px;line-height:1.2;',
            label);
        b.title = title;
        b.addEventListener('click', (e) => { e.stopPropagation(); onClick(); });
        return b;
    }

    async function load(scopeId) {
        state.scopeId = scopeId;
        state.selectedChild = null;
        state.view = null;      // a new scope opens fitted
        state.route = [];
        state.refEdit = false;  // reference adjust is per-scope
        state.refDrag = null;
        const box = _renderShell('🗺️ WorldPainter');
        box.appendChild(_el('div', 'color:var(--text-muted,#999);', 'Loading grid…'));
        try {
            state.payload = await _req(`${BASE}/${encodeURIComponent(scopeId)}/grid`,
                { cache: 'no-store' });
            render();
        } catch (e) {
            box.textContent = '';
            box.appendChild(_el('div', 'color:#e66;', `Failed to load grid: ${e.message}`));
        }
    }

    /**
     * Refetch the open scope's payload in place. Used after a rename/delete of a
     * scope that appears as a *card* in this scope's list: the card's name comes
     * from the payload, so redrawing it without refetching showed the pre-edit
     * list. Unlike `load()` this keeps the author's view and selection.
     */
    async function _reloadPayload() {
        if (!state.scopeId) return;
        state.payload = await _req(`${BASE}/${encodeURIComponent(state.scopeId)}/grid`,
            { cache: 'no-store' });
        render();
    }

    /** Shared header (title + close) and a fresh body container. */
    function _renderShell(title) {
        const panel = state.body;
        panel.textContent = '';
        const head = _el('div', 'display:flex;align-items:center;gap:10px;margin-bottom:10px;');
        head.appendChild(_el('div', 'font-weight:700;font-size:15px;', title));
        const spacer = _el('div', 'flex:1;');
        head.appendChild(spacer);
        head.appendChild(_btn('Close', close));
        panel.appendChild(head);
        const box = _el('div', 'overflow:auto;');
        panel.appendChild(box);
        return box;
    }

    // ───────────────────────────── rendering ───────────────────────────

    function render() {
        const p = state.payload;
        if (!p) return showChooser();
        state.routeInfoEl = null;   // the old HUD element dies with the panel
        const box = _renderShell('🗺️ WorldPainter');

        box.appendChild(_breadcrumb(p.breadcrumb));
        box.appendChild(_toolbar(p));

        if (!p.scope.has_grid) {
            box.appendChild(_noGridPanel(p));
            _renderChildren(box, p);
            return;
        }

        box.appendChild(_featureBar(p));
        box.appendChild(_grid(p));
        _renderChildren(box, p);
        if (state.status) {
            const color = state.statusError ? '#e66' : '#9c9';
            const status = _el('div', `margin-top:8px;font-size:12px;color:${color};`, state.status);
            status.setAttribute('data-role', 'wp-status');
            box.appendChild(status);
        }
    }

    function _breadcrumb(trail) {
        const row = _el('div', 'margin-bottom:8px;font-size:12px;display:flex;gap:6px;flex-wrap:wrap;');
        (trail || []).forEach((node, i) => {
            if (i) row.appendChild(_el('span', 'color:var(--text-muted,#888);', '›'));
            const link = _el('a', 'cursor:pointer;color:#7ab;', node.name);
            link.addEventListener('click', () => load(node.id));
            row.appendChild(link);
        });
        return row;
    }

    function _toolbar(p) {
        const wrap = _el('div', 'display:flex;flex-wrap:wrap;gap:8px;align-items:center;' +
            'padding:8px;border:1px solid var(--border,#3a3a44);border-radius:8px;margin-bottom:8px;');

        const modeBadge = _el('span',
            'font-size:11px;padding:2px 8px;border-radius:10px;background:#2d4a6b;color:#cfe;',
            `mode: ${p.mode || 'unset'}`);
        wrap.appendChild(modeBadge);

        const tools = [['paint', '🖌 Paint'], ['erase', '🧽 Erase'],
            ['route', '🧭 Route'], ['feature', '🏠 Feature']];
        tools.forEach(([id, label]) => {
            const btn = _btn(label, () => { state.tool = id; render(); },
                state.tool === id ? 'outline:2px solid #7ab;' : '');
            if (id === 'route') {
                btn.title = 'Click waypoints, then ✓ Paint route — paints the '
                    + 'current layer along the line (1 cell = 1 turn).';
            } else if (id === 'feature') {
                btn.title = 'Place a sub-zone (child scope) at a cell — not a '
                    + 'road. Roads/bridges are painted on the road layer.';
            }
            wrap.appendChild(btn);
        });

        wrap.appendChild(_el('span', 'font-size:12px;color:var(--text-muted,#999);',
            'layer'));
        const layerSel = _el('select', 'padding:3px;border-radius:5px;');
        layerSel.setAttribute('data-role', 'wp-layer');
        layerSel.title = 'Which layer you paint: biome, road or elevation. '
            + 'Roads, bridges and fords are on the road layer.';
        GM().PAINT_LAYERS.forEach((l) => {
            const opt = _el('option', null, l);
            opt.value = l;
            if (l === state.layer) opt.selected = true;
            layerSel.appendChild(opt);
        });
        layerSel.addEventListener('change', () => {
            state.layer = layerSel.value;
            state.value = _defaultValueForLayer(state.layer);
            render();
        });
        wrap.appendChild(layerSel);
        wrap.appendChild(_valueControl());

        // Brush size: paints an N×N block per click — the difference between a
        // forest being 8 clicks or 800. Also widens a route/trail.
        wrap.appendChild(_el('span', 'font-size:12px;color:var(--text-muted,#999);', 'brush'));
        const brushSel = _el('select', 'padding:3px;border-radius:5px;');
        brushSel.setAttribute('data-role', 'wp-brush');
        [1, 2, 3, 5, 8, 12].forEach((n) => {
            const opt = _el('option', null, `${n}×${n}`);
            opt.value = String(n);
            if (n === state.brush) opt.selected = true;
            brushSel.appendChild(opt);
        });
        brushSel.addEventListener('change', () => { state.brush = parseInt(brushSel.value, 10) || 1; });
        wrap.appendChild(brushSel);

        wrap.appendChild(_btn('▦ Grid…', () => _openGridDialog(p)));
        wrap.appendChild(_btn('➕ Add feature…', () => _promptNewScope(p.scope.id)));

        // Compile the painted grid into real area/way nodes (task-496/398).
        const merge = _el('input');
        merge.type = 'checkbox';
        merge.checked = !!state.merge;
        merge.setAttribute('data-role', 'wp-merge');
        merge.addEventListener('change', () => { state.merge = merge.checked; render(); });
        wrap.appendChild(merge);
        wrap.appendChild(_el('span', 'font-size:12px;color:var(--text-muted,#999);',
            'merge same-biome'));

        // Node-cost estimate, so painting 5,000 cells can't surprise the author
        // with a 15,000-node graph ("the laptop killer").
        const est = GM().estimateCompile(p, state.merge);
        const estEl = _el('span', 'font-size:11px;color:'
            + (est.total > 3000 ? '#c96' : 'var(--text-muted,#999)') + ';',
            `≈ ${est.areas} areas · ${est.ways} ways`
            + (est.links ? ` · 🔗 ${est.links} linked` : ''));
        estEl.title = est.links
            ? `${est.links} island(s) have no painted neighbour; each is joined to the `
              + 'nearest painted cell with a single way (not one per neighbour).'
            : 'Areas and ways this grid will compile to';
        estEl.setAttribute('data-role', 'wp-estimate');
        wrap.appendChild(estEl);
        wrap.appendChild(_btn('⚙ Generate', () => generate(), 'outline:1px solid #7ab;'));
        wrap.appendChild(_btn('🧹 Ungenerate', () => ungenerate(),
            'color:#c96;', 'Delete this zone\'s generated nodes but keep its painted grid, so you can regenerate a clean slate.'));

        wrap.appendChild(_btn('⟳', () => load(state.scopeId)));
        return wrap;
    }

    function _valueControl() {
        const options = _layerOptions(state.layer);
        if (state.layer === 'elevation' || !options.length) {
            // No vocabulary (fetch failed) or a numeric layer: free text.
            const input = _el('input',
                'width:130px;padding:3px 6px;border-radius:5px;border:1px solid ' +
                'var(--border,#444);background:var(--bg-card,#2a2a32);color:var(--text,#ddd);');
            input.setAttribute('data-role', 'wp-value');
            input.value = state.value;
            input.placeholder = state.layer === 'elevation' ? '0..1' : 'value';
            input.title = `Value painted on the ${state.layer} layer.`;
            input.addEventListener('input', () => { state.value = input.value; });
            return input;
        }
        // A real id, not free text — a mistyped biome silently compiles a barren
        // area, so the valid ids are the only choices.
        const sel = _el('select', 'padding:3px;border-radius:5px;min-width:160px;');
        sel.setAttribute('data-role', 'wp-value');
        const ids = options.map((o) => o.id);
        if (ids.indexOf(state.value) < 0) state.value = ids[0];
        options.forEach((o) => {
            const opt = _el('option', null, `${o.name} (${o.id})`);
            opt.value = o.id;
            sel.appendChild(opt);
        });
        sel.value = state.value;
        sel.title = `Value painted on the ${state.layer} layer.`;
        sel.addEventListener('change', () => { state.value = sel.value; });
        return sel;
    }

    function generate() {
        const p = state.payload;
        const est = GM().estimateCompile(p, state.merge);
        if (est.total > 3000 && !window.confirm(
            `This will create about ${est.areas} areas and ${est.ways} ways `
            + `(${est.total} nodes).\n\nThe graph view may become unresponsive. `
            + `Consider "merge same-biome", or generating smaller zones.\n\nContinue?`)) {
            return;
        }
        const body = { region_merge: !!state.merge };
        const run = async (allowRegenerate) => {
            try {
                const result = await _post(
                    `/${encodeURIComponent(p.scope.id)}/grid/generate`,
                    allowRegenerate ? { ...body, allow_regenerate: true } : body);
                state.payload = result;
                state.selectedChild = null;
                _notify(true);
                const r = result.report || {};
                const notes = (r.notes || []).join('; ');
                _status(`⚙ Generated ${r.node_count || 0} node(s), ` +
                    `${r.edge_count || 0} edge(s)` +
                    (notes ? ` — ${notes}` : ''), false);
            } catch (e) {
                if (!allowRegenerate && /already materialized/.test(e.message)
                        && window.confirm(`${e.message}\n\nRe-run generation?`)) {
                    return run(true);
                }
                _status(`Generate failed: ${e.message}`, true);
            }
        };
        return run(false);
    }

    function ungenerate() {
        const p = state.payload;
        if (!p || !p.scope) return;
        if (!window.confirm(
                `Delete every generated node for “${p.scope.name}”?\n\n` +
                `The painted grid, reference and placements are kept, and the scope `
                + `returns to unmade so you can ⚙ Generate again.`)) {
            return;
        }
        (async () => {
            try {
                const result = await _post(
                    `/${encodeURIComponent(p.scope.id)}/grid/ungenerate`, {});
                state.payload = result;
                state.selectedChild = null;
                _notify(true);
                _status(`🧹 Removed ${result.deleted_nodes || 0} generated node(s) — grid kept.`, false);
            } catch (e) {
                _status(`Ungenerate failed: ${e.message}`, true);
            }
        })();
    }

    function _noGridPanel(p) {
        const box = _el('div', 'padding:14px;border:1px dashed var(--border,#555);' +
            'border-radius:8px;margin-bottom:10px;color:var(--text-muted,#999);',
            'This scope has no grid yet.');
        box.appendChild(_el('div', null, ' '));
        box.appendChild(_btn('▦ Create grid…', () => _openGridDialog(p)));
        return box;
    }

    function _featureBar(p) {
        const wrap = _el('div', 'display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px;');
        wrap.appendChild(_el('span', 'font-size:12px;color:var(--text-muted,#999);', 'Feature:'));
        const sel = _el('select', 'padding:3px;border-radius:5px;min-width:160px;');
        sel.setAttribute('data-role', 'wp-feature');
        const none = _el('option', null, '— none (click a placed feature) —');
        none.value = '';
        sel.appendChild(none);
        (p.children || []).forEach((c) => {
            const opt = _el('option', null, `${c.name}${c.placed ? ' (placed)' : ''}`);
            opt.value = c.id;
            if (c.id === state.selectedChild) opt.selected = true;
            sel.appendChild(opt);
        });
        sel.addEventListener('change', () => { state.selectedChild = sel.value || null; render(); });
        wrap.appendChild(sel);

        if (state.selectedChild) {
            const child = (p.children || []).find((c) => c.id === state.selectedChild);
            wrap.appendChild(_btn('Open ▸', () => load(state.selectedChild)));
            if (child && child.placed) {
                wrap.appendChild(_btn('🗑 Remove', () => removeFeature(state.selectedChild)));
            }
            wrap.appendChild(_el('span', 'font-size:11px;color:var(--text-muted,#999);',
                'Pick “Feature”, then click a cell to place/move.'));
        }
        return wrap;
    }

    // ───────────────────── grid surface (Konva canvas) ────────────────────
    //
    // Konva draws the grid on a canvas as a fixed number of shapes (background
    // grid, paint, features, route) — a 160x100 world costs the same to render
    // as a 10x10, and work is proportional to *painted* cells, not grid area.
    // Pan/zoom and hit-testing are Konva's, so none of it is hand-rolled. The
    // same payload the DOM version used drives it, so the backend is unchanged.

    function _grid(p) {
        const wrap = _el('div',
            'position:relative;height:480px;border:1px solid var(--border,#3a3a44);' +
            'border-radius:8px;background:#0d0d11;overflow:hidden;margin-bottom:10px;');
        wrap.setAttribute('data-role', 'wp-grid');
        const holder = _el('div', 'position:absolute;inset:0;');
        wrap.appendChild(holder);
        state.gridHolder = holder;
        state.stage = null;
        // Mount after the wrap is in the DOM so Konva can measure the container.
        requestAnimationFrame(() => _mountGrid(p));
        wrap.appendChild(_gridHud(p));
        return wrap;
    }

    function _gridHud(p) {
        const hud = _el('div', 'position:absolute;left:8px;top:8px;z-index:3;display:flex;' +
            'gap:6px;align-items:center;flex-wrap:wrap;background:rgba(13,17,23,0.85);' +
            'border:1px solid var(--border,#3a3a44);border-radius:6px;padding:4px 6px;' +
            'pointer-events:auto;');
        hud.appendChild(_btn('＋', () => _zoomBy(p, 1.25), 'padding:1px 7px;'));
        hud.appendChild(_btn('−', () => _zoomBy(p, 0.8), 'padding:1px 7px;'));
        hud.appendChild(_btn('⤢ Fit', () => _fitGrid(p), 'padding:1px 7px;'));
        hud.appendChild(_el('span', 'font-size:11px;color:var(--text-muted,#999);',
            `${p.grid.w}×${p.grid.h} · 1 cell = 1 turn`));
        hud.appendChild(_referenceControl(p));
        // Painted-cell transparency: lets the reference art show through.
        const alpha = _el('input', 'width:64px;');
        alpha.type = 'range';
        alpha.min = '0.15';
        alpha.max = '1';
        alpha.step = '0.05';
        alpha.value = String(state.paintAlpha);
        alpha.setAttribute('data-role', 'wp-alpha');
        alpha.addEventListener('input', () => {
            state.paintAlpha = parseFloat(alpha.value);
            _redrawGrid();
        });
        hud.appendChild(alpha);
        if (state.tool === 'route') {
            const info = _el('span', 'font-size:11px;color:#7ab;margin-left:6px;');
            info.setAttribute('data-role', 'wp-route-info');
            info.textContent = _routeLabel();
            state.routeInfoEl = info;
            hud.appendChild(info);
            hud.appendChild(_btn('✓ Paint route', () => applyRoute(), 'outline:1px solid #7ab;'));
            hud.appendChild(_btn('✕ Clear', () => { state.route = []; render(); }));
        }
        return hud;
    }

    function _referenceControl(p) {
        const wrap = _el('span', 'display:flex;align-items:center;gap:4px;');
        const ref = p.reference || {};
        const sel = _el('select', 'padding:2px;border-radius:5px;max-width:190px;font-size:11px;');
        sel.setAttribute('data-role', 'wp-bg-select');
        const none = _el('option', null, '🗺 reference…');
        none.value = '';
        sel.appendChild(none);
        const known = (state.backgrounds || []).slice();
        if (ref.image && known.indexOf(ref.image) < 0) known.unshift(ref.image);
        known.forEach((url) => {
            const opt = _el('option', null, url.split('/').pop());
            opt.value = url;
            sel.appendChild(opt);
        });
        sel.value = ref.image || '';
        sel.addEventListener('change', () => updateReference({ image: sel.value || null }));
        wrap.appendChild(sel);

        // The picker only lists images already on the server. A new one has to be
        // uploaded into static/images/backgrounds (the same endpoint the graph
        // background uses), or referenced by URL — so offer both here instead of
        // making the author drop the file in by hand.
        const uploadInput = _el('input');
        uploadInput.type = 'file';
        uploadInput.accept = 'image/*';
        uploadInput.style.display = 'none';
        uploadInput.setAttribute('data-role', 'wp-bg-upload');
        uploadInput.addEventListener('change', async () => {
            const file = uploadInput.files && uploadInput.files[0];
            if (!file) return;
            try {
                const res = await ApiClient.uploadBackgroundImage(file);
                if (!res || res.error) throw new Error((res && res.error) || 'upload failed');
                state.backgrounds = null;          // refresh the picker list
                await ensureBackgrounds();
                await updateReference({ image: res.image });
                _status(`Reference: ${String(res.image).split('/').pop()}.`, false);
            } catch (e) {
                _status(`Upload failed: ${e.message}`, true);
            } finally {
                uploadInput.value = '';
            }
        });
        wrap.appendChild(uploadInput);
        const uploadBtn = _btn('⬆', () => uploadInput.click(), 'padding:1px 6px;');
        uploadBtn.title = 'Upload an image into static/images/backgrounds';
        wrap.appendChild(uploadBtn);
        const urlBtn = _btn('🔗', () => {
            const url = window.prompt(
                'Reference image URL (/static/…, https://… or data:):', ref.image || '');
            if (url !== null) updateReference({ image: url.trim() || null });
        }, 'padding:1px 6px;');
        urlBtn.title = 'Use an image by URL';
        wrap.appendChild(urlBtn);

        if (ref.image) {
            wrap.appendChild(_btn(ref.visible ? '👁' : '🚫', () =>
                updateReference({ visible: !ref.visible }), 'padding:1px 6px;'));
            const op = _el('input', 'width:64px;');
            op.type = 'range';
            op.min = '0';
            op.max = '1';
            op.step = '0.05';
            op.value = String(ref.opacity == null ? 0.5 : ref.opacity);
            op.setAttribute('data-role', 'wp-bg-opacity');
            op.addEventListener('change', () =>
                updateReference({ opacity: parseFloat(op.value) }));
            wrap.appendChild(op);
            // One click: make the grid the image's aspect, so painted cells and
            // the reference share geometry instead of fighting at different ratios.
            wrap.appendChild(_btn('▦ match', () => _gridFromReference(p),
                'padding:1px 6px;font-size:11px;'));
            // Move/resize/crop the picture (task-524). The rect is stored in cell
            // units, so the graph map layout draws the same geometry.
            const adjustBtn = _btn(state.refEdit ? '✔ adjust' : '✥ adjust', () => {
                state.refEdit = !state.refEdit;
                state.refDrag = null;
                render();
                _status(state.refEdit
                    ? 'Reference: drag to move · corners resize · edges crop.'
                    : 'Reference adjust off.', false);
            }, 'padding:1px 6px;font-size:11px;');
            adjustBtn.title = 'Move, resize and crop the reference image';
            wrap.appendChild(adjustBtn);
            const resetBtn = _btn('⤢ reset', () => updateReference({ reset: true }),
                'padding:1px 6px;font-size:11px;');
            resetBtn.title = 'Fit the whole image to the grid again (clears move/resize/crop)';
            wrap.appendChild(resetBtn);
        }
        return wrap;
    }

    async function _gridFromReference(p) {
        const img = state.refImage;
        if (!img || !img.naturalWidth) { _status('Load a reference image first.'); return; }
        const w = Math.max(1, Math.min(400, (p.grid && p.grid.w) || 160));
        const h = Math.max(1, Math.round(w * img.naturalHeight / img.naturalWidth));
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid`,
                { w, h, cell_scale: (p.grid && p.grid.cell_scale) || 1, mode: p.mode });
            state.view = null;   // refit to the new aspect
            _status(`Grid set to ${w}×${h} (image aspect ${img.naturalWidth}×${img.naturalHeight}).`, false);
        } catch (e) {
            _status(`Grid failed: ${e.message}`, true);
        }
    }

    async function updateReference(patch) {
        const p = state.payload;
        const ref = p.reference || {};
        const body = {
            image: ref.image || null,
            opacity: ref.opacity,
            visible: ref.visible,
            ...patch,
        };
        if (body.image == null) body.opacity = undefined;   // cleared
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/reference`, body);
            render();
        } catch (e) {
            _status(`Reference failed: ${e.message}`, true);
        }
    }

    function _routeLabel() {
        const stats = GM().routeStats(GM().routeCells(state.route || []).length);
        return `route: ${stats.label}`;
    }

    function _mountGrid(p) {
        if (!window.Konva || !state.gridHolder) return;
        const holder = state.gridHolder;
        const stage = new window.Konva.Stage({
            container: holder,
            width: holder.clientWidth || 900,
            height: holder.clientHeight || 480,
        });
        const shape = (draw) => new window.Konva.Shape({ listening: false, sceneFunc: draw });
        const bgShape = shape((ctx) => _drawGridLines(ctx, p));
        const paintShape = shape((ctx) => _drawPaint(ctx, p));
        const featureShape = shape((ctx) => _drawFeatures(ctx, p));
        const routeShape = shape((ctx) => _drawRoute(ctx));
        const refShape = shape((ctx) => _drawRefHandles(ctx, p));
        const refLayer = new window.Konva.Layer({ listening: false });
        const bg = new window.Konva.Layer({ listening: false });
        const paint = new window.Konva.Layer({ listening: false });
        const decor = new window.Konva.Layer({ listening: false });
        // Reference image sits under the grid lines, fitted to the grid without
        // distortion, so the art lines up with the same geometry you paint.
        const refNode = new window.Konva.Image({
            x: 0,
            y: 0,
            width: p.grid.w * CELL,
            height: p.grid.h * CELL,
            opacity: (p.reference && p.reference.opacity != null) ? p.reference.opacity : 0.5,
            visible: !!(p.reference && p.reference.visible),
            listening: false,
        });
        state.refNode = refNode;
        const refImg = _ensureRefImage(p);
        if (refImg && refImg.complete && refImg.naturalWidth) {
            refNode.image(refImg);
            _applyRefTransform(p);
        }
        refLayer.add(refNode);
        bg.add(bgShape);
        paint.add(paintShape);
        decor.add(featureShape);
        decor.add(routeShape);
        decor.add(refShape);
        stage.add(refLayer);
        stage.add(bg);
        stage.add(paint);
        stage.add(decor);
        state.stage = stage;
        state.shapes = { bgShape, paintShape, featureShape, routeShape };
        state.layers = { ref: refLayer, bg, paint, decor };
        _wireGrid(p);
        if (state.view) {
            // Rebuild (paint/layer change) keeps the author's place on the map.
            stage.scale({ x: state.view.scale, y: state.view.scale });
            stage.position({ x: state.view.x || 0, y: state.view.y || 0 });
            _redrawGrid();
        } else {
            _fitGrid(p);
        }
    }

    function _captureView() {
        const stage = state.stage;
        if (stage) state.view = { x: stage.x(), y: stage.y(), scale: stage.scaleX() };
    }

    function _redrawGrid() {
        if (state.stage) state.stage.batchDraw();
    }

    /**
     * Redraw only the decor layer (in-progress paint stroke + feature markers +
     * route waypoints). A paint *drag* changes nothing else: the ref/bg/paint
     * layers keep their canvases and the stage transform is unchanged until
     * mouse-up. Calling ``stage.batchDraw()`` on every painted cell re-rasterised
     * the reference image each frame, which made painting crawl once a large
     * reference (deep_forest) was loaded.
     */
    function _redrawDecor() {
        const layers = state.layers;
        if (layers && layers.decor) layers.decor.batchDraw();
        else _redrawGrid();
    }

    function _ensureRefImage(p) {
        const ref = p.reference;
        if (!ref || !ref.image) { state.refImage = null; return null; }
        if (state.refImage && state.refImage.__src === ref.image) return state.refImage;
        const img = new window.Image();
        img.__src = ref.image;
        img.onload = () => {
            state.refImage = img;
            if (state.refNode && state.payload) {
                state.refNode.image(img);
                _applyRefTransform(state.payload);
                _redrawGrid();
            }
        };
        img.onerror = () => { state.refImage = null; };
        img.src = ref.image;
        return img;
    }

    /** Fit the reference into the grid bounds, preserving its aspect ratio. */
    /**
     * The reference's destination rect in **cell** units. A stored rect (the
     * author's move/resize) wins; otherwise fit the whole image into the grid,
     * preserving aspect ratio and centring it. Cell units (not px) so the graph
     * map layout can draw the same picture at its own spacing (task-524).
     */
    function _refRectCells(p, img) {
        const stored = (p.reference || {}).rect;
        if (stored && typeof stored.x === 'number' && typeof stored.y === 'number'
                && typeof stored.w === 'number' && typeof stored.h === 'number'
                && stored.w > 0 && stored.h > 0) {
            return { x: stored.x, y: stored.y, w: stored.w, h: stored.h };
        }
        const gw = (p.grid && p.grid.w) || 0;
        const gh = (p.grid && p.grid.h) || 0;
        const iw = (img && img.naturalWidth) || gw || 1;
        const ih = (img && img.naturalHeight) || gh || 1;
        return GM().fitReferenceRect(gw, gh, iw, ih);
    }

    /** Draw the reference into its rect (px) with the stored crop window. */
    function _applyRefTransform(p) {
        const node = state.refNode;
        if (!node) return;
        const img = state.refImage;
        const rect = _refRectCells(p, img);
        node.x(rect.x * CELL);
        node.y(rect.y * CELL);
        node.width(rect.w * CELL);
        node.height(rect.h * CELL);
        const iw = (img && img.naturalWidth) || 0;
        const ih = (img && img.naturalHeight) || 0;
        if (!iw || !ih) return;
        const crop = (p.reference || {}).crop;
        node.crop(crop && crop.w
            ? { x: crop.x * iw, y: crop.y * ih, width: crop.w * iw, height: crop.h * ih }
            : { x: 0, y: 0, width: iw, height: ih });
    }

    /** Handle anchor points (cell units): corners resize, edges crop. */
    function _refHandlePoints(rect) {
        return GM().referenceHandlePoints(rect);
    }

    function _drawRefHandles(ctx, p) {
        if (!state.refEdit || !state.refImage || !(p.reference && p.reference.image)) return;
        const rect = _refRectCells(p, state.refImage);
        const scale = (state.stage && state.stage.scaleX()) || 1;
        ctx.save();
        ctx.strokeStyle = '#58a6ff';
        ctx.lineWidth = 1.5 / scale;
        ctx.setLineDash([6 / scale, 4 / scale]);
        ctx.strokeRect(rect.x * CELL, rect.y * CELL, rect.w * CELL, rect.h * CELL);
        ctx.setLineDash([]);
        const pts = _refHandlePoints(rect);
        Object.keys(pts).forEach((key) => {
            ctx.beginPath();
            ctx.arc(pts[key].x * CELL, pts[key].y * CELL, 5 / scale, 0, Math.PI * 2);
            ctx.fillStyle = key.length === 2 ? '#58a6ff' : '#e3b341';   // corners vs edges
            ctx.fill();
        });
        ctx.restore();
    }

    /** What a pointer press grabs on the reference: a handle or the body. */
    function _refHit(p, pos) {
        const rect = _refRectCells(p, state.refImage);
        const scale = (state.stage && state.stage.scaleX()) || 1;
        const tol = 9 / scale;
        const pts = _refHandlePoints(rect);
        for (const key of Object.keys(pts)) {
            if (Math.abs(pos.x - pts[key].x * CELL) <= tol
                    && Math.abs(pos.y - pts[key].y * CELL) <= tol) {
                return { kind: key.length === 2 ? 'resize' : 'crop', key };
            }
        }
        const x = rect.x * CELL, y = rect.y * CELL, w = rect.w * CELL, h = rect.h * CELL;
        if (pos.x >= x && pos.x <= x + w && pos.y >= y && pos.y <= y + h) {
            return { kind: 'move', key: null };
        }
        return null;
    }

    function _refMouseDown(p) {
        if (!state.refImage || !(p.reference && p.reference.image)) return;
        const pos = state.stage.getRelativePointerPosition();
        if (!pos) return;
        const target = _refHit(p, pos);
        if (!target) return;
        state.refDrag = {
            kind: target.kind,
            key: target.key,
            start: { x: pos.x / CELL, y: pos.y / CELL },
            rect: _refRectCells(p, state.refImage),
            crop: Object.assign({ x: 0, y: 0, w: 1, h: 1 }, (p.reference || {}).crop || {}),
        };
    }

    function _refMouseMove(p) {
        const drag = state.refDrag;
        if (!drag) return;
        const pos = state.stage.getRelativePointerPosition();
        if (!pos) return;
        const cx = pos.x / CELL;
        const cy = pos.y / CELL;
        let r = Object.assign({}, drag.rect);
        let crop = Object.assign({}, drag.crop);
        if (drag.kind === 'move') {
            r.x = drag.rect.x + (cx - drag.start.x);
            r.y = drag.rect.y + (cy - drag.start.y);
        } else {
            // Pure geometry lives in grid-model (unit-tested): corners resize,
            // edges crop.
            const next = GM().referenceHandleDrag(drag.rect, drag.crop, drag.key, cx, cy);
            r = next.rect;
            crop = next.crop;
        }
        state.refDrag.rect = r;
        state.refDrag.crop = crop;
        // Live preview without a round-trip; persisted on mouse-up.
        p.reference = Object.assign({}, p.reference, { rect: r, crop });
        _applyRefTransform(p);
        _redrawGrid();
    }

    function _refMouseUp() {
        const drag = state.refDrag;
        if (!drag) return;
        state.refDrag = null;
        const p = state.payload;
        if (!p || !(p.reference && p.reference.image)) return;
        updateReference({ rect: drag.rect, crop: drag.crop });
    }

    function _drawGridLines(ctx, p) {
        const w = p.grid.w * CELL;
        const h = p.grid.h * CELL;
        ctx.save();
        // No opaque fill: the reference image (a layer beneath) must show through.
        const scale = state.stage ? state.stage.scaleX() : 1;
        // Below ~4px per cell the lines become moiré — paint only.
        if (CELL * scale >= 4) {
            ctx.strokeStyle = 'rgba(255,255,255,0.07)';
            ctx.lineWidth = 1 / scale;
            ctx.beginPath();
            for (let x = 0; x <= p.grid.w; x += 1) {
                ctx.moveTo(x * CELL, 0);
                ctx.lineTo(x * CELL, h);
            }
            for (let y = 0; y <= p.grid.h; y += 1) {
                ctx.moveTo(0, y * CELL);
                ctx.lineTo(w, y * CELL);
            }
            ctx.stroke();
        }
        ctx.restore();
    }

    function _drawPaint(ctx, p) {
        ctx.save();
        ctx.globalAlpha = state.paintAlpha == null ? 1 : state.paintAlpha;
        Object.keys(p.layers || {}).forEach((layer) => {
            const cells = p.layers[layer] || {};
            Object.keys(cells).forEach((key) => {
                const pos = GM().parseCellKey(key);
                if (!pos) return;
                const color = GM().layerColor(layer, cells[key]);
                if (!color) return;
                ctx.fillStyle = color;
                ctx.fillRect(pos.x * CELL + 1, pos.y * CELL + 1, CELL - 2, CELL - 2);
            });
        });
        ctx.restore();
    }

    function _drawFeatures(ctx, p) {
        ctx.save();
        ctx.font = `${Math.max(9, CELL - 8)}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        (p.placements || []).forEach((pl) => {
            const selected = pl.id === state.selectedChild;
            ctx.fillStyle = selected ? '#f5c542' : '#7b5aa6';
            ctx.fillRect(pl.x * CELL + 2, pl.y * CELL + 2, CELL - 4, CELL - 4);
            ctx.fillStyle = '#fff';
            ctx.fillText('🏠', pl.x * CELL + CELL / 2, pl.y * CELL + CELL / 2);
        });
        ctx.restore();
    }

    function _drawRoute(ctx) {
        // In-progress paint stroke (drag): drawn optimistically, committed on
        // mouse-up as one batch. Without this a brush drag felt like "click and
        // wait" — now it paints a live trail.
        if (state.stroke && state.stroke.length) {
            ctx.save();
            ctx.globalAlpha = state.paintAlpha == null ? 1 : state.paintAlpha;
            ctx.fillStyle = state.strokeValue == null
                ? '#8a8a8a'
                : (GM().layerColor(state.strokeLayer, state.strokeValue) || '#cccccc');
            state.stroke.forEach((c) => {
                ctx.fillRect(c.x * CELL + 1, c.y * CELL + 1, CELL - 2, CELL - 2);
            });
            ctx.restore();
        }
        const pts = state.route || [];
        if (!pts.length) return;
        ctx.save();
        ctx.strokeStyle = '#7ab';
        ctx.lineWidth = Math.max(1.5, CELL / 6);
        ctx.setLineDash([6, 4]);
        if (pts.length > 1) {
            ctx.beginPath();
            pts.forEach((pt, i) => {
                const cx = pt.x * CELL + CELL / 2;
                const cy = pt.y * CELL + CELL / 2;
                if (i === 0) ctx.moveTo(cx, cy); else ctx.lineTo(cx, cy);
            });
            ctx.stroke();
        }
        ctx.setLineDash([]);
        ctx.fillStyle = '#f5c542';
        pts.forEach((pt) => {
            ctx.beginPath();
            ctx.arc(pt.x * CELL + CELL / 2, pt.y * CELL + CELL / 2, 3, 0, Math.PI * 2);
            ctx.fill();
        });
        ctx.restore();
    }

    function _isPaintTool() {
        return state.tool === 'paint' || state.tool === 'erase';
    }

    function _strokeAdd(p, cell) {
        if (!cell) return false;
        const keys = state.strokeKeys || (state.strokeKeys = {});
        let added = false;
        _brushCells(p, cell.x, cell.y).forEach((b) => {
            const k = GM().cellKey(b.x, b.y);
            if (!keys[k]) { keys[k] = true; state.stroke.push(b); added = true; }
        });
        return added;
    }

    async function _commitStroke(p) {
        state.stroking = false;
        const cells = state.stroke || [];
        const layer = state.strokeLayer;
        const value = state.strokeValue;
        state.stroke = [];
        state.strokeKeys = {};
        if (!cells.length) { _redrawDecor(); return; }
        try {
            if (cells.length === 1) {
                state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/paint`,
                    { layer, x: cells[0].x, y: cells[0].y, value });
            } else {
                state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`,
                    { edits: cells.map((c) => ({ layer, x: c.x, y: c.y, value })) });
            }
            _notify(true);
            render();
        } catch (e) {
            _status(`Paint failed: ${e.message}`, true);
        }
    }

    function _wireGrid(p) {
        const stage = state.stage;
        let dragged = false;
        // Paint/erase drag = paint. Pan is space-drag (or the zoom buttons), so a
        // stroke is never interrupted by a pan. In reference-adjust mode the drag
        // belongs to the picture, so only space pans there.
        stage.draggable(state.spaceDown || (!state.refEdit && !_isPaintTool()));
        stage.on('dragstart', () => { dragged = true; });
        stage.on('dragend', _captureView);

        stage.on('mousedown', (e) => {
            if (state.refEdit && !state.spaceDown) { _refMouseDown(p); return; }
            if (!_isPaintTool() || state.spaceDown || (e.evt && e.evt.button !== 0)) return;
            state.stroke = [];
            state.strokeKeys = {};
            state.strokeLayer = state.layer;
            state.strokeValue = state.tool === 'erase' ? null : state.value;
            state.stroking = true;
            _strokeAdd(p, _cellAtPointer(p));
            _redrawDecor();
        });
        stage.on('mousemove', () => {
            if (state.refEdit) { _refMouseMove(p); return; }
            if (!state.stroking) return;
            if (_strokeAdd(p, _cellAtPointer(p))) _redrawDecor();
        });
        stage.on('mouseup mouseleave', () => {
            if (state.refEdit) { _refMouseUp(); return; }
            if (state.stroking) _commitStroke(p);
        });

        stage.on('click tap', () => {
            if (state.refEdit) return;    // adjust mode owns the pointer
            if (dragged) { dragged = false; return; }
            if (_isPaintTool()) return;   // already committed by the stroke
            const cell = _cellAtPointer(p);
            if (cell) _gridClick(p, cell);
        });
        stage.on('wheel', (e) => {
            e.evt.preventDefault();
            const old = stage.scaleX();
            const ptr = stage.getPointerPosition();
            const gridPt = { x: (ptr.x - stage.x()) / old, y: (ptr.y - stage.y()) / old };
            const next = Math.max(MIN_SCALE, Math.min(MAX_SCALE, old * (e.evt.deltaY < 0 ? 1.12 : 0.89)));
            stage.scale({ x: next, y: next });
            stage.position({ x: ptr.x - gridPt.x * next, y: ptr.y - gridPt.y * next });
            _captureView();
            _redrawGrid();
        });
        stage.on('contextmenu', (e) => { e.evt.preventDefault(); });
    }

    function _cellAtPointer(p) {
        const rp = state.stage && state.stage.getRelativePointerPosition();
        if (!rp) return null;
        const x = Math.floor(rp.x / CELL);
        const y = Math.floor(rp.y / CELL);
        if (x < 0 || y < 0 || x >= p.grid.w || y >= p.grid.h) return null;
        return { x, y };
    }

    function _gridClick(p, cell) {
        const fmap = GM().featureMap(p);
        const placement = fmap[GM().cellKey(cell.x, cell.y)] || null;
        onCellClick(p, cell.x, cell.y, placement);
    }

    function _zoomBy(p, factor) {
        const stage = state.stage;
        if (!stage) return;
        const old = stage.scaleX();
        const next = Math.max(MIN_SCALE, Math.min(MAX_SCALE, old * factor));
        const c = { x: stage.width() / 2, y: stage.height() / 2 };
        const gridPt = { x: (c.x - stage.x()) / old, y: (c.y - stage.y()) / old };
        stage.scale({ x: next, y: next });
        stage.position({ x: c.x - gridPt.x * next, y: c.y - gridPt.y * next });
        _captureView();
        _redrawGrid();
    }

    function _fitGrid(p) {
        const stage = state.stage;
        if (!stage) return;
        const scale = Math.max(MIN_SCALE, Math.min(1.5,
            Math.min(stage.width() / (p.grid.w * CELL), stage.height() / (p.grid.h * CELL))));
        stage.scale({ x: scale, y: scale });
        stage.position({
            x: (stage.width() - p.grid.w * CELL * scale) / 2,
            y: (stage.height() - p.grid.h * CELL * scale) / 2,
        });
        _captureView();
        _redrawGrid();
    }

    async function applyRoute() {
        const p = state.payload;
        const cells = GM().routeCells(state.route || []);
        if (cells.length < 2) { _status('Route needs at least two waypoints.'); return; }
        const value = state.value;
        if (value == null || value === '') { _status('Pick a paint value first.'); return; }
        // Brush widens the trail: a 3×3 brush turns a 1-cell line into a 3-wide river.
        const seen = {};
        const wide = [];
        cells.forEach((c) => {
            _brushCells(p, c.x, c.y).forEach((b) => {
                const k = GM().cellKey(b.x, b.y);
                if (!seen[k]) { seen[k] = true; wide.push(b); }
            });
        });
        const edits = wide.map((c) => ({ layer: state.layer, x: c.x, y: c.y, value }));
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`,
                { edits });
            state.route = [];
            _notify(true);
            const stats = GM().routeStats(edits.length);
            _status(`🧭 Painted ${stats.label} on ${state.layer}.`, false);
        } catch (e) {
            _status(`Route failed: ${e.message}`, true);
        }
    }

    function _renderChildren(box, p) {
        const kids = p.children || [];
        if (!kids.length) return;
        const head = _el('div', 'font-size:12px;color:var(--text-muted,#999);margin:8px 0 4px;',
            'Child scopes');
        box.appendChild(head);
        const row = _el('div', 'display:flex;flex-wrap:wrap;gap:8px;');
        kids.forEach((c) => row.appendChild(_scopeCard(c, (card) => load(card.id))));
        box.appendChild(row);
    }

    // ───────────────────────────── mutations ───────────────────────────

    async function onCellClick(p, x, y, placement) {
        if (state.tool === 'route') {
            // Collect waypoints; the HUD's "Paint route" rasterises the line and
            // batch-paints it in one request (a 240-cell trail is one undo).
            state.route.push({ x, y });
            if (state.routeInfoEl) state.routeInfoEl.textContent = _routeLabel();
            _redrawDecor();
            return;
        }
        if (state.tool === 'feature') {
            if (state.selectedChild) {
                await placeFeature(state.selectedChild, x, y);
            } else if (placement) {
                state.selectedChild = placement.id;
                render();
            } else {
                _status('Select a feature first (Feature dropdown above).');
            }
            return;
        }
        if (!p.scope.has_grid) return;
        return _paintAt(p, x, y);
    }

    /** Cells an N×N brush covers, clipped to the grid. */
    function _brushCells(p, x, y) {
        const n = Math.max(1, state.brush | 0);
        const off = Math.floor((n - 1) / 2);
        const out = [];
        for (let dy = 0; dy < n; dy += 1) {
            for (let dx = 0; dx < n; dx += 1) {
                const cx = x - off + dx;
                const cy = y - off + dy;
                if (cx >= 0 && cy >= 0 && cx < p.grid.w && cy < p.grid.h) {
                    out.push({ x: cx, y: cy });
                }
            }
        }
        return out;
    }

    async function _paintAt(p, x, y) {
        const value = state.tool === 'erase' ? null : state.value;
        if (state.tool === 'paint' && (value == null || value === '')) {
            _status('Pick a paint value, or use Erase.');
            return;
        }
        const cells = _brushCells(p, x, y);
        try {
            if (cells.length === 1) {
                state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/paint`,
                    { layer: state.layer, x, y, value });
            } else {
                state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`,
                    { edits: cells.map((c) => ({ layer: state.layer, x: c.x, y: c.y, value })) });
            }
            _notify(true);
            render();
        } catch (e) {
            _status(`Paint failed: ${e.message}`, true);
        }
    }

    async function placeFeature(childId, x, y, onOverlap) {
        const p = state.payload;
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/place`,
                { child_id: childId, x, y, on_overlap: onOverlap || 'forbid' });
            _notify(true);
            render();
        } catch (e) {
            if (!onOverlap && /already holds/.test(e.message)
                    && window.confirm(`${e.message}\n\nDisplace the occupant?`)) {
                return placeFeature(childId, x, y, 'displace');
            }
            _status(`Place failed: ${e.message}`, true);
        }
    }

    async function removeFeature(childId) {
        try {
            state.payload = await _post(`/${encodeURIComponent(state.payload.scope.id)}/grid/remove`,
                { child_id: childId });
            state.selectedChild = null;
            _notify(true);
            render();
        } catch (e) {
            _status(`Remove failed: ${e.message}`, true);
        }
    }

    /** Rename a scope's display name (its id, and every node reference, stays). */
    async function renameScope(scopeId, currentName) {
        const name = window.prompt('Rename scope:', currentName || scopeId);
        if (name == null) return;
        const clean = name.trim();
        if (!clean || clean === currentName) return;
        try {
            await _post(`/${encodeURIComponent(scopeId)}/rename`, { name: clean });
            _notify(true);
            // A renamed *child* is a card in this scope's list, and the card's
            // name lives in the payload — refetch it. `render()` alone redrew the
            // stale list and the card kept its old label. Renaming the open scope
            // itself needs a full load (its title/breadcrumb changed).
            if (state.scopeId === scopeId) await load(scopeId);
            else await _reloadPayload();
            _status(`Renamed to “${clean}”.`, false);
        } catch (e) {
            _status(`Rename failed: ${e.message}`, true);
        }
    }

    /**
     * Delete a scope. Refuses one that still has children (delete those first);
     * a generated scope's areas/ways/items go with it. If it was the open scope,
     * fall back to its parent.
     */
    async function deleteScope(scopeId, name) {
        const label = name || scopeId;
        if (!window.confirm(`Delete scope “${label}”?\n\n`
            + `This removes the scope, unplaces it, and deletes the areas/ways/items `
            + `generated for it. Scopes that still have children must be emptied first.`)) {
            return;
        }
        const trail = (state.payload && state.payload.breadcrumb) || [];
        const parentId = trail.length > 1 ? trail[trail.length - 2].id : null;
        try {
            const result = await _post(`/${encodeURIComponent(scopeId)}/delete`, {});
            _notify(true);
            if (state.scopeId === scopeId) {
                if (parentId) load(parentId); else open();
            } else {
                // Deleted scope was a card here: refetch so the card disappears.
                await _reloadPayload();
            }
            _status(`Deleted “${label}” (${result.deleted_nodes || 0} generated node(s)).`, false);
        } catch (e) {
            _status(`Delete failed: ${e.message}`, true);
        }
    }

    async function _promptNewScope(parentId) {
        const name = window.prompt('Feature name:', 'New feature');
        if (!name) return;
        const mode = parentId && state.payload
            ? GM().nextMode(state.payload.mode) : 'world';
        const body = { name, parent_id: parentId || null, mode };
        if (state.payload && state.payload.grid) {
            body.w = Math.max(1, Math.min(8, state.payload.grid.w));
            body.h = Math.max(1, Math.min(8, state.payload.grid.h));
        }
        try {
            const created = await _post('', body);
            _notify(true);
            if (parentId && state.payload) {
                state.selectedChild = created.scope.id;
                // Re-open the parent so the new child appears in its list.
                state.payload = await _req(
                    `${BASE}/${encodeURIComponent(parentId)}/grid`, { cache: 'no-store' });
                render();
                _status(`Created “${created.scope.name}” — pick Feature and click a cell to place it.`);
            } else {
                load(created.scope.id);
            }
        } catch (e) {
            _status(`Create failed: ${e.message}`, true);
        }
    }

    function _openGridDialog(p) {
        const wrap = _el('div', 'display:flex;gap:8px;align-items:center;flex-wrap:wrap;' +
            'padding:8px;border:1px solid var(--border,#3a3a44);border-radius:8px;margin-bottom:8px;');
        const cur = p.grid || { w: 10, h: 10, cell_scale: 1 };
        const mk = (name, val, width) => {
            wrap.appendChild(_el('span', 'font-size:12px;color:var(--text-muted,#999);', name));
            const inp = _el('input',
                `width:${width || 56}px;padding:3px 6px;border-radius:5px;border:1px solid ` +
                'var(--border,#444);background:var(--bg-card,#2a2a32);color:var(--text,#ddd);');
            inp.value = val;
            wrap.appendChild(inp);
            return inp;
        };
        const wIn = mk('w', cur.w);
        wIn.setAttribute('data-role', 'wp-grid-w');
        const hIn = mk('h', cur.h);
        hIn.setAttribute('data-role', 'wp-grid-h');
        const sIn = mk('scale', cur.cell_scale, 64);
        sIn.setAttribute('data-role', 'wp-grid-scale');
        // Presets sized in *turns*: 1 cell = 1 turn, 60 turns/hour. A two-route
        // region (e.g. two 240-cell trails) needs roughly this much canvas.
        [['region 160×100', 160, 100], ['wide 180×70', 180, 70], ['small 60×60', 60, 60]]
            .forEach(([label, pw, ph]) => {
                wrap.appendChild(_btn(label, () => { wIn.value = pw; hIn.value = ph; refreshWarn(); },
                    'padding:2px 6px;font-size:11px;'));
            });
        wrap.appendChild(_el('span', 'font-size:12px;color:var(--text-muted,#999);', 'mode'));
        const modeSel = _el('select', 'padding:3px;border-radius:5px;');
        modeSel.setAttribute('data-role', 'wp-grid-mode');
        GM().MODES.forEach((m) => {
            const opt = _el('option', null, m);
            opt.value = m;
            if (m === (p.mode || 'world')) opt.selected = true;
            modeSel.appendChild(opt);
        });
        wrap.appendChild(modeSel);

        const warn = _el('span', 'font-size:11px;color:#c96;');
        wrap.appendChild(warn);
        const refreshWarn = () => {
            const w = parseInt(wIn.value, 10), h = parseInt(hIn.value, 10);
            if (!w || !h || w < 1 || h < 1) { warn.textContent = 'w and h must be ≥ 1'; return; }
            const pr = GM().pruneGrid(p, w, h);
            const lost = GM().PAINT_LAYERS.reduce((n, l) =>
                n + Object.keys((p.layers || {})[l] || {}).length, 0) - pr.paintKept;
            const lostP = (p.placements || []).length - pr.placementsKept;
            warn.textContent = (lost > 0 || lostP > 0)
                ? `shrink drops ${lost} paint cell(s), ${lostP} placement(s)` : '';
        };
        [wIn, hIn].forEach((i) => i.addEventListener('input', refreshWarn));
        refreshWarn();

        wrap.appendChild(_btn('Apply', async () => {
            try {
                state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid`, {
                    w: parseInt(wIn.value, 10),
                    h: parseInt(hIn.value, 10),
                    cell_scale: parseFloat(sIn.value) || 1,
                    mode: modeSel.value,
                });
                _notify(true);
                render();
            } catch (e) {
                _status(`Grid failed: ${e.message}`, true);
            }
        }));
        wrap.appendChild(_btn('Cancel', () => wrap.remove()));
        // Live at the bottom of the open panel so Apply/Cancel are always reachable.
        state.body.appendChild(wrap);
    }

    function _status(text, isError) {
        state.status = text;
        state.statusError = !!isError;
        _log((isError ? '⚠ ' : '') + text, isError ? 'error-msg' : 'system-msg');
        render();
    }

    window.VW = window.VW || {};
    window.VW.worldPainter = { open, close, refresh: () => (state.scopeId ? load(state.scopeId) : showChooser()) };
    window.worldPainter = window.VW.worldPainter;
})();
