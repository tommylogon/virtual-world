/**
 * GraphNetwork — vis.js network setup and management for the graph
 * Handles vis.Network initialization, options building, data loading,
 * tooltip building, physics toggling, legend rendering, and node filtering.
 * Extracted from graph-manager.js. References the global graphManager singleton.
 *
 * @module GraphNetwork
 */
// Lazy lit-html tag: window.Lit is only available at call time (deferred module
// bootstrap), not at parse time. Unique per file so top-level consts never collide.
const networkManagerHtmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

window.GraphNetwork = {
    /**
     * Initializes the vis.js Network on the graph container element.
     * Creates the legend overlay, sets up click/context event handlers,
     * and loads the initial graph data.
     */
    async init() {
        const container = document.getElementById('graph-container');
        if (!container) return;

        const options = GraphNetwork.buildOptions();
        graphManager.network = new vis.Network(container, { nodes: [], edges: [] }, options);

        // Create legend overlay (after vis.js so it doesn't get cleared)
        graphManager._legendEl = document.createElement('div');
        graphManager._legendEl.className = 'graph-legend';
        window.Lit.render(networkManagerHtmlTag`${window.Lit.unsafeHTML(GraphNetwork.buildLegendHTML())}`, graphManager._legendEl);
        graphManager._legendVisible = false;
        graphManager._legendEl.style.display = 'none';
        container.appendChild(graphManager._legendEl);

        // Create tag filter overlay (colored tag indicators + click-to-filter)
        graphManager._tagPanelEl = document.createElement('div');
        graphManager._tagPanelEl.className = 'graph-legend graph-tag-panel';
        window.Lit.render(networkManagerHtmlTag`<div class="graph-legend-inner"><div style="font-size:10px;font-weight:600;color:var(--text-dim);margin-bottom:4px;">🏷️ Tags</div></div>`, graphManager._tagPanelEl);
        graphManager._tagPanelVisible = false;
        graphManager._tagPanelEl.style.display = 'none';
        graphManager._tagFilter = null;
        graphManager._tagLibrary = null;
        container.appendChild(graphManager._tagPanelEl);
        GraphNetwork.ensureTagLibrary();

        graphManager.network.on("click", (params) => GraphEventHandlers.onClick(params));
        graphManager.network.on("oncontext", (params) => GraphEventHandlers.onContext(params));
        GraphNetwork._bindEdgeHoverTooltips();

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && graphManager._pendingConnection) {
                graphManager.cancelPendingConnection();
            }
        });

        await GraphNetwork.loadGraphData();
        setTimeout(() => GraphNetwork.fitView(), 100);
    },

    /**
     * Builds and returns the vis.js options object with physics, interaction,
     * manipulation, and group styling configuration.
     *
     * @returns {Object} vis.js Network options
     */
    buildOptions() {
        const cfg = window.config || {};
        const solver = cfg.graphSolver || 'forceAtlas2Based';
        const physicsBase = solver === 'barnesHut'
            ? { barnesHut: { gravitationalConstant: cfg.graphGravitationalConstant ?? -3000, centralGravity: 0.3, springLength: cfg.graphSpringLength ?? 120, springConstant: cfg.graphSpringConstant ?? 0.04, damping: cfg.graphDamping ?? 0.09 } }
            : { forceAtlas2Based: { gravitationalConstant: cfg.graphGravitationalConstant ?? -40, centralGravity: 0.005, springLength: cfg.graphSpringLength ?? 100, springConstant: cfg.graphSpringConstant ?? 0.02, damping: cfg.graphDamping ?? 0.4 } };
        return {
            physics: {
                enabled: true, solver,
                ...physicsBase,
                stabilization: { iterations: 100 }
            },
            interaction: { hover: true, tooltipDelay: 200, multiselect: false },
            edges: {
                font: { multi: 'html' },
                arrows: cfg.graphArrows !== false ? { to: { enabled: true, scaleFactor: 0.5 } } : { to: { enabled: false } },
                width: cfg.graphEdgeWidth || 1
            },
            layout: { improvedLayout: cfg.graphImprovedLayout === true },
            manipulation: {
                enabled: true, initiallyActive: false,
                addNode: (data, callback) => GraphEventHandlers.onAddNode(data, callback),
                addEdge: (data, callback) => GraphEventHandlers.onAddEdge(data, callback)
            },
            groups: {
                area:      { color: { background: '#2d333b', border: '#58a6ff' }, shape: 'box', font: { color: '#c9d1d9', size: 14 }, borderWidth: 2, margin: { top: 21, bottom: 21, left: 27, right: 27 } },
                item:      { color: { background: '#3d2e1a', border: '#e3b341' }, shape: 'diamond', font: { color: '#e3b341', size: 12 }, size: 18, borderWidth: 1 },
                way:      { color: { background: '#1a3a2a', border: '#4ec9b0' }, shape: 'triangle', font: { color: '#4ec9b0' }, size: 14, borderWidth: 1 },
                character: { color: { background: '#2a1a3d', border: '#bc8cff' }, shape: 'ellipse', font: { color: '#bc8cff', size: 14 }, size: 24, borderWidth: 2 }
            }
        };
    },

    applyGraphSettings() {
        if (!graphManager.network) return;
        graphManager._lastSig = '';
        graphManager.network.setOptions(GraphNetwork.buildOptions());
        GraphNetwork.loadGraphData();
    },

    /**
     * Fetches node and edge data from the API and updates the vis.js network.
     * Includes a signature-based deduplication to skip redundant reloads,
     * preserves node positions when possible, and applies cardinal layout
     * or search filters as needed.
     */
    async loadGraphData() {
        if (!graphManager.network) return;
        try {
            const nodesObj = await ApiClient.getGraphNodes();
            const edgesArr = await ApiClient.getGraphEdges();

            // Skip reload if graph structure hasn't changed (avoids jitter on tick updates)
            const nodeSig = Object.entries(nodesObj)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([id, nodeData]) => `${id}:${nodeData.type}:${nodeData.properties?.current_state || ''}:${nodeData.properties?.central_gravity_enabled !== false}:${nodeData.properties?.image || ''}`)
                .join('|');
            const edgeSig = edgesArr
                .map(edgeObj => `${edgeObj.source}:${edgeObj.target}:${edgeObj.type}:${edgeObj.properties?.description || ''}`)
                .sort()
                .join('|');
            const sig = `${nodeSig}|${edgeSig}`;
            if (sig === graphManager._lastSig) return;
            graphManager._lastSig = sig;

            // Preserve node positions before reload
            let savedPositions = {};
            try { savedPositions = graphManager.network.getPositions(); } catch (err) { /* ignore */ }

            graphManager.nodes.clear();
            graphManager._revealedItemIds = new Map();
            graphManager._revealedAreaIds.clear();
            const visNodes = [];
            const visEdges = [];
            graphManager._graphNodesObj = nodesObj;
            graphManager._graphEdgesArr = edgesArr;
            graphManager._edgeTooltipHtml = {};

            // Visibility (floor filter, inhabited-areas, items/triggers toggles,
            // revealed areas/items, search) is applied in place later by
            // applyVisibility(), so toggles never need a full setData() rebuild
            // (which was causing zoom/pan loss + jitter). Build every node here.

            for (const id in nodesObj) {
                const nodeData = nodesObj[id];
                graphManager.nodes.set(id, nodeData);
                visNodes.push(this.buildNodeConfig(nodeData));
            }

            const renderedConnectionPairs = new Set();
            for (const edgeObj of edgesArr) {
                const rawType = edgeObj.type || 'connection';
                const edgeType = EdgeTypes.resolve(rawType);
                const style = edgeObj.properties?.style || {};
                const typeCfg = EdgeTypes.getConfig(edgeType);
                let defaultColor = typeCfg.color;
                let defaultDashes = edgeType === 'unlocks';

                let edgeLabel = '';
                if (graphManager._showEdgeLabels) {
                    edgeLabel = edgeType;
                } else if (edgeType === 'unlocks') {
                    edgeLabel = edgeObj.properties?.description || 'unlocks';
                }

                // Collapse bidirectional connection pairs into a single visual edge
                if (edgeType === 'connection') {
                    const pairKey = [edgeObj.source, edgeObj.target].sort().join('|');
                    if (renderedConnectionPairs.has(pairKey)) continue;
                    renderedConnectionPairs.add(pairKey);
                    const otherEdges = edgesArr.filter(e =>
                        e.type === 'connection' &&
                        ((e.source === edgeObj.target && e.target === edgeObj.source) ||
                         (e.source === edgeObj.source && e.target === edgeObj.target))
                    );
                    if (otherEdges.length > 1) {
                        const dirs = otherEdges.map(e => e.properties?.direction).filter(Boolean);
                        edgeLabel = (graphManager._showEdgeLabels ? '↔ ' : '') + dirs.join(' ↔ ');
                    }
                }

                if (typeof WayAuthoring !== 'undefined') {
                    const tip = WayAuthoring.buildEdgeTooltipForVis(edgeObj.source, edgeObj.target, nodesObj, edgesArr);
                    if (tip) {
                        graphManager._edgeTooltipHtml[`${edgeObj.source}|${edgeObj.target}`] = tip.html;
                    }
                }

                // Check if the way node has a per-edge length override
                let edgeLength = undefined;
                if (edgeType === 'connection') {
                    const targetNode = nodesObj[edgeObj.target];
                    const sourceNode = nodesObj[edgeObj.source];
                    const wayNode = targetNode?.type === 'way' ? targetNode : sourceNode?.type === 'way' ? sourceNode : null;
                    if (wayNode) {
                        const len = wayNode.properties?.edge_length;
                        if (len && len > 0) edgeLength = len;
                    }
                }
                visEdges.push({
                    from: edgeObj.source, to: edgeObj.target,
                    type: edgeType,
                    label: edgeLabel,
                    length: edgeLength,
                    arrows: edgeType === 'connection' ? 'from,to' : (style.arrows || 'to'),
                    dashes: style.dashes !== undefined ? style.dashes : defaultDashes,
                    color: { color: style.color || defaultColor, highlight: '#4ec9b0' },
                    font: { color: style.color || defaultColor, size: graphManager._edgeLabelSize || 8, align: 'horizontal', strokeWidth: 2, strokeColor: '#0d1117' },
                    width: style.width || 1
                });
            }
            // Disable physics during data swap to avoid jitter
            const wasPhysics = graphManager._physicsEnabled;
            graphManager.network.setOptions({ physics: { enabled: false } });
            graphManager.network.setData({ nodes: visNodes, edges: visEdges });
            // Restore positions only for nodes that still exist
            const newNodeIds = new Set(visNodes.map(nodeConfig => nodeConfig.id));
            for (const [id, pos] of Object.entries(savedPositions)) {
                if (!newNodeIds.has(id)) continue;
                graphManager.network.moveNode(id, pos.x, pos.y);
            }
            // Apply cardinal-based area layout if enabled
            if (graphManager._cardinalLayout && worldState.areas) {
                GraphLayoutEngine.applyCardinalLayout(nodesObj);
            }

            if (wasPhysics) graphManager.network.setOptions({ physics: { enabled: true } });

            // Apply visibility in place (floor filter, inhabited areas, items,
            // triggers, revealed nodes, and active search). Reuses the dataset we
            // just built so no second rebuild happens here.
            GraphNetwork.applyVisibility();

            // Attach rich tippy tooltips to nodes and edges
            GraphNetwork._attachTippyTooltips();

            // Re-apply trait + tag label decorations (tag library may load async)
            GraphNetwork._applyNodeLabelDecorations();

            // Refresh floor picker options from areas now present
            graphManager.refreshFloorOptions();

            // Re-render overlay views (map/outline) if active
            if (graphManager._viewMode !== 'graph') graphManager._renderCurrentView();
        } catch (err) {
            console.warn("Graph API unavailable:", err);
        }
    },

    /**
     * Computes the set of node ids that should be visible right now based on
     * all active graph filters. See GraphProjector.computeVisibleNodeIds.
     *
     * @returns {Set<string>} ids of currently-visible nodes
     */
    _computeVisibleNodeIds() {
        return GraphProjector.computeVisibleNodeIds(
            graphManager._graphNodesObj || {},
            graphManager._graphEdgesArr || [],
            GraphProjector._viewState()
        );
    },

    /**
     * Applies the current visibility state to the live vis.js dataset in place.
     * Hides nodes via the `hidden` flag and hides edges whose endpoints are not
     * both visible. Called by toggles and filters instead of a full rebuild, so
     * zoom/pan and physics survive — the core fix for the laggy reloads.
     */
    applyVisibility() {
        const visibleIds = GraphNetwork._computeVisibleNodeIds();
        GraphProjector.applyVisibility(graphManager.network, visibleIds);
    },

    /**
     * Builds a plain-text tooltip string for a graph node.
     * Shows different information depending on node type (area, item, way, character).
     *
     * @param {Object} nodeData - The node data object
     * @returns {string} Tooltip text
     */
    /** @deprecated Use GraphTooltips.buildTooltip */
    buildTooltip(nodeData) {
        return GraphTooltips.buildTooltip(nodeData);
    },

    /** @deprecated Use GraphTooltips._escHtml */
    _escHtml(s) {
        return GraphTooltips._escHtml(s);
    },

    /** @deprecated Use GraphTooltips.buildTooltipHtml */
    buildTooltipHtml(nodeData) {
        return GraphTooltips.buildTooltipHtml(nodeData);
    },

    /** @deprecated Use GraphTooltips.bindEdgeHoverTooltips */
    _bindEdgeHoverTooltips() {
        return GraphTooltips.bindEdgeHoverTooltips();
    },

    /** @deprecated Use GraphTooltips.findGraphEdge */
    _findGraphEdge(fromId, toId) {
        return GraphTooltips.findGraphEdge(fromId, toId);
    },

    /** @deprecated Use GraphTooltips.attachNodeTooltips */
    _attachTippyTooltips() {
        return GraphTooltips.attachNodeTooltips();
    },

    /**
     * Fits the network view to show all nodes with animation.
     */
    fitView() {
        graphManager.network.fit({ animation: true });
    },

    /**
     * Toggles physics simulation on/off for the vis.js network.
     * Updates the physics button text accordingly.
     */
    togglePhysics() {
        graphManager._physicsEnabled = !graphManager._physicsEnabled;
        graphManager.network.setOptions({ physics: { enabled: graphManager._physicsEnabled } });
        const btn = document.getElementById('btn-physics');
        if (btn) btn.textContent = graphManager._physicsEnabled ? '⏸ Physics' : '▶ Physics';
    },

    /**
     * Toggles the graph legend overlay visibility.
     */
    toggleLegend() {
        if (!graphManager._legendEl) return;
        graphManager._legendVisible = !graphManager._legendVisible;
        graphManager._legendEl.style.display = graphManager._legendVisible ? 'block' : 'none';
    },

    toggleTriggers() {
        graphManager._showTriggers = !graphManager._showTriggers;
        const btn = document.getElementById('btn-triggers');
        if (btn) btn.classList.toggle('active', graphManager._showTriggers);
        GraphNetwork.applyVisibility();
    },

    /**
     * Toggle node image thumbnails on the graph. Persists the preference so it
     * survives reloads. Requires node `image` properties (see the inspector
     * image widget / upload endpoint); nodes without an image keep their
     * normal shape.
     */
    toggleImages() {
        graphManager._showImages = !graphManager._showImages;
        try {
            localStorage.setItem('vw_graphShowImages', graphManager._showImages ? '1' : '0');
        } catch (e) { /* ignore */ }
        const btn = document.getElementById('btn-images');
        if (btn) btn.classList.toggle('active', graphManager._showImages);
        graphManager._lastSig = '';
        GraphNetwork.loadGraphData();
    },

    toggleItems() {
        graphManager._showItems = !graphManager._showItems;
        const btn = document.getElementById('btn-items');
        if (btn) btn.classList.toggle('active', graphManager._showItems);
        if (graphManager._showItems) {
            this.hideRevealedItems();
        }
        GraphNetwork.applyVisibility();
    },

    toggleInhabitedAreas() {
        graphManager._showOnlyInhabitedAreas = !graphManager._showOnlyInhabitedAreas;
        const btn = document.getElementById('btn-inhabited');
        if (btn) btn.classList.toggle('active', graphManager._showOnlyInhabitedAreas);
        if (!graphManager._showOnlyInhabitedAreas) {
            graphManager._revealedAreaIds.clear();
        }
        GraphNetwork.applyVisibility();
    },

    revealAreasForWay(wayId) {
        if (!graphManager._showOnlyInhabitedAreas) return;
        const edgesArr = graphManager._graphEdgesArr || [];
        const connectedAreas = new Set();
        for (const edgeObj of edgesArr) {
            if (edgeObj.type !== 'connection') continue;
            if (edgeObj.source === wayId) connectedAreas.add(edgeObj.target);
            if (edgeObj.target === wayId) connectedAreas.add(edgeObj.source);
        }
        let changed = false;
        for (const areaId of connectedAreas) {
            if (!graphManager._revealedAreaIds.has(areaId)) {
                graphManager._revealedAreaIds.add(areaId);
                changed = true;
            }
        }
        if (changed) {
            GraphNetwork.applyVisibility();
        }
    },

    hideRevealedAreas() {
        if (graphManager._revealedAreaIds.size === 0) return;
        graphManager._revealedAreaIds.clear();
        GraphNetwork.applyVisibility();
    },

    /**
     * Builds a vis.js node config object for a node from its raw graph data.
     * Centralized so reveal-on-click can reuse the same label/tooltip/color
     * styling the main load path uses.
     *
     * @param {Object} nodeData - raw node data from the graph
     * @returns {Object} vis.js node configuration
     */
    buildNodeConfig(nodeData) {
        const nodeConfig = {
            id: nodeData.id,
            label: typeof NodeBadges !== 'undefined'
                ? NodeBadges.formatLabel(nodeData, GraphNetwork._tagMetaFor(nodeData))
                : `${nodeData.name || nodeData.id}`,
            group: nodeData.type,
            title: GraphNetwork.buildTooltip(nodeData),
            // vis-network's central gravity is global. A node excluded from
            // physics stays out of that pull while the rest keeps simulating.
            physics: nodeData.properties?.central_gravity_enabled !== false
        };

        // Way nodes: color by state
        if (nodeData.type === 'way') {
            const state = (nodeData.properties?.current_state || 'closed').toLowerCase();
            if (state === 'open') {
                nodeConfig.color = { background: '#1a3a2a', border: '#3fb950' };
            } else if (state === 'closed') {
                nodeConfig.color = { background: '#2d3a1a', border: '#e3b341' };
            } else if (state === 'locked') {
                nodeConfig.color = { background: '#3a1a1a', border: '#f85149' };
            } else if (state === 'hidden') {
                nodeConfig.color = { background: '#1a1a2a', border: '#6e7681' };
            } else if (state === 'blocked') {
                nodeConfig.color = { background: '#3a2a1a', border: '#f0883e' };
            } else if (state === 'broken') {
                nodeConfig.color = { background: '#3a1a1a', border: '#f85149' };
            }
            if (nodeData.properties?.one_way) {
                nodeConfig.color = nodeConfig.color || { background: '#1a3a2a', border: '#4ec9b0' };
                nodeConfig.color.border = '#58a6ff';
            }
        }

        // Item nodes: color by state
        if (nodeData.type === 'item') {
            const state = (nodeData.properties?.current_state || 'normal').toLowerCase();
            if (state === 'lit') {
                nodeConfig.color = { background: '#3d2a0a', border: '#f0883e' };
            } else if (state === 'broken') {
                nodeConfig.color = { background: '#2d2d2d', border: '#6e7681' };
            } else if (state === 'depleted') {
                nodeConfig.color = { background: '#2d251a', border: '#8b7355' };
            }
        }

        // Node image mode (task-249): when enabled and the node carries an
        // `image` property, render it as a circular thumbnail instead of the
        // plain colored shape. The label stays so names remain readable; the
        // rich tooltip still carries the full details. Nodes without an image
        // keep their normal group shape/color.
        if (graphManager._showImages && nodeData.properties?.image) {
            nodeConfig.shape = 'circularImage';
            nodeConfig.image = nodeData.properties.image;
            nodeConfig.size = { area: 45, character: 28, item: 24, way: 22 }[nodeData.type] || 24;
            nodeConfig.borderWidth = 2;
        }

        return nodeConfig;
    },

    /**
     * Reveals the items directly connected to a node, used when items are
     * hidden. Clicking an area shows its items, a character shows carried +
     * equipped items, and an item shows its container contents. Siblings stay
     * open when drilling into a child; switching to a different parent clears
     * the previous parent's revealed items.
     *
     * @param {string} nodeId - id of the clicked node
     */
    revealItemsForNode(nodeId) {
        if (graphManager._showItems) return; // items already visible
        const edgesArr = graphManager._graphEdgesArr || [];
        const revealed = new Set();
        for (const edgeObj of edgesArr) {
            const type = EdgeTypes.resolve(edgeObj.type || 'connection');
            if (type === 'connection' || type === 'unlocks' || type === 'triggers' || type === 'requires') continue;
            if (edgeObj.target !== nodeId) continue;
            const itemNodeData = graphManager.nodes.get(edgeObj.source);
            if (!itemNodeData || itemNodeData.type !== 'item') continue;
            revealed.add(edgeObj.source);
        }
        if (revealed.size === 0) return;

        // If nodeId is already a revealed item we're drilling into a child;
        // otherwise this is a new parent branch and we clear the previous set.
        let isDrillingIntoChild = false;
        for (const childSet of graphManager._revealedItemIds.values()) {
            if (childSet.has(nodeId)) {
                isDrillingIntoChild = true;
                break;
            }
        }
        if (!isDrillingIntoChild) {
            this.hideRevealedItems();
        }

        // Only track items not already revealed under some parent. The nodes
        // themselves are already in the dataset (built for the whole graph);
        // applyVisibility() unhides them and their edges in place.
        let added = false;
        for (const id of revealed) {
            let alreadyRevealed = false;
            for (const childSet of graphManager._revealedItemIds.values()) {
                if (childSet.has(id)) {
                    alreadyRevealed = true;
                    break;
                }
            }
            if (!alreadyRevealed) added = true;
        }
        if (added) {
            graphManager._revealedItemIds.set(nodeId, revealed);
            GraphNetwork.applyVisibility();
        }
    },

    /**
     * Removes any temporarily revealed item nodes from the network.
     */
    hideRevealedItems() {
        if (!graphManager._revealedItemIds || graphManager._revealedItemIds.size === 0) return;
        graphManager._revealedItemIds = new Map();
        GraphNetwork.applyVisibility();
    },

    /**
     * Builds and returns the HTML content for the graph legend.
     * Shows node type colors and state color mappings.
     *
     * @returns {string} Legend HTML string
     */
    buildLegendHTML() {
        return `<div class="graph-legend-inner">
            <div style="font-size:10px;font-weight:600;color:var(--text-dim);margin-bottom:4px;">📖 Legend</div>
            <div class="legend-row"><span class="legend-swatch" style="background:#2d333b;border:2px solid #58a6ff;"></span> Area</div>
            <div class="legend-row"><span class="legend-swatch legend-diamond" style="background:#3d2e1a;border:2px solid #e3b341;"></span> Item</div>
            <div class="legend-row"><span class="legend-swatch legend-triangle" style="background:#1a3a2a;border:2px solid #4ec9b0;"></span> Way</div>
            <div class="legend-row"><span class="legend-swatch legend-ellipse" style="background:#2a1a3d;border:2px solid #bc8cff;"></span> Character</div>
            <div style="font-size:9px;color:var(--text-muted);margin:4px 0 2px;">Way states:</div>
            <div class="legend-row"><span class="legend-swatch" style="background:#3a1a1a;border:2px solid #f85149;"></span><span style="font-size:9px;"> locked · broken</span></div>
            <div class="legend-row"><span class="legend-swatch" style="background:#1a3a2a;border:2px solid #3fb950;"></span><span style="font-size:9px;"> open</span></div>
            <div class="legend-row"><span class="legend-swatch" style="background:#2d3a1a;border:2px solid #e3b341;"></span><span style="font-size:9px;"> closed</span></div>
            <div class="legend-row"><span class="legend-swatch" style="background:#1a3a2a;border:2px solid #58a6ff;"></span><span style="font-size:9px;"> one-way (blue border)</span></div>
            <div class="legend-row"><span class="legend-swatch" style="background:#3a2a1a;border:2px solid #f0883e;"></span><span style="font-size:9px;"> blocked</span></div>
            <div style="font-size:9px;color:var(--text-muted);margin:4px 0 2px;">Item states:</div>
            <div class="legend-row"><span class="legend-swatch" style="background:#3d2a0a;border:2px solid #f0883e;"></span><span style="font-size:9px;"> lit</span></div>
            <div class="legend-row"><span class="legend-swatch" style="background:#2d2d2d;border:2px solid #6e7681;"></span><span style="font-size:9px;"> broken</span></div>
            <div class="legend-row"><span class="legend-swatch" style="background:#2d251a;border:2px solid #8b7355;"></span><span style="font-size:9px;"> depleted</span></div>
            ${typeof NodeBadges !== 'undefined' ? NodeBadges.legendHtml() : ''}
        </div>`;
    },

    // ──────────────────────────────────────────────
    //  TAG INDICATORS & FILTER
    // ──────────────────────────────────────────────

    /**
     * Load the tag library (GET /api/tags/search with no query returns all
     * tags) and cache it as {id: {id, name, icon, color}}. Re-applies node
     * label decorations once loaded.
     */
    ensureTagLibrary() {
        if (graphManager._tagLibrary) {
            GraphNetwork._applyNodeLabelDecorations();
            return;
        }
        fetch('/api/tags/search')
            .then(r => r.json())
            .then(tags => {
                const byId = {};
                (tags || []).forEach(t => { byId[t.id] = t; });
                graphManager._tagLibrary = byId;
                GraphNetwork._applyNodeLabelDecorations();
                if (graphManager._tagPanelVisible) GraphNetwork.renderTagPanel();
            })
            .catch(() => { graphManager._tagLibrary = {}; });
    },

    /**
     * Return {icon, color} for a node's tags, preferring library entries and
     * falling back to a deterministic hash color for unknown tags.
     */
    _tagMetaFor(nodeData) {
        const props = nodeData.properties || {};
        let tags = props.tags || [];
        if (typeof tags === 'string') tags = tags.split(',').map(t => t.trim()).filter(Boolean);
        if (!Array.isArray(tags) || tags.length === 0) return [];
        const lib = graphManager._tagLibrary || {};
        const hashColor = (s) => {
            let h = 0;
            for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
            return '#' + ((h % 0xffffff)).toString(16).padStart(6, '0');
        };
        return tags.map(tag => {
            const entry = lib[tag];
            return { tag, icon: entry?.icon || '🏷️', color: entry?.color || hashColor(tag) };
        });
    },

    /**
     * Apply trait badges + tag icons to node labels as visual indicators.
     */
    _applyNodeLabelDecorations() {
        const nodes = graphManager.network?.body?.data?.nodes;
        if (!nodes || typeof NodeBadges === 'undefined') return;
        nodes.forEach((node) => {
            const nodeData = graphManager.nodes.get(node.id);
            if (!nodeData) return;
            const label = NodeBadges.formatLabel(nodeData, GraphNetwork._tagMetaFor(nodeData));
            if (node.label !== label) nodes.update({ id: node.id, label, decoratedLabel: true });
        });
    },

    /** @deprecated Use _applyNodeLabelDecorations */
    _applyTagIconsToLabels() {
        GraphNetwork._applyNodeLabelDecorations();
    },

    /**
     * Toggle the tag filter panel visibility.
     */
    toggleTagPanel() {
        if (!graphManager._tagPanelEl) return;
        graphManager._tagPanelVisible = !graphManager._tagPanelVisible;
        graphManager._tagPanelEl.style.display = graphManager._tagPanelVisible ? 'block' : 'none';
        if (graphManager._tagPanelVisible) GraphNetwork.renderTagPanel();
    },

    /**
     * Render the tag filter panel: one clickable row per tag used in the
     * world, showing its color dot, icon, name, and node count.
     */
    renderTagPanel() {
        if (!graphManager._tagPanelEl) return;
        const lib = graphManager._tagLibrary || {};
        const counts = {};
        const metaById = {};
        graphManager.nodes.forEach((nodeData) => {
            GraphNetwork._tagMetaFor(nodeData).forEach(m => {
                if (!metaById[m.tag]) metaById[m.tag] = m;
                counts[m.tag] = (counts[m.tag] || 0) + 1;
            });
        });
        const entries = Object.keys(counts).sort();
        const inner = [networkManagerHtmlTag`<div style="font-size:10px;font-weight:600;color:var(--text-dim);margin-bottom:4px;">🏷️ Tags <span style="color:var(--text-muted);font-weight:400;">(click to filter)</span></div>`];
        if (graphManager._tagFilter) {
            inner.push(networkManagerHtmlTag`<div class="tag-filter-row tag-filter-active" data-tag="" @click=${() => GraphNetwork.setTagFilter('')}>✕ Clear filter</div>`);
        }
        entries.forEach(tag => {
            const m = metaById[tag];
            const active = graphManager._tagFilter === tag;
            inner.push(networkManagerHtmlTag`
                <div class="tag-filter-row ${active ? 'tag-filter-active' : ''}" data-tag="${tag}" @click=${() => GraphNetwork.setTagFilter(tag)}>
                    <span class="legend-swatch" style="background:${m.color};"></span> ${m.icon} ${m.name || tag} <span style="color:var(--text-muted);">(${counts[tag]})</span>
                </div>`);
        });
        window.Lit.render(networkManagerHtmlTag`<div class="graph-legend-inner">${inner}</div>`, graphManager._tagPanelEl);
    },

    /**
     * Set the active tag filter and re-apply node visibility. Empty string
     * clears the filter.
     */
    setTagFilter(tagId) {
        graphManager._tagFilter = tagId || null;
        GraphNetwork.applyTagFilter();
        GraphNetwork.renderTagPanel();
    },

    /**
     * Apply the active tag filter: matching nodes stay at full opacity with a
     * highlighted border, others are dimmed.
     */
    applyTagFilter() {
        const nodes = graphManager.network?.body?.data?.nodes;
        if (!nodes) return;
        const filter = graphManager._tagFilter;
        nodes.forEach((node) => {
            const nodeData = graphManager.nodes.get(node.id);
            let match = !filter;
            if (nodeData && filter) {
                match = GraphNetwork._tagMetaFor(nodeData).some(m => m.tag === filter);
            }
            const opacity = match ? 1.0 : 0.15;
            if (node.opacity !== opacity) nodes.update({ id: node.id, opacity });
        });
    },

    /**
     * Applies a search filter to graph nodes by hiding non-matching nodes
     * and edges. Only nodes whose labels contain the query stay visible;
     * edges remain visible if at least one endpoint matches.
     *
     * @param {string} query - The search query string
     */
    /** @deprecated Use GraphFocus.applyFilter */
    applyFilter(query) {
        return GraphFocus.applyFilter(query);
    },

    /** @deprecated Use GraphFocus.settleSearch */
    settleSearch() {
        return GraphFocus.settleSearch();
    },

    /** @deprecated Use GraphFocus._fitToSearchMatches */
    _fitToSearchMatches() {
        return GraphFocus._fitToSearchMatches();
    },

    /** @deprecated Use GraphFocus._kickClusterPhysics */
    _kickClusterPhysics() {
        return GraphFocus._kickClusterPhysics();
    },

    /** @deprecated Use GraphFocus.filterNodes */
    filterNodes(query) {
        return GraphFocus.filterNodes(query);
    },

    // ──────────────────────────────────────────────
    //  GRAPH VIEW OVERLAYS
    // ──────────────────────────────────────────────

    /** @deprecated Use GraphOverlays.lightToInt */
    _lightToInt(raw) {
        return GraphOverlays.lightToInt(raw);
    },

    /** @deprecated Use GraphOverlays.lightColors */
    _lightColors(level) {
        return GraphOverlays.lightColors(level);
    },

    /** @deprecated Use GraphOverlays.heatColors */
    _heatColors(temp) {
        return GraphOverlays.heatColors(temp);
    },

    /** @deprecated Use GraphOverlays.noiseColors */
    _noiseColors(noise) {
        return GraphOverlays.noiseColors(noise);
    },

    /**
     * Legacy alias for the cached ambient-light table. See
     * GraphOverlays.computeAmbientLight (now change-cached: only recomputes
     * when the world graph / area environments actually change, so repeated
     * overlay applies don't re-walk every edge per lit item).
     */
    _computeAmbientLight() {
        return GraphOverlays.computeAmbientLight();
    },

    /**
     * Apply the Light overlay — color areas by ambient light with spill.
     */
    _applyLightOverlay() {
        GraphOverlays.applyLightOverlay();
        GraphNetwork._updateOverlayLegend('light', GraphOverlays.computeAmbientLight());
    },

    /**
     * Apply the Heat overlay — color areas by temperature with propagation.
     */
    _applyHeatOverlay() {
        GraphOverlays.applyHeatOverlay();
        GraphNetwork._updateOverlayLegend('heat');
    },

    /**
     * Apply the Sound overlay — color areas by noise level with propagation.
     */
    _applySoundOverlay() {
        GraphOverlays.applySoundOverlay();
        GraphNetwork._updateOverlayLegend('sound');
    },

    /**
     * Apply the Trigger overlay — highlight trigger sources/targets, dim others.
     */
    _applyTriggerOverlay() {
        GraphOverlays.applyTriggerOverlay();
        GraphNetwork._updateOverlayLegend('trigger');
    },

    /**
     * Apply the Cardinal overlay — label ways with cardinal direction.
     */
    _applyCardinalOverlay() {
        GraphOverlays.applyCardinalOverlay();
        GraphNetwork._updateOverlayLegend('cardinal');
    },

    /**
     * Clear overlay styles and restore default structural view.
     */
    _clearOverlay() {
        graphManager._lastSig = '';
        graphManager.network.setOptions({ physics: { enabled: false } });
        GraphNetwork.loadGraphData();
        if (graphManager._physicsEnabled) {
            graphManager.network.setOptions({ physics: { enabled: true } });
        }
        GraphNetwork._updateOverlayLegend('structural');
    },

    /**
     * Update the legend for the current overlay view.
     */
    _updateOverlayLegend(mode, extraData) {
        if (!graphManager._legendEl) return;
        let inner = '';
        if (mode === 'structural') {
            inner = GraphNetwork.buildLegendHTML();
        } else if (mode === 'light') {
            inner = `<div class="graph-legend-inner">
                <div style="font-size:10px;font-weight:600;color:var(--text-dim);margin-bottom:4px;">💡 Light Overlay</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#0a0a0a;border:1px solid #333;"></span> pitch black 0-20</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#16162a;border:1px solid #4a4a7e;"></span> dim 21-40</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#1e2430;border:1px solid #58a6ff;"></span> normal 41-70</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#3a3518;border:1px solid #e3b341;"></span> bright 71-90</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#4a4020;border:1px solid #fff;"></span> blinding 91-100</div>
                <div class="legend-row" style="margin-top:4px;"><span class="legend-swatch" style="background:#3d2a0a;border:1px solid #f0883e;"></span><span style="font-size:9px;"> lit item</span></div>
            </div>`;
        } else if (mode === 'heat') {
            inner = `<div class="graph-legend-inner">
                <div style="font-size:10px;font-weight:600;color:var(--text-dim);margin-bottom:4px;">🌡️ Heat Overlay</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#0a0a2e;border:1px solid #6e9eff;"></span> ≤ -20°C freezing</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#101840;border:1px solid #7eb8ff;"></span> -5°C cold</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#1a2840;border:1px solid #58a6ff;"></span> 15°C cool</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#2d333b;border:1px solid #58a6ff;"></span> 25°C comfortable</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#3a2a18;border:1px solid #e3b341;"></span> 35°C warm</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#4a2818;border:1px solid #f0883e;"></span> 45°C hot</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#4a1010;border:1px solid #f85149;"></span> ≥ 50°C blazing</div>
                <div class="legend-row" style="margin-top:4px;"><span class="legend-swatch" style="background:#4a2818;border:1px solid #f0883e;"></span><span style="font-size:9px;"> heat source</span></div>
            </div>`;
        } else if (mode === 'sound') {
            inner = `<div class="graph-legend-inner">
                <div style="font-size:10px;font-weight:600;color:var(--text-dim);margin-bottom:4px;">🔊 Sound Overlay</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#0a0a0a;border:1px solid #333;"></span> silent</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#121220;border:1px solid #4a4a7e;"></span> quiet</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#2d333b;border:1px solid #58a6ff;"></span> moderate</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#3a2a18;border:1px solid #e3b341;"></span> loud</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#4a1010;border:1px solid #f85149;"></span> deafening</div>
            </div>`;
        } else if (mode === 'trigger') {
            inner = `<div class="graph-legend-inner">
                <div style="font-size:10px;font-weight:600;color:var(--text-dim);margin-bottom:4px;">⚡ Trigger Overlay</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#2d333b;border:2px solid #bc8cff;"></span> trigger node</div>
                <div class="legend-row"><span class="legend-swatch" style="background:#1a1a1a;border:1px solid #333;"></span> non-trigger node</div>
                <div class="legend-row"><span style="color:#bc8cff;font-size:14px;">━━▶</span> trigger edge</div>
                <div class="legend-row"><span style="color:#30363d;font-size:14px;">╌╌▶</span> normal edge</div>
            </div>`;
        } else if (mode === 'cardinal') {
            inner = `<div class="graph-legend-inner">
                <div style="font-size:10px;font-weight:600;color:var(--text-dim);margin-bottom:4px;">🧭 Cardinal Overlay</div>
                <div style="font-size:9px;color:var(--text-muted);">Ways labeled with direction</div>
                <div style="font-size:9px;color:var(--text-muted);">N S E W NE NW SE SW U D</div>
                <div style="font-size:9px;color:var(--text-muted);margin-top:4px;">Areas arranged geographically</div>
            </div>`;
        }
        if (inner) {
            window.Lit.render(networkManagerHtmlTag`${window.Lit.unsafeHTML(inner)}`, graphManager._legendEl);
            graphManager._legendVisible = true;
            graphManager._legendEl.style.display = 'block';
        }
    },

    /**
     * Apply a named overlay to the graph.
     * @param {string} mode - 'light' | 'heat' | 'sound' | 'trigger' | 'cardinal' | 'structural'
     */
    applyOverlay(mode) {
        if (!graphManager.network) { console.warn('Graph not initialized'); return; }
        graphManager.network.setOptions({ physics: { enabled: false } });
        graphManager._overlayMode = mode;

        if (mode === 'structural') {
            GraphNetwork._clearOverlay();
            return;
        }

        const t0 = performance.now();
        try {
            switch (mode) {
                case 'light': GraphNetwork._applyLightOverlay(); break;
                case 'heat': GraphNetwork._applyHeatOverlay(); break;
                case 'sound': GraphNetwork._applySoundOverlay(); break;
                case 'trigger': GraphNetwork._applyTriggerOverlay(); break;
                case 'cardinal': {
                    if (graphManager._viewMode !== 'cardinal') {
                        graphManager._viewMode = mode;
                    }
                    GraphNetwork._applyCardinalOverlay();
                    break;
                }
            }
            const dt = Math.round(performance.now() - t0);
            const overlayNames = { light:'Light', heat:'Heat', sound:'Sound', trigger:'Trigger', cardinal:'Cardinal' };
            events.log(`📊 ${overlayNames[mode] || mode} overlay applied (${dt}ms)`, 'system-msg');
        } catch (err) {
            console.error('Overlay error:', err);
            events.log(`⚠️ Overlay "${mode}" failed: ${err.message}`, 'error-msg');
            GraphNetwork._clearOverlay();
        }
    }
};
