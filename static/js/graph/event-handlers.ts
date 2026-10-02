/**
 * GraphEventHandlers — click, context, and manipulation event handlers for the vis.js graph
 * Handles node/edge clicks, right-click context menus, and the vis.js addNode/addEdge
 * manipulation callbacks. Extracted from graph-manager.js.
 * References the global graphManager singleton.
 *
 * @module graph/event-handlers — graph click/context/manipulation handlers
 * @contributes GraphEventHandlers: node/edge click, shift-click bulk selection, right-click context, addNode/addEdge callbacks
 * @powers Graph canvas — selecting and right-clicking nodes, and drawing new nodes/edges
 * @relates wired in GraphNetwork.init; delegates to GraphContextMenu + GraphNodeOps + GraphBackground
 * @docs docs/virtualWorld/UI & Settings/Rendering & UI Modules.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
// Named `GraphEventHandlersModule` because the global `GraphEventHandlers`
// ambient declaration below would otherwise collide with a same-named const.
const GraphEventHandlersModule = {
    /**
     * The modifier keys of a vis.js interaction (bug-49).
     *
     * `params.event` is **not** the DOM event. vis-network wraps the original
     * input in its own pointer object (Hammer), and that wrapper proxies the
     * geometry the context menu needs (`clientX`/`clientY`) but **not** the
     * keyboard state — so `params.event.shiftKey` is always `undefined` and a
     * shift-click silently behaved like a plain click: the inspector opened and
     * no bulk selection was made. The real event is `params.event.srcEvent`.
     *
     * All three shapes are unwrapped here rather than at each call site: the
     * wrapper, a bare DOM event, and the array some vis builds pass.
     *
     * @param {Object} params - vis.js event parameters
     * @returns {{shiftKey: boolean, ctrlKey: boolean, metaKey: boolean, altKey: boolean}}
     */
    modifiers(params: VisParams): { shiftKey: boolean; ctrlKey: boolean; metaKey: boolean; altKey: boolean } {
        const raw = params && params.event;
        const list: VisEventLike[] = Array.isArray(raw) ? raw : [raw as VisEventLike];
        for (const ev of list) {
            if (!ev) continue;
            const src = ev.srcEvent || ev;
            if (src.shiftKey || src.ctrlKey || src.metaKey || src.altKey) {
                return {
                    shiftKey: !!src.shiftKey,
                    ctrlKey: !!src.ctrlKey,
                    metaKey: !!src.metaKey,
                    altKey: !!src.altKey,
                };
            }
        }
        return { shiftKey: false, ctrlKey: false, metaKey: false, altKey: false };
    },

    /**
     * Handles click events on the vis.js network.
     * Opens the inspector for the clicked node or edge, or hides the inspector on empty click.
     *
     * @param {Object} params - vis.js click event parameters (nodes, edges arrays)
     */
    onClick(params: VisParams): void {
        if (graphManager._pendingConnection && params.nodes.length > 0) {
            const targetId = params.nodes[0];
            if (targetId !== graphManager._pendingConnection.fromNodeId) {
                graphManager._completePendingConnection(targetId);
                return;
            }
        }
        if (params.nodes.length > 0) {
            // task-378: shift-click toggles bulk selection (no inspector open).
            // `modifiers` reads srcEvent — params.event itself has no shiftKey.
            if (GraphEventHandlersModule.modifiers(params).shiftKey && !graphManager._pendingConnection) {
                graphManager._toggleBulkSelect(params.nodes[0]);
                return;
            }
            const nodeId = params.nodes[0];
            const nodeData: VisNode = graphManager.nodes.get(nodeId);
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
            let edgeData: VisEdgeData | null = null;
            if (graphManager.network.body?.data?.edges) {
                edgeData = graphManager.network.body.data.edges.get(edgeId);
            }
            graphManager._showEdgeInspector(edgeData || { id: edgeId, from: edgeId, to: edgeId, label: 'unknown' });
        } else {
            if (graphManager._pendingConnection) {
                graphManager.cancelPendingConnection();
                return;
            }
            graphManager._clearBulkSelection();
            GraphNetwork.hideRevealedItems();
            GraphNetwork.hideRevealedAreas();
            hideInspectorPanel();
        }
    },

    /**
     * Double-click: if the node is a placed child zone (a feature cell carrying
     * `child_scope_id`), load that scope into the graph — the level-scoped
     * drill-down (task-397). Otherwise fall through to the normal click.
     *
     * @param {Object} params - vis.js doubleClick event parameters
     */
    onDoubleClick(params: VisParams): void {
        const nodeId = params?.nodes?.[0];
        if (!nodeId) return;
        const nodeData: VisNode = graphManager.nodes.get(nodeId);
        const childScope = nodeData?.properties?.child_scope_id;
        if (!childScope) return;
        const sel = document.getElementById('graph-scope-filter') as HTMLSelectElement | null;
        graphManager.setScopeFilter(childScope);
        if (sel) sel.value = String(childScope);
    },

    /**
     * Handles right-click (context) events on the vis.js network.
     * Shows a context menu for the clicked node or edge.
     *
     * @param {Object} params - vis.js context event parameters (nodes, edges arrays, event)
     */
    onContext(params: VisParams): void {
        const rawEvent = params.event;
        (Array.isArray(rawEvent) ? rawEvent[0] : rawEvent)?.preventDefault?.();
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const nodeData: VisNode = graphManager.nodes.get(nodeId);
            GraphContextMenu.showContextMenu(params.event, nodeData, nodeId);
        } else if (params.edges.length > 0) {
            const edgeId = params.edges[0];
            let edgeData: VisEdgeData | null = null;
            if (graphManager.network.body?.data?.edges) {
                edgeData = graphManager.network.body.data.edges.get(edgeId);
            }
            GraphContextMenu.showEdgeContextMenu(params.event, edgeData || { id: edgeId, from: edgeId, to: edgeId, label: 'unknown' });
        } else if ((window as unknown as { GraphBackground?: { showCanvasMenu(event: unknown): void } }).GraphBackground) {
            // Empty canvas → the graph-map menu (add/edit/crop the background,
            // lock nodes, save the layout).
            (window as unknown as { GraphBackground: { showCanvasMenu(event: unknown): void } }).GraphBackground.showCanvasMenu(params.event);
        }
    },

    /**
     * Handles the vis.js addNode manipulation event.
     * Opens a create area modal and creates the new area on submit.
     *
     * @param {Object} data - vis.js add node data
     * @param {Function} callback - vis.js callback to finalize node creation
     */
    onAddNode(data: unknown, callback: (result: unknown) => void): void {
        callback(null);
        openCreateModal('area', async (formData: Record<string, any>) => {
            if (!formData.name) { toastInfo('Area name required'); return; }
            const res = await (ApiClient as unknown as EventHandlersApiClient).createRoom(formData);
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
    onAddEdge(data: { from: string; to: string }, callback: (result: unknown) => void): void {
        if (data.from === data.to) { toastInfo('Cannot connect node to itself.'); callback(null); return; }
        callback(null);
        const fromNode: VisNode = graphManager.nodes.get(data.from);
        const toNode: VisNode = graphManager.nodes.get(data.to);
        if (!fromNode || !toNode) { toastInfo('Invalid nodes.'); return; }
        if (fromNode.type === 'area' && toNode.type === 'area') {
            openCreateModal('connection', async (formData: Record<string, any>) => {
            if (!formData.room1 || !formData.room2) { toastInfo('Select both areas'); return; }
            if (formData.room1 === formData.room2) { toastInfo('Pick two different areas.'); return; }
            const payload = {
                room1: formData.room1, room2: formData.room2,
                dir1: formData.dir1.trim(), dir2: formData.dir2.trim(),
                name: formData.name || '',
                one_way: formData.one_way || false,
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
                const res = await (ApiClient as unknown as EventHandlersApiClient).connectRooms(payload);
                if (res.error) toastError('Error: ' + res.error);
                else { events.log(connectSummary(res, { room1: formData.room1, room2: formData.room2, way_id: formData.way_id }), 'system-msg'); worldState.fetch(); }
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

(window as unknown as { GraphEventHandlers: typeof GraphEventHandlersModule }).GraphEventHandlers = GraphEventHandlersModule;

// Declared below the first value statement on purpose: TypeScript drops a
// file's leading JSDoc block when the first statement is type-only, which would
// strip the `@module` header tools/js_module_index.py reads.

/**
 * Ambient declarations for the still-unconverted globals this file calls.
 * types/globals.d.ts is a shared hub other lanes edit concurrently, so the
 * names are declared here instead. `tools/globalsd-declarations.md` lists them
 * for a follow-up hub edit.
 */
declare const GraphNetwork: {
    revealItemsForNode(nodeId: string): void;
    revealAreasForWay(nodeId: string): void;
    hideRevealedItems(): void;
    hideRevealedAreas(): void;
};
declare const ui: { selectAgent?(name: string): void };
declare function hideInspectorPanel(): void;
declare function openCreateModal(kind: string, onSubmit: (formData: Record<string, any>) => void | Promise<void>): void;
declare const graphEditor: { setTool(tool: string): void };
declare function connectSummary(res: unknown, refs: Record<string, unknown>): string;

/** Extra ApiClient surface this file uses but the shared hub does not declare. */
interface EventHandlersApiClient {
    createRoom(formData: Record<string, unknown>): Promise<{ error?: string; [key: string]: unknown }>;
    connectRooms(payload: Record<string, unknown>): Promise<{ error?: string; [key: string]: unknown }>;
}

interface VisEventLike {
    srcEvent?: { shiftKey?: boolean; ctrlKey?: boolean; metaKey?: boolean; altKey?: boolean };
    shiftKey?: boolean;
    ctrlKey?: boolean;
    metaKey?: boolean;
    altKey?: boolean;
    preventDefault?: () => void;
}

interface VisParams {
    nodes: string[];
    edges: string[];
    event?: VisEventLike | VisEventLike[];
    [key: string]: unknown;
}

interface VisNode {
    id?: string;
    type?: string;
    name?: string;
    properties?: Record<string, unknown>;
    [key: string]: unknown;
}

interface VisEdgeData {
    id?: string;
    from?: string;
    to?: string;
    label?: string;
}
