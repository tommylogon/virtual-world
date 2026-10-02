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
        return window.GraphLayoutEngine.mapSpacing() / window.GraphLayoutEngine.PAINT_UNITS_PER_CELL;
    },

    /**
     * How much larger everything drawn on a painted map should be than in the
     * graph view, derived from the map pitch (bug-53).
     *
     * Node sizes were fixed pixel constants, so raising the pitch spread the
     * areas further apart while their boxes stayed the same size — the map
     * became specks on a field. 1 at the default 40px cell, so nothing changes
     * by default. The clamp matters in both directions: at pitch 260 the raw
     * ratio is 6.5, and a 6.5× box is not a readable map, it is a smear; at
     * pitch 20 a full-size box is wider than the cell it sits in, so the
     * drawing shrinks too (down to `MAP_SCALE_MIN`). *Spacing* follows the
     * pitch exactly (see :func:`mapSpacing`); only the drawing is clamped.
     */
    mapScale() {
        const spacing = window.GraphLayoutEngine.mapSpacing();
        if (!(spacing > 0)) return 1;
        const ratio = spacing / window.GraphLayoutEngine.PAINT_UNITS_PER_CELL;
        return Math.max(window.GraphLayoutEngine.MAP_SCALE_MIN, Math.min(2.5, ratio));
    },

    /** Floor for :func:`mapScale` — a dot-sized map is the limit, not a smear. */
    MAP_SCALE_MIN: 0.4,

    /**
     * Pixels per cell below which an area is drawn as a compact dot instead of a
     * named card (task-526).
     *
     * A card is `text width + 2 × 27px` of margin, and the text does **not** get
     * narrower with the pitch the way the box padding does — a 12-character room
     * name is ~85px of type at the default. So below roughly this pitch the cards
     * overlap into the "physics blob" the map used to look like, and the fix is
     * not a bigger pitch by hand but a *smaller mark*: the cell is the unit of
     * the map, and a dot fits in it at any pitch. Above it the cards are back and
     * the map reads as a set of places.
     *
     * Chosen so a small painted zone (the 6×8 goblin camp grid) stays on cards by
     * default, while the old 40px default — and anything auto-derived below it —
     * reads as topology instead of overlapping boxes.
     */
    MAP_CARD_MIN_PITCH: 140,

    /**
     * Draw compact dots rather than named cards?
     *
     * Only in the Map layout (checked by the caller): the graph view and Levels
     * keep their cards at every pitch, because those layouts are not a cell
     * lattice and have no overlap to solve.
     */
    mapCompact() {
        return window.GraphLayoutEngine.mapSpacing() < window.GraphLayoutEngine.MAP_CARD_MIN_PITCH;
    },

    /**
     * Dot diameter for the compact map, in px — tied to the **cell**, not to
     * `mapScale`, so a dot always sits inside its own cell whatever the pitch
     * (and stays visible when zoomed out on a 200×133 world).
     */
    mapDotSize() {
        const spacing = window.GraphLayoutEngine.mapSpacing();
        return Math.max(6, Math.min(28, spacing * 0.55));
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
     * The painted extent of a scope in cells: `{w, h}`, or `null` when nothing
     * carries a `cell`.
     *
     * Measured from the nodes themselves rather than from the scope record, so it
     * works on the subgraph the graph already has in hand and reflects what is
     * actually *drawn* (a 200×133 grid with 30 painted cells is 30 cells wide as
     * far as the reader is concerned).
     */
    paintedExtent(nodesObj: Record<string, any> | null | undefined) {
        let maxX = -1;
        let maxY = -1;
        for (const node of Object.values<any>(nodesObj || {})) {
            const cell = node && node.type === 'area' && (node.properties || {}).cell;
            if (!cell) continue;
            const x = Number(cell.x);
            const y = Number(cell.y);
            if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
            if (x > maxX) maxX = x;
            if (y > maxY) maxY = y;
        }
        if (maxX < 0 || maxY < 0) return null;
        return { w: maxX + 1, h: maxY + 1 };
    },

    /**
     * A map pitch that makes this scope readable without hand-tuning (task-526).
     *
     * The problem it solves: one global pitch cannot serve both a 6×8 camp and a
     * 200×133 world. Too tight and the cards overlap into a blob; too wide and a
     * small zone is a speck in a sea of empty canvas. So derive the pitch from the
     * painted extent — aim for the map to span roughly `AUTO_SPAN_PX`, then clamp.
     *
     * Returns `null` when there is nothing painted to fit, so the caller keeps
     * whatever pitch the user has. This is the *default*; the toolbar's stepper is
     * the override (see `graphManager.setMapSpacing`).
     *
     * @param {Object} nodesObj - the nodes being laid out
     * @param {number} [spanPx] - target on-screen width of the painted extent
     * @returns {number|null}
     */
    autoMapSpacing(nodesObj: Record<string, any>, spanPx?: number) {
        const extent = window.GraphLayoutEngine.paintedExtent(nodesObj);
        if (!extent) return null;
        const span = Number(spanPx) > 0 ? Number(spanPx) : window.GraphLayoutEngine.AUTO_SPAN_PX;
        const longest = Math.max(extent.w, extent.h);
        if (!(longest > 0)) return null;
        const raw = span / longest;
        const pitch = Math.max(window.GraphLayoutEngine.AUTO_SPACING_MIN,
            Math.min(window.GraphLayoutEngine.AUTO_SPACING_MAX, raw));
        // A tidy stepper value: multiples of 10 once the pitch is roomy enough
        // for the difference to be visible, multiples of 5 below that.
        const step = pitch >= 100 ? 10 : 5;
        return Math.round(pitch / step) * step;
    },

    /**
     * On-screen width a painted map should span, in px (task-526).
     *
     * The pitch is **derived**, not chosen: `AUTO_SPAN_PX / longest painted
     * extent in cells`, clamped, then snapped to a tidy stepper value (multiples
     * of 10 once the pitch is roomy). So one span serves both ends of the scale —
     * a 6×8 camp clamps to :data:`AUTO_SPACING_MAX` and gets roomy cards, a
     * 200×133 world clamps to :data:`AUTO_SPACING_MIN` and takes the whole map in
     * view as dots, and the middle (the Kraktooth world, 20×30) is the case the
     * span is tuned for: it lands well above :data:`MAP_CARD_MIN_PITCH` (140) so
     * the Map layout shows **place names** by default, because telling you where
     * a place is *called* is the one thing the map is for.
     *
     * **10000px** at the current clamps. Note the span is only hit *exactly* when
     * it divides evenly into `longest × step` — 10000 ÷ 30 is 333.3, so the pitch
     * snaps to 330 and a 20×30 world spans 9900. That ±1 stepper step is the
     * contract, not a defect: the snapping is deliberate, so the ladder is
     * readable in the stepper.
     */
    AUTO_SPAN_PX: 10000,

    /** Clamp for the derived pitch — never tighter than this, never wider. */
    AUTO_SPACING_MIN: 24,
    AUTO_SPACING_MAX: 600,

    /**
     * Painted coords → canvas position. Pure, so it is unit-tested.
     * @param {Object} properties - node properties with numeric x/y
     * @param {number} [scale] - defaults to GRID_SCALE
     * @returns {{x:number,y:number}|null}
     */
    gridPosition(properties: any, scale?: number) {
        const p = properties || {};
        const s = typeof scale === 'number' ? scale : window.GraphLayoutEngine.GRID_SCALE;
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
     * Painted coords + this node's scope offset → canvas position. Pure.
     * @param {Object} properties
     * @param {Object} node
     * @param {Object} [offsets]
     * @param {number} [scale]
     * @returns {{x:number,y:number}|null}
     */
    scopedGridPosition(properties: any, node: any, offsets?: Record<string, { x: number; y: number }> | null, scale?: number) {
        const base = window.GraphLayoutEngine.gridPosition(properties, scale);
        if (!base) return null;
        const off = window.GraphLayoutEngine.offsetPxFor(node, offsets);
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
                if (!belongsToMap) p = { x: props.x, y: props.y };
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

        // Items/characters without their own coords sit beside their area.
        const heldIn: Record<string, string[]> = {};
        for (const edge of edges) {
            if (edge.type !== 'in') continue;
            const source = nodesObj[edge.source];
            const target = nodesObj[edge.target];
            if (!source || !target || target.type !== 'area') continue;
            (heldIn[edge.target] = heldIn[edge.target] || []).push(edge.source);
        }
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

        // Ways that belong to the map were skipped by the loop above; place them
        // at the mean of their rooms' anchors, in the same scaled map frame.
        for (const [wayId, areaIds] of Object.entries<string[]>(wayAreas)) {
            if (placed.has(wayId) || !nodesDS.get(wayId)) continue;
            const rooms = areaIds.map((areaId: string) => anchors[areaId]).filter(Boolean);
            if (!rooms.length) continue;
            const x = rooms.reduce((sum: number, room: any) => sum + room.x, 0) / rooms.length;
            const y = rooms.reduce((sum: number, room: any) => sum + room.y, 0) / rooms.length;
            updates.push({ id: wayId, x, y, physics: false, fixed: { x: true, y: true } });
            placed.add(wayId);
        }
        return updates;
    },

    /**
     * Whether a node's coordinates are *painted* — i.e. the WorldPainter
     * compiler's `cell * 40` engine units, which the Map layout scales by the map
     * pitch — rather than a canvas position someone dragged.
     *
     * `cell` is the discriminator, not the numbers: the compiler and
     * `place_area` write `cell` next to the coords, while a node dragged in the
     * graph has only numeric `x`/`y`. Both look the same to a numeric check, and
     * treating a dragged node as painted would scale its position a second time.
     */
    hasPaintedCoords(properties: any) {
        const p = properties || {};
        return !!p.cell && typeof p.x === 'number' && typeof p.y === 'number'
            && isFinite(p.x) && isFinite(p.y);
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
