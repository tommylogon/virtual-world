/**
 * test_nl_editor_diff.js — property-level diff for staged ops (task-461).
 */

test('diff: patchProps folds nested and flat keys', () => {
    assertEq(NLEditorDiff.patchProps({ properties: { a: 1 }, b: 2, name: 'x', id: 'y' }), { a: 1, b: 2 });
    assertEq(NLEditorDiff.patchProps(null), {});
});

test('diff: diffPairs flattens dict values key-by-key', () => {
    const pairs = NLEditorDiff.diffPairs('traits', { hardy: true }, { hardy: true, dark_vision: true });
    assertEq(pairs, [{ key: 'traits.dark_vision', before: undefined, after: true }]);
});

test('diff: update_node reports before/after against the live node', () => {
    const nodes = { character_miki: { id: 'character_miki', type: 'character', properties: { description: 'old', traits: { hardy: true } } } };
    const diff = NLEditorDiff.opDiff(
        { type: 'update_node', payload: { node_id: 'character_miki', patch: { description: 'new', traits: { hardy: true, dark_vision: true } } } },
        { nodes }
    );
    assertEq(diff.kind, 'update');
    assertEq(diff.changes, [
        { key: 'description', before: 'old', after: 'new' },
        { key: 'traits.dark_vision', before: undefined, after: true },
    ]);
});

test('diff: a no-op patch is called out', () => {
    const nodes = { area_hall: { id: 'area_hall', type: 'area', properties: { description: 'same' } } };
    const op = { type: 'update_node', payload: { node_id: 'area_hall', patch: { description: 'same' } } };
    assertEq(NLEditorDiff.summaryLines(op, { nodes }), ['(no property change — will no-op)']);
});

test('diff: bulk op lists each matched target', () => {
    const nodes = {
        character_grub: { id: 'character_grub', type: 'character', properties: {} },
        character_nub: { id: 'character_nub', type: 'character', properties: {} },
    };
    const op = {
        type: 'update_matching_nodes',
        payload: { selector: { kind: 'character' }, patch: { traits: { dark_vision: true } }, matched_ids: ['character_grub', 'character_nub'] },
    };
    const lines = NLEditorDiff.summaryLines(op, { nodes });
    assertEq(lines, [
        'character_grub: traits.dark_vision: — → true',
        'character_nub: traits.dark_vision: — → true',
    ]);
});

test('diff: create/delete/library ops get a one-line label', () => {
    assertEq(NLEditorDiff.summaryLines({ type: 'create_node', payload: { node: { id: 'item_lamp' } } }, {}), ['+ create item_lamp']);
    assertEq(NLEditorDiff.summaryLines({ type: 'delete_node', payload: { node_id: 'item_lamp' } }, {}), ['− delete item_lamp']);
    assertEq(
        NLEditorDiff.summaryLines({ type: 'library_upsert', payload: { registry_type: 'traits', id: 'sturdy' } }, {}),
        ['library traits: upsert sturdy']
    );
});

test('diff: staged creations supply the pre-state for a patch', () => {
    const creations = { item_lamp: { id: 'item_lamp', type: 'item', properties: { current_state: 'unlit' } } };
    const diff = NLEditorDiff.opDiff(
        { type: 'update_node', payload: { node_id: 'item_lamp', patch: { current_state: 'lit' } } },
        { nodes: {}, creations }
    );
    assertEq(diff.changes, [{ key: 'current_state', before: 'unlit', after: 'lit' }]);
});

test('diff: long change lists are capped', () => {
    const nodes = { character_miki: { id: 'character_miki', type: 'character', properties: {} } };
    const patch = {};
    for (let i = 0; i < 6; i++) patch[`field_${i}`] = i;
    const lines = NLEditorDiff.summaryLines({ type: 'update_node', payload: { node_id: 'character_miki', patch } }, { nodes }, 3);
    assertEq(lines.length, 4);
    assertEq(lines[3], '+3 more');
});
