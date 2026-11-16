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

test('WorldSync._group collapses item instances sharing library_id into one template group', () => {
    const ws = new (window.WorldSync || WorldSync)();
    ws.entities = [
        {
            type: 'item',
            nodeId: 'item_berries_1',
            payload: { name: 'wild berries', library_id: 'wild_berries' },
            match: { id: 'wild_berries', entry: { name: 'wild berries' } },
            status: 'synced',
            generated: false
        },
        {
            type: 'item',
            nodeId: 'item_berries_2',
            payload: { name: 'wild berries', library_id: 'wild_berries' },
            match: { id: 'wild_berries', entry: { name: 'wild berries' } },
            status: 'synced',
            generated: true
        },
        {
            type: 'item',
            nodeId: 'item_berries_3',
            payload: { name: 'wild berries', library_id: 'wild_berries' },
            match: { id: 'wild_berries', entry: { name: 'wild berries' } },
            status: 'synced',
            generated: true
        }
    ];

    const groups = ws._group();
    assertEq(groups.length, 1, 'three berry instances collapse into 1 group');
    assertEq(groups[0].count, 3, 'group count is 3');
    assertEq(groups[0].key, 'item:wild_berries', 'keyed by library_id');
    assertEq(groups[0].generated, false, 'mixed group with an authored member is NOT generated-only');
    assertEq(groups[0].representative.nodeId, 'item_berries_1', 'prefers authored member as representative');
});

test('WorldSync._group collapses item instances without library_id by name slug', () => {
    const ws = new (window.WorldSync || WorldSync)();
    ws.entities = [
        {
            type: 'item',
            nodeId: 'item_apple_a',
            payload: { name: 'Red Apple' },
            match: null,
            status: 'new',
            generated: false
        },
        {
            type: 'item',
            nodeId: 'item_apple_b',
            payload: { name: 'Red Apple' },
            match: null,
            status: 'new',
            generated: false
        }
    ];

    const groups = ws._group();
    assertEq(groups.length, 1, 'duplicate name items collapse into 1 group');
    assertEq(groups[0].key, 'item:red_apple', 'keyed by slug of name');
    assertEq(groups[0].count, 2, 'group count is 2');
});

test('WorldSync._group leaves ways, areas, and characters as distinct individual rows', () => {
    const ws = new (window.WorldSync || WorldSync)();
    ws.entities = [
        {
            type: 'area',
            name: 'Courtyard',
            payload: { name: 'Courtyard' },
            match: null,
            status: 'new',
            generated: false
        },
        {
            type: 'area',
            name: 'Armory',
            payload: { name: 'Armory' },
            match: null,
            status: 'new',
            generated: false
        },
        {
            type: 'way',
            nodeId: 'way_1',
            payload: { id: 'wooden_door', name: 'wooden door' },
            match: null,
            status: 'new',
            generated: false
        },
        {
            type: 'character',
            name: 'Guard',
            payload: { name: 'Guard' },
            match: null,
            status: 'new',
            generated: false
        }
    ];

    const groups = ws._group();
    assertEq(groups.length, 4, 'spatial and character nodes never collapse together');
    const types = groups.map(g => g.type);
    assertEq(types.sort(), ['area', 'area', 'character', 'way'], 'keeps all entity types distinct');
});

test('WorldSync._group sets group status to worst status of its members (diff > new > synced)', () => {
    const ws1 = new (window.WorldSync || WorldSync)();
    ws1.entities = [
        { type: 'item', nodeId: 'i1', payload: { library_id: 'torch' }, match: null, status: 'synced', generated: false },
        { type: 'item', nodeId: 'i2', payload: { library_id: 'torch' }, match: null, status: 'diff', generated: false },
        { type: 'item', nodeId: 'i3', payload: { library_id: 'torch' }, match: null, status: 'new', generated: false }
    ];
    assertEq(ws1._group()[0].status, 'diff', 'diff outranks new and synced');

    const ws2 = new (window.WorldSync || WorldSync)();
    ws2.entities = [
        { type: 'item', nodeId: 'i1', payload: { library_id: 'torch' }, match: null, status: 'synced', generated: false },
        { type: 'item', nodeId: 'i2', payload: { library_id: 'torch' }, match: null, status: 'new', generated: false }
    ];
    assertEq(ws2._group()[0].status, 'new', 'new outranks synced');

    const ws3 = new (window.WorldSync || WorldSync)();
    ws3.entities = [
        { type: 'item', nodeId: 'i1', payload: { library_id: 'torch' }, match: null, status: 'synced', generated: false }
    ];
    assertEq(ws3._group()[0].status, 'synced', 'pure synced group has synced status');
});

test('WorldSync._group marks group as generated only when every member is generated', () => {
    const wsAllGen = new (window.WorldSync || WorldSync)();
    wsAllGen.entities = [
        { type: 'item', nodeId: 'gen1', payload: { library_id: 'pebble' }, match: null, status: 'new', generated: true },
        { type: 'item', nodeId: 'gen2', payload: { library_id: 'pebble' }, match: null, status: 'new', generated: true }
    ];
    assertEq(wsAllGen._group()[0].generated, true, 'all members generated -> group is generated');

    const wsMixed = new (window.WorldSync || WorldSync)();
    wsMixed.entities = [
        { type: 'item', nodeId: 'gen1', payload: { library_id: 'pebble' }, match: null, status: 'new', generated: true },
        { type: 'item', nodeId: 'auth1', payload: { library_id: 'pebble' }, match: null, status: 'new', generated: false }
    ];
    assertEq(wsMixed._group()[0].generated, false, 'authored member present -> group is NOT generated');
});

test('WorldSync filter and review toggles default to hiding unchanged and generated entities', () => {
    const ws = new (window.WorldSync || WorldSync)();
    assertEq(ws.showGenerated, false, 'showGenerated defaults to false');
    assertEq(ws.showUnchanged, false, 'showUnchanged defaults to false');

    ws.toggleShowGenerated();
    assertEq(ws.showGenerated, true, 'toggleShowGenerated turns on');
    ws.toggleShowGenerated();
    assertEq(ws.showGenerated, false, 'toggleShowGenerated turns off');

    ws.toggleShowUnchanged();
    assertEq(ws.showUnchanged, true, 'toggleShowUnchanged turns on');
    ws.toggleShowUnchanged();
    assertEq(ws.showUnchanged, false, 'toggleShowUnchanged turns off');
});

test('WorldSync undoLastSync reverts previous batch changes', async () => {
    const savedCalls = [];
    const origApiClient = window.ApiClient;
    window.ApiClient = {
        saveLibraryItem: async (entry) => { savedCalls.push({ type: 'item', entry }); return null; },
        saveLibraryType: async (plural, entry) => { savedCalls.push({ type: plural, entry }); return null; }
    };

    try {
        const ws = new (window.WorldSync || WorldSync)();
        ws.refresh = async () => {};

        ws._lastBatchBackup = [
            { type: 'item', id: 'old_sword', oldEntry: { name: 'Old Sword', damage: 5 } },
            { type: 'area', id: 'old_garden', oldEntry: { name: 'Old Garden', description: 'quiet garden' } }
        ];

        await ws.undoLastSync();
        assertEq(savedCalls.length, 2, 'restored both entries');
        assertEq(savedCalls[0].entry.name, 'Old Sword', 'restored item payload');
        assertEq(savedCalls[1].entry.name, 'Old Garden', 'restored area payload');
        assertEq(ws._lastBatchBackup, null, 'cleared backup after undo');
    } finally {
        window.ApiClient = origApiClient;
    }
});
