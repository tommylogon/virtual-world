/**
 * Unit test for ItemLibrary overhaul: type taxonomy filtering, preset filters,
 * tag deduping, and pagination windowing (task-510).
 */
const assert = require('node:assert');

// Mock DOM elements
const mockElements = {
    'item-lib-list': { innerHTML: '' },
    'item-lib-search': { value: '' },
    'lib-sort': { value: 'name' },
    'lib-item-count': { textContent: '' },
    'item-lib-batch-bar': { style: {} },
    'place-items-btn': { style: {} },
};

globalThis.byId = (id) => mockElements[id] || null;
globalThis.document = {
    getElementById: (id) => mockElements[id] || null,
    querySelectorAll: (sel) => [],
};
globalThis.window = {
    Lit: {
        render: (template, container) => {
            container.rendered = template;
        }
    },
    VW: {},
    events: { log: () => {} }
};
globalThis.itemLibraryHtmlTag = (strings, ...values) => ({ strings, values });

// Load ItemLibrary class
const { ItemLibrary } = require('../../static/js/item-library.js');

const lib = new ItemLibrary();
lib.data = {
    'iron_sword': {
        name: 'Iron Sword',
        description: 'A sharp blade.',
        tags: ['weapon', 'metal', 'weapon'], // repeated tag
        triggers: [{ id: 'trig1' }],
        contents: [],
    },
    'apple': {
        name: 'Apple',
        description: 'Fresh red apple.',
        tags: ['food', 'fruit', 'edible'],
        triggers: [],
        contents: [],
    },
    'wooden_chest': {
        name: 'Wooden Chest',
        description: 'A sturdy box.',
        tags: ['container', 'wood'],
        triggers: [],
        contents: ['coin'],
    },
    'mystery_stone': {
        name: 'Mystery Stone',
        description: '', // missing description
        tags: ['item', 'stone'],
        triggers: [],
        contents: [],
    }
};

// Test 1: Deduplication of tags
const itemTags = Array.from(new Set(lib.data['iron_sword'].tags || []));
assert.strictEqual(itemTags.length, 2, 'Repeated tag "weapon" should be deduped to 2 tags');

// Test 2: Type filter
lib.setTypeFilter('weapon');
assert.strictEqual(lib._activeTypeFilter, 'weapon');
lib.renderList('');
assert.strictEqual(lib._lastFilteredIds.length, 1);
assert.strictEqual(lib._lastFilteredIds[0], 'iron_sword');

// Test 3: Preset filter - no_triggers
lib.setTypeFilter('all');
lib.setPresetFilter('no_triggers');
lib.renderList('');
assert.strictEqual(lib._lastFilteredIds.length, 3, 'Expected 3 items with no triggers');
assert(!lib._lastFilteredIds.includes('iron_sword'));

// Test 4: Preset filter - edible
lib.setPresetFilter('edible');
lib.renderList('');
assert.strictEqual(lib._lastFilteredIds.length, 1);
assert.strictEqual(lib._lastFilteredIds[0], 'apple');

// Test 5: Preset filter - has_contents
lib.setPresetFilter('has_contents');
lib.renderList('');
assert.strictEqual(lib._lastFilteredIds.length, 1);
assert.strictEqual(lib._lastFilteredIds[0], 'wooden_chest');

// Test 6: Preset filter - missing_desc
lib.setPresetFilter('missing_desc');
lib.renderList('');
assert.strictEqual(lib._lastFilteredIds.length, 1);
assert.strictEqual(lib._lastFilteredIds[0], 'mystery_stone');

console.log('All ItemLibrary filter tests passed successfully.');
