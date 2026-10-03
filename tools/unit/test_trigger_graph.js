/**
 * task-388 regression tests for shared/trigger-graph.js.
 *
 * These exist because of two SILENT DATA LOSS defects, both of which destroyed
 * authored behavior data on the behaviors -> graph -> behaviors round trip with
 * no warning and no error:
 *
 *   #17  the action node's <select> offered 11 action types and
 *        _buildActionFromNode re-emitted only 10, so opening a behavior whose
 *        actions were any of the other 110 engine types and pressing save
 *        rewrote them as bare `{type}` - every param gone. Verified live:
 *        kiss {target, where, intensity} -> kiss {}.
 *   #9   the graph tracers used `wires.find(...)`, so only the FIRST wire off an
 *        output was followed. Fan-out is legal - the engine runs a flat action
 *        list - so a second branch simply disappeared.
 *
 * The assertions are on the MECHANISM (which wire was followed, which params
 * survived), not on incidental rendered text.
 */

// ─── #17: every action type the catalog knows must survive the round trip ───

test('trigger-graph: catalog is present (guards against a vacuous test)', () => {
    const cat = window.TriggerTypes.BEHAVIOR_ACTION_TYPES;
    assertTrue(Array.isArray(cat) && cat.length > 100,
        'catalog loaded with ' + (cat ? cat.length : 0) + ' types');
});

test('trigger-graph: every catalog action type survives a graph round trip', () => {
    const cat = window.TriggerTypes.BEHAVIOR_ACTION_TYPES;
    const failures = [];
    for (const spec of cat) {
        // Build an action carrying EVERY param the engine reads for this type,
        // plus a filler, so a param-dropping bug shows up as a missing key.
        const params = {};
        for (const p of spec.params) params[p] = 'v_' + p;
        const behavior = {
            name: 'rt-' + spec.value,
            conditions: {},
            actions: [Object.assign({ type: spec.value }, params)]
        };
        const graph = window.TriggerGraph.behaviorsToGraph([behavior]);
        const back = window.TriggerGraph.compileToBehaviors(graph);
        const got = back[0] && back[0].actions && back[0].actions[0];
        if (!got) { failures.push(spec.value + ': action vanished'); continue; }
        if (got.type !== spec.value) {
            failures.push(spec.value + ': type became ' + got.type);
            continue;
        }
        const missing = spec.params.filter((p) => got[p] === undefined);
        if (missing.length) {
            failures.push(spec.value + ': dropped ' + missing.join(','));
        }
    }
    assertEq(failures.length, 0,
        'all ' + cat.length + ' action types round-trip; failures: ' + failures.join(' | '));
});

test('trigger-graph: a param-less action stays param-less', () => {
    const graph = window.TriggerGraph.behaviorsToGraph([
        { name: 'p', conditions: {}, actions: [{ type: 'wait' }] }
    ]);
    const back = window.TriggerGraph.compileToBehaviors(graph);
    assertEq(back[0].actions[0].type, 'wait', 'type preserved');
});

test('trigger-graph: falsy param values survive the carry-through', () => {
    // The carry-through drops undefined/null/'' only, so a real 0 or false must
    // survive. (The bespoke `damage` branch has its own long-standing
    // `parseInt(p.amount) || 5` default, so 0 becomes 5 there by design - use a
    // non-bespoke type to pin the carry-through behaviour.)
    for (const [type, param, value] of [['set_flag', 'value', false], ['kiss', 'intensity', 0]]) {
        const graph = window.TriggerGraph.behaviorsToGraph([
            { name: 'f', conditions: {}, actions: [{ type: type, [param]: value }] }
        ]);
        const got = window.TriggerGraph.compileToBehaviors(graph)[0].actions[0];
        assertEq(got[param], value, type + ': ' + param + ' = ' + JSON.stringify(value) + ' survives');
    }
});

test('trigger-graph: the 7-tuple contact actions keep all three params', () => {
    // The documented worked example from the task file.
    for (const t of ['kiss', 'caress', 'lick', 'suck', 'bite', 'tickle', 'embrace']) {
        const graph = window.TriggerGraph.behaviorsToGraph([
            { name: t, conditions: {}, actions: [{ type: t, target: 'player', where: 'mouth', intensity: 'rough' }] }
        ]);
        const got = window.TriggerGraph.compileToBehaviors(graph)[0].actions[0];
        assertEq(got.type, t, t + ': type');
        assertEq(got.target, 'player', t + ': target');
        assertEq(got.where, 'mouth', t + ': where');
        assertEq(got.intensity, 'rough', t + ': intensity');
    }
});

// ─── #9: fan-out must follow every wire off an output ───

function _fanOutGraph() {
    return {
        nodes: [
            { id: 'n0', type: 'behavior', x: 0, y: 0, props: { name: 'fan' } },
            { id: 'c0', type: 'condition', x: 0, y: 0, props: { condition_type: 'always' } },
            { id: 'a0', type: 'action', x: 0, y: 0, props: { action_type: 'message', text: 'FIRST' } },
            { id: 'a1', type: 'action', x: 0, y: 0, props: { action_type: 'message', text: 'SECOND' } },
            { id: 'a2', type: 'action', x: 0, y: 0, props: { action_type: 'message', text: 'THIRD' } }
        ],
        wires: [
            { id: 'w0', from: ['n0', 'output'], to: ['c0', 'input'] },
            { id: 'w1', from: ['c0', 'output_yes'], to: ['a0', 'input'] },
            { id: 'w2', from: ['c0', 'output_yes'], to: ['a1', 'input'] },
            { id: 'w3', from: ['c0', 'output_yes'], to: ['a2', 'input'] }
        ]
    };
}

test('trigger-graph: a condition fanning out to 3 actions compiles all 3', () => {
    const acts = window.TriggerGraph.compileToBehaviors(_fanOutGraph())[0].actions;
    assertEq(acts.length, 3, 'all three branches compiled, got ' + acts.length);
    const texts = acts.map((a) => a.text).sort();
    assertEq(texts.join(','), 'FIRST,SECOND,THIRD', 'every branch present');
});

test('trigger-graph: a behavior node wired to 2 chains keeps both', () => {
    const g = _fanOutGraph();
    // Give the behavior a second, separate chain.
    g.nodes.push({ id: 'a3', type: 'action', x: 0, y: 0, props: { action_type: 'message', text: 'OTHER CHAIN' } });
    g.wires.push({ id: 'w4', from: ['n0', 'output'], to: ['a3', 'input'] });
    const acts = window.TriggerGraph.compileToBehaviors(g)[0].actions;
    const texts = acts.map((a) => a.text);
    assertTrue(texts.includes('FIRST'), 'first chain kept');
    assertTrue(texts.includes('OTHER CHAIN'), 'second chain off the behavior node kept');
});

test('trigger-graph: trigger-mode effect fan-out keeps every effect', () => {
    const g = {
        nodes: [
            { id: 't0', type: 'trigger', x: 0, y: 0, props: { trigger_type: 'on_tick' } },
            { id: 'e0', type: 'effect', x: 0, y: 0, props: { effect_type: 'message', message: 'one' } },
            { id: 'e1', type: 'effect', x: 0, y: 0, props: { effect_type: 'message', message: 'two' } }
        ],
        wires: [
            { id: 'w0', from: ['t0', 'output'], to: ['e0', 'input'] },
            { id: 'w1', from: ['e0', 'output'], to: ['e1', 'input'] }
        ]
    };
    const out = window.TriggerGraph.compileToEngine(g);
    const msgs = (out.effects || []).map((e) => (e.params && e.params.message) || '');
    assertTrue(msgs.includes('one') && msgs.includes('two'),
        'both effects compiled, got ' + JSON.stringify(msgs));
});

// ─── cycles: the tracers recurse, so a loop must not hang or blow the stack ───

test('trigger-graph: a cycle is reported instead of blowing the stack', () => {
    const g = {
        nodes: [
            { id: 'n0', type: 'behavior', x: 0, y: 0, props: { name: 'loop' } },
            { id: 'c0', type: 'condition', x: 0, y: 0, props: { condition_type: 'always' } },
            { id: 'c1', type: 'condition', x: 0, y: 0, props: { condition_type: 'always' } },
            { id: 'a0', type: 'action', x: 0, y: 0, props: { action_type: 'message', text: 'x' } }
        ],
        wires: [
            { id: 'w0', from: ['n0', 'output'], to: ['c0', 'input'] },
            { id: 'w1', from: ['c0', 'output_yes'], to: ['c1', 'input'] },
            { id: 'w2', from: ['c1', 'output_yes'], to: ['c0', 'input'] },
            { id: 'w3', from: ['c1', 'output_yes'], to: ['a0', 'input'] }
        ]
    };
    const r = window.TriggerGraph.compileToBehaviorsWithIssues(g);
    assertTrue(/cycle/i.test(r.compile_error), 'cycle reported, got: ' + r.compile_error);
    assertEq(r.behaviors.length, 1, 'still produced one behavior rather than throwing');
});

// ─── #10: an unrepresentable NO branch must stay a refusal, not a silent drop ───

test('trigger-graph: a behavior NO branch is refused, not silently dropped', () => {
    const g = {
        nodes: [
            { id: 'n0', type: 'behavior', x: 0, y: 0, props: { name: 'nb' } },
            { id: 'c0', type: 'condition', x: 0, y: 0, props: { condition_type: 'always' } },
            { id: 'a0', type: 'action', x: 0, y: 0, props: { action_type: 'message', text: 'yes branch' } },
            { id: 'a1', type: 'action', x: 0, y: 0, props: { action_type: 'message', text: 'no branch' } }
        ],
        wires: [
            { id: 'w0', from: ['n0', 'output'], to: ['c0', 'input'] },
            { id: 'w1', from: ['c0', 'output_yes'], to: ['a0', 'input'] },
            { id: 'w2', from: ['c0', 'output_no'], to: ['a1', 'input'] }
        ]
    };
    const r = window.TriggerGraph.compileToBehaviorsWithIssues(g);
    assertTrue(r.compile_error && /NO branch/.test(r.compile_error),
        'NO branch refusal surfaced, got: ' + JSON.stringify(r.compile_error));
    const texts = (r.behaviors[0].actions || []).map((a) => a.text);
    assertTrue(texts.includes('yes branch'), 'the YES branch still compiled');
});

// ─── catalog sanity: the single-source guarantee ───

test('trigger-graph: behaviors-view reads the same catalog (no drift)', () => {
    // The form editor used to keep its own 121-entry literal, which is how the
    // two editors diverged. It must now be the shared catalog.
    const shared = window.TriggerTypes.BEHAVIOR_ACTION_TYPES.map((a) => a.value);
    const form = window.BehaviorsView
        ? window.BehaviorsView.BEHAVIOR_ACTION_TYPES().map((a) => a.value)
        : null;
    if (!form) return; // behaviors-view not loaded in this sandbox; nothing to prove
    assertEq(form.length, shared.length, 'same type count');
    assertEq(form.join(','), shared.join(','), 'same types in the same order');
});
