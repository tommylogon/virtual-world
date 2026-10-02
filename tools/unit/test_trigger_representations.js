/**
 * test_trigger_representations.js — task-636.
 *
 * A trigger lives in two copies: the `triggers` edge properties and the target
 * `logic_trigger` node properties. The engine reads the edge first and falls
 * back to the node. These tests pin the one compiler (TriggerGraph.
 * triggerDefFromEdge / triggersFromGraphEdges) that the item library and the
 * inspector both use, so a mechanic authored on either copy is visible.
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
    assertEq(out, [{
        trigger_type: ['on_use'],
        effects: def.effects,
        conditions: def.conditions,
        target_name: '', target_state: '', success_message: '', fail_message: '',
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
