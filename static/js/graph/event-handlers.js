/**
 * GraphEventHandlers — click, context, and manipulation event handlers for the vis.js graph
 * Handles node/edge clicks, right-click context menus, and the vis.js addNode/addEdge
 * manipulation callbacks. Extracted from graph-manager.js.
 * References the global graphManager singleton.
 *
 * @module GraphEventHandlers
 */
window.GraphEventHandlers = {
    /**
     * Handles click events on the vis.js network.
     * Opens the inspector for the clicked node or edge, or hides the inspector on empty click.
     *
     * @param {Object} params - vis.js click event parameters (nodes, edges arrays)
     */
    onClick(params) {
        if (graphManager._pendingConnection && params.nodes.length > 0) {
            const targetId = params.nodes[0];
            if (targetId !== graphManager._pendingConnection.fromNodeId) {
                graphManager._completePendingConnection(targetId);
                return;
            }
        }
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const nodeData = graphManager.nodes.get(nodeId);
            if (nodeData?.type === 'character' && nodeData.name && worldState.players?.[nodeData.name]) {
                if (typeof ui !== 'undefined' && ui.selectAgent) ui.selectAgent(nodeData.name);
                else VW?.inspector?.showNode(nodeId);
            } else {
                VW?.inspector?.showNode(nodeId);
            }
            GraphNetwork.revealItemsForNode(nodeId);
            if (nodeData?.type === 'way') {
                GraphNetwork.revealAreasForWay(nodeId);
            }
        } else if (params.edges.length > 0) {
            const edgeId = params.edges[0];
            let edgeData = null;
            if (graphManager.network.body?.data?.edges) {
                edgeData = graphManager.network.body.data.edges.get(edgeId);
            }
            graphManager._showEdgeInspector(edgeData || { id: edgeId, from: edgeId, to: edgeId, label: 'unknown' });
        } else {
            if (graphManager._pendingConnection) {
                graphManager.cancelPendingConnection();
                return;
            }
            GraphNetwork.hideRevealedItems();
            GraphNetwork.hideRevealedAreas();
            hideInspectorPanel();
        }
    },

    /**
     * Handles right-click (context) events on the vis.js network.
     * Shows a context menu for the clicked node or edge.
     *
     * @param {Object} params - vis.js context event parameters (nodes, edges arrays, event)
     */
    onContext(params) {
        params.event.preventDefault();
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const nodeData = graphManager.nodes.get(nodeId);
            GraphContextMenu.showContextMenu(params.event, nodeData, nodeId);
        } else if (params.edges.length > 0) {
            const edgeId = params.edges[0];
            let edgeData = null;
            if (graphManager.network.body?.data?.edges) {
                edgeData = graphManager.network.body.data.edges.get(edgeId);
            }
            GraphContextMenu.showEdgeContextMenu(params.event, edgeData || { id: edgeId, from: edgeId, to: edgeId, label: 'unknown' });
        }
    },

    /**
     * Handles the vis.js addNode manipulation event.
     * Opens a create area modal and creates the new area on submit.
     *
     * @param {Object} data - vis.js add node data
     * @param {Function} callback - vis.js callback to finalize node creation
     */
    onAddNode(data, callback) {
        callback(null);
        openCreateModal('area', async (formData) => {
            if (!formData.name) { toastInfo('Area name required'); return; }
            const res = await ApiClient.createRoom(formData);
            if (res.error) toastError('Error: ' + res.error);
            else { events.log(`Created area: ${formData.name}`, 'system-msg'); worldState.fetch(); }
            graphEditor.setTool('select');
        });
    },

    /**
     * Handles the vis.js addEdge manipulation event.
     * Validates the connection (must be between areas) and opens
     * a create connection modal.
     *
     * @param {Object} data - vis.js add edge data (from and to node IDs)
     * @param {Function} callback - vis.js callback to finalize edge creation
     */
    onAddEdge(data, callback) {
        if (data.from === data.to) { toastInfo('Cannot connect node to itself.'); callback(null); return; }
        callback(null);
        const fromNode = graphManager.nodes.get(data.from);
        const toNode = graphManager.nodes.get(data.to);
        if (!fromNode || !toNode) { toastInfo('Invalid nodes.'); return; }
        if (fromNode.type === 'area' && toNode.type === 'area') {
            openCreateModal('connection', async (formData) => {
            if (!formData.room1 || !formData.room2) { toastInfo('Select both areas'); return; }
            const payload = {
                room1: formData.room1, room2: formData.room2,
                dir1: formData.dir1.trim(), dir2: formData.dir2.trim(),
                state: formData.state || (formData.locked ? 'locked' : 'open'),
                description: formData.description || `A ${formData.locked ? 'locked' : ''} way`.trim(),
                way_id: formData.way_id || '',
                pass_message: formData.pass_message || '',
                auto_close: formData.auto_close || false,
                see_through: formData.see_through || false,
                needs_open: formData.needs_open || { enabled: false, skill: 'Athletics', dc: 15 },
                tags: formData.tags || [],
                triggers: formData.triggers || [],
                view_from_a: formData.view_from_a || '',
                view_from_b: formData.view_from_b || '',
            };
                const res = await ApiClient.connectRooms(payload);
                if (res.error) toastError('Error: ' + res.error);
                else { events.log(`Connected ${formData.room1} <-> ${formData.room2}`, 'system-msg'); worldState.fetch(); }
                graphEditor.setTool('select');
            });
        } else {
            graphManager._createEdgeWithType(data.from);
        }
    },

    /**
     * Handles drag end events on the vis.js network (position saving).
     * Reserved for future use — currently a no-op.
     *
     * @param {Object} params - vis.js drag end event parameters
     */
    onDragEnd(/* params */) {
        // Reserved for future position-saving implementation
    }
};
