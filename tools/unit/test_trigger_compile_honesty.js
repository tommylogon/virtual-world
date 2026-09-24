/**
 * test_trigger_compile_honesty.js — task-501.
 *
 * The trigger node graph draws a linear AND chain and the engine supports only
 * a single fail message on a condition's NO branch. These tests pin the honest
 * behaviour: every imported condition is kept (not just the first), an imported
 * OR/NOT group round-trips unchanged, editing such a group is refused rather
 * than silently flattened to AND, and a NO branch with more than one effect is
 * refused rather than truncated to a message.
 */

function andChain() {
    return TriggerGraph.triggerToGraph({
        trigger_type: 'on_use',
        conditions: { operator: 'and', conditions: [
            { type: 'has_trait', value: 'goblin' },
            { type: 'in_area', area: 'Camp', target: 'npc' },
        ] },
        effects: [{ type: 'message', params: { message: 'hi' } }],
    });
}

test('import keeps every condition, not just the first', () => {
    const g = andChain();
    assertEq(g.nodes.filter(n => n.type === 'condition').length, 2,
             'both condition nodes are drawn');
    assertEq(TriggerGraph.compileToEngine(g).conditions, {
        operator: 'and',
        conditions: [
            { type: 'has_trait', value: 'goblin' },
            { type: 'in_area', area: 'Camp', target: 'npc' },
        ],
    }, 'the whole AND chain round-trips');
});

test('an OR group survives the round trip', () => {
    const tree = { operator: 'or', conditions: [
        { type: 'has_trait', value: 'goblin' },
        { type: 'in_area', area: 'Camp', target: 'npc' },
    ] };
    const compiled = TriggerGraph.compileToEngine(
        TriggerGraph.triggerToGraph({ trigger_type: 'on_use', conditions: tree,
                                      effects: [{ type: 'message', params: { message: 'hi' } }] }));
    assertEq(compiled.conditions, tree, 'the OR tree is re-emitted unchanged');
    assertEq(TriggerGraph.compileError(compiled), '', 'and compiles clean');
});

test('a NOT group survives the round trip', () => {
    const tree = { operator: 'not', conditions: [{ type: 'has_trait', value: 'goblin' }] };
    const compiled = TriggerGraph.compileToEngine(
        TriggerGraph.triggerToGraph({ trigger_type: 'on_use', conditions: tree,
                                      effects: [{ type: 'message', params: { message: 'hi' } }] }));
    assertEq(compiled.conditions, tree, 'the NOT tree is re-emitted unchanged');
});

test('a nested group survives the round trip', () => {
    const tree = { operator: 'and', conditions: [
        { type: 'has_trait', value: 'goblin' },
        { operator: 'or', conditions: [
            { type: 'in_area', area: 'Camp', target: 'npc' },
            { type: 'in_area', area: 'Pit', target: 'npc' },
        ] },
    ] };
    const compiled = TriggerGraph.compileToEngine(
        TriggerGraph.triggerToGraph({ trigger_type: 'on_use', conditions: tree,
                                      effects: [{ type: 'message', params: { message: 'hi' } }] }));
    assertEq(compiled.conditions, tree, 'the nested tree is re-emitted unchanged');
});

test('editing a grouped condition is refused, not flattened to AND', () => {
    const tree = { operator: 'or', conditions: [
        { type: 'has_trait', value: 'goblin' },
        { type: 'in_area', area: 'Camp', target: 'npc' },
    ] };
    const g = TriggerGraph.triggerToGraph({ trigger_type: 'on_use', conditions: tree,
                                            effects: [{ type: 'message', params: { message: 'hi' } }] });
    g.nodes.find(n => n.type === 'condition').props.value = 'elf';
    const compiled = TriggerGraph.compileToEngine(g);
    assertTrue(TriggerGraph.compileError(compiled).length > 0, 'refusal reason is set');
});

test('a single NO-branch message becomes fail_message and round-trips', () => {
    const g = TriggerGraph.triggerToGraph({
        trigger_type: 'on_use',
        conditions: [{ type: 'has_trait', value: 'goblin' }],
        effects: [{ type: 'message', params: { message: 'yes' } }],
        fail_message: 'no',
    });
    const noWire = g.wires.find(w => w.from[1] === 'output_no');
    assertTrue(noWire, 'the fail message is drawn on the NO socket');
    const compiled = TriggerGraph.compileToEngine(g);
    assertEq(compiled.fail_message, 'no', 'fail_message survives');
    assertEq(TriggerGraph.compileError(compiled), '', 'a lone NO message compiles clean');
});

test('a NO branch with two effects is refused, not truncated', () => {
    const g = {
        nodes: [
            { id: 'n0', type: 'trigger', props: { trigger_type: 'on_use' } },
            { id: 'n1', type: 'condition', props: { condition_type: 'has_trait', value: 'goblin' } },
            { id: 'n2', type: 'effect', props: { effect_type: 'message', message: 'yes' } },
            { id: 'n3', type: 'effect', props: { effect_type: 'message', message: 'no1' } },
            { id: 'n4', type: 'effect', props: { effect_type: 'message', message: 'no2' } },
        ],
        wires: [
            { id: 'w0', from: ['n0', 'output'], to: ['n1', 'input'] },
            { id: 'w1', from: ['n1', 'output_yes'], to: ['n2', 'input'] },
            { id: 'w2', from: ['n1', 'output_no'], to: ['n3', 'input'] },
            { id: 'w3', from: ['n3', 'output'], to: ['n4', 'input'] },
        ],
    };
    const compiled = TriggerGraph.compileToEngine(g);
    assertTrue(TriggerGraph.compileError(compiled).length > 0, 'the refusal reason is set');
});

// ── behavior mode (task-503) ──────────────────────────────────────────────

function behaviorGraph(withNo) {
    const nodes = [
        { id: 'b0', type: 'behavior', props: { trigger: 'on_tick' } },
        { id: 'c1', type: 'condition', props: { condition_type: 'has_trait', value: 'goblin' } },
        { id: 'a1', type: 'action', props: { action_type: 'message', text: 'yes' } },
    ];
    const wires = [
        { id: 'w0', from: ['b0', 'output'], to: ['c1', 'input'] },
        { id: 'w1', from: ['c1', 'output_yes'], to: ['a1', 'input'] },
    ];
    if (withNo) {
        nodes.push({ id: 'a2', type: 'action', props: { action_type: 'message', text: 'no' } });
        wires.push({ id: 'w2', from: ['c1', 'output_no'], to: ['a2', 'input'] });
    }
    return { nodes, wires };
}

test('behavior mode: a NO branch carrying an action is refused', () => {
    const detailed = TriggerGraph.compileToBehaviorsWithIssues(behaviorGraph(true));
    assertTrue(TriggerGraph.compileError(detailed).length > 0, 'the refusal reason is set');
    assertEq(TriggerGraph.compileToBehaviors(behaviorGraph(true)).length, 1,
             'compileToBehaviors still returns the behavior array');
});

test('behavior mode: a clean graph compiles without a refusal', () => {
    const detailed = TriggerGraph.compileToBehaviorsWithIssues(behaviorGraph(false));
    assertEq(TriggerGraph.compileError(detailed), '', 'no refusal reason');
    assertEq(detailed.behaviors.length, 1, 'one behavior compiled');
});

