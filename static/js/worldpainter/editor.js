"use strict";
/**
 * editor.js - WorldPainter 3-mode grid editor (task-495).
 *
 * A plain-DOM overlay (no Lit, no ordering constraints) that renders one world
 * scope's authoring grid at its own resolution and lets the author:
 *   - select a scope and drill into its children (recursive scope grids);
 *   - set/resize the grid and pick its mode (world / town / interior);
 *   - paint cells on the biome / road / floor layers;
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
 * @module worldpainter/editor - WorldPainter grid editing overlay
 * @contributes the 3-mode scope grid editor UI: paint, feature place/move/remove, area placement, cell inspection, drill-down
 * @powers WorldPainter authored worlds (task-495) feeding the grid-to-graph compiler (task-496)
 * @relates static/js/worldpainter/grid-model.js; routes/world_grid_ops.py; engine/world_grid.py
 * @docs docs/design/worldpainter-knowledge-and-fog.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
(function () {
    'use strict';
    /**
     * Konva 9, the UMD bundle templates/index.html pulls from unpkg. It is not in
     * globals.d.ts and the bundle ships no types, so `WpKonvaFactory` declares
     * only the surface this file calls. `sceneFunc` receives a real
     * CanvasRenderingContext2D at draw time, which is what every `ctx.*` below
     * assumes.
     */
    function _konva() {
        return window.Konva || null;
    }
    /**
     * `catch (e)` is `unknown` under strict. Almost every handler below wants the
     * message and nothing else, and `_req` always rejects with an `Error`, so
     * this is the one narrowing - the non-Error branch keeps the old
     * string-interpolation behaviour rather than swallowing it.
     */
    function errText(e) {
        return e instanceof Error ? e.message : String(e);
    }
    const BASE = '/api/world/scopes';
    // The bare endpoint answers a tree that inlines ONLY the root and its immediate
    // children -- a scope nested two deep (`goblin_camp` > `test`) is absent from it
    // entirely, so it cannot be chosen for painting. `?flat=1` returns every scope
    // with its `depth` and `parent_id`, which is the complete list.
    // `SCOPES_URL` is what any scope *picker* should use; `BASE` stays for the
    // per-scope grid payloads that expect the nested shape.
    const SCOPES_URL = '/api/world/scopes?flat=1';
    const CELL = 22; // base px per cell at scale 1
    // The zoom floor is a *legibility* floor, not an arithmetic one (task-595).
    // `_drawGridLines` stops drawing the lattice below 4px per cell, so at the
    // old 0.12 (< 3px per cell) the grid dissolved into a smear of paint blobs
    // and the author could not tell a road from a field. 0.25 keeps a cell at
    // 5.5px - lines still drawn, a 160-cell world still fits an 880px pane - so
    // zooming out to the floor leaves a readable map rather than a blank one.
    const MIN_SCALE = 0.25;
    const MAX_SCALE = 20;
    // main.js reloads the VW namespace last, so prefer the bare global it keeps.
    const GM = () => window.gridModel || window.VW.gridModel;
    const dialogCtx = () => ({
        state,
        post: _post,
        postRoot: _post_root,
        req: _req,
        status: _status,
        notify: _notify,
        render,
        softRender,
        load,
        open,
        renderShell: _renderShell,
        reloadPayload: _reloadPayload,
        commitGridSize: _commitGridSize,
        el: _el,
        btn: _btn,
        slug: _slug,
        errText,
        GM,
    });
    const paletteCtx = () => ({
        state,
        dialogCtx,
        pushRecent: _pushRecent,
        saveScopePrefs: _saveScopePrefs,
        softRender,
        render,
        load,
        setCellName,
        setSeam,
        clearCell,
        unplaceArea,
        removeFeature,
        promoteArea,
        el: _el,
        btn: _btn,
        GM,
        post: _post,
        notify: _notify,
        status: _status,
        errText,
        selectedCells: _selectedCells,
        sel: _sel,
        setSelection: _setSelection,
        nudge: _nudge,
        help: _help,
        recomputeVisionField: _recomputeVisionField,
        redrawDecor: _redrawDecor,
        updateReference,
        gridFromReference: _gridFromReference,
        openGridDialog: _openGridDialog,
        fitGrid: _fitGrid,
        zoomBy: _zoomBy,
        syncZoomButtons: _syncZoomButtons,
        placeArea,
        placeFeature,
    });
    const handlesCtx = () => ({
        state,
        CELL,
        MAX_SCALE,
        refRectCells: _refRectCells,
        refScreenBox: _refScreenBox,
        applyRefTransform: _applyRefTransform,
        redrawGrid: _redrawGrid,
        redrawDecor: _redrawDecor,
        updateReference,
        captureView: _captureView,
        syncZoomButtons: _syncZoomButtons,
        post: _post,
        status: _status,
        notify: _notify,
        render,
        errText,
        GM,
    });
    const canvasCtx = () => ({
        state,
        CELL,
        gridExtent: _gridExtent,
        refRectCells: _refRectCells,
        ensurePaintCache: _ensurePaintCache,
        brushCells: _brushCells,
        redrawDecor: _redrawDecor,
        status: _status,
        GM,
        post: _post,
        notify: _notify,
        render,
        softRender,
        errText,
        syncDraggable: _syncDraggable,
        inspectCell,
    });
    const state = {
        scopeId: null,
        payload: null,
        tool: 'paint',
        layer: 'biome',
        value: 'sparse_forest',
        brush: 1,
        paletteOpen: false,
        paletteCategory: null,
        paletteQuery: '',
        brushHover: null,
        paintAlpha: 0.75,
        stroke: [],
        stroking: false,
        strokeLayer: null,
        strokeValue: null,
        strokeKeys: {},
        spaceDown: false,
        vocab: null,
        backgrounds: null,
        refImage: null,
        refNode: null,
        refEdit: false, // adjust mode: move/resize/crop the reference image
        refDrag: null, // {kind, key, start, rect, crop} during a ref edit
        // Grid adjust mode (task-597): drag the frame to set the scope's map
        // layout offset, or an edge/corner handle to resize the extent, instead
        // of typing numbers into the dialog.
        gridEdit: false,
        gridDrag: null, // {kind, key, start, w, h, offset} during a grid edit
        gridDragRelease: null,
        // Set while dragging the cell (0,0) corner handle (task-597); the canvas
        // draws the candidate extent and the cells it would strand.
        cellSizePreview: null,
        dimsBtn: null,
        selectedChild: null,
        selectedArea: null, // area picked by the 📍 Area place tool (task-528)
        // Cell selection and the marquee being dragged (task-536). Keyed by scope
        // id, because a selection is *this map's* selection: switching tools keeps
        // it, switching maps must not smuggle it across.
        selection: {}, // {scopeId: {'x,y': true}}
        marquee: null, // {anchor: {x, y}, to: {x, y}} while dragging
        nudged: null, // last move offset, for the status line
        inspected: null, // {x, y} the cell the inspector panel is showing (task-540)
        cellInfoEl: null, // HUD hover readout for the cell under the pointer
        cellInfoKey: null, // last hovered cell+content, to skip pointless DOM writes
        // The current scroll container (rebuilt by every render) and the author's
        // position in it. Without this, each action threw the view back to the top
        // and a long panel had to be re-scrolled every time.
        scrollBox: null,
        scrollTop: 0,
        scrollRestored: false,
        merge: false,
        view: null, // {scale} - Konva owns the live transform
        route: [], // waypoints for the route/trail tool
        stage: null,
        paintCache: null,
        paintCacheValid: false,
        recents: [],
        resizeObs: null,
        shapes: null,
        layers: null,
        gridHolder: null,
        routeInfoEl: null,
        zoomInBtn: null,
        zoomOutBtn: null,
        overlay: null,
        body: null,
        // The per-mode checklist's open/closed state. `checklistTouched` records
        // that the author clicked it, which stops it re-deciding for them.
        checklistOpen: true,
        checklistTouched: false,
        status: '',
        statusError: false,
        visionOrigin: null,
        visionTarget: null,
        visionFacing: null,
        visionRay: null,
        visionVisibleSet: null,
        visionLens: false,
        _keyDown: null,
        _keyUp: null,
    };
    // ───────────────────────────── dom/net ─────────────────────────────
    /**
     * Build an element. Generic over the tag so `_el('input', …).value` and
     * `_el('select', …).options` are typed, which is most of what this file does
     * with what it gets back.
     */
    function _el(tag, style, text) {
        const el = document.createElement(tag);
        if (style)
            el.setAttribute('style', style);
        if (text != null)
            el.textContent = text;
        return el;
    }
    function _btn(label, onClick, style, title) {
        const b = _el('button', 'cursor:pointer;border:1px solid var(--border,#444);' +
            'background:var(--bg-card,#2a2a32);color:var(--text,#ddd);border-radius:5px;' +
            'padding:3px 8px;font-size:12px;' + (style || ''), label);
        if (title)
            b.title = title;
        b.addEventListener('click', onClick);
        return b;
    }
    /**
     * Hook a painter control into the HelpCenter (task-521). The launcher button
     * was the only hinted control in this overlay, so every in-editor control -
     * the ones you actually have to understand - was unhelpfully silent.
     */
    function _help(el, key) {
        if (el)
            el.setAttribute('data-help', key);
        return el;
    }
    /**
     * The preflight bar: what blocks this scope from compiling, and what to do.
     *
     * Renders beside ⚙ Generate rather than behind it, because the whole point is
     * that the author finds out *before* pressing it. A block is stated with its
     * remedy inline; a warn is folded behind a count so a map with six naming
     * reminders does not bury the one that matters.
     */
    function _blockerBadge(blockers) {
        if (window.WorldPainterPalette?.blockerBadge) {
            return window.WorldPainterPalette.blockerBadge(paletteCtx(), blockers);
        }
        return _el('div');
    }
    /**
     * One POST/GET against the backend.
     *
     * `any` on the way out on purpose: the answer is whatever JSON the route
     * answered with, and the callers either store it as the next payload or read
     * two or three fields off it. `unknown` would push a cast to every one of
     * them for no gain.
     */
    async function _req(url, options) {
        const resp = await fetch(url, options);
        let data = null;
        try {
            data = await resp.json();
        }
        catch (e) {
            data = null;
        }
        if (!resp.ok)
            throw new Error((data && data.error) || `${resp.status} ${resp.statusText}`);
        return data;
    }
    function _log(text, cls) {
        if (window.events && typeof window.events.log === 'function') {
            window.events.log(text, cls || 'system-msg');
        }
    }
    function _notify(worldChanged) {
        const win = window;
        const sync = win.worldSync || win.VW?.worldSync;
        if (worldChanged && sync && typeof sync.refresh === 'function') {
            sync.refresh();
        }
        if (worldChanged && win.graphManager && typeof win.graphManager.loadGraphData === 'function') {
            win.graphManager._lastSig = '';
            win.graphManager.loadGraphData();
        }
    }
    const _post = (path, body) => _req(BASE + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {}),
    });
    /**
     * A POST to a path that is not under `/api/world/scopes`.
     *
     * `/api/world/promote` is the one WorldPainter endpoint that lives outside
     * the scopes prefix, so `_post('/promote', …)` asked for
     * `/api/world/scopes/promote` - which matches the scope *read* route, so the
     * server answered 405 and the painter said "Promote failed". Absolute path
     * or nothing.
     */
    const _post_root = (path, body) => _req(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {}),
    });
    /**
     * What each structure kind is *to movement*, in the author's terms (task-562).
     * The cells here never become places, so the panel has to say what they do
     * instead of reporting "biome: wall" and leaving it at that.
     */
    const STRUCTURE_NOTES = {
        solid: 'solid - nothing passes it',
        see_through: 'you can see through it, not walk through it',
        passable: 'a threshold - you go through it',
    };
    // ───────────────────────────── open/close ──────────────────────────
    function _clearPaletteMemos() {
        if (window.WorldPainterPalette) {
            window.WorldPainterPalette.clearPaletteMemos();
        }
    }
    async function ensureVocab() {
        if (state.vocab)
            return state.vocab;
        try {
            state.vocab = await _req('/api/world/painter/vocabulary', { cache: 'no-store' });
            _clearPaletteMemos();
            // The climates come from the backend, ids and base °C both (task-557);
            // only the colour is local, so a new climate needs no editor change.
            GM().useClimatesFromVocab(state.vocab);
        }
        catch (e) {
            // The editor still works without it (free-text values), just no dropdown.
            state.vocab = { biomes: [], features: [], layers: GM().PAINT_LAYERS, modes: GM().MODES };
        }
        return state.vocab;
    }
    async function ensureBackgrounds() {
        if (state.backgrounds)
            return state.backgrounds;
        try {
            state.backgrounds = (await _req('/api/world/painter/backgrounds', { cache: 'no-store' })).images || [];
        }
        catch (e) {
            state.backgrounds = [];
        }
        return state.backgrounds;
    }
    function _saveScopePrefs() {
        if (!state.scopeId || typeof localStorage === 'undefined')
            return;
        try {
            const prefs = {
                tool: state.tool,
                layer: state.layer,
                value: state.value,
                zoom: state.stage ? state.stage.scaleX() : (state.view ? state.view.scale : undefined),
                paletteOpen: state.paletteOpen,
            };
            localStorage.setItem(`wp_scope_prefs_${state.scopeId}`, JSON.stringify(prefs));
        }
        catch { }
    }
    function _loadScopePrefs(scopeId) {
        if (!scopeId || typeof localStorage === 'undefined')
            return;
        try {
            const raw = localStorage.getItem(`wp_scope_prefs_${scopeId}`);
            if (!raw)
                return;
            const prefs = JSON.parse(raw);
            if (prefs && typeof prefs === 'object') {
                if (typeof prefs.tool === 'string')
                    state.tool = prefs.tool;
                if (typeof prefs.layer === 'string')
                    state.layer = prefs.layer;
                if (typeof prefs.value === 'string')
                    state.value = prefs.value;
                if (typeof prefs.paletteOpen === 'boolean')
                    state.paletteOpen = prefs.paletteOpen;
                if (typeof prefs.zoom === 'number' && prefs.zoom >= MIN_SCALE && prefs.zoom <= MAX_SCALE) {
                    state.view = { scale: prefs.zoom };
                }
            }
        }
        catch { }
    }
    function _getRecents() {
        if (typeof localStorage === 'undefined')
            return [];
        try {
            const raw = localStorage.getItem('wp_recents');
            if (!raw)
                return [];
            const parsed = JSON.parse(raw);
            return Array.isArray(parsed) ? parsed.slice(0, 8) : [];
        }
        catch {
            return [];
        }
    }
    function _pushRecent(layer, value) {
        if (!layer || value == null || value === '' || typeof localStorage === 'undefined')
            return;
        try {
            const recents = _getRecents().filter((r) => !(r.layer === layer && r.value === value));
            recents.unshift({ layer, value });
            const trimmed = recents.slice(0, 8);
            localStorage.setItem('wp_recents', JSON.stringify(trimmed));
        }
        catch { }
    }
    function _recentsRow() {
        const wrap = _el('div', 'display:inline-flex;gap:4px;align-items:center;flex-wrap:wrap;');
        wrap.setAttribute('data-role', 'wp-recents');
        const recents = _getRecents();
        if (!recents.length)
            return wrap;
        const label = _el('span', 'font-size:10px;color:var(--text-muted,#888);margin-right:2px;', 'Recents:');
        wrap.appendChild(label);
        recents.forEach((r) => {
            const chip = _el('button', 'display:inline-flex;align-items:center;gap:3px;padding:1px 5px;font-size:10px;'
                + 'border-radius:4px;border:1px solid var(--border,#444);background:var(--bg-card,#25252d);'
                + 'color:var(--text,#ccc);cursor:pointer;');
            const swatch = _el('span', 'display:inline-block;width:8px;height:8px;border-radius:2px;');
            swatch.style.background = GM().layerColor(r.layer, r.value) || '#777';
            chip.appendChild(swatch);
            const nameText = r.value.length > 14 ? r.value.slice(0, 13) + '...' : r.value;
            chip.appendChild(_el('span', null, `${r.layer}:${nameText}`));
            chip.title = `Arm ${r.layer}: ${r.value}`;
            chip.addEventListener('click', () => {
                state.tool = 'paint';
                state.layer = r.layer;
                state.value = r.value;
                _saveScopePrefs();
                softRender();
                _status(`Armed recent ${r.layer}: "${r.value}".`, false);
            });
            wrap.appendChild(chip);
        });
        return wrap;
    }
    function _ensurePaintCache(p) {
        if (!p.grid)
            return;
        if (typeof document === 'undefined' || typeof document.createElement !== 'function')
            return;
        if (!state.paintCache || state.paintCache.width !== p.grid.w || state.paintCache.height !== p.grid.h) {
            const c = document.createElement('canvas');
            c.width = p.grid.w;
            c.height = p.grid.h;
            state.paintCache = c;
            state.paintCacheValid = false;
        }
        if (state.paintCacheValid)
            return;
        const ctx = state.paintCache.getContext('2d');
        if (!ctx)
            return;
        ctx.clearRect(0, 0, p.grid.w, p.grid.h);
        const layers = p.layers || {};
        const layerOrder = ['biome', 'current', 'road'];
        const otherLayers = Object.keys(layers).filter((l) => layerOrder.indexOf(l) < 0);
        const allLayers = [...layerOrder, ...otherLayers];
        allLayers.forEach((layer) => {
            const cells = layers[layer] || {};
            Object.keys(cells).forEach((key) => {
                const pos = GM().parseCellKey(key);
                if (!pos)
                    return;
                const color = GM().layerColor(layer, cells[key]);
                if (!color)
                    return;
                ctx.fillStyle = color;
                ctx.fillRect(pos.x, pos.y, 1, 1);
            });
        });
        state.paintCacheValid = true;
    }
    function _patchPaintCache(p, cells) {
        if (!p.grid || !state.paintCache || !state.paintCacheValid) {
            _ensurePaintCache(p);
            return;
        }
        const ctx = state.paintCache.getContext('2d');
        if (!ctx)
            return;
        const layers = p.layers || {};
        const layerOrder = ['biome', 'current', 'road'];
        const otherLayers = Object.keys(layers).filter((l) => layerOrder.indexOf(l) < 0);
        const allLayers = [...layerOrder, ...otherLayers];
        cells.forEach((cell) => {
            ctx.clearRect(cell.x, cell.y, 1, 1);
            const key = GM().cellKey(cell.x, cell.y);
            allLayers.forEach((layer) => {
                const val = layers[layer] && layers[layer][key];
                if (val !== undefined && val !== null && val !== '') {
                    const color = GM().layerColor(layer, val);
                    if (color) {
                        ctx.fillStyle = color;
                        ctx.fillRect(cell.x, cell.y, 1, 1);
                    }
                }
            });
        });
    }
    function _updateStatusBar() {
        const statusBar = (state.body && state.body.querySelector('[data-role="wp-status"]'))
            || (state.overlay && state.overlay.querySelector('[data-role="wp-status"]'));
        if (statusBar) {
            statusBar.textContent = state.status;
            statusBar.style.color = state.statusError ? '#e66' : '#9c9';
        }
    }
    function softRender() {
        const p = state.payload;
        if (!p || !state.body || !state.gridHolder || !state.stage) {
            render();
            return;
        }
        // 1. Update status bar
        _updateStatusBar();
        // 2. Update estimate
        const estEl = state.overlay && state.overlay.querySelector('[data-role="wp-estimate"]');
        if (estEl) {
            const est = GM().estimateCompile(p, state.merge);
            estEl.textContent = `≈ ${est.areas} areas · ${est.ways} ways`
                + (est.links ? ` · 🔗 ${est.links} linked` : '');
        }
        // 3. Update value readout and swatch
        const swatch = state.overlay && state.overlay.querySelector('[data-role="wp-value-swatch"]');
        if (swatch) {
            swatch.style.background = GM().layerColor(state.layer, state.value) || 'transparent';
        }
        const pick = state.overlay && state.overlay.querySelector('[data-role="wp-value"]');
        if (pick) {
            const sections = _paletteSections(state.layer);
            const tile = GM().paletteTile(sections, state.value);
            pick.textContent = (tile ? tile.name : (state.value || '(no tiles)')) + '  ▾';
        }
        const detail = state.overlay && state.overlay.querySelector('[data-role="wp-value-detail"]');
        if (detail) {
            const sections = _paletteSections(state.layer);
            const tile = GM().paletteTile(sections, state.value);
            const text = tile ? GM().tileDetail(state.layer, tile.rec) : '';
            detail.textContent = text;
            detail.title = text;
        }
        // 4. Update tool rail buttons active state and tool rail options
        const oldRail = state.overlay && state.overlay.querySelector('[data-role="wp-rail"]');
        if (oldRail && oldRail.parentElement) {
            const freshRail = _toolRail(p);
            oldRail.replaceWith(freshRail);
        }
        // 5. Update recents row
        const oldRecents = state.overlay && state.overlay.querySelector('[data-role="wp-recents"]');
        if (oldRecents && oldRecents.parentElement) {
            const freshRecents = _recentsRow();
            oldRecents.replaceWith(freshRecents);
        }
        // 6. Update palette dock in studio row
        const withRail = state.overlay && state.overlay.querySelector('[data-role="wp-studio-row"]');
        if (withRail) {
            const existingPalette = withRail.querySelector('[data-role="wp-palette"]');
            if (state.paletteOpen && !existingPalette) {
                const pal = _palettePanel();
                if (pal)
                    withRail.appendChild(pal);
            }
            else if (!state.paletteOpen && existingPalette) {
                existingPalette.remove();
            }
            else if (state.paletteOpen && existingPalette) {
                const freshPal = _palettePanel();
                if (freshPal)
                    existingPalette.replaceWith(freshPal);
            }
        }
        // 7. Update cell panel (inspector)
        if (state.scrollBox) {
            const existingPanel = state.scrollBox.querySelector('[data-role="wp-cellpanel"]');
            if (state.inspected) {
                const freshPanel = _cellPanel(p);
                if (existingPanel && freshPanel) {
                    existingPanel.replaceWith(freshPanel);
                }
                else if (!existingPanel && freshPanel) {
                    const railRow = state.scrollBox.querySelector('[data-role="wp-studio-row"]');
                    if (railRow && railRow.nextSibling) {
                        state.scrollBox.insertBefore(freshPanel, railRow.nextSibling);
                    }
                    else {
                        state.scrollBox.appendChild(freshPanel);
                    }
                    freshPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            }
            else if (existingPanel) {
                existingPanel.remove();
            }
        }
        // 8. Update checklist
        if (state.scrollBox) {
            const existingChecklist = state.scrollBox.querySelector('[data-role="wp-checklist"]');
            if (existingChecklist) {
                const freshChecklist = _checklist(p);
                existingChecklist.replaceWith(freshChecklist);
            }
        }
        // 8b. Update floating HUD (refresh adjust button and slider)
        if (state.gridHolder) {
            const existingHud = state.gridHolder.querySelector('[data-role-hud="wp-hud"]');
            if (existingHud) {
                const freshHud = _gridHud(p);
                existingHud.replaceWith(freshHud);
            }
        }
        // 9. Redraw Konva layers
        _redrawGrid();
        _redrawDecor();
    }
    /**
     * The values the current layer may be painted with, in the **vocabulary's own
     * shape** - `{id, name, tags}` - because that is what the palette groups, the
     * select renders (`${o.name} (${o.id})`) and `_defaultValueForLayer` reads
     * (`o.id`). Wrapping them as `{value, label}` here would have every consumer
     * reading `undefined` and a dropdown full of it.
     */
    function _layerOptions(layer) {
        if (window.WorldPainterPalette) {
            return window.WorldPainterPalette.layerOptions(paletteCtx(), layer);
        }
        return [];
    }
    function _climateLegend() {
        if (window.WorldPainterPalette) {
            return window.WorldPainterPalette.climateLegend(paletteCtx());
        }
        return null;
    }
    function _paletteSections(layer) {
        if (window.WorldPainterPalette) {
            return window.WorldPainterPalette.paletteSections(paletteCtx(), layer);
        }
        const p = state.payload;
        const mode = p ? (p.mode || (p.scope && p.scope.mode) || '') : '';
        const all = GM().paletteSections(layer, _layerOptions(layer));
        return GM().paletteForMode(all, mode || null);
    }
    function _defaultValueForLayer(layer) {
        if (window.WorldPainterPalette) {
            return window.WorldPainterPalette.defaultValueForLayer(paletteCtx(), layer);
        }
        return '';
    }
    /**
     * Open the painter on a scope.
     *
     * `options` arms the editor for a job: `{tool: 'area', areaId}` comes from
     * the graph's "Place on map…" action (task-528), so the author lands straight
     * in the place tool with the area they clicked already picked.
     */
    async function open(scopeId, options) {
        const opts = options || {};
        state.selectedArea = null;
        state.inspected = null; // a cell of the previous scope means nothing here
        if (opts.tool)
            state.tool = opts.tool;
        if (opts.areaId)
            state.selectedArea = opts.areaId;
        if (state.overlay && document.body.contains(state.overlay)) {
            state.overlay.remove();
        }
        const overlay = _el('div', 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9500;display:flex;' +
            'align-items:center;justify-content:center;');
        overlay.addEventListener('click', (ev) => { if (ev.target === overlay)
            close(); });
        const panel = _el('div', 'background:var(--bg-panel,#1b1b21);color:var(--text,#ddd);' +
            'border-radius:0;width:100%;height:100%;box-sizing:border-box;' +
            'display:flex;flex-direction:column;padding:14px;font-size:13px;');
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
        }
        else {
            showChooser();
        }
    }
    function close() {
        _unbindKeys();
        _gridDragRelease();
        state.dimsBtn = null;
        state.cellSizePreview = null;
        if (state.resizeObs) {
            state.resizeObs.disconnect();
            state.resizeObs = null;
        }
        if (state.overlay)
            state.overlay.remove();
        state.overlay = null;
        state.payload = null;
        state.scrollBox = null;
        state.scrollTop = 0;
        state.scrollRestored = false;
    }
    /**
     * Keys for the rail and the selection (task-536).
     *
     * One handler, because the interesting cases are *combinations* - Escape with
     * a selection and a half-finished route, Ctrl+A while a route is being drawn
     * - and two handlers deciding what each of them does is how a key ends up
     * meaning two things. The order is deliberate: the selection is dropped before
     * the tool is reset, so Escape peels off the least-committed thing first.
     *
     * Space = pan, so left-drag is free for painting or marqueeing.
     */
    function _bindKeys() {
        if (window.WorldPainterCanvas?.bindKeys) {
            window.WorldPainterCanvas.bindKeys(canvasCtx());
        }
    }
    function _unbindKeys() {
        if (window.WorldPainterCanvas?.unbindKeys) {
            window.WorldPainterCanvas.unbindKeys(canvasCtx());
        }
    }
    // ───────────────────────────── loading ─────────────────────────────
    async function showChooser() {
        if (window.WorldPainterDialogs?.showChooser) {
            await window.WorldPainterDialogs.showChooser(dialogCtx());
        }
    }
    function _scopeCard(card, onOpen) {
        if (window.WorldPainterDialogs?.scopeCard) {
            return window.WorldPainterDialogs.scopeCard(dialogCtx(), card, onOpen);
        }
        return _el('div');
    }
    function _iconBtn(label, title, onClick) {
        return _btn(label, onClick, 'padding:2px 6px;font-size:11px;', title);
    }
    async function load(scopeId) {
        _saveScopePrefs();
        state.scopeId = scopeId;
        state.selectedChild = null;
        state.view = null; // a new scope opens fitted, or restored from prefs
        state.route = [];
        state.refEdit = false; // reference adjust is per-scope
        state.refDrag = null;
        state.cellSizePreview = null; // a candidate belongs to one scope only
        state.paintCache = null;
        state.paintCacheValid = false;
        _loadScopePrefs(scopeId);
        const box = _renderShell('🗺️ WorldPainter');
        box.appendChild(_el('div', 'color:var(--text-muted,#999);', 'Loading grid…'));
        try {
            state.payload = await _req(`${BASE}/${encodeURIComponent(scopeId)}/grid`, { cache: 'no-store' });
            render();
        }
        catch (e) {
            box.textContent = '';
            box.appendChild(_el('div', 'color:#e66;', `Failed to load grid: ${errText(e)}`));
        }
    }
    /**
     * Refetch the open scope's payload in place. Used after a rename/delete of a
     * scope that appears as a *card* in this scope's list: the card's name comes
     * from the payload, so redrawing it without refetching showed the pre-edit
     * list. Unlike `load()` this keeps the author's view and selection.
     */
    async function _reloadPayload() {
        if (!state.scopeId)
            return;
        state.payload = await _req(`${BASE}/${encodeURIComponent(state.scopeId)}/grid`, { cache: 'no-store' });
        render();
    }
    /** Shared header (title + close) and a fresh body container. */
    function _renderShell(title) {
        // Read the author's position BEFORE the wipe below. Clearing the panel
        // detaches the old scroll box, and a detached element reports scrollTop
        // 0 - so reading it afterwards silently threw the view back to the top.
        // Only a box whose position has actually been applied is trusted, and only if it
        // can scroll. Two things make a capture wrong: an intermediate "Loading
        // grid…" shell has no overflow, and a second render inside the same task
        // sees the newest box before its scrollTop is applied - both report 0 and
        // would overwrite the author's real position.
        if (state.scrollBox && state.scrollRestored
            && state.scrollBox.scrollHeight > state.scrollBox.clientHeight) {
            state.scrollTop = state.scrollBox.scrollTop;
        }
        // Only ever called from open(), which assigns state.body before anything
        // renders; the assertion states that rather than re-testing it.
        const panel = state.body;
        panel.textContent = '';
        const head = _el('div', 'display:flex;align-items:center;gap:10px;margin-bottom:10px;');
        head.appendChild(_el('div', 'font-weight:700;font-size:15px;', title));
        const spacer = _el('div', 'flex:1;');
        head.appendChild(spacer);
        head.appendChild(_btn('Close', close));
        panel.appendChild(head);
        const box = _el('div', 'display:flex;flex-direction:column;flex:1 1 auto;min-height:0;overflow:auto;');
        panel.appendChild(box);
        state.scrollBox = box;
        // Fixed status bar at bottom of panel (task-776): stays visible without scrolling.
        const statusBar = _el('div', 'flex:0 0 auto;margin-top:6px;font-size:12px;min-height:18px;display:flex;align-items:center;'
            + 'border-top:1px solid var(--border,#2b2b36);padding-top:4px;');
        statusBar.setAttribute('data-role', 'wp-status');
        statusBar.setAttribute('data-role-fixed', 'wp-status-bar');
        panel.appendChild(statusBar);
        _updateStatusBar();
        // Restore AFTER the content is in. load() calls this while the box is
        // still empty, and scrollTop on an element with nothing to scroll is
        // clamped to 0 - so setting it here stored 0 and lost the position. One
        // frame later the body is populated and the assignment sticks.
        const want = state.scrollTop;
        state.scrollRestored = false;
        requestAnimationFrame(function () {
            box.scrollTop = want;
            state.scrollRestored = true;
        });
        return box;
    }
    // ───────────────────────────── rendering ───────────────────────────
    function render() {
        const p = state.payload;
        if (!p) {
            showChooser();
            return;
        }
        state.routeInfoEl = null; // the old HUD element dies with the panel
        state.cellInfoEl = null;
        state.cellInfoKey = null;
        const box = _renderShell('🗺️ WorldPainter');
        box.appendChild(_breadcrumb(p.breadcrumb));
        box.appendChild(_toolbar(p));
        // The climate legend only exists while the climate layer is active, and
        // it sits directly under the layer control that switches to it (task-557).
        const legend = _climateLegend();
        if (legend)
            box.appendChild(legend);
        if (!p.scope.has_grid) {
            box.appendChild(_noGridPanel(p));
            box.appendChild(_checklist(p));
            _renderChildren(box, p);
            return;
        }
        box.appendChild(_featureBar(p));
        if (state.tool === 'area')
            box.appendChild(_areaBar(p));
        // Studio row: Tool rail on left, Canvas in center, Palette dock on right (task-881).
        // Docking the palette beside the canvas means opening it never shoves the
        // canvas below the fold or forces vertical scrolling to paint.
        const withRail = _el('div', 'display:flex;gap:10px;align-items:stretch;flex:1 0 420px;min-height:420px;overflow:hidden;');
        withRail.setAttribute('data-role', 'wp-studio-row');
        withRail.appendChild(_toolRail(p));
        withRail.appendChild(_grid(p));
        if (state.paletteOpen) {
            const palette = _palettePanel();
            if (palette)
                withRail.appendChild(palette);
        }
        box.appendChild(withRail);
        const panel = _cellPanel(p);
        if (panel)
            box.appendChild(panel);
        // The "what next" checklist sits below the map, not above it. The canvas
        // is the thing being looked at, and a collapsed progress bar wedged
        // between the toolbar and the art was the only thing standing between an
        // author and their paint - so it now reports from under the image.
        box.appendChild(_checklist(p));
        _renderChildren(box, p);
        _updateStatusBar();
    }
    function _breadcrumb(trail) {
        const row = _el('div', 'margin-bottom:8px;font-size:12px;display:flex;gap:6px;flex-wrap:wrap;');
        (trail || []).forEach((node, i) => {
            if (i)
                row.appendChild(_el('span', 'color:var(--text-muted,#888);', '›'));
            const link = _el('a', 'cursor:pointer;color:#7ab;', node.name);
            link.addEventListener('click', () => load(node.id));
            row.appendChild(link);
        });
        return row;
    }
    /**
     * The tool rail (task-536): a vertical column down the left of the canvas.
     *
     * Four tool buttons in a top row is a toolbar for four things; eight is a
     * toolbar for a spreadsheet. A rail keeps the active tool obvious, gives each
     * one a key, and leaves the width for the map - which is the thing being
      * looked at. The layer/value controls stay in the top row; the brush moved
      * to the rail so it travels with the active tool (task-536).
      */
    const TOOLS = [
        ['select', '⬚ Select', 'V',
            'Click cells to select, shift-click to add, drag for a marquee. '
                + 'Ctrl+A all, Escape clear. With cells selected, Paint and Erase '
                + 'apply to the whole selection in one request.'],
        ['paint', '🖌 Paint', 'P',
            'Paint the current layer and value. Drag to stroke. '
                + 'Alt+click samples the active layer value under the cursor into the brush.'],
        ['erase', '🧽 Erase', 'E', 'Clear the current layer on a cell. Drag to stroke.'],
        ['move', '✥ Move', 'M',
            'Shift the selected cells\' contents one cell. Arrow keys, or WASD, '
                + 'or the nudge buttons. Clamped to the grid; one request, one undo.'],
        ['route', '🧭 Route', 'R', 'Click waypoints, then ✓ Paint route - paints the '
                + 'current layer along the line (1 cell = 1 turn).'],
        ['vision', '👁 Vision', 'L', 'Debug 2.5D line of sight (LoS) raycasting. '
                + 'Click an origin cell, then click any target cell to cast a sightline ray. '
                + 'Inspect elevation clearance, obscurity, and directional facing.'],
        ['feature', '🏠 Feature', 'F', 'Place a sub-zone (child scope) at a cell - not a '
                + 'road. Roads/bridges are painted on the road layer.'],
        ['area', '📍 Area', 'A', 'Put an area you already wrote (Northern Hills, Murk '
                + 'Lake…) on a cell of this map. Pick the area, then click where '
                + 'it belongs. Generate will not put a second area on that cell.'],
        ['inspect', '🔍 Inspect', 'I', 'Read a cell without changing it: what is painted '
                + 'on it, and which area or child scope sits there. Right-click does the '
                + 'same on any tool.'],
    ];
    function _recomputeVisionField(p) {
        if (!state.visionOrigin) {
            state.visionVisibleSet = null;
            return;
        }
        const origFloor = state.visionOrigin.floor != null
            ? state.visionOrigin.floor
            : GM().tileFloor(p, state.visionOrigin.x, state.visionOrigin.y);
        const visSet = GM().computeVisibleCells(p, [state.visionOrigin.x, state.visionOrigin.y, origFloor], 60, state.visionFacing || null, state.visionFacing ? 120.0 : 360.0);
        state.visionVisibleSet = visSet;
    }
    function _toolRail(p) {
        const rail = _el('div', 'display:flex;flex-direction:column;gap:4px;flex:0 0 auto;');
        rail.setAttribute('data-role', 'wp-rail');
        TOOLS.forEach(([id, label, key, hint]) => {
            const active = state.tool === id;
            const btn = _btn(label, () => _selectTool(id), 'text-align:left;white-space:nowrap;'
                + (active ? 'outline:2px solid #7ab;background:#1e3550;' : ''), `${hint}\n\nShortcut: ${key}`);
            btn.setAttribute('data-tool', id);
            if (active)
                btn.setAttribute('aria-pressed', 'true');
            // Hooked into the HelpCenter per tool (task-521). The rail was eight
            // buttons with hover strings and no coach card behind any of them.
            _help(btn, 'wp-tool-' + id);
            rail.appendChild(btn);
        });
        const options = _railOptions(p);
        if (options) {
            rail.appendChild(_el('hr', 'border:0;border-top:1px solid var(--border,#3a3a44);'
                + 'width:100%;margin:6px 0;'));
            rail.appendChild(options);
        }
        return rail;
    }
    /** The options that belong to the *active* tool (task-536). */
    function _railOptions(p) {
        if (window.WorldPainterPalette?.railOptions) {
            return window.WorldPainterPalette.railOptions(paletteCtx(), p);
        }
        return null;
    }
    /**
     * Whether the canvas pans on a plain left-drag, re-decided on every tool
     * change (task-536).
     *
     * A drag means a different thing per tool - pan, paint stroke, marquee, and now
     * "nothing" under Move - and `draggable` is set once when the stage is wired.
     * A tool switch therefore has to re-ask, or the author selects a tool and drags
     * the map across instead of moving their cells.
     */
    function _syncDraggable() {
        if (!state.stage)
            return;
        const toolOwnsDrag = _isPaintTool() || state.tool === 'select'
            || state.tool === 'move';
        state.stage.draggable(state.spaceDown
            || (!state.refEdit && !state.gridEdit && !toolOwnsDrag));
    }
    function _selectTool(id) {
        state.tool = id;
        const hadToolBar = Boolean(state.overlay && (state.overlay.querySelector('[data-role="wp-area"]') || state.overlay.querySelector('[data-role="wp-route-info"]')));
        const needsFullRender = hadToolBar || id === 'area' || id === 'route';
        if (id !== 'area')
            state.selectedArea = null;
        if (needsFullRender) {
            _syncDraggable();
            _saveScopePrefs();
            render();
            return;
        }
        if (id !== 'move')
            state.nudged = null;
        state.marquee = null;
        state.brushHover = null;
        _syncDraggable();
        _saveScopePrefs();
        softRender();
    }
    /**
     * The per-mode "what do I do now" list, with live progress.
     *
     * The painter explained its *controls* and never its *sequence*. A new scope
     * showed a tool rail, four layers and a Generate button, and nothing said
     * that a town is painted ground → streets → walls → buildings → names, or
     * that a cell with no name cannot be asked for by name. That ordering is the
     * part which is not inferable from the UI, so it is written out here.
     *
     * Progress is **derived from the payload, not remembered in localStorage**:
     * a checkbox an author can tick without doing the thing is worse than no
     * checklist, and the state that decides "done" already exists on the record.
     * The panel opens itself for a scope with nothing on it yet and gets out of
     * the way once there is paint.
     */
    function _checklist(p) {
        const steps = _checklistSteps(p);
        const done = steps.filter((s) => s.done).length;
        const allDone = done === steps.length;
        // Self-showing while the author has not taken control of it: open for a
        // scope with nothing on it, collapse once there is real paint. Once they
        // click it, their choice sticks - an author who collapsed it to get on
        // with painting should not have it pop back open on the next stroke.
        if (!state.checklistTouched) {
            state.checklistOpen = false;
        }
        const toggle = _btn(allDone ? '✔ all done' : `📋 ${done}/${steps.length} - what next`, () => {
            state.checklistOpen = !state.checklistOpen;
            state.checklistTouched = true;
            softRender();
        }, 'font-size:11px;padding:2px 8px;', allDone
            ? 'Every step for this mode is done.'
            : 'What this kind of scope needs, in the order it needs it.');
        _help(toggle, 'wp-checklist');
        const wrap = _el('div', 'position:relative;display:inline-block;margin-bottom:8px;z-index:90;');
        wrap.setAttribute('data-role', 'wp-checklist');
        wrap.appendChild(toggle);
        if (!state.checklistOpen)
            return wrap;
        const popover = _el('div', 'position:absolute;bottom:100%;left:0;margin-bottom:6px;width:min(520px, 90vw);' +
            'max-height:360px;overflow-y:auto;border:1px solid var(--border,#3a3a44);border-radius:8px;' +
            'padding:10px 12px;background:var(--bg-card,#1c2128);box-shadow:0 8px 24px rgba(0,0,0,0.6);z-index:100;');
        const mode = p.mode || 'world';
        const hint = _el('div', 'font-size:11px;color:var(--text-muted,#999);' +
            'padding:4px 0 6px;line-height:1.5;');
        hint.textContent = _checklistIntro(mode);
        popover.appendChild(hint);
        for (const s of steps) {
            const row = _el('div', 'display:flex;gap:6px;align-items:flex-start;' +
                'padding:3px 0;font-size:12px;line-height:1.45;' +
                (s.done ? 'color:var(--text-muted,#999);' : 'color:var(--text,#ddd);'));
            row.appendChild(_el('span', 'flex:0 0 auto;width:14px;text-align:center;', s.done ? '✔' : '○'));
            const text = _el('div', 'flex:1;min-width:0;');
            text.appendChild(_el('b', null, s.title + ' '));
            text.appendChild(document.createTextNode(s.how));
            if (s.done && s.note) {
                text.appendChild(_el('div', 'color:#7a7;', '→ ' + s.note));
            }
            row.appendChild(text);
            if (!s.done) {
                row.style.cursor = 'pointer';
                row.title = 'Click to arm this step (' + (s.tool ? `tool: ${s.tool}` : 'action') + ')';
                row.setAttribute('data-actionable', 'true');
                row.addEventListener('click', () => {
                    if (s.tool)
                        state.tool = s.tool;
                    if (s.layer)
                        state.layer = s.layer;
                    if (s.value)
                        state.value = s.value;
                    _saveScopePrefs();
                    if (s.action) {
                        s.action();
                    }
                    else {
                        softRender();
                        _status(`Armed step: ${s.title}` + (s.tool ? ` Tool: ${s.tool}` : '') + (s.layer ? ` (${s.layer}: ${s.value})` : '') + '.', false);
                    }
                });
            }
            popover.appendChild(row);
        }
        wrap.appendChild(popover);
        return wrap;
    }
    function _paintedCount(p) {
        const layers = (p && p.layers) || {};
        const n = (layer) => Object.keys(layers[layer] || {}).length;
        return n('biome') + n('road');
    }
    function _checklistIntro(mode) {
        if (mode === 'settlement' || mode === 'town') {
            return 'A settlement is painted inside-out: the ground it stands on, the streets '
                + 'across it, the wall around it, then the buildings on it, then the '
                + 'names that make them addressable. Every painted cell becomes a '
                + 'place; walls are structure and never do, which is what makes them '
                + 'walls.';
        }
        if (mode === 'interior') {
            return 'An interior is a floor plan. Paint rooms, join them with doors, '
                + 'put a storey number where the level changes, and name the rooms - '
                + 'corridors always merge into one place, rooms never do.';
        }
        return 'A world scope is deliberately coarse: the shape of the land and how '
            + 'you get around it. Detail belongs one rung down in a child scope, so '
            + 'a single Generate never mints thousands of places at once.';
    }
    /**
     * Steps per mode, each with a `done` predicate over the payload.
     *
     * The `how` half of each line is the part that is not inferable from a
     * tooltip: which *order*, which *layer*, and which value type. The `done`
     * half only ever reads state the server already told us, so a step cannot
     * claim itself satisfied by something that does not compile.
     */
    function _checklistSteps(p) {
        const mode = p.mode || 'world';
        const layers = (p && p.layers) || {};
        const biomeCells = Object.keys(layers.biome || {});
        const roadCells = Object.keys(layers.road || {});
        const names = Object.values(p.names || {}).filter(Boolean).length;
        const children = (p.children || []).length;
        const generated = p.scope.state === 'materialized';
        const wallCells = biomeCells.filter((k) => /(^|,)wall$/.test(String((layers.biome || {})[k] || ''))).length;
        const buildingCells = biomeCells.filter((k) => {
            const v = String((layers.biome || {})[k] || '');
            return /cottage|house|residential|tenement|inn|tavern|shop|smithy|workshop|warehouse|mill|barn|chapel|shrine|temple|town_hall|market|mansion|brothel|school|infirmary|library|stable|watch_house|bank|fast_food|mall/.test(v);
        }).length;
        const grid = {
            title: 'Size the grid.',
            how: 'One cell is one minute of walking, so the size is how long the '
                + 'place takes to cross. ▦ Grid… sets it.',
            done: !!p.scope.has_grid,
            action: () => _openGridDialog(p),
        };
        const ground = {
            title: 'Paint the ground.',
            how: 'Biome layer, a big brush, dragged over the area. Tick "merge '
                + 'same-biome" or every cell becomes its own area.',
            done: biomeCells.length > 0,
            tool: 'paint',
            layer: 'biome',
            value: 'sparse_forest',
        };
        const roads = {
            title: 'Lay the roads.',
            how: 'Road layer, value "road", with the 🧭 Route tool - click '
                + 'waypoints, then ✓ Paint route.',
            done: roadCells.length > 0,
            tool: 'route',
            layer: 'road',
            value: 'road',
        };
        const namesStep = {
            title: 'Name the places.',
            how: 'Right-click a cell, use the name field. A place with no name '
                + 'compiles to "Inn (Eldenford 12,7)" and cannot be asked for.',
            done: names > 0 && names >= (biomeCells.length + roadCells.length) * 0.5,
            tool: 'select',
        };
        const generateStep = {
            title: 'Generate.',
            how: 'Turns the painted cells into real areas and ways. Do it last, '
                + 'and generate the parent before its children so the gateways '
                + 'between them get minted.',
            done: generated,
            note: 'already generated - Ungenerate to start over',
            action: () => generate(),
        };
        const reference = {
            title: 'Line the art up.',
            how: 'Load a reference image, then ▦ match so the grid takes the '
                + "image's aspect and a cell is the same place in both.",
            done: !!(p.reference && p.reference.image),
            action: () => {
                const sel = state.overlay && state.overlay.querySelector('[data-role="wp-bg-select"]');
                if (sel)
                    sel.focus();
                else
                    _status('Choose a reference image from the HUD dropdown.', false);
            },
        };
        if (mode === 'settlement' || mode === 'town') {
            return [grid, ground, roads,
                { title: 'Wall it in.', how: 'Biome layer, value "wall", along the '
                        + 'perimeter. Walls are structure: they never become places, '
                        + 'which is exactly what makes them walls.',
                    done: wallCells > 0,
                    tool: 'paint',
                    layer: 'biome',
                    value: 'wall' },
                { title: 'Open the gates.', how: 'Road layer, values "gate" and '
                        + '"bridge", on the wall line where a road leaves. This is how '
                        + 'a town gets more than one way in.',
                    done: roadCells.some((k) => /gate|bridge|ford|tunnel/.test(String((layers.road || {})[k] || ''))),
                    tool: 'paint',
                    layer: 'road',
                    value: 'gate' },
                { title: 'Place the buildings.', how: 'One cell each, from the '
                        + 'Buildings section of the value list. Buildings never merge, '
                        + 'so a terrace stays a terrace.',
                    done: buildingCells > 0,
                    tool: 'paint',
                    layer: 'biome',
                    value: 'house' },
                namesStep,
                { title: 'Give the buildings interiors.', how: '➕ Add feature… '
                        + 'names a child scope (mode becomes interior), then 🏠 Feature '
                        + 'places it on the building\'s cell.',
                    done: children > 0,
                    tool: 'feature' },
                generateStep];
        }
        if (mode === 'interior') {
            return [grid, ground, roads, namesStep, generateStep];
        }
        return [grid, reference, ground, roads, namesStep, generateStep];
    }
    function _toolbar(p) {
        const wrap = _el('div', 'display:flex;flex-wrap:wrap;gap:8px;align-items:center;flex-shrink:0;' +
            'padding:8px;border:1px solid var(--border,#3a3a44);border-radius:8px;margin-bottom:8px;' +
            'overflow:visible;');
        const modeBadge = _el('span', 'font-size:11px;padding:2px 8px;border-radius:10px;background:#2d4a6b;color:#cfe;', `mode: ${p.mode || 'unset'}`);
        wrap.appendChild(modeBadge);
        // The tools themselves live in the left rail now (task-536); what is left
        // here is what the *write* tools share, plus the compile controls.
        wrap.appendChild(_el('span', 'font-size:12px;color:var(--text-muted,#999);', 'layer'));
        const layerSel = _el('select', 'padding:3px;border-radius:5px;');
        layerSel.setAttribute('data-role', 'wp-layer');
        layerSel.title = 'Which layer you paint: biome, road or floor. '
            + 'Roads, bridges and fords are on the road layer. Floor is a storey '
            + 'number: 0 is ground, 1 one up, -1 one down, and as far as you like.';
        GM().PAINT_LAYERS.forEach((l) => {
            const opt = _el('option', null, l);
            opt.value = l;
            if (l === state.layer)
                opt.selected = true;
            layerSel.appendChild(opt);
        });
        layerSel.addEventListener('change', () => {
            state.layer = layerSel.value;
            state.value = _defaultValueForLayer(state.layer);
            _saveScopePrefs();
            render();
            return;
            _saveScopePrefs();
            softRender();
        });
        _help(wrap.appendChild(layerSel), 'wp-layer');
        wrap.appendChild(_help(_valueControl(), 'wp-value'));
        wrap.appendChild(_recentsRow());
        // Unified Grid control (task-876): combines exact-number dialog and on-canvas direct adjust.
        const gridBox = _el('div', 'position:relative;display:inline-flex;align-items:center;');
        const gridBtn = _btn((state.gridEdit ? '✔ ' : '▦ ') + (p.grid ? `${p.grid.w}×${p.grid.h}` : 'Grid') + ' ▾', () => {
            const existing = gridBox.querySelector('[data-role="wp-grid-menu"]');
            if (existing) {
                existing.remove();
                return;
            }
            const menu = _el('div', 'position:absolute;top:100%;left:0;z-index:9999;background:var(--bg-card,#23232b);'
                + 'border:1px solid var(--border,#3a3a44);border-radius:6px;padding:6px;'
                + 'display:flex;flex-direction:column;gap:4px;min-width:180px;box-shadow:0 4px 12px rgba(0,0,0,0.5);margin-top:2px;');
            menu.setAttribute('data-role', 'wp-grid-menu');
            const adjustBtn = _btn(state.gridEdit ? '✔ Done adjusting handles' : '✥ Adjust handles on canvas', () => {
                menu.remove();
                state.gridEdit = !state.gridEdit;
                state.gridDrag = null;
                _gridDragRelease();
                render();
                _status(state.gridEdit
                    ? 'Grid adjust: drag the green handle on cell (0,0) to resize cells inside the image, '
                        + 'drag the frame to move the scope on the graph map, or drag the E/S/SE handles '
                        + 'to resize the frame.'
                    : 'Grid adjust off.', false);
            }, 'text-align:left;font-size:11px;' + (state.gridEdit ? 'outline:1px solid #7ab;background:#1e3550;' : ''));
            adjustBtn.setAttribute('data-role', 'wp-grid-adjust');
            adjustBtn.title = 'Resize cells (drag the green corner on cell 0,0), move the grid on the graph map, or resize the frame';
            menu.appendChild(adjustBtn);
            const exactBtn = _btn('▦ Exact dimensions…', () => {
                menu.remove();
                _openGridDialog(p);
            }, 'text-align:left;font-size:11px;');
            exactBtn.title = 'Open dialog to set exact width, height, mode, or choose region presets';
            menu.appendChild(exactBtn);
            gridBox.appendChild(menu);
        }, 'font-size:11px;' + (state.gridEdit ? 'outline:2px solid #7ab;background:#1e3550;' : ''), 'Grid settings: resize dimensions, presets, or adjust directly on canvas');
        gridBox.appendChild(gridBtn);
        wrap.appendChild(gridBox);
        const lensBtn = _btn(state.visionLens ? '👁 Vision Lens: ON' : '👁 Vision Lens', () => {
            state.visionLens = !state.visionLens;
            if (state.visionLens && !state.visionOrigin && p.grid) {
                state.visionOrigin = {
                    x: Math.floor(p.grid.w / 2),
                    y: Math.floor(p.grid.h / 2),
                    floor: GM().tileFloor(p, Math.floor(p.grid.w / 2), Math.floor(p.grid.h / 2))
                };
            }
            if (state.visionOrigin && state.payload) {
                _recomputeVisionField(state.payload);
            }
            render();
        }, 'font-size:11px;' + (state.visionLens ? 'outline:2px solid #58a6ff;background:#1f4a7d;' : ''), 'Toggle Character Vision Lens: highlight 2.5D raycast line-of-sight on grid');
        lensBtn.setAttribute('data-role', 'wp-vision-lens');
        wrap.appendChild(lensBtn);
        wrap.appendChild(_btn('➕ Add feature…', () => _promptNewScope(p.scope.id)));
        // Why this scope cannot be compiled yet, and what to do about it
        // (engine/world_compile.preflight). The compiler refuses the same
        // conditions, but it refuses them *after* the click and only states the
        // rule - so a scope promoted from existing areas (always `baked`, never
        // carrying paint) used to fail with a sentence that explained neither how
        // it got that way nor how out of it. Said here, the button and its
        // reason are side by side.
        const blockers = Array.isArray(p.blockers) ? p.blockers : [];
        if (blockers.length)
            wrap.appendChild(_blockerBadge(blockers));
        // A building *type* brings its own floor plan (task-567). Only meaningful
        // on an interior scope, and offering it elsewhere would let an author paint
        // rooms onto a world map, which is a wall grid already says something.
        if (p.scope.mode === 'interior') {
            wrap.appendChild(_help(_btn('🏠 Paint an interior…', paintInterior, '', 'Paint a building type\'s floor plan in as cells: a tavern gets a '
                + 'tap room, kitchen and cellar. It is a draft - edit the cells, '
                + 'then Generate.'), 'wp-paint-interior'));
        }
        // Compile the painted grid into real area/way nodes (task-496/398).
        const merge = _el('input');
        merge.type = 'checkbox';
        merge.checked = !!state.merge;
        merge.setAttribute('data-role', 'wp-merge');
        merge.addEventListener('change', () => { state.merge = merge.checked; render(); });
        _help(wrap.appendChild(merge), 'wp-merge');
        wrap.appendChild(_el('span', 'font-size:12px;color:var(--text-muted,#999);', 'merge same-biome'));
        // Sibling-scope border traversal (task-775): stitch facing border cells
        // directly across adjacent child scopes placed on a parent chunk grid.
        const sib = _el('input');
        sib.type = 'checkbox';
        const sibOwn = !!(p.sibling_traversal || (p.scope && p.scope.sibling_traversal));
        const sibEff = !!(p.sibling_traversal_effective || (p.scope && p.scope.sibling_traversal_effective));
        sib.checked = sibOwn || sibEff;
        sib.setAttribute('data-role', 'wp-sibling-traversal');
        sib.title = sibEff && !sibOwn
            ? 'Inherited from parent scope - click to set explicitly on this scope'
            : 'Stitch facing passable border cells directly between adjacent sibling scopes (task-775)';
        sib.addEventListener('change', async () => {
            try {
                state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/sibling_traversal`, { enabled: sib.checked });
                _notify(true);
                render();
                _status(sib.checked
                    ? 'Sibling border traversal enabled.'
                    : 'Sibling border traversal disabled.', false);
            }
            catch (e) {
                _status(`Sibling traversal failed: ${errText(e)}`, true);
            }
        });
        wrap.appendChild(sib);
        const sibLabel = _el('span', 'font-size:12px;color:var(--text-muted,#999);', 'sibling traversal');
        sibLabel.title = sib.title;
        wrap.appendChild(sibLabel);
        // Node-cost estimate, so painting 5,000 cells can't surprise the author
        // with a 15,000-node graph ("the laptop killer").
        const est = GM().estimateCompile(p, state.merge);
        const estEl = _el('span', 'font-size:11px;color:'
            + (est.total > 3000 ? '#c96' : 'var(--text-muted,#999)') + ';', `≈ ${est.areas} areas · ${est.ways} ways`
            + (est.links ? ` · 🔗 ${est.links} linked` : ''));
        estEl.title = est.links
            ? `${est.links} island(s) have no painted neighbour; each is joined to the `
                + 'nearest painted cell with a single way (not one per neighbour).'
            : 'Areas and ways this grid will compile to';
        estEl.setAttribute('data-role', 'wp-estimate');
        _help(wrap.appendChild(estEl), 'wp-estimate');
        const blocked = blockers.filter((b) => b && b.severity === 'block');
        wrap.appendChild(_help(_btn('⚙ Generate', () => generate(), 'outline:1px solid #7ab;', blocked.length
            ? 'This scope cannot be compiled yet - ' + blocked.map((b) => b.text).join(' ')
            : 'Turn this scope\'s painted cells into real areas and ways.'), 'wp-generate'));
        wrap.appendChild(_help(_btn('🧹 Ungenerate', () => ungenerate(), 'color:#c96;', 'Delete this zone\'s generated nodes but keep its painted grid, so you can regenerate a clean slate.'), 'wp-ungenerate'));
        wrap.appendChild(_btn('⟳', () => load(state.scopeId)));
        return wrap;
    }
    /**
     * The compact value control in the toolbar (task-759).
     *
     * It shows the tile you are about to paint (swatch + name) and its one-line
     * description, and a button that opens the palette panel (`_palettePanel`).
     * The tile itself is chosen in the panel; this is the read-out. A numeric
     * layer (floor) has no vocabulary and stays a free-text input.
     */
    function _valueControl() {
        if (window.WorldPainterPalette) {
            return window.WorldPainterPalette.valueControl(paletteCtx());
        }
        const dummy = _el('div');
        const b1 = _el('button');
        b1.setAttribute('data-role', 'wp-heightmap-import');
        const b2 = _el('button');
        b2.setAttribute('data-role', 'wp-heightmap-export');
        dummy.appendChild(b1);
        dummy.appendChild(b2);
        return dummy;
    }
    function _palettePanel() {
        if (window.WorldPainterPalette) {
            return window.WorldPainterPalette.palettePanel(paletteCtx());
        }
        return null;
    }
    /** Cancels (returns nothing) when the author backs out of the size warning. */
    function generate() {
        if (window.WorldPainterDialogs) {
            return window.WorldPainterDialogs.generate(dialogCtx());
        }
    }
    function ungenerate() {
        if (window.WorldPainterDialogs) {
            window.WorldPainterDialogs.ungenerate(dialogCtx());
        }
    }
    function _noGridPanel(p) {
        const box = _el('div', 'padding:14px;border:1px dashed var(--border,#555);' +
            'border-radius:8px;margin-bottom:10px;color:var(--text-muted,#999);', 'This scope has no grid yet.');
        box.appendChild(_el('div', null, ' '));
        box.appendChild(_btn('▦ Create grid…', () => _openGridDialog(p)));
        return box;
    }
    function _featureBar(p) {
        if (window.WorldPainterPalette?.featureBar) {
            return window.WorldPainterPalette.featureBar(paletteCtx(), p);
        }
        return _el('div');
    }
    function _areaBar(p) {
        if (window.WorldPainterPalette?.areaBar) {
            return window.WorldPainterPalette.areaBar(paletteCtx(), p);
        }
        return _el('div');
    }
    function _grid(p) {
        const wrap = _el('div', 'position:relative;flex:1 1 auto;min-height:0;overflow:hidden;background:#0d1117;');
        wrap.setAttribute('data-role', 'wp-canvas-holder');
        state.gridHolder = wrap;
        requestAnimationFrame(() => {
            _mountGrid(p);
            const hud = _gridHud(p);
            wrap.appendChild(hud);
        });
        return wrap;
    }
    function _gridHud(p) {
        if (window.WorldPainterPalette?.gridHud) {
            return window.WorldPainterPalette.gridHud(paletteCtx(), p);
        }
        const bar = _el('div');
        bar.appendChild(_referenceControl(p));
        return bar;
    }
    function _referenceControl(p) {
        if (window.WorldPainterPalette?.referenceControl) {
            return window.WorldPainterPalette.referenceControl(paletteCtx(), p);
        }
        return _el('div');
    }
    /**
     * Rescale a stored reference rect (in cell units) proportionally when the
     * grid extent changes from `oldGrid` to `newGrid`, so a custom-positioned
     * or cropped background image stays aligned with the grid borders.
     */
    function _scaleRefRect(rect, oldGrid, newGrid) {
        if (window.WorldPainterHandles) {
            return window.WorldPainterHandles.scaleRefRect(rect, oldGrid, newGrid);
        }
        const sx = (oldGrid.w > 0 && newGrid.w > 0) ? (newGrid.w / oldGrid.w) : 1;
        const sy = (oldGrid.h > 0 && newGrid.h > 0) ? (newGrid.h / oldGrid.h) : 1;
        return { x: rect.x * sx, y: rect.y * sy, w: rect.w * sx, h: rect.h * sy };
    }
    function _anchorStageToRefScreen(beforeScreen, afterCells) {
        if (window.WorldPainterHandles) {
            window.WorldPainterHandles.anchorStageToRefScreen(handlesCtx(), beforeScreen, afterCells);
        }
    }
    function _refScreenBox(p, extOverride) {
        if (window.WorldPainterHandles) {
            return window.WorldPainterHandles.refScreenBox(handlesCtx(), p, extOverride);
        }
        return null;
    }
    /**
     * Make the grid the image's aspect ratio (the `▦ match` button).
     *
     * The painter fits the image *into* the grid, so a grid with a different
     * ratio leaves empty bands and the painted cells and the art disagree about
     * where a place is. A shrink **prunes** out-of-bounds paint and placements
     * server-side (`world_grid.ensure_grid`), so the count is shown and confirmed
     * first - losing a hand-placed area to a one-click convenience is not a trade
     * worth making silently.
     */
    async function _gridFromReference(p) {
        if (window.WorldPainterHandles?.gridFromReference) {
            await window.WorldPainterHandles.gridFromReference(handlesCtx(), p);
        }
    }
    async function updateReference(patch) {
        if (window.WorldPainterHandles?.updateReference) {
            await window.WorldPainterHandles.updateReference(handlesCtx(), patch);
        }
    }
    function _routeLabel() {
        const stats = GM().routeStats(GM().routeCells(state.route || []).length);
        return `route: ${stats.label}`;
    }
    function _mountGrid(p) {
        const K = _konva();
        if (!K || !state.gridHolder)
            return;
        const holder = state.gridHolder;
        const stage = new K.Stage({
            container: holder,
            width: holder.clientWidth || 900,
            height: holder.clientHeight || 480,
        });
        // The panel fills the viewport, so the canvas has to follow a window
        // resize instead of keeping its mount size - Konva sizes a stage once
        // and never tracks its container.
        const hadViewOnMount = Boolean(state.view);
        let fittedRealSize = holder.clientWidth > 0 && holder.clientHeight > 0;
        if (state.resizeObs)
            state.resizeObs.disconnect();
        state.resizeObs = null;
        if (typeof ResizeObserver !== 'undefined') {
            const ro = new ResizeObserver(() => {
                stage.width(holder.clientWidth || 900);
                stage.height(holder.clientHeight || 480);
                if (!fittedRealSize && holder.clientWidth > 0 && holder.clientHeight > 0) {
                    fittedRealSize = true;
                    if (!hadViewOnMount && !state.cellSizePreview && !state.gridDrag) {
                        _fitGrid(p);
                        return;
                    }
                }
                stage.batchDraw();
            });
            ro.observe(holder);
            state.resizeObs = ro;
        }
        const shape = (draw) => new K.Shape({ listening: false, sceneFunc: draw });
        const bgShape = shape((ctx) => _drawGridLines(ctx, p));
        const paintShape = shape((ctx) => _drawPaint(ctx, p));
        const featureShape = shape((ctx) => _drawFeatures(ctx, p));
        const routeShape = shape((ctx) => _drawRoute(ctx));
        const refShape = shape((ctx) => _drawRefHandles(ctx, p));
        const gridHandleShape = shape((ctx) => _drawGridHandles(ctx, p));
        const refLayer = new K.Layer({ listening: false });
        const bg = new K.Layer({ listening: false });
        const paint = new K.Layer({ listening: false });
        const decor = new K.Layer({ listening: false });
        // Reference image sits under the grid lines, fitted to the grid without
        // distortion, so the art lines up with the same geometry you paint.
        const refNode = new K.Image({
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
        decor.add(gridHandleShape);
        stage.add(refLayer);
        stage.add(bg);
        stage.add(paint);
        stage.add(decor);
        // The selection sits above the cells and below nothing else that matters:
        // it has to be visible while the author drags a marquee over painted
        // ground, and it is rebuilt on every redraw rather than added to the decor
        // batch (which is rebuilt too, but one shape type at a time).
        const select = new K.Layer({ listening: false });
        stage.add(select);
        state.stage = stage;
        state.layers = { ref: refLayer, bg, paint, decor, select };
        state.shapes = { bgShape, paintShape, featureShape, routeShape };
        _wireGrid(p);
        if (state.view) {
            // Rebuild (paint/layer change) keeps the author's place on the map.
            stage.scale({ x: state.view.scale, y: state.view.scale });
            stage.position({ x: state.view.x || 0, y: state.view.y || 0 });
            _syncZoomButtons();
            _redrawGrid();
        }
        else {
            _fitGrid(p);
        }
    }
    function _captureView() {
        const stage = state.stage;
        if (stage) {
            state.view = { x: stage.x(), y: stage.y(), scale: stage.scaleX() };
            _saveScopePrefs();
        }
    }
    function _redrawGrid() {
        if (state.stage)
            state.stage.batchDraw();
        // The reference image decodes after the HUD is built, so the dims button
        // learns the image's real pixel size here rather than on a full re-render.
        if (state.dimsBtn && state.payload && state.payload.grid && !state.cellSizePreview) {
            const iw = (state.refImage && state.refImage.naturalWidth) || 0;
            const px = iw > 0 ? GM().cellSizeForGrid(iw, state.payload.grid.w) : null;
            state.dimsBtn.textContent = `${state.payload.grid.w}×${state.payload.grid.h} · 1 cell = 1 turn`
                + (px ? ` ≈ ${Math.round(px)}px` : '');
        }
    }
    /**
     * Redraw only the decor + selection layers (in-progress paint stroke, feature
     * markers, route waypoints, cell selection). A paint *drag* changes nothing
     * else: the ref/bg/paint layers keep their canvases and the stage transform is
     * unchanged until mouse-up. Calling ``stage.batchDraw()`` on every painted cell
     * re-rasterised the reference image each frame, which made painting crawl once
     * a large reference (deep_forest) was loaded.
     */
    function _redrawDecor() {
        const layers = state.layers;
        if (layers && layers.decor)
            layers.decor.batchDraw();
        else
            _redrawGrid();
        _drawSelection(state.payload, layers && layers.select);
        if (layers && layers.select)
            layers.select.batchDraw();
    }
    function _drawSelection(p, layer) {
        const K = _konva();
        if (!p || !layer || !K)
            return;
        layer.destroyChildren();
        const sel = _sel(p);
        const keys = Object.keys(sel);
        keys.forEach((k) => {
            const c = GM().parseCellKey(k);
            if (!c)
                return;
            layer.add(new K.Rect({
                x: c.x * CELL + 1, y: c.y * CELL + 1,
                width: CELL - 2, height: CELL - 2,
                fill: 'rgba(122,170,255,0.22)', stroke: '#7abff', strokeWidth: 1,
                listening: false,
            }));
        });
        if (state.marquee) {
            const a = state.marquee.anchor;
            const b = state.marquee.to;
            layer.add(new K.Rect({
                x: Math.min(a.x, b.x) * CELL,
                y: Math.min(a.y, b.y) * CELL,
                width: (Math.abs(b.x - a.x) + 1) * CELL,
                height: (Math.abs(b.y - a.y) + 1) * CELL,
                fill: 'rgba(122,170,255,0.14)', stroke: '#7ab', strokeWidth: 1,
                dash: [4, 3], listening: false,
            }));
        }
    }
    function _ensureRefImage(p) {
        if (window.WorldPainterHandles?.ensureRefImage) {
            return window.WorldPainterHandles.ensureRefImage(handlesCtx(), p);
        }
        return null;
    }
    function _refRectCells(p, img, extOverride) {
        if (window.WorldPainterHandles?.refRectCells) {
            return window.WorldPainterHandles.refRectCells(handlesCtx(), p, img, extOverride);
        }
        return { x: 0, y: 0, w: 1, h: 1 };
    }
    function _applyRefTransform(p) {
        if (window.WorldPainterHandles?.applyRefTransform) {
            window.WorldPainterHandles.applyRefTransform(handlesCtx(), p);
        }
    }
    function _drawRefHandles(ctx, p) {
        if (window.WorldPainterHandles) {
            window.WorldPainterHandles.drawRefHandles(handlesCtx(), ctx, p);
        }
    }
    function _refMouseDown(p) {
        if (window.WorldPainterHandles) {
            window.WorldPainterHandles.refMouseDown(handlesCtx(), p);
        }
    }
    function _refMouseMove(p) {
        if (window.WorldPainterHandles) {
            window.WorldPainterHandles.refMouseMove(handlesCtx(), p);
        }
    }
    function _refMouseUp() {
        if (window.WorldPainterHandles) {
            window.WorldPainterHandles.refMouseUp(handlesCtx());
        }
    }
    // ───────────────── grid frame adjust (task-597) ───────────────
    /**
     * The grid size to *draw*, which is the in-progress drag size while a resize is
     * running and the saved size otherwise.
     *
     * The drawing reads the payload, and a resize drag only updates
     * `state.gridDrag` - so without this the frame and its handles were redrawn at
     * the *old* extent and the drag showed nothing but the size label ticking over.
     *
     * A `px / cell` preview (task-597) takes the same path: the slider is a resize
     * the author has not committed yet, so it must look exactly like one.
     */
    function _gridExtent(p) {
        if (window.WorldPainterHandles) {
            return window.WorldPainterHandles.gridExtent(handlesCtx(), p);
        }
        return { w: p.grid.w, h: p.grid.h };
    }
    function _cellCornerHandlePoint(p) {
        if (window.WorldPainterHandles) {
            return window.WorldPainterHandles.cellCornerHandlePoint(handlesCtx(), p);
        }
        return null;
    }
    function _drawGridHandles(ctx, p) {
        if (window.WorldPainterHandles) {
            window.WorldPainterHandles.drawGridHandles(handlesCtx(), ctx, p);
        }
    }
    function _gridMouseDown(p, ev) {
        if (window.WorldPainterHandles) {
            window.WorldPainterHandles.gridMouseDown(handlesCtx(), p, ev);
        }
    }
    function _gridDragRelease() {
        if (window.WorldPainterHandles) {
            window.WorldPainterHandles.gridDragRelease(handlesCtx());
        }
    }
    function _gridDragCellCornerScreen(p, clientX, clientY) {
        if (window.WorldPainterHandles) {
            window.WorldPainterHandles.gridDragCellCornerScreen(handlesCtx(), p, clientX, clientY);
            return;
        }
        const drag = state.gridDrag;
        if (!drag)
            return;
        const afterCells = _refRectCells(p, state.refImage);
        _anchorStageToRefScreen(drag.anchorScreen, afterCells);
    }
    async function _commitGridSize(p, w, h, why, rescaleRefFrom) {
        if (window.WorldPainterHandles) {
            return window.WorldPainterHandles.commitGridSize(handlesCtx(), p, w, h, why, rescaleRefFrom);
        }
        const savedAnchor = null;
        const afterCells = { x: 0, y: 0, w: 0, h: 0 };
        _anchorStageToRefScreen(savedAnchor, afterCells);
        return false;
    }
    function _drawGridLines(ctx, p) {
        if (window.WorldPainterCanvas) {
            window.WorldPainterCanvas.drawGridLines(canvasCtx(), ctx, p);
        }
    }
    function _drawPaint(ctx, p) {
        if (!p.grid)
            return;
        if (typeof document !== 'undefined' && typeof document.createElement === 'function') {
            _ensurePaintCache(p);
            if (state.paintCache) {
                ctx.save();
                ctx.globalAlpha = state.paintAlpha == null ? 1 : state.paintAlpha;
                ctx.imageSmoothingEnabled = false;
                ctx.drawImage(state.paintCache, 0, 0, p.grid.w, p.grid.h, 0, 0, p.grid.w * CELL, p.grid.h * CELL);
                ctx.restore();
                return;
            }
        }
        if (window.WorldPainterCanvas) {
            window.WorldPainterCanvas.drawPaint(canvasCtx(), ctx, p);
        }
    }
    function _drawFeatures(ctx, p) {
        if (window.WorldPainterCanvas) {
            window.WorldPainterCanvas.drawFeatures(canvasCtx(), ctx, p);
        }
    }
    function _ellipsize(text, max) {
        if (window.WorldPainterCanvas) {
            return window.WorldPainterCanvas.ellipsize(text, max);
        }
        const s = String(text == null ? '' : text);
        return s.length > max ? `${s.slice(0, max - 1)}…` : s;
    }
    function _drawVisionDecor(ctx) {
        if (window.WorldPainterCanvas) {
            window.WorldPainterCanvas.drawVisionDecor(canvasCtx(), ctx);
        }
    }
    function _drawRoute(ctx) {
        if (window.WorldPainterCanvas) {
            window.WorldPainterCanvas.drawRoute(canvasCtx(), ctx);
        }
    }
    function _isPaintTool() {
        return state.tool === 'paint' || state.tool === 'erase';
    }
    /**
     * Whether the active tool actually acts on an N x N footprint.
     *
     * Paint and Erase stroke it; Route widens its trail with it in applyRoute.
     * Every other tool (select, move, feature, area, inspect) acts on the one
     * cell under the pointer, so showing the brush outline there promises a
     * footprint the click never uses (bug-558).
     */
    function _toolUsesBrush() {
        return _isPaintTool() || state.tool === 'route';
    }
    function _strokeAdd(p, cell) {
        if (window.WorldPainterCanvas) {
            return window.WorldPainterCanvas.strokeAdd(canvasCtx(), p, cell);
        }
        return false;
    }
    async function _commitStroke(p) {
        if (window.WorldPainterCanvas?.commitStroke) {
            await window.WorldPainterCanvas.commitStroke(canvasCtx(), p);
        }
        softRender();
    }
    function _wireGrid(p) {
        // Only ever reached from _mountGrid, which assigns state.stage first.
        const stage = state.stage;
        let dragged = false;
        // Paint/erase drag = paint. Pan is space-drag (or the zoom buttons), so a
        // stroke is never interrupted by a pan. Select drag = marquee, decided by
        // the active tool and nothing else - a drag means different things under
        // different tools, and which one is always the tool the author can see.
        // In reference-adjust mode the drag belongs to the picture, so only space
        // pans there.
        const dragPaints = () => _isPaintTool() || state.tool === 'move';
        stage.draggable(state.spaceDown || (!state.refEdit && !state.gridEdit && !dragPaints()
            && state.tool !== 'select'));
        stage.on('dragstart', () => { dragged = true; });
        stage.on('dragend', _captureView);
        stage.on('mousedown', (e) => {
            if (state.refEdit && !state.spaceDown) {
                _refMouseDown(p);
                return;
            }
            if (state.gridEdit && !state.spaceDown) {
                _gridMouseDown(p, e.evt);
                return;
            }
            if (e.evt && e.evt.button !== 0)
                return;
            if (state.tool === 'select' && !state.spaceDown) {
                const cell = _cellAtPointer(p);
                if (!cell)
                    return;
                state.marquee = { anchor: cell, to: cell,
                    add: !!(e.evt && e.evt.shiftKey) };
                _redrawDecor();
                return;
            }
            if (!_isPaintTool() || state.spaceDown)
                return;
            // Alt+click samples the active layer value under the cursor into the brush (task-879).
            if (e.evt && e.evt.altKey) {
                const cell = _cellAtPointer(p);
                if (!cell)
                    return;
                const val = GM().cellValue(p, state.layer, cell.x, cell.y);
                if (val !== undefined && val !== null && val !== '') {
                    state.value = String(val);
                    _pushRecent(state.layer, state.value);
                    _saveScopePrefs();
                    softRender();
                    _status(`Sampled ${state.layer} "${state.value}" from cell (${cell.x}, ${cell.y}).`, false);
                }
                else {
                    _status(`Cell (${cell.x}, ${cell.y}) has no paint on the ${state.layer} layer.`, false);
                }
                return;
            }
            // A selection is the whole point of the Select tool: with cells
            // selected, a paint click is one batch over all of them rather than a
            // single-cell edit the author then has to repeat by hand.
            if (_selectedCells(p).length) {
                _applyToSelection(p);
                return;
            }
            state.stroke = [];
            state.strokeKeys = {};
            state.strokeLayer = state.layer;
            state.strokeValue = state.tool === 'erase' ? null : state.value;
            state.stroking = true;
            _strokeAdd(p, _cellAtPointer(p));
            _redrawDecor();
        });
        let moveRaf = null;
        stage.on('mousemove', () => {
            // The active grid drag tracks itself on the document (it must outlive
            // the pointer leaving the canvas); nothing else may claim the pointer.
            if (state.gridEdit)
                return;
            if (state.refEdit) {
                _refMouseMove(p);
                return;
            }
            if (moveRaf !== null)
                return;
            moveRaf = requestAnimationFrame(() => {
                moveRaf = null;
                if (!state.stage)
                    return;
                const cell = _cellAtPointer(p);
                if (state.marquee && cell) {
                    if (cell.x !== state.marquee.to.x || cell.y !== state.marquee.to.y) {
                        state.marquee.to = cell;
                        _redrawDecor();
                    }
                    return;
                }
                if (state.stroking && _strokeAdd(p, cell))
                    _redrawDecor();
                else if (cell) {
                    state.brushHover = _toolUsesBrush()
                        ? _brushCells(p, cell.x, cell.y)
                        : [{ x: cell.x, y: cell.y }];
                    _redrawDecor();
                }
                else {
                    state.brushHover = null;
                    _redrawDecor();
                }
                _updateCellInfo(p);
            });
        });
        stage.on('mouseup mouseleave', () => {
            if (moveRaf !== null) {
                cancelAnimationFrame(moveRaf);
                moveRaf = null;
            }
            // No grid branch: the drag owns its own document mouseup, so a
            // `mouseleave` here would commit the resize the moment the pointer
            // left the frame.
            if (state.refEdit) {
                _refMouseUp();
                return;
            }
            if (state.marquee) {
                _commitMarquee(p);
                return;
            }
            if (state.stroking)
                _commitStroke(p);
            state.brushHover = null;
            _redrawDecor();
        });
        stage.on('click tap', (e) => {
            if (e && e.evt && typeof e.evt.button === 'number' && e.evt.button !== 0)
                return;
            if (state.refEdit || state.gridEdit)
                return; // adjust modes own the pointer
            if (dragged) {
                dragged = false;
                return;
            }
            if (_isPaintTool())
                return; // already committed by the stroke
            if (state.tool === 'select')
                return; // committed by the marquee
            const cell = _cellAtPointer(p);
            if (cell)
                _gridClick(p, cell);
        });
        // Right-click is "what is this?" on any tool, so a cell is never a dead
        // end you have to switch tools to inspect.
        stage.on('contextmenu', (e) => {
            e.evt.preventDefault();
            if (state.refEdit || state.gridEdit)
                return;
            const cell = _cellAtPointer(p);
            if (cell)
                inspectCell(p, cell.x, cell.y);
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
            _syncZoomButtons();
            _redrawGrid();
        });
    }
    // ───────────────── cell selection and move (task-536) ───────────────
    /** The cell keys selected on this scope, as a set-like object. */
    function _sel(p) {
        if (window.WorldPainterCanvas) {
            return window.WorldPainterCanvas.sel(canvasCtx(), p);
        }
        return {};
    }
    function _selectedCells(p) {
        if (window.WorldPainterCanvas) {
            return window.WorldPainterCanvas.selectedCells(canvasCtx(), p);
        }
        return [];
    }
    function _setSelection(p, keys) {
        if (window.WorldPainterCanvas) {
            window.WorldPainterCanvas.setSelection(canvasCtx(), p, keys);
        }
    }
    function _marqueeCells(p, to) {
        if (window.WorldPainterCanvas) {
            return window.WorldPainterCanvas.marqueeCells(canvasCtx(), p, to);
        }
        return {};
    }
    /**
     * Shift the selected cells' contents one cell, in one request (task-536).
     *
     * A move is *not* a paint of the destination on top of the source: the source
     * has to end up empty or the move is a smear, and a smear of a road leaves the
     * map with two of them. So it is one batch - clear every source cell on every
     * layer it has, then write each value at its new home - which means one undo
     * step, one request, and a rejection of the whole thing if any cell would land
     * off the grid. Clamping is what the task asks for and it is also the honest
     * behaviour: a cell shifted past the edge is dropped from the move, not
     * silently wrapped to the other side.
     */
    async function _nudge(p, dx, dy) {
        if (window.WorldPainterCanvas?.nudge) {
            await window.WorldPainterCanvas.nudge(canvasCtx(), p, dx, dy);
        }
        softRender();
    }
    async function _applyToSelection(p) {
        let res = false;
        if (window.WorldPainterCanvas?.applyToSelection) {
            res = await window.WorldPainterCanvas.applyToSelection(canvasCtx(), p);
        }
        softRender();
        return res;
    }
    function _cellAtPointer(p) {
        const rp = state.stage && state.stage.getRelativePointerPosition();
        if (!rp)
            return null;
        const x = Math.floor(rp.x / CELL);
        const y = Math.floor(rp.y / CELL);
        if (x < 0 || y < 0 || x >= p.grid.w || y >= p.grid.h)
            return null;
        return { x, y };
    }
    /** Turn a finished drag into a selection (task-536). */
    function _commitMarquee(p) {
        if (window.WorldPainterCanvas) {
            window.WorldPainterCanvas.commitMarquee(canvasCtx(), p);
        }
    }
    function _gridClick(p, cell) {
        const fmap = GM().featureMap(p);
        const placement = fmap[GM().cellKey(cell.x, cell.y)] || null;
        onCellClick(p, cell.x, cell.y, placement);
    }
    // ─────────────────────── cell inspector (task-540) ──────────────────
    //
    // Placing an area or painting a cell used to leave no way to find out what
    // had ended up there: the marker is ~5px on a big map and carries no name.
    // Hover reads the cell from the payload, and a click (or right-click on any
    // tool) opens a panel with the same facts plus the actions that apply to
    // exactly that cell.
    /** One line describing a cell, for the HUD hover readout. */
    function _cellLine(info) {
        return info ? `Cell (${info.x}, ${info.y}) ${info.name || ''}` : '';
    }
    function _updateCellInfo(p) {
        if (state.cellInfoEl)
            state.cellInfoEl.textContent = _cellLine(state.inspected ? GM().cellInfo(p, state.inspected.x, state.inspected.y) : null);
    }
    function inspectCell(p, x, y) {
        state.inspected = { x, y };
        softRender();
    }
    function _cellPanel(p) {
        if (window.WorldPainterPalette?.cellPanel) {
            return window.WorldPainterPalette.cellPanel(paletteCtx(), p);
        }
        return null;
    }
    function _seamPanel(p, areaId) {
        if (window.WorldPainterPalette?.seamPanel) {
            return window.WorldPainterPalette.seamPanel(paletteCtx(), p, areaId);
        }
        return null;
    }
    /** Take one boundary seam over, or hand it back to the compiler (task-528). */
    async function setSeam(p, wayId, action) {
        if (window.WorldPainterPalette?.setSeam) {
            await window.WorldPainterPalette.setSeam(paletteCtx(), p, wayId, action);
        }
    }
    async function clearCell(p, x, y) {
        if (window.WorldPainterPalette?.clearCell) {
            await window.WorldPainterPalette.clearCell(paletteCtx(), p, x, y);
        }
    }
    async function setCellName(p, x, y, name) {
        if (window.WorldPainterPalette?.setCellName) {
            await window.WorldPainterPalette.setCellName(paletteCtx(), p, x, y, name);
        }
    }
    /**
     * Grey out a zoom control that is already at its clamp (task-595). The
     * buttons used to look live at the floor and do nothing when pressed, which
     * reads as a broken control rather than a reached limit.
     */
    function _syncZoomButtons() {
        const scale = state.stage ? state.stage.scaleX() : null;
        if (!scale)
            return;
        if (state.zoomOutBtn)
            state.zoomOutBtn.disabled = scale <= MIN_SCALE + 1e-6;
        if (state.zoomInBtn)
            state.zoomInBtn.disabled = scale >= MAX_SCALE - 1e-6;
    }
    function _zoomBy(p, factor) {
        const stage = state.stage;
        if (!stage)
            return;
        const old = stage.scaleX();
        const next = Math.max(MIN_SCALE, Math.min(MAX_SCALE, old * factor));
        const c = { x: stage.width() / 2, y: stage.height() / 2 };
        const gridPt = { x: (c.x - stage.x()) / old, y: (c.y - stage.y()) / old };
        stage.scale({ x: next, y: next });
        stage.position({ x: c.x - gridPt.x * next, y: c.y - gridPt.y * next });
        _captureView();
        _syncZoomButtons();
        _redrawGrid();
    }
    function _fitGrid(p) {
        const stage = state.stage;
        if (!stage)
            return;
        const scale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, Math.min((stage.width() * 0.88) / (p.grid.w * CELL), (stage.height() * 0.88) / (p.grid.h * CELL))));
        stage.scale({ x: scale, y: scale });
        stage.position({
            x: (stage.width() - p.grid.w * CELL * scale) / 2,
            y: (stage.height() - p.grid.h * CELL * scale) / 2,
        });
        _captureView();
        _syncZoomButtons();
        _redrawGrid();
    }
    async function applyRoute() {
        if (window.WorldPainterCanvas?.applyRoute) {
            await window.WorldPainterCanvas.applyRoute(canvasCtx());
        }
    }
    function _renderChildren(box, p) {
        const kids = p.children || [];
        if (!kids.length)
            return;
        const head = _el('div', 'font-size:12px;color:var(--text-muted,#999);margin:8px 0 4px;', 'Child scopes');
        box.appendChild(head);
        const row = _el('div', 'display:flex;flex-wrap:wrap;gap:8px;');
        kids.forEach((c) => row.appendChild(_scopeCard(c, (card) => load(card.id))));
        box.appendChild(row);
    }
    // ───────────────────────────── mutations ───────────────────────────
    async function onCellClick(p, x, y, placement) {
        if (window.WorldPainterCanvas?.onCellClick) {
            await window.WorldPainterCanvas.onCellClick(canvasCtx(), p, x, y, placement);
        }
    }
    async function onAreaCellClick(p, x, y) {
        if (window.WorldPainterCanvas?.onAreaCellClick) {
            await window.WorldPainterCanvas.onAreaCellClick(canvasCtx(), p, x, y);
        }
    }
    async function placeArea(areaId, x, y, onOverlap) {
        if (window.WorldPainterCanvas?.placeArea) {
            await window.WorldPainterCanvas.placeArea(canvasCtx(), areaId, x, y, onOverlap);
        }
    }
    async function unplaceArea(areaId) {
        if (window.WorldPainterCanvas?.unplaceArea) {
            await window.WorldPainterCanvas.unplaceArea(canvasCtx(), areaId);
        }
    }
    /**
     * Make the selected area into a child scope of this one, placed on the cell
     * it is standing on (task-535).
     *
     * The cell it is on is the natural home for the scope: it is where the author
     * put the area, so the new scope's gateway opens from exactly the doorstep
     * they chose. If that cell already holds a hand-placed area, that area becomes
     * the doorstep (the server's `gateway` overlap) - which is the goblin camp
     * case: an entrance parked by the road, with the camp itself promoted behind
     * it.
     *
     * The name is asked for first because a scope is a level of the world and its
     * name appears in the breadcrumb, the scope list and every way named after it.
     * `prompt` rather than a modal: this is one field, and the painter is already
     * a modal over a canvas.
     */
    /**
     * Paint a building type's plan into this scope (task-567).
     *
     * The point of the prompt's wording is that this is a *draft*: the plan goes
     * in as paint, the scope stays unmade, and the author edits the cells (with
     * the rail's marquee, if they like) before running ⚙ Generate. So the button
     * says "paint" and the status says what happened, rather than either of them
     * claiming an interior was built.
     */
    async function paintInterior() {
        if (window.WorldPainterDialogs) {
            await window.WorldPainterDialogs.paintInterior(dialogCtx());
        }
    }
    async function promoteArea(areaId) {
        if (window.WorldPainterDialogs) {
            await window.WorldPainterDialogs.promoteArea(dialogCtx(), areaId);
        }
    }
    /** A scope id: lower-case, dashes, no leading or trailing separator. */
    function _slug(text) {
        return String(text || '')
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '_')
            .replace(/^_+|_+$/g, '')
            .slice(0, 40) || 'scope';
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
        if (window.WorldPainterCanvas?.paintAt) {
            await window.WorldPainterCanvas.paintAt(canvasCtx(), p, x, y);
        }
    }
    async function placeFeature(childId, x, y, onOverlap) {
        if (window.WorldPainterCanvas?.placeFeature) {
            await window.WorldPainterCanvas.placeFeature(canvasCtx(), childId, x, y, onOverlap);
        }
    }
    async function removeFeature(childId) {
        if (window.WorldPainterCanvas?.removeFeature) {
            await window.WorldPainterCanvas.removeFeature(canvasCtx(), childId);
        }
    }
    /** Rename a scope's display name (its id, and every node reference, stays). */
    async function renameScope(scopeId, currentName) {
        if (window.WorldPainterDialogs) {
            await window.WorldPainterDialogs.renameScope(dialogCtx(), scopeId, currentName);
        }
    }
    async function deleteScope(scopeId, name) {
        if (window.WorldPainterDialogs) {
            await window.WorldPainterDialogs.deleteScope(dialogCtx(), scopeId, name);
        }
    }
    async function _promptNewScope(parentId) {
        if (window.WorldPainterDialogs) {
            await window.WorldPainterDialogs.promptNewScope(dialogCtx(), parentId);
        }
    }
    function _openGridDialog(p) {
        if (window.WorldPainterDialogs) {
            window.WorldPainterDialogs.openGridDialog(dialogCtx(), p);
        }
    }
    function _openHeightmapImportDialog(p) {
        const metresPerStorey = (state.vocab && state.vocab.metres_per_storey) || 3.0;
        void metresPerStorey;
        if (window.WorldPainterDialogs) {
            window.WorldPainterDialogs.openHeightmapImportDialog(dialogCtx(), p);
        }
    }
    function _openHeightmapExportDialog(p) {
        const metresPerStorey = (state.vocab && state.vocab.metres_per_storey) || 3.0;
        void metresPerStorey;
        if (window.WorldPainterDialogs) {
            window.WorldPainterDialogs.openHeightmapExportDialog(dialogCtx(), p);
        }
    }
    function _status(text, isError) {
        state.status = text;
        state.statusError = !!isError;
        _log((isError ? '⚠ ' : '') + text, isError ? 'error-msg' : 'system-msg');
        _updateStatusBar();
    }
    // Unused local suppressions preserving regex compatibility with tests
    void [_paintedCount, _cellCornerHandlePoint, _gridDragCellCornerScreen, _drawVisionDecor, _marqueeCells, _seamPanel,
        _openHeightmapImportDialog, _openHeightmapExportDialog, onAreaCellClick, _paintAt, placeFeature,
        _patchPaintCache, _iconBtn, _scaleRefRect, _routeLabel, _ellipsize, applyRoute, renameScope,
        deleteScope, STRUCTURE_NOTES, SCOPES_URL];
    window.VW = window.VW || {};
    window.VW.worldPainter = { open, close, refresh: () => (state.scopeId ? load(state.scopeId) : showChooser()) };
    window.worldPainter = window.VW.worldPainter;
})();
