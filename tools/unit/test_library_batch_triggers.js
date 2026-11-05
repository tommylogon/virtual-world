/**
 * tools/unit/test_library_batch_triggers.js
 *
 * task-509: Unit tests for Library batch trigger generation for selected items.
 */
'use strict';

(() => {
    if (typeof window.TriggerSuggestDiff === 'undefined' && typeof __readFile === 'function') {
        eval(__readFile('static/js/shared/trigger-suggest-diff.js'));
    }
    if (typeof window.ItemLibraryTriggerSuggester === 'undefined' && typeof __readFile === 'function') {
        eval(__readFile('static/js/item-library/consumable-triggers.js'));
    }
    if (typeof window.ItemLibraryBatchTriggers === 'undefined' && typeof __readFile === 'function') {
        eval(__readFile('static/js/item-library/batch-triggers.js'));
    }

    const BatchTriggers = window.ItemLibraryBatchTriggers;

    test('ItemLibraryBatchTriggers.prepareItemFields normalizes item properties', () => {
        assertTrue(typeof BatchTriggers.prepareItemFields === 'function', 'prepareItemFields exists');

        // Test with string actions and string uses
        const fields1 = BatchTriggers.prepareItemFields({
            name: 'Red Apple',
            description: 'A crisp red apple.',
            actions: 'examine, eat, drop',
            tags: ['food', 'fruit'],
            uses: '1',
        });
        assertEq(fields1.name, 'Red Apple');
        assertEq(fields1.description, 'A crisp red apple.');
        assertEq(fields1.actions, ['examine', 'eat', 'drop']);
        assertEq(fields1.tags, ['food', 'fruit']);
        assertEq(fields1.uses, 1);
        assertEq(fields1.current_state, 'normal');

        // Test with array actions and fallback uses
        const fields2 = BatchTriggers.prepareItemFields({
            name: 'Iron Key',
            actions: ['examine', 'use'],
        });
        assertEq(fields2.actions, ['examine', 'use']);
        assertEq(fields2.uses, -1);
    });

    test('ItemLibraryBatchTriggers selection helpers toggle and select filtered items', () => {
        const mockHost = {
            _multiSelect: false,
            _checkedIds: new Set(),
            _lastFilteredIds: ['apple', 'bread', 'cheese'],
            data: {
                apple: { name: 'Apple' },
                bread: { name: 'Bread' },
                cheese: { name: 'Cheese' },
            },
            renderListCalls: 0,
            renderList() { this.renderListCalls++; },
            _updateBatchBar() {},
            _updatePlaceButton() {},
        };

        // 1. toggleMultiSelect
        BatchTriggers.toggleMultiSelect.call(mockHost);
        assertTrue(mockHost._multiSelect, 'multiSelect is now true');
        assertEq(mockHost.renderListCalls, 1);

        // 2. selectAllFiltered
        BatchTriggers.selectAllFiltered.call(mockHost);
        assertEq(mockHost._checkedIds.size, 3, 'all 3 filtered items checked');
        assertTrue(mockHost._checkedIds.has('apple'));
        assertTrue(mockHost._checkedIds.has('bread'));
        assertTrue(mockHost._checkedIds.has('cheese'));

        // 3. clearSelection
        BatchTriggers.clearSelection.call(mockHost);
        assertEq(mockHost._checkedIds.size, 0, 'selection cleared');

        // 4. toggleMultiSelect off
        mockHost._checkedIds.add('apple');
        BatchTriggers.toggleMultiSelect.call(mockHost);
        assertFalse(mockHost._multiSelect, 'multiSelect is now false');
        assertEq(mockHost._checkedIds.size, 0, 'checkedIds cleared when leaving multiSelect');
    });

    test('ItemLibraryBatchTriggers.runBatch skips already-authored items by default and stages diff', async () => {
        const DiffUI = window.TriggerSuggestDiff;
        let diffShownOpts = null;
        const origShow = DiffUI.show;
        DiffUI.show = (opts) => {
            diffShownOpts = opts;
            return { remove: () => {} };
        };

        const savedPayloads = [];
        const origApiClient = window.ApiClient;
        window.ApiClient = {
            saveLibraryItem: async (payload) => {
                savedPayloads.push(payload);
                return { status: 'success' };
            },
        };

        const mockHost = {
            _checkedIds: new Set(['apple', 'already_authored']),
            data: {
                apple: {
                    id: 'apple',
                    name: 'Apple',
                    description: 'A crisp apple.',
                    actions: ['examine', 'eat'],
                    tags: ['food'],
                    uses: 1,
                    triggers: [],
                },
                already_authored: {
                    id: 'already_authored',
                    name: 'Magic Potion',
                    description: 'A glowing flask.',
                    actions: ['examine', 'drink'],
                    tags: ['medicine'],
                    uses: 1,
                    triggers: [
                        { trigger_type: 'on_drink', effects: [{ type: 'adjust_vital', params: { stat: 'HP', delta: 50 } }] }
                    ],
                },
            },
            refreshCalls: 0,
            async refresh() { this.refreshCalls++; },
            renderList() {},
            _updateBatchBar() {},
        };

        try {
            // Run batch without replaceExisting: already_authored MUST be skipped
            await BatchTriggers.runBatch.call(mockHost, { useAI: false, replaceExisting: false });

            assertTrue(diffShownOpts !== null, 'DiffUI.show was called');
            assertTrue(diffShownOpts.subtitle.includes('1 skipped - already authored'), 'reports 1 skipped');
            assertEq(diffShownOpts.rows.length, 2, 'apple has 2 planned triggers (on_examine, on_eat)');
            assertTrue(diffShownOpts.rows.every(r => r.item_id === 'apple'), 'all rows belong to apple');

            // Simulate clicking Apply in diff view
            const mockDiffResult = {
                keep: [],
                replace: [],
                add: [
                    { type: 'on_eat', data: diffShownOpts.rows.find(r => r.type === 'on_eat').suggested, item_id: 'apple' },
                    { type: 'on_examine', data: diffShownOpts.rows.find(r => r.type === 'on_examine').suggested, item_id: 'apple' },
                ],
            };
            await diffShownOpts.onApply(mockDiffResult);

            assertEq(savedPayloads.length, 1, 'only apple was saved');
            assertEq(savedPayloads[0].id, 'apple');
            assertEq(savedPayloads[0].triggers.length, 2);
            assertEq(mockHost.refreshCalls, 1);
        } finally {
            DiffUI.show = origShow;
            window.ApiClient = origApiClient;
        }
    });

    test('ItemLibraryBatchTriggers.runBatch with replaceExisting includes already-authored items', async () => {
        const DiffUI = window.TriggerSuggestDiff;
        let diffShownOpts = null;
        const origShow = DiffUI.show;
        DiffUI.show = (opts) => {
            diffShownOpts = opts;
            return { remove: () => {} };
        };

        const mockHost = {
            _checkedIds: new Set(['authored_item']),
            data: {
                authored_item: {
                    id: 'authored_item',
                    name: 'Old Bread',
                    description: 'Dry bread.',
                    actions: ['examine', 'eat'],
                    tags: ['food'],
                    uses: 1,
                    triggers: [
                        { trigger_type: 'on_eat', effects: [{ type: 'message', params: { text: 'You chew old bread.' } }] }
                    ],
                },
            },
            async refresh() {},
            renderList() {},
            _updateBatchBar() {},
        };

        try {
            // Run batch WITH replaceExisting: authored_item MUST be processed
            await BatchTriggers.runBatch.call(mockHost, { useAI: false, replaceExisting: true });

            assertTrue(diffShownOpts !== null, 'DiffUI.show was called');
            assertFalse(diffShownOpts.subtitle.includes('skipped'), 'no items skipped when replaceExisting is true');
            assertTrue(diffShownOpts.rows.some(r => r.item_id === 'authored_item'), 'authored_item is included');
        } finally {
            DiffUI.show = origShow;
        }
    });
})();
