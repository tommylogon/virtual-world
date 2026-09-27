/**
 * editor.js — WorldPainter 3-mode grid editor (task-495).
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
 * @module worldpainter/editor — WorldPainter grid editing overlay
 * @contributes the 3-mode scope grid editor UI: paint, feature place/move/remove, area placement, cell inspection, drill-down
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
        selectedArea: null,   // area picked by the 📍 Area place tool (task-528)
        // Cell selection and the marquee being dragged (task-536). Keyed by scope
        // id, because a selection is *this map's* selection: switching tools keeps
        // it, switching maps must not smuggle it across.
        selection: {},         // {scopeId: {'x,y': true}}
        marquee: null,         // {anchor: {x, y}, to: {x, y}} while dragging
        nudged: null,          // last move offset, for the status line
        inspected: null,      // {x, y} the cell the inspector panel is showing (task-540)
        cellInfoEl: null,     // HUD hover readout for the cell under the pointer
        cellInfoKey: null,    // last hovered cell+content, to skip pointless DOM writes
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

    /**
     * What each structure kind is *to movement*, in the author's terms (task-562).
     * The cells here never become places, so the panel has to say what they do
     * instead of reporting "biome: wall" and leaving it at that.
     */
    const STRUCTURE_NOTES = {
        solid: 'solid — nothing passes it',
        see_through: 'you can see through it, not walk through it',
        passable: 'a threshold — you go through it',
    };

    // ───────────────────────────── open/close ──────────────────────────

    async function ensureVocab() {
        if (state.vocab) return state.vocab;
        try {
            state.vocab = await _req('/api/world/painter/vocabulary', { cache: 'no-store' });
            // The climates come from the backend, ids and base °C both (task-557);
            // only the colour is local, so a new climate needs no editor change.
            GM().useClimatesFromVocab(state.vocab);
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

    /**
     * The values the current layer may be painted with, in the **vocabulary's own
     * shape** — `{id, name, tags}` — because that is what the palette groups, the
     * select renders (`${o.name} (${o.id})`) and `_defaultValueForLayer` reads
     * (`o.id`). Wrapping them as `{value, label}` here would have every consumer
     * reading `undefined` and a dropdown full of it.
     */
    function _layerOptions(layer) {
        const vocab = state.vocab || {};
        if (layer === 'biome') return (vocab.b || vocab.biomes || []).slice();
        if (layer === 'road') return (vocab.f || vocab.features || []).slice();
        if (layer === 'climate') {
            // Shaped like a record so one renderer serves every layer, with the
            // base °C in the name because that number is the whole point of
            // painting it (task-557) and it otherwise lives only in the report.
            return GM().CLIMATE_IDS.map((id) => {
                const c = GM().CLIMATES[id] || {};
                return {
                    id,
                    name: `${c.label} (${c.base}°C)`,
                    tags: ['climate'],
                };
            });
        }
        return [];
    }

    /** A climate legend, shown while the climate layer is active (task-557). */
    function _climateLegend() {
        if (state.layer !== 'climate') return null;
        const box = _el('div', 'display:flex;gap:6px;align-items:center;flex-wrap:wrap;' +
            'padding:4px 8px;margin-bottom:6px;border:1px solid var(--border,#3a3a44);' +
            'border-radius:6px;font-size:11px;');
        box.setAttribute('data-role', 'wp-climate-legend');
        box.appendChild(_el('span', 'color:var(--text-muted,#999);',
            'compiles to base_temperature:'));
        GM().CLIMATE_IDS.forEach((id) => {
            const c = GM().CLIMATES[id] || {};
            const chip = _el('span',
                'display:inline-flex;align-items:center;gap:4px;padding:1px 6px;'
                + 'border-radius:9px;border:1px solid var(--border,#3a3a44);',
                c.label);
            const swatch = _el('span',
                'display:inline-block;width:9px;height:9px;border-radius:2px;',
                '');
            swatch.style.background = c.color;
            chip.insertBefore(swatch, chip.firstChild);
            chip.title = `${c.label}: ${c.base}°C base, plus the day's curve`;
            box.appendChild(chip);
        });
        box.appendChild(_el('span', 'color:var(--text-muted,#777);',
            '· unpainted is Temperate'));
        box.title = 'A region takes the majority climate of its cells, and a '
            + 'climate boundary never splits an area. Only world scopes compile '
            + 'a climate; a town or interior keeps its own air.';
        return box;
    }

    /**
     * The biome palette, split so a town can be painted (task-561).
     *
     * 47 biomes in one column is unpickable, and the author's question when
     * painting a settlement is not "which biome" but "which *building*". So
     * building types are gathered into one section and sorted by their category
     * (residential, religious, commercial, civic, craft, military, industrial,
     * rural, transport), with the wild terrain above it where it already was. The
     * grouping is cosmetic — a `select` cannot nest, so it is one flat list with
     * "— Buildings —" and "— Category —" separators that cannot be painted.
     *
     * **Rooms** get the same treatment for the same reason, and it matters more
     * here: the indoor vocabulary is *purpose* first (where does a person sleep,
     * where do they cook) and an author drawing a floor plan is asking exactly
     * that question, not "which of the 80 biomes". Rooms sit between the wild
     * terrain and the buildings, because a plan is where terrain gives way to
     * rooms and a building is the thing you arrive at.
     */
    function _biomePalette(layer) {
        const options = _layerOptions(layer);
        if (layer !== 'biome') return options.map((o) => ({ ...o, group: null }));
        const CATEGORIES = ['residential', 'religious', 'commercial', 'civic',
            'craft', 'industrial', 'military', 'rural', 'transport'];
        // A room's purpose, in the order a plan is drawn: arrive, move, then
        // the rooms you pass. Circulation first because it is what everything else
        // connects to, and the two "why people gather" purposes (living, civic)
        // before the service ones, which is the order a reader thinks in.
        const ROOM_PURPOSES = ['circulation', 'living', 'sleeping', 'cooking',
            'eating', 'storage', 'workshop', 'worship', 'records', 'study',
            'trade', 'civic', 'service', 'outdoor'];
        const wild = [];
        const rooms = new Map(ROOM_PURPOSES.map((c) => [c, []]));
        const buildings = new Map(CATEGORIES.map((c) => [c, []]));
        const structure = [];
        for (const option of options) {
            const tags = (option.tags || []).map((t) => String(t).toLowerCase());
            // Structure — wall, void, window, door, stairway — is neither terrain
            // nor a room nor a building, and it is what makes a floor plan mean
            // anything (task-562/568), so it gets its own section rather than
            // being sorted by its category.
            if (tags.includes('not_a_place')) { structure.push({ ...option, group: null }); continue; }
            if (tags.includes('indoor')) {
                const purpose = ROOM_PURPOSES.find((c) => tags.includes(c)) || 'other';
                if (!rooms.has(purpose)) rooms.set(purpose, []);
                rooms.get(purpose).push({ ...option, group: purpose });
                continue;
            }
            if (!tags.includes('building')) { wild.push({ ...option, group: null }); continue; }
            const category = CATEGORIES.find((c) => tags.includes(c)) || 'other';
            if (!buildings.has(category)) buildings.set(category, []);
            buildings.get(category).push({ ...option, group: category });
        }
        const out = wild.slice();
        if ([...rooms.values()].some((g) => g.length)) {
            out.push({ separator: '— Rooms —' });
            for (const purpose of [...ROOM_PURPOSES, 'other']) {
                const group = rooms.get(purpose);
                if (!group || !group.length) continue;
                out.push({ separator: `— ${purpose[0].toUpperCase()}${purpose.slice(1)} —` });
                out.push(...group);
            }
        }
        if (out.length) out.push({ separator: '— Buildings —' });
        for (const category of [...CATEGORIES, 'other']) {
            const group = buildings.get(category);
            if (!group || !group.length) continue;
            out.push({ separator: `— ${category[0].toUpperCase()}${category.slice(1)} —` });
            out.push(...group);
        }
        if (structure.length) {
            out.push({ separator: '— Structure —' });
            out.push(...structure);
        }
        return out;
    }

    function _defaultValueForLayer(layer) {
        // The floor layer is a *storey index* (engine/world_grid.py): 0 is ground,
        // so 1 — "one storey up" — is the only useful value to start dragging
        // with. It used to default to a 0..1 height fraction, which is not a
        // storey and cannot express "eighty floors up".
        if (layer === 'floor') return '1';
        const options = _layerOptions(layer);
        if (!options.length) return '';
        const preferred = { biome: 'sparse_forest', road: 'road' }[layer];
        if (preferred && options.some((o) => o.id === preferred)) return preferred;
        return options[0].id;
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
        state.inspected = null;   // a cell of the previous scope means nothing here
        if (opts.tool) state.tool = opts.tool;
        if (opts.areaId) state.selectedArea = opts.areaId;
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

    /**
     * Keys for the rail and the selection (task-536).
     *
     * One handler, because the interesting cases are *combinations* — Escape with
     * a selection and a half-finished route, Ctrl+A while a route is being drawn
     * — and two handlers deciding what each of them does is how a key ends up
     * meaning two things. The order is deliberate: the selection is dropped before
     * the tool is reset, so Escape peels off the least-committed thing first.
     *
     * Space = pan, so left-drag is free for painting or marqueeing.
     */
    function _bindKeys() {
        _unbindKeys();
        state._keyDown = (e) => {
            const tag = (e.target && e.target.tagName) || '';
            const typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
            const p = state.payload;

            if (e.key === 'Escape') {
                if (typing) return;
                // The selection is the least-committed thing on screen: drop it
                // before dropping a route or resetting the tool.
                if (p && _selectedCells(p).length) {
                    _setSelection(p, {});
                    state.marquee = null;
                    _status('Selection cleared.');
                    _redrawDecor();
                    render();
                    return;
                }
                // Route points and a picked area are half-finished work: drop
                // them and go back to painting rather than leaving the tool armed.
                if (state.tool !== 'paint' || state.route.length || state.selectedArea
                    || state.inspected) {
                    state.tool = 'paint';
                    state.route = [];
                    state.selectedArea = null;
                    state.inspected = null;
                    if (state.routeInfoEl) state.routeInfoEl.textContent = _routeLabel();
                    _redrawDecor();
                    render();
                }
                return;
            }
            if (typing) return;

            if ((e.ctrlKey || e.metaKey) && (e.key || '').toLowerCase() === 'a' && p) {
                e.preventDefault();
                const keys = {};
                for (let y = 0; y < p.grid.h; y += 1) {
                    for (let x = 0; x < p.grid.w; x += 1) keys[GM().cellKey(x, y)] = true;
                }
                _setSelection(p, keys);
                _status(`Selected all ${p.grid.w * p.grid.h} cells.`);
                _redrawDecor();
                render();
                return;
            }
            if (e.ctrlKey || e.metaKey) return;

            const tool = TOOLS.find(
                (t) => t[2].toLowerCase() === (e.key || '').toLowerCase());
            if (tool) { e.preventDefault(); _selectTool(tool[0]); return; }

            // Arrow keys (or WASD) nudge a selection. They only do that when there
            // is one to nudge: with nothing selected an arrow key is the map's to
            // use, and a selection the author cannot see is not worth guessing at.
            const nudge = {
                arrowup: [0, -1], w: [0, -1],
                arrowdown: [0, 1], s: [0, 1],
                arrowleft: [-1, 0], a: [-1, 0],
                arrowright: [1, 0], d: [1, 0],
            }[(e.key || '').toLowerCase()];
            if (nudge && p && _selectedCells(p).length) {
                e.preventDefault();
                _nudge(p, nudge[0], nudge[1]);
                return;
            }

            if (e.code !== 'Space' || state.spaceDown) return;
            state.spaceDown = true;
            _syncDraggable();
            e.preventDefault();
        };
        state._keyUp = (e) => {
            if (e.code !== 'Space') return;
            state.spaceDown = false;
            _syncDraggable();
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
        state.cellInfoEl = null;
        state.cellInfoKey = null;
        const box = _renderShell('🗺️ WorldPainter');

        box.appendChild(_breadcrumb(p.breadcrumb));
        box.appendChild(_toolbar(p));
        // The climate legend only exists while the climate layer is active, and
        // it sits directly under the layer control that switches to it (task-557).
        const legend = _climateLegend();
        if (legend) box.appendChild(legend);

        if (!p.scope.has_grid) {
            box.appendChild(_noGridPanel(p));
            _renderChildren(box, p);
            return;
        }

            box.appendChild(_featureBar(p));
            if (state.tool === 'area') box.appendChild(_areaBar(p));
            // Rail beside the canvas, not above it: the tool column and the map it
            // acts on are read together, and the map gets the width back (task-536).
            const withRail = _el('div', 'display:flex;gap:10px;align-items:flex-start;');
            withRail.appendChild(_toolRail(p));
            withRail.appendChild(_grid(p));
            box.appendChild(withRail);
            const panel = _cellPanel(p);
            if (panel) box.appendChild(panel);
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

    /**
     * The tool rail (task-536): a vertical column down the left of the canvas.
     *
     * Four tool buttons in a top row is a toolbar for four things; eight is a
     * toolbar for a spreadsheet. A rail keeps the active tool obvious, gives each
     * one a key, and leaves the width for the map — which is the thing being
     * looked at. The layer/value/brush controls stay in the top row on purpose:
     * they are not options of one tool but of the four that write paint (paint,
     * erase, route, feature), and putting them in the rail would mean the author
     * switches tools to change a setting that outlives the switch. What the rail
     * *does* own is the options that belong to the active tool: the selection
     * panel under Select, the nudge readout under Move.
     */
    const TOOLS = [
        ['select', '⬚ Select', 'V',
            'Click cells to select, shift-click to add, drag for a marquee. '
            + 'Ctrl+A all, Escape clear. With cells selected, Paint and Erase '
            + 'apply to the whole selection in one request.'],
        ['paint', '🖌 Paint', 'P', 'Paint the current layer and value. Drag to stroke.'],
        ['erase', '🧽 Erase', 'E', 'Clear the current layer on a cell. Drag to stroke.'],
        ['move', '✥ Move', 'M',
            'Shift the selected cells\' contents one cell. Arrow keys, or WASD, '
            + 'or the nudge buttons. Clamped to the grid; one request, one undo.'],
        ['route', '🧭 Route', 'R', 'Click waypoints, then ✓ Paint route — paints the '
            + 'current layer along the line (1 cell = 1 turn).'],
        ['feature', '🏠 Feature', 'F', 'Place a sub-zone (child scope) at a cell — not a '
            + 'road. Roads/bridges are painted on the road layer.'],
        ['area', '📍 Area', 'A', 'Put an area you already wrote (Northern Hills, Murk '
            + 'Lake…) on a cell of this map. Pick the area, then click where '
            + 'it belongs. Generate will not put a second area on that cell.'],
        ['inspect', '🔍 Inspect', 'I', 'Read a cell without changing it: what is painted '
            + 'on it, and which area or child scope sits there. Right-click does the '
            + 'same on any tool.'],
    ];

    function _toolRail(p) {
        const rail = _el('div', 'display:flex;flex-direction:column;gap:4px;flex:0 0 auto;');
        rail.setAttribute('data-role', 'wp-rail');
        TOOLS.forEach(([id, label, key, hint]) => {
            const active = state.tool === id;
            const btn = _btn(label, () => _selectTool(id),
                'text-align:left;white-space:nowrap;'
                + (active ? 'outline:2px solid #7ab;background:#1e3550;' : ''),
                `${hint}\n\nShortcut: ${key}`);
            btn.setAttribute('data-tool', id);
            if (active) btn.setAttribute('aria-pressed', 'true');
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
        const count = _selectedCells(p).length;
        if (state.tool === 'select') {
            const box = _el('div', 'display:flex;flex-direction:column;gap:4px;align-items:flex-start;');
            box.appendChild(_el('span', 'font-size:11px;color:var(--text-muted,#999);',
                count ? `${count} cell${count === 1 ? '' : 's'} selected` : 'no cells selected'));
            box.appendChild(_btn('Select all', () => {
                const cells = {};
                for (let y = 0; y < p.grid.h; y += 1) {
                    for (let x = 0; x < p.grid.w; x += 1) cells[GM().cellKey(x, y)] = true;
                }
                _setSelection(p, cells);
                _status(`Selected all ${p.grid.w * p.grid.h} cells.`);
            }, 'width:100%;', 'Select every cell on this grid (Ctrl+A)'));
            box.appendChild(_btn('Clear', () => {
                _setSelection(p, {});
                _status('Selection cleared.');
            }, 'width:100%;', 'Select nothing (Escape)'));
            if (count) {
                box.appendChild(_btn('Invert', () => {
                    const next = {};
                    for (let y = 0; y < p.grid.h; y += 1) {
                        for (let x = 0; x < p.grid.w; x += 1) {
                            const k = GM().cellKey(x, y);
                            if (!_sel(p)[k]) next[k] = true;
                        }
                    }
                    _setSelection(p, next);
                }, 'width:100%;', 'Select everything you had not selected'));
            }
            return box;
        }
        if (state.tool === 'move') {
            const box = _el('div', 'display:flex;flex-direction:column;gap:4px;align-items:flex-start;');
            box.appendChild(_el('span', 'font-size:11px;color:var(--text-muted,#999);',
                count ? `Move ${count} cell${count === 1 ? '' : 's'}` : 'Select cells first'));
            const grid = _el('div', 'display:grid;grid-template-columns:repeat(3,1fr);gap:2px;');
            grid.appendChild(_el('span'));
            grid.appendChild(_btn('↑', () => _nudge(p, 0, -1), 'padding:2px 6px;', 'Up'));
            grid.appendChild(_el('span'));
            grid.appendChild(_btn('←', () => _nudge(p, -1, 0), 'padding:2px 6px;', 'Left'));
            grid.appendChild(_btn('↓', () => _nudge(p, 0, 1), 'padding:2px 6px;', 'Down'));
            grid.appendChild(_btn('→', () => _nudge(p, 1, 0), 'padding:2px 6px;', 'Right'));
            box.appendChild(grid);
            return box;
        }
        return null;
    }

    /**
     * Whether the canvas pans on a plain left-drag, re-decided on every tool
     * change (task-536).
     *
     * A drag means a different thing per tool — pan, paint stroke, marquee, and now
     * "nothing" under Move — and `draggable` is set once when the stage is wired.
     * A tool switch therefore has to re-ask, or the author selects a tool and drags
     * the map across instead of moving their cells.
     */
    function _syncDraggable() {
        if (!state.stage) return;
        const toolOwnsDrag = _isPaintTool() || state.tool === 'select'
            || state.tool === 'move';
        state.stage.draggable(state.spaceDown || (!state.refEdit && !toolOwnsDrag));
    }

    function _selectTool(id) {
        state.tool = id;
        if (id !== 'area') state.selectedArea = null;
        if (id !== 'move') state.nudged = null;
        state.marquee = null;
        _syncDraggable();
        render();
    }

    function _toolbar(p) {
        const wrap = _el('div', 'display:flex;flex-wrap:wrap;gap:8px;align-items:center;' +
            'padding:8px;border:1px solid var(--border,#3a3a44);border-radius:8px;margin-bottom:8px;');

        const modeBadge = _el('span',
            'font-size:11px;padding:2px 8px;border-radius:10px;background:#2d4a6b;color:#cfe;',
            `mode: ${p.mode || 'unset'}`);
        wrap.appendChild(modeBadge);

        // The tools themselves live in the left rail now (task-536); what is left
        // here is what the *write* tools share, plus the compile controls.
        wrap.appendChild(_el('span', 'font-size:12px;color:var(--text-muted,#999);',
            'layer'));
        const layerSel = _el('select', 'padding:3px;border-radius:5px;');
        layerSel.setAttribute('data-role', 'wp-layer');
        layerSel.title = 'Which layer you paint: biome, road or floor. '
            + 'Roads, bridges and fords are on the road layer. Floor is a storey '
            + 'number: 0 is ground, 1 one up, -1 one down, and as far as you like.';
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
        // A building *type* brings its own floor plan (task-567). Only meaningful
        // on an interior scope, and offering it elsewhere would let an author paint
        // rooms onto a world map, which is a wall grid already says something.
        if (p.scope.mode === 'interior') {
            wrap.appendChild(_btn('🏠 Paint an interior…', paintInterior, '',
                'Paint a building type\'s floor plan in as cells: a tavern gets a '
                + 'tap room, kitchen and cellar. It is a draft — edit the cells, '
                + 'then Generate.'));
        }

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
        const options = _biomePalette(state.layer);
        if (state.layer === 'floor' || !options.filter((o) => !o.separator).length) {
            // No vocabulary (fetch failed) or a numeric layer: free text.
            const input = _el('input',
                'width:130px;padding:3px 6px;border-radius:5px;border:1px solid ' +
                'var(--border,#444);background:var(--bg-card,#2a2a32);color:var(--text,#ddd);');
            input.setAttribute('data-role', 'wp-value');
            input.value = state.value;
            input.placeholder = state.layer === 'floor' ? '+1 / -1' : 'value';
            input.title = state.layer === 'floor'
                ? 'Storey: 0 is ground, 1 is one up, -1 one down. Unbounded — 3 for a '
                  + 'room three storeys up, 80 for a tower, -900 for a hole.'
                : `Value painted on the ${state.layer} layer.`;
            input.addEventListener('input', () => { state.value = input.value; });
            return input;
        }
        // A real id, not free text — a mistyped biome silently compiles a barren
        // area, so the valid ids are the only choices.
        const sel = _el('select', 'padding:3px;border-radius:5px;min-width:160px;');
        sel.setAttribute('data-role', 'wp-value');
        const paintable = options.filter((o) => !o.separator);
        const ids = paintable.map((o) => o.id);
        if (ids.indexOf(state.value) < 0) state.value = ids[0];
        // A separator is a disabled option rather than a group: `select` cannot
        // nest, and a disabled option cannot be painted, so the section headers
        // can never be chosen by accident.
        options.forEach((o) => {
            if (o.separator) {
                const sep = _el('option', null, o.separator);
                sep.disabled = true;
                sep.value = '';
                sel.appendChild(sep);
                return;
            }
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

    /**
     * The place tool's picker (task-528/541): the areas that can go on a cell of
     * THIS map, grouped by scope. Only shown while the tool is active, so the
     * painter's default surface stays as it was.
     *
     * Grouping is the point: a flat list of every unplaced area in the world made
     * a child scope's interior look like it belonged on the world map.
     */
    function _areaBar(p) {
        const wrap = _el('div', 'display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px;');
        wrap.appendChild(_el('span', 'font-size:12px;color:var(--text-muted,#999);', 'Area:'));
        const sel = _el('select', 'padding:3px;border-radius:5px;min-width:200px;');
        sel.setAttribute('data-role', 'wp-area');
        const none = _el('option', null, '— pick an area to place —');
        none.value = '';
        sel.appendChild(none);
        const groups = GM().areaGroups(p, state.selectedArea);
        groups.forEach((g) => {
            const og = _el('optgroup');
            og.label = g.key === 'elsewhere'
                ? `${g.label} — picking one moves it here`
                : g.label;
            g.areas.forEach((a) => {
                const where = a.placedHere ? ` (${a.placedHere.x},${a.placedHere.y})` : '';
                const opt = _el('option', null, a.name + where);
                opt.value = a.id;
                if (a.id === state.selectedArea) opt.selected = true;
                og.appendChild(opt);
            });
            sel.appendChild(og);
        });
        sel.addEventListener('change', () => {
            state.selectedArea = sel.value || null;
            render();
        });
        wrap.appendChild(sel);
        if (!groups.length) {
            wrap.appendChild(_el('span', 'font-size:11px;color:var(--text-muted,#999);',
                `No areas available here — every area of “${p.scope.name}” already sits on a map.`));
        } else {
            wrap.appendChild(_el('span', 'font-size:11px;color:var(--text-muted,#999);',
                'Then click a cell. Click a placed 📍 to take it off the map again.'));
        }
        // A 200x133 world draws cells about 5px wide, so the marker cannot carry
        // a name. The list is how you see what is where: name + cell, and picking
        // one lets you move it.
        const placedHere = (p.area_placements || []).filter(
            (a) => !groups.some((g) => g.areas.some((x) => x.id === a.id)));
        if (placedHere.length) {
            const list = _el('div', 'display:flex;flex-wrap:wrap;gap:6px;width:100%;margin-top:2px;');
            placedHere.forEach((a) => {
                const chip = _btn(`📍 ${a.name} (${a.x},${a.y})`, () => {
                    state.selectedArea = a.id;
                    render();
                }, 'font-size:11px;padding:1px 7px;border-radius:10px;' +
                    'border-color:#2f7d5a;color:#9fd8bd;', `Move "${a.name}" — click, then click a new cell`);
                list.appendChild(chip);
            });
            wrap.appendChild(list);
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
        // `flex:1 1 auto; min-width:0` is load-bearing since the rail moved beside
        // the grid (task-536). This element used to be a child of the panel's
        // *column* flex box, where `align-items:stretch` gave it the full width for
        // free; as a flex item in a **row** it takes its content width instead, and
        // its only child is the absolutely-positioned holder, which contributes
        // nothing — so without this the wrapper collapsed to 0px, the 900px canvas
        // overflowed a zero-width box, and the grid simply did not appear.
        // `min-width:0` is the other half: a flex item's default `min-width:auto`
        // refuses to shrink below its content, which fights the zoom buttons.
        const wrap = _el('div',
            'flex:1 1 auto;min-width:0;position:relative;height:480px;'
            + 'border:1px solid var(--border,#3a3a44);'
            + 'border-radius:8px;background:#0d0d11;overflow:hidden;margin-bottom:10px;');
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
        // What the cell under the pointer holds (task-540). A marker on a 200x133
        // world is ~5px and carries no name, so this is the only way to tell a
        // painted cell from a placed area while moving the mouse.
        const readout = _el('span', 'font-size:11px;color:#9ab;margin-left:6px;' +
            'max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;');
        readout.setAttribute('data-role', 'wp-cellinfo');
        readout.textContent = 'hover a cell to read it';
        state.cellInfoEl = readout;
        hud.appendChild(readout);
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

    /**
     * Make the grid the image's aspect ratio (the `▦ match` button).
     *
     * The painter fits the image *into* the grid, so a grid with a different
     * ratio leaves empty bands and the painted cells and the art disagree about
     * where a place is. A shrink **prunes** out-of-bounds paint and placements
     * server-side (`world_grid.ensure_grid`), so the count is shown and confirmed
     * first — losing a hand-placed area to a one-click convenience is not a trade
     * worth making silently.
     */
    async function _gridFromReference(p) {
        const img = state.refImage;
        if (!img || !img.naturalWidth) { _status('Load a reference image first.'); return; }
        const next = GM().gridForImageAspect(p.grid && p.grid.w, img.naturalWidth, img.naturalHeight);
        if (!next) { _status('That image has no readable size — try another file.', true); return; }
        const stranded = GM().strandedCount(p, next.w, next.h);
        if (stranded > 0) {
            const go = window.confirm(
                `Match the grid to the image (${img.naturalWidth}×${img.naturalHeight})?\n\n`
                + `The grid becomes ${next.w}×${next.h} cells, and ${stranded} painted cell(s) or `
                + `placement(s) currently outside it will be removed. This can be undone.`);
            if (!go) return;
        }
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid`,
                { w: next.w, h: next.h, cell_scale: (p.grid && p.grid.cell_scale) || 1, mode: p.mode });
            state.view = null;   // refit to the new aspect
            _status(`Grid set to ${next.w}×${next.h} (image aspect ${img.naturalWidth}×${img.naturalHeight})`
                + (stranded ? `, ${stranded} out-of-bounds cell(s) removed` : '') + '.', false);
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
        // The selection sits above the cells and below nothing else that matters:
        // it has to be visible while the author drags a marquee over painted
        // ground, and it is rebuilt on every redraw rather than added to the decor
        // batch (which is rebuilt too, but one shape type at a time).
        const select = new window.Konva.Layer({ listening: false });
        stage.add(select);
        state.stage = stage;
        state.layers = { ref: refLayer, bg, paint, decor, select };
        state.shapes = { bgShape, paintShape, featureShape, routeShape };
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
     * Redraw only the decor + selection layers (in-progress paint stroke, feature
     * markers, route waypoints, cell selection). A paint *drag* changes nothing
     * else: the ref/bg/paint layers keep their canvases and the stage transform is
     * unchanged until mouse-up. Calling ``stage.batchDraw()`` on every painted cell
     * re-rasterised the reference image each frame, which made painting crawl once
     * a large reference (deep_forest) was loaded.
     */
    function _redrawDecor() {
        const layers = state.layers;
        if (layers && layers.decor) layers.decor.batchDraw();
        else _redrawGrid();
        _drawSelection(state.payload, layers && layers.select);
        if (layers && layers.select) layers.select.batchDraw();
    }

    function _drawSelection(p, layer) {
        if (!p || !layer) return;
        layer.destroyChildren();
        const sel = _sel(p);
        const keys = Object.keys(sel);
        keys.forEach((k) => {
            const c = GM().parseCellKey(k);
            if (!c) return;
            layer.add(new window.Konva.Rect({
                x: c.x * CELL + 1, y: c.y * CELL + 1,
                width: CELL - 2, height: CELL - 2,
                fill: 'rgba(122,170,255,0.22)', stroke: '#7abff', strokeWidth: 1,
                listening: false,
            }));
        });
        if (state.marquee) {
            const a = state.marquee.anchor;
            const b = state.marquee.to;
            layer.add(new window.Konva.Rect({
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
        // Placed areas (task-528) sit in the same decor layer but are a different
        // kind of thing — a node that already exists, not a child scope — so they
        // get their own colour and a corner notch instead of the house glyph.
        (p.area_placements || []).forEach((a) => {
            const selected = a.id === state.selectedArea;
            ctx.fillStyle = selected ? '#f5c542' : '#2f7d5a';
            ctx.fillRect(a.x * CELL + 2, a.y * CELL + 2, CELL - 4, CELL - 4);
            ctx.strokeStyle = '#d9f2e5';
            ctx.lineWidth = 1;
            ctx.strokeRect(a.x * CELL + 2.5, a.y * CELL + 2.5, CELL - 5, CELL - 5);
            // A name is worth showing when the cell is big enough to hold one;
            // at 1x the map is a mosaic and only the marker reads.
            if (CELL >= 26) {
                ctx.fillStyle = '#d9f2e5';
                ctx.font = '9px sans-serif';
                ctx.fillText(_ellipsize(a.name, 12), a.x * CELL + CELL / 2,
                    a.y * CELL + CELL + 8);
            }
        });
        ctx.restore();
    }

    function _ellipsize(text, max) {
        const s = String(text == null ? '' : text);
        return s.length > max ? `${s.slice(0, max - 1)}…` : s;
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
        // stroke is never interrupted by a pan. Select drag = marquee, decided by
        // the active tool and nothing else — a drag means different things under
        // different tools, and which one is always the tool the author can see.
        // In reference-adjust mode the drag belongs to the picture, so only space
        // pans there.
        const dragPaints = () => _isPaintTool() || state.tool === 'move';
        stage.draggable(state.spaceDown || (!state.refEdit && !dragPaints()
            && state.tool !== 'select'));        stage.on('dragstart', () => { dragged = true; });
        stage.on('dragend', _captureView);

        stage.on('mousedown', (e) => {
            if (state.refEdit && !state.spaceDown) { _refMouseDown(p); return; }
            if (e.evt && e.evt.button !== 0) return;
            if (state.tool === 'select' && !state.spaceDown) {
                const cell = _cellAtPointer(p);
                if (!cell) return;
                state.marquee = { anchor: cell, to: cell,
                    add: !!(e.evt && e.evt.shiftKey) };
                _redrawDecor();
                return;
            }
            if (!_isPaintTool() || state.spaceDown) return;
            // A selection is the whole point of the Select tool: with cells
            // selected, a paint click is one batch over all of them rather than a
            // single-cell edit the author then has to repeat by hand.
            if (_selectedCells(p).length) { _applyToSelection(p); return; }
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
            const cell = _cellAtPointer(p);
            if (state.marquee && cell) {
                if (cell.x !== state.marquee.to.x || cell.y !== state.marquee.to.y) {
                    state.marquee.to = cell;
                    _redrawDecor();
                }
                return;
            }
            if (state.stroking && _strokeAdd(p, cell)) _redrawDecor();
            _updateCellInfo(p);
        });
        stage.on('mouseup mouseleave', () => {
            if (state.refEdit) { _refMouseUp(); return; }
            if (state.marquee) { _commitMarquee(p); return; }
            if (state.stroking) _commitStroke(p);
        });

        stage.on('click tap', () => {
            if (state.refEdit) return;    // adjust mode owns the pointer
            if (dragged) { dragged = false; return; }
            if (_isPaintTool()) return;   // already committed by the stroke
            if (state.tool === 'select') return;   // committed by the marquee
            const cell = _cellAtPointer(p);
            if (cell) _gridClick(p, cell);
        });
        // Right-click is "what is this?" on any tool, so a cell is never a dead
        // end you have to switch tools to inspect.
        stage.on('contextmenu', (e) => {
            e.evt.preventDefault();
            if (state.refEdit) return;
            const cell = _cellAtPointer(p);
            if (cell) inspectCell(p, cell.x, cell.y);
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
    }

    // ───────────────── cell selection and move (task-536) ───────────────

    /** The cell keys selected on this scope, as a set-like object. */
    function _sel(p) {
        const id = (p && p.scope && p.scope.id) || state.scopeId || '';
        if (!state.selection[id]) state.selection[id] = {};
        return state.selection[id];
    }

    function _selectedCells(p) {
        return Object.keys(_sel(p)).map((k) => GM().parseCellKey(k))
            .filter(Boolean)
            .map((c) => ({ x: c.x, y: c.y }));
    }

    function _setSelection(p, keys) {
        _sel(p);
        state.selection[(p && p.scope && p.scope.id) || state.scopeId] = keys;
    }

    /** The cells a marquee from the anchor to `to` covers, clipped to the grid. */
    function _marqueeCells(p, to) {
        const a = (state.marquee && state.marquee.anchor) || to;
        const x0 = Math.max(0, Math.min(a.x, to.x));
        const x1 = Math.min(p.grid.w - 1, Math.max(a.x, to.x));
        const y0 = Math.max(0, Math.min(a.y, to.y));
        const y1 = Math.min(p.grid.h - 1, Math.max(a.y, to.y));
        const out = {};
        for (let y = y0; y <= y1; y += 1) {
            for (let x = x0; x <= x1; x += 1) out[GM().cellKey(x, y)] = true;
        }
        return out;
    }

    /**
     * Shift the selected cells' contents one cell, in one request (task-536).
     *
     * A move is *not* a paint of the destination on top of the source: the source
     * has to end up empty or the move is a smear, and a smear of a road leaves the
     * map with two of them. So it is one batch — clear every source cell on every
     * layer it has, then write each value at its new home — which means one undo
     * step, one request, and a rejection of the whole thing if any cell would land
     * off the grid. Clamping is what the task asks for and it is also the honest
     * behaviour: a cell shifted past the edge is dropped from the move, not
     * silently wrapped to the other side.
     */
    async function _nudge(p, dx, dy) {
        const cells = _selectedCells(p);
        if (!cells.length) { _status('Nothing selected — use the ⬚ Select tool first.', true); return; }
        const layers = GM().PAINT_LAYERS;
        const layerCells = {};
        layers.forEach((l) => { layerCells[l] = p.layers[l] || {}; });
        const edits = [];
        const moving = [];
        cells.forEach((c) => {
            const nx = c.x + dx;
            const ny = c.y + dy;
            if (nx < 0 || ny < 0 || nx >= p.grid.w || ny >= p.grid.h) return;   // clamped off
            moving.push({ from: c, to: { x: nx, y: ny } });
        });
        if (!moving.length) {
            _status('The whole selection is against that edge — nowhere to move it.');
            return;
        }
        // Clear first, then write: a value moving one cell east must not be
        // cleared by its own neighbour's clear on the next step of the same batch.
        moving.forEach(({ from }) => layers.forEach((l) => {
            const k = GM().cellKey(from.x, from.y);
            if (layerCells[l][k] != null) {
                edits.push({ layer: l, x: from.x, y: from.y, value: null });
            }
        }));
        moving.forEach(({ from, to }) => layers.forEach((l) => {
            const k = GM().cellKey(from.x, from.y);
            const value = layerCells[l][k];
            if (value != null) edits.push({ layer: l, x: to.x, y: to.y, value });
        }));
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`,
                { edits });
            const next = {};
            moving.forEach(({ to }) => { next[GM().cellKey(to.x, to.y)] = true; });
            _setSelection(p, next);
            const dropped = cells.length - moving.length;
            _status(`Moved ${moving.length} cell${moving.length === 1 ? '' : 's'}`
                + (dropped ? `, ${dropped} left at the edge.` : '.'));
            _notify(true);
            render();
        } catch (e) {
            _status(`Move failed: ${e.message || e}`, true);
        }
    }

    /** Paint the active value (or erase) across the whole selection, one request. */
    async function _applyToSelection(p) {
        const cells = _selectedCells(p);
        if (!cells.length) return false;
        const layer = state.layer;
        const value = state.tool === 'erase' ? null : state.value;
        if (state.tool === 'paint' && (value == null || value === '')) {
            _status('Pick a value to paint first.', true);
            return true;
        }
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`,
                { edits: cells.map((c) => ({ layer, x: c.x, y: c.y, value })) });
            _status(`${state.tool === 'erase' ? 'Cleared' : 'Painted'} ${cells.length} `
                + `cell${cells.length === 1 ? '' : 's'} on ${layer}.`);
            _notify(true);
            render();
        } catch (e) {
            _status(`${state.tool === 'erase' ? 'Clear' : 'Paint'} failed: ${e.message || e}`, true);
        }
        return true;
    }

    /** Key handling for the rail: one key per tool, plus selection and nudges. */
    function _wireKeys() {
        document.addEventListener('keydown', (e) => {
            if (!state.body || !state.scopeId) return;
            const tag = (e.target && e.target.tagName) || '';
            if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
            if (e.ctrlKey || e.metaKey) {
                if ((e.key || '').toLowerCase() === 'a') {
                    e.preventDefault();
                    const p = state.payload;
                    if (!p) return;
                    const keys = {};
                    for (let y = 0; y < p.grid.h; y += 1) {
                        for (let x = 0; x < p.grid.w; x += 1) keys[GM().cellKey(x, y)] = true;
                    }
                    _setSelection(p, keys);
                    _status(`Selected all ${p.grid.w * p.grid.h} cells.`);
                    render();
                }
                return;
            }
            const tool = TOOLS.find(([, , key]) => key.toLowerCase() === (e.key || '').toLowerCase());
            if (tool) { e.preventDefault(); _selectTool(tool[0]); return; }
            const nudge = { arrowup: [0, -1], w: [0, -1], arrowdown: [0, 1], s: [0, 1],
                arrowleft: [-1, 0], a: [-1, 0], arrowright: [1, 0], d: [1, 0] }[(e.key || '').toLowerCase()];
            if (nudge && _selectedCells(state.payload).length) {
                e.preventDefault();
                _nudge(state.payload, nudge[0], nudge[1]);
                return;
            }
            if (e.key === 'Escape') {
                _setSelection(state.payload, {});
                state.marquee = null;
                _status('Selection cleared.');
                render();
            }
        });
    }

    function _cellAtPointer(p) {
        const rp = state.stage && state.stage.getRelativePointerPosition();
        if (!rp) return null;
        const x = Math.floor(rp.x / CELL);
        const y = Math.floor(rp.y / CELL);
        if (x < 0 || y < 0 || x >= p.grid.w || y >= p.grid.h) return null;
        return { x, y };
    }

    /** Turn a finished drag into a selection (task-536). */
    function _commitMarquee(p) {
        const drag = state.marquee;
        state.marquee = null;
        if (!drag) return;
        const keys = _marqueeCells(p, drag.to);
        const k = GM().cellKey(drag.anchor.x, drag.anchor.y);
        const single = Object.keys(keys).length === 1;
        if (drag.add) {
            // Shift adds to what was already selected; it never clears, which is
            // the whole point of holding shift.
            _setSelection(p, Object.assign({}, _sel(p), keys));
        } else if (single && _sel(p)[k]) {
            // A click on an already-selected cell takes it back. The same gesture
            // that made the selection removes it, so there is no state where the
            // only way out of a stray selection is a keyboard shortcut.
            const next = { ..._sel(p) };
            delete next[k];
            _setSelection(p, next);
        } else {
            _setSelection(p, keys);
        }
        const n = Object.keys(_sel(p)).length;
        _status(n ? `${n} cell${n === 1 ? '' : 's'} selected.`
            : 'Selection cleared.');
        _redrawDecor();
        render();
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
        if (!info) return '';
        if (info.empty) return `(${info.x},${info.y}) — nothing here`;
        const bits = [];
        // The author's name leads, because it is the thing they wrote (task-560);
        // the paint layers are the evidence for it.
        if (info.name) bits.push(info.name);
        else if (info.biome) bits.push(String(info.biome).replace(/_/g, ' '));
        if (info.road) bits.push(String(info.road).replace(/_/g, ' '));
        // A structure cell says what it is, because it is not a place and the
        // author needs to know that before generating (task-562).
        if (info.kind) bits.push(STRUCTURE_NOTES[info.kind] || info.kind);
        // A building without an interior says so on hover, because "the door is
        // locked" is a thing the author wants to notice *while* painting, not
        // discover in play (task-563).
        if (info.enter && !info.child) bits.push(info.enter);
        if (info.floor !== null) bits.push(GM().floorLabel(info.floor));
        if (info.area) bits.push(`📍 ${info.area.name}`);
        if (info.child) bits.push(`🏠 ${info.child.name || info.child.id}`);
        return `(${info.x},${info.y}) ${bits.join(' · ')}`;
    }

    function _updateCellInfo(p) {
        const el = state.cellInfoEl;
        if (!el) return;
        const cell = _cellAtPointer(p);
        const info = cell ? GM().cellInfo(p, cell.x, cell.y, state.vocab) : null;
        // Konva fires mousemove per pixel; only touch the DOM when the cell or
        // its content actually changed.
        const key = info ? `${info.key}|${info.name}|${info.biome}|${info.road}|${info.floor}|` +
            `${info.area ? info.area.id : ''}|${info.child ? info.child.id : ''}` : '';
        if (key === state.cellInfoKey) return;
        state.cellInfoKey = key;
        el.textContent = _cellLine(info) || 'hover a cell to read it';
    }

    function inspectCell(p, x, y) {
        state.inspected = { x, y };
        render();
    }

    function _cellPanel(p) {
        const at = state.inspected;
        if (!at || !p.scope.has_grid) return null;
        const info = GM().cellInfo(p, at.x, at.y, state.vocab);
        const wrap = _el('div', 'border:1px solid var(--border,#3a3a44);border-radius:8px;' +
            'padding:8px;margin-bottom:10px;font-size:12px;');
        wrap.setAttribute('data-role', 'wp-cellpanel');
        const head = _el('div', 'display:flex;gap:8px;align-items:center;flex-wrap:wrap;');
        head.appendChild(_el('strong', null, `Cell (${info.x},${info.y})`));
        head.appendChild(_el('span', 'color:var(--text-muted,#999);',
            info.empty ? 'nothing on this cell' : 'what is on this cell'));
        head.appendChild(_btn('✕', () => { state.inspected = null; render(); },
            'margin-left:auto;padding:1px 7px;', 'Close the cell panel'));
        wrap.appendChild(head);

        const rows = _el('div', 'display:flex;flex-direction:column;gap:2px;margin-top:6px;');
        const row = (label, value) => {
            const r = _el('div', 'display:flex;gap:6px;align-items:baseline;');
            r.appendChild(_el('span', 'color:var(--text-muted,#999);min-width:78px;', label));
            r.appendChild(_el('span', null, value));
            rows.appendChild(r);
        };
        row('biome', info.biome ? String(info.biome).replace(/_/g, ' ') : '—');
        row('road', info.road ? String(info.road).replace(/_/g, ' ') : '—');
        row('floor', GM().floorLabel(info.floor));
        // Structure is not a place, and saying so is the point: the author just
        // painted a wall and it will not appear in the graph (task-562).
        row('structure', info.kind
            ? `not a place — ${STRUCTURE_NOTES[info.kind] || info.kind}`
            : '—');
        // A building is entered with `in`; a shut one is the author's cue that it
        // still owes an interior (task-563).
        row('enter', info.enter || '—');
        row('area', info.area ? `${info.area.name} (${info.area.id})` : '—');
        row('sub-zone', info.child ? `${info.child.name || info.child.id} (${info.child.id})` : '—');
        wrap.appendChild(rows);

        // The cell's name (task-560) — what the place is *called*, which is what
        // it compiles to. First, because a painted town is a list of names, and
        // "Building 3,4" is not an address.
        const nameRow = _el('div', 'display:flex;gap:6px;align-items:center;margin-top:6px;');
        nameRow.appendChild(_el('span', 'color:var(--text-muted,#999);min-width:78px;', 'name'));
        const nameInput = _el('input', 'flex:1;min-width:0;padding:2px 6px;border-radius:5px;' +
            'border:1px solid var(--border,#444);background:var(--bg-card,#2a2a32);color:var(--text,#ddd);');
        nameInput.value = info.name || '';
        nameInput.placeholder = 'unnamed — compiles to a coordinate';
        nameInput.title = 'The name this place compiles to. Needed for a town: a building is not addressable until it has one.';
        nameInput.addEventListener('change', () => {
            setCellName(p, info.x, info.y, nameInput.value);
        });
        nameInput.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') nameInput.blur(); });
        nameRow.appendChild(nameInput);
        wrap.appendChild(nameRow);

        const actions = _el('div', 'display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;');
        if (info.area) {
            actions.appendChild(_btn(`📍 Move ${info.area.name}`, () => {
                state.tool = 'area';
                state.selectedArea = info.area.id;
                render();
            }, '', 'Switch to the Area tool with this area picked, then click its new cell'));
            actions.appendChild(_btn('🗑 Unplace', () => unplaceArea(info.area.id),
                '', 'Take this area off the map; the area itself is untouched'));
            if (window.VW && window.VW.inspector) {
                actions.appendChild(_btn('🔎 Open area', () => {
                    state.overlay.remove();
                    window.VW.inspector.showNode(info.area.id);
                }, '', 'Open this area in the graph inspector'));
            }
        }
        if (info.child) {
            actions.appendChild(_btn(`📂 Open ${info.child.name || info.child.id}`, () => {
                load(info.child.id);
            }, '', 'Drill into this sub-zone'));
            actions.appendChild(_btn('🗑 Remove sub-zone', () => removeFeature(info.child.id),
                '', 'Take the child scope off this cell (the scope itself is kept)'));
        }
        if (info.painted) {
            actions.appendChild(_btn('🧽 Clear paint', () => clearCell(p, info.x, info.y),
                '', 'Erase every paint layer on this one cell (one undo step)'));
        }
        if (!actions.childNodes.length) {
            actions.appendChild(_el('span', 'color:var(--text-muted,#999);',
                'Nothing to do here — paint it, or place an area/feature on it.'));
        }
        wrap.appendChild(actions);
        // The ways Generate minted out of the area placed on this cell, and what
        // the author has already done about them (task-528). Listed here because
        // the seam is the author\'s decision, and the cell it belongs to is the
        // one place the painter can show it next to the thing it joins.
        const seams = _seamPanel(p, info.area && info.area.id);
        if (seams) wrap.appendChild(seams);
        // …and the one action that changes what an area *is* rather than where it
        // sits: promote it into a child scope, with the gateway to it (task-535).
        if (info.area) {
            wrap.appendChild(_btn('🪜 Make this a scope…',
                () => promoteArea(info.area.id), 'margin-top:8px;width:100%;',
                'Turn this area into a child scope of '
                + `${p.scope.name}, with a way in from its cell`));
        }
        return wrap;
    }

    /**
     * The boundary ways of one placed area, each with a way to take it away or
     * hand it back.
     *
     * Removing a seam here deletes the generated way *and* records the decision,
     * so it does not come back on the next Generate — the record is the whole
     * reason the two live in one request. A seam already handed over (a hand
     * written way of the author\'s own) is listed as such, with only "Restore".
     */
    function _seamPanel(p, areaId) {
        if (!areaId) return null;
        const rows = (p.boundary_ways || []).filter((w) => w.area_id === areaId);
        const taken = (p.boundary_overrides || []).filter((o) => {
            const row = rows.find((w) => w.way_id === o.way_id);
            return row === undefined;
        });
        if (!rows.length && !taken.length) return null;

        const box = _el('div', 'margin-top:8px;padding-top:8px;border-top:1px solid ' +
            'var(--border,#3a3a44);display:flex;flex-direction:column;gap:3px;');
        box.setAttribute('data-role', 'wp-seams');
        box.appendChild(_el('div', 'color:var(--text-muted,#999);font-size:11px;',
            'Ways out of this area — Generate made these, you decide'));

        const line = (label, title, action) => {
            const r = _el('div', 'display:flex;gap:6px;align-items:center;');
            const text = _el('span', 'flex:1;min-width:0;', label);
            text.title = title || label;
            r.appendChild(text);
            if (action) r.appendChild(action);
            box.appendChild(r);
        };

        rows.forEach((w) => {
            const seamId = w.way_id;
            const where = w.to_name || w.to_id || 'somewhere';
            const label = w.direction ? `${w.direction} → ${where}` : `to ${where}`;
            if (w.overridden) {
                line(label, 'You have taken this seam over; Generate leaves it alone', null);
                return;
            }
            line(label, 'Remove this way. Generate will not put it back.',
                _btn('✕', () => setSeam(p, seamId, 'suppress'), 'padding:1px 7px;',
                    'Delete this way and keep Generate from re-adding it'));
        });

        // A seam the author removed (or replaced) has no node left to list, so it
        // is read back from the record — otherwise restoring it would need a
        // remembered way id, which is exactly what an author should not have to do.
        taken.forEach((o) => {
            const restore = _btn('↺', () => setSeam(p, o.way_id, 'auto'),
                'padding:1px 7px;', 'Hand this seam back to Generate');
            const what = o.action === 'hand' && o.hand_way_id
                ? `your own way (${o.hand_way_id})` : 'removed by you';
            line(`to ${what}`, 'Generate left this one alone; restore it', restore);
        });
        return box;
    }

    /** Take one boundary seam over, or hand it back to the compiler (task-528). */
    async function setSeam(p, wayId, action) {
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/boundary_override`,
                { way_id: wayId, action });
            _status(action === 'auto'
                ? 'Generate will mint that way again.'
                : 'Way removed — Generate will not put it back.');
            _notify(true);
            render();
        } catch (e) {
            _status(`Could not change that way: ${e.message || e}`, true);
        }
    }

    /** Erase all three paint layers on one cell, in a single request/undo step. */
    async function clearCell(p, x, y) {
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/paint_batch`, {
                edits: GM().PAINT_LAYERS.map((layer) => ({ layer, x, y, value: null })),
            });
            _status(`Cleared the paint on (${x},${y}).`);
            _notify(true);
            render();
        } catch (e) {
            _status(`Clear failed: ${e.message || e}`, true);
        }
    }

    /**
     * Set (or clear) one cell's author name (task-560).
     *
     * Its own route rather than a paint layer, because a name is not paint: there
     * is no name vocabulary, the eraser should not wipe it, and "clear this cell"
     * must not silently unname a place. An empty box clears it, and the server drops
     * the entry entirely so an unnamed scope loads byte-identically.
     */
    async function setCellName(p, x, y, name) {
        const wanted = String(name || '').trim();
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/name`,
                { x, y, name: wanted });
            _status(wanted
                ? `Named (${x},${y}) “${wanted}”.`
                : `Cleared the name on (${x},${y}).`);
            _notify(true);
            render();
        } catch (e) {
            _status(`Name failed: ${e.message || e}`, true);
        }
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
        if (state.tool === 'inspect') {
            inspectCell(p, x, y);
            return;
        }
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
        if (state.tool === 'area') {
            await onAreaCellClick(p, x, y);
            return;
        }
        if (!p.scope.has_grid) return;
        return _paintAt(p, x, y);
    }

    /**
     * Place tool (task-528). One click places the picked area; a click on a cell
     * that already holds one offers to take it off the map, so removing needs no
     * second mode to learn.
     */
    async function onAreaCellClick(p, x, y) {
        if (!p.scope.has_grid) { _status('This scope has no grid to place on.', true); return; }
        const here = GM().areaAt(p, x, y);
        if (here) {
            if (!window.confirm(`Take "${here.name}" off this map? The area itself stays.`)) return;
            await unplaceArea(here.id);
            return;
        }
        if (!state.selectedArea) {
            _status('Pick an area from the Area dropdown first.');
            return;
        }
        await placeArea(state.selectedArea, x, y);
    }

    async function placeArea(areaId, x, y, onOverlap) {
        const p = state.payload;
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/place_area`,
                { area_id: areaId, x, y, on_overlap: onOverlap || 'forbid' });
            _status(`Placed on cell (${x},${y}).`);
            _notify(true);
            render();
        } catch (e) {
            // The server names the occupant, so a clash is actionable as-is.
            const msg = String(e.message || e);
            if (/already holds/.test(msg) && window.confirm(`${msg}\n\nDisplace it?`)) {
                await placeArea(areaId, x, y, 'displace');
                return;
            }
            _status(`Place failed: ${msg}`, true);
        }
    }

    async function unplaceArea(areaId) {
        const p = state.payload;
        try {
            state.payload = await _post(`/${encodeURIComponent(p.scope.id)}/grid/unplace_area`,
                { area_id: areaId });
            if (state.selectedArea === areaId) state.selectedArea = null;
            _status('Taken off the map (the area itself is untouched).');
            _notify(true);
            render();
        } catch (e) {
            _status(`Unplace failed: ${e.message || e}`, true);
        }
    }

    /**
     * Make the selected area into a child scope of this one, placed on the cell
     * it is standing on (task-535).
     *
     * The cell it is on is the natural home for the scope: it is where the author
     * put the area, so the new scope's gateway opens from exactly the doorstep
     * they chose. If that cell already holds a hand-placed area, that area becomes
     * the doorstep (the server's `gateway` overlap) — which is the goblin camp
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
        const p = state.payload;
        const options = (state.vocab && state.vocab.b ? state.vocab.b
            : (state.vocab.biomes || []))
            .filter((r) => (r.tags || []).indexOf('building') >= 0)
            .map((r) => r.id);
        if (!options.length) {
            _status('No building types in the vocabulary.', true);
            return;
        }
        const pick = window.prompt(
            `Paint which building's interior into "${p.scope.name}"?\n\n`
            + options.join(', '),
            options.indexOf('inn') >= 0 ? 'inn' : options[0]);
        if (!pick || !options.indexOf(pick)) {
            if (pick) _status(`${pick} is not a building type.`, true);
            return;
        }
        try {
            const res = await _post(
                `/${encodeURIComponent(p.scope.id)}/grid/interior`, { building: pick });
            state.payload = res;
            const notes = (res.report && res.report.notes) || [];
            _status(`Painted the ${pick} plan — edit the cells, then ⚙ Generate.`);
            for (let i = 0; i < Math.min(notes.length, 2); i += 1) {
                _status(notes[i]);
            }
            _notify(true);
            render();
        } catch (e) {
            _status(`Could not paint that interior: ${e.message || e}`, true);
        }
    }

    async function promoteArea(areaId) {
        const p = state.payload;
        const area = (p.areas || []).find((a) => a.id === areaId);
        if (!area) return;
        const defaultName = `${area.name} interior`;
        const name = (window.prompt(
            'Name for the new child scope:', defaultName) || '').trim();
        if (!name) return;
        const cell = area.cell || {};
        const hasCell = Number.isInteger(cell.x) && Number.isInteger(cell.y);
        const body = {
            scope_id: (window.prompt(
                'Id for the new scope (lower-case, no spaces):',
                _slug(name)) || '').trim() || _slug(name),
            name,
            area_ids: [areaId],
            parent_id: p.scope.id,
            entry_area_id: areaId,
            mode: 'interior',
        };
        if (hasCell) body.cell = { x: cell.x, y: cell.y };
        try {
            const res = await _post('/promote', body);
            state.selectedArea = null;
            // The parent grid is what moved (a placement appeared, an area left),
            // so the whole payload is re-read rather than patched by hand.
            await _reloadPayload();
            _status(`"${res.name}" is now a scope of its own, entered from `
                + `${hasCell ? `cell (${cell.x},${cell.y})` : 'nowhere yet'}.`);
            _notify(true);
        } catch (e) {
            _status(`Promote failed: ${e.message || e}`, true);
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
