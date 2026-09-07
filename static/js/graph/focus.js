/**
 * GraphFocus — search reveal + camera/physics focus for the graph (task-394).
 *
 * Search is a *focus* operation: it surfaces matching nodes (see
 * GraphProjector) and, once the query settles, frames the match cluster and
 * gives the freshly-unhidden nodes a bounded physics kick so they visibly pull
 * together instead of sitting at stale coordinates.
 *
 * task-394 adds three behaviors:
 *   1. FREEZE — while a query is active, nodes that are hidden (non-matches)
 *      are excluded from the physics simulation (physics:false) so they stop
 *      repelling the matches and wedging them in place.
 *   2. CLUSTER — on activate, the match cluster is gathered into a compact
 *      grid at the viewport center (with the prior positions + viewport saved),
 *      so "find all food" shows a tight, scannable group. Clearing the search
 *      restores the exact prior layout.
 *   3. KEEP-IN-PLACE — an optional mode that still freezes the hidden set but
 *      does NOT move the matches, for spatial reasoning ("where does food
 *      live?").
 *
 * @module GraphFocus
 */
window.GraphFocus = {

    /** Debounce timer handle (module state, not graphManager). */
    _searchDebounceTimer: undefined,

    /** True once the active query has clustered results (positions saved). */
    _clusterActive: false,

    /** Saved node positions ({ id: {x,y} }) for the cluster frame before move. */
    _savedPositions: null,

    /** Saved viewport ({ position, scale }) before moving the camera. */
    _savedView: null,

    /** Nodes we parked (physics:false) this session, to restore on clear. */
    _parked: null,

    /**
     * Sets the search query and instantly reveals matches (cheap — only toggles
     * node/edge hidden flags). The frame-fit + physics kick are deferred to
     * settleSearch(). Clearing the query restores any parked physics + cluster
     * layout from the previous search session.
     *
     * @param {string} query - raw search input
     */
    applyFilter(query) {
        const q = (query || '').toLowerCase().trim();
        const wasActive = !!graphManager._searchQuery;
        graphManager._searchQuery = q;
        GraphNetwork.applyVisibility();
        if (wasActive && !q) {
            GraphFocus._restoreAfterSearch();
        }
    },

    /**
     * Called when a search should "settle": park the hidden set, then (unless
     * keep-in-place) cluster the matches toward the viewport center, then run a
     * bounded physics kick. Runs once the query is stable (on Enter/blur/
     * debounce), not on every keystroke.
     */
    settleSearch() {
        const q = graphManager._searchQuery;
        if (!q) return;
        GraphFocus._parkHiddenSet();
        const keep = graphManager._searchKeepInPlace ?? GraphFocus.isKeepInPlace();
        if (keep) {
            GraphFocus._fitToSearchMatches();
        } else {
            GraphFocus._clusterResults();
        }
    },

    /** Whether keep-in-place mode is on (persists across reloads). */
    isKeepInPlace() {
        return localStorage.getItem('graph-search-keep-in-place') === '1';
    },

    /**
     * Toggle keep-in-place. Turning ON during an active cluster un-clusters
     * (restores positions) but keeps the hidden set frozen; turning OFF during
     * an active search re-clusters immediately.
     * @param {boolean} on
     */
    setKeepInPlace(on) {
        localStorage.setItem('graph-search-keep-in-place', on ? '1' : '0');
        graphManager._searchKeepInPlace = on;
        const q = graphManager._searchQuery;
        if (!q) return;
        if (on && GraphFocus._clusterActive) {
            GraphFocus._unCluster();
        } else if (!on) {
            GraphFocus._clusterResults();
        }
    },

    /** The currently-visible node ids (matches + visible one-hop neighbours). */
    _visibleSet() {
        return GraphNetwork._computeVisibleNodeIds();
    },

    /**
     * Exclude every currently-hidden node from the physics sim so it stops
     * repelling the visible results. Newly-revealed nodes are restored to their
     * normal physics. Diff-based so per-keystroke runs stay cheap.
     */
    _parkHiddenSet() {
        if (!graphManager.network) return;
        const nodesDs = graphManager.network.body?.data?.nodes;
        if (!nodesDs) return;
        const visible = GraphFocus._visibleSet();
        GraphFocus._parked = GraphFocus._parked || {};
        const updates = [];
        nodesDs.forEach((node) => {
            const hidden = !visible.has(node.id);
            if (hidden) {
                if (node.physics !== false) { updates.push({ id: node.id, physics: false }); GraphFocus._parked[node.id] = true; }
            } else if (!hidden && node.physics === false && GraphFocus._parked[node.id]) {
                updates.push({ id: node.id, physics: GraphFocus._nodeDefaultPhysics(node.id) });
                GraphFocus._parked[node.id] = false;
            }
        });
        if (updates.length) nodesDs.update(updates);
    },

    _nodeDefaultPhysics(id) {
        const nd = (graphManager._graphNodesObj || {})[id];
        return nd ? (nd.properties?.central_gravity_enabled !== false) : true;
    },

    /**
     * Restore the pre-search layout & any parked physics after a query clears.
     * Idempotent / safe to call with nothing pending.
     */
    _restoreAfterSearch() {
        GraphFocus._unCluster();
        GraphFocus._restoreParkedPhysics();
        GraphFocus._clusterActive = false;
        GraphFocus._parked = null;
        GraphFocus._savedPositions = null;
        GraphFocus._savedView = null;
    },

    _restoreParkedPhysics() {
        if (!graphManager.network || !GraphFocus._parked) return;
        const nodesDs = graphManager.network.body?.data?.nodes;
        if (!nodesDs) return;
        const updates = [];
        for (const id in GraphFocus._parked) {
            if (GraphFocus._parked[id]) {
                const nd = (graphManager._graphNodesObj || {})[id];
                const phys = nd ? (nd.properties?.central_gravity_enabled !== false) : true;
                const n = nodesDs.get(id);
                if (n && n.physics !== phys) updates.push({ id, physics: phys });
            }
        }
        if (updates.length) nodesDs.update(updates);
    },

    /**
     * Gather the visible match cluster into a compact grid at the viewport
     * center. Saves prior positions + viewport so clearing the search restores
     * the exact layout the user had.
     */
    _clusterResults() {
        if (!graphManager.network) return;
        const network = graphManager.network;
        const visible = GraphFocus._visibleSet();
        const ids = [...visible];
        if (ids.length === 0) { GraphFocus._fitToSearchMatches(); return; }

        // First fit so the visible set is what we center on.
        const ds = network.body?.data?.nodes;
        let present = ids;
        if (ds) present = ids.filter(id => ds.get(id) !== null);
        if (!present.length) { GraphFocus._fitToSearchMatches(); return; }

        // Save current layout (only for nodes we're about to move).
        try { GraphFocus._savedPositions = network.getPositions(present); } catch (e) { GraphFocus._savedPositions = null; }
        try { GraphFocus._savedView = { position: network.getViewPosition(), scale: network.getScale() }; } catch (e) { GraphFocus._savedView = null; }

        const view = network.getViewPosition();
        const scale = network.getScale() || 1;
        const cols = Math.min(6, Math.max(1, Math.ceil(Math.sqrt(present.length))));
        const spacing = 150 / scale;
        present.forEach((id, i) => {
            const col = i % cols;
            const row = Math.floor(i / cols);
            const x = view.x + (col - (cols - 1) / 2) * spacing;
            const y = view.y + (row - (Math.ceil(present.length / cols) - 1) / 2) * spacing;
            network.moveNode(id, x, y);
        });

        network.fit({ nodes: present, animation: true, maxZoomLevel: 1.2 });
        GraphFocus._clusterActive = true;
        GraphFocus._kickClusterPhysics();
    },

    /** Undo a cluster: return moved nodes to their saved positions + viewport. */
    _unCluster() {
        if (!graphManager.network || !GraphFocus._clusterActive) return;
        const network = graphManager.network;
        if (GraphFocus._savedPositions) {
            const moves = [];
            for (const id in GraphFocus._savedPositions) {
                const p = GraphFocus._savedPositions[id];
                moves.push({ id, x: p.x, y: p.y });
            }
            for (const m of moves) network.moveNode(m.id, m.x, m.y);
        }
        if (GraphFocus._savedView) {
            try { network.moveTo({ position: GraphFocus._savedView.position, scale: GraphFocus._savedView.scale, animation: true }); } catch (e) { /* ignore */ }
        }
        // Keep physics parking until restore runs (parking is cleared in the
        // same clear flow); if called mid-search (keep-in-place toggle on),
        // parking stays so ghosts don't push.
        GraphFocus._clusterActive = false;
        GraphFocus._savedPositions = null;
        GraphFocus._savedView = null;
    },

    /**
     * Fits the camera to the current search-match cluster so the revealed
     * results are brought into view (keep-in-place path — no repositioning).
     */
    _fitToSearchMatches() {
        const q = graphManager._searchQuery;
        if (!q) return;
        if (!graphManager.network) return;

        const nodesObj = graphManager._graphNodesObj || {};
        const edgesArr = graphManager._graphEdgesArr || [];
        const matches = new Set();
        for (const id in nodesObj) {
            if (GraphProjector.nodeMatchesQuery(nodesObj[id], q)) {
                matches.add(id);
            }
        }
        if (matches.size === 0) return;
        // Include one-hop neighbours so the connected cluster is framed.
        const frame = new Set(matches);
        for (const e of edgesArr) {
            if (matches.has(e.source)) frame.add(e.target);
            if (matches.has(e.target)) frame.add(e.source);
        }
        const frameIds = [...frame];
        const ds = graphManager.network.body?.data?.nodes;
        if (ds) {
            const present = frameIds.filter(id => ds.get(id) !== null);
            if (present.length > 0) {
                graphManager.network.fit({ nodes: present, animation: true, maxZoomLevel: 1.4 });
            }
        }
        GraphFocus._kickClusterPhysics();
    },

    /**
     * Gives the physics solver a short kick so just-revealed nodes (which were
     * parked while hidden and excluded from forces) re-join the simulation and
     * pull toward their connections. Bounded so it settles fast. Restores the
     * user's physics on/off state afterwards.
     */
    _kickClusterPhysics() {
        if (!graphManager.network) return;
        const nodes = graphManager.network.body?.data?.nodes;
        if (!nodes) return;
        const wasEnabled = graphManager._physicsEnabled !== false;
        graphManager.network.setOptions({ physics: { enabled: true } });
        try {
            graphManager.network.stabilize(60);
        } catch (e) { /* ignore */ }
        if (!wasEnabled) graphManager.network.setOptions({ physics: { enabled: false } });
    },

    /**
     * Public entry point for filtering graph nodes by name/tag. Sets the query
     * and debounces the camera fit + physics kick so they only run once typing
     * stops (~450ms idle) or on Enter/blur.
     *
     * @param {string} query - raw search input
     */
    filterNodes(query) {
        GraphFocus.applyFilter(query);

        if (typeof GraphFocus._searchDebounceTimer !== 'undefined') {
            clearTimeout(GraphFocus._searchDebounceTimer);
        }
        const q = graphManager._searchQuery;
        if (q) {
            GraphFocus._searchDebounceTimer = setTimeout(() => {
                GraphFocus.settleSearch();
            }, 450);
        } else {
            clearTimeout(GraphFocus._searchDebounceTimer);
            GraphFocus._searchDebounceTimer = undefined;
        }
    },

    /** Sync the toolbar checkbox (and manager flag) with persisted state. */
    init() {
        const on = GraphFocus.isKeepInPlace();
        graphManager._searchKeepInPlace = on;
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => GraphFocus._applyCheckbox(on));
        } else {
            GraphFocus._applyCheckbox(on);
        }
    },

    _applyCheckbox(on) {
        const cb = document.getElementById('search-keep-in-place');
        if (!cb) return;
        cb.checked = !!on;
        if (cb.parentElement) cb.parentElement.classList.toggle('active', !!on);
    }
};

if (typeof document !== 'undefined') GraphFocus.init();