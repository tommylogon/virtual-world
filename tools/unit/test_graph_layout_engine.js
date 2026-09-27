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

test('mapScale is 1 at the default pitch and clamped at a wide one (bug-53)', () => {
    assertEq(GraphLayoutEngine.mapScale(), 1, 'default 40px pitch scales nothing');
    config = { graphMapSpacing: 80 };
    assertEq(GraphLayoutEngine.mapScale(), 2, 'double pitch doubles the drawing');
    // 260px is 6.5x, which would smear the labels — the clamp keeps boxes
    // readable while the *spacing* still follows the pitch exactly.
    config = { graphMapSpacing: 260 };
    assertEq(GraphLayoutEngine.mapScale(), 2.5, 'clamped at 2.5x');
    config = { graphMapSpacing: 10 };   // below the default: never shrink below 1
    assertEq(GraphLayoutEngine.mapScale(), 1, 'never below 1');
    config = undefined;
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
