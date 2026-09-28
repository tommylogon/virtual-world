/**
 * Unit tests for the scope tree's pure rules (task-397 step 4).
 *
 * The panel's whole behaviour is "nest a flat list, then draw the rows that are
 * currently visible". Both halves are pure, so they are checked here rather than
 * by eye in a browser — including the awkward inputs a hand-edited manifest
 * produces: a child listed before its parent, a parent that does not exist, and
 * a cycle.
 */
'use strict';
const ST = window.GraphScopeTree;

const WORLD = [
    { id: 'county', name: 'Riverside County', kind: 'settlement', state: 'materialized', parent_id: null, depth: 0, area_count: 2, character_count: 0, item_count: 3 },
    { id: 'millbrook', name: 'Millbrook Falls', kind: 'settlement', state: 'materialized', parent_id: 'county', depth: 1, area_count: 40, character_count: 3, item_count: 90, has_character: true },
    { id: 'downtown', name: 'Downtown District', kind: 'district', state: 'materialized', parent_id: 'county', depth: 1, area_count: 12, character_count: 0, item_count: 20 },
    { id: 'pines', name: 'The Pines', kind: 'building', state: 'materialized', parent_id: 'downtown', depth: 2, area_count: 6, character_count: 1, item_count: 14, has_character: true },
    { id: 'pines_3b', name: 'Apartment 3B', kind: 'room', state: 'unmade', parent_id: 'pines', depth: 3, area_count: 0, character_count: 0, item_count: 0 },
];

test('the flat list nests into a tree by parent_id', () => {
    const tree = ST.buildTree(WORLD);
    assertEq(tree.children.length, 1, 'one root scope');
    assertEq(tree.children[0].id, 'county', 'the root scope is the parentless one');

    const downtown = tree.children[0].children.find(c => c.id === 'downtown');
    assertEq(downtown.children.map(c => c.id), ['pines'], 'pines hangs off downtown');
    assertEq(downtown.children[0].children.map(c => c.id), ['pines_3b'], 'and 3B off pines');
});

test('the tree does not depend on the order the list arrived in', () => {
    const shuffled = [WORLD[4], WORLD[1], WORLD[3], WORLD[0], WORLD[2]];
    const rows = ST.visibleRows(ST.buildTree(shuffled), new Set(), '');
    assertEq(rows.map(r => r.id),
        ['county', 'millbrook', 'downtown', 'pines', 'pines_3b'],
        'a child listed before its parent still nests');
});

test('a scope whose parent is missing is kept, at the top level', () => {
    const tree = ST.buildTree([
        { id: 'orphan', name: 'Orphan Zone', parent_id: 'nowhere', state: 'materialized' },
    ]);
    assertEq(tree.children.map(c => c.id), ['orphan'], 'not dropped');
});

test('a scope that lists itself as its own parent is kept, at the top level', () => {
    const tree = ST.buildTree([{ id: 'loop', name: 'Loop', parent_id: 'loop' }]);
    assertEq(tree.children.map(c => c.id), ['loop'], 'not dropped or recursed into');
});

test('a parent cycle does not hang the tree', () => {
    const tree = ST.buildTree([
        { id: 'a', name: 'A', parent_id: 'b' },
        { id: 'b', name: 'B', parent_id: 'a' },
    ]);
    // Every scope still appears exactly once, so the panel can show all of them.
    const rows = ST.visibleRows(tree, new Set(), '');
    assertEq(rows.map(r => r.id).sort(), ['a', 'b'], 'both present, neither duplicated');
});

test('rows come out parents-first, indented by depth', () => {
    const rows = ST.visibleRows(ST.buildTree(WORLD), new Set(), '');
    assertEq(rows.map(r => r.id),
        ['county', 'millbrook', 'downtown', 'pines', 'pines_3b'], 'order');
    assertEq(rows.map(r => r.depth), [0, 1, 1, 2, 3], 'depths');
});

test('collapsing a scope hides what is inside, never the scope itself', () => {
    const rows = ST.visibleRows(ST.buildTree(WORLD), new Set(['downtown']), '');
    assertEq(rows.map(r => r.id), ['county', 'millbrook', 'downtown'],
        'the subtree under downtown is hidden, downtown is still a card');
    assertEq(rows[2].collapsed, true, 'and it is marked collapsed');
});

test('a selected scope is marked, so the panel can show which one is loaded', () => {
    const rows = ST.visibleRows(ST.buildTree(WORLD), new Set(), 'pines');
    assertEq(rows.map(r => r.selected), [false, false, false, true, false], 'only pines');
});

test('a collapsed scope has nothing to expand', () => {
    const rows = ST.visibleRows(ST.buildTree([{ id: 'leaf', name: 'Leaf', parent_id: null }]),
        new Set(['leaf']), '');
    assertEq(rows[0].hasChildren, false, 'a leaf cannot be collapsed open');
    assertEq(rows[0].collapsed, false, 'so it is not reported as collapsed');
});

test('toggleCollapsed returns a new set and leaves the old one alone', () => {
    const before = new Set(['downtown']);
    const after = ST.toggleCollapsed(before, 'pines');
    assertTrue(after.has('pines'), 'pines opened');
    assertTrue(after.has('downtown'), 'downtown untouched');
    assertFalse(before.has('pines'), 'the original set was not mutated');
    assertEq(ST.toggleCollapsed(after, 'pines').has('pines'), false, 'toggles closed');
});

test('an unmade scope says so instead of showing a count of nothing', () => {
    const rows = ST.visibleRows(ST.buildTree(WORLD), new Set(), '');
    const unmade = rows.find(r => r.id === 'pines_3b');
    assertEq(unmade.unmade, true, 'flagged');
    assertEq(ST.rowLabel(unmade), 'Apartment 3B — not built', 'spells it out');
});

test('a materialized scope reports what the manifest says it holds', () => {
    const rows = ST.visibleRows(ST.buildTree(WORLD), new Set(), '');
    assertEq(ST.rowLabel(rows.find(r => r.id === 'county')),
        'Riverside County — 2 areas · 3 items', 'counts');
    assertEq(ST.rowLabel(rows.find(r => r.id === 'millbrook')),
        'Millbrook Falls — 40 areas · 90 items · 3 here now', 'and occupancy');
});

test('singular counts read as one', () => {
    const rows = ST.visibleRows(ST.buildTree([{
        id: 'one', name: 'One Room', state: 'materialized',
        area_count: 1, item_count: 1, character_count: 1, has_character: true,
    }]), new Set(), '');
    assertEq(ST.rowLabel(rows[0]), 'One Room — 1 area · 1 item · 1 here now', 'no plural s');
});

test('a scope with no items and nobody in it does not list zeroes', () => {
    const rows = ST.visibleRows(ST.buildTree([{
        id: 'bare', name: 'Bare', state: 'materialized', area_count: 5,
        item_count: 0, character_count: 0,
    }]), new Set(), '');
    assertEq(ST.rowLabel(rows[0]), 'Bare — 5 areas', 'items and people are omitted');
});

test('a duplicate id is kept once', () => {
    const tree = ST.buildTree([
        { id: 'x', name: 'X', parent_id: null },
        { id: 'x', name: 'X again', parent_id: null },
    ]);
    assertEq(tree.children.length, 1, 'one card, not two');
});

test('an empty or missing list is an empty tree, not a crash', () => {
    assertEq(ST.buildTree([]).children.length, 0, 'empty list');
    assertEq(ST.buildTree(null).children.length, 0, 'null list');
    assertEq(ST.visibleRows(null, null, '').length, 0, 'no tree at all');
});
