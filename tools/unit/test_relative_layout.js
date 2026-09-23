/**
 * Unit tests for graph/relative-layout.js (task-485).
 *
 * Positions must be derived from the relations, so the interesting cases are
 * the precedence rules (carried beats inside, worn beats inside), cycles, and
 * stability â€” the same graph must lay out the same way twice.
 */

const NODES = {
    area_hall: { id: 'area_hall', type: 'area' },
    area_cellar: { id: 'area_cellar', type: 'area' },
    item_lamp: { id: 'item_lamp', type: 'item' },
    item_oil: { id: 'item_oil', type: 'item' },
    char_kael: { id: 'char_kael', type: 'character' },
    item_vest: { id: 'item_vest', type: 'item' },
    item_bag: { id: 'item_bag', type: 'item' },
    way_hatch: { id: 'way_hatch', type: 'way' },
    trigger_hatch: { id: 'trigger_hatch', type: 'logic_trigger' },
};

// Mirrors the real save's edge shapes: `in` is stored both ways round
// (container -> contained for nested items, contained -> container for rooms),
// and equipped/carrying/at all run item -> character/area.
const EDGES = [
    { type: 'in', source: 'item_lamp', target: 'area_hall' },        // lamp is in the hall
    { type: 'in', source: 'item_lamp', target: 'item_oil' },         // lamp holds the oil
    { type: 'in', source: 'char_kael', target: 'area_hall' },        // Kaelen is in the hall
    { type: 'equipped', source: 'item_vest', target: 'char_kael' },  // vest worn by Kaelen
    { type: 'carrying', source: 'item_bag', target: 'char_kael' },   // bag carried by Kaelen
    { type: 'in', source: 'item_bag', target: 'area_cellar' },       // stale: bag left in the cellar once
    { type: 'triggers', source: 'item_lamp', target: 'trigger_hatch' }, // lamp hosts the trigger
    { type: 'connection', source: 'way_hatch', target: 'area_hall' },
    { type: 'connection', source: 'way_hatch', target: 'area_cellar' },
];

const layout = (positions) =>
    GraphRelativeLayout.layoutPositions(NODES, EDGES, positions);

const POS = { area_hall: { x: 0, y: 0 }, area_cellar: { x: 800, y: 600 } };

test('an item hangs off the area that holds it', () => {
    assertEq(GraphRelativeLayout.parentOf('item_lamp', EDGES, NODES), 'area_hall');
    // Both `in` directions resolve: the lamp is in the hall, the oil is in the lamp.
    assertEq(GraphRelativeLayout.parentOf('item_oil', EDGES, NODES), 'item_lamp');
});

test('a carried item follows the carrier, not the room it was left in', () => {
    // item_bag BOTH sits in the cellar and is carried â€” the carrier wins.
    assertEq(GraphRelativeLayout.parentOf('item_bag', EDGES, NODES), 'char_kael');
});

test('worn gear follows the wearer', () => {
    assertEq(GraphRelativeLayout.parentOf('item_vest', EDGES, NODES), 'char_kael');
});

test('a trigger sits on its host and a way between its rooms', () => {
    assertEq(GraphRelativeLayout.parentOf('trigger_hatch', EDGES, NODES), 'item_lamp');
    const mid = GraphRelativeLayout.wayMidpoint('way_hatch', EDGES, POS, NODES);
    assertEq(mid, { x: 400, y: 300 }, 'way midpoint');
});

test('a trigger hosted by a way hangs off that way', () => {
    const nodes = { area_a: { type: 'area' }, area_b: { type: 'area' }, way_door: { type: 'way' }, trigger_door: { type: 'logic_trigger' } };
    const edges = [
        { type: 'connection', source: 'way_door', target: 'area_a' },
        { type: 'connection', source: 'way_door', target: 'area_b' },
        { type: 'triggers', source: 'way_door', target: 'trigger_door' },
    ];
    assertEq(GraphRelativeLayout.parentOf('trigger_door', edges, nodes), 'way_door');
    const out = GraphRelativeLayout.layoutPositions(nodes, edges, { area_a: { x: 0, y: 0 }, area_b: { x: 200, y: 0 } });
    assertTrue(Number.isFinite(out.trigger_door.x), 'the trigger is placed');
    assertTrue(Math.abs(out.trigger_door.x - 100) < 200, 'near the way midpoint');
});

test('an area is a root: it comes back at its own position, unplaced', () => {
    assertEq(GraphRelativeLayout.parentOf('area_hall', EDGES, NODES), null);
    assertEq(layout(POS).area_hall, { x: 0, y: 0 });
});

test('children orbit their parent instead of stacking on it', () => {
    const out = layout(POS);
    const r = (id, parent) => Math.hypot(out[id].x - POS[parent].x, out[id].y - POS[parent].y);
    // A lone item sits on the ring, clear of the room's own label.
    assertTrue(Math.abs(r('item_lamp', 'area_hall') - GraphRelativeLayout.ORBIT.minRadius) < 0.5,
        'one child sits on the minimum orbit');
    // Nested contents orbit their container on a smaller ring.
    const nested = Math.hypot(out.item_oil.x - out.item_lamp.x, out.item_oil.y - out.item_lamp.y);
    assertTrue(nested < GraphRelativeLayout.ORBIT.minRadius, 'nested orbit is tighter');
});

test('the orbit grows with the crowd so labels do not collide', () => {
    const one = { area_a: { type: 'area' }, item_0: { type: 'item' } };
    const oneEdges = [{ type: 'in', source: 'item_0', target: 'area_a' }];
    const oneOut = GraphRelativeLayout.layoutPositions(one, oneEdges, { area_a: { x: 0, y: 0 } });
    const oneR = Math.hypot(oneOut.item_0.x, oneOut.item_0.y);

    const many = { area_a: { type: 'area' } };
    const manyEdges = [];
    for (let i = 0; i < 12; i++) {
        many['item_' + i] = { type: 'item' };
        manyEdges.push({ type: 'in', source: 'item_' + i, target: 'area_a' });
    }
    const manyOut = GraphRelativeLayout.layoutPositions(many, manyEdges, { area_a: { x: 0, y: 0 } });
    const items = Object.entries(manyOut).filter(([id]) => id !== 'area_a').map(([, p]) => p);
    const radii = items.map(p => Math.round(Math.hypot(p.x, p.y)));
    const unique = new Set(radii);
    assertEq(unique.size, 1, 'every item is on the same ring');
    const wide = radii[0];
    assertTrue(wide > oneR, 'a crowded room gets a wider ring');
    assertTrue(wide <= GraphRelativeLayout.ORBIT.maxRadius, 'the ring is bounded, so nothing is stretched away');
    // Evenly spaced: no two items share a spot.
    const keys = items.map(p => `${Math.round(p.x)},${Math.round(p.y)}`);
    assertEq(new Set(keys).size, keys.length, 'no two items overlap');
});

test('an extremely crowded room stays capped rather than flying off', () => {
    const nodes = { area_a: { type: 'area' } };
    const edges = [];
    for (let i = 0; i < 60; i++) {
        nodes['item_' + i] = { type: 'item' };
        edges.push({ type: 'in', source: 'item_' + i, target: 'area_a' });
    }
    const out = GraphRelativeLayout.layoutPositions(nodes, edges, { area_a: { x: 0, y: 0 } });
    const maxR = Math.max(...Object.values(out).map(p => Math.hypot(p.x, p.y)));
    assertTrue(Math.round(maxR) <= GraphRelativeLayout.ORBIT.maxRadius, 'capped at maxRadius');
});

test('a carried item ends up beside the carrier, wherever the carrier is', () => {
    const out = { ...layout(POS), ...POS };
    const nearHall = Math.hypot(out.item_bag.x - POS.area_hall.x, out.item_bag.y - POS.area_hall.y);
    const nearCellar = Math.hypot(out.item_bag.x - POS.area_cellar.x, out.item_bag.y - POS.area_cellar.y);
    assertTrue(nearHall < 250, 'the bag is with its carrier');
    assertTrue(nearCellar > 500, 'the bag did not stay in the room it was left in');
});

test('the same graph lays out the same way twice', () => {
    assertEq(layout(POS), layout(POS));
});

test('a container cycle resolves through the area instead of hanging', () => {
    const nodes = { a: { id: 'a', type: 'item' }, b: { id: 'b', type: 'item' }, area: { id: 'area', type: 'area' } };
    const edges = [
        { type: 'in', source: 'a', target: 'b' },
        { type: 'in', source: 'b', target: 'a' },
        { type: 'in', source: 'b', target: 'area' },
    ];
    const out = GraphRelativeLayout.layoutPositions(nodes, edges, { area: { x: 0, y: 0 } });
    // b is in the area, a is in b: the loop breaks towards the root.
    assertEq(GraphRelativeLayout.parentOf('b', edges, nodes), 'area');
    assertEq(GraphRelativeLayout.parentOf('a', edges, nodes), 'b');
    assertTrue(Number.isFinite(out.a.x) && Number.isFinite(out.b.x), 'both placed');
});

test('a relation island with no area is left alone, not hung on', () => {
    const nodes = { x: { id: 'x', type: 'item' }, y: { id: 'y', type: 'item' } };
    const edges = [
        { type: 'in', source: 'x', target: 'y' },
        { type: 'in', source: 'y', target: 'x' },
    ];
    assertEq(GraphRelativeLayout.parentOf('x', edges, nodes), null);
    assertEq(GraphRelativeLayout.layoutPositions(nodes, edges, {}), {});
});

test('apply() seeds children and keeps them out of the global solver', () => {
    const updated = [];
    const previousGraphManager = globalThis.graphManager;
    globalThis.graphManager = {
        _graphNodesObj: NODES,
        _graphEdgesArr: EDGES,
        network: {
            body: {
                nodes: { area_hall: { x: 0, y: 0 }, area_cellar: { x: 800, y: 600 } },
                data: { nodes: { update: (u) => updated.push(...u) } },
            },
            getPositions: () => POS,
        },
    };
    try {
        const count = GraphRelativeLayout.apply();
        assertEq(count, updated.length, 'returns what it placed');
        assertTrue(updated.every((u) => u.id !== 'area_hall'), 'areas untouched');
        // Not `fixed` (the player can drag them); simply not pulled by the global
        // field, which is what would drag them to the middle.
        assertTrue(updated.every((u) => u.fixed === false && u.physics === false),
            'children stay out of the global solver');
        assertTrue(updated.some((u) => u.id === 'item_bag'), 'the carried bag was placed');
    } finally {
        globalThis.graphManager = previousGraphManager;
    }
});

test('a child holds its offset from the parent and follows it', () => {
    GraphRelativeLayout._offsets = null;
    const moved = [];
    const positions = {
        area_hall: { x: 0, y: 0 },
        item_lamp: { x: 4000, y: 0 },   // flung across the map
        item_oil: { x: 0, y: 60 },      // still tucked in the lamp
    };
    const previousGraphManager = globalThis.graphManager;
    globalThis.graphManager = {
        _graphNodesObj: NODES,
        _graphEdgesArr: EDGES,
        network: {
            body: { nodes: positions, data: { nodes: { update: () => {} } } },
            moveNode: (id, x, y) => { positions[id] = { x, y }; moved.push({ id, x, y }); },
        },
    };
    try {
        // Seed: the lamp takes its place under the hall, the oil inside the lamp.
        GraphRelativeLayout.apply();
        assertTrue(!!GraphRelativeLayout._offsets.item_lamp, 'the lamp has an offset');
        assertTrue(Math.abs(GraphRelativeLayout._offsets.item_lamp.dx) < 0.5, 'below its parent');

        // Physics flings the lamp away; the follow pass brings it back onto its
        // offset, and the oil rides along rather than staying behind.
        positions.item_lamp = { x: 4000, y: 0 };
        const fixed = GraphRelativeLayout.follow();
        assertTrue(fixed >= 2, 'both lamp and oil re-placed');
        assertTrue(Math.abs(positions.item_lamp.x) < 1, 'the lamp is back with the hall');
        assertTrue(Math.abs(positions.item_oil.x) < 60, 'the oil stayed in the lamp');
    } finally {
        globalThis.graphManager = previousGraphManager;
        GraphRelativeLayout._offsets = null;
    }
});

test('an idle tick costs nothing and does not re-place anything', () => {
    GraphRelativeLayout._offsets = null;
    const moved = [];
    const positions = { area_hall: { x: 0, y: 0 }, item_lamp: { x: 0, y: 58 } };
    const previousGraphManager = globalThis.graphManager;
    globalThis.graphManager = {
        _graphNodesObj: NODES,
        _graphEdgesArr: EDGES,
        _physicsEnabled: true,
        network: {
            body: { nodes: positions, data: { nodes: { update: () => {} } } },
            moveNode: (id, x, y) => { positions[id] = { x, y }; moved.push(id); },
        },
    };
    try {
        GraphRelativeLayout.apply();
        moved.length = 0;
        GraphRelativeLayout.follow();
        const afterSettled = moved.length;
        const second = GraphRelativeLayout.follow();
        assertEq(second, 0, 'a settled graph re-places nothing');
        assertEq(moved.length, afterSettled, 'no extra moveNode calls');
    } finally {
        globalThis.graphManager = previousGraphManager;
        GraphRelativeLayout._offsets = null;
    }
});

test('a big graph degrades by queueing the rest for the next tick', () => {
    GraphRelativeLayout._offsets = null;
    const nodes = { area_a: { type: 'area' } };
    const edges = [];
    for (let i = 0; i < 5; i++) {
        nodes['item_' + i] = { type: 'item' };
        edges.push({ type: 'in', source: 'item_' + i, target: 'area_a' });
    }
    const positions = { area_a: { x: 0, y: 0 } };
    for (let i = 0; i < 5; i++) positions['item_' + i] = { x: 0, y: 0 };
    const previousGraphManager = globalThis.graphManager;
    const previousBudget = GraphRelativeLayout.FOLLOW_BUDGET;
    globalThis.graphManager = {
        _graphNodesObj: nodes,
        _graphEdgesArr: edges,
        _physicsEnabled: true,
        network: {
            body: { nodes: positions, data: { nodes: { update: () => {} } } },
            moveNode: (id, x, y) => { positions[id] = { x, y }; },
        },
    };
    try {
        GraphRelativeLayout.apply();
        GraphRelativeLayout.FOLLOW_BUDGET = 2;
        const first = GraphRelativeLayout.follow();
        assertTrue(first <= 2, 'first tick respects the budget');
        assertTrue((GraphRelativeLayout._pendingParents || []).length > 0, 'the rest is queued');
        GraphRelativeLayout.FOLLOW_BUDGET = previousBudget;
        const second = GraphRelativeLayout.follow();
        assertTrue(second > 0, 'the next tick continues');
        assertEq(GraphRelativeLayout._pendingParents, null, 'the queue drains');
    } finally {
        GraphRelativeLayout.FOLLOW_BUDGET = previousBudget;
        globalThis.graphManager = previousGraphManager;
        GraphRelativeLayout._offsets = null;
    }
});

test('a dragged child keeps the place it was dropped in', () => {
    GraphRelativeLayout._offsets = null;
    const positions = { area_hall: { x: 0, y: 0 }, item_lamp: { x: 0, y: 58 } };
    const previousGraphManager = globalThis.graphManager;
    globalThis.graphManager = {
        _graphNodesObj: NODES,
        _graphEdgesArr: EDGES,
        network: {
            body: { nodes: positions, data: { nodes: { update: () => {} } } },
            moveNode: (id, x, y) => { positions[id] = { x, y }; },
        },
    };
    try {
        GraphRelativeLayout.apply();
        positions.item_lamp = { x: 220, y: 30 };          // dropped to the side
        GraphRelativeLayout.rememberDrop(['item_lamp']);
        assertEq(GraphRelativeLayout._offsets.item_lamp, { dx: 220, dy: 30 });
        GraphRelativeLayout.follow();
        assertEq(positions.item_lamp, { x: 220, y: 30 }, 'it stays where it was dropped');
        positions.area_hall = { x: 500, y: 500 };          // the room moves
        GraphRelativeLayout.follow();
        assertEq(positions.item_lamp, { x: 720, y: 530 }, 'and follows the room from there');
    } finally {
        globalThis.graphManager = previousGraphManager;
        GraphRelativeLayout._offsets = null;
    }
});

test('hierarchical level edges run parent -> child whichever way `in` is stored', () => {
    const nodes = {
        area_hall: { type: 'area' }, item_lamp: { type: 'item' }, item_oil: { type: 'item' },
        char_kael: { type: 'character' }, item_bag: { type: 'item' },
    };
    const edges = [
        { type: 'in', source: 'item_lamp', target: 'area_hall' },   // child -> parent
        { type: 'in', source: 'item_lamp', target: 'item_oil' },    // parent -> child (bug-44 style)
        { type: 'carrying', source: 'item_bag', target: 'char_kael' },
        { type: 'in', source: 'char_kael', target: 'area_hall' },
    ];
    // child -> parent is flipped so the area sits above its lamp.
    const a = GraphRelativeLayout.levelEdge('item_lamp', 'area_hall', nodes, edges);
    assertEq(a, { from: 'area_hall', to: 'item_lamp', flipped: true });
    // parent -> child is already the right way round and is left alone.
    const b = GraphRelativeLayout.levelEdge('item_lamp', 'item_oil', nodes, edges);
    assertEq(b, { from: 'item_lamp', to: 'item_oil', flipped: false });
    // a carried item hangs below its carrier.
    const c = GraphRelativeLayout.levelEdge('item_bag', 'char_kael', nodes, edges);
    assertEq(c, { from: 'char_kael', to: 'item_bag', flipped: true });
    // an unrelated pair is left as stored.
    const d = GraphRelativeLayout.levelEdge('area_hall', 'char_kael', nodes, edges);
    assertEq(d.from, 'area_hall');
});

test('levels mode is off unless the setting says so', () => {
    // The sandbox has no `config`, which is the free-layout default.
    assertFalse(GraphRelativeLayout.levelsMode(), 'free by default');
});

test('room-to-door edges put the door below the room in level mode', () => {
    const nodes = { area_a: { type: 'area' }, area_b: { type: 'area' }, way_door: { type: 'way' } };
    // Stored both ways round (a door opens from either side).
    assertEq(GraphRelativeLayout.connectionLevelEdge('area_a', 'way_door', nodes),
        { from: 'area_a', to: 'way_door', flipped: false });
    assertEq(GraphRelativeLayout.connectionLevelEdge('way_door', 'area_b', nodes),
        { from: 'area_b', to: 'way_door', flipped: true });
    // A non-way pair is left alone.
    assertEq(GraphRelativeLayout.connectionLevelEdge('area_a', 'area_b', nodes),
        { from: 'area_a', to: 'area_b', flipped: false });
});

test('a frozen node keeps its own place (no orbit, no offset)', () => {
    GraphRelativeLayout._offsets = null;
    const frozenNodes = {
        area_hall: { type: 'area' },
        item_lamp: { type: 'item', properties: { central_gravity_enabled: false } },
        char_kael: { type: 'character' },
    };
    const edges = [
        { type: 'in', source: 'item_lamp', target: 'area_hall' },
        { type: 'in', source: 'char_kael', target: 'area_hall' },
    ];
    const updated = [];
    const previousGraphManager = globalThis.graphManager;
    globalThis.graphManager = {
        _graphNodesObj: frozenNodes,
        _graphEdgesArr: edges,
        network: {
            body: {
                nodes: { area_hall: { x: 0, y: 0 }, item_lamp: { x: 999, y: 999 }, char_kael: { x: 0, y: 0 } },
                data: { nodes: { update: (u) => updated.push(...u) } },
            },
            getPositions: () => ({ area_hall: { x: 0, y: 0 } }),
        },
    };
    try {
        GraphRelativeLayout.apply();
        assertTrue(!updated.some(u => u.id === 'item_lamp'), 'the frozen node is not repositioned');
        assertTrue(!GraphRelativeLayout._offsets.item_lamp, 'and gets no offset, so follow ignores it');
        assertTrue(updated.some(u => u.id === 'char_kael'), 'others still orbit');
    } finally {
        globalThis.graphManager = previousGraphManager;
        GraphRelativeLayout._offsets = null;
    }
});

test('a dragged frozen node has its position written so a reload keeps it', () => {
    const previousGraphManager = globalThis.graphManager;
    globalThis.graphManager = {
        _graphNodesObj: {
            way_door: { type: 'way', properties: { central_gravity_enabled: false } },
            item_loose: { type: 'item' },
        },
        _graphEdgesArr: [],
        network: { body: { nodes: { way_door: { x: 12.34, y: 56.78 }, item_loose: { x: 1, y: 2 } } } },
    };
    try {
        const ops = GraphRelativeLayout.frozenDropOps(['way_door', 'item_loose']);
        assertEq(ops.length, 1, 'only the frozen node is saved');
        assertEq(ops[0].payload.node_id, 'way_door');
        assertEq(ops[0].payload.patch.properties, { x: 12.3, y: 56.8 });
    } finally {
        globalThis.graphManager = previousGraphManager;
    }
});

test('a parent can set how its own contents are arranged', () => {
    const nodes = {
        area_a: { type: 'area', properties: { layout_child_distance: 90, layout_child_spacing: 40, layout_max_radius: 200 } },
        item_0: { type: 'item' }, item_1: { type: 'item' },
    };
    const edges = [
        { type: 'in', source: 'item_0', target: 'area_a' },
        { type: 'in', source: 'item_1', target: 'area_a' },
    ];
    const out = GraphRelativeLayout.layoutPositions(nodes, edges, { area_a: { x: 0, y: 0 } });
    const r = Math.round(Math.hypot(out.item_0.x, out.item_0.y));
    // max(90 requested, 2 children * 40 spacing / 2pi = 13) = 90
    assertEq(r, 90, 'the parent controls its own ring');
});

test('a child can override its own distance from the parent', () => {
    const nodes = { area_a: { type: 'area', properties: { layout_child_distance: 90 } }, item_0: { type: 'item', properties: { layout_distance: 140 } } };
    const edges = [{ type: 'in', source: 'item_0', target: 'area_a' }];
    const out = GraphRelativeLayout.layoutPositions(nodes, edges, { area_a: { x: 0, y: 0 } });
    assertEq(Math.round(Math.hypot(out.item_0.x, out.item_0.y)), 140, 'the child wins for itself');
});

test('a static node is recognised however it is declared', () => {
    assertTrue(GraphRelativeLayout.isStatic({ properties: { central_gravity_enabled: false } }), 'physics off');
    assertTrue(GraphRelativeLayout.isStatic({ properties: { layout_static: true } }), 'layout_static');
    assertFalse(GraphRelativeLayout.isStatic({ properties: {} }), 'default is dynamic');
    assertFalse(GraphRelativeLayout.isStatic(null), 'missing node is dynamic');
});

test('the item-edge-length setting drives the orbit (Hug Parent vs Stretched)', () => {
    const nodes = { area_a: { type: 'area' }, item_0: { type: 'item' }, item_1: { type: 'item' } };
    const edges = [
        { type: 'in', source: 'item_0', target: 'area_a' },
        { type: 'in', source: 'item_1', target: 'area_a' },
    ];
    const ringRadiusFor = (length) => {
        const previous = globalThis.config;
        globalThis.config = { graphItemEdgeLength: length };
        try {
            const out = GraphRelativeLayout.layoutPositions(nodes, edges, { area_a: { x: 0, y: 0 } });
            return Math.round(Math.hypot(out.item_0.x, out.item_0.y));
        } finally {
            globalThis.config = previous;
        }
    };
    const hug = ringRadiusFor(20);
    const standard = ringRadiusFor(60);
    const stretched = ringRadiusFor(200);
    assertTrue(hug < standard, `a low setting hugs the parent (${hug} < ${standard})`);
    assertTrue(stretched > standard, `a high setting stretches the ring (${stretched} > ${standard})`);
    // The default (no config at all) is the classic orbit.
    assertTrue(ringRadiusFor(undefined) === standard, 'no setting behaves like the default');
});

test('re-deriving the arrangement drops remembered offsets', () => {
    GraphRelativeLayout._offsets = { some: { dx: 1, dy: 1 } };
    GraphRelativeLayout._lastParentPos = new Map([['a', { x: 0, y: 0 }]]);
    GraphRelativeLayout.reseed();
    assertEq(GraphRelativeLayout._offsets, null);
    assertEq(GraphRelativeLayout._lastParentPos, null);
});

test('attach() registers the follow hooks once', () => {
    const handlers = {};
    const network = { on: (name, fn) => { handlers[name] = fn; } };
    GraphRelativeLayout.attach(network);
    GraphRelativeLayout.attach(network);         // idempotent
    assertTrue(!!handlers.stabilizationIterationsDone, 'settle hook');
    assertTrue(!!handlers.dragEnd, 'drag hook');
});
