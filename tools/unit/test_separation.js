/**
 * Unit tests for graph/separation.js.
 *
 * Only the interesting edges: unconnected nodes push apart up to `min`, an edge
 * exempts its pair, a pair beyond `max` is ignored, and areas/the world's
 * anchors never move. `layoutPositions` must apply the same relaxation.
 */

const SEP = () => globalThis.GraphSeparation;

test('two unconnected nodes closer than min push apart', () => {
    const nodes = { a: { type: 'item', name: '' }, b: { type: 'item', name: '' } };
    const out = SEP().resolve(nodes, [], { a: { x: 0, y: 0 }, b: { x: 10, y: 0 } },
        { min: 100, max: 300, strength: 0.6, iterations: 6 });
    const dist = Math.hypot(out.a.x - out.b.x, out.a.y - out.b.y);
    assertTrue(dist > 10, `moved apart (${dist})`);
    assertTrue(dist <= 100.5, `but not past min (${dist})`);
    // Both were movable, so the pair's midpoint is preserved (sum stays 10).
    assertTrue(Math.abs((out.a.x + out.b.x) - 10) < 0.5, 'the midpoint is preserved');
});

test('an edge exempts its pair from separation', () => {
    const nodes = { a: { type: 'item' }, b: { type: 'item' } };
    const edges = [{ type: 'in', source: 'a', target: 'b' }];
    const out = SEP().resolve(nodes, edges, { a: { x: 0, y: 0 }, b: { x: 10, y: 0 } },
        { min: 100, max: 300, strength: 0.6, iterations: 6 });
    assertEq(out.a, { x: 0, y: 0 });
    assertEq(out.b, { x: 10, y: 0 });
});

test('a pair further apart than max is ignored', () => {
    const nodes = { a: { type: 'item' }, b: { type: 'item' } };
    const out = SEP().resolve(nodes, [], { a: { x: 0, y: 0 }, b: { x: 400, y: 0 } },
        { min: 100, max: 260, strength: 0.6, iterations: 6 });
    assertEq(out.b, { x: 400, y: 0 });
});

test('an area is an anchor: only the item moves off it', () => {
    const nodes = { area_1: { type: 'area' }, item_1: { type: 'item' } };
    const out = SEP().resolve(nodes, [], { area_1: { x: 0, y: 0 }, item_1: { x: 10, y: 0 } },
        { min: 120, max: 300, strength: 0.6, iterations: 6 });
    assertEq(out.area_1, { x: 0, y: 0 }, 'the area never moves');
    assertTrue(out.item_1.x > 110, `the item was pushed out (${out.item_1.x})`);
});

test('a frozen node keeps its place', () => {
    const nodes = { a: { type: 'item', properties: { central_gravity_enabled: false } }, b: { type: 'item' } };
    const out = SEP().resolve(nodes, [], { a: { x: 0, y: 0 }, b: { x: 10, y: 0 } },
        { min: 120, max: 300, strength: 0.6, iterations: 6 });
    assertEq(out.a, { x: 0, y: 0 });
    assertTrue(out.b.x > 110);
});

test('the same input resolves the same way twice', () => {
    const nodes = { a: { type: 'item' }, b: { type: 'item' }, c: { type: 'item' } };
    const input = { a: { x: 0, y: 0 }, b: { x: 5, y: 5 }, c: { x: 5, y: 0 } };
    const spec = { min: 80, max: 300, strength: 0.6, iterations: 6 };
    assertEq(SEP().resolve(nodes, [], input, spec), SEP().resolve(nodes, [], input, spec));
});

test('a long label is pushed further away than a short one', () => {
    assertTrue(SEP().radiusOf({ type: 'item', name: 'A very long item name indeed' })
        > SEP().radiusOf({ type: 'item', name: 'cup' }), 'label length matters');
});

test('the pull restores a displaced node to its layout target', () => {
    const nodes = { a: { type: 'item' }, b: { type: 'item' } };
    const positions = { a: { x: -10, y: 0 }, b: { x: 10, y: 0 } };
    const targets = { a: { x: -30, y: 0 }, b: { x: 30, y: 0 } };
    const base = { min: 100, max: 300, strength: 0.6, iterations: 6, targets };
    const loose = SEP().resolve(nodes, [], positions, { ...base, pull: 0 });
    const held = SEP().resolve(nodes, [], positions, { ...base, pull: 0.3 });
    const spread = (out) => Math.abs(out.a.x) + Math.abs(out.b.x);
    assertTrue(spread(held) < spread(loose),
        `pull keeps them nearer their target (${spread(held)} < ${spread(loose)})`);
    assertTrue(Math.hypot(held.a.x - held.b.x, held.a.y - held.b.y) > 40, 'still separated');
});

test('the pull never moves a node repulsion did not touch', () => {
    const nodes = { a: { type: 'item' }, b: { type: 'item' } };
    const positions = { a: { x: 200, y: 0 }, b: { x: 320, y: 0 } };
    const spec = {
        min: 100, max: 300, strength: 0.6, iterations: 6, pull: 0.3,
        targets: { a: { x: 0, y: 0 }, b: { x: 0, y: 0 } },
    };
    const out = SEP().resolve(nodes, [], positions, spec);
    // 120 apart, no overlap: untouched even though a target was supplied.
    assertEq(out.a, { x: 200, y: 0 });
    assertEq(out.b, { x: 320, y: 0 });
});

test('separation is off unless the setting says on', () => {
    const previous = globalThis.config;
    try {
        globalThis.config = undefined;
        assertFalse(SEP().enabled(), 'no config -> off');
        globalThis.config = { graphRepelEnabled: false };
        assertFalse(SEP().enabled(), 'explicitly off');
        globalThis.config = { graphRepelEnabled: true };
        assertTrue(SEP().enabled(), 'explicitly on');
    } finally {
        globalThis.config = previous;
    }
});

test('layoutPositions relaxes overlapping contents when enabled', () => {
    const previous = globalThis.config;
    const nodes = {
        area_a: { type: 'area', properties: { layout_child_distance: 30 } },
        item_0: { type: 'item' },
        item_1: { type: 'item' },
    };
    const edges = [
        { type: 'in', source: 'item_0', target: 'area_a' },
        { type: 'in', source: 'item_1', target: 'area_a' },
    ];
    const positions = { area_a: { x: 0, y: 0 } };
    try {
        globalThis.config = { graphItemEdgeLength: 60 };
        const before = GraphRelativeLayout.layoutPositions(nodes, edges, positions);
        const beforeDist = Math.hypot(before.item_0.x - before.item_1.x, before.item_0.y - before.item_1.y);
        globalThis.config = { graphItemEdgeLength: 60, graphRepelEnabled: true, graphRepelMin: 100, graphRepelMax: 300 };
        const after = GraphRelativeLayout.layoutPositions(nodes, edges, positions);
        const afterDist = Math.hypot(after.item_0.x - after.item_1.x, after.item_0.y - after.item_1.y);
        assertTrue(afterDist > beforeDist, `separated (${beforeDist} -> ${afterDist})`);
        assertEq(after.area_a, { x: 0, y: 0 }, 'the area is untouched');
    } finally {
        globalThis.config = previous;
        GraphRelativeLayout._depthCache = null;
        GraphRelativeLayout._parentCache = null;
    }
});
