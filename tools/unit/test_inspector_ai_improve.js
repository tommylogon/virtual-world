/**
 * Unit tests for InspectorHelpers.improveWithAI (task-760).
 */

test('improveWithAI routes through DiffModal and does not write on cancel', async () => {
    let diffModalCalled = false;
    let updateNodeCalled = false;

    // Stubs
    window.worldState.getNode = (id) => ({
        id: 'item_sword',
        name: 'Iron Sword',
        properties: {
            description: 'A rusty iron blade.',
            tags: ['weapon', 'rusty'],
            locked_fields: ['tags'],
        },
    });
    window.worldState.fetch = async () => {};

    window.config.apiKey = 'test-key';
    window.config.model = 'test-model';

    window.llmClient = {
        chat: async () => JSON.stringify({
            description: 'A polished steel sword.',
            tags: ['weapon', 'sharp', 'legendary'],
            weight: 2.5,
        }),
    };

    window.DiffModal = {
        show: async (current, incoming, sections, opts) => {
            diffModalCalled = true;
            assertEq(current.description, 'A rusty iron blade.', 'current description matches');
            assertEq(incoming.description, 'A polished steel sword.', 'incoming description matches');
            // Locked field 'tags' must NOT be in incoming or sections
            assertFalse('tags' in incoming, 'locked field tags not in incoming');
            assertFalse(sections.some((s) => s.key === 'tags'), 'locked field tags not in sections');
            return null; // simulate user Cancel
        },
    };

    window.api = {
        updateNode: async () => { updateNodeCalled = true; },
    };

    const spec = {
        btnId: 'test-improve-btn',
        id: 'item',
        system: 'test-system',
        buildPrompt: (node, locked) => 'prompt',
        apply: (parsed, node, locked, update) => {
            const propUpdate = {};
            if (parsed.description && !locked.includes('description')) propUpdate.description = parsed.description;
            if (parsed.tags && !locked.includes('tags')) propUpdate.tags = parsed.tags;
            if (parsed.weight && !locked.includes('weight')) propUpdate.weight = parsed.weight;
            update.properties = propUpdate;
        },
    };

    await window.InspectorHelpers.improveWithAI('item_sword', spec);

    assertTrue(diffModalCalled, 'DiffModal.show was called');
    assertFalse(updateNodeCalled, 'api.updateNode was NOT called on Cancel');
});

test('improveWithAI applies only user-selected sections in a single updateNode call', async () => {
    let capturedUpdate = null;

    window.worldState.getNode = (id) => ({
        id: 'item_shield',
        name: 'Wooden Shield',
        properties: {
            description: 'A battered wooden buckler.',
            weight: 3.0,
            uses: 5,
        },
    });
    window.worldState.fetch = async () => {};

    window.llmClient = {
        chat: async () => JSON.stringify({
            description: 'A reinforced oak shield.',
            weight: 3.5,
            uses: 10,
        }),
    };

    window.DiffModal = {
        show: async (current, incoming, sections, opts) => {
            // User chooses to keep ONLY description, dropping weight and uses
            return {
                action: 'update',
                sections: ['description'],
            };
        },
    };

    window.api = {
        updateNode: async (nodeId, payload) => {
            capturedUpdate = payload;
        },
    };

    const spec = {
        btnId: 'test-improve-btn',
        id: 'item',
        system: 'test-system',
        buildPrompt: () => 'prompt',
        apply: (parsed, node, locked, update) => {
            update.properties = {
                description: parsed.description,
                weight: parsed.weight,
                uses: parsed.uses,
            };
        },
    };

    await window.InspectorHelpers.improveWithAI('item_shield', spec);

    assertTrue(capturedUpdate !== null, 'api.updateNode was called');
    assertEq(capturedUpdate.properties.description, 'A reinforced oak shield.', 'description applied');
    assertFalse('weight' in capturedUpdate.properties, 'dropped section weight not applied');
    assertFalse('uses' in capturedUpdate.properties, 'dropped section uses not applied');
});
