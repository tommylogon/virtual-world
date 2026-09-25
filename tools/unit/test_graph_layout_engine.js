/**
 * Unit tests for graph/layout-engine — the map layout's grid mode.
 *
 * Only the pure helpers are covered here; `_applyGridLayout` moves vis nodes and
 * needs a live network, so it is exercised manually in the app.
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
