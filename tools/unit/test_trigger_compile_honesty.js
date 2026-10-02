/**
 * test_trigger_compile_honesty.js — task-501.
 *
 * The trigger node graph draws a linear AND chain plus real group nodes for
 * OR/NOT (task-502), and the engine supports only a single fail message on a
 * condition's NO branch. These tests pin the honest behaviour: every imported
 * condition is kept (not just the first), an imported OR/NOT group round-trips
 * unchanged, editing a grouped condition compiles the edit back into the group
 * (no side-channel, no refusal), and a NO branch with more than one effect is
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

test('editing a condition inside an imported OR group compiles the edit into the OR tree', () => {
    const tree = { operator: 'or', conditions: [
        { type: 'has_trait', value: 'goblin' },
        { type: 'in_area', area: 'Camp', target: 'npc' },
    ] };
    const g = TriggerGraph.triggerToGraph({ trigger_type: 'on_use', conditions: tree,
                                            effects: [{ type: 'message', params: { message: 'hi' } }] });
    assertEq(g.nodes.filter(n => n.type === 'group').length, 1, 'a real group node is drawn');
    assertEq(g.nodes.filter(n => n.type === 'condition').length, 2, 'both children are drawn');
    g.nodes.find(n => n.type === 'condition').props.value = 'elf';
    const compiled = TriggerGraph.compileToEngine(g);
    assertEq(TriggerGraph.compileError(compiled), '', 'the edited group compiles clean');
    assertEq(compiled.conditions, { operator: 'or', conditions: [
        { type: 'has_trait', value: 'elf' },
        { type: 'in_area', area: 'Camp', target: 'npc' },
    ] }, 'the edit is reflected in the OR tree');
});

test('a group compiles for each operator', () => {
    const mk = (op, children) => TriggerGraph.compileToEngine(
        TriggerGraph.triggerToGraph({ trigger_type: 'on_use',
            conditions: { operator: op, conditions: children },
            effects: [{ type: 'message', params: { message: 'hi' } }] })).conditions;
    assertEq(mk('and', [{ type: 'has_trait', value: 'a' }, { type: 'has_trait', value: 'b' }]),
             { operator: 'and', conditions: [{ type: 'has_trait', value: 'a' }, { type: 'has_trait', value: 'b' }] }, 'AND');
    assertEq(mk('or', [{ type: 'has_trait', value: 'a' }, { type: 'has_trait', value: 'b' }]),
             { operator: 'or', conditions: [{ type: 'has_trait', value: 'a' }, { type: 'has_trait', value: 'b' }] }, 'OR');
    assertEq(mk('not', [{ type: 'has_trait', value: 'a' }]),
             { operator: 'not', conditions: [{ type: 'has_trait', value: 'a' }] }, 'NOT');
});

test('a hand-built group node compiles to the engine tree', () => {
    const g = { nodes: [
        { id: 'n0', type: 'trigger', props: { trigger_type: 'on_use' } },
        { id: 'n1', type: 'group', props: { operator: 'or' } },
        { id: 'n2', type: 'condition', props: { condition_type: 'has_trait', value: 'a' } },
        { id: 'n3', type: 'condition', props: { condition_type: 'has_trait', value: 'b' } },
        { id: 'n4', type: 'effect', props: { effect_type: 'message', message: 'x' } },
    ], wires: [
        { id: 'w0', from: ['n0', 'output'], to: ['n1', 'input'] },
        { id: 'w1', from: ['n1', 'child'], to: ['n2', 'input'] },
        { id: 'w2', from: ['n2', 'output_yes'], to: ['n3', 'input'] },
        { id: 'w3', from: ['n1', 'output_yes'], to: ['n4', 'input'] },
    ] };
    const compiled = TriggerGraph.compileToEngine(g);
    assertEq(TriggerGraph.compileError(compiled), '', 'compiles clean');
    assertEq(compiled.conditions, { operator: 'or', conditions: [
        { type: 'has_trait', value: 'a' }, { type: 'has_trait', value: 'b' }] }, 'group children form the OR tree');
});

test('deleting a group child drops it from the compiled group', () => {
    const tree = { operator: 'or', conditions: [
        { type: 'has_trait', value: 'a' }, { type: 'has_trait', value: 'b' }] };
    const g = TriggerGraph.triggerToGraph({ trigger_type: 'on_use', conditions: tree,
                                            effects: [{ type: 'message', params: { message: 'hi' } }] });
    const last = g.nodes.filter(n => n.type === 'condition').pop();
    g.nodes = g.nodes.filter(n => n.id !== last.id);
    g.wires = g.wires.filter(w => w.from[0] !== last.id && w.to[0] !== last.id);
    const compiled = TriggerGraph.compileToEngine(g);
    assertEq(compiled.conditions, { operator: 'or', conditions: [
        { type: 'has_trait', value: 'a' }] }, 'the removed child is gone from the OR tree');
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

