const { chromium } = require('playwright');
(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto('http://127.0.0.1:4444', { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => typeof TriggerGraph !== 'undefined', null, { timeout: 20000 });
    await page.waitForTimeout(1200);
    const out = await page.evaluate(() => {
        const g = { nodes: [
            { id: 't0', type: 'trigger', x: 0, y: 0, props: { trigger_type: ['on_open', 'on_state_enter'], target_state: 'lit' } },
            { id: 'c0', type: 'condition', x: 300, y: 0, props: { condition_type: 'eq', target: 'npc_state', value: 'fleeing' } },
            { id: 'e0', type: 'effect', x: 600, y: 0, props: { effect_type: 'save', save_mode: 'skill', save_skill: 'Athletics', save_dc: 13, succ_type: 'message', succ_msg: 'You resist!', fail_type: 'apply_condition', fail_cond: 'frightened', fail_dur: 4, fail_src: 'the door', fail_src_type: 'way' } },
            { id: 'e1', type: 'effect', x: 900, y: 0, props: { effect_type: 'schedule_trigger', delay_ticks: 5, target: 'cursed_ring' } },
            { id: 'e2', type: 'effect', x: 1200, y: 0, props: { effect_type: 'llm_respond', instructions: 'Be a mirror.', fallback_message: 'Silent.', max_words: 25, cooldown: '', name: '' } },
            { id: 'e3', type: 'effect', x: 1500, y: 0, props: { effect_type: 'spawn_item', item_id: 'torch', display_name: 'Lit Torch', into: 'container', capture: 'speech' } },
            { id: 'e4', type: 'effect', x: 1800, y: 0, props: { effect_type: 'damage', amount: 7, target: 'other' } },
            { id: 'e5', type: 'effect', x: 2100, y: 0, props: { effect_type: 'apply_condition', condition: 'poisoned', target_by: 'tag', target_value: 'fleshy', duration: 6, source: 'wine', symptoms: '{"8":"queasy"}', extra_conditions: '[{"condition":"blind","duration":3}]' } },
            { id: 'e6', type: 'effect', x: 2400, y: 0, props: { effect_type: 'message', message: 'done', success_message: '', fail_message: 'nope' } },
        ], wires: [
            { id: 'w0', from: ['t0', 'output'], to: ['c0', 'input'] },
            { id: 'w1', from: ['c0', 'output_yes'], to: ['e0', 'input'] },
            { id: 'w2', from: ['e0', 'output'], to: ['e1', 'input'] },
            { id: 'w3', from: ['e1', 'output'], to: ['e2', 'input'] },
            { id: 'w4', from: ['e2', 'output'], to: ['e3', 'input'] },
            { id: 'w5', from: ['e3', 'output'], to: ['e4', 'input'] },
            { id: 'w6', from: ['e4', 'output'], to: ['e5', 'input'] },
            { id: 'w7', from: ['e5', 'output'], to: ['e6', 'input'] },
        ] };
        const c = TriggerGraph.compileToEngine(g);
        // behavior-mode: emotion condition round-trip
        const bg = TriggerGraph.behaviorsToGraph([{ trigger: 'on_tick', interval: 2, priority: 2, conditions: { type: 'npc_emotion_is', emotion: 'angry', operator: 'gte', value: 0.5 }, actions: [{ type: 'attack', target: 'player' }] }]);
        const bc = TriggerGraph.compileToBehaviors(bg);
        return { c, bc };
    });
    console.log(JSON.stringify(out, null, 1));
    const c = out.c;
    const e = c.effects;
    const checks = {
        multiType: JSON.stringify(c.trigger_type) === JSON.stringify(['on_open', 'on_state_enter']),
        targetState: c.target_state === 'lit',
        saveGate: e[0].type === 'save' && e[0].params.skill === 'Athletics' && e[0].params.dc === 13
            && e[0].params.on_success[0].params.message === 'You resist!'
            && e[0].params.on_fail[0].params.condition === 'frightened' && e[0].params.on_fail[0].params.duration === 4
            && e[0].params.on_fail[0].params.source_type === 'way',
        schedule: e[1].type === 'schedule_trigger' && e[1].params.delay_ticks === 5 && e[1].params.target === 'cursed_ring',
        llm: e[2].type === 'llm_respond' && e[2].params.max_words === 25 && !('cooldown' in e[2].params) && !('name' in e[2].params),
        spawnItem: e[3].params.display_name === 'Lit Torch' && e[3].params.into === 'container' && e[3].params.capture === 'speech' && !('name' in e[3].params),
        damageOther: e[4].params.target === 'other' && e[4].params.amount === 7,
        condNormalize: e[5].params.target_by === 'tag' && e[5].params.target_value === 'fleshy' && !('target' in e[5].params)
            && e[5].params.symptoms && e[5].params.symptoms['8'] === 'queasy'
            && Array.isArray(e[5].params.extra_conditions) && e[5].params.extra_conditions[0].condition === 'blind',
        emptyDropped: !('success_message' in e[6].params),
        behaviorEmotion: out.bc[0].conditions && out.bc[0].conditions.emotion === 'angry' && out.bc[0].conditions.operator === 'gte',
    };
    let fail = 0;
    for (const [k, v] of Object.entries(checks)) { console.log((v ? 'PASS ' : 'FAIL ') + k); if (!v) fail++; }
    console.log('page errors:', errors.length ? errors.join(' | ') : 'none');
    console.log(fail === 0 && errors.length === 0 ? 'RESULT: PASS' : 'RESULT: FAIL');
    await browser.close();
    process.exit(fail === 0 && errors.length === 0 ? 0 : 1);
})();
