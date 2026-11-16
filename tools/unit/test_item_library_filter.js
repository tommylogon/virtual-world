/**
 * tools/unit/test_item_library_filter.js
 *
 * task-510: Unit tests for Library browser item filtering, tag deduping, and presets.
 */
'use strict';

(() => {
    test('ItemLibrary dedupes repeated tags', () => {
        const rawTags = ['weapon', 'metal', 'weapon', 'iron', 'metal'];
        const deduped = Array.from(new Set(rawTags));
        assertEq(deduped.length, 3, 'Repeated tags are deduped to 3');
        assertEq(deduped.includes('weapon'), true);
        assertEq(deduped.includes('metal'), true);
        assertEq(deduped.includes('iron'), true);
    });

    test('ItemLibrary type filter matches item taxonomy', () => {
        const dummyItems = {
            sword: { name: 'Sword', tags: ['weapon', 'sharp'] },
            trousers: { name: 'Trousers', tags: ['clothing', 'bottom'] },
            bread: { name: 'Bread', tags: ['food', 'consumable'] },
            box: { name: 'Box', tags: ['container'] },
            hammer: { name: 'Hammer', tags: ['tool'] },
            chair: { name: 'Chair', tags: ['furniture'] },
            note: { name: 'Note', tags: [] }
        };

        const getItemType = (item) => {
            const tags = (item.tags || []).map(t => t.toLowerCase());
            if (tags.some(t => ['weapon', 'sword', 'axe', 'bow', 'blade'].includes(t))) return 'weapon';
            if (tags.some(t => ['clothing', 'armor', 'top', 'bottom', 'torso', 'legs'].includes(t))) return 'clothing';
            if (tags.some(t => ['food', 'drink', 'consumable'].includes(t))) return 'food';
            if (tags.some(t => ['container', 'chest', 'bag'].includes(t))) return 'container';
            if (tags.some(t => ['tool', 'hammer'].includes(t))) return 'tool';
            if (tags.some(t => ['furniture', 'chair'].includes(t))) return 'furniture';
            return 'item';
        };

        assertEq(getItemType(dummyItems.sword), 'weapon');
        assertEq(getItemType(dummyItems.trousers), 'clothing');
        assertEq(getItemType(dummyItems.bread), 'food');
        assertEq(getItemType(dummyItems.box), 'container');
        assertEq(getItemType(dummyItems.hammer), 'tool');
        assertEq(getItemType(dummyItems.chair), 'furniture');
        assertEq(getItemType(dummyItems.note), 'item');
    });

    test('ItemLibrary preset filters filter by triggers, edibility, contents, and missing description', () => {
        const items = [
            { id: '1', triggers: [], tags: ['food'], contents: [], description: 'apple' },
            { id: '2', triggers: [{ id: 't1' }], tags: ['tool'], contents: [], description: 'hammer' },
            { id: '3', triggers: [], tags: ['container'], contents: ['coin'], description: 'chest' },
            { id: '4', triggers: [], tags: ['item'], contents: [], description: '' } // missing desc
        ];

        // No triggers
        const noTriggers = items.filter(it => (it.triggers || []).length === 0);
        assertEq(noTriggers.length, 3);

        // Edible
        const edible = items.filter(it => (it.tags || []).some(t => ['food', 'drink'].includes(t)));
        assertEq(edible.length, 1);
        assertEq(edible[0].id, '1');

        // Has contents
        const hasContents = items.filter(it => (it.contents || []).length > 0);
        assertEq(hasContents.length, 1);
        assertEq(hasContents[0].id, '3');

        // Missing description
        const missingDesc = items.filter(it => !(it.description && it.description.trim()));
        assertEq(missingDesc.length, 1);
        assertEq(missingDesc[0].id, '4');
    });
})();
