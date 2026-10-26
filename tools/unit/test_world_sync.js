/**
 * Unit tests for WorldSync (bug-526).
 *
 * Covers:
 * 1. syncAll() tab scoping (respecting this.filter)
 * 2. syncAll() generated exclusion (skipping generated: true)
 * 3. syncAll() overwrite confirmation before overwriting diff entries
 */
'use strict';

test('worldSync.syncAll respects active tab filter, skips generated, and confirms overwrite (bug-526)', async () => {
    // Ensure minimal DOM / globals for world-sync
    if (!window.Lit) {
        window.Lit = { html: () => '' };
    }
    if (typeof window.toastInfo !== 'function') {
        window.toastInfo = () => {};
    }
    if (typeof window.toastError !== 'function') {
        window.toastError = () => {};
    }

    if (typeof window.__readFile === 'function') {
        const src = window.__readFile('static/js/world-sync.js');
        (new Function(src))();
    }

    const ws = window.worldSync || (typeof WorldSync !== 'undefined' ? new WorldSync() : null);
    assertTrue(!!ws, 'worldSync instance must exist');

    // 1. Tab Scoping Test
    const saved = [];
    ws._silentSave = async (rep) => {
        saved.push(rep);
        return { ok: true };
    };
    ws._renderSummary = () => {};
    ws._renderList = () => {};

    ws.filter = 'items';
    ws.groups = [
        { type: 'item', status: 'new', generated: false, representative: { id: 'item_1' }, members: [{ status: 'new' }] },
        { type: 'way', status: 'new', generated: false, representative: { id: 'way_1' }, members: [{ status: 'new' }] },
        { type: 'area', status: 'new', generated: false, representative: { id: 'area_1' }, members: [{ status: 'new' }] },
    ];

    await ws.syncAll();
    assertEq(saved.length, 1, 'Only 1 item should be synced when on items tab');
    assertEq(saved[0].id, 'item_1', 'Synced item should be item_1');
    assertEq(ws.groups[0].status, 'synced', 'Item group should be flipped to synced');
    assertEq(ws.groups[1].status, 'new', 'Way group should remain untouched');

    // 2. Generated Exclusion Test
    saved.length = 0;
    ws.filter = 'all';
    ws.groups = [
        { type: 'item', status: 'new', generated: false, representative: { id: 'authored_item' }, members: [{ status: 'new' }] },
        { type: 'item', status: 'new', generated: true, representative: { id: 'gen_item' }, members: [{ status: 'new' }] },
        { type: 'way', status: 'new', generated: true, representative: { id: 'gen_way' }, members: [{ status: 'new' }] },
        { type: 'area', status: 'new', generated: true, representative: { id: 'gen_area' }, members: [{ status: 'new' }] },
    ];

    await ws.syncAll();
    assertEq(saved.length, 1, 'Only non-generated entity should be synced');
    assertEq(saved[0].id, 'authored_item', 'Only authored item should be saved');

    // 3. Overwrite Confirmation Test (Cancelled)
    saved.length = 0;
    let confirmCalled = false;
    window.Dialog = {
        confirm: async (opts) => {
            confirmCalled = true;
            return false; // User cancels overwrite
        }
    };

    ws.groups = [
        { type: 'item', status: 'diff', generated: false, representative: { id: 'modified_item' }, members: [{ status: 'diff' }] },
    ];

    await ws.syncAll();
    assertTrue(confirmCalled, 'Dialog.confirm should be called when status is diff');
    assertEq(saved.length, 0, 'No saves should happen when user cancels overwrite');
    assertEq(ws.groups[0].status, 'diff', 'Group status should remain diff');

    // 4. Overwrite Confirmation Test (Accepted)
    confirmCalled = false;
    window.Dialog = {
        confirm: async (opts) => {
            confirmCalled = true;
            return true; // User accepts overwrite
        }
    };

    await ws.syncAll();
    assertTrue(confirmCalled, 'Dialog.confirm should be called again');
    assertEq(saved.length, 1, 'Save should proceed when confirmed');
    assertEq(ws.groups[0].status, 'synced', 'Group status should be synced after accepted overwrite');
});
