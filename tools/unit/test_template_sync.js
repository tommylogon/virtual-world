/**
 * tools/unit/test_template_sync.js
 *
 * task-290: Unit tests for InspectorTemplateSync variant and override badge rendering.
 */

(() => {
    if (typeof window.InspectorTemplateSync === 'undefined' && typeof __readFile === 'function') {
        eval(__readFile('static/js/shared/template-sync.js'));
    }
    const TS = window.InspectorTemplateSync;

    test('InspectorTemplateSync renderTemplateRow with variant and overrides (task-290)', () => {
        assertTrue(typeof TS.renderTemplateRow === 'function', 'TS.renderTemplateRow exists');

        // 1. Unlinked node
        const unlinkedHtml = TS.renderTemplateRow('item', 'node_1', {});
        assertTrue(unlinkedHtml.includes('Search or pick a library template...'), 'has placeholder');
        assertFalse(unlinkedHtml.includes('🔗 Break Link'), 'no break link button when unlinked');
        assertFalse(unlinkedHtml.includes('variant:'), 'no variant badge');
        assertFalse(unlinkedHtml.includes('overridden'), 'no override badge');

        // 2. Linked node without variant or overrides
        const linkedHtml = TS.renderTemplateRow('item', 'node_2', { library_id: 'iron_dagger' });
        assertTrue(linkedHtml.includes('value="iron_dagger"'), 'has library_id preselected');
        assertTrue(linkedHtml.includes('🔗 Break Link'), 'has break link button');
        assertFalse(linkedHtml.includes('variant:'), 'no variant badge');
        assertFalse(linkedHtml.includes('overridden'), 'no override badge');

        // 3. Linked node with template_ref variant and overrides
        const richLinkedHtml = TS.renderTemplateRow('item', 'node_3', {
            library_id: 'iron_dagger',
            template_ref: {
                variant: 'serrated_blade',
                overrides: { weight: 1.5, damage: 8 },
            },
        });
        assertTrue(richLinkedHtml.includes('value="iron_dagger"'), 'has library_id preselected');
        assertTrue(richLinkedHtml.includes('🔗 Break Link'), 'has break link button');
        assertTrue(richLinkedHtml.includes('variant: serrated_blade'), 'has variant badge');
        assertTrue(richLinkedHtml.includes('🛡️ 2 overridden'), 'has override count badge');
        assertTrue(richLinkedHtml.includes('title="Overridden fields preserved from sync: weight, damage"'), 'has override field names in tooltip');

        // 4. Broken link provenance
        const brokenHtml = TS.renderTemplateRow('item', 'node_4', {
            template_broken_from: 'iron_dagger',
        });
        assertTrue(brokenHtml.includes('was linked to <code>iron_dagger</code> - this copy no longer syncs'), 'displays broken provenance');
    });

    test('InspectorTemplateSync dedupeLibraryEntries and unified Save button (task-983)', () => {
        const deduped = TS.dedupeLibraryEntries({
            kyrie: { name: 'kyrie johansen' },
            'kyrie johansen': { name: 'kyrie johansen' },
            zoe: { name: 'zoe mercer' },
        });
        assertEq(deduped.length, 2, 'collapses duplicate entries sharing same name');
        assertEq(deduped[0][0], 'kyrie johansen', 'prefers canonical name key');

        const keepCurrent = TS.dedupeLibraryEntries({
            kyrie: { name: 'kyrie johansen' },
            'kyrie johansen': { name: 'kyrie johansen' },
        }, 'kyrie');
        assertEq(keepCurrent[0][0], 'kyrie', 'preserves currently linked alias id');

        TS.register('way', {
            buildWorldPayload: () => ({}),
            sections: [],
            save: () => {},
        });
        const unifiedHtml = TS.renderTemplateRow('way', 'way_1', {});
        assertTrue(unifiedHtml.includes('Save to Library'), 'renders unified Save to Library button when save handler is registered');
    });
})();
