window.GraphLayoutEngine = {
    applyCardinalLayout(nodesObj) {
        if (!graphManager.network) return;
        const nodesDS = graphManager.network.body.data.nodes;
        if (!nodesDS) return;

        const rooms = worldState.areas || {};
        const roomNames = Object.keys(rooms).sort();
        if (roomNames.length === 0) return;

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
        if (keys.length === 0) return;
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

        // Apply all updates
        nodesDS.update([...areaUpdates, ...wayUpdates, ...looseUpdates]);

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
    }
};
