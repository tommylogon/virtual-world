/**
 * GraphContextMenu — context menu for graph nodes and edges
 * Provides right-click context menus with actions tailored to node types.
 * Extracted from graph-manager.js. References the global graphManager singleton.
 *
 * @module GraphContextMenu
 */
const contextMenuHtmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

window.GraphContextMenu = {
    /**
     * Shows a context menu at the given event position for a graph node.
     * Builds a menu string with actions appropriate to the node type (area, item, way, character).
     *
     * @param {MouseEvent} event - The right-click mouse event
     * @param {Object} nodeData - The node data object from the graph
     * @param {string} nodeId - The node identifier
     */
    showContextMenu(event, nodeData, nodeId) {
        graphManager._contextTarget = { nodeData, nodeId, nodeType: nodeData?.type };
        const name = nodeData?.name || nodeId;
        const menu = document.getElementById('context-menu');
        if (!menu) return;

        const typeIcons = { area: '🏠', item: '📦', way: '🚪', character: '🧍' };
        const typeIcon = typeIcons[nodeData?.type] || '📄';
        const items = [contextMenuHtmlTag`<div class="context-menu-header" style="padding:6px 12px;font-size:10px;color:var(--text-dim);border-bottom:1px solid var(--border-light);text-transform:uppercase;letter-spacing:0.5px;">${typeIcon} ${nodeData?.type || 'node'} · ${name}</div>`];
        items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('inspect')}>🔍 Inspect</div>`);

        if (nodeData?.type === 'area') {
            items.push(contextMenuHtmlTag`<div class="context-menu-separator"></div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('add_item')}>📦 Add Item to Area</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('move_character')}>🧍 Move Character Here</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('create_character')}>✨ Create Character Here</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('attach_item')}>🔗 Attach Edge…</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('connect_to')}>👆 Connect to…</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('create_trigger')}>⚡ Add Trigger Edge</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('connect_trigger')}>⚡ Connect Trigger to…</div>`);
        } else if (nodeData?.type === 'item') {
            items.push(contextMenuHtmlTag`<div class="context-menu-separator"></div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('edit')}>✏️ Edit Item</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('save_to_lib')}>📚 Save to Library</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('attach_item')}>🔗 Attach Edge…</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('connect_to')}>👆 Connect to…</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('create_trigger')}>⚡ Add Trigger Edge</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('connect_trigger')}>⚡ Connect Trigger to…</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('delete')}>🗑️ Delete Item</div>`);
        } else if (nodeData?.type === 'way') {
            items.push(contextMenuHtmlTag`<div class="context-menu-separator"></div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('edit')}>✏️ Edit Way</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('attach_item')}>🔗 Attach Edge…</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('connect_to')}>👆 Connect to…</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('create_trigger')}>⚡ Add Trigger Edge</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('connect_trigger')}>⚡ Connect Trigger to…</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('delete')}>🗑️ Delete Way</div>`);
        } else if (nodeData?.type === 'character') {
            items.push(contextMenuHtmlTag`<div class="context-menu-separator"></div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('edit')}>✏️ Edit Character</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('attach_item')}>🔗 Attach Edge…</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('connect_to')}>👆 Connect to…</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('create_trigger')}>⚡ Add Trigger Edge</div>`);
            items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('connect_trigger')}>⚡ Connect Trigger to…</div>`);
        }

        items.push(contextMenuHtmlTag`<div class="context-menu-separator"></div>`);
        items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('duplicate')}>📋 Duplicate</div>`);
        items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('lib_search')}>📚 Show in Library</div>`);
        items.push(contextMenuHtmlTag`<div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('delete')}>🗑️ Delete Node</div>`);

        window.Lit.render(contextMenuHtmlTag`${items}`, menu);
        menu.style.display = 'block';
        menu.style.left = event.clientX + 'px';
        menu.style.top = event.clientY + 'px';
        setTimeout(() => document.addEventListener('click', () => menu.style.display = 'none', { once: true }), 0);
    },

    /**
     * Handles a context menu action based on the action name.
     * Dispatches to the appropriate graphManager method or VW module.
     *
     * @param {string} action - The action identifier (e.g. 'inspect', 'delete', 'duplicate')
     */
    ctxAction(action) {
        const menu = document.getElementById('context-menu');
        if (menu) menu.style.display = 'none';
        const target = graphManager._contextTarget;
        if (!target) return;
        const name = target.nodeData?.name || target.nodeId;

        switch (action) {
            case 'inspect': {
                if (target.isEdge) {
                    // Inspect edge - shows edge inspector
                    if (target.edgeData) {
                        graphManager._showEdgeInspector(target.edgeData);
                    }
                } else {
                    VW?.inspector?.showNode(target.nodeId);
                }
                break;
            }
            case 'add_item': VW?.itemLib?.openForRoom(name); break;
            case 'edit': VW?.inspector?.showNode(target.nodeId); break;
            case 'save_to_lib': VW?.itemLib?.saveWorldItem(target.nodeId); break;
            case 'delete': graphManager._deleteNode(target.nodeId); break;
            case 'delete_edge': {
                if (target.edgeData) {
                    let rawType = target.edgeData.type || 'connection';
                    if (worldState.graph && worldState.graph.edges && (!rawType || rawType === 'connection')) {
                        const matched = worldState.graph.edges.find(e =>
                            e.source === target.edgeData.from && e.target === target.edgeData.to
                        );
                        if (matched) rawType = matched.type || 'connection';
                    }
                    graphManager._deleteEdge(target.edgeData.from, target.edgeData.to, rawType);
                }
                break;
            }
            case 'flip_edge': {
                if (target.edgeData) {
                    const NON_FLIPPABLE = new Set(['connection', 'triggers', 'requires']);
                    const rawType = target.edgeData.type || 'connection';
                    if (NON_FLIPPABLE.has(rawType)) {
                        events.log(`Cannot flip '${rawType}' edges`, 'error-msg');
                        break;
                    }
                    ApiClient.flipEdge(target.edgeData.from, target.edgeData.to, rawType).then(res => {
                        if (res.error) { events.log(`Flip failed: ${res.error}`, 'error-msg'); return; }
                        events.log(`Flipped edge ${res.source} ↔ ${res.target}`, 'system-msg');
                        worldState.fetch();
                    });
                }
                break;
            }
            case 'duplicate': graphManager._duplicateNode(target.nodeId); break;
            case 'move_character': {
                const players = Object.keys(worldState.players || {});
                if (players.length === 0) {
                    events.log('No characters to move.', 'system-msg');
                    return;
                }
                const characterName = prompt(`Move which character to "${name}"?\nAvailable: ${players.join(', ')}`, players[0]);
                if (!characterName || !players.includes(characterName)) {
                    events.log('Character not found.', 'error-msg');
                    return;
                }
                ApiClient.movePlayerToRoom(characterName, name).then(res => {
                    if (res.error) { events.log(`Move failed: ${res.error}`, 'error-msg'); return; }
                    events.log(`Moved "${characterName}" to "${name}"`, 'system-msg');
                    worldState.fetch();
                });
                break;
            }
            case 'create_character': {
                const newName = prompt('Enter name for new character:', 'New Character');
                if (!newName?.trim()) return;
                ApiClient.createCharacter(newName.trim()).then(res => {
                    if (res.error) { events.log(`Create failed: ${res.error}`, 'error-msg'); return; }
                    events.log(`Created "${newName}"`, 'system-msg');
                    // Move to area
                    ApiClient.movePlayerToRoom(newName.trim(), name).then(() => {
                        worldState.fetch();
                    });
                });
                break;
            }
            case 'create_trigger':
                graphManager._createSpecialEdge(target.nodeId, 'triggers', '⚡');
                break;
            case 'connect_to': {
                const fromNodeId = target.nodeId;
                const fromNode = graphManager.nodes.get(fromNodeId);
                if (!fromNode) break;
                const edgeTypes = EdgeTypes.validForSource(fromNode.type);
                graphManager.startPendingConnection(fromNodeId, edgeTypes[0]);
                break;
            }
            case 'connect_trigger':
                graphManager.startPendingConnection(target.nodeId, 'triggers');
                break;
            case 'attach_item':
                graphManager._createEdgeWithType(target.nodeId);
                break;
            case 'lib_search':
                VW?.itemLib?.open();
                if (target.nodeType === 'item') {
                    const search = document.getElementById('item-lib-search');
                    if (search) search.value = name;
                    filterItemLibrary();
                }
                break;
        }
    },

    /**
     * Shows a context menu for a graph edge (connection between nodes).
     * Provides Inspect Edge and Delete Edge options.
     *
     * @param {MouseEvent} event - The right-click mouse event
     * @param {Object} edgeData - The edge data object from the graph
     */
    showEdgeContextMenu(event, edgeData) {
        graphManager._contextTarget = { edgeData, isEdge: true };
        const menu = document.getElementById('context-menu');
        if (!menu) return;

        window.Lit.render(contextMenuHtmlTag`
            <div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('inspect')}>🔍 Inspect Edge</div>
            <div class="context-menu-separator"></div>
            <div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('flip_edge')}>🔀 Flip Edge</div>
            <div class="context-menu-item" @click=${() => GraphContextMenu.ctxAction('delete_edge')} style="color:var(--red);">🗑️ Delete Edge</div>`, menu);
        menu.style.display = 'block';
        menu.style.left = event.clientX + 'px';
        menu.style.top = event.clientY + 'px';
        setTimeout(() => document.addEventListener('click', () => menu.style.display = 'none', { once: true }), 0);
    }
};
