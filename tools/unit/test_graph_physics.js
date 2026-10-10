/**
 * tools/unit/test_graph_physics.js — the one graph physics policy (task-765).
 *
 * The decision used to be spread over five files and written into a shared
 * boolean by nine call sites, so a reload could undo the toolbar toggle (the
 * saved "off" was read too late) and a load could leave the solver paused for
 * good. These tests pin the decision as a pure function of its inputs.
 */
'use strict';

test('physics runs by default when nothing gates it', () => {
    assertTrue(GraphPhysics.shouldRun({ userEnabled: true, layout: 'graph', overlay: 'none' }), 'plain graph');
});

test('the user off switch wins over everything', () => {
    assertFalse(GraphPhysics.shouldRun({ userEnabled: false, layout: 'graph', overlay: 'none' }), 'user off');
});

test('Hierarchical owns positions — physics off', () => {
    assertFalse(GraphPhysics.shouldRun({ userEnabled: true, layout: 'levels' }), 'levels');
});

test('an overlay holds positions — physics off', () => {
    for (const overlay of ['light', 'heat', 'sound', 'trigger', 'cardinal']) {
        assertFalse(GraphPhysics.shouldRun({ userEnabled: true, layout: 'graph', overlay }), overlay);
    }
    assertTrue(GraphPhysics.shouldRun({ userEnabled: true, layout: 'graph', overlay: 'none' }), 'none is escapable');
});

test('the node-layout lock holds positions — physics off', () => {
    assertFalse(GraphPhysics.shouldRun({ userEnabled: true, layout: 'map', locked: true }), 'locked');
});

test('the node-count valve suppresses physics', () => {
    assertFalse(GraphPhysics.shouldRun({ userEnabled: true, layout: 'graph', overNodeLimit: true }), 'over the limit');
});

test('a transient pause holds the solver off without changing the preference', () => {
    const base = { userEnabled: true, layout: 'graph', overlay: 'none' };
    assertTrue(GraphPhysics.shouldRun(base), 'unpaused');
    assertFalse(GraphPhysics.shouldRun({ ...base, paused: true }), 'paused for a window');
});

test('Map is not gated — physics is allowed there', () => {
    assertTrue(GraphPhysics.shouldRun({ userEnabled: true, layout: 'map', overlay: 'none' }), 'map');
});

test('an empty or partial state defaults to running, never an accidental freeze', () => {
    assertTrue(GraphPhysics.shouldRun(), 'no state');
    assertTrue(GraphPhysics.shouldRun({}), 'empty object');
    assertTrue(GraphPhysics.shouldRun({ layout: 'graph' }), 'no userEnabled field');
});

test('availability mirrors shouldRun and explains itself', () => {
    assertTrue(GraphPhysics.availability({ userEnabled: true, layout: 'graph' }).enabled, 'available');
    const lv = GraphPhysics.availability({ userEnabled: true, layout: 'levels' });
    assertFalse(lv.enabled, 'levels block');
    assertTrue(lv.reason.length > 0, 'levels reason');
    const ov = GraphPhysics.availability({ userEnabled: true, layout: 'graph', overlay: 'light' });
    assertFalse(ov.enabled, 'overlay block');
    assertTrue(ov.reason.length > 0, 'overlay reason');
});

test('reason is empty only when physics actually runs', () => {
    assertEq(GraphPhysics.reason({ userEnabled: true, layout: 'graph', overlay: 'none' }), '', 'running → no reason');
    assertTrue(GraphPhysics.reason({ userEnabled: false }).length > 0, 'user off reason');
    assertTrue(GraphPhysics.reason({ userEnabled: true, layout: 'levels' }).length > 0, 'levels reason');
    assertTrue(GraphPhysics.reason({ userEnabled: true, overNodeLimit: true }).length > 0, 'valve reason');
});

test('nodePinned: author-frozen pins, an explicit on overrides, nothing else pins', () => {
    assertTrue(GraphPhysics.nodePinned({ properties: { central_gravity_enabled: false } }), 'authored off');
    assertTrue(GraphPhysics.nodePinned({ properties: { layout_static: true } }), 'layout_static');
    assertFalse(GraphPhysics.nodePinned({ properties: { central_gravity_enabled: true } }), 'explicit on wins');
    assertFalse(GraphPhysics.nodePinned({ properties: {} }), 'no marker');
    assertFalse(GraphPhysics.nodePinned({}), 'no properties');
});

test('the load path releases the transient instead of only resuming when it was on', () => {
    // Wiring pin. The old load path resumed physics only `if (wasPhysics)`, so a
    // saved "physics off" reloaded paused forever and the reload ignored the
    // setting. Now the policy is released unconditionally and decides.
    const src = __readFile('static/js/graph/network-manager.ts');
    assertTrue(src.includes('GraphPhysics.resume();'), 'the load path releases the pause');
    assertFalse(src.includes('graphManager._physicsEnabled = true'), 'no hardcoded re-enable remains');
});
