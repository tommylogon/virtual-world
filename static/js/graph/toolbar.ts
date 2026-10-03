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
 * Popovers (Build / View / More) share one open-close path: a `menu-open` class
 * (so the existing `closeTopMenus()` helper keeps working from item handlers),
 * `aria-expanded` on the trigger, and close-on-outside-click / Escape.
 *
 * @module graph/toolbar — graph workspace control bar: state, disabled rules, popovers
 * @contributes GraphToolbar: layout/overlay selection, toolbar state sync, popover plumbing
 * @powers the graph editor toolbar — layout tabs, View popover, honest disabled states
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
    physicsAvailability(state?: GraphToolbarPhysicsState): GraphToolbarPhysicsAvailability {
        const s: GraphToolbarPhysicsState = state || {};
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
    mapTabDisabled(state?: GraphToolbarLayoutState): string | null {
        const s: GraphToolbarLayoutState = state || {};
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
    keepInPlaceDisabled(state?: GraphToolbarSearchState): string | null {
        const s: GraphToolbarSearchState = state || {};
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
    pasteDisabled(state?: GraphToolbarManualState): string | null {
        const s: GraphToolbarManualState = state || {};
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
    breadcrumbTrail(
        scopes: GraphToolbarScopeSummary[] | null | undefined,
        scopeId: string | null | undefined,
    ): GraphToolbarBreadcrumb[] {
        if (!scopeId) return [];
        const byId = new Map<string, GraphToolbarScopeSummary>();
        for (const scope of scopes || []) {
            if (scope && scope.id) byId.set(scope.id, scope);
        }
        const trail: GraphToolbarBreadcrumb[] = [];
        const seen = new Set<string>();
        let current: GraphToolbarScopeSummary | null = byId.get(scopeId) || null;
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
    state(): GraphToolbarState {
        const gm = window.graphManager;
        // `config` carries an index signature, so `manualMode` arrives as `unknown`.
        const cfg = ((typeof config !== 'undefined' && config) || {}) as { manualMode?: unknown };
        const layout = gm ? gm.activeLayout() : 'graph';
        const overlay = gm && gm._viewMode && gm._viewMode !== 'graph' ? gm._viewMode : 'none';
        let searchQuery = '';
        let manualMode = false;
        try { searchQuery = (gm && gm._searchQuery) || ''; } catch (e) { /* ignore */ }
        try { manualMode = !!cfg.manualMode; } catch (e) { /* ignore */ }
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
    setLayout(layout: 'graph' | 'map' | 'levels'): void {
        const gm = window.graphManager;
        if (!gm) return;
        const s = GraphToolbar.state();
        if (layout === s.layout) { GraphToolbar.closeAll(); GraphToolbar.syncAll(); return; }
        const blocked = GraphToolbar.mapTabDisabled({ layout: s.layout });
        if (layout === 'map' && blocked) {
            if (typeof toastError === 'function') toastError(blocked);
            GraphToolbar.syncAll();
            return;
        }
        if (layout === 'levels') {
            gm.toggleLayoutMode();               // flips config.graphLayoutMode
        } else if (layout === 'map') {
            gm.toggleCardinalLayout();           // flips _cardinalLayout
        } else {
            // Leaving Levels for Graph: free physics again.
            if (s.layout === 'levels') gm.toggleLayoutMode();
            if (s.layout === 'map') gm.toggleCardinalLayout();
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
    setOverlay(overlay: string): void {
        const gm = window.graphManager;
        if (!gm) return;
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
    togglePopover(ev: Event | undefined, id: string): void {
        if (ev) ev.stopPropagation();
        const menu = document.getElementById(id);
        if (!menu) return;
        const wasOpen = menu.classList.contains('menu-open');
        GraphToolbar.closeAll();
        if (wasOpen) return;
        menu.style.display = 'block';
        menu.classList.add('menu-open');
        GraphToolbar._bindGlobalClose();
        GraphToolbar.syncAria();
        // Reflect freshly-picked state in the chips of the popover just opened.
        GraphToolbar.syncOverlayChips();
        GraphToolbar.syncDisabled();
    },

    /** Close every open toolbar popover. */
    closeAll(): void {
        const open = document.querySelectorAll<HTMLElement>('.dropdown-menu.menu-open');
        open.forEach(m => { m.style.display = 'none'; m.classList.remove('menu-open'); });
        if (open.length) {
            document.removeEventListener('click', GraphToolbar._outsideClick, true);
            document.removeEventListener('keydown', GraphToolbar._outsideKey, true);
        }
        GraphToolbar.syncAria();
    },

    _bindGlobalClose(): void {
        document.removeEventListener('click', GraphToolbar._outsideClick, true);
        document.removeEventListener('keydown', GraphToolbar._outsideKey, true);
        document.addEventListener('click', GraphToolbar._outsideClick, true);
        document.addEventListener('keydown', GraphToolbar._outsideKey, true);
    },

    // Capture phase: a click on an item calls closeTopMenus() from its bubble
    // handler, so listening later would miss the same click.
    _outsideClick(e: MouseEvent): void {
        const open = Array.from(document.querySelectorAll<HTMLElement>('.dropdown-menu.menu-open'));
        const target = e.target as Node | null;
        for (const menu of open) {
            const trigger = menu.parentElement ? menu.parentElement.querySelector('button') : null;
            if (menu.contains(target)) continue;
            if (trigger && trigger.contains(target)) continue;
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

    _outsideKey(e: KeyboardEvent): void {
        if (e.key !== 'Escape') return;
        if (!document.querySelector('.dropdown-menu.menu-open')) return;
        GraphToolbar.closeAll();
    },

    // ──────────────────────────────────────────────
    //  DOM sync
    // ──────────────────────────────────────────────

    /** Repaint every control from the current state. Cheap; safe to call often. */
    syncAll(): void {
        GraphToolbar.syncLayout();
        GraphToolbar.syncOverlayChips();
        GraphToolbar.syncToggles();
        GraphToolbar.syncDisabled();
        GraphToolbar.syncScope();
    },
    /** `aria-selected` on the layout segment; the Map tab greys out under Levels. */
    syncLayout(): void {
        const s = GraphToolbar.state();
        document.querySelectorAll<HTMLButtonElement>('#layout-segment [data-layout]').forEach(tab => {
            const layout = tab.dataset.layout;
            const selected = layout === s.layout;
            tab.setAttribute('aria-selected', selected ? 'true' : 'false');
            tab.classList.toggle('active', selected);
            const blocked = layout === 'map' ? GraphToolbar.mapTabDisabled(s) : null;
            tab.disabled = !!blocked;
            if (blocked) tab.title = blocked;
        });
    },

    /** Which overlay chip is on. `none` is highlighted for the structural view. */
    syncOverlayChips(): void {
        const s = GraphToolbar.state();
        document.querySelectorAll<HTMLElement>('.overlay-toggle').forEach(chip => {
            const on = chip.dataset.overlay === s.overlay;
            chip.classList.toggle('active', on);
            chip.setAttribute('aria-pressed', on ? 'true' : 'false');
        });
    },

    /** `aria-pressed` mirrors the state of every boolean toggle in the bar. */
    syncToggles(): void {
        const gm = window.graphManager;
        if (!gm) return;
        const press = (id: string, on: boolean): void => {
            const el = document.getElementById(id);
            if (!el) return;
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
        if (phys) phys.setAttribute('aria-pressed', gm._physicsEnabled ? 'true' : 'false');
    },

    /**
     * Honest affordances: disable what cannot run, and say why in the tooltip.
     * The label never changes — the label is "⏸ Physics" whatever the state.
     */
syncDisabled(): void {
        const s = GraphToolbar.state();
        const phys = GraphToolbar.physicsAvailability(s);
        const physBtn = document.getElementById('btn-physics') as HTMLButtonElement | null;
        if (physBtn) {
            physBtn.disabled = !phys.enabled;
            physBtn.title = phys.enabled
                ? (s.physicsEnabled ? 'Pause the simulation and freeze every node where it is' : 'Resume the simulation — nodes start moving again')
                : phys.reason;
        }
        const keepLabel = document.getElementById('keep-label');
        const keepBox = document.getElementById('search-keep-in-place') as HTMLInputElement | null;
        const keepReason = GraphToolbar.keepInPlaceDisabled(s);
        if (keepBox) keepBox.disabled = !!keepReason;
        if (keepLabel) {
            if (keepReason) { keepLabel.title = keepReason; keepLabel.classList.add('disabled'); }
            else { keepLabel.title = 'Keep matches where they are instead of gathering them into a cluster (remembered)'; keepLabel.classList.remove('disabled'); }
        }
        const paste = document.getElementById('menu-paste-response') as HTMLButtonElement | null;
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
    _nodeCounts(): GraphToolbarNodeCounts {
        const gm = window.graphManager;
        const nodes = (gm && gm._graphNodesObj) || {};
        const counts: Record<string, number> = { area: 0, way: 0, item: 0, character: 0 };
        let other = 0;
        for (const id of Object.keys(nodes)) {
            const type = nodes[id] && nodes[id].type;
            if (Object.prototype.hasOwnProperty.call(counts, type)) counts[type] += 1;
            else other += 1;
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

    _plural(n: number, noun: string): string { return `${n} ${noun}${n === 1 ? '' : 's'}`; },

    /** The loaded dataset, described in one line. */
    _countsText(counts: GraphToolbarNodeCounts | null | undefined, detailed?: boolean): string {
        if (!counts || !counts.total) return '';
        if (detailed) {
            const parts = [GraphToolbar._plural(counts.area, 'area'), GraphToolbar._plural(counts.way, 'way')];
            if (counts.character) parts.push(GraphToolbar._plural(counts.character, 'character'));
            if (counts.item) parts.push(GraphToolbar._plural(counts.item, 'item'));
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
    syncScope(): void {
        const s = GraphToolbar.state();
        const chipIcon = document.querySelector('.scope-chip-icon');
        if (chipIcon) chipIcon.textContent = s.scope ? '🗺️' : '🌍';
        const counts: GraphToolbarNodeCounts = GraphToolbar._nodeCounts();
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
        if (scopeTree) scopeTree.render();
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
    syncScopeBar(counts?: GraphToolbarNodeCounts): void {
        const bar = document.getElementById('scope-bar');
        if (!bar) return;
        const toolbar = document.getElementById('graph-toolbar');
        const s = GraphToolbar.state();
        const gm = window.graphManager;
        const stats = counts || GraphToolbar._nodeCounts();

        if (!s.scope) {
            bar.hidden = true;
            if (toolbar) toolbar.classList.remove('scope-bar-open');
            return;
        }
        bar.hidden = false;
        if (toolbar) toolbar.classList.add('scope-bar-open');

        const barStat = document.getElementById('scope-bar-stats');
        if (barStat) barStat.textContent = GraphToolbar._countsText(stats, true);

        const crumbs = document.getElementById('scope-breadcrumb');
        if (!crumbs) return;
        let trail = GraphToolbar.breadcrumbTrail((gm && gm._scopeSummaries) || [], s.scope);
        if (!trail.length) {
            // Stale selection (a scope the manifest no longer lists): fall back to
            // whatever the picker is showing rather than an empty trail.
const sel = document.getElementById('graph-scope-filter') as HTMLSelectElement | null;
            const opt = sel && sel.selectedOptions && sel.selectedOptions[0];
            trail = [{ id: s.scope, name: ((opt && opt.textContent) || s.scope).trim() }];
        }
        crumbs.textContent = '';
        trail.forEach((node: GraphToolbarBreadcrumb, i: number) => {
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
            } else {
                crumb.title = `Load ${node.name} instead of this scope`;
                crumb.addEventListener('click', () => GraphToolbar.loadScope(node.id));
            }
            crumbs.appendChild(crumb);
        });
    },

    /** Load a scope by id, keeping the picker's value in step. */
    loadScope(scopeId: string): void {
        const sel = document.getElementById('graph-scope-filter') as HTMLSelectElement | null;
        if (sel) sel.value = scopeId || '';
        const gm = window.graphManager;
        if (gm) gm.setScopeFilter(scopeId);
    },

    /**
     * Open the WorldPainter already pointed at the loaded scope: it takes a scope
     * id and the bar already knows it. This is the bridge between "inspect this
     * zone in the graph" and "paint this zone".
     */
    openScopeInWorldPainter(): void {
        const gm = window.graphManager;
        const scopeId = gm && gm._scopeFilter;
        if (!scopeId) return;
        const painter = window.VW && VW.worldPainter;
        if (!painter || typeof painter.open !== 'function') {
            if (typeof toastError === 'function') toastError('The WorldPainter is not available.');
            return;
        }
        painter.open(scopeId);
    },

    /** Unload the scope: put the whole world back on the canvas. */
    showWholeWorld(): void {
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

    _collapseHomes: null as GraphToolbarCollapseHome[] | null,
    _overflowGroup: null as HTMLElement | null,
    _collapsed: null as boolean | null,
    _collapseQuery: null as MediaQueryList | null,

    /**
     * Record where each collapsible node lives once, then follow the viewport.
     * Relocation (not hiding) keeps every handler, title and aria attribute: a
     * hidden control is unreachable, a moved one is still one click away.
     */
    _initCollapse(): void {
        const group = document.getElementById('toolbar-overflow');
        if (!group) return;
        GraphToolbar._overflowGroup = group;
        GraphToolbar._collapseHomes = [];
        for (const id of GraphToolbar.COLLAPSE_IDS) {
            const el = document.getElementById(id);
            if (!el || !el.parentElement) continue;
            GraphToolbar._collapseHomes.push({ el, parent: el.parentElement, next: el.nextElementSibling });
        }
        if (typeof window.matchMedia !== 'function') return;
        GraphToolbar._collapseQuery = window.matchMedia(GraphToolbar.COLLAPSE_QUERY);
        GraphToolbar._applyCollapse(GraphToolbar._collapseQuery.matches);
        if (typeof GraphToolbar._collapseQuery.addEventListener === 'function') {
            GraphToolbar._collapseQuery.addEventListener('change', (e: MediaQueryListEvent) => GraphToolbar._applyCollapse(e.matches));
        }
    },

    _applyCollapse(collapsed: boolean): void {
        const group = GraphToolbar._overflowGroup;
        const homes = GraphToolbar._collapseHomes;
        if (!group || !homes || collapsed === GraphToolbar._collapsed) return;
        GraphToolbar._collapsed = collapsed;
        if (collapsed) {
            for (const home of homes) group.appendChild(home.el);
        } else {
            for (const home of homes) {
                if (home.next && home.next.parentElement === home.parent) home.parent.insertBefore(home.el, home.next);
                else home.parent.appendChild(home.el);
            }
        }
        group.hidden = !collapsed;
        const doZone = document.querySelector('.toolbar-zone[aria-label="Create and history"]');
        if (doZone) doZone.classList.toggle('collapsed', collapsed);
        // Physics may have just moved into the overflow: its disabled rule is
        // computed on the node, so repaint either way.
        GraphToolbar.syncAll();
    },

    /** `aria-expanded` on every popover trigger, from the `menu-open` class. */
    syncAria(): void {
        document.querySelectorAll<HTMLButtonElement>('.toolbar-dropdown > button').forEach(btn => {
            const menu = btn.nextElementSibling;
            const open = !!(menu && menu.classList.contains('menu-open'));
            btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        });
    },

    /** Hide the legend (its ✕ button). */
    closeLegend(): void {
        const gm = window.graphManager;
        if (!gm || !gm._legendEl) return;
        gm._legendVisible = false;
        gm._legendEl.style.display = 'none';
        GraphToolbar.syncToggles();
    },

    // ──────────────────────────────────────────────
    //  Wiring
    // ──────────────────────────────────────────────

    init(): void {
        // The legend is rebuilt as HTML on every overlay change, so its ✕ is
        // delegated rather than bound.
        document.addEventListener('click', (e) => {
            const target = e.target as Element;
            if (target.closest && target.closest('[data-legend-close]')) {
                e.stopPropagation();
                GraphToolbar.closeLegend();
            }
        });
        // Keep the search box's own disabled rules honest if it is filled by code
        // (a palette jump, a "find" link) rather than by typing.
        const search = document.getElementById('graph-search');
        if (search) search.addEventListener('input', () => GraphToolbar.syncDisabled());
        // Relocated toolbar buttons act inside the More menu: let the action run,
        // then close it. The undo-history panel is exempt — it is absolutely
        // positioned inside the menu, so hiding the menu would hide the panel.
        const overflow = document.getElementById('toolbar-overflow');
        if (overflow) {
            overflow.addEventListener('click', (e) => {
                const target = e.target as Element;
                if (!target.closest || !target.closest('button')) return;
                if (target.closest('[data-role="undo-history-toggle"]')) return;
                // `closeTopMenus` is only defined once its module has loaded, and
                // has no ambient declaration, so read it through `window`.
                const closeTopMenusFn = (window as unknown as { closeTopMenus?: () => void }).closeTopMenus;
                if (typeof closeTopMenusFn === 'function') closeTopMenusFn();
            });
        }
        GraphToolbar._initCollapse();
        GraphToolbar.syncAll();
    },
};

// Types used above. A top-level `interface` in a classic script is a global, so
// every name here is prefixed with the file stem to stay unique across modules.
interface GraphToolbarPhysicsState {
    layout?: string;
    overlay?: string;
    paintedGrid?: boolean;
    mapLocked?: boolean;
    physicsEnabled?: boolean;
}
interface GraphToolbarLayoutState { layout?: string; }
interface GraphToolbarSearchState { searchQuery?: string; }
interface GraphToolbarManualState { manualMode?: boolean; }
interface GraphToolbarPhysicsAvailability { enabled: boolean; reason: string; }
/** One row of `graphManager._scopeSummaries`, the flat scope manifest. */
interface GraphToolbarScopeSummary { id: string; name?: string; parent_id?: string | null; }
/** One breadcrumb crumb: root first, loaded scope last. */
interface GraphToolbarBreadcrumb { id: string; name: string; }
/** `_nodeCounts` result; the key order is the scope chip's tooltip order. */
interface GraphToolbarNodeCounts {
    area: number; way: number; item: number; character: number; other: number; total: number;
}
/** Where a collapsible toolbar control lives, recorded once by `_initCollapse`. */
interface GraphToolbarCollapseHome { el: HTMLElement; parent: HTMLElement; next: Element | null; }
/** Plain snapshot of everything the toolbar's rules depend on. */
interface GraphToolbarState {
    layout: string;
    overlay: string;
    paintedGrid: boolean;
    mapLocked: boolean;
    physicsEnabled: boolean;
    searchQuery: string;
    manualMode: boolean;
    legendVisible: boolean;
    scope: string;
}

if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => GraphToolbar.init());
    } else {
        GraphToolbar.init();
    }
}
