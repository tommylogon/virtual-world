/**
 * GraphManager — vis.js network graph, context menu, and graph API operations
 */
const graphManagerHtmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

class GraphManager {
    constructor() {
        this.network = null;
        this.nodes = new Map();
        this._contextTarget = null;
        this._lastSig = '';          // hash to skip redundant reloads
        this._physicsEnabled = true;
        this._legendEl = null;
        this._searchQuery = '';
        this._viewMode = 'graph';
        this._cardinalLayout = false;
        this._showEdgeLabels = true;
        this._edgeLabelSize = 8;
        this._showItems = false;
        this._showOnlyInhabitedAreas = true;
        this._revealedAreaIds = new Set();
        this._pendingConnection = null;
        this._revealedItemIds = new Map();
        this._floorFilter = 'all';
        this._floorOptions = [];
        this._showImages = (() => {
            try { const stored = localStorage.getItem('vw_graphShowImages'); return stored !== null ? stored === '1' : true; } catch (e) { return true; }
        })();
    }

    async init() {
        await GraphNetwork.init();
        await this._applyEngineConfigDefaults();
    }

    async _applyEngineConfigDefaults() {
        try {
            const resp = await fetch('/api/settings/engine_config');
            if (!resp.ok) return;
            const data = await resp.json();
            const values = data.values || {};
            if ('graph.physics_enabled' in values) {
                this._physicsEnabled = !!values['graph.physics_enabled'];
                const pb = document.getElementById('btn-physics');
                if (pb) pb.textContent = this._physicsEnabled ? '⏸ Physics' : '▶ Physics';
                if (this.network) {
                    this.network.setOptions({ physics: { enabled: this._physicsEnabled } });
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

    async _saveGraphConfigKey(key, value) {
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

    toggleCardinalLayout() {
        this._cardinalLayout = !this._cardinalLayout;
        const btn = document.getElementById('btn-cardinal');
        if (btn) btn.textContent = this._cardinalLayout ? '🗺️ Map' : '🔮 Graph';
        this._physicsEnabled = true;
        const pb = document.getElementById('btn-physics');
        if (pb) pb.textContent = this._cardinalLayout ? '▶ Physics' : '⏸ Physics';
        // Clear signature so loadGraphData doesn't skip the reload
        this._lastSig = '';
        this.loadGraphData();
        this._saveGraphConfigKey('graph.physics_enabled', this._physicsEnabled);
    }

    async loadGraphData() { return GraphNetwork.loadGraphData(); }

    _buildTooltip(nodeData) { return GraphNetwork.buildTooltip(nodeData); }

    _onClick(params) { return GraphEventHandlers.onClick(params); }

    _onContext(params) { return GraphEventHandlers.onContext(params); }

    // --- Context Menu ---

    _showContextMenu(event, nodeData, nodeId) {
        this._contextTarget = { nodeData, nodeId, nodeType: nodeData?.type };
        const name = nodeData?.name || nodeId;
        const menu = document.getElementById('context-menu');
        if (!menu) return;

        const typeIcons = { area: '🏠', item: '📦', way: '🚪', character: '🧍' };
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

    _ctxAction(action) {
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
                if (libraryBrowser?.saveAreaByName) libraryBrowser.saveAreaByName(areaName);
                else events.log('Library browser not ready.', 'error-msg');
                break;
            }
            case 'delete': this._deleteNode(t.nodeId); break;
            case 'delete_edge': {
                if (t.edgeData) {
                    // Extract raw type from worldState.graph.edges, not the display label
                    let rawType = t.edgeData.type || 'connection';
                    if (worldState.graph && worldState.graph.edges && (!rawType || rawType === 'connection')) {
                        const matched = worldState.graph.edges.find(e => 
                            e.source === t.edgeData.from && e.target === t.edgeData.to
                        );
                        if (matched) rawType = matched.type || 'connection';
                    }
                    this._deleteEdge(t.edgeData.from, t.edgeData.to, rawType);
                }
                break;
            }
            case 'duplicate': this._duplicateNode(t.nodeId); break;
            case 'move_character': {
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
                ApiClient.movePlayerToRoom(charName, name).then(res => {
                    if (res.error) { events.log(`Move failed: ${res.error}`, 'error-msg'); return; }
                    events.log(`Moved "${charName}" to "${name}"`, 'system-msg');
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
                this._createSpecialEdge(t.nodeId, 'triggers', '⚡');
                break;
            case 'lib_search':
                VW?.itemLib?.open();
                if (t.nodeType === 'item') {
                    const search = document.getElementById('item-lib-search');
                    if (search) search.value = name;
                    filterItemLibrary();
                }
                break;
        }
    }

    async _deleteNode(nodeId) { return GraphNodeOps.deleteNode(nodeId); }

    async _deleteEdge(source, target, edgeType) { return GraphNodeOps.deleteEdge(source, target, edgeType); }

    async _duplicateNode(nodeId) { return GraphNodeOps.duplicateNode(nodeId); }

    async _createSpecialEdge(fromNodeId, edgeType, emoji) { return GraphNodeOps.createSpecialEdge(fromNodeId, edgeType, emoji); }

    async _createEdgeWithType(fromNodeId) {
        const fromNode = this.nodes.get(fromNodeId);
        if (!fromNode) return;

        const edgeTypes = EdgeTypes.validForSource(fromNode.type);
        const typeList = edgeTypes.map((t, i) => {
            const cfg = EdgeTypes.getConfig(t);
            return `${i + 1}. ${cfg.icon} ${cfg.label} — ${cfg.desc}`;
        }).join('\n');

        const typeChoice = prompt(`Select edge type for "${fromNode.name}":\n\n${typeList}\n\nEnter number (1-${edgeTypes.length}):`, '1');
        if (!typeChoice) return;

        const typeIdx = parseInt(typeChoice) - 1;
        if (typeIdx < 0 || typeIdx >= edgeTypes.length) { events.log('Invalid edge type.', 'error-msg'); return; }
        const edgeType = edgeTypes[typeIdx];

        const cfg = EdgeTypes.getConfig(edgeType);
        const validTargets = EdgeTypes.validTargets(edgeType);

        const allNodes = Array.from(this.nodes.entries());
        const candidates = allNodes.filter(([id, nd]) => id !== fromNodeId && validTargets.includes(nd.type));
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
        const properties = {};
        if (description) properties.description = description;

        const result = await ApiClient.createEdge(fromNodeId, targetId, edgeType, properties);
        if (result.status === 'success') {
            events.log(`${cfg.icon} Created ${cfg.label} edge: ${fromNode.name} → ${this.nodes.get(targetId)?.name || targetId}`, 'system-msg');
            worldState.fetch();
        } else {
            events.log(`Failed to create edge: ${result.error || 'unknown error'}`, 'error-msg');
        }
    }

    startPendingConnection(fromNodeId, edgeType) {
        const fromNode = this.nodes.get(fromNodeId);
        if (!fromNode) return;
        this._pendingConnection = { fromNodeId, edgeType, fromName: fromNode.name || fromNode.id };
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

    async _completePendingConnection(targetNodeId) {
        const pending = this._pendingConnection;
        if (!pending) return;
        const { fromNodeId, edgeType, fromName } = pending;
        this._pendingConnection = null;
        VW?.ui?.setStatus('Idle.', 'info');

        const toNode = this.nodes.get(targetNodeId);
        if (!toNode) { events.log('Target node not found.', 'error-msg'); return; }
        if (targetNodeId === fromNodeId) { events.log('Cannot connect node to itself.', 'error-msg'); return; }

        const cfg = EdgeTypes.getConfig(edgeType);
        const result = await ApiClient.createEdge(fromNodeId, targetNodeId, edgeType, {});
        if (result.status === 'success') {
            events.log(`${cfg.icon} Connected ${cfg.label}: ${fromName} → ${toNode.name || targetNodeId}`, 'system-msg');
            worldState.fetch();
        } else {
            events.log(`Failed to connect: ${result.error || 'unknown error'}`, 'error-msg');
        }
    }

    async _saveEdgeProperty(fromId, toId, key, rawValue) {
        let value = rawValue;
        try { value = JSON.parse(rawValue); } catch (e) { /* keep string */ }
        const res = await ApiClient.updateEdge(fromId, toId, { old_type: 'connection', properties: { [key]: value } });
        if (res.status === 'success') {
            events.log('Edge property updated.', 'system-msg');
            worldState.fetch();
        } else {
            events.log('Failed to update property: ' + (res.error || 'unknown'), 'error-msg');
        }
    }

    async _deleteEdgeProperty(fromId, toId, key) {
        const res = await ApiClient.updateEdge(fromId, toId, { old_type: 'connection', properties: { [key]: null } });
        if (res.status === 'success') {
            events.log('Edge property removed.', 'system-msg');
            worldState.fetch();
        } else {
            events.log('Failed to remove property: ' + (res.error || 'unknown'), 'error-msg');
        }
    }

    async _addEdgeProperty(fromId, toId, rawType) {
        const key = prompt('Property name:');
        if (!key || !key.trim()) return;
        const rawValue = prompt('Property value (JSON or plain text):', '');
        if (rawValue === null) return;
        let value = rawValue;
        try { value = JSON.parse(rawValue); } catch (e) { /* keep string */ }
        const res = await ApiClient.updateEdge(fromId, toId, { old_type: rawType, properties: { [key.trim()]: value } });
        if (res.status === 'success') {
            events.log('Edge property added.', 'system-msg');
            worldState.fetch();
        } else {
            events.log('Failed to add property: ' + (res.error || 'unknown'), 'error-msg');
        }
    }

    _onAddNode(data, callback) { return GraphEventHandlers.onAddNode(data, callback); }

    _onAddEdge(data, callback) { return GraphEventHandlers.onAddEdge(data, callback); }

    _showEdgeContextMenu(event, edgeData) {
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

    _showEdgeInspector(edge) {
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
            const htmlTag = (strings, ...values) => window.Lit.html(strings, ...values);
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

    async _changeEdgeType(source, target, oldType, newType) {
        if (oldType === newType) return;
        const cfg = EdgeTypes.getConfig(newType);
        // Carry the existing edge's properties so a type change doesn't drop
        // direction/cardinal/description data on the way.
        const worldEdge = worldState.graph?.edges?.find(e =>
            e.source === source && e.target === target && e.type === oldType
        );
        const properties = worldEdge?.properties || {};
        const result = await ApiClient.updateEdge(source, target, { old_type: oldType, new_type: newType, properties });
        if (result.status === 'success') {
            events.log(`${cfg.icon} Changed edge type: ${oldType} → ${newType}`, 'system-msg');
            worldState.fetch();
        } else {
            events.log(`Failed to change edge type: ${result.error || 'unknown error'}`, 'error-msg');
        }
    }

    _toggleTree(id) {
        const el = document.getElementById(id);
        if (!el) return;
        const toggle = el.parentElement.querySelector('.vtree-toggle');
        if (el.style.display === 'none') {
            el.style.display = 'block';
            if (toggle) toggle.textContent = '▼';
        } else {
            el.style.display = 'none';
            if (toggle) toggle.textContent = '▶';
        }
    }

    _toggleDesc(id) {
        const short = document.getElementById(id + '-d');
        const full = document.getElementById(id + '-df');
        const more = short.parentElement.querySelector('.vtree-more');
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

    _selectRoom(name) {
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
    focusNode(nodeId) {
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
    showNodeAndFocus(nodeId) {
        if (VW?.inspector) VW.inspector.showNode(nodeId);
        this.focusNode(nodeId);
    }

    _escHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    togglePhysics() {
        graphManager._physicsEnabled = !graphManager._physicsEnabled;
        graphManager.network.setOptions({ physics: { enabled: graphManager._physicsEnabled } });
        const btn = document.getElementById('btn-physics');
        if (btn) btn.textContent = graphManager._physicsEnabled ? '⏸ Physics' : '▶ Physics';
        graphManager._saveGraphConfigKey('graph.physics_enabled', graphManager._physicsEnabled);
    }

    fitView() { return GraphNetwork.fitView(); }

    toggleLegend() { return GraphNetwork.toggleLegend(); }

    toggleTriggers() { return GraphNetwork.toggleTriggers(); }

    toggleItems() {
        GraphNetwork.toggleItems();
        graphManager._saveGraphConfigKey('graph.show_items', graphManager._showItems);
    }

    toggleInhabitedAreas() {
        GraphNetwork.toggleInhabitedAreas();
        graphManager._saveGraphConfigKey('graph.show_only_inhabited', graphManager._showOnlyInhabitedAreas);
    }

    toggleTagPanel() { return GraphNetwork.toggleTagPanel(); }

    toggleEdgeLabels() {
        this._showEdgeLabels = !this._showEdgeLabels;
        const btn = document.getElementById('btn-edge-labels');
        if (btn) btn.classList.toggle('active', this._showEdgeLabels);
        this._lastSig = '';
        this.loadGraphData();
    }

    setEdgeLabelSize(delta) {
        this._edgeLabelSize = Math.max(4, Math.min(20, this._edgeLabelSize + delta));
        const out = document.getElementById('edge-label-size');
        if (out) out.textContent = this._edgeLabelSize;
        this._lastSig = '';
        this.loadGraphData();
    }

    // --- Floor filter ---

    /**
     * Set the active floor filter and reload the graph. Empty/'all' shows all floors.
     * Also refreshes the picker dropdown from the areas seen in the graph.
     * @param {string|number} floor - 'all' or a floor number
     */
    setFloorFilter(floor) {
        const normalized = (String(floor) === 'all' || floor === null || floor === undefined) ? 'all' : String(floor);
        this._floorFilter = normalized;
        const sel = document.getElementById('floor-filter');
        if (sel) sel.value = normalized;
        GraphNetwork.applyVisibility();
    }

    /**
     * Refresh the available floors from area nodes and the picker dropdown.
     * Composes with the current filter (keeps the selected floor if still present).
     */
    refreshFloorOptions() {
        const floors = new Set(['all']);
        this.nodes.forEach((nodeData) => {
            if (nodeData.type === 'area' && nodeData.properties?.floor !== undefined) {
                floors.add(String(nodeData.properties.floor));
            }
        });
        this._floorOptions = ['all', ...Array.from(floors).filter(f => f !== 'all').sort((a, b) => Number(a) - Number(b))];
        // Reflect current filter; default to 'all' if the selected floor no longer exists
        const sel = document.getElementById('floor-filter');
        if (!sel) return;
        const current = this._floorOptions.includes(this._floorFilter) ? this._floorFilter : 'all';
        this._floorFilter = current;
        window.Lit.render(graphManagerHtmlTag`${this._floorOptions.map(f =>
            graphManagerHtmlTag`<option value=${f} ?selected=${f === current}>${f === 'all' ? '🏢 All Floors' : `🏢 Floor ${f}`}</option>`)}`, sel);
        sel.value = current;
    }

    /**
     * True when an active floor filter is set.
     */
    floorFilterActive() {
        return this._floorFilter !== 'all';
    }

    // --- View mode switching: Graph / Map / Overlays ---

    setViewMode(mode) {
        this._viewMode = mode;
        document.querySelectorAll('.view-toggle').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === mode);
        });
        document.querySelectorAll('.overlay-toggle').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.overlay === mode);
        });
        // Update dropdown button text to reflect active overlay
        const overlayBtn = document.getElementById('btn-overlays');
        const overlayNames = { light:'💡 Light', heat:'🌡️ Heat', sound:'🔊 Sound', trigger:'⚡ Triggers', cardinal:'🧭 Cardinal' };
        if (overlayBtn) overlayBtn.textContent = overlayNames[mode] || '📊 Overlays ▾';
        const container = document.getElementById('graph-container');
        container.querySelectorAll('.view-overlay').forEach(el => el.remove());
        const visEl = container.querySelector('.vis-network') || container.querySelector('canvas');

        const overlayModes = ['light', 'heat', 'sound', 'trigger', 'cardinal'];

        if (mode === 'graph') {
            if (visEl) visEl.style.display = '';
            // Disengage cardinal layout first so loadGraphData doesn't re-apply it
            if (this._cardinalLayout) {
                this._cardinalLayout = false;
                const cb = document.getElementById('btn-cardinal');
                if (cb) cb.textContent = '🗺️ Map';
                this._physicsEnabled = true;
                const pb = document.getElementById('btn-physics');
                if (pb) pb.textContent = '⏸ Physics';
            }
            if (this.network) {
                GraphNetwork.applyOverlay('structural');
                this.network.setOptions({ physics: { enabled: this._physicsEnabled } });
                this.fitView();
            }
        } else if (overlayModes.includes(mode)) {
            if (visEl) visEl.style.display = '';
            if (this.network) {
                this.network.setOptions({ physics: { enabled: false } });
                if (mode === 'cardinal' && !this._cardinalLayout) {
                    this._viewMode = mode;
                    this.toggleCardinalLayout();
                } else {
                    GraphNetwork.applyOverlay(mode);
                }
            }
        }
    }

    _renderCurrentView() {
        if (this._viewMode === 'graph') return;
        const container = document.getElementById('graph-container');
        container.querySelectorAll('.view-overlay').forEach(el => el.remove());
        const overlayModes = ['light', 'heat', 'sound', 'trigger', 'cardinal'];
        if (!overlayModes.includes(this._viewMode)) return;
        const visEl = container.querySelector('.vis-network') || container.querySelector('canvas');
        if (visEl) visEl.style.display = '';
        if (this.network) GraphNetwork.applyOverlay(this._viewMode);
    }

    _toggleOverlayDropdown() {
        const menu = document.getElementById('overlay-dropdown');
        if (!menu) return;
        const shown = menu.style.display !== 'none';
        menu.style.display = shown ? 'none' : 'block';
        if (!shown) {
            const close = (e) => {
                if (!menu.contains(e.target) && e.target.id !== 'btn-overlays') {
                    menu.style.display = 'none';
                    document.removeEventListener('click', close);
                }
            };
            setTimeout(() => document.addEventListener('click', close), 0);
        }
    }

    _buildLegendHTML() { return GraphNetwork.buildLegendHTML(); }

    _applyFilter(query) { GraphNetwork.applyFilter(query); }

    filterNodes(query) { GraphNetwork.filterNodes(query); }
}

// Singleton
const graphManager = new GraphManager();
window.graphManager = graphManager;

// Compatibility aliases for inline onclick handlers in HTML
function hideInspectorPanel() { VW?.inspector?.hide(); }
function selectAgent(name) { ui.selectAgent(name); }
