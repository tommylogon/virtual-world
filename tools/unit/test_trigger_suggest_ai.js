/**
 * test_trigger_suggest_ai.js — Unit tests for the shared trigger-AI prompt (task-396).
 *
 * The LLM's *output* cannot be unit-tested, but the prompt's contract can: the hard
 * rules must be stated, and every WORKED EXAMPLE embedded in the prompt must itself
 * obey them. A rule-violating example is the real regression risk — the model
 * pattern-matches to the examples, not to the prose rules.
 */
'use strict';

const SYS_ITEM = TriggerSuggestAI.buildSystem('item');

/** Every line of the prompt that is a worked example (one JSON trigger per line). */
function examplesOf(kind) {
    return TriggerSuggestAI.buildSystem(kind)
        .split('\n')
        .map(l => l.trim())
        .filter(l => l.startsWith('{"trigger_type":'))
        .map(l => JSON.parse(l));
}

// ── the hard rules are stated ──

test('buildSystem states the mandatory non-empty effects rule', () => {
    assertTrue(/EVERY trigger MUST have a non-empty "effects"/.test(SYS_ITEM), 'effects rule present');
    assertTrue(/effects: \[\] fires and does NOTHING/.test(SYS_ITEM), 'empty-effects consequence stated');
});

test('buildSystem sends prose into params.message, not the top-level field', () => {
    assertTrue(/params\.message/.test(SYS_ITEM), 'params.message named');
    assertTrue(/Leave the trigger's top-level/.test(SYS_ITEM), 'top-level success/fail rule present');
});

test('buildSystem forbids pairing on_light with on_toggle_on', () => {
    assertTrue(/DO NOT use on_light \+ on_toggle_on/.test(SYS_ITEM), 'on_light pairing rule present');
});

test('buildSystem forbids pairing on_use with on_eat/on_drink', () => {
    assertTrue(/NEVER use BOTH "on_use" and "on_eat"\/"on_drink"/.test(SYS_ITEM), 'consume rule present');
});

test('buildSystem states heat sources are properties, not triggers', () => {
    assertTrue(/target_temperature & heating_rate are item PROPERTIES, NOT triggers/.test(SYS_ITEM),
        'heat-source rule present');
});

// ── the embedded examples obey the rules ──

test('every embedded worked example has at least one effect', () => {
    const examples = examplesOf('item');
    assertTrue(examples.length >= 3, `expected >=3 worked examples, got ${examples.length}`);
    examples.forEach((t, i) => {
        assertTrue(Array.isArray(t.effects) && t.effects.length > 0,
            `example ${i} (${t.trigger_type}) must have >=1 effect`);
    });
});

test('no worked example pairs on_light with on_toggle_on', () => {
    const types = examplesOf('item').map(t => t.trigger_type);
    assertFalse(types.includes('on_light') && types.includes('on_toggle_on'),
        'examples must not show both on_light and on_toggle_on');
});

test('no worked example pairs on_use with on_eat/on_drink', () => {
    const types = examplesOf('item').map(t => t.trigger_type);
    assertFalse(types.includes('on_use') && (types.includes('on_eat') || types.includes('on_drink')),
        'examples must not mix on_use with a consume type');
});

test('worked examples keep top-level success_message honest', () => {
    examplesOf('item').forEach((t, i) => {
        assertEq(typeof t.success_message, 'string', `example ${i} success_message is a string`);
        if (t.trigger_type !== 'on_eat' && t.trigger_type !== 'on_drink') {
            assertEq(t.success_message, '', `example ${i} (${t.trigger_type}) success_message should be ""`);
        }
    });
});

test('every effect in the examples has a documented type and a params object', () => {
    const documented = new Set([
        'message', 'adjust_vital', 'heal', 'damage', 'save', 'set_state', 'set_environment',
        'unlock_way', 'spawn_item', 'give_item', 'remove_item', 'consume_item', 'destroy_self',
        'add_tag', 'remove_tag', 'set_parameter', 'adjust_parameter', 'schedule_trigger',
        'surface_memory', 'teleport', 'set_time', 'set_weather', 'apply_condition',
        'remove_condition', 'apply_trait', 'remove_trait', 'drain', 'adjust_uses',
    ]);
    examplesOf('item').forEach((t, i) => {
        t.effects.forEach((e, j) => {
            assertTrue(typeof e.type === 'string' && e.type.length > 0, `example ${i} effect ${j} has a type`);
            assertTrue(documented.has(e.type),
                `example ${i} effect ${j} type '${e.type}' is in the documented effect list`);
            assertTrue(e.params && typeof e.params === 'object', `example ${i} effect ${j} has params`);
        });
    });
});

test('nested save branches in the examples are non-empty effect arrays', () => {
    examplesOf('item').forEach((t, i) => {
        t.effects.forEach((e) => {
            if (e.type !== 'save') return;
            assertTrue(Array.isArray(e.params.on_fail) && e.params.on_fail.length > 0,
                `example ${i} save.on_fail must be a non-empty effect array`);
            e.params.on_fail.forEach((branch, j) => {
                assertTrue(branch && typeof branch.type === 'string',
                    `example ${i} save.on_fail[${j}] is an effect object`);
            });
        });
    });
});

// ── kind-specific guidance ──

test('buildSystem carries way guidance and its prohibitions', () => {
    const way = TriggerSuggestAI.buildSystem('way');
    assertTrue(/This is a WAY/.test(way), 'way guidance present');
    assertTrue(/Do NOT use adjust_vital or spawn_item on a way/.test(way), 'way prohibition present');
});

test('buildSystem carries area guidance and the ambience gate', () => {
    const area = TriggerSuggestAI.buildSystem('area');
    assertTrue(/This is an AREA/.test(area), 'area guidance present');
    assertTrue(/random_chance/.test(area), 'area ambience gating mentioned');
});

test('the item prompt has no way/area preamble', () => {
    assertFalse(/This is a WAY|This is an AREA/.test(SYS_ITEM), 'item prompt has no way/area line');
});

// ── the user prompt ──

test('buildPrompt echoes a required plan verbatim, in order', () => {
    const fields = { name: 'Candlestick', description: 'a brass candlestick', tags: ['light_source'], uses: -1 };
    const withPlan = TriggerSuggestAI.buildPrompt(fields, 'item', ['on_take', 'on_toggle_on']);
    assertTrue(withPlan.includes('EXACTLY these trigger types, in this order'), 'plan instruction present');
    assertTrue(withPlan.includes('on_take, on_toggle_on'), 'plan list rendered in order');
});

test('buildPrompt falls back to a generic instruction without a plan', () => {
    const fields = { name: 'Candlestick', description: 'a brass candlestick', tags: ['light_source'] };
    const noPlan = TriggerSuggestAI.buildPrompt(fields, 'item');
    assertTrue(noPlan.includes('Generate a full set of useful triggers for this item'), 'fallback present');
    assertFalse(noPlan.includes('EXACTLY these trigger types'), 'no plan instruction without a plan');
    assertFalse(TriggerSuggestAI.buildPrompt(fields, 'item', []).includes('EXACTLY these trigger types'),
        'empty plan array is treated as no plan');
});

test('buildPrompt includes node context and renders infinite uses', () => {
    const p = TriggerSuggestAI.buildPrompt(
        { name: 'Locket', description: 'a silver locket', tags: ['jewelry'], actions: ['examine'], uses: -1 },
        'item');
    assertTrue(p.includes('Node kind: item'), 'kind included');
    assertTrue(p.includes('Name: Locket'), 'name included');
    assertTrue(p.includes('Tags: jewelry'), 'tags included');
    assertTrue(p.includes('Uses: infinite'), 'uses of -1 renders as infinite');
});
