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

test('diff: update_player diffs schedule/goals against context.players', () => {
    const players = {
        Alice: {
            name: 'Alice',
            schedule: [],
            goals: [{ id: 'eat', text: 'Eat breakfast', priority: 1, status: 'active' }],
        },
    };
    const op = {
        type: 'update_player',
        payload: {
            character: 'Alice',
            patch: {
                schedule: [{ start: '08:00', duration_minutes: 60, activity: 'work', area: 'area_smithy' }],
                goals: [{ id: 'eat', text: 'Eat breakfast', priority: 1, status: 'active' }],
            },
        },
    };
    const diff = NLEditorDiff.opDiff(op, { players });
    assertEq(diff.kind, 'update-player');
    assertEq(diff.changes.length, 1);
    assertEq(diff.changes[0].key, 'schedule');
    const lines = NLEditorDiff.summaryLines(op, { players });
    assertEq(lines.length, 1);
    assertTrue(lines[0].startsWith('schedule: [] → '));
});

test('diff: spawn_library_item, attach, detach, connect_areas, create_trigger, rename_character get one-line labels', () => {
    assertEq(
        NLEditorDiff.summaryLines({ type: 'spawn_library_item', payload: { library_id: 'torch', parent_id: 'character_alice' } }, {}),
        ['+ spawn torch into character_alice']
    );
    assertEq(
        NLEditorDiff.summaryLines({ type: 'attach', payload: { from_id: 'item_sword', to_id: 'character_alice', relation: 'carrying' } }, {}),
        ['+ attach item_sword -> character_alice (carrying)']
    );
    assertEq(
        NLEditorDiff.summaryLines({ type: 'detach', payload: { from_id: 'item_sword', to_id: 'character_alice', relation: 'carrying' } }, {}),
        ['− detach item_sword from character_alice (carrying)']
    );
    assertEq(
        NLEditorDiff.summaryLines({ type: 'connect_areas', payload: { area_a_id: 'area_a', area_b_id: 'area_b', way_id: 'way_ab' } }, {}),
        ['+ connect area_a <-> area_b via way_ab']
    );
    assertEq(
        NLEditorDiff.summaryLines({ type: 'create_trigger', payload: { owner_id: 'item_trap', trigger: { trigger_type: 'enter_area' } } }, {}),
        ['+ trigger (enter_area) on item_trap']
    );
    assertEq(
        NLEditorDiff.summaryLines({ type: 'rename_character', payload: { character: 'Bob', new_name: 'Robert' } }, {}),
        ['rename Bob -> Robert']
    );
});
