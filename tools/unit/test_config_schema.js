// Tests for CONFIG_SCHEMA coercion, persistence, and pub/sub in static/js/config.ts.

function createIsolatedConfigInstance() {
    const prevConfig = window.config;
    const prevSchema = window.CONFIG_SCHEMA;
    const src = __readFile('static/js/config.js');
    new Function(src)();
    const inst = window.config;
    const schema = window.CONFIG_SCHEMA;
    window.config = prevConfig;
    window.CONFIG_SCHEMA = prevSchema;
    return { inst, schema };
}

test('CONFIG_SCHEMA: coerce preserves 0 and false and defaults blank or NaN', async () => {
    const { inst, schema } = createIsolatedConfigInstance();
    await inst._initPromise;

    assertTrue(Boolean(schema && schema.maxTokens), 'maxTokens exists in CONFIG_SCHEMA');
    assertEq(inst.coerce('maxTokens', 0), 0, 'numeric 0 preserved for maxTokens');
    assertEq(inst.coerce('maxTokens', '0'), 0, 'string "0" preserved for maxTokens');
    assertEq(inst.coerce('maxTokens', ''), 0, 'blank string defaults to 0 (Auto) for maxTokens');
    assertEq(inst.coerce('maxTokens', 'not-a-number'), 0, 'NaN defaults to 0 for maxTokens');
    assertEq(inst.coerce('maxTokens', -50), 0, 'negative clamped to min 0 for maxTokens');
    assertEq(inst.coerce('maxTokens', '4096'), 4096, 'positive integer parsed');

    assertEq(inst.coerce('softMaxTokens', ''), 512, 'blank string defaults to 512 for softMaxTokens');
    assertEq(inst.coerce('softMaxTokens', 0), 0, 'explicit 0 preserved for softMaxTokens');
    assertEq(inst.coerce('softMaxTokens', -10), 0, 'negative clamped to 0 for softMaxTokens');

    assertEq(inst.coerce('reasoningMaxTokens', ''), 0, 'blank string defaults to 0 (Auto) for reasoningMaxTokens');
    assertEq(inst.coerce('reasoningMaxTokens', 0), 0, 'explicit 0 preserved for reasoningMaxTokens');
    assertEq(inst.coerce('reasoningMaxTokens', -100), 0, 'negative clamped to 0 for reasoningMaxTokens');
    assertEq(inst.coerce('reasoningMaxTokens', '4096'), 4096, 'positive integer parsed for reasoningMaxTokens');

    assertEq(inst.coerce('graphGravitationalConstant', -40), -40, 'negative repulsion preserved');
    assertEq(inst.coerce('graphRepelPull', 0), 0, '0 pull preserved');
    assertEq(inst.coerce('graphRepelPull', ''), 0.12, 'empty pull defaults to 0.12');

    assertEq(inst.coerce('reactiveMode', false), false, 'boolean false preserved for true-default field');
    assertEq(inst.coerce('reactiveMode', 'false'), false, 'string "false" preserved for true-default field');
    assertEq(inst.coerce('reactiveMode', null), true, 'null defaults to true for reactiveMode');
    assertEq(inst.coerce('showLogs', null), false, 'null defaults to false for showLogs');
    assertEq(inst.coerce('showLogs', 'true'), true, 'string "true" coerced to true');
});

test('ConfigManager: set and applyPatch emit change events only on actual value change', async () => {
    const { inst } = createIsolatedConfigInstance();
    await inst._initPromise;

    const eventsReceived = [];
    const unsub = inst.on('change', (payload) => {
        eventsReceived.push(payload);
    });

    // Setting to current default (0) should not emit
    inst.set('maxTokens', '0');
    assertEq(eventsReceived.length, 0, 'no change event when value is unchanged');

    // Setting to 4096 emits once
    inst.set('maxTokens', '4096');
    assertEq(inst.maxTokens, 4096, 'maxTokens updated to 4096');
    assertEq(eventsReceived.length, 1, 'change event emitted on update');
    assertEq(eventsReceived[0].keys, ['maxTokens'], 'changed key reported');
    assertEq(eventsReceived[0].changed.maxTokens, 4096, 'new value reported');
    assertEq(eventsReceived[0].prev.maxTokens, 0, 'previous value reported');

    // applyPatch with multiple fields (one unchanged, two changed)
    const changedKeys = inst.applyPatch({
        maxTokens: 4096,
        softMaxTokens: '1024',
        reactiveMode: 'false',
    });
    assertEq(changedKeys, ['softMaxTokens', 'reactiveMode'], 'only changed keys returned');
    assertEq(inst.softMaxTokens, 1024, 'softMaxTokens coerced to number');
    assertEq(inst.reactiveMode, false, 'reactiveMode coerced to boolean false');
    assertEq(eventsReceived.length, 2, 'single batched change event emitted for applyPatch');

    unsub();
    inst.set('maxTokens', 2048);
    assertEq(eventsReceived.length, 2, 'unsubscribed listener no longer receives events');
});

test('ConfigManager: _persistStorage and _loadFromStorage round-trip all schema keys cleanly', async () => {
    storage._map.clear();
    const { inst } = createIsolatedConfigInstance();
    await inst._initPromise;

    inst.applyPatch({
        maxTokens: 0,
        softMaxTokens: 768,
        reactiveMode: false,
        memoryModelEnabled: false,
        filterThoughts: false,
        graphGravitationalConstant: -24,
        graphRepelPull: 0,
    });
    await inst.save(true);

    const { inst: reloaded } = createIsolatedConfigInstance();
    await reloaded._initPromise;

    assertEq(reloaded.maxTokens, 0, 'maxTokens 0 round-tripped');
    assertEq(reloaded.softMaxTokens, 768, 'softMaxTokens 768 round-tripped');
    assertEq(reloaded.reactiveMode, false, 'reactiveMode false round-tripped');
    assertEq(reloaded.memoryModelEnabled, false, 'memoryModelEnabled false round-tripped');
    assertEq(reloaded.filterThoughts, false, 'filterThoughts false round-tripped');
    assertEq(reloaded.graphGravitationalConstant, -24, 'negative integer round-tripped');
    assertEq(reloaded.graphRepelPull, 0, '0 float round-tripped');
    storage._map.clear();
});
