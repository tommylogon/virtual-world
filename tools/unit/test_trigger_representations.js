/**
 * test_trigger_representations.js - task-636, bug-567.
 *
 * A trigger is authored in `properties.triggers` on its owner; a legacy pair of
 * a `logic_trigger` node and a `triggers` edge may still exist from before the
 * task-886 migration. The readers take the property array first and fall back
 * to the edge, deduping by definition id. These tests pin the one compiler
 * (TriggerGraph.triggerDefFromEdge / triggersFromGraphEdges) that the item
 * library and the inspector both use, so a mechanic authored in either store is
 * visible, and pin the multi-root graph round trip the editor depends on.
 */

function edgeAndNode(edgeProps, nodeProps) {
    return {
        edges: [{ source: 'item_1', target: 'trig_1', type: 'triggers', properties: edgeProps }],
        nodes: { trig_1: { id: 'trig_1', type: 'logic_trigger', properties: nodeProps } },
    };
}

test('a trigger stored only on the edge compiles', () => {
    const { edges, nodes } = edgeAndNode({
        trigger_type: 'on_use',
        effects: [{ type: 'message', params: { message: 'hi' } }],
    }, {});
    const out = TriggerGraph.triggersFromGraphEdges(edges, nodes, 'item_1');
    assertEq(out.length, 1, 'one trigger');
    assertEq(out[0].trigger_type, 'on_use', 'type read from the edge');
    assertEq(out[0].effects, [{ type: 'message', params: { message: 'hi' } }], 'effects read from the edge');
});

test('a trigger stored only on the logic_trigger node compiles', () => {
    const { edges, nodes } = edgeAndNode({}, {
        trigger_type: 'on_take',
        effects: [{ type: 'message', params: { message: 'taken' } }],
        conditions: { operator: 'or', conditions: [{ type: 'eq', target: 'a', value: '1' }] },
    });
    const out = TriggerGraph.triggersFromGraphEdges(edges, nodes, 'item_1');
    assertEq(out[0].trigger_type, 'on_take', 'type falls back to the node');
    assertEq(out[0].effects, [{ type: 'message', params: { message: 'taken' } }], 'effects fall back to the node');
    assertEq(out[0].conditions, { operator: 'or', conditions: [{ type: 'eq', target: 'a', value: '1' }] }, 'tree conditions survive');
});

test('the edge copy wins per field, matching the engine precedence', () => {
    const { edges, nodes } = edgeAndNode(
        { trigger_type: 'on_use', effects: [{ type: 'message', params: { message: 'edge' } }] },
        { trigger_type: 'on_take', effects: [{ type: 'message', params: { message: 'node' } }] });
    const out = TriggerGraph.triggersFromGraphEdges(edges, nodes, 'item_1');
    assertEq(out[0].trigger_type, 'on_use', 'edge type wins');
    assertEq(out[0].effects, [{ type: 'message', params: { message: 'edge' } }], 'edge effects win');
});

test('a flat condition list keeps its conditions_logic', () => {
    const { edges, nodes } = edgeAndNode({
        trigger_type: 'on_use',
        conditions: [{ type: 'eq', target: 'a', value: '1' }],
        conditions_logic: 'or',
    }, {});
    const out = TriggerGraph.triggersFromGraphEdges(edges, nodes, 'item_1');
    assertEq(out[0].conditions, { operator: 'or', conditions: [{ type: 'eq', target: 'a', value: '1' }] },
             'flat list becomes an OR tree');
});

test('a legacy singular condition becomes an AND tree', () => {
    const { edges, nodes } = edgeAndNode({
        trigger_type: 'on_use',
        condition: { type: 'has_trait', value: 'goblin' },
    }, {});
    const out = TriggerGraph.triggersFromGraphEdges(edges, nodes, 'item_1');
    assertEq(out[0].conditions, { operator: 'and', conditions: [{ type: 'has_trait', value: 'goblin' }] },
             'singular condition is wrapped');
});

test('legacy effect_type/effect_params normalises', () => {
    const { edges, nodes } = edgeAndNode({
        trigger_type: 'on_use', effect_type: 'adjust_vital', effect_params: { stat: 'Hunger', amount: 10 },
    }, {});
    const out = TriggerGraph.triggersFromGraphEdges(edges, nodes, 'item_1');
    assertEq(out[0].effects, [{ type: 'adjust_vital', params: { stat: 'Hunger', amount: 10 } }], 'legacy effect normalised');
});

test('an inline definition round-trips graph -> edges -> definition', () => {
    const def = {
        trigger_type: 'on_use',
        conditions: { operator: 'or', conditions: [
            { type: 'has_trait', value: 'goblin' },
            { type: 'in_area', area: 'Camp', target: 'npc' },
        ] },
        effects: [{ type: 'message', params: { message: 'hi' } }],
    };
    const compiled = TriggerGraph.compileToEngine(TriggerGraph.triggerToGraph(def));
    // Simulate what materialize_trigger writes: the same props on edge AND node.
    const { edges, nodes } = edgeAndNode(compiled, compiled);
    const out = TriggerGraph.triggersFromGraphEdges(edges, nodes, 'item_1');
    // triggerToGraph canonicalises trigger_type to the multi-select array form.
    // The legacy edge target is the definition id (bug-567): without it the
    // editor cannot match an edited block back to the entry it came from.
    assertEq(out, [{
        trigger_type: ['on_use'],
        effects: def.effects,
        conditions: def.conditions,
        target_name: '', target_state: '', success_message: '', fail_message: '',
        id: 'trig_1',
    }], 'the OR branch survives the full round trip');
});

test('triggersFromGraphEdges ignores other edge types and other sources', () => {
    const edges = [
        { source: 'item_1', target: 'trig_1', type: 'triggers', properties: { trigger_type: 'on_use' } },
        { source: 'item_1', target: 'trig_2', type: 'in', properties: {} },
        { source: 'item_2', target: 'trig_3', type: 'triggers', properties: { trigger_type: 'on_take' } },
    ];
    const nodes = { trig_1: { id: 'trig_1', type: 'logic_trigger', properties: { trigger_type: 'on_use' } } };
    const out = TriggerGraph.triggersFromGraphEdges(edges, nodes, 'item_1');
    assertEq(out.length, 1, 'only the source node’s triggers');
    assertEq(out[0].trigger_type, 'on_use', 'correct trigger');
});

// ─── bug-567: properties.triggers is the authoritative store ───

test('a property-only trigger is read with no triggers edge', () => {
    const nodes = { item_1: { id: 'item_1', type: 'item', properties: { triggers: [{
        id: 'trigger_item_1_on_use',
        trigger_type: ['on_use', 'on_drink'],
        effects: [{ type: 'message', params: { message: 'sip' } }],
        once: true,
        success_message: 'you drink',
    }] } } };
    const out = TriggerGraph.triggersFromGraphEdges([], nodes, 'item_1');
    assertEq(out.length, 1, 'one trigger despite zero edges');
    assertEq(out[0].id, 'trigger_item_1_on_use', 'the stored id survives');
    assertEq(out[0].trigger_type, ['on_use', 'on_drink'], 'both trigger types');
    assertEq(out[0].once, true, 'once survives');
    assertEq(out[0].success_message, 'you drink', 'the message survives');
});

test('a property entry and a legacy edge with the same id are one trigger', () => {
    const { edges } = edgeAndNode({ trigger_type: 'on_use' }, {});
    const nodes = { item_1: { id: 'item_1', type: 'item', properties: { triggers: [{
        id: 'trig_1', trigger_type: 'on_use', effects: [{ type: 'message', params: { message: 'stored' } }],
    }] } }, trig_1: { id: 'trig_1', type: 'logic_trigger', properties: { trigger_type: 'on_use' } } };
    const out = TriggerGraph.triggersFromGraphEdges(edges, nodes, 'item_1');
    assertEq(out.length, 1, 'deduped by id');
    assertEq(out[0].effects, [{ type: 'message', params: { message: 'stored' } }], 'the property copy wins');
});

test('a wrapped library entry normalises to a definition', () => {
    const wrapped = { item: {
        id: 'trigger_item_1_on_use',
        trigger_type: { item: ['on_use'] },
        effects: { item: { item: [
            { type: 'adjust_vital', params: { stat: 'thirst', amount: '-30' } },
            { type: 'adjust_uses', params: { delta: '-1' } },
        ] } },
        conditions: '',
    } };
    const entries = TriggerGraph.normalizeTriggerList(wrapped);
    assertEq(entries.length, 1, 'one definition');
    assertEq(entries[0].trigger_type, ['on_use'], 'trigger_type unwrapped');
    assertEq(entries[0].effects.length, 2, 'both effects unwrapped');
    assertEq(entries[0].conditions, undefined, 'the empty condition string is dropped');
});

test('triggersToGraph draws one root per definition and keeps their ids', () => {
    const graph = TriggerGraph.triggersToGraph([
        { id: 'a', trigger_type: 'on_use', effects: [{ type: 'message', params: { message: 'a' } }] },
        { id: 'b', trigger_type: 'on_take', effects: [{ type: 'message', params: { message: 'b' } }] },
    ]);
    const roots = graph.nodes.filter((n) => n.type === 'trigger');
    assertEq(roots.length, 2, 'two roots, not one');
    assertEq(roots[0].props.id, 'a', 'first id stays on its root');
    assertEq(roots[1].props.id, 'b', 'second id stays on its root');
    assertEq(graph.nodes.length, new Set(graph.nodes.map((n) => n.id)).size, 'graph ids are unique');
});

test('compileToTriggers round-trips every root with its state', () => {
    const graph = TriggerGraph.triggersToGraph([
        { id: 'a', trigger_type: 'on_use', once: true, success_message: 'yum',
          effects: [{ type: 'message', params: { message: 'a' } }] },
        { id: 'b', trigger_type: 'on_take', name: 'grab',
          effects: [{ type: 'message', params: { message: 'b' } }] },
    ]);
    const defs = TriggerGraph.compileToTriggers(graph);
    assertEq(defs.length, 2, 'both roots compile');
    assertEq(defs[0].id, 'a', 'first id');
    assertEq(defs[0].once, true, 'once survives the round trip');
    assertEq(defs[0].success_message, 'yum', 'success message survives');
    assertEq(defs[1].id, 'b', 'second id');
    assertEq(defs[1].name, 'grab', 'name survives');
    assertEq(TriggerGraph.compileToEngine(graph).id, 'a', 'the single-root wrapper returns the first');
});
