/**
 * GraphFocus — search reveal + camera/physics focus for the graph.
 *
 * Extracted from the network-manager monolith. Search is a *focus* operation:
 * it surfaces matching nodes (see GraphProjector) and, once the query settles,
 * frames the match cluster and gives the freshly-unhidden nodes a bounded
 * physics kick so they visibly pull together instead of sitting at stale
 * coordinates. Debounced so typing doesn't spam the graph with fit/stabilize.
 *
 * @module GraphFocus
 */
window.GraphFocus = {

    /** Debounce timer handle (module state, not graphManager). */
    _searchDebounceTimer: undefined,

    /**
     * Sets the search query and instantly reveals matches (cheap — only toggles
     * node/edge hidden flags). The frame-fit + physics kick are deferred to
     * settleSearch(), called when the user pauses/confirms.
     *
     * @param {string} query - raw search input
     */
    applyFilter(query) {
        graphManager._searchQuery = (query || '').toLowerCase().trim();
        GraphNetwork.applyVisibility();
    },

    /**
     * Called when a search should "settle": run the camera fit + bounded physics
     * kick once the query is stable (on Enter/blur/debounce), not on every
     * keystroke. This is what actually pulls revealed nodes together.
     */
    settleSearch() {
        const q = graphManager._searchQuery;
        if (!q) return;
        GraphFocus._fitToSearchMatches();
    },

    /**
     * Fits the camera to the current search-match cluster so the revealed
     * results are brought into view. Only acts when a query is active.
     */
    _fitToSearchMatches() {
        const q = graphManager._searchQuery;
        if (!q) return;
        if (!graphManager.network) return;

        const nodesObj = graphManager._graphNodesObj || {};
        const edgesArr = graphManager._graphEdgesArr || [];
        const matches = new Set();
        for (const id in nodesObj) {
            if (String(nodesObj[id].name || id || '').toLowerCase().includes(q)) {
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
        // Only nodes currently present in the dataset should be fitted.
        const ds = graphManager.network.body?.data?.nodes;
        if (ds) {
            const present = frameIds.filter(id => ds.get(id) !== null);
            if (present.length > 0) {
                graphManager.network.fit({ nodes: present, animation: true, maxZoomLevel: 1.4 });
            }
        }

        // Hidden nodes were parked (excluded from the solver), so revealing them
        // won't re-simulate on its own. Nudge the solver on just the visible
        // cluster so the revealed nodes actually pull together toward their
        // connections again — bounded so it settles quickly without reorganizing
        // the whole world.
        GraphFocus._kickClusterPhysics();
    },

    /**
     * Gives the physics solver a short kick so just-revealed nodes (which were
     * parked while hidden and excluded from forces) re-join the simulation and
     * pull toward their connections. Uses a bounded iteration count so it settles
     * fast and without restructuring the whole graph. Because reveal only ran on
     * the visible search cluster, only those nodes participate. Restores physics
     * on/off state afterwards.
     */
    _kickClusterPhysics() {
        if (!graphManager.network) return;
        const nodes = graphManager.network.body?.data?.nodes;
        if (!nodes) return;
        const wasEnabled = graphManager._physicsEnabled !== false;
        graphManager.network.setOptions({ physics: { enabled: true } });
        try {
            graphManager.network.stabilize(80);
        } catch (e) { /* ignore */ }
        if (!wasEnabled) graphManager.network.setOptions({ physics: { enabled: false } });
    },

    /**
     * Public entry point for filtering graph nodes by name. Sets the query and
     * debounces the camera fit + physics kick so they only run once typing stops
     * (~450ms idle) or on Enter/blur.
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
    }
};