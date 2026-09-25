/**
 * @module graph/layout-engine — map layout: painted grid or cardinal fallback
 * @contributes window.GraphLayoutEngine.applyCardinalLayout(nodesObj), gridPosition, hasPaintedGrid
 * @powers arranging areas as a map — from painted WorldPainter coords when
 *   present, else derived from exit cardinals
 * @relates reads worldState.areas + exit cardinals; moves nodes on graphManager.network
 * @docs docs/virtualWorld/UI & Settings/Rendering & UI Modules.md
 *
 * Two modes:
 *  - GRID (preferred) — nodes carry `properties.x`/`y` from the WorldPainter
 *    compiler (areas `cell * CELL_CANVAS_UNITS`, ways at cell midpoints). The map
 *    is *read* exactly, physics stays off, nothing is force-settled. This is the
 *    "same XY grid we painted" the author expects.
 *  - CARDINAL (fallback) — hand-authored worlds with no painted coords: BFS the
 *    exits onto an integer grid and let hybrid physics settle it, as before.
 */
window.GraphLayoutEngine = {
    /**
     * Lay areas out for map mode. Returns which layout was used — `'grid'` when
     * the painted lattice was read, `'cardinal'` for the derived fallback, or
     * `null` when nothing was applied — so the caller can keep physics off for a
     * painted map (a grid is read, not simulated).
     * @param {Object} nodesObj
     * @returns {'grid'|'cardinal'|null}
     */
    applyCardinalLayout(nodesObj) {
        if (!graphManager.network) return null;
        const nodesDS = graphManager.network.body.data.nodes;
        if (!nodesDS) return null;

        // Painted grid → exact map, no guessing and no physics.
        if (GraphLayoutEngine.hasPaintedGrid(nodesObj)) {
            GraphLayoutEngine._applyGridLayout(nodesObj, nodesDS);
            return 'grid';
        }

        const rooms = worldState.areas || {};
        const roomNames = Object.keys(rooms).sort();
        if (roomNames.length === 0) return null;

        const nameToId = {};
        for (const [nodeId, nodeData] of Object.entries(nodesObj)) {
            if (nodeData.type === 'area' && nodeData.name) nameToId[nodeData.name] = nodeId;
        }

        const CARDINALS = { 'n':'north','ne':'northeast','e':'east','se':'southeast','s':'south','sw':'southwest','w':'west','nw':'northwest','u':'up','d':'down' };
        const normalizeCardinal = (cardinalStr) => {
            if (!cardinalStr) return '';
            const lowered = cardinalStr.toLowerCase().trim();
            return CARDINALS[lowered] || lowered;
        };
        const dirOffsets = { north:{x:0,y:-1}, south:{x:0,y:1}, east:{x:1,y:0}, west:{x:-1,y:0}, up:{x:0,y:-2}, down:{x:0,y:2}, northeast:{x:1,y:-1}, northwest:{x:-1,y:-1}, southeast:{x:1,y:1}, southwest:{x:-1,y:1} };

        // Build adjacency from exits
        const adj = {};
        roomNames.forEach(areaName => { adj[areaName] = {}; });
        roomNames.forEach(areaName => {
            const exits = rooms[areaName].exits || {};
            Object.entries(exits).forEach(([direction, exitData]) => {
                const target = typeof exitData === 'object' ? (exitData.target || exitData.targetAreaName || exitData.targetAreaId) : exitData;
                if (target && rooms[target]) {
                    const rawCardinal = exitData && exitData.cardinal ? exitData.cardinal : direction;
                    const cardinal = normalizeCardinal(rawCardinal);
                    if (cardinal && dirOffsets[cardinal]) {
                        adj[areaName][direction] = { target, cardinal };
                        const reverseCardinal = { north:'south', south:'north', east:'west', west:'east', up:'down', down:'up', northeast:'southwest', northwest:'southeast', southeast:'northwest', southwest:'northeast' }[cardinal];
                        if (reverseCardinal && !adj[target][reverseCardinal]) adj[target][reverseCardinal] = { target: areaName, cardinal: reverseCardinal };
                    }
                }
            });
        });

        // BFS to calculate anchor grid positions
        const placed = {}, grid = {};
        const seed = roomNames.find(areaName => Object.values(adj[areaName]).some(entry => entry.cardinal)) || roomNames[0];
        const queue = [seed];
        placed[seed] = true;
        grid[seed] = { x: 0, y: 0 };
        let head = 0;
        while (head < queue.length) {
            const current = queue[head++], position = grid[current];
            Object.values(adj[current]).forEach(entry => {
                if (placed[entry.target]) return;
                const offset = dirOffsets[entry.cardinal];
                if (!offset) return;
                grid[entry.target] = { x: position.x + offset.x, y: position.y + offset.y };
                placed[entry.target] = true;
                queue.push(entry.target);
            });
        }

        // Calculate bounding box and scale to pixel positions
        const cellW = 500, cellH = 350, padX = 150, padY = 150;
        const keys = Object.keys(grid);
        if (keys.length === 0) return null;
        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = Infinity;
        keys.forEach(areaName => {
            const gridPos = grid[areaName];
            if (gridPos.x < minX) minX = gridPos.x;
            if (gridPos.x > maxX) maxX = gridPos.x;
            if (gridPos.y < minY) minY = gridPos.y;
            if (gridPos.y > maxY) maxY = gridPos.y;
        });

        // Calculate anchor positions (where rooms SHOULD be based on cardinals)
        const anchors = {};
        keys.forEach(areaName => {
            const nodeId = nameToId[areaName];
            if (nodeId) {
                anchors[nodeId] = {
                    x: (grid[areaName].x - minX) * cellW + padX,
                    y: (grid[areaName].y - minY) * cellH + padY
                };
            }
        });

        // Build node updates with anchor positions as targets
        const areaUpdates = [];
        keys.forEach(areaName => {
            const nodeId = nameToId[areaName];
            if (!nodeId || !nodesDS.get(nodeId)) return;
            const anchor = anchors[nodeId];
            areaUpdates.push({
                id: nodeId,
                x: anchor.x,
                y: anchor.y,
                // Start at anchor position, physics will settle them
                physics: true,
                fixed: { x: false, y: false }
            });
        });

        roomNames.forEach(areaName => {
            if (!placed[areaName]) {
                const nodeId = nameToId[areaName];
                if (nodeId && nodesDS.get(nodeId)) {
                    areaUpdates.push({ id: nodeId, physics: true, fixed: { x: false, y: false } });
                }
            }
        });

        // Way nodes: midpoint between connected rooms
        const wayUpdates = [];
        const edges = worldState.graph?.edges || [];
        for (const [wayId, wayNode] of Object.entries(nodesObj)) {
            if (wayNode.type !== 'way') continue;
            if (!nodesDS.get(wayId)) continue;

            const connectedRooms = [];
            edges.filter(e => e.type === 'connection').forEach(edge => {
                if (edge.source === wayId || edge.target === wayId) {
                    const otherId = edge.source === wayId ? edge.target : edge.source;
                    const otherNode = nodesObj[otherId];
                    if (otherNode && otherNode.type === 'area') {
                        connectedRooms.push(otherNode);
                    }
                }
            });

            if (connectedRooms.length < 2) continue;

            const anchorA = anchors[connectedRooms[0].id];
            const anchorB = anchors[connectedRooms[1].id];
            if (!anchorA || !anchorB) continue;

            wayUpdates.push({
                id: wayId,
                x: (anchorA.x + anchorB.x) / 2,
                y: (anchorA.y + anchorB.y) / 2,
                physics: true,
                fixed: { x: false, y: false }
            });
        }

        // Item/character positions near parent room (with physics)
        const graphEdges = worldState.graph?.edges || [];
        const areaToItems = {};
        const areaToChars = {};
        for (const edge of graphEdges) {
            if (edge.type !== 'in') continue;
            const sourceNode = nodesObj[edge.source];
            const targetNode = nodesObj[edge.target];
            if (!sourceNode || !targetNode || targetNode.type !== 'area') continue;
            if (sourceNode.type === 'item') {
                if (!areaToItems[edge.target]) areaToItems[edge.target] = [];
                areaToItems[edge.target].push(edge.source);
            } else if (sourceNode.type === 'character') {
                if (!areaToChars[edge.target]) areaToChars[edge.target] = [];
                areaToChars[edge.target].push(edge.source);
            }
        }

        const looseUpdates = [];
        for (const [areaId, itemIds] of Object.entries(areaToItems)) {
            const anchor = anchors[areaId];
            if (!anchor) continue;
            const baseX = anchor.x;
            const baseY = anchor.y + 150;
            const totalCols = Math.min(itemIds.length, 6);
            itemIds.forEach((itemId, index) => {
                if (!nodesDS.get(itemId)) return;
                const col = index % totalCols;
                const row = Math.floor(index / totalCols);
                looseUpdates.push({
                    id: itemId,
                    x: baseX + col * 80 - ((totalCols > 1 ? ((totalCols - 1) * 80) / 2 : 0)),
                    y: baseY + row * 55,
                    physics: true,
                    fixed: { x: false, y: false }
                });
            });
        }

        for (const [areaId, charIds] of Object.entries(areaToChars)) {
            const anchor = anchors[areaId];
            if (!anchor) continue;
            const baseX = anchor.x + 250;
            const baseY = anchor.y;
            const totalCols = Math.min(charIds.length, 3);
            charIds.forEach((charId, index) => {
                if (!nodesDS.get(charId)) return;
                const col = index % totalCols;
                const row = Math.floor(index / totalCols);
                looseUpdates.push({
                    id: charId,
                    x: baseX + col * 100 - ((totalCols > 1 ? ((totalCols - 1) * 100) / 2 : 0)),
                    y: baseY + row * 70,
                    physics: true,
                    fixed: { x: false, y: false }
                });
            });
        }

        // Apply all updates. A node the user froze ("Physics enabled" off in the
        // inspector) is left exactly as it is: its position is theirs and its
        // physics is already off, so re-anchoring it here is what made a placed
        // way snap back and get pushed again (bug report, task-485 follow-up).
        const frozen = (id) => {
            const props = (nodesObj[id] || {}).properties || {};
            return props.central_gravity_enabled === false;
        };
        nodesDS.update([...areaUpdates, ...wayUpdates, ...looseUpdates].filter(u => u && !frozen(u.id)));

        // Enable hybrid physics: force-directed with anchor attraction
        // - Strong repulsion between area nodes (prevent overlap)
        // - Edge springs (keep connected rooms close)
        // - Nodes start at anchor positions and settle naturally
        graphManager.network.setOptions({
            physics: {
                enabled: true,
                barnesHut: {
                    gravitationalConstant: -3000,
                    centralGravity: 0.2,
                    springLength: 300,
                    springConstant: 0.04,
                    damping: 0.45,
                    avoidOverlap: 0.6
                },
                maxVelocity: 50,
                minVelocity: 0.75,
                solver: 'barnesHut',
                stabilization: {
                    enabled: true,
                    iterations: 200,
                    updateInterval: 25,
                    onlyDynamicEdges: false,
                    fit: false
                }
            }
        });

        const physicsBtn = document.getElementById('btn-physics');
        if (physicsBtn) physicsBtn.textContent = '⏸ Physics';

        setTimeout(() => {
            graphManager.network.redraw();
            graphManager.network.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
        }, 100);
        return 'cardinal';
    },

    /**
     * Engine units per painted cell — mirrors `CELL_CANVAS_UNITS`
     * (`engine/world_compile.py`). The compiler stores `cell * 40`, so a node's
     * stored `x`/`y` is a cell index times this.
     */
    PAINT_UNITS_PER_CELL: 40,

    /**
     * Canvas px between adjacent painted cells — the map's spacing/margin.
     *
     * The painter paints on a 1-cell lattice, so spacing is the whole scale: 40
     * means an area every 40px with the way at the 20px midpoint — "20px to the
     * way, 20px to the next area". Stored coords are absolute engine units, so
     * we never use them raw; we treat the cell *lattice* as relative and apply
     * this margin. Override with `config.graphMapSpacing`.
     * @returns {number}
     */
    mapSpacing() {
        if (typeof config !== 'undefined' && config) {
            const value = Number(config.graphMapSpacing);
            if (value > 0) return value;
        }
        return 40;
    },

    /** Canvas px per painted *unit*, for `gridPosition` (spacing / 40). */
    get GRID_SCALE() {
        return GraphLayoutEngine.mapSpacing() / GraphLayoutEngine.PAINT_UNITS_PER_CELL;
    },

    /**
     * True when the payload has painted-grid areas (`properties.cell`), i.e. it
     * came from the WorldPainter compiler rather than hand authoring.
     * @param {Object} nodesObj
     * @returns {boolean}
     */
    hasPaintedGrid(nodesObj) {
        for (const node of Object.values(nodesObj || {})) {
            if (node && node.type === 'area' && node.properties && node.properties.cell) {
                return true;
            }
        }
        return false;
    },

    /**
     * Painted coords → canvas position. Pure, so it is unit-tested.
     * @param {Object} properties - node properties with numeric x/y
     * @param {number} [scale] - defaults to GRID_SCALE
     * @returns {{x:number,y:number}|null}
     */
    gridPosition(properties, scale) {
        const p = properties || {};
        const s = typeof scale === 'number' ? scale : GraphLayoutEngine.GRID_SCALE;
        if (typeof p.x !== 'number' || typeof p.y !== 'number') return null;
        return { x: p.x * s, y: p.y * s };
    },

    /**
     * The scope a compiled node belongs to. Areas and ways both store
     * `world_scope_id`; a gateway also carries `generated.scope_id`.
     * @param {Object} node
     * @returns {string|null}
     */
    nodeScopeId(node) {
        const props = (node || {}).properties || {};
        return props.world_scope_id
            || (props.generated && props.generated.scope_id)
            || null;
    },

    /**
     * A node's map offset in canvas px, from the per-scope offset table.
     *
     * The offset is stored in **cells** (task-523), so it is multiplied by the
     * map spacing — the same pitch `gridPosition` scales painted cells to. Pure
     * apart from the default table, so it is unit-tested.
     * @param {Object} node
     * @param {Object} [offsets] - `{scopeId: {x,y}}`; defaults to graphManager's
     * @param {number} [spacing] - px per cell; defaults to mapSpacing()
     * @returns {{x:number,y:number}}
     */
    offsetPxFor(node, offsets, spacing) {
        const table = offsets || ((typeof graphManager !== 'undefined' && graphManager)
            ? graphManager._scopeOffsets : null) || {};
        const scopeId = GraphLayoutEngine.nodeScopeId(node);
        const off = scopeId ? table[scopeId] : null;
        const gap = typeof spacing === 'number' ? spacing : GraphLayoutEngine.mapSpacing();
        const x = off && isFinite(Number(off.x)) ? Number(off.x) : 0;
        const y = off && isFinite(Number(off.y)) ? Number(off.y) : 0;
        return { x: x * gap, y: y * gap };
    },

    /**
     * Painted coords + this node's scope offset → canvas position. Pure.
     * @param {Object} properties
     * @param {Object} node
     * @param {Object} [offsets]
     * @param {number} [scale]
     * @returns {{x:number,y:number}|null}
     */
    scopedGridPosition(properties, node, offsets, scale) {
        const base = GraphLayoutEngine.gridPosition(properties, scale);
        if (!base) return null;
        const off = GraphLayoutEngine.offsetPxFor(node, offsets);
        return { x: base.x + off.x, y: base.y + off.y };
    },

    /**
     * Position updates for a painted map: every node with coords at its painted
     * cell (plus its scope's map offset, task-523), and items/characters held in
     * an area beside that area. Shared by the initial layout and the live
     * zone-drag refresh, so both place things identically.
     * @param {Object} nodesObj
     * @param {Object} nodesDS
     * @param {Object} [offsets]
     * @returns {Array<Object>} vis DataSet node updates
     */
    _gridUpdates(nodesObj, nodesDS, offsets) {
        const updates = [];
        const placed = new Set();
        const anchors = {};

        for (const [id, node] of Object.entries(nodesObj)) {
            if (!nodesDS.get(id)) continue;
            const p = GraphLayoutEngine.scopedGridPosition(
                (node || {}).properties, node, offsets);
            if (!p) continue;
            updates.push({ id, x: p.x, y: p.y, physics: false, fixed: { x: false, y: false } });
            placed.add(id);
            if (node.type === 'area') anchors[id] = p;
        }

        // Items/characters without their own coords sit beside their area.
        const edges = (worldState.graph && worldState.graph.edges) || [];
        const heldIn = {};
        for (const edge of edges) {
            if (edge.type !== 'in') continue;
            const source = nodesObj[edge.source];
            const target = nodesObj[edge.target];
            if (!source || !target || target.type !== 'area') continue;
            (heldIn[edge.target] = heldIn[edge.target] || []).push(edge.source);
        }
        for (const [areaId, ids] of Object.entries(heldIn)) {
            const anchor = anchors[areaId];
            if (!anchor) continue;
            ids.forEach((id, index) => {
                if (placed.has(id) || !nodesDS.get(id)) return;
                const isChar = (nodesObj[id] || {}).type === 'character';
                updates.push({
                    id,
                    x: anchor.x + (isChar ? 130 : -70) + (index % 4) * 45,
                    y: anchor.y + (isChar ? 0 : 70) + Math.floor(index / 4) * 45,
                    physics: false,
                    fixed: { x: false, y: false },
                });
            });
        }
        return updates;
    },

    /**
     * Lay the graph out exactly as painted: areas and ways at their stored cell
     * positions (plus each scope's map offset), items/characters beside the area
     * that holds them. Physics is left off — this is a map, not a simulation.
     * @param {Object} nodesObj
     * @param {Object} nodesDS - vis DataSet
     * @param {Object} [offsets] - `{scopeId: {x,y}}` cells; defaults to graphManager
     */
    _applyGridLayout(nodesObj, nodesDS, offsets) {
        const frozen = (id) =>
            (((nodesObj[id] || {}).properties || {}).central_gravity_enabled === false);
        const updates = GraphLayoutEngine._gridUpdates(nodesObj, nodesDS, offsets)
            .filter((u) => u && !frozen(u.id));
        nodesDS.update(updates);
        graphManager.network.setOptions({ physics: { enabled: false } });
        // Clear the flag too: the caller re-enables physics from this flag after
        // the load, so setting only the button text left physics coming back on.
        graphManager._physicsEnabled = false;
        const physicsBtn = document.getElementById('btn-physics');
        if (physicsBtn) physicsBtn.textContent = '▶ Physics';
        setTimeout(() => {
            graphManager.network.redraw();
            graphManager.network.fit({ animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
        }, 60);
    },

    /**
     * Re-place painted nodes after a zone offset changed, **without** refitting
     * the camera — a live drag must keep the viewport still. Returns the number
     * of nodes moved.
     * @param {Object} [nodesObj] - defaults to graphManager._graphNodesObj
     * @param {Object} [offsets] - defaults to graphManager._scopeOffsets
     * @returns {number}
     */
    refreshGridLayout(nodesObj, offsets) {
        if (!graphManager.network) return 0;
        const nodesDS = graphManager.network.body && graphManager.network.body.data
            && graphManager.network.body.data.nodes;
        if (!nodesDS) return 0;
        const src = nodesObj || graphManager._graphNodesObj || {};
        const updates = GraphLayoutEngine._gridUpdates(src, nodesDS, offsets);
        if (!updates.length) return 0;
        nodesDS.update(updates);
        graphManager.network.redraw();
        return updates.length;
    }
};
