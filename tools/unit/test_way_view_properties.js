/**
 * tools/unit/test_way_view_properties.js - tests for way inspector property wiring (task-780).
 */

test('saveWayPassage writes requires_item, refusal_message, and entry_phrase to nodePatch', async () => {
    let patchedProperties = null;

    window.worldState.getNode = (id) => ({
        id: 'way_123',
        name: 'Iron Gate',
        properties: {
            description: 'A heavy iron gate.',
            current_state: 'closed',
            pass_message: 'You pass through.',
            refusal_message: 'Old refusal.',
            entry_phrase: 'Old phrase.',
            requires_item: 'old_key',
        },
    });

    window.worldState.fetch = async () => {};
    window.worldState.graph = { edges: [] };

    // Stub input elements
    const inputs = {
        'way-passage-desc-way_123': { value: 'A reinforced gate.' },
        'way-passage-state-way_123': { value: 'locked' },
        'way-passage-pass-msg-way_123': { value: 'You step through the gate.' },
        'way-passage-refusal-way_123': { value: 'The gate is firmly chained.' },
        'way-passage-entry-phrase-way_123': { value: 'walk through the gate' },
        'way-passage-requires-way_123': { value: 'crawl' },
        'way-passage-requires-item-way_123': { value: 'iron_key, tag:heavy' },
        'way-passage-one-way-way_123': { checked: true },
        'way-passage-see-through-way_123': { checked: true },
        'way-passage-auto-close-way_123': { checked: false },
        'way-passage-prevent-close-way_123': { checked: true },
    };

    const origGetElementById = document.getElementById;
    document.getElementById = (id) => inputs[id] || origGetElementById.call(document, id);

    window.api = {
        updateNode: async (id, patch) => {
            patchedProperties = patch.properties;
        },
        updateEdge: async () => {},
    };

    try {
        await window.InspectorWayView.saveWayPassage('way_123');

        assertTrue(!!patchedProperties, 'updateNode was called with patch');
        assertEq(patchedProperties.refusal_message, 'The gate is firmly chained.', 'refusal_message saved');
        assertEq(patchedProperties.entry_phrase, 'walk through the gate', 'entry_phrase saved');
        assertEq(patchedProperties.requires_item, 'iron_key, tag:heavy', 'requires_item saved');
        assertEq(patchedProperties.current_state, 'locked', 'current_state saved');
        assertEq(patchedProperties.requires, 'crawl', 'requires saved');
    } finally {
        document.getElementById = origGetElementById;
    }
});

test('way template sync includes refusal_message, entry_phrase, and requires_item', () => {
    window.worldState.getNode = (id) => ({
        id: 'way_456',
        name: 'Passage',
        properties: {
            description: 'A tunnel.',
            refusal_message: 'Too dark to enter.',
            entry_phrase: 'creep into the tunnel',
            requires_item: 'torch',
        },
    });

    const reg = window.InspectorTemplateSync?.registry?.get?.('way') || {};
    if (reg.buildWorldPayload) {
        const payload = reg.buildWorldPayload('way_456');
        assertEq(payload.refusal_message, 'Too dark to enter.', 'payload refusal_message');
        assertEq(payload.entry_phrase, 'creep into the tunnel', 'payload entry_phrase');
        assertEq(payload.requires_item, 'torch', 'payload requires_item');

        const keys = reg.sections.map((s) => s.key);
        assertTrue(keys.includes('refusal_message'), 'sections has refusal_message');
        assertTrue(keys.includes('entry_phrase'), 'sections has entry_phrase');
        assertTrue(keys.includes('requires_item'), 'sections has requires_item');
    }
});
