/**
 * GraphManager — graph-view facade: the single `graphManager` singleton the rest of
 * the app talks to. The heavy lifting lives in static/js/graph/* (GraphNetwork,
 * GraphEventHandlers, GraphContextMenu, GraphProjection, GraphFocus, GraphOverlays,
 * GraphLayoutEngine). Many methods here are thin, deprecated delegates kept so
 * existing callers and HTML onclick handlers keep working.
 *
 * @module graph-manager — graph view facade + shared graph state
 * @contributes `graphManager`: network handle, node map, filters, reveal/bulk/floor state
 * @powers the graph view — rendering, context menus, search/focus, overlays, authoring
 * @relates delegates to static/js/graph/*; reads worldState; used by inspector + nl-editor
 * @docs docs/virtualWorld/UI & Settings/Rendering & UI Modules.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
const graphManagerHtmlTag = (strings: TemplateStringsArray, ...values: unknown[]) => window.Lit.html(strings, ...values);

// ── File-local types ────────────────────────────────────────────────────────
// A top-level `type` in a classic script is a GLOBAL declaration, so every name
// here is prefixed with this file's stem and declared nowhere else.

// A graph node as this facade reads it. graph/network-manager.ts builds these,
// so the property bag is genuinely open — index signature rather than `unknown`,
// which would reject every property access.
type GraphManagerNodeData = {
    id?: string;
    name?: string;
    type?: string;
    properties?: Record<string, any>;
    [key: string]: any;
};

// An edge in worldState.graph.edges / graphManager._graphEdgesArr. source and
// target are always present on a rendered edge; type and properties are not.
type GraphManagerEdgeData = {
    source: string;
    target: string;
    type?: string;
    properties?: Record<string, any>;
    [key: string]: any;
};

// One entry of /api/world/scopes after ScopeOptions.flattenScopes flattens the
// nested tree. id and name are always returned; the rest is optional.
type GraphManagerScopeSummary = {
    id: string;
    name: string;
    depth?: number;
    parent_id?: string | null;
    map_offset?: { x?: number; y?: number } | null;
    [key: string]: any;
};

// graphManager._contextTarget is either a node target (context menu on a node)
// or an edge target (context menu on an edge), so every field is optional.
type GraphManagerContextTarget = {
    nodeData?: any;
    nodeId?: string;
    nodeType?: string;
    edgeData?: any;
    isEdge?: boolean;
} | null;

// The ApiClient endpoints this facade calls that the ambient shim in
// types/globals.d.ts does not carry. Widened locally rather than editing the hub.
type GraphManagerApi = {
    getWorldScopes(includeFlat?: boolean): Promise<{ scopes?: GraphManagerScopeSummary[] } | null>;
    setScopeAreas(scopeId: string, areaIds: string[], cellIds: unknown[]): Promise<unknown>;
    deleteNode(nodeId: string): Promise<unknown>;
    updateNode(nodeId: string, data: unknown): Promise<unknown>;
    movePlayerToRoom(charName: string, areaName: string): Promise<{ error?: string }>;
    createCharacter(name: string): Promise<{ error?: string }>;
    createEdge(from: string, to: string, type: string, properties?: Record<string, unknown>):
        Promise<{ status?: string; error?: string }>;
    updateEdge(from: string, to: string, data: Record<string, unknown>):
        Promise<{ status?: string; error?: string }>;
    duplicateNode(nodeId: string, includeChildren?: boolean):
        Promise<{ id?: string; name?: string; cloned?: number; error?: string } | null>;
};

// graph/node-operations.ts publishes this on window (line 628 of that file).
type GraphManagerNodeOps = {
    deleteNode(nodeId: string): Promise<unknown>;
    deleteEdge(source: string, target: string, edgeType: string): Promise<unknown>;
    createSpecialEdge(fromNodeId: string, edgeType: string, emoji: string): Promise<unknown>;
    _showDuplicateChoiceModal(html: string, title: string): Promise<boolean>;
};

// graph/edge-types.ts publishes on window (line 92) as well as binding the bare
// name. Read through `window` so a missing module is undefined rather than a
// ReferenceError, and so the ambient `EdgeTypes: any` can be narrowed here.
type GraphManagerEdgeTypes = {
    validForSource(nodeType: string | undefined): string[];
    validTargets(edgeType: string): string[];
    getConfig(edgeType: string): { icon: string; label: string; desc: string; color?: string };
};

// shared/scope-options.ts publishes this on window.
type GraphManagerScopeOptions = {
    flattenScopes(payload: unknown): GraphManagerScopeSummary[];
    populate(sel: Element, scopes: GraphManagerScopeSummary[]): void;
};

// graph/layout-engine.ts's ambient shape predates mapCompact (task-526).
type GraphManagerLayoutEngine = { mapCompact?: () => boolean };

/**
 * A storey index as the picker words it: 0 is ground, a positive number is a
 * floor above it, a negative one is below. `floor` is deliberately unbounded
 * (three stacked rooms, a lake bottom, an 80-storey tower, -900 in a hole to
 * hell), so the label never clamps — it just says which way is which.
 */
function _floorOptionLabel(floor: number) {
    if (floor === 0) return 'Ground (0)';
    return floor > 0 ? `Floor ${floor}` : `Floor ${floor} (below ground)`;
}

// Named `GraphManagerImpl` because types/globals.d.ts declares a hand-written
// global `interface GraphManager` for the un-converted .js. An interface and a
// class of the same name MERGE, and a merged duplicate member must have an
// identical type — the interface says `any` for most of these fields, so a
// merged `nodes: Map<...>` would be TS2717. Renaming keeps the two independent;
// the interface should be deleted once this conversion lands.
class GraphManagerImpl {
    // ── State this class owns ──────────────────────────────────────────────
    // Every field the constructor assigns is declared here. `declare` erases at
    // emit, so no `this.x;` initializer is generated (useDefineForClassFields is
    // on for target ES2022 and would otherwise add a property definition that
    // HEAD never had). Other modules READ these off the singleton, so a field
    // missing here is a field no reader can see.
    /** vis Network handle. vis-network is vendored and ships no types. */
    declare network: any;
    declare nodes: Map<string, GraphManagerNodeData>;
    declare _contextTarget: GraphManagerContextTarget;
    declare _lastSig: string;          // hash to skip redundant reloads
    declare _scopeFilter: string | null;    // task-397: load one world scope at a time
    declare _scopeOffsets: Record<string, { x?: number; y?: number } | null>; // task-523
    declare _physicsEnabled: boolean;
    declare _legendEl: any;
    declare _searchQuery: string;
    declare _viewMode: string;
    declare _cardinalLayout: boolean;
    declare _paintedGridLayout: boolean;
    declare _showEdgeLabels: boolean;
    declare _edgeLabelSize: number;
    declare _showNodeLabels: boolean;
    declare _nodeLabelsShown: boolean | null;   // last applied decision (avoid churn)
    declare _labelCache: any;        // decorated labels saved while hidden
    declare _mapSpacingAuto: boolean;
    declare _showItems: boolean;
    declare _showOnlyInhabitedAreas: boolean;
    declare _revealedAreaIds: Set<string>;
    declare _pendingConnection: { fromNodeId: string; edgeType: string; fromName: string } | null;
    declare _revealedItemIds: Map<string, any>;
    declare _bulkSelection: Set<string>;
    declare _bulkBar: HTMLElement | null;
    declare _floorFilter: string;
    declare _floorOptions: string[];
    declare _showImages: boolean;

    // ── State assigned outside the constructor ─────────────────────────────
    // Set by the bulk-bar lifecycle, the scope-filter load, graph/focus.ts's
    // search box, and graph/network-manager.ts (the graph renderer). Declared
    // here so every one of those readers and writers type-checks against the
    // real class rather than dropping to `any`.
    declare _bulkScopesFilled: boolean;
    declare _scopeSummaries: GraphManagerScopeSummary[];
    declare _graphNodesObj: Record<string, GraphManagerNodeData>;
    declare _graphEdgesArr: GraphManagerEdgeData[];
    declare _searchKeepInPlace: boolean | undefined;
    declare _baseNodeStyles: any;
    declare _baseEdgeStyles: any;
    declare _edgeTooltipHtml: any;
    declare _legendVisible: boolean | undefined;
    declare _overlayMode: string | undefined;
    declare _showTriggers: boolean | undefined;
    declare _tagFilter: any;
    declare _tagLibrary: any;
    declare _tagPanelEl: any;
    declare _tagPanelVisible: boolean | undefined;

    constructor() {
        this.network = null;
        this.nodes = new Map();
        this._contextTarget = null;
        this._lastSig = '';          // hash to skip redundant reloads
        this._scopeFilter = null;    // task-397: load one world scope at a time
        this._scopeOffsets = {};     // task-523: scopeId -> {x,y} map offset (cells)
        this._physicsEnabled = true;
        this._legendEl = null;
        this._searchQuery = '';
        this._viewMode = 'graph';
        // bug-510: the Map tab's on/off choice persists (config.graphCardinalLayout).
        // Re-read in init() too, after config's load promise resolves.
        this._cardinalLayout = (typeof config !== 'undefined' && config)
            ? config.graphCardinalLayout === true : false;
        // task-530: set by the load path when the painted grid laid the nodes out.
        // The painted lattice owns positions, so physics must be disabled — and
        // the toolbar shows that instead of pretending the toggle still works.
        this._paintedGridLayout = false;
        this._showEdgeLabels = true;
        this._edgeLabelSize = 8;
        // Node-name labels: a manual toggle plus zoom LOD, because a dense
        // painted map (1k+ cells) becomes a wall of text at overview zoom.
        this._showNodeLabels = (() => {
            try { const stored = localStorage.getItem('vw_graphNodeLabels'); return stored !== null ? stored === '1' : true; } catch (e) { return true; }
        })();
        this._nodeLabelsShown = null;   // last applied decision (avoid churn)
        this._labelCache = null;        // decorated labels saved while hidden
        // Map pitch ownership (task-526): true while the pitch is the derived
        // default (re-derived from the painted extent on every load), false once
        // the user nudges it. Read from the persisted config so a reload keeps the
        // choice they made rather than re-deriving over it.
        this._mapSpacingAuto = (typeof config !== 'undefined' && config)
            ? config.graphMapSpacingAuto !== false : true;
        this._showItems = false;
        this._showOnlyInhabitedAreas = true;
        this._revealedAreaIds = new Set();
        this._pendingConnection = null;
        this._revealedItemIds = new Map();
        // task-378: bulk selection (shift-click) + action bar.
        this._bulkSelection = new Set();
        this._bulkBar = null;
        this._floorFilter = 'all';
        this._floorOptions = [];
        this._showImages = (() => {
            try { const stored = localStorage.getItem('vw_graphShowImages'); return stored !== null ? stored === '1' : true; } catch (e) { return true; }
        })();
    }

    async init() {
        await GraphNetwork.init();
        if (window.GraphBackground) await window.GraphBackground.init();
        await this._applyEngineConfigDefaults();
        // bug-510: config._initPromise resolved before init() runs (main.js), so
        // the persisted Map choice is available here even if the constructor saw
        // a pre-load default.
        if (typeof config !== 'undefined' && config && config.graphCardinalLayout === true) {
            this._cardinalLayout = true;
        }
        this._syncMapSpacingButton();
        this._watchScopeChanges();
    }

    /**
     * Persist the Map-tab on/off choice (bug-510) so a reload keeps it. Mirrors
     * the fire-and-forget save `GraphNetwork.toggleLayoutMode` uses for Levels.
     */
    _persistCardinalLayout() {
        if (typeof config === 'undefined' || !config) return;
        config.graphCardinalLayout = this._cardinalLayout === true;
        if (typeof config.save === 'function') {
            try { config.save(); } catch (e) { /* keep the session value */ }
        }
    }

    /**
     * Keep the scope picker and the scope bar in step with the manifest
     * (bug-50). Both are derived from `loadScopeFilterOptions`, and nothing
     * called it after a rename, so a scope the author had just renamed kept
     * showing its **old** name in the graph's picker and breadcrumb until a full
     * page reload — including a rename made by an external agent over MCP or
     * reverted by Undo, since those publish the same `world_changed` event.
     *
     * The predicate is deliberately narrow. Painting, placing and offset drags
     * also live under `/api/world/scopes/...` and are far too frequent to
     * refetch the list for; the routes below are the only ones that can change
     * a scope's *name or place in the tree*, plus the whole-world operations
     * (undo, redo, reset, load) that can revert one.
     */
    _watchScopeChanges() {
        if (!window.appEvents) return;
        const WHOLE_WORLD = /^\/(api\/(undo|redo|reset|load)|api\/load-game\/)/;
        appEvents.on('world:changed', (ev: any) => {
            const path = String((ev && ev.path) || '');
            const renamesScope = path.startsWith('/api/world/scopes')   // created
                || /\/rename$/.test(path)                              // renamed
                || /\/delete$/.test(path)                              // deleted
                || WHOLE_WORLD.test(path);                            // undo/redo/reset/load
            if (renamesScope) this.loadScopeFilterOptions();
        });
    }

    // ───────────── Bulk selection (task-378 / audit #12) ─────────────
    _toggleBulkSelect(nodeId: string) {
        if (!nodeId) return;
        if (this._bulkSelection.has(nodeId)) this._bulkSelection.delete(nodeId);
        else {
            if (this._bulkSelection.size >= 100) { if (typeof toastError === 'function') toastError('Bulk selection capped at 100 nodes.'); return; }
            this._bulkSelection.add(nodeId);
        }
        try { this.network?.selectNodes([...this._bulkSelection]); } catch (e) { /* ignore */ }
        this._updateBulkBar();
    }
    _clearBulkSelection() {
        this._bulkSelection.clear();
        try { this.network?.unselectAll(); } catch (e) { /* ignore */ }
        if (this._bulkBar) { this._bulkBar.remove(); this._bulkBar = null; }
        // The bar carries the populated scope list, so a fresh one has to refill.
        this._bulkScopesFilled = false;
    }
    _updateBulkBar() {
        if (!this._bulkSelection.size) {
            if (this._bulkBar) { this._bulkBar.remove(); this._bulkBar = null; }
            return;
        }
        if (!this._bulkBar) {
            const bar = document.createElement('div');
            bar.id = 'bulk-action-bar';
            bar.style.cssText = 'position:absolute;left:12px;bottom:12px;z-index:50;display:flex;align-items:center;gap:6px;background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:6px 10px;font-size:11px;box-shadow:0 8px 24px rgba(0,0,0,.5);';
            bar.innerHTML =
                '<span id="bulk-count" style="color:var(--text-muted);"></span>' +
                '<select id="bulk-scope" title="Move every selected area into one scope. ' +
                'Membership only — a scope is not a painted cell. One undo step for the whole selection." ' +
                'style="font-size:11px;padding:2px;border-radius:5px;max-width:150px;">' +
                '<option value="">🗺️ Scope…</option></select>' +
                '<button class="btn btn-sm" id="bulk-tag">🏷 Tag</button>' +
                '<button class="btn btn-sm" id="bulk-state">⚠ State</button>' +
                '<button class="btn btn-sm" id="bulk-delete" style="background:#3a1a1a;color:#ff6b6b;">🗑 Delete</button>' +
                '<button class="btn btn-sm" id="bulk-clear">✕ Clear</button>';
            bar.querySelector('#bulk-tag')!.addEventListener('click', () => graphManager._bulkTag());
            bar.querySelector('#bulk-state')!.addEventListener('click', () => graphManager._bulkState());
            bar.querySelector('#bulk-delete')!.addEventListener('click', () => graphManager._bulkDelete());
            bar.querySelector('#bulk-clear')!.addEventListener('click', () => graphManager._clearBulkSelection());
            bar.querySelector('#bulk-scope')!.addEventListener('change', (ev) => {
                const target = (ev.target as HTMLSelectElement).value;
                (ev.target as HTMLSelectElement).value = '';       // so the same scope can be picked twice
                if (target) graphManager._bulkScope(target);
            });
            const host = document.getElementById('graph-container');
            (host || document.body).appendChild(bar);
            this._bulkBar = bar;
            this._fillBulkScopes();
        }
        const count = this._bulkBar.querySelector('#bulk-count');
        if (count) count.textContent = `${this._bulkSelection.size} selected — `;
    }

    /**
     * Fill the bulk bar's scope picker once (task-539). The option list comes
     * from the server, so a new scope needs no front-end change, and the
     * placeholder is always re-selected afterwards so the control reads as a
     * one-shot action rather than a filter.
     */
    async _fillBulkScopes() {
        const _gmApi = ApiClient as unknown as GraphManagerApi;
        const sel = this._bulkBar && this._bulkBar.querySelector('#bulk-scope');
        if (!sel || this._bulkScopesFilled) return;
        this._bulkScopesFilled = true;
        try {
            const data = await _gmApi.getWorldScopes(true);
            const scopes = (data && data.scopes) || [];
            sel.innerHTML = '<option value="">🗺️ Scope…</option>';
            scopes.forEach((s) => {
                const opt = document.createElement('option');
                opt.value = s.id;
                // flat_scopes is depth-first with a `depth`, so a nested scope
                // reads as a child of the one above it.
                opt.textContent = `${'  '.repeat(s.depth || 0)}${s.name}`;
                sel.appendChild(opt);
            });
        } catch (e) {
            this._bulkScopesFilled = false;   // let a later selection retry
            sel.innerHTML = '<option value="">scopes unavailable</option>';
        }
    }

    /**
     * Move the whole selection into one scope (task-539), in a single request so
     * it is one undo step. The route refuses generated areas, so if the
     * selection mixes hand-written and generated areas nothing is moved and the
     * reason is reported.
     */
    async _bulkScope(scopeId: string) {
        const _gmApi = ApiClient as unknown as GraphManagerApi;
        const _gmWin = window as unknown as {
            worldSync?: { refresh?: () => void };
            toastSuccess?: (msg: string) => void;
        };
        const ids = [...this._bulkSelection];
        if (!ids.length || !scopeId) return;
        // The display name, not the id: the picker already had the name on screen
        // and a message like "moved into deep_woods_2" undoes a rename in the
        // author's eyes.
        const label = (this._scopeSummaries || []).find((s) => s.id === scopeId)?.name || scopeId;
        try {
            await _gmApi.setScopeAreas(scopeId, ids, []);
            await worldState.fetch();
            this._clearBulkSelection();
            if (typeof _gmWin.worldSync !== 'undefined' && _gmWin.worldSync?.refresh) {
                _gmWin.worldSync.refresh();
            }
            if (typeof _gmWin.toastSuccess === 'function') {
                _gmWin.toastSuccess(`Moved ${ids.length} area(s) into ${label}.`);
            }
        } catch (e) {
            if (typeof toastError === 'function') toastError(`Scope change failed: ${(e as Error).message || e}`);
        }
    }

    async _bulkTag() {
        const _gmApi = ApiClient as unknown as GraphManagerApi;
        const _gmToast = window as unknown as { toastSuccess?: (msg: string) => void };
        const tags = prompt('Add tag(s) to the selected nodes (comma-separated):');
        if (!tags || !tags.trim()) return;
        const add = tags.split(',').map(t => t.trim()).filter(Boolean);
        const ids = [...this._bulkSelection];
        for (const id of ids) {
            const node = this.nodes.get(id);
            const existing = (node?.properties?.tags || []).map(String);
            const merged = [...new Set([...existing, ...add])];
            try { await _gmApi.updateNode(id, { properties: { tags: merged } }); } catch (e) { /* keep going */ }
        }
        await worldState.fetch();
        this._clearBulkSelection();
        if (typeof _gmToast.toastSuccess === 'function') _gmToast.toastSuccess(`Tagged ${ids.length} node(s): ${add.join(', ')}`);
    }
    async _bulkState() {
        const _gmApi = ApiClient as unknown as GraphManagerApi;
        const _gmToast = window as unknown as { toastSuccess?: (msg: string) => void };
        const state = prompt('Set current_state on selected nodes (e.g. on/closed/locked):');
        if (!state || !state.trim()) return;
        const ids = [...this._bulkSelection];
        for (const id of ids) {
            try { await _gmApi.updateNode(id, { properties: { current_state: state.trim() } }); } catch (e) { /* keep going */ }
        }
        await worldState.fetch();
        this._clearBulkSelection();
        if (typeof _gmToast.toastSuccess === 'function') _gmToast.toastSuccess(`State set to "${state.trim()}" on ${ids.length} node(s).`);
    }
    async _bulkDelete() {
        const _gmApi = ApiClient as unknown as GraphManagerApi;
        const _gmToast = window as unknown as { toastSuccess?: (msg: string) => void };
        const ids = [...this._bulkSelection];
        if (!confirm(`Delete ${ids.length} node(s)? (undo-safe)`)) return;
        for (const id of ids) {
            try { await _gmApi.deleteNode(id); } catch (e) { /* keep going */ }
        }
        await worldState.fetch();
        this._clearBulkSelection();
        if (typeof _gmToast.toastSuccess === 'function') _gmToast.toastSuccess(`Deleted ${ids.length} node(s).`);
    }

    async _applyEngineConfigDefaults() {
        try {
            const resp = await fetch('/api/settings/engine_config');
            if (!resp.ok) return;
            const data = await resp.json();
            const values = data.values || {};
            if ('graph.physics_enabled' in values) {
                this._physicsEnabled = !!values['graph.physics_enabled'];
                // Hierarchical mode owns positions: the solver would drag nodes
                // off their levels, so the stored preference is not applied there.
                const on = this._physicsEnabled && !this._levelsMode();
                if (this.network) {
                    GraphNetwork.applyModePhysics(on);
                }
            }
            if ('graph.show_items' in values) {
                this._showItems = !!values['graph.show_items'];
                const btn = document.getElementById('btn-items');
                if (btn) btn.classList.toggle('active', this._showItems);
                GraphNetwork.applyVisibility();
            }
            if ('graph.show_only_inhabited' in values) {
                this._showOnlyInhabitedAreas = !!values['graph.show_only_inhabited'];
                const btn = document.getElementById('btn-inhabited');
                if (btn) btn.classList.toggle('active', this._showOnlyInhabitedAreas);
                if (!this._showOnlyInhabitedAreas) {
                    this._revealedAreaIds.clear();
                }
                GraphNetwork.applyVisibility();
            }
        } catch (e) {
            console.warn('Failed to apply engine config graph defaults:', e);
        }
    }

    async _saveGraphConfigKey(key: string, value: unknown) {
        try {
            const resp = await fetch('/api/settings/engine_config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ values: { [key]: value } }),
            });
            if (!resp.ok) throw new Error('Failed to save graph config');
        } catch (e) {
            console.warn('Failed to save graph config:', e);
        }
    }

    _buildOptions() { return GraphNetwork.buildOptions(); }

    /**
     * Populate the graph view's scope picker (task-397 step 4). Safe to call
     * repeatedly: it preserves the current selection. Options are indented by
     * `depth` so the world's zone hierarchy reads as a tree.
     */
    async loadScopeFilterOptions() {
        const _gmApi = ApiClient as unknown as GraphManagerApi;
        const _gmScopeOptions = (window as unknown as { ScopeOptions: GraphManagerScopeOptions }).ScopeOptions;
        const sel = document.getElementById('graph-scope-filter') as HTMLSelectElement | null;
        const current = this._scopeFilter || '';
        try {
            const data = await _gmApi.getWorldScopes(true);
            // task-523: the flat summary carries each scope's map offset; the map
            // layout reads it per node, so the whole-world (descendant) view can
            // place every zone correctly after a drag. Populated even when the
            // picker element is absent, so the layout still has the offsets.
            this._scopeOffsets = {};
            // task-531: keep the summaries themselves. Each entry carries
            // `parent_id`, which is all the scope bar's breadcrumb needs to walk
            // up the zone tree — the only endpoint that returns a breadcrumb is
            // the WorldPainter's per-scope grid payload, and one request per scope
            // change is not worth it for a trail this short.
            // task-627: `/api/world/scopes` answers a NESTED tree under
            // `children` and has no `scopes` key and no `depth`, so
            // `data.scopes` was always `undefined` and the picker had never
            // rendered a single scope -- four child scopes existed and none were
            // reachable. Flatten it into depth-carrying summaries first.
            this._scopeSummaries = _gmScopeOptions.flattenScopes(data);
            for (const scope of this._scopeSummaries) {
                if (scope.map_offset) this._scopeOffsets[scope.id] = scope.map_offset;
            }
            if (!sel) return;
            sel.innerHTML = '';
            const wholeWorld = document.createElement('option');
            wholeWorld.value = '';
            wholeWorld.textContent = '🌍 Whole world';
            sel.appendChild(wholeWorld);
            // task-627: real <optgroup> nesting instead of leading nbsp padding.
            _gmScopeOptions.populate(sel, this._scopeSummaries);
            sel.value = current;
        } catch (e) {
            console.warn('Failed to load scope filter options:', e);
        }
        // The scope bar and its breadcrumb read _scopeSummaries, and a scenario
        // switch resets _scopeFilter without touching the picker (saveload-view),
        // so repaint rather than assume the previous state still holds. syncAll
        // repaints the scope tree too (task-397 step 4), so it needs no own call.
        if (window.GraphToolbar) GraphToolbar.syncAll();
    }

    /**
     * Load the graph one world scope at a time (empty id restores the whole
     * world). A scope loads only its own slice, so a huge painted world never
     * ships every node to the canvas (task-397 / task-400).
     */
    setScopeFilter(scopeId: string) {
        this._scopeFilter = scopeId || null;
        this._lastSig = '';
        if (window.GraphToolbar) GraphToolbar.syncAll();
        const loaded = this.loadGraphData();
        // A painted scope's art is derived from that scope's grid, and switching
        // scope loads a subgraph without a world fetch, so the map has to be
        // re-derived here or it keeps the previous grid's cells (bug-51).
        //
        // Guarded on the MODULE, not on the method. A `typeof
        // refreshForScope === 'function'` guard here is what turned commit
        // 6fd774b8's deletion of that function into a silent no-op: a missing
        // method and a module that had not loaded are indistinguishable at the
        // call site, and only the first one is a bug. The contract is pinned in
        // tools/unit/test_graph_background.js.
        if (window.GraphBackground) {
            loaded.then(() => window.GraphBackground.refreshForScope()).catch(() => { });
        }
        return loaded;
    }

    /**
     * Which layout the graph is in, as one of GraphToolbar.LAYOUTS. The layout
     * axis used to be three independent toggles whose state lived in their own
     * labels; the segmented control and every disabled rule read this instead.
     * @returns {'graph'|'map'|'levels'}
     */
    activeLayout() {
        if (this._levelsMode()) return 'levels';
        return this._cardinalLayout ? 'map' : 'graph';
    }

    /**
     * Turn the Map layout on/off. Returns false when the toggle is refused
     * because another layout owns positions (Levels) — the Map tab is disabled
     * in that state, this is the programmatic guard behind it (bug-48).
     * @returns {boolean} whether the layout changed
     */
    toggleCardinalLayout() {
        if (this._levelsMode()) {
            if (typeof toastError === 'function') {
                toastError('Map is unavailable while Levels owns the layout — pick Graph first, then Map.');
            }
            return false;
        }
        this._cardinalLayout = !this._cardinalLayout;
        this._persistCardinalLayout();   // bug-510: survive a reload
        if (window.GraphToolbar) GraphToolbar.syncAll();
        // The painted lattice owns positions in Map mode, but physics stays on
        // by default so edges don't get pushed around. An explicit toolbar toggle
        // still wins, and only that explicit choice is persisted — so a
        // reload always starts the graph view with the user's own preference.
        // Clear signature so loadGraphData doesn't skip the reload
        this._lastSig = '';
        this.loadGraphData();
        return true;
    }

    async loadGraphData() {
        this._clearBulkSelection();
        return GraphNetwork.loadGraphData();
    }

    /**
     * Nudge the map-layout pitch (px per painted cell) — the padding between
     * areas in Map mode. Persists to `config.graphMapSpacing`, re-lays the
     * painted grid at the new pitch, and re-aligns the map art. `delta` is
     * relative (e.g. +20 / -20 from the toolbar's +/- buttons).
     *
     * Nudging is a *decision*, so it ends auto-pitching (task-526): a person who
     * wants 40px/cell on a 200-cell world has to keep 40px/cell through reloads
     * and scope switches. `setAutoMapSpacing(true)` hands the pitch back.
     */
    async setMapSpacing(delta: number) {
        const current = this._mapSpacingValue();
        const next = Math.max(20, Math.min(1000, Math.round(current + Number(delta || 0))));
        if (typeof config !== 'undefined' && config) {
            config.graphMapSpacing = next;
            config.graphMapSpacingAuto = false;
        }
        this._mapSpacingAuto = false;
        try { storage.setConfig('graphMapSpacing', next); } catch (e) { /* keep the session value */ }
        try { storage.setConfig('graphMapSpacingAuto', '0'); } catch (e) { /* keep the session value */ }
        this._syncMapSpacingButton();
        this._lastSig = '';
        // Node boxes and item rings scale with the pitch, so the group options
        // have to be rebuilt before the data is re-laid out (bug-53).
        if (window.GraphNetwork && typeof GraphNetwork.applyGraphSettings === 'function') {
            try { GraphNetwork.applyGraphSettings(); } catch (e) { /* ignore */ }
        }
        await this.loadGraphData();
        // The art is positioned in px, so a pitch change must re-fit it. With a
        // scope selected that is `fitToPaintedGrid` (which also *saves* the fitted
        // rect — what a deliberate nudge wants). In the whole-world view there is
        // no single grid for it to fit to, so every mounted reference is
        // re-derived from its own scope instead, without writing the world.
        if (this._cardinalLayout && window.GraphBackground) {
            try {
                if (this._scopeFilter) {
                    await window.GraphBackground.fitToPaintedGrid();
                } else {
                    await window.GraphBackground.reconcileAllForGapChange();
                }
            } catch (e) { /* ignore */ }
        }
    }

    /**
     * Hand the map pitch back to auto-pitching (task-526), or take it back with
     * `false`. Re-derives from the painted extent on the next load, so it reloads
     * the graph by the same path a manual nudge does: the pitch feeds node sizes,
     * the lattice and the background art at once.
     */
    async setAutoMapSpacing(enabled: boolean) {
        const on = enabled !== false;
        this._mapSpacingAuto = on;
        if (typeof config !== 'undefined' && config) config.graphMapSpacingAuto = on;
        try { storage.setConfig('graphMapSpacingAuto', on ? '1' : '0'); } catch (e) { /* session value stands */ }
        this._syncMapSpacingButton();
        this._lastSig = '';
        await this.loadGraphData();
        if (this._cardinalLayout && window.GraphBackground) {
            // The load path already re-derived the art when the pitch moved; this
            // is the belt to that braces, and it writes nothing.
            try { await window.GraphBackground.reconcileAllForGapChange(); } catch (e) { /* ignore */ }
        }
    }

    _mapSpacingValue() {
        try {
            const value = Number(config && config.graphMapSpacing);
            return value > 0 ? value : 40;
        } catch (e) { return 40; }
    }

    /**
     * Show the effective pitch, and mark whether it is derived or the user's own
     * (task-526). Without the mark, an auto pitch looks exactly like a hand-set
     * one, so the +/- buttons would silently end auto-pitching on what looks like
     * a first nudge on an already-chosen number.
     */
    _syncMapSpacingButton() {
        const el = document.getElementById('map-spacing');
        if (el) {
            el.textContent = this._mapSpacingAuto
                ? `${this._mapSpacingValue()} auto`
                : String(this._mapSpacingValue());
        }
        const autoBtn = document.getElementById('map-spacing-auto');
        if (autoBtn) {
            autoBtn.setAttribute('aria-pressed', this._mapSpacingAuto ? 'true' : 'false');
            autoBtn.title = this._mapSpacingAuto
                ? 'Pitch is derived from the painted extent. Click to fix it and use − / +.'
                : 'Pitch is yours. Click to derive it from the painted extent again.';
        }
        // A compact map has no names on it, so say why rather than leaving the
        // user to wonder why their rooms turned into dots.
        const note = document.getElementById('map-compact-note');
        if (note) {
            const _gmLayout = GraphLayoutEngine as unknown as GraphManagerLayoutEngine;
            const compact = this._cardinalLayout === true
                && typeof GraphLayoutEngine !== 'undefined'
                && _gmLayout.mapCompact && _gmLayout.mapCompact();
            note.hidden = !compact;
        }
    }

    _buildTooltip(nodeData: any) { return GraphNetwork.buildTooltip(nodeData); }

    _onClick(params: any) { return GraphEventHandlers.onClick(params); }

    _onContext(params: any) { return GraphEventHandlers.onContext(params); }

    // --- Context Menu ---

    _showContextMenu(event: MouseEvent, nodeData: any, nodeId: string) {
        this._contextTarget = { nodeData, nodeId, nodeType: nodeData?.type };
        const name = nodeData?.name || nodeId;
        const menu = document.getElementById('context-menu');
        if (!menu) return;

        const typeIcons: Record<string, string> = { area: '🏠', item: '📦', way: '🚪', character: '🧍' };
        const typeIcon = typeIcons[nodeData?.type] || '📄';
        const items = [graphManagerHtmlTag`<div class="context-menu-header" style="padding:6px 12px;font-size:10px;color:var(--text-dim);border-bottom:1px solid var(--border-light);text-transform:uppercase;letter-spacing:0.5px;">${typeIcon} ${nodeData?.type || 'node'} · ${name}</div>`];
        items.push(graphManagerHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('inspect')}>🔍 Inspect</div>`);

        if (nodeData?.type === 'area') {
            items.push(graphManagerHtmlTag`<div class="context-menu-separator"></div>`);
            items.push(graphManagerHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('add_item')}>📦 Add Item to Area</div>`);
            items.push(graphManagerHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('move_character')}>🧍 Move Character Here</div>`);
            items.push(graphManagerHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('create_character')}>✨ Create Character Here</div>`);
            items.push(graphManagerHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('create_trigger')}>⚡ Add Trigger Edge</div>`);
            items.push(graphManagerHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('save_area_to_lib')}>📚 Save to Library</div>`);
            items.push(graphManagerHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('save_structure')}>📦 Save as Structure…</div>`);
        } else if (nodeData?.type === 'item') {
            items.push(graphManagerHtmlTag`<div class="context-menu-separator"></div>`);
            items.push(graphManagerHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('edit')}>✏️ Edit Item</div>`);
            items.push(graphManagerHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('save_to_lib')}>📚 Save to Library</div>`);
            items.push(graphManagerHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('create_trigger')}>⚡ Add Trigger Edge</div>`);
            items.push(graphManagerHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('delete')}>🗑️ Delete Item</div>`);
        } else if (nodeData?.type === 'way') {
            items.push(graphManagerHtmlTag`<div class="context-menu-separator"></div>`);
            items.push(graphManagerHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('edit')}>✏️ Edit Way</div>`);
            items.push(graphManagerHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('create_trigger')}>⚡ Add Trigger Edge</div>`);
            items.push(graphManagerHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('delete')}>🗑️ Delete Way</div>`);
        } else if (nodeData?.type === 'character') {
            items.push(graphManagerHtmlTag`<div class="context-menu-separator"></div>`);
            items.push(graphManagerHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('edit')}>✏️ Edit Character</div>`);
            items.push(graphManagerHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('create_trigger')}>⚡ Add Trigger Edge</div>`);
        }

        items.push(graphManagerHtmlTag`<div class="context-menu-separator"></div>`);
        items.push(graphManagerHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('duplicate')}>📋 Duplicate</div>`);
        items.push(graphManagerHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('lib_search')}>📚 Show in Library</div>`);

        window.Lit.render(graphManagerHtmlTag`${items}`, menu);
        menu.style.display = 'block';
        menu.style.left = event.clientX + 'px';
        menu.style.top = event.clientY + 'px';
        setTimeout(() => document.addEventListener('click', () => menu.style.display = 'none', { once: true }), 0);
    }

    _ctxAction(action: string) {
        const menu = document.getElementById('context-menu');
        if (menu) menu.style.display = 'none';
        const t = this._contextTarget;
        if (!t) return;
        const name = t.nodeData?.name || t.nodeId;

        switch (action) {
            case 'inspect': {
                if (t.isEdge) {
                    // Inspect edge - shows edge inspector
                    if (t.edgeData) {
                        this._showEdgeInspector(t.edgeData);
                    }
                } else {
                    VW?.inspector?.showNode(t.nodeId);
                }
                break;
            }
            case 'add_item': VW?.itemLib?.openForRoom(name); break;
            case 'edit': VW?.inspector?.showNode(t.nodeId); break;
            case 'save_to_lib': VW?.itemLib?.saveWorldItem(t.nodeId); break;
            case 'save_area_to_lib': {
                const areaName = t.nodeData?.name || name;
                // @ts-ignore -- libraryBrowser is a bare lexical `const` in
                // library-browser.ts (no window assignment), so the name must stay
                // bare. types/globals.d.ts should declare it.
                if (libraryBrowser?.saveAreaByName) libraryBrowser.saveAreaByName(areaName);
                else events.log('Library browser not ready.', 'error-msg');
                break;
            }
            case 'save_structure': {
                if (VW?.structures?.openSaveDialog) VW.structures.openSaveDialog(t.nodeId, name);
                else events.log('Structure module not loaded.', 'error-msg');
                break;
            }
            case 'delete': this._deleteNode(t.nodeId!); break;
            case 'delete_edge': {
                if (t.edgeData) {
                    // Extract raw type from worldState.graph.edges, not the display label
                    let rawType = t.edgeData.type || 'connection';
                    if (worldState.graph && worldState.graph.edges && (!rawType || rawType === 'connection')) {
                        const matched = worldState.graph.edges.find((e: any) =>
                            e.source === t.edgeData.from && e.target === t.edgeData.to
                        );
                        if (matched) rawType = matched.type || 'connection';
                    }
                    this._deleteEdge(t.edgeData.from, t.edgeData.to, rawType);
                }
                break;
            }
            case 'duplicate': this._duplicateNode(t.nodeId!); break;
            case 'move_character': {
                const _gmApi = ApiClient as unknown as GraphManagerApi;
                const players = Object.keys(worldState.players || {});
                if (players.length === 0) {
                    events.log('No characters to move.', 'system-msg');
                    return;
                }
                const charName = prompt(`Move which character to "${name}"?\nAvailable: ${players.join(', ')}`, players[0]);
                if (!charName || !players.includes(charName)) {
                    events.log('Character not found.', 'error-msg');
                    return;
                }
                _gmApi.movePlayerToRoom(charName, name).then(res => {
                    if (res.error) { events.log(`Move failed: ${res.error}`, 'error-msg'); return; }
                    events.log(`Moved "${charName}" to "${name}"`, 'system-msg');
                    worldState.fetch();
                });
                break;
            }
            case 'create_character': {
                const _gmApi = ApiClient as unknown as GraphManagerApi;
                const newName = prompt('Enter name for new character:', 'New Character');
                if (!newName?.trim()) return;
                _gmApi.createCharacter(newName.trim()).then(res => {
                    if (res.error) { events.log(`Create failed: ${res.error}`, 'error-msg'); return; }
                    events.log(`Created "${newName}"`, 'system-msg');
                    // Move to area
                    _gmApi.movePlayerToRoom(newName.trim(), name).then(() => {
                        worldState.fetch();
                    });
                });
                break;
            }
            case 'create_trigger':
                this._createSpecialEdge(t.nodeId!, 'triggers', '⚡');
                break;
            case 'lib_search':
                VW?.itemLib?.open();
                if (t.nodeType === 'item') {
                    const search = document.getElementById('item-lib-search') as HTMLInputElement | null;
                    if (search) search.value = name;
                    // main.ts declares this as a top-level function, so it is a
                    // real window property. Kept as a hard call (not `?.()`) so a
                    // missing module still fails loudly, as the bare name did.
                    (window as unknown as { filterItemLibrary: () => void }).filterItemLibrary();
                }
                break;
        }
    }

    async _deleteNode(nodeId: string) { return (window as unknown as { GraphNodeOps: GraphManagerNodeOps }).GraphNodeOps.deleteNode(nodeId); }

    async _deleteEdge(source: string, target: string, edgeType: string) { return (window as unknown as { GraphNodeOps: GraphManagerNodeOps }).GraphNodeOps.deleteEdge(source, target, edgeType); }

    async _duplicateNode(nodeId: string) {
        const _gmApi = ApiClient as unknown as GraphManagerApi;
        const nodeData = this.nodes.get(nodeId);
        const nodeType = nodeData?.type;
        // Triggers are never duplicated via the graph — the inspector editor
        // is where new triggers are made.
        if (nodeType === 'logic_trigger') {
            events.log('Triggers are never duplicated from the graph — edit the node and use the inspector to create a new trigger.', 'error-msg');
            return null;
        }
        if (!['area', 'item', 'way', 'character'].includes(nodeType!)) {
            events.log(`Cannot duplicate nodes of type "${nodeType}".`, 'error-msg');
            return null;
        }
        // ONE atomic write on the backend (POST /api/graph/duplicate). It
        // snapshots the original, clones the node + children + triggers in a
        // single request, and pushes an undo snapshot before mutating. Children
        // are items attached TO the node (salt --[on]--> table / top --[equipped]--> char);
        // parents are always shared, never cloned.
        try {
            let includeChildren = true;
            const hasChildren = await this._dupNodeHasChildren(nodeId, nodeType!);
            if (hasChildren) {
                includeChildren = await (window as unknown as { GraphNodeOps: GraphManagerNodeOps }).GraphNodeOps._showDuplicateChoiceModal(
                    `Also duplicate the items attached to <strong>${nodeData?.name || nodeId}</strong>?<br><br>No = just the ${nodeType} and its triggers.`,
                    'Duplicate Items?'
                );
            }
            const res = await _gmApi.duplicateNode(nodeId, includeChildren);
            if (res && res.id) {
                const extra = res.cloned! > 1 ? ` (${res.cloned} nodes)` : '';
                events.log(`Duplicated "${nodeData?.name || nodeId}" as "${res.name}"${extra}`, 'system-msg');
                worldState.fetch();
                return res;
            }
            events.log(`Duplicate failed: ${res?.error || 'unknown error'}`, 'error-msg');
            return null;
        } catch (err) {
            events.log(`Duplicate failed: ${(err as Error).message}`, 'error-msg');
            return null;
        }
    }

    /** Does this node have item children attached to it (edges pointing TO it)? */
    async _dupNodeHasChildren(nodeId: string, nodeType: string) {
        const edges: GraphManagerEdgeData[] = this._graphEdgesArr || worldState.graph?.edges || [];
        const CHILD_TYPES = new Set(['in', 'on', 'under', 'behind', 'beside', 'at', 'carrying', 'equipped', 'known']);
        for (const e of edges) {
            if (e.target !== nodeId) continue;
            if (!CHILD_TYPES.has(e.type || 'connection')) continue;
            const src = this.nodes.get(e.source);
            if (src && src.type === 'item') return true;
        }
        return false;
    }

    async _createSpecialEdge(fromNodeId: string, edgeType: string, emoji: string) { return (window as unknown as { GraphNodeOps: GraphManagerNodeOps }).GraphNodeOps.createSpecialEdge(fromNodeId, edgeType, emoji); }

    async _createEdgeWithType(fromNodeId: string) {
        const _gmApi = ApiClient as unknown as GraphManagerApi;
        const _gmEdgeTypes = window.EdgeTypes as GraphManagerEdgeTypes;
        const fromNode = this.nodes.get(fromNodeId);
        if (!fromNode) return;

        const edgeTypes = _gmEdgeTypes.validForSource(fromNode.type);
        const typeList = edgeTypes.map((t, i) => {
            const cfg = _gmEdgeTypes.getConfig(t);
            return `${i + 1}. ${cfg.icon} ${cfg.label} — ${cfg.desc}`;
        }).join('\n');

        const typeChoice = prompt(`Select edge type for "${fromNode.name}":\n\n${typeList}\n\nEnter number (1-${edgeTypes.length}):`, '1');
        if (!typeChoice) return;

        const typeIdx = parseInt(typeChoice) - 1;
        if (typeIdx < 0 || typeIdx >= edgeTypes.length) { events.log('Invalid edge type.', 'error-msg'); return; }
        const edgeType = edgeTypes[typeIdx];

        const cfg = _gmEdgeTypes.getConfig(edgeType);
        const validTargets = _gmEdgeTypes.validTargets(edgeType);

        const allNodes = Array.from(this.nodes.entries());
        const candidates = allNodes.filter(([id, nd]) => id !== fromNodeId && validTargets.includes(nd.type!));
        if (candidates.length === 0) {
            events.log(`No suitable target nodes for ${cfg.label} edge.`, 'error-msg');
            return;
        }

        const candidateList = candidates.map(([id, nd], i) => `${i + 1}. ${nd.name || id} (${nd.type})`).join('\n');
        const targetChoice = prompt(`${cfg.icon} Which target for "${fromNode.name}"?\n\n${candidateList}\n\nEnter number or node ID:`, '1');
        if (!targetChoice) return;

        let targetId = null;
        const num = parseInt(targetChoice);
        if (num > 0 && num <= candidates.length) targetId = candidates[num - 1][0];
        else if (this.nodes.has(targetChoice.trim())) targetId = targetChoice.trim();

        if (!targetId || targetId === fromNodeId) { events.log('Invalid target selected.', 'error-msg'); return; }

        const description = prompt(`Enter a description for this ${cfg.label} edge (optional):`, '');
        const properties: Record<string, unknown> = {};
        if (description) properties.description = description;

        const result = await _gmApi.createEdge(fromNodeId, targetId, edgeType, properties);
        if (result.status === 'success') {
            events.log(`${cfg.icon} Created ${cfg.label} edge: ${fromNode.name} → ${this.nodes.get(targetId)?.name || targetId}`, 'system-msg');
            worldState.fetch();
        } else {
            events.log(`Failed to create edge: ${result.error || 'unknown error'}`, 'error-msg');
        }
    }

    startPendingConnection(fromNodeId: string, edgeType: string) {
        const fromNode = this.nodes.get(fromNodeId);
        if (!fromNode) return;
        this._pendingConnection = { fromNodeId, edgeType, fromName: (fromNode.name || fromNode.id)! };
        events.log(`🖱️ Click a target node to connect "${this._pendingConnection.fromName}" → ... (Esc to cancel)`, 'system-msg');
        VW?.ui?.setStatus(`Connect: click target for "${this._pendingConnection.fromName}" (Esc to cancel)`, 'info');
    }

    cancelPendingConnection() {
        if (!this._pendingConnection) return;
        const name = this._pendingConnection.fromName;
        this._pendingConnection = null;
        events.log(`Cancelled connecting "${name}".`, 'system-msg');
        VW?.ui?.setStatus('Idle.', 'info');
    }

    async _completePendingConnection(targetNodeId: string) {
        const _gmApi = ApiClient as unknown as GraphManagerApi;
        const _gmEdgeTypes = window.EdgeTypes as GraphManagerEdgeTypes;
        const pending = this._pendingConnection;
        if (!pending) return;
        const { fromNodeId, edgeType, fromName } = pending;
        this._pendingConnection = null;
        VW?.ui?.setStatus('Idle.', 'info');

        const toNode = this.nodes.get(targetNodeId);
        if (!toNode) { events.log('Target node not found.', 'error-msg'); return; }
        if (targetNodeId === fromNodeId) { events.log('Cannot connect node to itself.', 'error-msg'); return; }

        const cfg = _gmEdgeTypes.getConfig(edgeType);
        const result = await _gmApi.createEdge(fromNodeId, targetNodeId, edgeType, {});
        if (result.status === 'success') {
            events.log(`${cfg.icon} Connected ${cfg.label}: ${fromName} → ${toNode.name || targetNodeId}`, 'system-msg');
            worldState.fetch();
        } else {
            events.log(`Failed to connect: ${result.error || 'unknown error'}`, 'error-msg');
        }
    }

    async _saveEdgeProperty(fromId: string, toId: string, key: string, rawValue: string) {
        const _gmApi = ApiClient as unknown as GraphManagerApi;
        let value: any = rawValue;
        try { value = JSON.parse(rawValue); } catch (e) { /* keep string */ }
        const res = await _gmApi.updateEdge(fromId, toId, { old_type: 'connection', properties: { [key]: value } });
        if (res.status === 'success') {
            events.log('Edge property updated.', 'system-msg');
            worldState.fetch();
        } else {
            events.log('Failed to update property: ' + (res.error || 'unknown'), 'error-msg');
        }
    }

    async _deleteEdgeProperty(fromId: string, toId: string, key: string) {
        const res = await (ApiClient as unknown as GraphManagerApi).updateEdge(fromId, toId, { old_type: 'connection', properties: { [key]: null } });
        if (res.status === 'success') {
            events.log('Edge property removed.', 'system-msg');
            worldState.fetch();
        } else {
            events.log('Failed to remove property: ' + (res.error || 'unknown'), 'error-msg');
        }
    }

    async _addEdgeProperty(fromId: string, toId: string, rawType: string) {
        const _gmApi = ApiClient as unknown as GraphManagerApi;
        const key = prompt('Property name:');
        if (!key || !key.trim()) return;
        const rawValue = prompt('Property value (JSON or plain text):', '');
        if (rawValue === null) return;
        let value: any = rawValue;
        try { value = JSON.parse(rawValue); } catch (e) { /* keep string */ }
        const res = await _gmApi.updateEdge(fromId, toId, { old_type: rawType, properties: { [key.trim()]: value } });
        if (res.status === 'success') {
            events.log('Edge property added.', 'system-msg');
            worldState.fetch();
        } else {
            events.log('Failed to add property: ' + (res.error || 'unknown'), 'error-msg');
        }
    }

    _onAddNode(data: any, callback: any) { return GraphEventHandlers.onAddNode(data, callback); }

    _onAddEdge(data: any, callback: any) { return GraphEventHandlers.onAddEdge(data, callback); }

    _showEdgeContextMenu(event: MouseEvent, edgeData: any) {
        this._contextTarget = { edgeData, isEdge: true };
        const menu = document.getElementById('context-menu');
        if (!menu) return;

        window.Lit.render(graphManagerHtmlTag`
            <div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('inspect')}>🔍 Inspect Edge</div>
            <div class="context-menu-separator"></div>
            <div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('delete_edge')} style="color:var(--red);">🗑️ Delete Edge</div>`, menu);
        menu.style.display = 'block';
        menu.style.left = event.clientX + 'px';
        menu.style.top = event.clientY + 'px';
        setTimeout(() => document.addEventListener('click', () => menu.style.display = 'none', { once: true }), 0);
    }

    _showEdgeInspector(edge: any) {
        // EdgeInspector (lit) is the owner of the inspector panel. This fallback
        // only exists if edge-inspector.js failed to load; it renders a static
        // template through InspectorPanel so lit's part tracking stays intact.
        if (window.EdgeInspector?.renderEdgeInspector) {
            window.EdgeInspector.renderEdgeInspector(edge);
        } else if (window.InspectorPanel?.render) {
            const fromNode = this.nodes.get(edge.from);
            const toNode = this.nodes.get(edge.to);
            const fromName = fromNode?.name || edge.from;
            const toName = toNode?.name || edge.to;
            const fromId = fromNode?.id || edge.from;
            const toId = toNode?.id || edge.to;
            const htmlTag = (strings: TemplateStringsArray, ...values: unknown[]) => window.Lit.html(strings, ...values);
            window.InspectorPanel.render(htmlTag`
                <div class="inspector-header">
                    <span class="inspector-type-badge" style="background:var(--accent)">🔗 Edge</span>
                    <h2 style="margin:0;font-size:14px;"><span style="color:var(--accent)">${fromName} → ${toName}</span></h2>
                    <button class="btn btn-sm btn-ghost" @click=${() => hideInspectorPanel()}>✕</button>
                </div>
                <div class="inspector-section">
                    <div class="relationship-item" style="cursor:pointer;" @click=${() => VW.inspector.showNode(fromId)}>🧩 ${fromName} <span style="color:var(--text-muted);font-size:10px;">(${fromNode?.type})</span></div>
                    <div class="relationship-item" style="cursor:pointer;" @click=${() => VW.inspector.showNode(toId)}>→ 🧩 ${toName} <span style="color:var(--text-muted);font-size:10px;">(${toNode?.type})</span></div>
                </div>
                <div class="inspector-section">
                    <label style="font-size:10px;font-weight:600;">Edge Type</label>
                    <div style="font-size:11px;color:var(--text-muted);">${edge.type || 'connection'}</div>
                </div>
                <div style="padding:0 16px 8px;display:flex;gap:6px;">
                    <button class="btn btn-sm btn-red" @click=${() => graphManager._deleteEdge(fromId, toId, edge.type || 'connection')}>🗑️ Delete Edge</button>
                </div>`);
        }
    }

    async _changeEdgeType(source: string, target: string, oldType: string, newType: string) {
        const _gmApi = ApiClient as unknown as GraphManagerApi;
        const _gmEdgeTypes = window.EdgeTypes as GraphManagerEdgeTypes;
        if (oldType === newType) return;
        const cfg = _gmEdgeTypes.getConfig(newType);
        // Carry the existing edge's properties so a type change doesn't drop
        // direction/cardinal/description data on the way.
        const worldEdge = worldState.graph?.edges?.find((e: any) =>
            e.source === source && e.target === target && e.type === oldType
        );
        const properties = worldEdge?.properties || {};
        const result = await _gmApi.updateEdge(source, target, { old_type: oldType, new_type: newType, properties });
        if (result.status === 'success') {
            events.log(`${cfg.icon} Changed edge type: ${oldType} → ${newType}`, 'system-msg');
            worldState.fetch();
        } else {
            events.log(`Failed to change edge type: ${result.error || 'unknown error'}`, 'error-msg');
        }
    }

    _toggleTree(id: string) {
        const el = document.getElementById(id);
        if (!el) return;
        const toggle = el.parentElement!.querySelector('.vtree-toggle');
        if (el.style.display === 'none') {
            el.style.display = 'block';
            if (toggle) toggle.textContent = '▼';
        } else {
            el.style.display = 'none';
            if (toggle) toggle.textContent = '▶';
        }
    }

    _toggleDesc(id: string) {
        const short = document.getElementById(id + '-d');
        const full = document.getElementById(id + '-df');
        // `!` is erased at emit. The null check is deliberately AFTER this line
        // in HEAD, so the ordering (and any throw it produces) is preserved.
        const more = short!.parentElement!.querySelector('.vtree-more');
        if (!short || !full) return;
        if (short.style.display === 'none') {
            short.style.display = 'inline';
            full.style.display = 'none';
            if (more) more.textContent = 'more';
        } else {
            short.style.display = 'none';
            full.style.display = 'inline';
            if (more) more.textContent = 'less';
        }
    }

    _selectRoom(name: string) {
        if (VW?.inspector) VW.inspector.showNode(name);
        const node = worldState.getNodeByIdentifier(name);
        if (node) this.focusNode(node.id);
    }

    /**
     * Move the camera to a graph node: switch back to graph view if an
     * overlay is active, highlight the node, and animate the viewport to it.
     * Falls back to a fit-all view when the node isn't in the loaded graph.
     *
     * @param {string} nodeId - The graph node id to focus on
     */
    focusNode(nodeId: string) {
        if (!this.network) return;
        if (this._viewMode !== 'graph') this.setViewMode('graph');
        if (this.nodes.has(nodeId)) {
            this.network.selectNodes([nodeId]);
            this.network.focus(nodeId, {
                scale: 1.15,
                animation: { duration: 500, easingFunction: 'easeInOutQuad' }
            });
        } else {
            this.fitView();
        }
    }

    /**
     * Open the inspector for a node AND move the camera to it.
     * Used by outline items and ways.
     *
     * @param {string} nodeId - The graph node id to inspect and focus on
     */
    showNodeAndFocus(nodeId: string) {
        if (VW?.inspector) VW.inspector.showNode(nodeId);
        this.focusNode(nodeId);
    }

    _escHtml(str: string) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    togglePhysics() {
        graphManager._physicsEnabled = !graphManager._physicsEnabled;
        GraphNetwork.applyModePhysics(graphManager._physicsEnabled);
        if (window.GraphToolbar) GraphToolbar.syncAll();
        graphManager._saveGraphConfigKey('graph.physics_enabled', graphManager._physicsEnabled);
    }

    /** Free physics layout <-> vis hierarchical levels (task-485). */
    toggleLayoutMode() { return GraphNetwork.toggleLayoutMode(); }

    /** True when the hierarchical (level) layout owns node positions. */
    _levelsMode() {
        try {
            return (typeof config !== 'undefined' && config && config.graphLayoutMode) === 'levels';
        } catch (err) {
            return false;
        }
    }

    fitView() { return GraphNetwork.fitView(); }

    /** Floating zoom-cluster actions (bottom-right of the canvas). */
    zoomIn() { this._zoomBy(1.25); }

    zoomOut() { this._zoomBy(0.8); }

    _zoomBy(factor: number) {
        if (!this.network) return;
        const scale = this.network.getScale() * factor;
        this.network.moveTo({ scale, animation: { duration: 200, easingFunction: 'easeInOutQuad' } });
    }

    toggleLegend() { return GraphNetwork.toggleLegend(); }

    toggleTriggers() { return GraphNetwork.toggleTriggers(); }

    toggleItems() {
        GraphNetwork.toggleItems();
        if (window.GraphToolbar) GraphToolbar.syncAll();
        graphManager._saveGraphConfigKey('graph.show_items', graphManager._showItems);
    }

    toggleInhabitedAreas() {
        GraphNetwork.toggleInhabitedAreas();
        if (window.GraphToolbar) GraphToolbar.syncAll();
        graphManager._saveGraphConfigKey('graph.show_only_inhabited', graphManager._showOnlyInhabitedAreas);
    }

    toggleTagPanel() { return GraphNetwork.toggleTagPanel(); }

    toggleEdgeLabels() {
        this._showEdgeLabels = !this._showEdgeLabels;
        if (window.GraphToolbar) GraphToolbar.syncToggles();
        this._lastSig = '';
        this.loadGraphData();
    }

    /**
     * Toggle node-name labels. Independent of the zoom LOD: off forces every
     * name hidden, on restores them (the LOD still hides them at overview zoom
     * for a very dense map until you zoom in).
     */
    toggleNodeLabels() {
        this._showNodeLabels = !this._showNodeLabels;
        try { localStorage.setItem('vw_graphNodeLabels', this._showNodeLabels ? '1' : '0'); } catch (e) { /* ignore */ }
        if (window.GraphToolbar) GraphToolbar.syncToggles();
        GraphNetwork.applyNodeLabelVisibility(true);
    }

    setEdgeLabelSize(delta: number) {
        this._edgeLabelSize = Math.max(4, Math.min(20, this._edgeLabelSize + delta));
        const out = document.getElementById('edge-label-size');
        if (out) out.textContent = String(this._edgeLabelSize);
        this._lastSig = '';
        this.loadGraphData();
    }

    // --- Storey (floor) filter ---

    /**
     * Set the active storey filter and reload the graph. 'all' shows every storey.
     * Also refreshes the picker dropdown from the areas seen in the graph.
     *
     * `floor` is a **storey index** (0 ground, 1 up, -1 down, unbounded), so the
     * filter is kept as a number; the dropdown's string values are parsed back.
     * @param {string|number} floor - 'all' or a storey number
     */
    setFloorFilter(floor: string | number | null | undefined) {
        const isAll = (String(floor) === 'all' || floor === null || floor === undefined);
        const parsed = Number(floor);
        this._floorFilter = isAll || !Number.isFinite(parsed) ? 'all' : String(Math.round(parsed));
        const sel = document.getElementById('floor-filter') as HTMLSelectElement | null;
        if (sel) sel.value = this._floorFilter;
        GraphNetwork.applyVisibility();
    }

    /**
     * Refresh the storey picker from the area nodes in the graph.
     * Composes with the current filter (keeps the selected storey if still present).
     *
     * A non-numeric `floor` is a save from before the ground material moved to
     * `properties.surface`; `GraphProjector.floorOf` reads it as ground, so the
     * picker offers a storey the filter can actually match.
     */
    refreshFloorOptions() {
        const floors = new Set<string>();
        this.nodes.forEach((nodeData) => {
            if (nodeData.type !== 'area') return;
            if ((nodeData.properties || {}).floor === undefined) return;
            floors.add(String(GraphProjector.floorOf(nodeData)));
        });
        this._floorOptions = ['all', ...Array.from(floors).sort((a, b) => Number(a) - Number(b))];
        // Reflect current filter; default to 'all' if the selected storey no longer exists
        const sel = document.getElementById('floor-filter') as HTMLSelectElement | null;
        if (!sel) return;
        const current = this._floorOptions.includes(this._floorFilter) ? this._floorFilter : 'all';
        this._floorFilter = current;
        window.Lit.render(graphManagerHtmlTag`${this._floorOptions.map(f =>
            graphManagerHtmlTag`<option value=${f} ?selected=${f === current}>${f === 'all' ? 'All storeys' : _floorOptionLabel(Number(f))}</option>`)}`, sel);
        sel.value = current;
    }

    /**
     * True when an active floor filter is set.
     */
    floorFilterActive() {
        return this._floorFilter !== 'all';
    }

    // --- View mode switching: Graph / Map / Overlays ---

    /**
     * Switch the *overlay* (the recolouring view) — the layout is a separate
     * axis, owned by the segmented control (see activeLayout/toggleCardinalLayout).
     * `graph` clears the overlay; `light` | `heat` | `sound` | `trigger` |
     * `cardinal` apply one. Nothing here renames a control: the toolbar repaints
     * itself from state via GraphToolbar.syncAll().
     *
     * @param {'graph'|'light'|'heat'|'sound'|'trigger'|'cardinal'} mode
     */
    setViewMode(mode: string) {
        this._viewMode = mode;
        const container = document.getElementById('graph-container')!;
        container.querySelectorAll('.view-overlay').forEach(el => el.remove());
        const visEl = container.querySelector<HTMLElement>('.vis-network') || container.querySelector<HTMLElement>('canvas');

        const overlayModes = ['light', 'heat', 'sound', 'trigger', 'cardinal'];

        if (mode === 'graph') {
            if (visEl) visEl.style.display = '';
            // Disengage cardinal layout first so loadGraphData doesn't re-apply it
            if (this._cardinalLayout) {
                this._cardinalLayout = false;
                this._physicsEnabled = true;
                this._persistCardinalLayout();   // bug-510: the choice is real
            }
            if (this.network) {
                GraphNetwork.applyOverlay('structural');
                GraphNetwork.applyModePhysics(this._physicsEnabled && !this._levelsMode());
                this.fitView();
            }
        } else if (overlayModes.includes(mode)) {
            if (visEl) visEl.style.display = '';
            if (this.network) {
                GraphNetwork.applyModePhysics(false);
                GraphNetwork.applyOverlay(mode);
            }
        }
        if (window.GraphToolbar) GraphToolbar.syncAll();
    }

    _renderCurrentView() {
        if (this._viewMode === 'graph') return;
        const container = document.getElementById('graph-container')!;
        container.querySelectorAll('.view-overlay').forEach(el => el.remove());
        const overlayModes = ['light', 'heat', 'sound', 'trigger', 'cardinal'];
        if (!overlayModes.includes(this._viewMode)) return;
        const visEl = container.querySelector<HTMLElement>('.vis-network') || container.querySelector<HTMLElement>('canvas');
        if (visEl) visEl.style.display = '';
        if (this.network) GraphNetwork.applyOverlay(this._viewMode);
    }

    _buildLegendHTML() { return GraphNetwork.buildLegendHTML(); }

    _applyFilter(query: string) { GraphNetwork.applyFilter(query); }

    filterNodes(query: string) { GraphNetwork.filterNodes(query); }
}

// Singleton. Assigned straight onto window with no top-level const: types/
// globals.d.ts already declares `graphManager` as an ambient const, and a second
// one here would be TS2451. Bare `graphManager` reads inside this file resolve to
// that ambient binding, which this line populates at runtime exactly as the
// `const graphManager = new GraphManager(); window.graphManager = graphManager;`
// pair it replaces did.
(window as unknown as { graphManager: GraphManagerImpl }).graphManager = new GraphManagerImpl();

// Compatibility aliases for inline onclick handlers in HTML
function hideInspectorPanel() { VW?.inspector?.hide(); }
function selectAgent(name: string) {
    // @ts-ignore -- `ui` is a bare lexical const in ui-controller.ts (no window
    // assignment), so the name must stay bare. types/globals.d.ts should declare it.
    ui.selectAgent(name);
}
