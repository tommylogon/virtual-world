/**
 * test_doc_panel.js — the doc panel's view-model (task-579).
 *
 * The DOM path is exercised live; this pins the state machine: the two lookup
 * keys, the empty state that must never look like an error, and the populated
 * state.
 */

test('doc panel: no rows is the quiet empty state', () => {
    const f = window.DocPanel.format([]);
    assertTrue(f.empty, 'empty flag');
    assertEq(f.title, 'No documentation yet');
    assertEq(f.url, null, 'no open link when empty');
});

test('doc panel: a non-array response is treated as empty, not an error', () => {
    assertTrue(window.DocPanel.format(null).empty);
    assertTrue(window.DocPanel.format({}).empty);
});

test('doc panel: a row yields title, summary and open url', () => {
    const f = window.DocPanel.format([
        { title: 'Search & Forage', summary: 'A weighted draw.', body_url: '/api/docs/body?path=x' },
    ]);
    assertFalse(f.empty, 'not empty');
    assertEq(f.title, 'Search & Forage');
    assertEq(f.summary, 'A weighted draw.');
    assertEq(f.url, '/api/docs/body?path=x');
});

test('doc panel: request url encodes the key and picks the parameter', () => {
    assertEq(window.DocPanel.requestUrl({ kind: 'node', value: 'way 1' }),
             '/api/docs/resolve?node=way%201');
    assertEq(window.DocPanel.requestUrl({ kind: 'module', value: 'engine/tick_manager.py' }),
             '/api/docs/resolve?module=engine%2Ftick_manager.py');
    assertEq(window.DocPanel.requestUrl(null), null);
});

test('doc panel: a node resolves by library id, else by its view module', () => {
    assertEq(window.DocPanel.selectionForNode({ type: 'item', properties: { library_id: 'lantern' } }),
             { kind: 'node', value: 'lantern' });
    assertEq(window.DocPanel.selectionForNode({ type: 'area', properties: {} }),
             { kind: 'module', value: 'static/js/inspector/area-view.js' });
    assertEq(window.DocPanel.selectionForNode({ type: 'unknown_thing', properties: {} }), null);
});

test('doc panel: a keyless selection becomes the empty state, not a fetch', async () => {
    await window.DocPanel.setSelection(null);
    assertEq(window.DocPanel.state().status, 'ready');
    assertEq(window.DocPanel.state().rows, []);
});
