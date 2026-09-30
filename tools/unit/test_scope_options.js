/**
 * task-627: the scope picker used to render a hierarchy as a FLAT option list
 * with leading non-breaking spaces ("\u00A0".repeat(depth * 2) + name), so the
 * tree was invisible whitespace the player had to count. It now nests via
 * <optgroup>.
 *
 * This tests the pure builder rather than the live picker on purpose: a world
 * with zero scopes exercises nothing, and the multi-scope world is not always
 * the one loaded. Verifying against whatever scenario happens to be open is the
 * exact mistake that produced this audit's four retractions.
 */
'use strict';
const _populate = window.ScopeOptions.populate;

/** Minimal fake element: enough for appendChild/label/value/textContent. */
function fakeEl(tag) {
    return {
        tagName: tag.toUpperCase(),
        label: '',
        value: '',
        textContent: '',
        children: [],
        appendChild(child) { this.children.push(child); return child; },
    };
}
function makeSel() {
    return { tagName: 'SELECT', children: [], appendChild(c) { this.children.push(c); return c; } };
}

/** Every option value in the tree, depth-first. */
function values(el) {
    const out = [];
    for (const c of el.children) {
        if (c.tagName === 'OPTION') out.push(c.value);
        else out.push(...values(c));
    }
    return out;
}

// --- the regression itself ----------------------------------------------------
test('depth-1 scopes nest inside an optgroup, not at the top level', () => {
    const sel = makeSel();
    _populate(sel, [
        { id: 's_root', name: 'Root Scope', depth: 0 },
        { id: 's_a', name: 'Zone A', depth: 1 },
    ], fakeEl);
    assertEq(sel.children.length, 2, 'children: one top option + one optgroup');
    assertEq(sel.children[0].tagName, 'OPTION', 'depth 0 stays a top-level option');
    assertEq(sel.children[1].tagName, 'OPTGROUP', 'depth 1 becomes an optgroup');
    assertEq(sel.children[1].children[0].textContent, 'Zone A', 'the option is nested in the group');
});

test('option text carries no leading non-breaking spaces any more', () => {
    const sel = makeSel();
    _populate(sel, [
        { id: 'a', name: 'A', depth: 0 },
        { id: 'b', name: 'B', depth: 1 },
        { id: 'c', name: 'C', depth: 2 },
    ], fakeEl);
    (function walk(el) {
        for (const c of el.children) {
            if (c.tagName === 'OPTION') {
                assertEq(/ /.test(c.textContent), false, 'no nbsp in ' + JSON.stringify(c.textContent));
                assertEq(c.textContent, c.textContent.trim(), 'no padding in ' + JSON.stringify(c.textContent));
            } else walk(c);
        }
    })(sel);
});

// --- shape ---------------------------------------------------------------------
test('depth 2 nests inside depth 1, not beside it', () => {
    const sel = makeSel();
    _populate(sel, [
        { id: 'r', name: 'R', depth: 0 },
        { id: 'z1', name: 'Z1', depth: 1 },
        { id: 's1', name: 'S1', depth: 2 },
    ], fakeEl);
    const zones = sel.children[1];
    assertEq(zones.tagName, 'OPTGROUP', 'Zones group holds Z1');
    const sub = zones.children.find(c => c.tagName === 'OPTGROUP');
    assertEq(!!sub, true, 'a Sub-zones group exists under Zones');
    assertEq(sub.children[0].textContent, 'S1', 'S1 is inside Sub-zones');
});

test('a sibling at a shallower depth closes the deeper branch', () => {
    const sel = makeSel();
    _populate(sel, [
        { id: 'r', name: 'R', depth: 0 },
        { id: 'z1', name: 'Z1', depth: 1 },
        { id: 's1', name: 'S1', depth: 2 },
        { id: 'z2', name: 'Z2', depth: 1 },
    ], fakeEl);
    const zones = sel.children.filter(c => c.tagName === 'OPTGROUP');
    assertEq(zones.length, 1, 'one Zones group holds both Z1 and Z2');
    assertEq(!!zones[0].children.find(c => c.tagName === 'OPTION' && c.value === 'z2'), true, 'Z2 sits in Zones');
    const sub = zones[0].children.find(c => c.tagName === 'OPTGROUP');
    assertEq(sub.children.length, 1, 'Sub-zones holds only S1, not Z2');
});

test('multiple roots each become their own top-level option', () => {
    const sel = makeSel();
    _populate(sel, [
        { id: 'r1', name: 'R1', depth: 0 },
        { id: 'z1', name: 'Z1', depth: 1 },
        { id: 'r2', name: 'R2', depth: 0 },
        { id: 'z2', name: 'Z2', depth: 1 },
    ], fakeEl);
    assertEq(values(sel).slice().sort().join(','), 'r1,r2,z1,z2', 'every scope reachable exactly once');
    assertEq(values(sel).length, 4, 'no scope duplicated');
});

// --- degenerate inputs --------------------------------------------------------
test('zero scopes renders nothing and reports 0', () => {
    const sel = makeSel();
    assertEq(_populate(sel, [], fakeEl), 0, 'reports zero');
    assertEq(sel.children.length, 0, 'select left empty for the caller to add whole-world');
});

test('undefined and null scope lists are tolerated', () => {
    assertEq(_populate(makeSel(), undefined, fakeEl), 0, 'undefined ok');
    assertEq(_populate(makeSel(), null, fakeEl), 0, 'null ok');
});

test('a missing depth is treated as depth 0 (top level)', () => {
    const sel = makeSel();
    _populate(sel, [{ id: 'x', name: 'X' }], fakeEl);
    assertEq(sel.children[0].tagName, 'OPTION', 'no depth means top level');
});

// --- flattenScopes: both API shapes -------------------------------------------
// The picker calls /api/world/scopes?flat=1, which is ALREADY flat and already
// carries `depth`. The first version of this helper only read `payload.children`
// (the non-flat endpoint), so the picker was handed an empty list and rendered
// nothing. Both shapes are pinned here so that cannot recur.
const _flatten = window.ScopeOptions.flattenScopes;

test('the FLAT payload is passed through untouched', () => {
    const flat = {
        scopes: [
            { id: 'world', name: 'World', depth: 0, parent_id: null },
            { id: 'woods', name: 'Woods', depth: 1, parent_id: 'world' },
        ],
    };
    const out = _flatten(flat);
    assertEq(out.length, 2, 'both scopes');
    assertEq(out[1].depth, 1, 'depth preserved, not recomputed');
    assertEq(out[1].parent_id, 'world', 'parent preserved');
});

test('the NESTED payload is walked into the same flat shape', () => {
    const nested = {
        scope: null,
        children: [{
            id: 'world', name: 'World', parent_id: null, state: 'materialized',
            children: ['camp', 'woods'],
        }],
    };
    const out = _flatten(nested);
    assertEq(out.length, 3, 'root plus two children');
    assertEq(out[0].id + ',' + out[0].depth, 'world,0', 'root at depth 0');
    assertEq(out[1].id + ',' + out[1].depth + ',' + out[1].parent_id, 'camp,1,world', 'child at depth 1 under world');
    assertEq(out[2].id + ',' + out[2].depth, 'woods,1', 'second child at depth 1');
});

test('a real two-level nested tree keeps its depth', () => {
    const nested = {
        children: [{
            id: 'world', name: 'World', children: [
                { id: 'goblin_camp', name: 'Goblin camp', children: ['test'] },
            ],
        }],
    };
    const out = _flatten(nested);
    const by = {}; out.forEach(s => { by[s.id] = s.depth; });
    assertEq(by.world, 0, 'world depth 0');
    assertEq(by.goblin_camp, 1, 'goblin_camp depth 1');
    assertEq(by.test, 2, 'grandchild depth 2');
});

test('an empty or malformed payload yields an empty list', () => {
    assertEq(_flatten(null).length, 0, 'null');
    assertEq(_flatten({}).length, 0, 'no keys');
    assertEq(_flatten({ scopes: [] }).length, 0, 'flat but empty');
});

test('round-trip: flatten then populate yields the same scope set', () => {
    const scopes = _flatten({ scopes: [
        { id: 'world', name: 'World', depth: 0 },
        { id: 'a', name: 'Zone A', depth: 1 },
        { id: 'b', name: 'Sub-zone', depth: 2 },
    ] });
    const sel = { tagName: 'SELECT', children: [], appendChild(c) { this.children.push(c); return c; } };
    const _mk = (tag) => ({ tagName: tag.toUpperCase(), label: '', value: '', textContent: '', children: [],
                            appendChild(c) { this.children.push(c); return c; } });
    _populate(sel, scopes, _mk);
    const ids = []; (function w(e) { for (const c of e.children) { if (c.tagName === 'OPTION') ids.push(c.value); else w(c); } })(sel);
    assertEq(ids.sort().join(','), 'a,b,world', 'all three scopes reachable in the picker');
});