"use strict";
/**
 * GraphToolbar — the control bar of the graph workspace (task-530).
 *
 * The bar used to be ~36 peer controls whose state lived in their own labels: the
 * Map button renamed itself to "Graph" when switched off, the Overlays trigger
 * replaced itself with the active overlay name (and could never say "none"
 * again), Levels had no on/off at all, and KEEP / Paste Response were always
 * enabled although they do nothing without a search / Manual Response Mode.
 *
 * This module owns the bar's *state display* so there is exactly one writer:
 *   - `setLayout` / `setOverlay` — the segmented layout control and the View
 *     popover, which are the only places a layout or overlay is chosen.
 *   - `syncAll()` — re-reads graphManager/config/GraphFocus and repaints every
 *     control: `aria-selected` on the layout tabs, `aria-pressed` on the toggles,
 *     `disabled` + a `title` explaining *why* on the controls that cannot run.
 *   - the pure `*Disabled()` / `physicsAvailability()` helpers, which decide what
 *     is available from a plain state object so the rules are unit-testable
 *     (tools/unit/test_graph_toolbar.js) instead of being scattered over five
 *     files that each rewrote a button's textContent.
 *
 * Popovers (Build / View / Tune / More) share one open-close path: a `menu-open`
 * class (so the existing `closeTopMenus()` helper keeps working from item
 * handlers), `aria-expanded` on the trigger, and close-on-outside-click / Escape.
 *
 * The Tune popover (⚙ Tune) is the ⚙ Settings → Graph tab rendered at the
 * canvas, so physics/separation/edge parameters can be dragged while the graph
 * reacts. Its controls are built from `TUNING_GROUPS`, and `applyTuning()` is
 * the one writer of the apply behavior (`config.save()` +
 * `GraphNetwork.applyGraphSettings()`) — the Settings modal keeps its own
 * static markup over the same config keys, and both surfaces re-read config
 * when opened, so config stays the single source of truth for values.
 *
 * @module graph/toolbar — graph workspace control bar: state, disabled rules, popovers
 * @contributes GraphToolbar: layout/overlay selection, toolbar state sync, popover plumbing
 * @contributes GraphToolbar.TUNING_GROUPS: the Tune popover's field spec
 * @powers the graph editor toolbar — layout tabs, View popover, Tune popover, honest disabled states
 * @relates driven by graph-manager and graph/network-manager; uses GraphFocus search state
 * @docs docs/virtualWorld/UI & Settings/Rendering & UI Modules.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
window.GraphToolbar = {
    // ──────────────────────────────────────────────
    //  Pure rules (unit-tested — no DOM, no globals)
    // ──────────────────────────────────────────────
    /** The three layouts the segmented control offers, in display order. */
    LAYOUTS: ['graph', 'map', 'levels'],
    /** Overlays offered in View ▾; `none` is the explicit "no overlay" entry. */
    OVERLAYS: ['none', 'light', 'heat', 'sound', 'trigger', 'cardinal'],
    /**
     * Can physics simulation run right now, and if not, why not?
     *
     * Two things own node positions and override the user's preference: a layout
     * that places every node itself (Levels) and an overlay that recolours the
     * canvas while it is on. A **painted grid does not** — the lattice is only
     * Map mode's starting arrangement, and the load path hands it back to the
     * solver, so physics stays available there (the user asked for this; nodes
     * will drift off the painted cells, and the map art with them). What still
     * wins is an explicit 🔒 Lock on the node layout, which is the user's own
     * "these positions are intentional".
     *
     * @param {{layout: string, overlay: string, paintedGrid: boolean, mapLocked: boolean, physicsEnabled: boolean}} state
     * @returns {{enabled: boolean, reason: string}} reason is '' when enabled
     */
    physicsAvailability(state) {
        const s = state || {};
        if (s.layout === 'levels') {
            return { enabled: false, reason: 'Levels owns node positions — physics is off until you pick Graph or Map.' };
        }
        if (s.overlay && s.overlay !== 'none') {
            return { enabled: false, reason: 'An overlay recolors the canvas and holds positions while it is on.' };
        }
        if (s.mapLocked) {
            return { enabled: false, reason: 'The node layout is locked — unlock it (🔒 in the background menu) to simulate.' };
        }
        return { enabled: true, reason: '' };
    },
    /**
     * Why the Map tab cannot be picked in this state, or null when it can.
     * Levels places every node itself, so Map would silently do nothing (bug-48).
     * @param {{layout: string}} state
     * @returns {string|null}
     */
    mapTabDisabled(state) {
        const s = state || {};
        if (s.layout === 'levels') {
            return 'Map is unavailable while Levels owns the layout \u2014 pick Graph first, then Map.';
        }
        return null;
    },
    /**
     * Why "Keep layout" is unavailable, or null. It only has meaning while a
     * search is on screen, so an empty query is a silent no-op today (focus.js).
     * @param {{searchQuery: string}} state
     * @returns {string|null}
     */
    keepInPlaceDisabled(state) {
        const s = state || {};
        const q = s.searchQuery || '';
        return q.trim() ? null : 'Type a search query first \u2014 Keep layout only matters while matches are on screen.';
    },
    /**
     * Paste Response is unavailable, or null. Submitting without Manual
     * Response Mode is rejected, so the button used to open a modal that could
     * only fail (main.js).
     * @param {{manualMode: boolean}} state
     * @returns {string|null}
     */
    pasteDisabled(state) {
        const s = state || {};
        return s.manualMode ? null : 'Enable ✋ Manual Response Mode in Settings first.';
    },
    /**
     * Ancestor trail for a scope, root first, from the flat scope summary list.
     *
     * Pure, and deliberately so: the only endpoint that returns a breadcrumb is
     * the WorldPainter's per-scope grid payload, and the graph workspace already
     * has the whole list in memory (graphManager._scopeSummaries). Every entry
     * carries `parent_id`, so the trail is a walk up that chain, cycle-guarded.
     *
     * @param {Array<{id: string, name: string, parent_id: string|null}>} scopes
     * @param {string} scopeId
     * @returns {Array<{id: string, name: string}>} root first, scope last ([] if unknown)
     */
    breadcrumbTrail(scopes, scopeId) {
        if (!scopeId)
            return [];
        const byId = new Map();
        for (const scope of scopes || []) {
            if (scope && scope.id)
                byId.set(scope.id, scope);
        }
        const trail = [];
        const seen = new Set();
        let current = byId.get(scopeId) || null;
        while (current && !seen.has(current.id)) {
            seen.add(current.id);
            trail.push({ id: current.id, name: current.name || current.id });
            current = current.parent_id ? (byId.get(current.parent_id) || null) : null;
        }
        trail.reverse();
        return trail;
    },
    // ──────────────────────────────────────────────
    //  State read (single source of truth for the DOM)
    // ──────────────────────────────────────────────
    /** Plain snapshot of everything the toolbar's rules depend on. */
    state() {
        const gm = window.graphManager;
        // `config` carries an index signature, so `manualMode` arrives as `unknown`.
        const cfg = ((typeof config !== 'undefined' && config) || {});
        const layout = gm ? gm.activeLayout() : 'graph';
        const overlay = gm && gm._viewMode && gm._viewMode !== 'graph' ? gm._viewMode : 'none';
        let searchQuery = '';
        let manualMode = false;
        try {
            searchQuery = (gm && gm._searchQuery) || '';
        }
        catch (e) { /* ignore */ }
        try {
            manualMode = !!cfg.manualMode;
        }
        catch (e) { /* ignore */ }
        return {
            layout,
            overlay,
            // The painted lattice only applies in the Map layout, so a stale
            // flag from a previous load must not disable physics elsewhere.
            paintedGrid: !!(gm && gm._paintedGridLayout) && layout === 'map',
            mapLocked: !!(gm && gm._mapLayoutLocked) && layout === 'map',
            physicsEnabled: !!(gm && gm._physicsEnabled),
            searchQuery,
            manualMode,
            legendVisible: !!(gm && gm._legendVisible),
            scope: (gm && gm._scopeFilter) || '',
        };
    },
    // ──────────────────────────────────────────────
    //  Actions
    // ──────────────────────────────────────────────
    /**
     * Pick a layout from the segmented control. Clicking the already-selected tab
     * is a no-op (Graph is the off state for Map) — a tab is not a toggle, which
     * is what made the old self-renaming button impossible to reason about.
     * @param {'graph'|'map'|'levels'} layout
     */
    setLayout(layout) {
        const gm = window.graphManager;
        if (!gm)
            return;
        const s = GraphToolbar.state();
        if (layout === s.layout) {
            GraphToolbar.closeAll();
            GraphToolbar.syncAll();
            return;
        }
        const blocked = GraphToolbar.mapTabDisabled({ layout: s.layout });
        if (layout === 'map' && blocked) {
            if (typeof toastError === 'function')
                toastError(blocked);
            GraphToolbar.syncAll();
            return;
        }
        if (layout === 'levels') {
            gm.toggleLayoutMode(); // flips config.graphLayoutMode
        }
        else if (layout === 'map') {
            gm.toggleCardinalLayout(); // flips _cardinalLayout
        }
        else {
            // Leaving Levels for Graph: free physics again.
            if (s.layout === 'levels')
                gm.toggleLayoutMode();
            if (s.layout === 'map')
                gm.toggleCardinalLayout();
            gm.setViewMode('graph');
        }
        GraphToolbar.closeAll();
        GraphToolbar.syncAll();
    },
    /**
     * Pick an overlay from View ▾. `none` returns to the structural graph view.
     * Cardinal is a *label* overlay (way directions) only — it no longer turns
     * the Map layout on; the Map tab is the single layout control.
     * @param {string} overlay - one of GraphToolbar.OVERLAYS
     */
    setOverlay(overlay) {
        const gm = window.graphManager;
        if (!gm)
            return;
        const mode = !overlay || overlay === 'none' ? 'graph' : overlay;
        gm.setViewMode(mode);
        GraphToolbar.closeAll();
        GraphToolbar.syncAll();
    },
    // ──────────────────────────────────────────────
    //  Popovers
    // ──────────────────────────────────────────────
    /**
     * Open/close a toolbar popover by id. Shares the `menu-open` class with the
     * global `closeTopMenus()` helper, so item handlers that call it still work.
     * @param {Event} [ev]
     * @param {string} id - the menu element id
     */
    togglePopover(ev, id) {
        if (ev)
            ev.stopPropagation();
        const menu = document.getElementById(id);
        if (!menu)
            return;
        const wasOpen = menu.classList.contains('menu-open');
        GraphToolbar.closeAll();
        if (wasOpen)
            return;
        menu.style.display = 'block';
        menu.classList.add('menu-open');
        GraphToolbar._bindGlobalClose();
        GraphToolbar.syncAria();
        // Reflect freshly-picked state in the chips of the popover just opened.
        GraphToolbar.syncOverlayChips();
        GraphToolbar.syncDisabled();
    },
    /** Close every open toolbar popover. */
    closeAll() {
        const open = document.querySelectorAll('.dropdown-menu.menu-open');
        open.forEach(m => { m.style.display = 'none'; m.classList.remove('menu-open'); });
        if (open.length) {
            document.removeEventListener('click', GraphToolbar._outsideClick, true);
            document.removeEventListener('keydown', GraphToolbar._outsideKey, true);
        }
        GraphToolbar.syncAria();
    },
    _bindGlobalClose() {
        document.removeEventListener('click', GraphToolbar._outsideClick, true);
        document.removeEventListener('keydown', GraphToolbar._outsideKey, true);
        document.addEventListener('click', GraphToolbar._outsideClick, true);
        document.addEventListener('keydown', GraphToolbar._outsideKey, true);
    },
    // Capture phase: a click on an item calls closeTopMenus() from its bubble
    // handler, so listening later would miss the same click.
    _outsideClick(e) {
        const open = Array.from(document.querySelectorAll('.dropdown-menu.menu-open'));
        const target = e.target;
        for (const menu of open) {
            const trigger = menu.parentElement ? menu.parentElement.querySelector('button') : null;
            if (menu.contains(target))
                continue;
            if (trigger && trigger.contains(target))
                continue;
            menu.style.display = 'none';
            menu.classList.remove('menu-open');
        }
        // Self-heal: closeTopMenus() may have hidden the last menu behind our back.
        if (!document.querySelector('.dropdown-menu.menu-open')) {
            document.removeEventListener('click', GraphToolbar._outsideClick, true);
            document.removeEventListener('keydown', GraphToolbar._outsideKey, true);
        }
        GraphToolbar.syncAria();
    },
    _outsideKey(e) {
        if (e.key !== 'Escape')
            return;
        if (!document.querySelector('.dropdown-menu.menu-open'))
            return;
        GraphToolbar.closeAll();
    },
    // ──────────────────────────────────────────────
    //  ⚙ Tune popover — the Settings → Graph tab at the canvas
    // ──────────────────────────────────────────────
    /** Whether the Tune popover's controls have been built into the DOM. */
    _tuningBuilt: false,
    /**
     * The Tune popover's field spec, grouped the way you think while tuning,
     * not the way the engine names its forces:
     *   1. Length of connections — how long an edge holds its two nodes.
     *   2. Pushing apart — unconnected nodes: the solver's spread force, then
     *      the overlap guard (separation pass) with its own strength and range.
     *   3. Look — node size, edge width, arrows.
     *   4. Engine — settling speed and the solver itself.
     *   5. Camera — focus zoom.
     * The ⚙ Settings → Graph tab keeps its own static markup over the same
     * config keys; test_graph_toolbar.js asserts the two stay in parity.
     */
    TUNING_GROUPS: [
        {
            heading: 'Length of connections',
            fields: [
                // NOTE: there is deliberately no global "edge length" slider here.
                // Connections are stamped per edge in the dataset — room↔room ways
                // size themselves to their labels (or a per-way edge_length),
                // attachments use Contents length — so the solver's global spring
                // length (config.graphSpringLength) only reaches rare edges with
                // no length of their own. Measured: dragging it across its whole
                // range moved average attachment distances ~4% (equilibrium
                // noise). It stays a config/engine fallback, not a control.
                { key: 'graphItemEdgeLength', id: 'gt-item-edge-length', label: 'Contents length', type: 'range', min: 20, max: 200, step: 5, lo: 'Hug Parent', hi: 'Stretched', fallback: 60, hint: 'Rest length for the edges that hold things (in/on/carrying/equipped) — lower = contents hug what holds them. Room↔room ways size themselves to their labels instead.' },
                { key: 'graphSpringConstant', id: 'gt-spring-constant', label: 'Snappiness', type: 'range', min: 0.01, max: 0.15, step: 0.01, dp: 2, lo: 'Soft', hi: 'Rigid', fallback: 0.1, hint: 'How strongly an edge pulls its two nodes to that length — higher = rigid spacing, lower = soft and stretchy.' },
            ],
        },
        {
            heading: 'Pushing apart',
            fields: [
                { key: 'graphGravitationalConstant', id: 'gt-repulsion', label: 'Spread', type: 'range', min: -500, max: -5, step: 5, lo: 'Weak', hi: 'Strong', fallback: -8, hint: 'How hard every node pushes every other away. Connected pairs are held at their edge length; unconnected ones spread out under this.' },
                { key: 'graphRepelEnabled', id: 'gt-repel-enabled', label: '🧲 Overlap guard', type: 'check', fallback: true, hint: 'Push overlapping nodes apart even when no edge joins them — a second pass on top of the spread force.' },
                { key: 'graphRepelStrength', id: 'gt-repel-strength', label: 'Guard strength', type: 'range', min: 0.05, max: 1, step: 0.05, dp: 2, lo: 'Soft', hi: 'Firm', fallback: 0.6, hint: 'How hard the overlap guard pushes a pair apart.' },
                { key: 'graphRepelMin', id: 'gt-repel-min', label: 'Push apart when closer than', type: 'range', min: 20, max: 180, step: 5, lo: 'Overlap', hi: 'Spaced', fallback: 55, hint: 'The guard only acts on pairs closer than this. A floor — long names need room, so it grows with the label.' },
                { key: 'graphRepelMax', id: 'gt-repel-max', label: 'Stop pushing beyond', type: 'range', min: 60, max: 600, step: 10, lo: 'Near', hi: 'Far', fallback: 220, hint: 'Pairs further apart than this are ignored — keeps the pass cheap on a big graph.' },
                { key: 'graphRepelPull', id: 'gt-repel-pull', label: 'Pull strays back', type: 'range', min: 0, max: 0.4, step: 0.01, dp: 2, lo: 'Loose', hi: 'Hugging', fallback: 0.12, hint: 'How strongly a node the guard pushed away is reeled back toward what holds it. Edge-joined pairs are never pushed in the first place.' },
            ],
        },
        {
            heading: 'Look',
            fields: [
                { key: 'graphNodeScale', id: 'gt-node-scale', label: 'Node size', type: 'range', min: 0.5, max: 2, step: 0.05, dp: 2, lo: 'Small', hi: 'Large', fallback: 1, hint: 'Drawn size of item, way and character nodes. Areas are cards that size to their name. The overlap guard grants bigger nodes more room.' },
                { key: 'graphEdgeWidth', id: 'gt-edge-width', label: 'Edge width', type: 'range', min: 0.5, max: 5, step: 0.5, dp: 1, lo: 'Thin', hi: 'Thick', fallback: 1 },
                { key: 'graphArrows', id: 'gt-arrows', label: '➡️ Edge arrows', type: 'check', fallback: true, hint: 'Show direction arrows on connection edges.' },
            ],
        },
        {
            heading: 'Engine (advanced)',
            fields: [
                { key: 'graphDamping', id: 'gt-damping', label: 'Settle speed', type: 'range', min: 0, max: 1, step: 0.05, dp: 2, lo: 'Swings', hi: 'Calms fast', fallback: 0.4, hint: 'How fast movement dies down — higher calms the layout sooner, lower keeps it swinging.' },
                { key: 'graphSolver', id: 'gt-solver', label: 'Physics solver', type: 'select', options: [['forceAtlas2Based', 'Force Atlas 2'], ['barnesHut', 'Barnes-Hut'], ['repulsion', 'Repulsion']], fallback: 'forceAtlas2Based', hint: 'Force Atlas 2: smooth organic layouts · Barnes-Hut: faster for large graphs.' },
                { key: 'graphImprovedLayout', id: 'gt-improved-layout', label: '🧩 Improved layout', type: 'check', fallback: false, hint: 'Better initial node placement (may shift positions).' },
            ],
        },
        {
            heading: 'Camera',
            fields: [
                { key: 'graphFocusZoom', id: 'gt-focus-zoom', label: 'Focus zoom', type: 'range', min: 0.5, max: 3, step: 0.05, dp: 2, lo: 'Far', hi: 'Close', fallback: 1.15, hint: 'How close the camera zooms when a node is focused from a list, the outline or a search hit (1 = 100%). Read at click time — no reapply needed.' },
            ],
        },
    ],
    /** Open/close the Tune popover, building and syncing its controls first. */
    toggleTuning(ev) {
        GraphToolbar.buildTuningMenu();
        GraphToolbar.syncTuning();
        GraphToolbar.togglePopover(ev, 'graph-tuning-menu');
        GraphToolbar.placeTuningMenu();
    },
    /**
     * Keep the Tune menu inside the center viewport. It is 640px wide but its
     * positioning ancestor chain (`#center-viewport`) clips `overflow: hidden`,
     * so a plain right-aligned menu loses its left column under the left panel
     * whenever the trigger sits near that panel. Right-align to the trigger,
     * then clamp into the clipping ancestor's box, shrinking first if the
     * viewport itself is too narrow. Runs on every open, so a moved or wrapped
     * trigger re-places it.
     */
    placeTuningMenu() {
        const menu = document.getElementById('graph-tuning-menu');
        if (!menu || !menu.classList.contains('menu-open'))
            return;
        const viewport = menu.closest('#center-viewport');
        const anchor = menu.parentElement;
        if (!viewport || !anchor)
            return;
        const vpRect = viewport.getBoundingClientRect();
        if (!vpRect.width)
            return;
        const anchorRect = anchor.getBoundingClientRect();
        const margin = 8;
        const width = Math.min(640, vpRect.width - margin * 2);
        const minLeft = vpRect.left + margin;
        let left = anchorRect.right - width;
        if (left < minLeft)
            left = Math.min(minLeft, vpRect.right - width - margin);
        menu.style.right = 'auto';
        menu.style.width = `${Math.round(width)}px`;
        // The menu is absolutely positioned within the trigger's anchor, so
        // `left` is measured from the anchor's left edge.
        menu.style.left = `${Math.round(left - anchorRect.left)}px`;
    },
    /** Fill `#graph-tuning-menu` from `TUNING_GROUPS`, once. */
    buildTuningMenu() {
        if (GraphToolbar._tuningBuilt)
            return;
        const menu = document.getElementById('graph-tuning-menu');
        if (!menu)
            return;
        for (const group of GraphToolbar.TUNING_GROUPS) {
            const heading = document.createElement('div');
            heading.className = 'menu-heading';
            heading.textContent = group.heading;
            menu.appendChild(heading);
            const grid = document.createElement('div');
            grid.className = 'tuning-grid';
            for (const field of group.fields)
                grid.appendChild(GraphToolbar._tuningField(field));
            menu.appendChild(grid);
        }
        GraphToolbar._tuningBuilt = true;
    },
    /** One control's DOM. Ranges/selects reuse the Settings modal's own classes. */
    _tuningField(f) {
        if (f.type === 'check') {
            const label = document.createElement('label');
            label.className = 'tuning-check';
            label.title = f.hint || '';
            const box = document.createElement('input');
            box.type = 'checkbox';
            box.id = f.id;
            box.checked = GraphToolbar.tuningValue(f) === true;
            box.addEventListener('change', () => GraphToolbar.applyTuning(f.key, box.checked));
            const text = document.createElement('span');
            text.textContent = f.label;
            label.appendChild(box);
            label.appendChild(text);
            return label;
        }
        const wrap = document.createElement('div');
        wrap.className = 'settings-field';
        const row = document.createElement('label');
        row.setAttribute('for', f.id);
        const name = document.createElement('span');
        name.textContent = f.label;
        row.appendChild(name);
        wrap.appendChild(row);
        const value = GraphToolbar.tuningValue(f);
        if (f.type === 'range') {
            const chip = document.createElement('span');
            chip.className = 'range-value';
            chip.id = f.id + '-val';
            chip.textContent = GraphToolbar.tuningDisplay(f, Number(value));
            row.appendChild(chip);
            const rangeRow = document.createElement('div');
            rangeRow.className = 'range-row';
            const input = document.createElement('input');
            input.type = 'range';
            input.id = f.id;
            input.min = String(f.min);
            input.max = String(f.max);
            input.step = String(f.step);
            input.value = String(value);
            input.addEventListener('input', () => {
                const n = parseFloat(input.value);
                chip.textContent = GraphToolbar.tuningDisplay(f, n);
                GraphToolbar.applyTuning(f.key, n);
            });
            const lo = document.createElement('span');
            lo.className = 'tuning-end';
            lo.textContent = f.lo || '';
            const hi = document.createElement('span');
            hi.className = 'tuning-end';
            hi.textContent = f.hi || '';
            rangeRow.appendChild(lo);
            rangeRow.appendChild(input);
            rangeRow.appendChild(hi);
            wrap.appendChild(rangeRow);
        }
        else {
            const sel = document.createElement('select');
            sel.id = f.id;
            for (const opt of f.options || []) {
                const o = document.createElement('option');
                o.value = opt[0];
                o.textContent = opt[1];
                if (String(value) === opt[0])
                    o.selected = true;
                sel.appendChild(o);
            }
            sel.addEventListener('change', () => GraphToolbar.applyTuning(f.key, sel.value));
            wrap.appendChild(sel);
        }
        if (f.hint) {
            const hint = document.createElement('div');
            hint.className = 'field-hint';
            hint.textContent = f.hint;
            wrap.appendChild(hint);
        }
        return wrap;
    },
    /**
     * The one writer of the apply behavior for Tune controls: write config,
     * persist, reapply to the live network. `applyGraphSettings()` ends with
     * `syncAll()` → `syncTuning()`, which repaints every chip from config; the
     * chip of the control being dragged is updated by its own listener first.
     */
    applyTuning(key, value) {
        const cfg = ((typeof config !== 'undefined' && config) || null);
        if (!cfg)
            return;
        cfg[key] = value;
        cfg.save();
        GraphNetwork.applyGraphSettings();
    },
    /** Read a field's value off config, falling back to the config.ts default. */
    tuningValue(f) {
        const cfg = ((typeof config !== 'undefined' && config) || {});
        const v = cfg[f.key];
        if (v === undefined || v === null || v === '')
            return f.fallback !== undefined ? f.fallback : 0;
        return v;
    },
    /** A value chip's text: `dp` decimals, otherwise an integer. */
    tuningDisplay(f, n) {
        return typeof f.dp === 'number' ? n.toFixed(f.dp) : String(Math.round(n));
    },
    /** Repaint every Tune control from config. Cheap; no-op until built. */
    syncTuning() {
        if (!GraphToolbar._tuningBuilt)
            return;
        for (const group of GraphToolbar.TUNING_GROUPS) {
            for (const f of group.fields) {
                const v = GraphToolbar.tuningValue(f);
                if (f.type === 'check') {
                    const box = document.getElementById(f.id);
                    if (box)
                        box.checked = v === true;
                    continue;
                }
                const el = document.getElementById(f.id);
                if (!el)
                    continue;
                el.value = String(v);
                const chip = document.getElementById(f.id + '-val');
                if (chip && f.type === 'range')
                    chip.textContent = GraphToolbar.tuningDisplay(f, Number(v));
            }
        }
    },
    // ──────────────────────────────────────────────
    //  DOM sync
    // ──────────────────────────────────────────────
    /** Repaint every control from the current state. Cheap; safe to call often. */
    syncAll() {
        GraphToolbar.syncLayout();
        GraphToolbar.syncOverlayChips();
        GraphToolbar.syncToggles();
        GraphToolbar.syncDisabled();
        GraphToolbar.syncScope();
        GraphToolbar.syncTuning();
    },
    /** `aria-selected` on the layout segment; the Map tab greys out under Levels. */
    syncLayout() {
        const s = GraphToolbar.state();
        document.querySelectorAll('#layout-segment [data-layout]').forEach(tab => {
            const layout = tab.dataset.layout;
            const selected = layout === s.layout;
            tab.setAttribute('aria-selected', selected ? 'true' : 'false');
            tab.classList.toggle('active', selected);
            const blocked = layout === 'map' ? GraphToolbar.mapTabDisabled(s) : null;
            tab.disabled = !!blocked;
            if (blocked)
                tab.title = blocked;
        });
    },
    /** Which overlay chip is on. `none` is highlighted for the structural view. */
    syncOverlayChips() {
        const s = GraphToolbar.state();
        document.querySelectorAll('.overlay-toggle').forEach(chip => {
            const on = chip.dataset.overlay === s.overlay;
            chip.classList.toggle('active', on);
            chip.setAttribute('aria-pressed', on ? 'true' : 'false');
        });
    },
    /** `aria-pressed` mirrors the state of every boolean toggle in the bar. */
    syncToggles() {
        const gm = window.graphManager;
        if (!gm)
            return;
        const press = (id, on) => {
            const el = document.getElementById(id);
            if (!el)
                return;
            el.classList.toggle('active', !!on);
            el.setAttribute('aria-pressed', on ? 'true' : 'false');
        };
        press('btn-inhabited', gm._showOnlyInhabitedAreas);
        press('btn-images', gm._showImages);
        press('btn-triggers', gm._showTriggers);
        press('btn-items', gm._showItems);
        press('btn-edge-labels', gm._showEdgeLabels);
        press('btn-node-labels', gm._showNodeLabels);
        press('btn-legend', gm._legendVisible);
        const phys = document.getElementById('btn-physics');
        if (phys)
            phys.setAttribute('aria-pressed', gm._physicsEnabled ? 'true' : 'false');
    },
    /**
     * Honest affordances: disable what cannot run, and say why in the tooltip.
     * The label never changes — the label is "⏸ Physics" whatever the state.
     */
    syncDisabled() {
        const s = GraphToolbar.state();
        const phys = GraphToolbar.physicsAvailability(s);
        const physBtn = document.getElementById('btn-physics');
        if (physBtn) {
            physBtn.disabled = !phys.enabled;
            physBtn.title = phys.enabled
                ? (s.physicsEnabled ? 'Pause the simulation and freeze every node where it is' : 'Resume the simulation — nodes start moving again')
                : phys.reason;
        }
        const keepLabel = document.getElementById('keep-label');
        const keepBox = document.getElementById('search-keep-in-place');
        const keepReason = GraphToolbar.keepInPlaceDisabled(s);
        if (keepBox)
            keepBox.disabled = !!keepReason;
        if (keepLabel) {
            if (keepReason) {
                keepLabel.title = keepReason;
                keepLabel.classList.add('disabled');
            }
            else {
                keepLabel.title = 'Keep matches where they are instead of gathering them into a cluster (remembered)';
                keepLabel.classList.remove('disabled');
            }
        }
        const paste = document.getElementById('menu-paste-response');
        const pasteReason = GraphToolbar.pasteDisabled(s);
        if (paste) {
            paste.disabled = !!pasteReason;
            paste.title = pasteReason || 'Paste a manual LLM response for the next agent step';
            paste.classList.toggle('disabled', !!pasteReason);
        }
    },
    /**
     * What the canvas actually holds right now. A painted world is too large to
     * take on faith, so the count comes from the loaded dataset, not a summary.
     * @returns {{area:number, way:number, item:number, character:number, other:number, total:number}}
     */
    _nodeCounts() {
        const gm = window.graphManager;
        const nodes = (gm && gm._graphNodesObj) || {};
        const counts = { area: 0, way: 0, item: 0, character: 0 };
        let other = 0;
        for (const id of Object.keys(nodes)) {
            const type = nodes[id] && nodes[id].type;
            if (Object.prototype.hasOwnProperty.call(counts, type))
                counts[type] += 1;
            else
                other += 1;
        }
        // Key order matters: `syncScope` renders `Object.entries(counts)` as the
        // scope chip's tooltip, so it reads area · way · item · character.
        return {
            area: counts.area,
            way: counts.way,
            item: counts.item,
            character: counts.character,
            other,
            total: counts.area + counts.way + counts.item + counts.character + other,
        };
    },
    _plural(n, noun) { return `${n} ${noun}${n === 1 ? '' : 's'}`; },
    /** The loaded dataset, described in one line. */
    _countsText(counts, detailed) {
        if (!counts || !counts.total)
            return '';
        if (detailed) {
            const parts = [GraphToolbar._plural(counts.area, 'area'), GraphToolbar._plural(counts.way, 'way')];
            if (counts.character)
                parts.push(GraphToolbar._plural(counts.character, 'character'));
            if (counts.item)
                parts.push(GraphToolbar._plural(counts.item, 'item'));
            return `${parts.join(' · ')} · ${counts.total} loaded`;
        }
        return `${GraphToolbar._plural(counts.area, 'area')} · ${GraphToolbar._plural(counts.way, 'way')} · ${counts.total} loaded`;
    },
    /**
     * "What is loaded" — the scope chip's name plus a live count. When a scope is
     * loaded the contextual scope bar carries the same numbers plus the zone
     * breadcrumb, so the chip's count steps aside (CSS decides which of the two
     * is rendered: a narrow window drops the bar, not the number).
     */
    syncScope() {
        const s = GraphToolbar.state();
        const chipIcon = document.querySelector('.scope-chip-icon');
        if (chipIcon)
            chipIcon.textContent = s.scope ? '🗺️' : '🌍';
        const counts = GraphToolbar._nodeCounts();
        const stat = document.getElementById('scope-stats');
        if (stat) {
            stat.textContent = GraphToolbar._countsText(counts);
            stat.title = Object.entries(counts).filter(([, n]) => n > 0)
                .map(([k, n]) => `${n} ${k}${n === 1 ? '' : 's'}`).join(' · ');
        }
        GraphToolbar.syncScopeBar(counts);
        // task-397 step 4: the scope tree is repainted from the same sync as the
        // breadcrumb, so the loaded scope is marked in both or in neither. It
        // cannot live in `loadScopeFilterOptions` alone: that only runs when the
        // *manifest* changes, while the selection changes on every scope click.
        // Read through `window` so a missing module stays a no-op.
        const scopeTree = window.GraphScopeTree;
        if (scopeTree)
            scopeTree.render();
    },
    // ──────────────────────────────────────────────
    //  Contextual scope bar (task-531)
    // ──────────────────────────────────────────────
    /**
     * The second tier of the toolbar: a thin row that exists only while a world
     * scope is loaded. It answers "where am I?" (breadcrumb) and "how much of it?"
     * (counts), and offers the two ways out — open the scope in the WorldPainter,
     * or go back to the whole world. Generation deliberately does NOT live here:
     * `⚙ Generate` / `🧹 Ungenerate` belong to the WorldPainter's own toolbar,
     * which is the only surface that can paint or compile a grid.
     *
     * @param {Object} [counts] pre-computed node counts (syncScope passes them)
     */
    syncScopeBar(counts) {
        const bar = document.getElementById('scope-bar');
        if (!bar)
            return;
        const toolbar = document.getElementById('graph-toolbar');
        const s = GraphToolbar.state();
        const gm = window.graphManager;
        const stats = counts || GraphToolbar._nodeCounts();
        if (!s.scope) {
            bar.hidden = true;
            if (toolbar)
                toolbar.classList.remove('scope-bar-open');
            return;
        }
        bar.hidden = false;
        if (toolbar)
            toolbar.classList.add('scope-bar-open');
        const barStat = document.getElementById('scope-bar-stats');
        if (barStat)
            barStat.textContent = GraphToolbar._countsText(stats, true);
        const crumbs = document.getElementById('scope-breadcrumb');
        if (!crumbs)
            return;
        let trail = GraphToolbar.breadcrumbTrail((gm && gm._scopeSummaries) || [], s.scope);
        if (!trail.length) {
            // Stale selection (a scope the manifest no longer lists): fall back to
            // whatever the picker is showing rather than an empty trail.
            const sel = document.getElementById('graph-scope-filter');
            const opt = sel && sel.selectedOptions && sel.selectedOptions[0];
            trail = [{ id: s.scope, name: ((opt && opt.textContent) || s.scope).trim() }];
        }
        crumbs.textContent = '';
        trail.forEach((node, i) => {
            if (i > 0) {
                const sep = document.createElement('span');
                sep.className = 'scope-crumb-sep';
                sep.textContent = '›';
                crumbs.appendChild(sep);
            }
            const isCurrent = i === trail.length - 1;
            const crumb = document.createElement('button');
            crumb.type = 'button';
            crumb.className = 'scope-crumb' + (isCurrent ? ' current' : '');
            crumb.textContent = node.name;
            if (isCurrent) {
                crumb.setAttribute('aria-current', 'true');
                crumb.disabled = true;
            }
            else {
                crumb.title = `Load ${node.name} instead of this scope`;
                crumb.addEventListener('click', () => GraphToolbar.loadScope(node.id));
            }
            crumbs.appendChild(crumb);
        });
    },
    /** Load a scope by id, keeping the picker's value in step. */
    loadScope(scopeId) {
        const sel = document.getElementById('graph-scope-filter');
        if (sel)
            sel.value = scopeId || '';
        const gm = window.graphManager;
        if (gm)
            gm.setScopeFilter(scopeId);
    },
    /**
     * Open the WorldPainter already pointed at the loaded scope: it takes a scope
     * id and the bar already knows it. This is the bridge between "inspect this
     * zone in the graph" and "paint this zone".
     */
    openScopeInWorldPainter() {
        const gm = window.graphManager;
        const scopeId = gm && gm._scopeFilter;
        if (!scopeId)
            return;
        const painter = window.VW && VW.worldPainter;
        if (!painter || typeof painter.open !== 'function') {
            if (typeof toastError === 'function')
                toastError('The WorldPainter is not available.');
            return;
        }
        painter.open(scopeId);
    },
    /** Unload the scope: put the whole world back on the canvas. */
    showWholeWorld() {
        GraphToolbar.loadScope('');
    },
    // ──────────────────────────────────────────────
    //  Narrow-window collapse (task-532)
    // ──────────────────────────────────────────────
    /** Below this width the bar moves its secondary controls into More ▾. */
    COLLAPSE_QUERY: '(max-width: 900px)',
    /**
     * The nodes that live in the overflow at a narrow width, in the order they
     * appear there. Build ▾, the layout segment and View ▾ stay in the bar — they
     * are the controls you reach for; these are the ones you do not.
     */
    COLLAPSE_IDS: ['btn-undo', 'btn-redo', 'undo-history-anchor', 'btn-fit', 'btn-physics', 'btn-export-png', 'btn-report-bug'],
    _collapseHomes: null,
    _overflowGroup: null,
    _collapsed: null,
    _collapseQuery: null,
    /**
     * Record where each collapsible node lives once, then follow the viewport.
     * Relocation (not hiding) keeps every handler, title and aria attribute: a
     * hidden control is unreachable, a moved one is still one click away.
     */
    _initCollapse() {
        const group = document.getElementById('toolbar-overflow');
        if (!group)
            return;
        GraphToolbar._overflowGroup = group;
        GraphToolbar._collapseHomes = [];
        for (const id of GraphToolbar.COLLAPSE_IDS) {
            const el = document.getElementById(id);
            if (!el || !el.parentElement)
                continue;
            GraphToolbar._collapseHomes.push({ el, parent: el.parentElement, next: el.nextElementSibling });
        }
        if (typeof window.matchMedia !== 'function')
            return;
        GraphToolbar._collapseQuery = window.matchMedia(GraphToolbar.COLLAPSE_QUERY);
        GraphToolbar._applyCollapse(GraphToolbar._collapseQuery.matches);
        if (typeof GraphToolbar._collapseQuery.addEventListener === 'function') {
            GraphToolbar._collapseQuery.addEventListener('change', (e) => GraphToolbar._applyCollapse(e.matches));
        }
    },
    _applyCollapse(collapsed) {
        const group = GraphToolbar._overflowGroup;
        const homes = GraphToolbar._collapseHomes;
        if (!group || !homes || collapsed === GraphToolbar._collapsed)
            return;
        GraphToolbar._collapsed = collapsed;
        if (collapsed) {
            for (const home of homes)
                group.appendChild(home.el);
        }
        else {
            for (const home of homes) {
                if (home.next && home.next.parentElement === home.parent)
                    home.parent.insertBefore(home.el, home.next);
                else
                    home.parent.appendChild(home.el);
            }
        }
        group.hidden = !collapsed;
        const doZone = document.querySelector('.toolbar-zone[aria-label="Create and history"]');
        if (doZone)
            doZone.classList.toggle('collapsed', collapsed);
        // Physics may have just moved into the overflow: its disabled rule is
        // computed on the node, so repaint either way.
        GraphToolbar.syncAll();
    },
    /** `aria-expanded` on every popover trigger, from the `menu-open` class. */
    syncAria() {
        document.querySelectorAll('.toolbar-dropdown > button').forEach(btn => {
            const menu = btn.nextElementSibling;
            const open = !!(menu && menu.classList.contains('menu-open'));
            btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        });
    },
    /** Hide the legend (its ✕ button). */
    closeLegend() {
        const gm = window.graphManager;
        if (!gm || !gm._legendEl)
            return;
        gm._legendVisible = false;
        gm._legendEl.style.display = 'none';
        GraphToolbar.syncToggles();
    },
    // ──────────────────────────────────────────────
    //  Wiring
    // ──────────────────────────────────────────────
    init() {
        // The legend is rebuilt as HTML on every overlay change, so its ✕ is
        // delegated rather than bound.
        document.addEventListener('click', (e) => {
            const target = e.target;
            if (target.closest && target.closest('[data-legend-close]')) {
                e.stopPropagation();
                GraphToolbar.closeLegend();
            }
        });
        // Keep the search box's own disabled rules honest if it is filled by code
        // (a palette jump, a "find" link) rather than by typing.
        const search = document.getElementById('graph-search');
        if (search)
            search.addEventListener('input', () => GraphToolbar.syncDisabled());
        // Relocated toolbar buttons act inside the More menu: let the action run,
        // then close it. The undo-history panel is exempt — it is absolutely
        // positioned inside the menu, so hiding the menu would hide the panel.
        const overflow = document.getElementById('toolbar-overflow');
        if (overflow) {
            overflow.addEventListener('click', (e) => {
                const target = e.target;
                if (!target.closest || !target.closest('button'))
                    return;
                if (target.closest('[data-role="undo-history-toggle"]'))
                    return;
                // `closeTopMenus` is only defined once its module has loaded, and
                // has no ambient declaration, so read it through `window`.
                const closeTopMenusFn = window.closeTopMenus;
                if (typeof closeTopMenusFn === 'function')
                    closeTopMenusFn();
            });
        }
        GraphToolbar._initCollapse();
        GraphToolbar.syncAll();
    },
};
if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => GraphToolbar.init());
    }
    else {
        GraphToolbar.init();
    }
}
