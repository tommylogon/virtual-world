/**
 * test_graph_event_handlers.js — the graph's click routing (bug-49).
 *
 * The trap this guards: vis-network does **not** hand the DOM event to the
 * click handler. `params.event` is its own pointer wrapper, which proxies the
 * geometry the context menu needs but not the keyboard state, so reading
 * `params.event.shiftKey` is always `undefined` and a shift-click quietly
 * behaved like a plain click. These tests pin the real shapes.
 */

const GEH = window.GraphEventHandlers;

// A vis params object as it actually arrives: a wrapper with srcEvent.
const visParams = (nodes, mods = {}) => ({
    nodes,
    edges: [],
    items: { nodes: [] },
    event: {
        type: 'click',
        clientX: 10,
        clientY: 20,
        preventDefault: () => {},
        srcEvent: { shiftKey: false, ctrlKey: false, metaKey: false, altKey: false, ...mods },
    },
});

// Install the globals GraphEventHandlers.onClick reaches for, and record calls.
function withGraph(fake, fn) {
    const prevGm = window.graphManager;
    const prevVw = window.VW;
    const prevNet = window.GraphNetwork;
    const prevPanel = window.hideInspectorPanel;
    const calls = { toggled: [], inspected: [], cleared: 0, hidden: 0, revealed: [] };
    window.graphManager = Object.assign({
        nodes: new Map([['area_a', { type: 'area', name: 'A' }]]),
        _pendingConnection: null,
        _toggleBulkSelect: (id) => calls.toggled.push(id),
        _clearBulkSelection: () => { calls.cleared += 1; },
    }, fake || {});
    window.VW = { inspector: { showNode: (id) => calls.inspected.push(id) } };
    window.GraphNetwork = {
        revealItemsForNode: (id) => calls.revealed.push(id),
        revealAreasForWay: () => {},
        hideRevealedItems: () => { calls.hidden += 1; },
        hideRevealedAreas: () => {},
    };
    window.hideInspectorPanel = () => {};
    try {
        fn(calls);
    } finally {
        window.graphManager = prevGm;
        window.VW = prevVw;
        window.GraphNetwork = prevNet;
        window.hideInspectorPanel = prevPanel;
    }
}

test('modifiers reads the real event: vis wraps the DOM event in srcEvent', () => {
    assertEq(GEH.modifiers(visParams(['n'], { shiftKey: true })).shiftKey, true, 'shift on srcEvent');
    assertEq(GEH.modifiers(visParams(['n'], { ctrlKey: true })).ctrlKey, true, 'ctrl on srcEvent');
    assertEq(GEH.modifiers(visParams(['n'], { metaKey: true })).metaKey, true, 'meta on srcEvent');
    assertEq(GEH.modifiers(visParams(['n'], { altKey: true })).altKey, true, 'alt on srcEvent');
    assertEq(GEH.modifiers(visParams(['n'])),
        { shiftKey: false, ctrlKey: false, metaKey: false, altKey: false }, 'no modifiers');
});

test('modifiers survives the other shapes vis/hammer can pass', () => {
    // A bare DOM event (no wrapper).
    assertEq(GEH.modifiers({ event: { shiftKey: true } }).shiftKey, true, 'bare DOM event');
    // An array of events.
    assertEq(GEH.modifiers({ event: [{ shiftKey: false }, { shiftKey: true }] }).shiftKey, true, 'array');
    // Nothing at all.
    assertEq(GEH.modifiers({}), { shiftKey: false, ctrlKey: false, metaKey: false, altKey: false }, 'no event');
    assertEq(GEH.modifiers(null), { shiftKey: false, ctrlKey: false, metaKey: false, altKey: false }, 'null params');
});

test('a plain click opens the inspector (bug-49: unchanged)', () => {
    withGraph(null, (calls) => {
        GEH.onClick(visParams(['area_a']));
        assertEq(calls.toggled, [], 'no bulk toggle');
        assertEq(calls.inspected, ['area_a'], 'inspector opened');
        assertEq(calls.revealed, ['area_a'], 'items revealed for the node');
    });
});

test('shift-click toggles the bulk selection and opens no inspector (bug-49)', () => {
    withGraph(null, (calls) => {
        GEH.onClick(visParams(['area_a'], { shiftKey: true }));
        assertEq(calls.toggled, ['area_a'], 'selection toggled');
        assertEq(calls.inspected, [], 'inspector stays closed');
    });
});

test('a pending connection wins over the shift-click selection', () => {
    withGraph({ _pendingConnection: { fromNodeId: 'area_a' } }, (calls) => {
        GEH.onClick(visParams(['area_a'], { shiftKey: true }));
        assertEq(calls.toggled, [], 'no toggle while connecting');
        assertEq(calls.inspected, ['area_a'], 'still just a click on the source node');
    });
});

test('clicking empty canvas clears the selection and closes the panel', () => {
    withGraph(null, (calls) => {
        GEH.onClick({ nodes: [], edges: [], items: { nodes: [] }, event: { srcEvent: {} } });
        assertEq(calls.cleared, 1, 'selection cleared');
        assertEq(calls.hidden, 1, 'revealed items hidden');
    });
});
