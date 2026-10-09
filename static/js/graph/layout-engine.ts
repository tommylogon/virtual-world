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
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
(window as unknown as { GraphLayoutEngine: unknown }).GraphLayoutEngine = {
    /**
     * Lay areas out for map mode. Returns which layout was used — `'grid'` when
     * the painted lattice was read, `'cardinal'` for the derived fallback, or
     * `null` when nothing was applied — so the caller can keep physics off for a
     * painted map (a grid is read, not simulated).
     * @param {Object} nodesObj
     * @returns {'grid'|'cardinal'|null}
     */
    applyCardinalLayout(nodesObj: Record<string, any>) {
        if (!graphManager.network) return null;
        const nodesDS = graphManager.network.body.data.nodes;
        if (!nodesDS) return null;

        // Painted grid → exact map, no guessing and no physics.
        if (window.GraphLayoutEngine.hasPaintedGrid(nodesObj)) {
            window.GraphLayoutEngine._applyGridLayout(nodesObj, nodesDS);
            return 'grid';
        }

        const rooms: Record<string, any> = worldState.areas || {};
        const roomNames = Object.keys(rooms).sort();
        if (roomNames.length === 0) return null;

        const nameToId: Record<string, string> = {};
        for (const [nodeId, nodeData] of Object.entries<any>(nodesObj)) {
            if (nodeData.type === 'area' && nodeData.name) nameToId[nodeData.name] = nodeId;
        }

        const CARDINALS: Record<string, string> = { 'n':'north','ne':'northeast','e':'east','se':'southeast','s':'south','sw':'southwest','w':'west','nw':'northwest','u':'up','d':'down' };
        const normalizeCardinal = (cardinalStr: string) => {
            if (!cardinalStr) return '';
            const lowered = cardinalStr.toLowerCase().trim();
            return CARDINALS[lowered] || lowered;
        };
        const dirOffsets: Record<string, { x: number; y: number }> = { north:{x:0,y:-1}, south:{x:0,y:1}, east:{x:1,y:0}, west:{x:-1,y:0}, up:{x:0,y:-2}, down:{x:0,y:2}, northeast:{x:1,y:-1}, northwest:{x:-1,y:-1}, southeast:{x:1,y:1}, southwest:{x:-1,y:1} };

        // Build adjacency from exits
        const adj: Record<string, Record<string, any>> = {};
        roomNames.forEach((areaName: string) => { adj[areaName] = {}; });
        roomNames.forEach((areaName: string) => {
            const exits: Record<string, any> = rooms[areaName].exits || {};
            Object.entries(exits).forEach(([direction, exitData]: [string, any]) => {
                const target = typeof exitData === 'object' ? (exitData.target || exitData.targetAreaName || exitData.targetAreaId) : exitData;
                if (target && rooms[target]) {
                    const rawCardinal = exitData && exitData.cardinal ? exitData.cardinal : direction;
                    const cardinal = normalizeCardinal(rawCardinal);
                    if (cardinal && dirOffsets[cardinal]) {
                        adj[areaName][direction] = { target, cardinal };
                        const reverseCardinal = ({ north:'south', south:'north', east:'west', west:'east', up:'down', down:'up', northeast:'southwest', northwest:'southeast', southeast:'northwest', southwest:'northeast' } as Record<string, string>)[cardinal];
                        if (reverseCardinal && !adj[target][reverseCardinal]) adj[target][reverseCardinal] = { target: areaName, cardinal: reverseCardinal };
                    }
                }
            });
        });

        // BFS to calculate anchor grid positions
        const placed: Record<string, boolean> = {}, grid: Record<string, { x: number; y: number }> = {};
        const seed = roomNames.find((areaName: string) => Object.values(adj[areaName]).some(entry => entry.cardinal)) || roomNames[0];
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
        keys.forEach((areaName: string) => {
            const gridPos = grid[areaName];
            if (gridPos.x < minX) minX = gridPos.x;
            if (gridPos.x > maxX) maxX = gridPos.x;
            if (gridPos.y < minY) minY = gridPos.y;
            if (gridPos.y > maxY) maxY = gridPos.y;
        });

        // Calculate anchor positions (where rooms SHOULD be based on cardinals)
        const anchors: Record<string, { x: number; y: number }> = {};
        keys.forEach((areaName: string) => {
            const nodeId = nameToId[areaName];
            if (nodeId) {
                anchors[nodeId] = {
                    x: (grid[areaName].x - minX) * cellW + padX,
                    y: (grid[areaName].y - minY) * cellH + padY
                };
            }
        });

        // Build node updates with anchor positions as targets
        const areaUpdates: any[] = [];
        keys.forEach((areaName: string) => {
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

        roomNames.forEach((areaName: string) => {
            if (!placed[areaName]) {
                const nodeId = nameToId[areaName];
                if (nodeId && nodesDS.get(nodeId)) {
                    areaUpdates.push({ id: nodeId, physics: true, fixed: { x: false, y: false } });
                }
            }
        });

        // Way nodes: midpoint between connected rooms
        const wayUpdates: any[] = [];
        const edges = worldState.graph?.edges || [];
        for (const [wayId, wayNode] of Object.entries<any>(nodesObj)) {
            if (wayNode.type !== 'way') continue;
            if (!nodesDS.get(wayId)) continue;

            const connectedRooms: any[] = [];
            edges.filter((e: any) => e.type === 'connection').forEach((edge: any) => {
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
        const areaToItems: Record<string, string[]> = {};
        const areaToChars: Record<string, string[]> = {};
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

        const looseUpdates: any[] = [];
        for (const [areaId, itemIds] of Object.entries<string[]>(areaToItems)) {
            const anchor = anchors[areaId];
            if (!anchor) continue;
            const baseX = anchor.x;
            const baseY = anchor.y + 150;
            const totalCols = Math.min(itemIds.length, 6);
            itemIds.forEach((itemId: string, index: number) => {
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

        for (const [areaId, charIds] of Object.entries<string[]>(areaToChars)) {
            const anchor = anchors[areaId];
            if (!anchor) continue;
            const baseX = anchor.x + 250;
            const baseY = anchor.y;
            const totalCols = Math.min(charIds.length, 3);
            charIds.forEach((charId: string, index: number) => {
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
        const frozen = (id: string) => {
            const props = (nodesObj[id] || {}).properties || {};
            return props.central_gravity_enabled === false;
        };
        nodesDS.update([...areaUpdates, ...wayUpdates, ...looseUpdates].filter((u: any) => u && !frozen(u.id)));

        // Enable hybrid physics: force-directed with anchor attraction
        // - Strong repulsion between area nodes (prevent overlap)
        // - Edge springs (keep connected rooms close)
        // - Nodes start at anchor positions and settle naturally
        graphManager.network.setOptions({
            physics: {
                enabled: true,
                barnesHut: {
                    gravitationalConstant: -3000,
                    // 0 = no pull toward the origin, same as buildOptions().
                    centralGravity: 0,
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

        if (window.GraphToolbar) GraphToolbar.syncAll();

        setTimeout(() => {
            graphManager.network.redraw();
            graphManager.network.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
        }, 100);
        return 'cardinal';
    },

    /**
     * Canvas px between adjacent painted cells — the map's spacing knob.
     *
     * The pitch moves areas apart; it no longer sizes the marks (task-748). When
     * the user has not set one, it is the mark envelope (see
     * `markEnvelopePitch`), so a fresh map is spaced so its marks cannot overlap.
     * Override with `config.graphMapSpacing`.
     * @returns {number}
     */
    mapSpacing() {
        if (typeof config !== 'undefined' && config) {
            const value = Number(config.graphMapSpacing);
            if (value > 0) return value;
        }
        return window.GraphLayoutEngine.markEnvelopePitch();
    },

    /**
     * Mark sizes in **absolute px**, the same at every pitch (task-748).
     *
     * A mark is a thing drawn on the map, not a fraction of the layout cell. The
     * pitch moves the areas apart; the marks are sized by the node-size / item /
     * character controls. The previous model made every mark a fraction of the
     * pitch (`MARK_FRACTION`), so the one slider both spread the rooms *and*
     * inflated every marker — raising the spacing from 40 to 660 grew a way node
     * from 10px to 172px. These numbers are now the *input* the pitch is derived
     * from (`markEnvelopePitch`), not the output.
     */
    MAP_MARK_PX: {
        areaEdge: 130,   // max card side, incl. padding
        areaPad: 8,      // card padding, each side
        font: 14,        // area-name font
        item: 30,
        way: 26,
        character: 42,
    },

    /** Clear space left between the largest card and the way beside it, in px. */
    MARK_ENVELOPE_GAP: 20,

    /**
     * The smallest pitch at which the marks cannot overlap: two area cards a cell
     * apart with a way node on the midpoint between them. The binding case is
     * `card + way + gap` — a half-cell must hold a half-card and a half-way — so
     * this is a **constant** for a given mark configuration, independent of the
     * canvas, the painted extent and the reference image (task-748).
     * @returns {number} px per cell
     */
    markEnvelopePitch() {
        const px = window.GraphLayoutEngine.MAP_MARK_PX as Record<string, number>;
        const network = (window as unknown as { GraphNetwork?: { nodeSizeScale?: () => number } }).GraphNetwork;
        const ns = (network && typeof network.nodeSizeScale === 'function') ? network.nodeSizeScale() : 1;
        return Math.round((px.areaEdge + px.way) * ns + window.GraphLayoutEngine.MARK_ENVELOPE_GAP * ns);
    },

    /** Mark diameter in px (fixed; the node-size multiplier is applied by the caller). */
    markSize(type: string) {
        const px = window.GraphLayoutEngine.MAP_MARK_PX as Record<string, number>;
        return px[type] || px.item;
    },

    /** Area-name font size in px (fixed). */
    markFontPx() {
        return (window.GraphLayoutEngine.MAP_MARK_PX as Record<string, number>).font;
    },

    /** Card padding in px (fixed). */
    markCardPad() {
        return (window.GraphLayoutEngine.MAP_MARK_PX as Record<string, number>).areaPad;
    },

    /** Card max side in px (fixed). */
    markCardMax() {
        return (window.GraphLayoutEngine.MAP_MARK_PX as Record<string, number>).areaEdge;
    },

    /**
     * Where loose nodes (items, characters) sit beside the painted area that
     * holds them, in **cells of the current pitch**.
     *
     * These were absolute pixels tuned at the 40px default, so on a 260px map an
     * item landed practically on top of its room. As cell multiples they look
     * identical at the default and scale everywhere else — the same geometry the
     * WorldPainter draws, so "beside the room" means one thing at any pitch.
     */
    mapBesideOffsets() {
        const pitch = window.GraphLayoutEngine.mapSpacing();
        return {
            itemX: -1.75 * pitch, itemY: 1.75 * pitch,
            charX: 3.25 * pitch, charY: 0,
            step: 1.125 * pitch,
            perRow: 4,
        };
    },

    /**
     * True when the payload has painted-grid areas (`properties.cell`), i.e. it
     * came from the WorldPainter compiler rather than hand authoring.
     * @param {Object} nodesObj
     * @returns {boolean}
     */
    hasPaintedGrid(nodesObj: Record<string, any> | null | undefined) {
        for (const node of Object.values<any>(nodesObj || {})) {
            if (node && node.type === 'area' && node.properties && node.properties.cell) {
                return true;
            }
        }
        return false;
    },

    /**
     * The default map pitch: the **mark envelope** (see `markEnvelopePitch`) —
     * how much room the marks need, not how many cells fit the canvas and not
     * how wide the world is.
     *
     * Returns `null` when nothing is painted, so a hand-authored world keeps
     * whatever pitch the user has. This is the *default*; the toolbar's stepper
     * is the override (see `graphManager.setMapSpacing`).
     *
     * History (task-748): the first version aimed `AUTO_SPAN_PX` of canvas at the
     * painted extent; the next aimed `AUTO_CELLS_ACROSS` cells at the viewport.
     * Both made the pitch a function of something other than the marks, and both
     * clamped into a band that fought the intent (a 240 floor on a wide world, a
     * 40 floor on a small pane). The envelope needs no clamp: it *is* the value
     * that keeps the invariant "no overlap, a way fits between two areas".
     *
     * @param {Object} nodesObj - the nodes being laid out
     * @param {{w:number,h:number}} [viewSize] - ignored; kept for call compatibility
     * @returns {number|null}
     */
    autoMapSpacing(nodesObj: Record<string, any>, viewSize?: { w: number; h: number }) {
        if (!window.GraphLayoutEngine.hasPaintedGrid(nodesObj)) return null;
        return window.GraphLayoutEngine.markEnvelopePitch();
    },

    /**
     * The map canvas size in px. No longer feeds the pitch (task-748) - kept for
     * diagnostics and any other viewer that wants the live pane size.
     * @returns {{w:number,h:number}}
     */
    viewportSize() {
        const net = (typeof graphManager !== 'undefined' && graphManager && (graphManager as { network?: any }).network)
            ? (graphManager as { network?: any }).network : null;
        const el = (net && net.body && net.body.container)
            ? net.body.container
            : (typeof document !== 'undefined' ? document.getElementById('graph-container') : null);
        const w = el ? el.clientWidth : 0;
        const h = el ? el.clientHeight : 0;
        return { w: w || 1200, h: h || 800 };
    },

    /**
     * A painted **cell** → canvas position: `cell × pitch`. Pure, so it is
     * unit-tested. The cell is the node's local coordinate; the renderer never
     * touches the compiler's `cell × 40` engine units, so that constant (and the
     * `GRID_SCALE` derived from it) no longer exists here.
     * @param {{x:number,y:number}} cell
     * @param {number} [pitch] - px per cell; defaults to mapSpacing()
     * @returns {{x:number,y:number}|null}
     */
    gridPosition(cell: any, pitch?: number) {
        const p = cell || {};
        const s = typeof pitch === 'number' ? pitch : window.GraphLayoutEngine.mapSpacing();
        if (typeof p.x !== 'number' || typeof p.y !== 'number') return null;
        return { x: p.x * s, y: p.y * s };
    },

    /**
     * The scope a compiled node belongs to. Areas and ways both store
     * `world_scope_id`; a gateway also carries `generated.scope_id`.
     * @param {Object} node
     * @returns {string|null}
     */
    nodeScopeId(node: any) {
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
    offsetPxFor(node: any, offsets?: Record<string, { x: number; y: number }> | null, spacing?: number) {
        const table: Record<string, { x: number; y: number }> = offsets || ((typeof graphManager !== 'undefined' && graphManager)
            ? graphManager._scopeOffsets : null) || {};
        const scopeId = window.GraphLayoutEngine.nodeScopeId(node);
        const off = scopeId ? table[scopeId] : null;
        const gap = typeof spacing === 'number' ? spacing : window.GraphLayoutEngine.mapSpacing();
        const x = off && isFinite(Number(off.x)) ? Number(off.x) : 0;
        const y = off && isFinite(Number(off.y)) ? Number(off.y) : 0;
        return { x: x * gap, y: y * gap };
    },

    /**
     * A painted node's **cell** plus its scope offset → canvas position. Pure.
     * @param {Object} properties - node properties carrying a `cell`
     * @param {Object} node
     * @param {Object} [offsets]
     * @param {number} [pitch] - px per cell
     * @returns {{x:number,y:number}|null}
     */
    scopedGridPosition(properties: any, node: any, offsets?: Record<string, { x: number; y: number }> | null, pitch?: number) {
        const base = window.GraphLayoutEngine.gridPosition((properties || {}).cell, pitch);
        if (!base) return null;
        const off = window.GraphLayoutEngine.offsetPxFor(node, offsets, pitch);
        return { x: base.x + off.x, y: base.y + off.y };
    },

    /**
     * Whether the *author* placed this node rather than letting the solver move
     * it: the inspector's "Physics enabled" off (`central_gravity_enabled:
     * false`) or an explicit `layout_static: true`, which are the same intent.
     *
     * Delegates to `GraphRelativeLayout.isStatic` so the layout and the derived
     * seed agree on one rule instead of two copies of it that can drift apart.
     * @param {Object} node
     * @returns {boolean}
     */
    isFrozen(node: any) {
        if (typeof window.GraphRelativeLayout !== 'undefined' && window.GraphRelativeLayout
                && typeof window.GraphRelativeLayout.isStatic === 'function') {
            return window.GraphRelativeLayout.isStatic(node);
        }
        const props = (node || {}).properties || {};
        return props.central_gravity_enabled === false || props.layout_static === true;
    },

    /**
     * Where a way with no stored position of its own belongs on the
     * painted map (task-723): between the areas it connects, at the
     * current pitch.
     *
     * A way the compiler mints carries no `cell`/`x`/`y` — only the
     * areas it joins — so its position is derived from theirs. Two
     * rooms: the way belongs in the *gap* between the rooms' drawn
     * marks, not on a mark. A mark spans about half a cell (`pitch/2`)
     * from its anchor along the connecting edge, so the gap runs from
     * a half-cell in from each room and the way sits at the centre of
     * that gap — for two rooms a cell apart (the painted lattice), the
     * segment midpoint, a half-cell from each: the "20px to the way,
     * 20px to the next area" geometry the pitch is built around. Three
     * or more (a junction): the centroid, the balanced point between
     * all of them. Pure, so the placement is unit-tested at any pitch.
     * @param {Array<{x:number,y:number}>} anchors - the way's areas' map positions
     * @param {number} pitch - px per cell (mapSpacing)
     * @returns {{x:number,y:number}|null} null when there is nothing to place by
     */
    wayMapPosition(anchors: Array<{ x: number; y: number }> | null, pitch: number): { x: number; y: number } | null {
        if (!anchors || !anchors.length) return null;
        if (anchors.length === 1) return { x: anchors[0].x, y: anchors[0].y };
        if (anchors.length === 2) {
            const a = anchors[0];
            const b = anchors[1];
            const dx = b.x - a.x;
            const dy = b.y - a.y;
            const d = Math.hypot(dx, dy);
            const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
            if (!(d > 0)) return mid;
            // Gap endpoints along the connecting edge: a half-cell in
            // from each room. Clamped to the segment's midpoint when
            // the rooms are closer than a cell (no gap exists then, and
            // the midpoint is the nearest point to both).
            const mark = pitch * 0.5;
            const ux = dx / d;
            const uy = dy / d;
            const near = Math.min(mark, d / 2);
            const far = Math.max(d - mark, d / 2);
            const t = (near + far) / 2;
            return { x: a.x + ux * t, y: a.y + uy * t };
        }
        let cx = 0;
        let cy = 0;
        for (const a of anchors) {
            cx += a.x;
            cy += a.y;
        }
        return { x: cx / anchors.length, y: cy / anchors.length };
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
    _gridUpdates(nodesObj: Record<string, any>, nodesDS: any, offsets?: Record<string, { x: number; y: number }> | null) {
        const updates: any[] = [];
        const placed = new Set<string>();
        const anchors: Record<string, { x: number; y: number }> = {};

        const edges = (worldState.graph && worldState.graph.edges) || [];
        // way id -> the areas it joins, so a coordinate-less way can be placed
        // from its rooms rather than from a stale saved position.
        const wayAreas: Record<string, string[]> = {};
        for (const edge of edges) {
            if (edge.type !== 'connection') continue;
            const source = nodesObj[edge.source];
            const target = nodesObj[edge.target];
            if (!source || !target) continue;
            if (source.type === 'way' && target.type === 'area') {
                (wayAreas[edge.source] = wayAreas[edge.source] || []).push(edge.target);
            } else if (target.type === 'way' && source.type === 'area') {
                (wayAreas[edge.target] = wayAreas[edge.target] || []).push(edge.source);
            }
        }
        const isPaintedArea = (id: string) => {
            const room = nodesObj[id];
            return !!room && window.GraphLayoutEngine.hasPaintedCoords((room.properties) || {});
        };

        // Items/characters held in an area sit beside it, so the holder map is
        // built *before* the main loop: a loose node's stale canvas `x`/`y` must
        // not be used when its room is painted — the saved canvas frame and the
        // cell frame disagree, which stranded the node (and its `in` edge)
        // thousands of px from the room. Such a node is deferred to the beside
        // pass below instead of being placed from its `x`/`y`.
        const heldIn: Record<string, string[]> = {};
        const holderOf: Record<string, string> = {};
        for (const edge of edges) {
            if (edge.type !== 'in') continue;
            const source = nodesObj[edge.source];
            const target = nodesObj[edge.target];
            if (!source || !target || target.type !== 'area') continue;
            (heldIn[edge.target] = heldIn[edge.target] || []).push(edge.source);
            if (!holderOf[edge.source]) holderOf[edge.source] = edge.target;
        }

        for (const [id, node] of Object.entries<any>(nodesObj)) {
            if (!nodesDS.get(id)) continue;
            const props = (node || {}).properties || {};
            // Painted coords are the compiler's ENGINE units, so they are scaled
            // by the map pitch and translated by the scope's offset. A node the
            // author placed by hand — and every character/item, whose stored
            // position is already a CANVAS pixel — must be used verbatim:
            // re-scaling it compounds the pitch, and re-adding the offset walks
            // it further out on every single layout, so a node that is dragged
            // once creeps away from everything for good (bug-52's latent twin,
            // which the `cell`-only guard never closed for ways or characters).
            let p: { x: number; y: number } | null = null;
            if (window.GraphLayoutEngine.hasPaintedCoords(props)) {
                p = window.GraphLayoutEngine.scopedGridPosition(props, node, offsets);
            } else if (typeof props.x === 'number' && typeof props.y === 'number'
                    && isFinite(props.x) && isFinite(props.y)) {
                // A way whose room(s) are painted belongs *on the map*: a saved
                // graph-mode position is a different frame from the cell-scaled
                // map, so using it verbatim stranded the way thousands of px
                // from its rooms and strung every connection edge across empty
                // space (task-618). Such a way is placed from its rooms in the
                // pass below. A way with no painted room (a hand-placed way among
                // hand-placed rooms) keeps its canvas position, like any dragged
                // node (task-530).
                const rooms = wayAreas[id] || [];
                const belongsToMap = node.type === 'way' && rooms.some(isPaintedArea);
                // An item/character held in a painted area is part of the map too:
                // its saved canvas `x`/`y` is a different frame, so it is placed
                // beside its room (the pass below) rather than from the copy.
                const holder = holderOf[id];
                const looseHeldInPainted = (node.type === 'item' || node.type === 'character')
                    && !!holder && isPaintedArea(holder);
                if (!belongsToMap && !looseHeldInPainted) p = { x: props.x, y: props.y };
            }
            if (!p) continue;
            const isArea = node.type === 'area';
            const isWay = node.type === 'way';
            // Areas are pinned: the cells are the map, and the background art is
            // drawn to them. Ways are left free, so the solver pulls them in next
            // to their areas — the grid path places no way nodes of its own, so
            // without the solver they pile up wherever they were last saved and
            // every edge then crosses the whole map (task-530). Items and
            // characters are simulated too: with `centralGravity: 0` there is no
            // global field to drag a child off its parent, so their edge spring
            // holds them to the area that has them. An author-frozen node keeps
            // physics off.
            const frozen = window.GraphLayoutEngine.isFrozen(node);
            // An *area* and a *painted way* are both placed by the grid: their
            // cell (or their rooms' cells) is their map position, so they are
            // pinned there. Letting the solver "pull a painted way toward its
            // areas" moved it off its cell instead — the map frame and the
            // solver frame disagree — and strung the connection edges across
            // empty space (task-618). A way with no cell is either placed from
            // its rooms (pass below) or, if it has no painted rooms, left to the
            // solver like any other node (task-530).
            const pinnedToGrid = isArea || (isWay && window.GraphLayoutEngine.hasPaintedCoords(props));
            updates.push({
                id,
                x: p.x,
                y: p.y,
                // Everything else with its own position is simulated. A
                // hand-placed character reaches here, not the `heldIn` branch
                // below, so gating on `isWay` here would quietly leave a placed
                // character out of the solver.
                physics: !pinnedToGrid && !frozen,
                fixed: pinnedToGrid ? { x: true, y: true } : { x: false, y: false },
            });
            placed.add(id);
            if (isArea) anchors[id] = p;
        }

        // Items/characters without their own coords — and those held in a painted
        // area, whose saved canvas coords were deliberately skipped above — sit
        // beside the area that holds them.
        for (const [areaId, ids] of Object.entries<string[]>(heldIn)) {
            const anchor = anchors[areaId];
            if (!anchor) continue;
            const beside = window.GraphLayoutEngine.mapBesideOffsets();
            ids.forEach((id: string, index: number) => {
                if (placed.has(id) || !nodesDS.get(id)) return;
                const isChar = (nodesObj[id] || {}).type === 'character';
                updates.push({
                    id,
                    x: anchor.x + (isChar ? beside.charX : beside.itemX) + (index % beside.perRow) * beside.step,
                    y: anchor.y + (isChar ? beside.charY : beside.itemY)
                        + Math.floor(index / beside.perRow) * beside.step,
                    physics: true,
                    fixed: { x: false, y: false },
                });
            });
        }

        // Ways that belong to the map were skipped by the loop above;
        // place them between their rooms (task-723), in the same
        // scaled map frame.
        for (const [wayId, areaIds] of Object.entries<string[]>(wayAreas)) {
            if (placed.has(wayId) || !nodesDS.get(wayId)) continue;
            const rooms = areaIds.map((areaId: string) => anchors[areaId]).filter(Boolean);
            const pos = window.GraphLayoutEngine.wayMapPosition(rooms, window.GraphLayoutEngine.mapSpacing());
            if (!pos) continue;
            updates.push({ id: wayId, x: pos.x, y: pos.y, physics: false, fixed: { x: true, y: true } });
            placed.add(wayId);
        }
        return updates;
    },

    /**
     * Whether a node is *painted* — it carries a scope-relative `cell`, the map's
     * local coordinate — rather than being a node dragged to a canvas position.
     *
     * `cell` alone is the discriminator now. The compiler's `x`/`y`
     * (`cell × 40`) is redundant and no longer read here: a `cell` is the
     * position, so a painted node is placed from it whether or not an `x`/`y`
     * copy exists.
     */
    hasPaintedCoords(properties: any) {
        const cell = (properties || {}).cell;
        return !!cell && Number.isFinite(Number(cell.x)) && Number.isFinite(Number(cell.y));
    },

    /**
     * Lay the graph out exactly as painted: areas and ways at their stored cell
     * positions (plus each scope's map offset), items/characters beside the area
     * that holds them. Physics is left off — this is a map, not a simulation.
     * @param {Object} nodesObj
     * @param {Object} nodesDS - vis DataSet
     * @param {Object} [offsets] - `{scopeId: {x,y}}` cells; defaults to graphManager
     */
    _applyGridLayout(nodesObj: Record<string, any>, nodesDS: any, offsets?: Record<string, { x: number; y: number }> | null) {
        // A node the author froze ("Physics enabled" off in the inspector) is
        // normally left exactly where it is — that is the point of the flag. A
        // node with *painted* coordinates is the exception: its cell **is** its
        // position and the background art is drawn to those same cells, so
        // exempting it left the area at whatever pitch it was last saved at while
        // the art re-fitted to the current one — the map and its areas ended up on
        // two different grids (bug-52). The scenario builders default every area
        // to physics-off, so this hit any imported world rather than a choice.
        // The exemption still stands for a node with no painted coords.
        const frozen = (id: string) => {
            const props = ((nodesObj[id] || {}).properties) || {};
            return props.central_gravity_enabled === false
                && !window.GraphLayoutEngine.hasPaintedCoords(props);
        };
        const updates = window.GraphLayoutEngine._gridUpdates(nodesObj, nodesDS, offsets)
            .filter((u: any) => u && !frozen(u.id));
        nodesDS.update(updates);
        window.GraphNetwork.applyModePhysics(false);
        // The solver is off for this placement pass only. The user's preference
        // (`graphManager._physicsEnabled`) is deliberately NOT cleared here: the
        // load path restores it when the user wants physics in Map mode, so the
        // painted lattice is a starting point rather than a freeze.
        if (window.GraphToolbar) GraphToolbar.syncAll();
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
    refreshGridLayout(nodesObj?: Record<string, any> | null, offsets?: Record<string, { x: number; y: number }> | null) {
        if (!graphManager.network) return 0;
        const nodesDS = graphManager.network.body && graphManager.network.body.data
            && graphManager.network.body.data.nodes;
        if (!nodesDS) return 0;
        const src: Record<string, any> = nodesObj || graphManager._graphNodesObj || {};
        const updates = window.GraphLayoutEngine._gridUpdates(src, nodesDS, offsets);
        if (!updates.length) return 0;
        nodesDS.update(updates);
        graphManager.network.redraw();
        return updates.length;
    }
};

/**
 * Interface *merges* with the global `Window` and emits nothing, so it cannot
 * collide the way a `declare const` would (TS2451). The generated
 * `window members` block in types/globals.d.ts does not list
 * GraphLayoutEngine — the generator ran while this file was already renamed to
 * .ts — so without this the self-references below would not type-check.
 * `any` matches what main's block uses, so a future hand-added entry with the
 * same type still merges cleanly.
 */
interface Window {
    GraphLayoutEngine: any;
}
