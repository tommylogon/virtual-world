/**
 * tools/unit/test_graph_toolbar.js — the graph toolbar's decision rules.
 *
 * These are the "honest affordance" rules task-530 introduced: a control that
 * cannot run right now must be disabled *and* say why. They used to be five
 * independent label writers spread over four files, which is why the bar could
 * show a live-looking Physics button in a mode where the solver was overridden
 * and a Map button that silently did nothing under Levels.
 */
'use strict';

// ─── Layout axis ──────────────────────────────────────────────────────────────

test('the layout axis is exactly Graph / Map / Levels', () => {
    assertEq(GraphToolbar.LAYOUTS, ['graph', 'map', 'levels'], 'layouts');
    assertEq(GraphToolbar.OVERLAYS, ['none', 'light', 'heat', 'sound', 'trigger', 'cardinal'], 'overlays');
});

test('an explicit None overlay exists, so the overlays menu is escapable', () => {
    assertEq(GraphToolbar.OVERLAYS[0], 'none', 'first overlay entry');
});

// ─── Map tab vs Levels (bug-48) ──────────────────────────────────────────────

test('Map is unavailable while Levels owns the layout', () => {
    const why = GraphToolbar.mapTabDisabled({ layout: 'levels' });
    assertTrue(typeof why === 'string' && why.length > 0, 'levels must explain why Map is off');
});

test('Map is available in the other two layouts', () => {
    assertEq(GraphToolbar.mapTabDisabled({ layout: 'graph' }), null, 'graph layout');
    assertEq(GraphToolbar.mapTabDisabled({ layout: 'map' }), null, 'map layout');
    assertEq(GraphToolbar.mapTabDisabled({}), null, 'empty state');
});

// ─── Physics availability ────────────────────────────────────────────────────

test('physics is unavailable under Levels, with a reason', () => {
    const r = GraphToolbar.physicsAvailability({ layout: 'levels', overlay: 'none' });
    assertFalse(r.enabled, 'levels disables physics');
    assertTrue(r.reason.length > 0, 'and says why');
});

test('physics is unavailable while an overlay is on', () => {
    for (const overlay of ['light', 'heat', 'sound', 'trigger', 'cardinal']) {
        const r = GraphToolbar.physicsAvailability({ layout: 'graph', overlay });
        assertFalse(r.enabled, `${overlay} overlay holds positions`);
        assertTrue(r.reason.length > 0, `${overlay} overlay explains itself`);
    }
});

test('physics is unavailable when the node layout is explicitly locked', () => {
    const r = GraphToolbar.physicsAvailability({ layout: 'map', overlay: 'none', mapLocked: true });
    assertFalse(r.enabled, 'a 🔒 lock is the user saying these positions are intentional');
    assertTrue(r.reason.length > 0, 'and it explains itself');
});

test('a painted grid does NOT block physics — the user asked for it', () => {
    // Deliberate behaviour change: in Map mode the painted lattice is a starting
    // arrangement, not a freeze. Nodes drift off the cells (and the map art with
    // them); locking the layout is how you keep them.
    const painted = GraphToolbar.physicsAvailability({ layout: 'map', overlay: 'none', paintedGrid: true, physicsEnabled: true });
    assertTrue(painted.enabled, 'painted grid');
    assertEq(painted.reason, '', 'no reason needed');
});

test('physics is available in plain graph and map views', () => {
    const graph = GraphToolbar.physicsAvailability({ layout: 'graph', overlay: 'none', physicsEnabled: true });
    assertTrue(graph.enabled, 'graph view');
    assertEq(graph.reason, '', 'no reason when available');
    const map = GraphToolbar.physicsAvailability({ layout: 'map', overlay: 'none', paintedGrid: false, physicsEnabled: false });
    assertTrue(map.enabled, 'cardinal fallback map, no painted grid');
});

test('a missing state never throws and never blocks', () => {
    assertTrue(GraphToolbar.physicsAvailability().enabled, 'empty state falls back to available');
    assertEq(GraphToolbar.mapTabDisabled(), null, 'empty state has no Map block');
});

// ─── KEEP layout (needs a search) ────────────────────────────────────────────

test('Keep layout is unavailable with an empty or blank query', () => {
    assertTrue(GraphToolbar.keepInPlaceDisabled({ searchQuery: '' }).length > 0, 'empty query');
    assertTrue(GraphToolbar.keepInPlaceDisabled({ searchQuery: '   ' }).length > 0, 'whitespace query');
    assertEq(GraphToolbar.keepInPlaceDisabled({ searchQuery: 'berry' }), null, 'real query');
    // No state means no query, which means the control has nothing to do.
    assertTrue(GraphToolbar.keepInPlaceDisabled().length > 0, 'missing state is treated as no query');
});

// ─── Paste Response (needs Manual Response Mode) ─────────────────────────────

test('Paste Response is unavailable unless Manual Response Mode is on', () => {
    assertTrue(GraphToolbar.pasteDisabled({ manualMode: false }).length > 0, 'manual mode off');
    assertEq(GraphToolbar.pasteDisabled({ manualMode: true }), null, 'manual mode on');
    assertTrue(GraphToolbar.pasteDisabled({}).length > 0, 'unknown means off, not a silent no-op');
});

// ─── Scope bar breadcrumb (task-531) ─────────────────────────────────────────
// The flat scope list from /api/world/scopes?flat=1 carries `parent_id`; the
// trail is a walk up that chain, not a second request.

test('the breadcrumb runs root first and ends on the loaded scope', () => {
    const scopes = [
        { id: 'world', name: 'World', parent_id: null, depth: 0 },
        { id: 'town', name: 'Oakhaven', parent_id: 'world', depth: 1 },
        { id: 'ward', name: 'Dockside', parent_id: 'town', depth: 2 },
    ];
    assertEq(GraphToolbar.breadcrumbTrail(scopes, 'ward'), [
        { id: 'world', name: 'World' },
        { id: 'town', name: 'Oakhaven' },
        { id: 'ward', name: 'Dockside' },
    ], 'three levels');
    assertEq(GraphToolbar.breadcrumbTrail(scopes, 'town').map(s => s.id), ['world', 'town'], 'two levels');
    assertEq(GraphToolbar.breadcrumbTrail(scopes, 'world').map(s => s.id), ['world'], 'a root is its own trail');
});

test('the breadcrumb is empty for the whole world or an unknown scope', () => {
    const scopes = [{ id: 'world', name: 'World', parent_id: null }];
    assertEq(GraphToolbar.breadcrumbTrail(scopes, ''), [], 'no scope selected');
    assertEq(GraphToolbar.breadcrumbTrail(scopes, null), [], 'null scope');
    assertEq(GraphToolbar.breadcrumbTrail(scopes, 'gone'), [], 'stale selection falls back in the DOM');
    assertEq(GraphToolbar.breadcrumbTrail([], 'world'), [], 'no list yet');
    assertEq(GraphToolbar.breadcrumbTrail(undefined, 'world'), [], 'undefined list');
});

test('a scope whose parent is not in the list still yields its own crumb', () => {
    // The manifest can change between the list fetch and the click; a half-trail
    // beats an empty one.
    const scopes = [{ id: 'ward', name: 'Dockside', parent_id: 'missing' }];
    assertEq(GraphToolbar.breadcrumbTrail(scopes, 'ward'), [{ id: 'ward', name: 'Dockside' }], 'orphan');
});

test('a parent cycle cannot hang the breadcrumb', () => {
    const scopes = [
        { id: 'a', name: 'A', parent_id: 'b' },
        { id: 'b', name: 'B', parent_id: 'a' },
    ];
    const trail = GraphToolbar.breadcrumbTrail(scopes, 'a');
    assertEq(trail.map(s => s.id).sort(), ['a', 'b'], 'visits each once');
});

// ─── ⚙ Tune popover — the Settings → Graph tab at the canvas ────────────────

// The spec is the single writer of the apply behavior; the Settings modal keeps
// its own static markup over the same config keys. These tests read the modal's
// own markup out of index.html and assert the popover stays in parity with it,
// so a field added to one surface without the other fails here.

function tuningSpec() {
    return GraphToolbar.TUNING_GROUPS.flatMap(g => g.fields);
}

test('the Tune popover covers exactly the Settings modal Graph tab, control for control', () => {
    const spec = tuningSpec();
    const html = __readFile('templates/index.html');
    const start = html.indexOf('id="tab-graph"');
    const end = html.indexOf('id="tab-embedding"');
    assertTrue(start !== -1 && end !== -1 && end > start, 'the modal Graph tab is where the test expects it');
    const tab = html.slice(start, end);
    // Every config key the modal's Graph tab writes...
    const modalKeys = [...new Set([...tab.matchAll(/config\.(\w+)\s*=/g)].map(m => m[1]))].sort();
    // ...is in the spec, and the spec adds nothing of its own.
    const specKeys = spec.map(f => f.key).sort();
    assertEq(specKeys, modalKeys, 'config keys');
});

test('the Tune popover has one control per modal control, with matching bounds', () => {
    const spec = tuningSpec();
    const html = __readFile('templates/index.html');
    const tab = html.slice(html.indexOf('id="tab-graph"'), html.indexOf('id="tab-embedding"'));
    // 16 controls like the modal: 12 ranges, 1 select, 3 checks — counted, not assumed.
    assertEq(spec.length, 15, 'field count');
    assertEq(spec.filter(f => f.type === 'range').length, 11, 'range count');
    assertEq(spec.filter(f => f.type === 'select').length, 1, 'select count');
    assertEq(spec.filter(f => f.type === 'check').length, 3, 'check count');
    // Each spec range mirrors a modal range input with the same min/max/step.
    // The modal pairs a control id with its config key inside one <input> tag.
    const modalRanges = new Map();
    for (const m of tab.matchAll(/<input type="range" id="([\w-]+)" min="([-\d.]+)" max="([-\d.]+)" step="([-\d.]+)"[^>]*config\.(\w+)\s*=/g)) {
        modalRanges.set(m[5], { min: m[2], max: m[3], step: m[4] });
    }
    assertEq(modalRanges.size, 11, 'range inputs parsed out of the modal');
    for (const f of spec.filter(f => f.type === 'range')) {
        const twin = modalRanges.get(f.key);
        assertTrue(!!twin, `${f.key} has a modal range twin`);
        assertEq(String(f.min), twin.min, `${f.key} min`);
        assertEq(String(f.max), twin.max, `${f.key} max`);
        assertEq(String(f.step), twin.step, `${f.key} step`);
    }
});

test('the Tune popover element ids never collide with the modal control ids', () => {
    const html = __readFile('templates/index.html');
    const modalIds = new Set([...html.matchAll(/id="(graph-[\w-]+)"/g)].map(m => m[1]));
    for (const f of tuningSpec()) {
        assertFalse(modalIds.has(f.id), `${f.id} is gt-prefixed, not a modal id`);
        assertTrue(f.id.startsWith('gt-'), `${f.id} carries the gt- prefix`);
    }
});

test('tuningDisplay formats value chips like the modal does', () => {
    assertEq(GraphToolbar.tuningDisplay({}, 120), '120', 'integer field');
    assertEq(GraphToolbar.tuningDisplay({}, -40), '-40', 'negative integer');
    assertEq(GraphToolbar.tuningDisplay({ dp: 2 }, 0.4), '0.40', 'two decimals');
    assertEq(GraphToolbar.tuningDisplay({ dp: 1 }, 2.5), '2.5', 'one decimal');
});

test('tuningValue falls back to the config default only when config has no value', () => {
    const field = { key: 'graphDamping', fallback: 0.4 };
    assertEq(GraphToolbar.tuningValue(field), 0.4, 'no config yet → fallback');
    assertEq(GraphToolbar.tuningValue({ key: 'nonexistent' }), 0, 'no fallback declared → 0');
});

test('applyTuning writes config, saves, and reapplies the graph settings', () => {
    const saved = [];
    let applied = 0;
    window.config = { graphSpringLength: 120, save() { saved.push(this.graphSpringLength); } };
    window.GraphNetwork = { applyGraphSettings() { applied++; } };
    GraphToolbar.applyTuning('graphSpringLength', 200);
    assertEq(window.config.graphSpringLength, 200, 'written to config');
    assertEq(saved, [200], 'config.save() ran after the write');
    assertEq(applied, 1, 'GraphNetwork.applyGraphSettings() ran after the save');
});

test('applyTuning is inert without a config object rather than throwing', () => {
    const hadConfig = window.config;
    window.config = undefined;
    let applied = 0;
    window.GraphNetwork = { applyGraphSettings() { applied++; } };
    GraphToolbar.applyTuning('graphSpringLength', 200);
    assertEq(applied, 0, 'nothing applied when config is absent');
    window.config = hadConfig;
});

test('focusNode reads the camera zoom off config, no hardcoded scale left', () => {
    // Wiring pin: every list/outline/palette "go to node" funnels through
    // graphManager.focusNode, whose zoom used to be a literal 1.15.
    const src = __readFile('static/js/graph-manager.ts');
    const fn = src.slice(src.indexOf('focusNode(nodeId'), src.indexOf('showNodeAndFocus'));
    assertTrue(fn.includes('config.graphFocusZoom'), 'reads config.graphFocusZoom');
    assertFalse(/scale:\s*1\.15/.test(fn), 'no hardcoded 1.15 scale');
    assertTrue(fn.includes('1.15'), 'falls back to the same default the config ships with');
});
