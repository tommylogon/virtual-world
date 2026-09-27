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
