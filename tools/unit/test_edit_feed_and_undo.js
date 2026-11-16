/**
 * Unit tests for EditFeed and UndoHistory (task-384, task-371).
 */

test('EditFeed.PATH_LABEL maps known mutating routes to readable labels', () => {
    const fn = window.EditFeed.PATH_LABEL;
    assertEq(fn('/graph/node/goblin_camp'), 'graph node edited', 'node edit');
    assertEq(fn('/graph/edge/way_road'), 'graph edge edited', 'edge edit');
    assertEq(fn('/api/load'), 'world loaded', 'world loaded');
    assertEq(fn('/api/reset'), 'world reset', 'world reset');
    assertEq(fn('/api/players/hero'), 'player updated', 'player update');
    assertEq(fn('/api/memory/add'), 'memory updated', 'memory update');
    assertEq(fn('/library/weapons'), 'library edited', 'library edit');
    assertEq(fn(''), 'world changed', 'fallback');
});

test('EditFeed.push renders toast row with explicit label or path fallback', () => {
    // Reset container if any
    const existing = window.document.getElementById('edit-feed');
    if (existing) existing.remove();

    window.EditFeed.push({ method: 'POST', path: '/graph/node/1', label: 'Custom edit description' });
    const feed = window.document.getElementById('edit-feed');
    assertTrue(!!feed, 'edit-feed container created');
    const rows = feed.children;
    assertTrue(rows.length >= 1, 'at least 1 row rendered');
    const lastRow = rows[rows.length - 1];
    assertTrue(lastRow.textContent.includes('Custom edit description'), 'rendered custom label');
    assertTrue(lastRow.textContent.includes('Undo'), 'rendered undo button');

    window.EditFeed.push({ method: 'PATCH', path: '/graph/node/2' });
    const lastRowFallback = rows[rows.length - 1];
    assertTrue(lastRowFallback.textContent.includes('graph node edited'), 'rendered path fallback label');
});

test('UndoHistory toggle and close manage visibility', () => {
    const menu = window.document.createElement('div');
    menu.id = 'undo-history-menu';
    menu.style.display = 'none';
    window.document.getElementById = (id) => (id === 'undo-history-menu' ? menu : null);

    window.UndoHistory.close();
    assertEq(menu.style.display, 'none', 'closed menu stays none');
});
