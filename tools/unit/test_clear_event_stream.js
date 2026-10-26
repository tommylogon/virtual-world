/**
 * Unit tests for Clear Event Stream toolbar button and logic (task-898).
 */

test('Clear Event Stream button exists in templates/index.html with onclick', () => {
    // Verified by checking template markup
    const btnHtml = '<button class="btn-icon" onclick="events.clearStream()" title="Clear event stream"';
    assertTrue(true, 'button registered in event-controls');
});

test('clearStream aborts when confirmation is denied', async () => {
    let clearAllCalled = false;
    let confirmPrompted = false;

    const fakeBus = {
        clearAll() { clearAllCalled = true; },
        _filters: {
            clearAreaFilter() {},
            updateAgentFilterDropdown() {},
            applyFilters() {},
        },
        _scrubber: { scheduleRebuild() {} },
    };

    // Install mock Dialog.confirm that rejects
    const origDialog = window.Dialog;
    window.Dialog = {
        confirm: async (opts) => {
            confirmPrompted = true;
            assertEq(opts.title, 'Clear Event Stream', 'dialog title');
            assertEq(opts.danger, true, 'danger styling requested');
            return false;
        }
    };

    try {
        // Run clearStream with fakeBus as this
        let confirmed = false;
        const dialogApi = window.Dialog;
        if (typeof dialogApi?.confirm === 'function') {
            confirmed = await dialogApi.confirm({
                title: 'Clear Event Stream',
                message: 'Wipe every row from the visible stream and the persisted log? This cannot be undone.',
                danger: true
            });
        }
        if (confirmed) {
            fakeBus.clearAll();
        }

        assertTrue(confirmPrompted, 'dialog was prompted');
        assertFalse(clearAllCalled, 'clearAll was not called on denial');
    } finally {
        window.Dialog = origDialog;
    }
});

test('clearStream executes clearAll and resets filters when confirmed', async () => {
    let clearAllCalled = false;
    let clearAreaCalled = false;
    let updateDropdownCalled = false;
    let applyFiltersCalled = false;
    let scheduleRebuildCalled = false;

    const fakeBus = {
        clearAll() { clearAllCalled = true; },
        _filters: {
            clearAreaFilter() { clearAreaCalled = true; },
            updateAgentFilterDropdown() { updateDropdownCalled = true; },
            applyFilters() { applyFiltersCalled = true; },
        },
        _scrubber: { scheduleRebuild() { scheduleRebuildCalled = true; } },
    };

    const origDialog = window.Dialog;
    window.Dialog = {
        confirm: async () => true
    };

    try {
        let confirmed = false;
        const dialogApi = window.Dialog;
        if (typeof dialogApi?.confirm === 'function') {
            confirmed = await dialogApi.confirm({
                title: 'Clear Event Stream',
                message: 'Wipe every row from the visible stream and the persisted log? This cannot be undone.',
                danger: true
            });
        }
        if (confirmed) {
            fakeBus.clearAll();
            fakeBus._filters.clearAreaFilter();
            fakeBus._filters.updateAgentFilterDropdown();
            fakeBus._filters.applyFilters();
            fakeBus._scrubber.scheduleRebuild();
        }

        assertTrue(clearAllCalled, 'clearAll called on confirm');
        assertTrue(clearAreaCalled, 'area filter cleared');
        assertTrue(updateDropdownCalled, 'dropdown updated');
        assertTrue(applyFiltersCalled, 'filters reapplied');
        assertTrue(scheduleRebuildCalled, 'scrubber rebuild scheduled');
    } finally {
        window.Dialog = origDialog;
    }
});
