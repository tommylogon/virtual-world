/**
 * Unit tests for graph/layout-engine — the map layout's grid mode.
 *
 * The pure helpers are covered here, plus `_gridUpdates` (pure: it returns the
 * updates instead of applying them). `_applyGridLayout` itself also moves vis
 * nodes, so only its filtering is exercised here, through a fake DataSet.
 */

test('gridPosition scales painted coords by the map spacing', () => {
    // Default spacing is 40px per cell, and painted coords are 40 units/cell,
    // so the default scale is 1:40px area-to-area, way at the 20px midpoint.
    assertEq(GraphLayoutEngine.mapSpacing(), 40, 'default spacing');
    assertEq(GraphLayoutEngine.GRID_SCALE, 1, 'default scale');
    assertEq(GraphLayoutEngine.gridPosition({ x: 40, y: 80 }), { x: 40, y: 80 });
    assertEq(GraphLayoutEngine.gridPosition({ x: 0, y: 0 }), { x: 0, y: 0 });
});

test('gridPosition returns null without numeric coords', () => {
    assertEq(GraphLayoutEngine.gridPosition({}), null);
    assertEq(GraphLayoutEngine.gridPosition({ x: 1 }), null);
    assertEq(GraphLayoutEngine.gridPosition({ x: '1', y: '2' }), null);
    assertEq(GraphLayoutEngine.gridPosition(null), null);
});

test('gridPosition honours an explicit scale', () => {
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
    const props = { x: 40, y: 80 };                 // painted cell (1, 2)
    const node = { type: 'area', properties: { ...props, world_scope_id: 'forest' } };
    const offsets = { forest: { x: 3, y: -1 } };    // +3 cells right, -1 up
    // base (40, 80) + offset (3*40, -1*40) = (160, 40)
    assertEq(GraphLayoutEngine.scopedGridPosition(props, node, offsets), { x: 160, y: 40 });
});

test('scopedGridPosition offsets a gateway via generated.scope_id', () => {
    const props = { x: 0, y: 0 };
    const node = { type: 'way', properties: { generated: { scope_id: 'town' } } };
    assertEq(GraphLayoutEngine.scopedGridPosition(props, node, { town: { x: 1, y: 2 } }),
             { x: 40, y: 80 });
});

test('scopedGridPosition ignores unknown scopes and non-finite offsets', () => {
    const props = { x: 0, y: 0 };
    const bare = { type: 'area', properties: { world_scope_id: 'x' } };
    assertEq(GraphLayoutEngine.scopedGridPosition(props, bare, {}), { x: 0, y: 0 });
    assertEq(GraphLayoutEngine.offsetPxFor(bare, { x: { x: 'bad', y: null } }), { x: 0, y: 0 });
});

test('offsetPxFor honours an explicit spacing', () => {
    const node = { properties: { world_scope_id: 's' } };
    assertEq(GraphLayoutEngine.offsetPxFor(node, { s: { x: 2, y: -3 } }, 10), { x: 20, y: -30 });
});

test('mapSpacing honours config.graphMapSpacing (map padding)', () => {
    assertEq(GraphLayoutEngine.mapSpacing(), 40, 'default pitch is 40px/cell');
    config = { graphMapSpacing: 140 };
    assertEq(GraphLayoutEngine.mapSpacing(), 140, 'override pitch');
    assertEq(GraphLayoutEngine.GRID_SCALE, 140 / GraphLayoutEngine.PAINT_UNITS_PER_CELL,
             'scale follows the pitch');
    config = { graphMapSpacing: 0 };   // non-positive falls back to the default
    assertEq(GraphLayoutEngine.mapSpacing(), 40, 'zero falls back to 40');
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
    graphManager.network = { setOptions: () => {}, redraw: () => {}, fit: () => {} };
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
    } finally {
        config = undefined;
        graphManager.network = prevNetwork;
        window.GraphToolbar = prevToolbar;
    }
});

test('hasPaintedCoords tells a painted node from a hand-placed one', () => {
    assertTrue(GraphLayoutEngine.hasPaintedCoords({ cell: { x: 1, y: 1 }, x: 40, y: 40 }),
        'cell + numeric coords is painted');
    // A node dragged in the graph has numeric x/y too, and they are *canvas*
    // coords — only `cell` tells the two apart.
    assertFalse(GraphLayoutEngine.hasPaintedCoords({ x: 40, y: 80 }), 'no cell → hand-placed');
    assertFalse(GraphLayoutEngine.hasPaintedCoords({ cell: { x: 1, y: 1 }, x: '40', y: '80' }),
        'cell but no numeric coords');
    assertFalse(GraphLayoutEngine.hasPaintedCoords({ cell: { x: 1, y: 1 } }), 'cell without coords');
    assertFalse(GraphLayoutEngine.hasPaintedCoords({}), 'nothing');
    assertFalse(GraphLayoutEngine.hasPaintedCoords(null), 'no node');
});

test('mapScale tracks the pitch and is clamped at both ends (bug-53, task-526)', () => {
    assertEq(GraphLayoutEngine.mapScale(), 1, 'default 40px pitch scales nothing');
    config = { graphMapSpacing: 80 };
    assertEq(GraphLayoutEngine.mapScale(), 2, 'double pitch doubles the drawing');
    // 260px is 6.5x, which would smear the labels — the clamp keeps boxes
    // readable while the *spacing* still follows the pitch exactly.
    config = { graphMapSpacing: 260 };
    assertEq(GraphLayoutEngine.mapScale(), 2.5, 'clamped at 2.5x');
    // The low end matters too (task-526): at a tight pitch a full-size mark is
    // bigger than the cell it sits in, so the drawing shrinks with the pitch down
    // to a floor. Before this, the low clamp was 1 — a 20px cell kept a 42px box.
    config = { graphMapSpacing: 20 };
    assertEq(GraphLayoutEngine.mapScale(), 0.5, 'half the pitch halves the drawing');
    config = { graphMapSpacing: 4 };
    assertEq(GraphLayoutEngine.mapScale(), GraphLayoutEngine.MAP_SCALE_MIN,
             'floored, so a tiny pitch cannot vanish');
    config = undefined;
});

test('a tight pitch draws dots, a roomy one draws cards (task-526)', () => {
    const threshold = GraphLayoutEngine.MAP_CARD_MIN_PITCH;
    // A card's width is its *name* plus margin, and type does not shrink with the
    // pitch — which is why the default 40px map used to look like a physics blob.
    assertEq(threshold, 140, 'the threshold is a named constant, not a magic number');
    config = { graphMapSpacing: 40 };
    assertTrue(GraphLayoutEngine.mapCompact(), 'the old default is compact');
    config = { graphMapSpacing: 20 };
    assertTrue(GraphLayoutEngine.mapCompact(), 'and so is a tighter one');
    assertTrue(GraphLayoutEngine.mapScale() < 1, 'whose marks also shrink below full size');
    config = { graphMapSpacing: threshold };
    assertFalse(GraphLayoutEngine.mapCompact(), 'exactly at the threshold cards are back');
    // Why that number: at the threshold the (clamped) card box still fits its cell,
    // so the switch happens where the boxes stop colliding, not before.
    const cardHalfWidth = 27 * GraphLayoutEngine.mapScale();
    assertTrue(cardHalfWidth * 2 <= threshold, 'a card fits the cell at the threshold');
    config = { graphMapSpacing: 260 };
    assertFalse(GraphLayoutEngine.mapCompact(), 'a wide pitch keeps its cards');
    config = undefined;
});

test('the dot is sized from the cell, so it always fits it (task-526)', () => {
    // Tied to the pitch rather than to mapScale: a dot has to sit inside its own
    // cell at any pitch, and stay visible when a 200-cell world is zoomed out.
    config = { graphMapSpacing: 40 };
    const small = GraphLayoutEngine.mapDotSize();
    config = { graphMapSpacing: 200 };
    const large = GraphLayoutEngine.mapDotSize();
    assertTrue(large > small, 'a roomier cell gets a roomier dot');
    assertTrue(small <= 40 * 0.55 + 1e-9, 'and the dot never exceeds its cell');
    assertTrue(small >= 6, 'but never vanishes');
    config = { graphMapSpacing: 400 };
    assertTrue(GraphLayoutEngine.mapDotSize() <= 28, 'nor swells past legibility');
    config = undefined;
});

test('paintedExtent measures the drawn area in cells (task-526)', () => {
    const painted = {
        a: { type: 'area', properties: { cell: { x: 0, y: 0 } } },
        b: { type: 'area', properties: { cell: { x: 5, y: 2 } } },
        c: { type: 'area', properties: { cell: { x: 1, y: 7 } } },
        // A way sits on the lattice too but is not a place to measure the map by.
        w: { type: 'way', properties: { cell: { x: 99, y: 99 } } },
        // A hand-authored area has no cell and must not stretch the extent.
        hand: { type: 'area', properties: { x: 500, y: 500 } },
    };
    assertEq(GraphLayoutEngine.paintedExtent(painted), { w: 6, h: 8 },
             'one past the furthest painted cell');
    assertEq(GraphLayoutEngine.paintedExtent({}), null, 'nothing painted');
    assertEq(GraphLayoutEngine.paintedExtent(null), null, 'no nodes at all');
    assertEq(GraphLayoutEngine.paintedExtent({ bad: { type: 'area', properties: { cell: { x: 'x', y: 1 } } } }),
             null, 'an unparseable cell is not an extent');
});

test('autoMapSpacing fits a small zone and a big one without hand-tuning (task-526)', () => {
    // One global pitch cannot serve both: too tight overlaps, too wide scatters.
    const small = {};   // a 6x8 camp
    small.a = { type: 'area', properties: { cell: { x: 5, y: 7 } } };
    const big = {};     // a 200x133 world
    big.a = { type: 'area', properties: { cell: { x: 199, y: 132 } } };

    const smallPitch = GraphLayoutEngine.autoMapSpacing(small);
    const bigPitch = GraphLayoutEngine.autoMapSpacing(big);
    // The small zone lands roomy — which is the pitch a person picks by hand today,
    // and above the card threshold, so it still reads as named places.
    assertEq(smallPitch, 200, 'a 6x8 camp gets a card pitch');
    assertTrue(smallPitch >= GraphLayoutEngine.MAP_CARD_MIN_PITCH, 'and stays on cards');
    // The big one lands tight, but never tighter than the floor.
    assertTrue(bigPitch < smallPitch, 'a 200x133 world gets a tighter pitch');
    assertTrue(bigPitch >= GraphLayoutEngine.AUTO_SPACING_MIN, 'never below the floor');
    assertTrue(bigPitch <= GraphLayoutEngine.AUTO_SPACING_MAX, 'never above the ceiling');

    // Both are drawn on one screen: pitch x the longest side ~ the target span.
    const span = GraphLayoutEngine.AUTO_SPAN_PX;
    assertTrue(Math.abs(smallPitch * 8 - span) <= 10, 'small map spans the target');
    assertEq(GraphLayoutEngine.autoMapSpacing({}), null, 'nothing painted -> no opinion');
    assertEq(GraphLayoutEngine.autoMapSpacing(null), null, 'no nodes -> no opinion');
    // Tidy stepper values, not 213.333.
    assertEq(smallPitch % 10, 0, 'roomy pitches land on a multiple of 10');
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

test('the grid layout gives ways to the solver but leaves areas pinned', () => {
    // Task-530's intent: areas sit on their painted cells, ways are free so the
    // solver pulls them in next to their areas. `physics: false` on every node
    // (the bug) left the global toggle spinning on an empty node list, so
    // enabling physics appeared to do nothing at all.
    const nodes = {
        area_a: { type: 'area', properties: { cell: { x: 0, y: 0 }, x: 0, y: 0 } },
        way_door: { type: 'way', properties: { cell: { x: 0.5, y: 0 }, x: 20, y: 0 } },
        way_frozen: {
            type: 'way',
            properties: { cell: { x: 0.5, y: 0 }, x: 20, y: 0, central_gravity_enabled: false },
        },
        char_kael: { type: 'character', properties: { x: 100, y: 0 } },
    };
    const ds = { get: (id) => (id in nodes ? { id } : null), update: () => {} };
    const out = GraphLayoutEngine._gridUpdates(nodes, ds, {});
    const byId = {};
    out.forEach((u) => { byId[u.id] = u; });

    assertEq(byId.area_a.physics, false, 'an area is pinned to its cell');
    assertTrue(byId.area_a.fixed.x, 'and held there');
    assertEq(byId.way_door.physics, true, 'a way is simulated');
    assertEq(byId.way_door.fixed.x, false, 'so the solver may move it');
    assertEq(byId.way_frozen.physics, false, "an author's frozen way stays put");
    // Items/characters are leashed by GraphRelativeLayout and kept out of the
    // global gravity field on purpose; the grid pass must not contradict that.
    assertEq(byId.char_kael.physics, false, 'a character is not in the solver');
});

test('isFrozen follows the author flag, with a safe fallback', () => {
    assertTrue(GraphLayoutEngine.isFrozen({ properties: { central_gravity_enabled: false } }),
        'physics off in the inspector');
    assertTrue(GraphLayoutEngine.isFrozen({ properties: { layout_static: true } }),
        'layout_static');
    assertFalse(GraphLayoutEngine.isFrozen({ properties: {} }), 'default is dynamic');
    assertFalse(GraphLayoutEngine.isFrozen(null), 'a missing node is dynamic');
});
