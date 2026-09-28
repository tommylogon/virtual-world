/**
 * test_item_containment.js — the ONE item-containment walk (task-493).
 *
 * The engine's `engine/item_reach.py` is the other half of this rule. Before
 * this module the client had its own, and the two disagreed on both axes that
 * matter: depth (the client looked one level, the engine any) and state (the
 * client barely looked, the engine seals closed/locked/hidden). So these tests
 * pin the client's half to the engine's semantics, and the failure they exist to
 * prevent is a prompt that lists a battery inside a locked cabinet — or omits
 * a part three levels down.
 */
'use strict';

const IC = window.ItemContainment;

function makeGraph() {
    const nodes = {};
    const edges = [];
    return {
        nodes,
        edges,
        item(id, name, props) {
            nodes[id] = { id, type: 'item', name, properties: props || {} };
            return id;
        },
        way(id) {
            nodes[id] = { id, type: 'way', name: id, properties: {} };
            return id;
        },
        in_(child, parent) {
            edges.push({ source: child, target: parent, type: 'in' });
        },
        spatial(child, parent, rel) {
            edges.push({ source: child, target: parent, type: rel || 'on' });
        },
        getNode: (id) => nodes[id] || null,
    };
}

function ids(list) {
    return list.map(i => i.id);
}

// ── the state gates ────────────────────────────────────────────────────────

test('a hidden node is pruned, and so is everything inside it', () => {
    const g = makeGraph();
    g.item('a', 'Box', { current_state: 'hidden' });
    g.item('b', 'Part', {});
    g.in_('b', 'a');
    assertEq(ids(IC.walkContents('a', g)), [], 'a hidden branch is entirely pruned');
});

test('a closed container is listed but its contents are sealed', () => {
    const g = makeGraph();
    g.item('a', 'Case', { current_state: 'closed' });
    g.item('b', 'Part', {});
    g.in_('b', 'a');
    const root = IC.collectReachable(['a'], g);
    assertEq(ids(root), ['a'], 'the closed case is still there');
    assertEq(ids(root.filter(i => i.depth > 0)), [], 'but what is inside is not');
});

test('locked and sealed seal too', () => {
    for (const state of ['locked', 'sealed']) {
        const g = makeGraph();
        g.item('a', 'Chest', { current_state: state });
        g.item('b', 'Coin', {});
        g.in_('b', 'a');
        assertEq(ids(IC.walkContents('a', g)), [], `${state} seals its contents`);
    }
});

test('the boolean locked property seals as well as the state', () => {
    const g = makeGraph();
    g.item('a', 'Safe', { current_state: 'normal', locked: true });
    g.item('b', 'Coin', {});
    g.in_('b', 'a');
    assertEq(ids(IC.walkContents('a', g)), [], 'locked: true seals its contents');
});

test('an open container lets its contents through', () => {
    const g = makeGraph();
    g.item('a', 'Pack', { current_state: 'normal' });
    g.item('b', 'Rope', {});
    g.in_('b', 'a');
    assertEq(ids(IC.walkContents('a', g)), ['b'], 'an open pack shows its contents');
});

test('the boolean hidden property is deliberately ignored', () => {
    // The engine honours `current_state == 'hidden'` only. Honouring the
    // boolean here would make the client disagree with it in the other
    // direction, which is the same bug wearing a different hat.
    const g = makeGraph();
    g.item('a', 'Box', { hidden: true, current_state: 'normal' });
    g.item('b', 'Part', {});
    g.in_('b', 'a');
    assertEq(ids(IC.walkContents('a', g)), ['b'], 'visibility follows the state machine');
});

test('state matching is case- and whitespace-insensitive', () => {
    assertTrue(IC.isOpen({ properties: { current_state: ' Closed ' } }) === false, 'CLOSED seals');
    assertTrue(IC.isOpen({ properties: { current_state: 'NORMAL' } }) === true, 'NORMAL opens');
});

// ── depth: the axis the client got wrong ───────────────────────────────────

test('a part nested three deep is still found', () => {
    const g = makeGraph();
    g.item('phone', 'Phone', { current_state: 'normal' });
    g.item('case', 'Back plate', { current_state: 'normal' });
    g.item('battery', 'Battery', { current_state: 'normal' });
    g.in_('case', 'phone');
    g.in_('battery', 'case');
    const found = IC.collectReachable(['phone'], g);
    assertEq(ids(found.filter(i => i.depth > 0)), ['case', 'battery'], 'both levels are listed');
    assertEq(found.find(i => i.id === 'battery').depth, 2, 'and the depth is reported');
});

test('depth stops at a sealed ancestor, not at a fixed level', () => {
    const g = makeGraph();
    g.item('phone', 'Phone', { current_state: 'normal' });
    g.item('case', 'Back plate', { current_state: 'locked' });
    g.item('battery', 'Battery', {});
    g.in_('case', 'phone');
    g.in_('battery', 'case');
    assertEq(ids(IC.collectReachable(['phone'], g).filter(i => i.depth > 0)),
        ['case'], 'the locked plate shows; the cell behind it does not');
});

test('maxDepth bounds the walk when asked', () => {
    const g = makeGraph();
    g.item('a', 'A', { current_state: 'normal' });
    g.item('b', 'B', { current_state: 'normal' });
    g.item('c', 'C', { current_state: 'normal' });
    g.in_('b', 'a');
    g.in_('c', 'b');
    assertEq(ids(IC.walkContents('a', { ...g, maxDepth: 0 })), [], 'the parent itself only');
    assertEq(ids(IC.walkContents('a', { ...g, maxDepth: 1 })), ['b'], 'depth 1 stops one level in');
    assertEq(ids(IC.walkContents('a', { ...g, maxDepth: 2 })), ['b', 'c'], 'depth 2 reaches the grandchild');
});

test('a containment cycle does not hang', () => {
    const g = makeGraph();
    g.item('a', 'A', { current_state: 'normal' });
    g.item('b', 'B', { current_state: 'normal' });
    g.in_('b', 'a');
    g.in_('a', 'b');
    assertEq(ids(IC.collectReachable(['a'], g).filter(i => i.depth > 0)), ['b'], 'the walk terminates');
});

test('a node is listed once even if several edges claim it', () => {
    const g = makeGraph();
    g.item('phone', 'Phone', { current_state: 'normal' });
    g.item('battery', 'Battery', {});
    g.in_('battery', 'phone');
    g.in_('battery', 'phone');
    assertEq(ids(IC.collectReachable(['phone'], g).filter(i => i.depth > 0)), ['battery']);
});

// ── only `in` counts as containment ───────────────────────────────────────

test('a spatial edge is not containment', () => {
    const g = makeGraph();
    g.item('table', 'Table', { current_state: 'normal' });
    g.item('mug', 'Mug', {});
    g.spatial('mug', 'table', 'on');
    assertEq(ids(IC.walkContents('table', g)), [], 'on/under/behind are placement, not inside');
});

test('a non-item child is not listed', () => {
    const g = makeGraph();
    g.item('box', 'Box', { current_state: 'normal' });
    g.way('way_in_box');
    g.in_('way_in_box', 'box');
    assertEq(ids(IC.walkContents('box', g)), [], 'only item nodes come back');
});

// ── roots, and the ordering the engine uses ───────────────────────────────

test('a carried root is listed even when it is sealed', () => {
    const g = makeGraph();
    g.item('safe', 'Safe', { current_state: 'locked' });
    assertEq(ids(IC.collectReachable(['safe'], g)), ['safe'], 'holding a locked safe shows the safe');
});

test('roots come out in the order given, each expanded once', () => {
    const g = makeGraph();
    g.item('phone', 'Phone', { current_state: 'normal' });
    g.item('battery', 'Battery', {});
    g.item('rope', 'Rope', {});
    g.in_('battery', 'phone');
    g.in_('rope', 'phone');
    const out = ids(IC.collectReachable(['phone', 'rope'], g));
    assertEq(out, ['phone', 'battery', 'rope'], 'carried-first order, contents after their root');
});

test('a root that is not an item is skipped rather than thrown on', () => {
    const g = makeGraph();
    g.way('way_1');
    g.item('battery', 'Battery', {});
    assertEq(ids(IC.collectReachable(['way_1', 'nope'], g)), [], 'bad roots are simply not listed');
});

test('an empty graph is empty, not an error', () => {
    assertEq(IC.collectReachable([], { getNode: () => null, edges: [] }), []);
    assertEq(IC.walkContents('anything', { getNode: () => null, edges: [] }), []);
});
