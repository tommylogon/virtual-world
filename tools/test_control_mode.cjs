const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push('[pageerror] ' + e.message));

    await page.goto('http://127.0.0.1:4444', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2500);

    const name = await page.evaluate(() => worldState.data?.active_player);
    if (!name) { console.log('FAIL no active player'); await browser.close(); process.exit(1); }
    console.log('Active player: ' + name);

    const seq = await page.evaluate(async (n) => {
        const order = ['human', 'llm', 'npc'];
        const out = [];
        const before = events.getControlMode(n);
        out.push('before=' + before + ' autonomy=' + worldState.players[n].autonomy + ' simple_npc=' + worldState.players[n].simple_npc);
        for (let i = 0; i < 3; i++) {
            if (!events.cycleControlMode) return out.concat('NO cycleControlMode');
            events.cycleControlMode(n);
            // allow update + fetch + render to settle
            await new Promise(r => setTimeout(r, 800));
            const mode = events.getControlMode(n);
            const p = worldState.players[n];
            out.push(`step${i + 1}: mode=${mode} autonomy=${p ? p.autonomy : 'missing'} simple_npc=${p ? p.simple_npc : 'missing'}`);
        }
        return out;
    }, name);
    seq.forEach(l => console.log(l));

    // Badge on the inspector should now reflect a fresh mode.
    // The cycle must advance every click: llm → npc → human → llm
    const stepModes = seq.slice(1).map(l => /mode=([a-z]+)/.exec(l)?.[1]);
    const expected = ['npc', 'human', 'llm'];
    const advanced = stepModes.length === 3 && stepModes.every((m, i) => m === expected[i]);
    console.log('Cycle advanced correctly: ' + advanced);
    const allOk = advanced && errors.length === 0;
    console.log('\nJS page errors: ' + (errors.length ? errors.join(' | ') : 'none'));
    console.log(allOk && errors.length === 0 ? 'RESULT: PASS' : 'RESULT: FAIL');
    await browser.close();
    process.exit(allOk && errors.length === 0 ? 0 : 1);
})();