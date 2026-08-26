/**
 * GraphProjector — the pure "what should be visible" model for the graph.
 *
 * Kept deliberately free of vis.js calls and live-state mutation. Given the
 * graph data and the current UI view-state, it answers one question: which
 * node ids are visible right now, and (via applyVisibility) syncs a vis.js
 * dataset's `hidden` flags to match. Extracted from the network-manager
 * monolith so the filtering logic is unit-testable and toggles never need a
 * full rebuild.
 *
 * @module GraphProjector
 */
window.GraphProjector = {

    /**
     * Read the current UI view-state off the GraphManager. Centralized so the
     * pure compute functions can take a plain view-state bag instead of
     * reaching into the global.
     *
     * @returns {{
     *   searchQuery: string,
     *   revealedAreaIds: Set<string>,
     *   revealedItemIds: Map<string, Set<string>>,
     *   showOnlyInhabitedAreas: boolean,
     *   floorFilterActive: boolean,
     *   floorFilter: (string|number),
     *   showTriggers: boolean,
     *   showItems: boolean,
     * }}
     */
    _viewState() {
        return {
            searchQuery: (graphManager._searchQuery || '').toLowerCase().trim(),
            revealedAreaIds: new Set(graphManager._revealedAreaIds || []),
            revealedItemIds: graphManager._revealedItemIds || new Map(),
            showOnlyInhabitedAreas: !!graphManager._showOnlyInhabitedAreas,
            floorFilterActive: !!(graphManager.floorFilterActive && graphManager.floorFilterActive()),
            floorFilter: graphManager._floorFilter,
            showTriggers: !!graphManager._showTriggers,
            showItems: !!graphManager._showItems
        };
    },

    /**
     * Compute the set of visible node ids from raw graph data + view state.
     *
     * Search mode is special: it surfaces every matching node PLUS its direct
     * neighbours (one hop over any edge), so results come into view with their
     * connecting edges — overriding spatial/inhabited/item/trigger filters so a
     * match is never buried. When no query is active, visibility derives from
     * the floor filter, inhabited-areas mode, and the items/triggers toggles,
     * with manually-revealed areas/items always kept visible.
     *
     * @param {object} nodesObj - node id → raw node data
     * @param {Array}  edgesArr - raw edge objects
     * @param {object} vs        - view state bag (from _viewState)
     * @returns {Set<string>} visible node ids
     */
    computeVisibleNodeIds(nodesObj, edgesArr, state) {
        const query = state.searchQuery;

        // ── SEARCH MODE ────────────────────────────────────────────────
        if (query) {
            const matchIds = new Set();
            for (const id in nodesObj) {
                if (String(nodesObj[id].name || id || '').toLowerCase().includes(query)) {
                    matchIds.add(id);
                }
            }
            if (matchIds.size === 0) return new Set();
            const visible = new Set(matchIds);
            for (const e of edgesArr) {
                if (matchIds.has(e.source)) visible.add(e.target);
                if (matchIds.has(e.target)) visible.add(e.source);
            }
            return visible;
        }

        const revealedIds = new Set(state.revealedAreaIds);
        for (const childSet of state.revealedItemIds.values()) {
            for (const cid of childSet) revealedIds.add(cid);
        }

        // Inhabited-areas mode: an area is visible if it has a character (an
        // 'in' edge from a character) or is manually revealed; everything else
        // is visible only if it sits one hop from a visible area.
        let linkedIds = null;
        if (state.showOnlyInhabitedAreas) {
            const seeded = new Set(state.revealedAreaIds);
            for (const e of edgesArr) {
                if (e.type !== 'in') continue;
                if (nodesObj[e.source]?.type === 'character') seeded.add(e.target);
            }
            linkedIds = new Set(seeded);
            for (const e of edgesArr) {
                if (seeded.has(e.source)) linkedIds.add(e.target);
                if (seeded.has(e.target)) linkedIds.add(e.source);
            }
        }

        // Floor filter: only areas on the active floor, plus their direct links.
        let floorAreas = null;
        let floorChildren = null;
        if (state.floorFilterActive) {
            const targetFloor = String(state.floorFilter);
            floorAreas = new Set();
            floorChildren = new Set();
            for (const id in nodesObj) {
                if (nodesObj[id].type === 'area' && String(nodesObj[id].properties?.floor) === targetFloor) {
                    floorAreas.add(id);
                }
            }
            for (const e of edgesArr) {
                if (floorAreas.has(e.source) && !floorAreas.has(e.target)) floorChildren.add(e.target);
                if (floorAreas.has(e.target) && !floorAreas.has(e.source)) floorChildren.add(e.source);
            }
        }

        const visible = new Set();
        for (const id in nodesObj) {
            const nd = nodesObj[id];
            if (floorAreas && !(nd.type === 'area' ? floorAreas.has(id) : floorChildren.has(id))) continue;
            if (linkedIds && !linkedIds.has(id)) continue;
            if (nd.type === 'logic_trigger' && !state.showTriggers) continue;
            if (nd.type === 'item' && !state.showItems && !revealedIds.has(id)) continue;
            visible.add(id);
        }

        // Revealed nodes stay visible even if a spatial filter would hide them.
        for (const rid of revealedIds) visible.add(rid);
        return visible;
    },

    /**
     * Is a single edge visible given the visible node set? Edges inherit
     * visibility from their endpoints — an edge is visible only when BOTH
     * endpoints are visible.
     *
     * @param {Set<string>} visibleIds - from computeVisibleNodeIds
     * @param {object} edge            - a vis.js edge ({from, to})
     * @returns {boolean}
     */
    edgeVisible(visibleIds, edge) {
        return (visibleIds.has(edge.from) && visibleIds.has(edge.to));
    },

    /**
     * Sync a live vis.js dataset's hidden flags to match the projection.
     * Diffs BEFORE updating so unchanged nodes/edges are left untouched —
     * this is the cheap path that makes toggles not reset zoom/physics.
     *
     * @param {object} network     - live vis.Network
     * @param {Set<string>} visibleIds - visible node ids
     */
    applyVisibility(network, visibleIds) {
        if (!network) return;
        const nodesDs = network.body?.data?.nodes;
        const edgesDs = network.body?.data?.edges;
        if (!nodesDs || !edgesDs) return;

        const nodeUpdates = [];
        nodesDs.forEach((node) => {
            const shouldHide = !visibleIds.has(node.id);
            if (node.hidden !== shouldHide) nodeUpdates.push({ id: node.id, hidden: shouldHide });
        });
        if (nodeUpdates.length > 0) nodesDs.update(nodeUpdates);

        const edgeUpdates = [];
        edgesDs.forEach((edge) => {
            const shouldHide = !(visibleIds.has(edge.from) && visibleIds.has(edge.to));
            if (edge.hidden !== shouldHide) edgeUpdates.push({ id: edge.id, hidden: shouldHide });
        });
        if (edgeUpdates.length > 0) edgesDs.update(edgeUpdates);
    }
};