/**
 * ghosts.js — Live "ghost" preview of staged NL-editor ops (task-387 power-up).
 *
 * Renders uncommitted staged operations onto the vis.js graph in real time:
 *   - created / spawned / connected entities appear as translucent dashed
 *     "ghost nodes" (fixed, labeled "(staged)")
 *   - updated nodes get a dashed highlight on the live node
 *   - deleted nodes get a dashed red highlight on the live node
 *   - attach ops get a dashed ghost edge; detach ops get a dashed red one
 *
 * Re-applies itself after every graph data reload (hook in loadGraphData) and
 * on staging changes, and can auto-pan the camera to the newest staged target
 * when a turn finishes with fresh ops ("Here's what I just drafted").
 *
 * @module nl-editor/ghosts — live preview of staged operations
 * @contributes NLEditorGhosts: dashed ghost nodes/edges for create/update/delete/attach/detach, auto-pan
 * @powers seeing what the NL editor drafted before anything is applied
 * @relates hooks GraphNetwork.loadGraphData; reads staging.js
 * @docs docs/virtualWorld/dev_tasks/done/graph/task-387-natural-language-editor-mode.md
 */

window.NLEditorGhosts = (() => {
    'use strict';

    const NODE_PREFIX = 'nlghost_';
    const EDGE_PREFIX = 'nlghost_e_';

    const TYPE_STYLE = {
        area:      { shape: 'box',      border: '#58a6ff', fill: 'rgba(88,166,255,0.10)',  font: '#8ab9ff', borderWidth: 2 },
        item:      { shape: 'diamond',  border: '#e3b341', fill: 'rgba(227,179,65,0.10)',  font: '#e3b341', borderWidth: 1 },
        way:       { shape: 'triangle', border: '#4ec9b0', fill: 'rgba(78,201,176,0.10)',   font: '#4ec9b0', borderWidth: 1 },
        character: { shape: 'ellipse',  border: '#bc8cff', fill: 'rgba(188,140,255,0.10)',  font: '#bc8cff', borderWidth: 2 }
    };
    const EDITED_STYLE = { border: '#d29922', fill: 'rgba(210,153,34,0.10)', font: '#d29922' };
    const DELETE_STYLE = { border: '#f85149', fill: 'rgba(248,81,73,0.10)',  font: '#f85149' };

    let liveStyledNodeIds = new Set();   // live nodes we currently restyle
    let lastStagedCount = -1;            // for auto-spotlight on new ops

    function _net() {
        return (typeof graphManager !== 'undefined' && graphManager?.network) || null;
    }

    function _nodeConf(id, label, type, x, y) {
        const t = TYPE_STYLE[type] || TYPE_STYLE.item;
        return {
            id,
            label: `${label}`,
            font: { color: t.font, size: 11 },
            shape: t.shape,
            color: { background: t.fill, border: t.border },
            borderWidth: t.borderWidth,
            shapeProperties: { borderDashes: [5, 4] },
            fixed: { x: true, y: true },
            physics: false,
            stagingGhost: true,
            x, y
        };
    }

    function _liveStyleOverride(nodeId, style) {
        const net = _net();
        const raw = (typeof graphManager !== 'undefined')
            && graphManager._graphNodesObj?.[nodeId];
        if (!net?.body?.data?.nodes || !raw) return;
        try {
            const base = (typeof GraphNetwork !== 'undefined' && GraphNetwork.buildNodeConfig)
                ? GraphNetwork.buildNodeConfig(raw)
                : { id: nodeId };
            const cfg = Object.assign({}, base, {
                color: { background: style.fill, border: style.border },
                font: Object.assign({}, base.font || {}, { color: style.font }),
                borderWidth: base.borderWidth || 2,
                shapeProperties: Object.assign({}, base.shapeProperties || {}, { borderDashes: [5, 4] })
            });
            net.body.data.nodes.update(cfg);
        } catch (e) { /* ignore per-node restyle failures */ }
    }

    function _restoreLiveStyles() {
        const net = _net();
        if (!net?.body?.data?.nodes || liveStyledNodeIds.size === 0) return;
        try {
            for (const nodeId of liveStyledNodeIds) {
                const raw = graphManager?._graphNodesObj?.[nodeId];
                if (raw && typeof GraphNetwork?.buildNodeConfig === 'function') {
                    net.body.data.nodes.update(GraphNetwork.buildNodeConfig(raw));
                }
            }
        } catch (e) { /* ignore */ }
        liveStyledNodeIds = new Set();
    }

    /** Position a ghost node near an anchor, spreading spawned siblings. */
    function _near(net, anchorId, index, fallback) {
        try {
            const positions = net.getPositions([anchorId]);
            if (positions && positions[anchorId]) {
                const p = positions[anchorId];
                return { x: p.x + (index % 4) * 70 - 105, y: p.y + Math.floor(index / 4) * 70 - 35 };
            }
        } catch (e) { /* fall through */ }
        try {
            const vp = net.getViewPosition();
            const s = net.getScale() || 1;
            return { x: vp.x + (index % 4) * 80 / s, y: vp.y + Math.floor(index / 4) * 80 / s };
        } catch (e) {
            return { x: (index % 4) * 80, y: Math.floor(index / 4) * 80 };
        }
    }

    function _midpoint(net, idA, idB) {
        try {
            const p = net.getPositions([idA, idB]);
            if (p[idA] && p[idB]) return { x: (p[idA].x + p[idB].x) / 2, y: (p[idA].y + p[idB].y) / 2 };
        } catch (e) { /* ignore */ }
        return null;
    }

    /**
     * Rebuild the ghost overlay from the current staging buffer.
     * @param {{freshOps?: boolean}} options — freshOps triggers auto-spotlight
     *        when new ops appeared since the last refresh.
     */
    function refresh(options = {}) {
        const net = _net();
        const staging = window.NLEditor?.staging;
        if (!net?.body?.data?.nodes || !net.body.data.edges || !staging) return;

        try {
            const nodesDS = net.body.data.nodes;
            const edgesDS = net.body.data.edges;

            // 1. Drop previous ghosts + restore restyled live nodes.
            const oldGhosts = nodesDS.get({ filter: n => String(n.id).startsWith(NODE_PREFIX) });
            if (oldGhosts.length) nodesDS.remove(oldGhosts.map(n => n.id));
            const oldGhostEdges = edgesDS.get({ filter: e => String(e.id).startsWith(EDGE_PREFIX) });
            if (oldGhostEdges.length) edgesDS.remove(oldGhostEdges.map(e => e.id));
            _restoreLiveStyles();

            const ops = staging.getOps();
            const creations = staging.getStagedCreations();
            const deletions = staging.getStagedDeletions();
            const updates = staging.getStagedUpdates();

            const ghostNodes = [];
            const ghostEdges = [];
            let index = 0;

            // 2. Staged creations → ghost nodes (created + connected ways).
            for (const [key, node] of Object.entries(creations)) {
                if (deletions.has(key)) continue;
                const pos = _near(net, null, index++);
                ghostNodes.push(_nodeConf(`${NODE_PREFIX}${node.id}`, `${node.name} (staged)`, node.type || 'item', pos.x, pos.y));
            }

            // 3. Spawns (server mints the id) → ghost near the parent.
            for (const op of ops) {
                if (op.type !== 'spawn_library_item') continue;
                const p = op.payload || {};
                const label = p.rename || String(p.library_id || 'item').replace(/_/g, ' ');
                const pos = _near(net, p.parent_id, index++);
                ghostNodes.push(_nodeConf(`${NODE_PREFIX}spawn_${op.id}`, `${label} (spawn)`, 'item', pos.x, pos.y));
            }

            // 4. connect_areas → way ghost at the midpoint of the two areas.
            for (const op of ops) {
                if (op.type !== 'connect_areas') continue;
                const p = op.payload || {};
                const mid = _midpoint(net, p.area_a_id, p.area_b_id);
                const anchor = mid || _near(net, p.area_a_id, index++);
                const config = _nodeConf(`${NODE_PREFIX}${p.way_id}`, `${p.way_name || 'Door'} (staged)`, 'way', anchor.x, anchor.y);
                ghostNodes.push(config);
                // Two visual ghost edges: area_a ↔ way, area_b ↔ way.
                ghostEdges.push({ id: `${EDGE_PREFIX}c_a_${p.way_id}`, from: p.area_a_id, to: p.way_id, dashes: [8, 5], color: { color: 'rgba(78,201,176,0.55)' }, stagingGhost: true, width: 1 });
                ghostEdges.push({ id: `${EDGE_PREFIX}c_b_${p.way_id}`, from: p.way_id, to: p.area_b_id, dashes: [8, 5], color: { color: 'rgba(78,201,176,0.55)' }, stagingGhost: true, width: 1 });
            }

            // 5. Attach / detach → ghost edges.
            for (const op of ops) {
                if (op.type === 'attach') {
                    const p = op.payload || {};
                    ghostEdges.push({
                        id: `${EDGE_PREFIX}at_${op.id}`,
                        from: p.from_id, to: p.to_id,
                        dashes: [8, 5],
                        color: { color: 'rgba(88,166,255,0.65)' },
                        label: `${p.relation || 'in'} (staged)`,
                        font: { color: '#8ab9ff', size: 8 },
                        stagingGhost: true, width: 1
                    });
                } else if (op.type === 'detach') {
                    const p = op.payload || {};
                    ghostEdges.push({
                        id: `${EDGE_PREFIX}de_${op.id}`,
                        from: p.from_id, to: p.to_id,
                        dashes: [4, 5],
                        color: { color: 'rgba(248,81,73,0.7)' },
                        label: `${p.relation || 'in'} (will detach)`,
                        font: { color: '#f85149', size: 8 },
                        stagingGhost: true, width: 2
                    });
                }
            }

            // 6. update_node / update_matching_nodes / delete_node → restyle
            //    live nodes (no ghost node).
            for (const op of ops) {
                let ids = [];
                if (op.type === 'update_node' || op.type === 'delete_node') {
                    ids = [op.payload?.node_id];
                } else if (op.type === 'update_matching_nodes') {
                    ids = op.payload?.matched_ids || [];
                } else {
                    continue;
                }
                for (const nodeId of ids) {
                    if (!nodeId || !graphManager?._graphNodesObj?.[nodeId]) continue;
                    // Re-synced by loadGraphData if the node no longer exists.
                    if (op.type === 'delete_node') _liveStyleOverride(nodeId, DELETE_STYLE);
                    else _liveStyleOverride(nodeId, EDITED_STYLE);
                    liveStyledNodeIds.add(nodeId);
                }
            }

            if (ghostNodes.length) nodesDS.update(ghostNodes);
            if (ghostEdges.length) edgesDS.update(ghostEdges);
            net.redraw();

            // 7. Auto-spotlight on fresh staged ops ("here's what I drafted").
            if (options.freshOps && lastStagedCount >= 0 && ops.length > lastStagedCount) {
                _spotlight(ops);
            }
            lastStagedCount = ops.length;
        } catch (e) {
            console.warn('[NLEditorGhosts] refresh failed:', e);
        }
    }

    /** Ghost overlay id for an op. Mirrors refresh(): creations and ways use
     *  their minted id, spawns use the op id because the server mints the node. */
    function _ghostIdFor(op) {
        const p = op.payload || {};
        switch (op.type) {
            case 'create_node': return p.node?.id ? `${NODE_PREFIX}${p.node.id}` : null;
            case 'connect_areas': return p.way_id ? `${NODE_PREFIX}${p.way_id}` : null;
            case 'spawn_library_item': return `${NODE_PREFIX}spawn_${op.id}`;
            default: return null;
        }
    }

    /** Live-graph node the newest op concerns, when one exists. */
    function _liveTargetId(op) {
        const p = op.payload || {};
        switch (op.type) {
            case 'create_node': return p.node?.id || null;
            case 'spawn_library_item': return p.parent_id || null;
            case 'connect_areas': return p.area_a_id || null;
            case 'update_node':
            case 'delete_node':
            case 'link_to_library': return p.node_id || null;
            case 'update_matching_nodes': return (p.matched_ids || [])[0] || null;
            case 'attach':
            case 'detach': return p.to_id || null;
            default: return null;
        }
    }

    /** Gently pan the camera to the newest staged op's target. */
    function _spotlight(ops) {
        const net = _net();
        if (!net || ops.length === 0) return;
        const newest = ops[ops.length - 1];
        try {
            const ghostId = _ghostIdFor(newest);
            if (ghostId) {
                const pos = net.getPositions([ghostId]);
                if (pos && pos[ghostId]) {
                    net.moveTo({ position: pos[ghostId], scale: 1.25, animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
                    net.selectNodes([ghostId]);
                    return;
                }
            }
            const targetId = _liveTargetId(newest);
            if (targetId && graphManager?.nodes?.has(targetId)) {
                graphManager.focusNode(targetId);
            }
        } catch (e) { /* camera pan must never throw */ }
    }

    /** Listen to staging changes (the controller fires turn-end spotlights). */
    function wire() {
        if (wire._done) return;
        wire._done = true;
        const staging = window.NLEditor?.staging;
        if (staging?.onChange) staging.onChange(() => refresh());
    }

    return { refresh, wire, spotlight: () => refresh({ freshOps: true }) };
})();

// Auto-wire once the NL editor singleton exists (index.js loads after us).
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => window.NLEditorGhosts?.wire());
} else {
    setTimeout(() => window.NLEditorGhosts?.wire(), 150);
}
