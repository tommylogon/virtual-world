/**
 * Unit tests for graph/layout-engine — the map layout's grid mode.
 *
 * The pure helpers are covered here, plus `_gridUpdates` (pure: it returns the
 * updates instead of applying them). `_applyGridLayout` itself also moves vis
 * nodes, so only its filtering is exercised here, through a fake DataSet.
 */

test('gridPosition maps a cell to the canvas at the map pitch', () => {
    // The node's position is its scope-relative `cell`, times the pitch. The
    // compiler's `cell * 40` engine units are not read here anymore. With no
    // explicit pitch the default is the mark envelope (task-748): card 130 +
    // way 26 + gap 20 = 176 at node-size 1.
    const pitch = GraphLayoutEngine.markEnvelopePitch();
    assertEq(GraphLayoutEngine.mapSpacing(), pitch, 'default spacing is the mark envelope');
    assertEq(pitch, 176, '130 card + 26 way + 20 gap');
    assertEq(GraphLayoutEngine.gridPosition({ x: 1, y: 2 }), { x: pitch, y: 2 * pitch });
    assertEq(GraphLayoutEngine.gridPosition({ x: 0, y: 0 }), { x: 0, y: 0 });
});

test('gridPosition returns null without a numeric cell', () => {
    assertEq(GraphLayoutEngine.gridPosition({}), null);
    assertEq(GraphLayoutEngine.gridPosition({ x: 1 }), null);
    assertEq(GraphLayoutEngine.gridPosition({ x: '1', y: '2' }), null);
    assertEq(GraphLayoutEngine.gridPosition(null), null);
});

test('gridPosition honours an explicit pitch', () => {
    assertEq(GraphLayoutEngine.gridPosition({ x: 2, y: 3 }, 10), { x: 20, y: 30 });
    assertEq(GraphLayoutEngine.gridPosition({ x: 2, y: 3 }, 0), { x: 0, y: 0 });
});

test('hasPaintedGrid detects compiler output via properties.cell', () => {
    assertTrue(GraphLayoutEngine.hasPaintedGrid({
        a: { type: 'area', properties: { cell: { x: 0, y: 0 } } },
    }), 'area with cell is a painted grid');
    assertFalse(GraphLayoutEngine.hasPaintedGrid({
        a: { type: 'area', properties: { x: 0, y: 0 } },
    }), 'hand-placed x/y is not a painted grid');
    assertFalse(GraphLayoutEngine.hasPaintedGrid({ way: { type: 'way' } }), 'no areas');
    assertFalse(GraphLayoutEngine.hasPaintedGrid({}), 'empty');
});

test('nodeScopeId reads world_scope_id then generated.scope_id', () => {
    assertEq(GraphLayoutEngine.nodeScopeId({ properties: { world_scope_id: 'a' } }), 'a');
    assertEq(GraphLayoutEngine.nodeScopeId({ properties: { generated: { scope_id: 'b' } } }), 'b');
    assertEq(GraphLayoutEngine.nodeScopeId({ properties: {} }), null);
    assertEq(GraphLayoutEngine.nodeScopeId(null), null);
});

test('scopedGridPosition adds the scope offset in cell units (task-523)', () => {
    const props = { cell: { x: 1, y: 2 } };          // painted cell (1, 2)
    const node = { type: 'area', properties: { ...props, world_scope_id: 'forest' } };
    const offsets = { forest: { x: 3, y: -1 } };    // +3 cells right, -1 up
    const p = GraphLayoutEngine.mapSpacing();
    // base (1,2) + offset (3,-1) = (4,1) cells, times the pitch.
    assertEq(GraphLayoutEngine.scopedGridPosition(props, node, offsets), { x: 4 * p, y: 1 * p });
});

test('scopedGridPosition offsets a gateway via generated.scope_id', () => {
    const props = { cell: { x: 0, y: 0 } };
    const node = { type: 'way', properties: { generated: { scope_id: 'town' } } };
    const p = GraphLayoutEngine.mapSpacing();
    assertEq(GraphLayoutEngine.scopedGridPosition(props, node, { town: { x: 1, y: 2 } }),
             { x: p, y: 2 * p });
});

test('scopedGridPosition ignores unknown scopes and non-finite offsets', () => {
    const props = { cell: { x: 0, y: 0 } };
    const bare = { type: 'area', properties: { world_scope_id: 'x' } };
    assertEq(GraphLayoutEngine.scopedGridPosition(props, bare, {}), { x: 0, y: 0 });
    assertEq(GraphLayoutEngine.offsetPxFor(bare, { x: { x: 'bad', y: null } }), { x: 0, y: 0 });
});

test('offsetPxFor honours an explicit spacing', () => {
    const node = { properties: { world_scope_id: 's' } };
    assertEq(GraphLayoutEngine.offsetPxFor(node, { s: { x: 2, y: -3 } }, 10), { x: 20, y: -30 });
});

test('mapSpacing honours config.graphMapSpacing (map padding)', () => {
    assertEq(GraphLayoutEngine.mapSpacing(), GraphLayoutEngine.markEnvelopePitch(),
        'default pitch is the mark envelope');
    config = { graphMapSpacing: 140 };
    assertEq(GraphLayoutEngine.mapSpacing(), 140, 'override pitch');
    assertEq(GraphLayoutEngine.gridPosition({ x: 1, y: 0 }), { x: 140, y: 0 }, 'a cell follows the pitch');
    config = { graphMapSpacing: 0 };   // non-positive falls back to the default
    assertEq(GraphLayoutEngine.mapSpacing(), GraphLayoutEngine.markEnvelopePitch(),
        'zero falls back to the mark envelope');
    config = undefined;                // restore the sandbox's "no config" state
});

test('a painted area is placed at its cell even with physics off (bug-52)', () => {
    // The scenario builders default every area to `central_gravity_enabled: false`
    // (tools/build_scenario.py), so the old freeze filter skipped *every* painted
    // area: the areas kept whatever pitch they were last saved at while the
    // background art re-fitted to the current one, and the map and its areas ended
    // up on two different grids. A painted cell is the position; the flag is about
    // physics, which is not what places the node.
    const nodes = {
        area_painted: {
            type: 'area',
            properties: { cell: { x: 5, y: 2 }, x: 200, y: 80, central_gravity_enabled: false },
        },
        area_free: {           // no painted coords → the freeze still applies
            type: 'area',
            properties: { x: 999, y: 999, central_gravity_enabled: false },
        },
        way_placed: {          // a way on a painted lattice: also map-anchored
            type: 'way',
            properties: { cell: { x: 1, y: 1 }, x: 40, y: 40, central_gravity_enabled: false },
        },
    };
    const applied = [];
    const ds = { get: (id) => (id in nodes ? { id } : null), update: (u) => applied.push(...u) };
    const prevNetwork = graphManager.network;
    const prevToolbar = window.GraphToolbar;
    const prevGraphNetwork = window.GraphNetwork;
    const physicsCalls = [];
    graphManager.network = { setOptions: () => {}, redraw: () => {}, fit: () => {} };
    // The grid layout now switches the solver through GraphNetwork.applyModePhysics
    // (so centralGravity follows the layout). network-manager.js is not loaded in
    // this sandbox, so stand in for the seam and record what it was asked to do;
    // the decision itself is covered live, and `centralGravityFor` is pure.
    window.GraphNetwork = {
        applyModePhysics: (enabled) => physicsCalls.push(enabled),
    };
    window.GraphToolbar = { syncAll: () => {} };
    try {
        config = { graphMapSpacing: 260 };
        GraphLayoutEngine._applyGridLayout(nodes, ds, {});
        const byId = {};
        applied.forEach((u) => { byId[u.id] = u; });
        // 260px pitch on cell*40 engine units → cell 5,2 lands at 1300, 520.
        assertEq(byId.area_painted.x, 5 * 260, 'painted area x at the current pitch');
        assertEq(byId.area_painted.y, 2 * 260, 'painted area y at the current pitch');
        assertTrue(byId.area_painted.fixed.x, 'and it is pinned to its cell');
        assertEq(byId.way_placed.x, 1 * 260, 'a placed way follows too');
        assertEq(byId.area_free, undefined, 'a frozen area with no cell is left alone');
        assertTrue(physicsCalls.includes(false), 'and the grid layout turns the solver off');
    } finally {
        config = undefined;
        graphManager.network = prevNetwork;
        window.GraphToolbar = prevToolbar;
        window.GraphNetwork = prevGraphNetwork;
    }
});

test('hasPaintedCoords tells a painted node from a hand-placed one', () => {
    // `cell` alone is the discriminator now: the compiler's x/y copy is
    // redundant, so a painted node is placed from its cell with or without it.
    assertTrue(GraphLayoutEngine.hasPaintedCoords({ cell: { x: 1, y: 1 } }), 'a cell is painted');
    assertTrue(GraphLayoutEngine.hasPaintedCoords({ cell: { x: 1, y: 1 }, x: 40, y: 40 }),
        'x/y alongside a cell is still painted');
    assertFalse(GraphLayoutEngine.hasPaintedCoords({ x: 40, y: 80 }), 'no cell → hand-placed');
    assertFalse(GraphLayoutEngine.hasPaintedCoords({ cell: { x: 'x', y: 1 } }),
        'an unparseable cell is not painted');
    assertFalse(GraphLayoutEngine.hasPaintedCoords({}), 'nothing');
    assertFalse(GraphLayoutEngine.hasPaintedCoords(null), 'no node');
});

test('map marks are fixed px, so the pitch never resizes them (task-748)', () => {
    // A mark is a thing drawn on the map, not a fraction of the cell. Its size
    // is the same at every pitch; the pitch is derived *from* it, so raising the
    // spacing must not inflate a card, way, item, character or font.
    config = { graphMapSpacing: 200 };
    const wide = {
        card: GraphLayoutEngine.markCardMax(),
        item: GraphLayoutEngine.markSize('item'),
        char: GraphLayoutEngine.markSize('character'),
        font: GraphLayoutEngine.markFontPx(),
        pad: GraphLayoutEngine.markCardPad(),
    };
    config = { graphMapSpacing: 40 };
    assertEq(GraphLayoutEngine.markCardMax(), wide.card, 'card is the same at 40 as at 200');
    assertEq(GraphLayoutEngine.markSize('item'), wide.item, 'item is the same at 40 as at 200');
    assertEq(GraphLayoutEngine.markSize('character'), wide.char, 'character is the same');
    assertEq(GraphLayoutEngine.markFontPx(), wide.font, 'font is the same');
    assertEq(GraphLayoutEngine.markCardPad(), wide.pad, 'padding is the same');
    assertEq(GraphLayoutEngine.markCardMax(), GraphLayoutEngine.MAP_MARK_PX.areaEdge,
        'card max is the constant');
    assertTrue(GraphLayoutEngine.markCardPad() > 0, 'padding is a positive constant');
    config = undefined;
});

test('autoMapSpacing is the mark envelope, not a viewport or world width (task-748)', () => {
    // The pitch is how much room the marks need, so it does not move with the
    // canvas size or the painted extent. card 130 + way 26 + gap 20 = 176.
    const painted = { a: { type: 'area', properties: { cell: { x: 0, y: 0 } } } };
    assertEq(GraphLayoutEngine.autoMapSpacing(painted, { w: 1400, h: 1400 }), 176, 'the envelope');
    assertEq(GraphLayoutEngine.autoMapSpacing(painted, { w: 400, h: 400 }), 176,
        'a small pane does not lower it');
    assertEq(GraphLayoutEngine.autoMapSpacing(painted, { w: 100000, h: 100000 }), 176,
        'a big pane does not raise it');

    // The painted extent does NOT change the pitch either.
    const big = { a: { type: 'area', properties: { cell: { x: 199, y: 132 } } } };
    assertEq(GraphLayoutEngine.autoMapSpacing(big, { w: 1400, h: 1400 }), 176,
        'a 200-cell world gets the same pitch');

    // Nothing painted → no opinion, so a hand-authored world keeps its pitch.
    assertEq(GraphLayoutEngine.autoMapSpacing({}, { w: 1400, h: 1400 }), null, 'nothing painted -> no opinion');
    assertEq(GraphLayoutEngine.autoMapSpacing(null, { w: 1400, h: 1400 }), null, 'no nodes -> no opinion');
});

test('the mark envelope leaves room for a way between two areas (task-748)', () => {
    // The pitch is derived from the marks, so by construction it has to be at
    // least a card plus a way: a half-cell must hold a half-card and a half-way.
    const pitch = GraphLayoutEngine.markEnvelopePitch();
    const card = GraphLayoutEngine.markCardMax();
    const way = GraphLayoutEngine.markSize('way');
    assertTrue(pitch >= card + way, `pitch ${pitch} >= card ${card} + way ${way}`);

    // A way sits at the midpoint of two areas a cell apart, so its drawn mark
    // clears both cards with the envelope gap to spare.
    const pos = GraphLayoutEngine.wayMapPosition([{ x: 0, y: 0 }, { x: pitch, y: 0 }], pitch);
    assertEq(pos, { x: pitch / 2, y: 0 }, 'the way sits at the gap centre');
    const clearance = pitch / 2 - card / 2 - way / 2;
    assertTrue(clearance >= 0, `the way clears both cards (clearance ${clearance})`);
});

test('mapBesideOffsets keep the 40px look and follow a wider pitch (bug-53)', () => {
    config = { graphMapSpacing: 40 };
    let o = GraphLayoutEngine.mapBesideOffsets();
    // The numbers this replaced, at the pitch they were tuned for.
    assertEq(o.itemX, -70, 'item x at 40px');
    assertEq(o.itemY, 70, 'item y at 40px');
    assertEq(o.charX, 130, 'character x at 40px');
    assertEq(o.charY, 0, 'character y sits on the room');
    assertEq(o.step, 45, 'fan step at 40px');
    assertEq(o.perRow, 4, 'four per row, unchanged');

    config = { graphMapSpacing: 260 };
    o = GraphLayoutEngine.mapBesideOffsets();
    // Same cell multiples, so an item is the same *relative* distance away.
    assertEq(o.itemX, -1.75 * 260, 'item x follows the pitch');
    assertEq(o.itemY, 1.75 * 260, 'item y follows the pitch');
    assertEq(o.charX, 3.25 * 260, 'character x follows the pitch');
    assertEq(o.step, 1.125 * 260, 'fan step follows the pitch');
    config = undefined;
});

test('items are placed beside their area at the current pitch (bug-53)', () => {
    // `_gridUpdates` puts loose nodes next to the area that holds them; the
    // offsets have to follow the pitch or an item lands on top of its room.
    const nodes = {
        area_hall: { type: 'area', properties: { cell: { x: 2, y: 1 }, x: 80, y: 40 } },
        item_lamp: { type: 'item', properties: {} },
    };
    const ds = { get: (id) => (id in nodes ? { id } : null), update: () => {} };
    const edges = [{ type: 'in', source: 'item_lamp', target: 'area_hall' }];
    const prevEdges = (worldState.graph || {}).edges;
    worldState.graph = Object.assign({}, worldState.graph, { edges });
    try {
        config = { graphMapSpacing: 260 };
        const out = GraphLayoutEngine._gridUpdates(nodes, ds, {});
        const anchor = { x: 2 * 260, y: 1 * 260 };
        const lamp = out.find((u) => u.id === 'item_lamp');
        assertEq(lamp.x, anchor.x - 1.75 * 260, 'beside the room, by cells');
        assertEq(lamp.y, anchor.y + 1.75 * 260, 'below-left of the room');
    } finally {
        worldState.graph.edges = prevEdges;
        config = undefined;
    }
});

test('a coordinate-less way on a painted map is placed between its rooms (task-618)', () => {
    // A grid-generated way often carries no `cell` and only a stale canvas
    // `properties.x/y` from a graph-mode save. Using that verbatim put the way
    // thousands of px from the areas it joins, so the connection edges crossed
    // empty space. It must be derived from its rooms instead.
    const nodes = {
        area_a: { type: 'area', properties: { cell: { x: 0, y: 0 }, x: 0, y: 0, world_scope_id: 's' } },
        area_b: { type: 'area', properties: { cell: { x: 4, y: 0 }, x: 160, y: 0, world_scope_id: 's' } },
        way_conn: { type: 'way', properties: { x: 9999, y: 9999, world_scope_id: 's' } },
        way_hand: { type: 'way', properties: { x: 777, y: 0 } },
    };
    const ds = { get: (id) => (id in nodes ? { id } : null), update: () => {} };
    const edges = [
        { type: 'connection', source: 'way_conn', target: 'area_a' },
        { type: 'connection', source: 'way_conn', target: 'area_b' },
    ];
    const prevEdges = (worldState.graph || {}).edges;
    worldState.graph = Object.assign({}, worldState.graph, { edges });
    try {
        config = { graphMapSpacing: 40 };
        const out = GraphLayoutEngine._gridUpdates(nodes, ds, {});
        const byId = {};
        out.forEach((u) => { byId[u.id] = u; });
        assertEq(byId.way_conn.x, 80, 'midpoint x of its two rooms');
        assertEq(byId.way_conn.y, 0, 'midpoint y');
        assertEq(byId.way_conn.physics, false, 'and pinned at the derived midpoint');
        // A way whose rooms are not painted keeps its hand-placed canvas position.
        assertEq(byId.way_hand.x, 777, 'a way with no painted room keeps its canvas x');
    } finally {
        worldState.graph.edges = prevEdges;
        config = undefined;
    }
});

test('wayMapPosition places a two-room way in the gap between them (task-723)', () => {
    // Two rooms a cell apart at the default 40px pitch: the way sits
    // at the half-cell, a half-cell from each room — the "20px to the
    // way, 20px to the next area" geometry the pitch is built around.
    assertEq(GraphLayoutEngine.wayMapPosition([{ x: 0, y: 0 }, { x: 40, y: 0 }], 40),
             { x: 20, y: 0 }, 'half-cell from each room');
    // The same two cells at a roomier pitch: the anchors scale with the
    // pitch, so the way stays at the gap centre.
    assertEq(GraphLayoutEngine.wayMapPosition([{ x: 0, y: 0 }, { x: 260, y: 0 }], 260),
             { x: 130, y: 0 }, 'gap centre at 260px pitch');
    // Diagonal connecting edge: interpolated along it, not axis-aligned.
    assertEq(GraphLayoutEngine.wayMapPosition([{ x: 0, y: 0 }, { x: 40, y: 40 }], 40),
             { x: 20, y: 20 }, 'midpoint of a diagonal edge');
    // Rooms further apart than a cell: still the segment midpoint, the
    // centre of the (wider) gap.
    assertEq(GraphLayoutEngine.wayMapPosition([{ x: 0, y: 0 }, { x: 160, y: 0 }], 40),
             { x: 80, y: 0 }, 'midpoint of a two-cell gap');
    // Rooms closer than a cell: no gap exists, so the midpoint is the
    // nearest point to both — not pushed onto a room.
    assertEq(GraphLayoutEngine.wayMapPosition([{ x: 0, y: 0 }, { x: 20, y: 0 }], 40),
             { x: 10, y: 0 }, 'midpoint when the rooms overlap');
    // Coincident rooms: the midpoint degenerates to the shared point.
    assertEq(GraphLayoutEngine.wayMapPosition([{ x: 5, y: 5 }, { x: 5, y: 5 }], 40),
             { x: 5, y: 5 }, 'coincident rooms');
});

test('wayMapPosition handles junctions, a single room, and none (task-723)', () => {
    // A junction of three rooms: the centroid, the balanced point.
    assertEq(GraphLayoutEngine.wayMapPosition(
        [{ x: 0, y: 0 }, { x: 60, y: 0 }, { x: 0, y: 60 }], 40),
        { x: 20, y: 20 }, 'centroid of three rooms');
    // One room: on it (a degenerate way has nowhere else to go).
    assertEq(GraphLayoutEngine.wayMapPosition([{ x: 120, y: 40 }], 40),
             { x: 120, y: 40 }, 'a single room');
    // Nothing to place by.
    assertEq(GraphLayoutEngine.wayMapPosition([], 40), null, 'no rooms');
    assertEq(GraphLayoutEngine.wayMapPosition(null, 40), null, 'null rooms');
});

test('_gridUpdates places a coordinate-less way via wayMapPosition (task-723)', () => {
    // The derived placement is the gap midpoint of the way's rooms, at
    // the current pitch — the same result the inline mean produced, now
    // through the named, tested helper.
    const nodes = {
        area_a: { type: 'area', properties: { cell: { x: 0, y: 0 }, x: 0, y: 0, world_scope_id: 's' } },
        area_b: { type: 'area', properties: { cell: { x: 2, y: 0 }, x: 80, y: 0, world_scope_id: 's' } },
        area_c: { type: 'area', properties: { cell: { x: 1, y: 2 }, x: 40, y: 80, world_scope_id: 's' } },
        way_two: { type: 'way', properties: { world_scope_id: 's' } },
        way_junction: { type: 'way', properties: { world_scope_id: 's' } },
    };
    const ds = { get: (id) => (id in nodes ? { id } : null), update: () => {} };
    const edges = [
        { type: 'connection', source: 'way_two', target: 'area_a' },
        { type: 'connection', source: 'way_two', target: 'area_b' },
        { type: 'connection', source: 'way_junction', target: 'area_a' },
        { type: 'connection', source: 'way_junction', target: 'area_b' },
        { type: 'connection', source: 'way_junction', target: 'area_c' },
    ];
    const prevEdges = (worldState.graph || {}).edges;
    worldState.graph = Object.assign({}, worldState.graph, { edges });
    try {
        config = { graphMapSpacing: 40 };
        const out = GraphLayoutEngine._gridUpdates(nodes, ds, {});
        const byId = {};
        out.forEach((u) => { byId[u.id] = u; });
        // Two rooms at (0,0) and (80,0): gap midpoint (40, 0).
        assertEq(byId.way_two.x, 40, 'two-room way at the gap midpoint');
        assertEq(byId.way_two.y, 0, 'two-room way y');
        // Junction of (0,0), (80,0), (40,80): centroid (40, 26.67).
        assertEq(byId.way_junction.x, 40, 'junction way x at the centroid');
        assertTrue(Math.abs(byId.way_junction.y - 80 / 3) < 1e-9,
            `junction way y at the centroid (got ${byId.way_junction.y})`);
    } finally {
        worldState.graph.edges = prevEdges;
        config = undefined;
    }
});

test('a hand-placed node keeps its canvas position: no rescale, no offset', () => {
    // `properties.x/y` is an overloaded field. The compiler writes ENGINE units
    // (`cell * 40`), which the map layout scales by the pitch and translates by
    // the scope offset; a node dragged in the graph stores CANVAS pixels in the
    // same field, which must be used verbatim. Treating the second as the first
    // compounds the pitch and re-adds the offset on every layout, so a node
    // creeps further from everything each time it is saved or re-laid out.
    const nodes = {
        area_painted: {
            type: 'area',
            properties: { cell: { x: 2, y: 1 }, x: 80, y: 40, world_scope_id: 'town' },
        },
        char_kael: { type: 'character', properties: { x: -477, y: -405 } },
        way_hand: { type: 'way', properties: { x: 812, y: 76 } },
    };
    const ds = { get: (id) => (id in nodes ? { id } : null), update: () => {} };
    const offsets = { town: { x: 3, y: 1 } };          // 3 cells right, 1 down
    try {
        // A 2x pitch: engine units are 2x, canvas pixels are not rescaled.
        config = { graphMapSpacing: 80 };
        const out = GraphLayoutEngine._gridUpdates(nodes, ds, offsets);
        const byId = {};
        out.forEach((u) => { byId[u.id] = u; });

        // Painted: (80,40) engine units * 2 = (160,80), + offset 3*80, 1*80.
        assertEq(byId.area_painted.x, 400, 'a painted node is scaled and offset');
        assertEq(byId.area_painted.y, 160, 'on both axes');

        // Hand-placed: taken literally. Before the fix these came back as
        // -477*2 and -477*2+240, and the next save stored that back.
        assertEq(byId.char_kael.x, -477, 'a hand-placed character is used as-is');
        assertEq(byId.char_kael.y, -405, 'on both axes');
        assertEq(byId.way_hand.x, 812, 'a hand-placed way is used as-is');
        assertEq(byId.way_hand.y, 76, 'on both axes');
    } finally {
        config = undefined;
    }
});

test('the grid layout pins painted areas and ways; other nodes go to the solver', () => {
    // task-618: a way painted on a cell is part of the map, so it is pinned to
    // its cell like an area. task-530 left it free for the solver, but the
    // solver frame and the grid frame disagree, so a painted way drifted off
    // its cell and its connection edges crossed empty space. A way with no
    // painted room/no cell is still left to the solver (task-530's concern:
    // ways piling up at a stale saved position).
    const nodes = {
        area_a: { type: 'area', properties: { cell: { x: 0, y: 0 }, x: 0, y: 0 } },
        way_door: { type: 'way', properties: { cell: { x: 0.5, y: 0 }, x: 20, y: 0 } },
        way_frozen: {
            type: 'way',
            properties: { cell: { x: 0.5, y: 0 }, x: 20, y: 0, central_gravity_enabled: false },
        },
        char_kael: { type: 'character', properties: { x: 100, y: 0 } },
        char_frozen: { type: 'character', properties: { x: 140, y: 0, central_gravity_enabled: false } },
    };
    const ds = { get: (id) => (id in nodes ? { id } : null), update: () => {} };
    const out = GraphLayoutEngine._gridUpdates(nodes, ds, {});
    const byId = {};
    out.forEach((u) => { byId[u.id] = u; });

    assertEq(byId.area_a.physics, false, 'an area is pinned to its cell');
    assertTrue(byId.area_a.fixed.x, 'and held there');
    assertEq(byId.way_door.physics, false, 'a painted way is pinned to its cell');
    assertTrue(byId.way_door.fixed.x, 'and held there');
    assertEq(byId.way_frozen.physics, false, "an author's frozen way stays put");
    // A hand-placed character is seeded where it was put and then simulated: the
    // solver has no central gravity, so its `in` edge holds it beside its room.
    // (This node never reaches the `heldIn` branch — it has its own coords — so a
    // way-only gate here used to leave it pinned out of the solver while the test
    // below still passed.)
    assertEq(byId.char_kael.physics, true, 'a hand-placed character is in the solver');
    assertEq(byId.char_kael.fixed.x, false, 'and the solver may move it');
    assertEq(byId.char_frozen.physics, false, "an author's frozen character stays put");
});

test('isFrozen follows the author flag, with a safe fallback', () => {
    assertTrue(GraphLayoutEngine.isFrozen({ properties: { central_gravity_enabled: false } }),
        'physics off in the inspector');
    assertTrue(GraphLayoutEngine.isFrozen({ properties: { layout_static: true } }),
        'layout_static');
    assertFalse(GraphLayoutEngine.isFrozen({ properties: {} }), 'default is dynamic');
    assertFalse(GraphLayoutEngine.isFrozen(null), 'a missing node is dynamic');
});
