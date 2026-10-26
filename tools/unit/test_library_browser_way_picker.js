/**
 * Unit tests for LibraryBrowser way placement target picker (bug-538).
 */
'use strict';

test('importSelectedWay uses ItemLibraryPlacement.pickTarget and avoids window.prompt (bug-538)', async () => {
    let promptCalled = false;
    const originalPrompt = window.prompt;
    window.prompt = () => { promptCalled = true; return 'fallback'; };

    if (!window.LibraryBrowser && typeof window.__readFile === 'function') {
        window.DiffModal = window.DiffModal || {};
        window.toastInfo = window.toastInfo || (() => {});
        window.toastError = window.toastError || (() => {});
        const src = window.__readFile('static/js/library-browser.js');
        (new Function(src))();
    }

    try {
        const pickerCalls = [];
        let importWayCalledWith = null;

        const fakePicker = {
            pickTarget: async (title, options) => {
                pickerCalls.push({ title, options });
                if (pickerCalls.length === 1) return { type: 'area', name: 'Throne Room' };
                if (pickerCalls.length === 2) return { type: 'area', name: 'Courtyard' };
                return null;
            },
        };

        const oldImportWay = window.ApiClient?.importWayFromLibrary;
        if (window.ApiClient) {
            window.ApiClient.importWayFromLibrary = async (id, payload) => {
                importWayCalledWith = { id, payload };
                return { status: 'imported', way: 'way_stone_arch' };
            };
        }

        const fakeBrowser = {
            selectedId: { ways: 'stone_arch' },
            data: { ways: { stone_arch: { name: 'Stone Arch' } } },
            importSelectedWay: window.LibraryBrowser ? window.LibraryBrowser.prototype.importSelectedWay : null,
        };

        assertTrue(!!fakeBrowser.importSelectedWay, 'importSelectedWay is a function on LibraryBrowser.prototype');

        window.ItemLibraryPlacement = fakePicker;
        const oldEvents = window.events;
        window.events = { log: () => {} };
        const oldWorldState = window.worldState;
        window.worldState = { fetch: () => {} };
        const oldVW = window.VW;
        window.VW = {
            dialog: {
                prompt: async ({ title, message, defaultValue }) => ({ value: defaultValue || 'out' }),
            },
        };

        await fakeBrowser.importSelectedWay();

        // Assert picker was called twice with area tab
        assertEq(pickerCalls.length, 2, 'pickTarget was called twice (from and to)');
        assertEq(pickerCalls[0].options.tabs, ['area'], 'source picker restricted to area');
        assertEq(pickerCalls[1].options.tabs, ['area'], 'destination picker restricted to area');

        // Assert importWayFromLibrary received the picked area names
        assertTrue(!!importWayCalledWith, 'importWayFromLibrary was called');
        assertEq(importWayCalledWith.id, 'stone_arch', 'correct way id');
        assertEq(importWayCalledWith.payload.area_from, 'Throne Room', 'area_from resolved from picker');
        assertEq(importWayCalledWith.payload.area_to, 'Courtyard', 'area_to resolved from picker');
        assertEq(promptCalled, false, 'window.prompt was never called');

        // Assert clean cancellation on first pick
        pickerCalls.length = 0;
        importWayCalledWith = null;
        fakePicker.pickTarget = async (title, options) => {
            pickerCalls.push({ title, options });
            return null; // user cancels
        };
        await fakeBrowser.importSelectedWay();
        assertEq(pickerCalls.length, 1, 'picker was called once');
        assertEq(importWayCalledWith, null, 'import was not called when user cancelled source');

        // Restore globals
        if (window.ApiClient && oldImportWay) {
            window.ApiClient.importWayFromLibrary = oldImportWay;
        }
        window.events = oldEvents;
        window.worldState = oldWorldState;
        window.VW = oldVW;
    } finally {
        window.prompt = originalPrompt;
    }
});
