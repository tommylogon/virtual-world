/**
 * test_nl_editor.js — Unit tests for Natural-Language Editor (task-387).
 * Tests staging buffer, overlay graph view, and atomic context window pruning.
 */
'use strict';

// ── ContextWindowManager Atomic Pruning ──

test('ContextWindowManager preserves assistant tool_calls and matching tool results atomically', () => {
    const cwm = new ContextWindowManager({ maxTokens: 100, maxMessages: 5, recentTurnCount: 1 });
    const messages = [
        { role: 'system', content: 'system prompt' },
        { role: 'user', content: 'turn 1' },
        { role: 'assistant', content: 'thought 1' },
        { role: 'user', content: 'turn 2' },
        { role: 'assistant', content: 'calling tool', tool_calls: [{ id: 'call_1', function: { name: 'search_library_items' } }] },
        { role: 'tool', tool_call_id: 'call_1', content: '{"matches":[]}' },
        { role: 'user', content: 'turn 3' },
        { role: 'assistant', content: 'final answer' }
    ];

    messages.forEach(m => cwm.addMessage(m));
    const pruned = cwm.prune(messages);

    // Verify system message is kept
    assertEq(pruned[0].role, 'system');

    // If tool message is kept, assistant tool_calls must also be kept
    const hasTool = pruned.some(m => m.role === 'tool');
    const hasAssistantWithTools = pruned.some(m => m.role === 'assistant' && m.tool_calls);
    if (hasTool) {
        assertTrue(hasAssistantWithTools, 'Assistant with tool_calls must be preserved alongside tool result');
    }
});

// ── StagingBuffer ──

test('StagingBuffer mintId generates deterministic unique IDs', () => {
    const staging = new NLEditorStaging.StagingBuffer();
    const id1 = staging.mintId('item', 'Oak Desk');
    const id2 = staging.mintId('area', 'Hidden Library');

    assertTrue(id1.startsWith('item_oak_desk_'), 'id1 prefix correct');
    assertTrue(id2.startsWith('area_hidden_library_'), 'id2 prefix correct');
    assertTrue(id1 !== id2, 'IDs must be distinct');
});

test('StagingBuffer tracks creations, updates, and removals', () => {
    const staging = new NLEditorStaging.StagingBuffer();
    const op1 = staging.addOp('create_node', {
        node: { id: 'item_torch_1', type: 'item', name: 'Torch', properties: { tags: ['light_source'] } }
    }, 'Create Torch');

    assertEq(staging.getOps().length, 1);
    const creations = staging.getStagedCreations();
    assertTrue(creations['item_torch_1'] !== undefined, 'item_torch_1 in creations');
    assertEq(creations['item_torch_1'].name, 'Torch');

    const op2 = staging.addOp('update_node', {
        node_id: 'item_torch_1',
        patch: { current_state: 'lit' }
    }, 'Update Torch to lit');

    assertEq(staging.getOps().length, 2);
    const updates = staging.getStagedUpdates();
    assertEq(updates['item_torch_1'].current_state, 'lit');

    // Remove first op
    const removed = staging.removeOp(op1.id);
    assertTrue(removed, 'op1 removed');
    assertEq(staging.getOps().length, 1);
});

// ── OverlayGraphView ──

test('OverlayGraphView queries uncommitted staged entities and respects deletions', () => {
    const staging = new NLEditorStaging.StagingBuffer();
    const router = new NLEditorTools.ToolRouter(staging);
    const overlay = router.overlay;

    // Stage a new area and item
    staging.addOp('create_node', {
        node: { id: 'area_cellar_1', type: 'area', name: 'Dark Cellar', properties: { tags: ['cold'] } }
    }, 'Create Cellar');

    staging.addOp('create_node', {
        node: { id: 'item_lantern_1', type: 'item', name: 'Brass Lantern', properties: { tags: ['light_source'] } }
    }, 'Create Lantern');

    // Stage an update to lantern
    staging.addOp('update_node', {
        node_id: 'item_lantern_1',
        patch: { current_state: 'lit' }
    }, 'Light lantern');

    // Node lookup should resolve staged creation with staged patch applied
    const lantern = overlay.getNode('item_lantern_1');
    assertTrue(lantern !== null, 'lantern found in overlay');
    assertEq(lantern.name, 'Brass Lantern');
    assertEq(lantern.properties.current_state, 'lit');
    assertTrue(lantern.staged, 'lantern marked as staged');

    // Search nodes should find both
    const results = overlay.searchNodes('cellar');
    assertEq(results.length, 1);
    assertEq(results[0].id, 'area_cellar_1');
    assertTrue(results[0].staged, 'search match is staged');

    // Staged deletion hides node from overlay
    staging.addOp('delete_node', { node_id: 'area_cellar_1' }, 'Delete Cellar');
    const deletedArea = overlay.getNode('area_cellar_1');
    assertEq(deletedArea, null, 'deleted node should not be returned');
});
