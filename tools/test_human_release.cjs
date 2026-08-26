const { chromium } = require('playwright');

(async () => {
    const BASE = 'http://127.0.0.1:4444';
    const http = (method, path, body) => fetch(BASE + path, {
        method,
        headers: body ? { 'Content-Type': 'application/json' } : {},
        body: body ? JSON.stringify(body) : undefined
    }).then(r => r.json());

    // Back up the live world so it can be restored.
    const backup = await http('GET', '/api/save');
    console.log('Backed up live world. players=' + Object.keys(backup.players || {}).length);

    // Probe world: two players in one room, Jake = human, Violet = simple NPC.
    const probe = {
        areas: {
            tavern: { name: 'tavern', description: 'A small quiet tavern.', players: ['Jake', 'Violet'] }
        },
        items: {},
        ways: {},
        connections: {},
        players: {
            Jake: { name: 'Jake', current_area: 'tavern', state: 'awake', autonomy: false, simple_npc: false, personality: '', vitals: {}, stats: {} },
            Violet: { name: 'Violet', current_area: 'tavern', state: 'awake', autonomy: true, simple_npc: true, npc_behavior: 'wander', npc_action_interval: 1, personality: '', vitals: {}, stats: {} }
        },
        game_time: { tick: 0, display: '08:00' },
        active_player: 'Jake',
        _scenario_name: 'probe_release'
    };

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push('[pageerror] ' + e.message));

    try {
        await http('POST', '/api/load', probe);
        await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 });
        await page.waitForTimeout(2500);

        const kicked = await page.evaluate(async () => {
            // Prime behavior state: non-turn mode, Jake selected + autonomous=false.
            events._characterAutonomy['Jake'] = false;
            config.controllingPlayer = 'Jake';
            config.turnBased = false;
            config.running = false;
            config.busy = false;
            // Fire a single human step (the start() loop would do this); it will
            // pause on the composer and set controllingPlayer when resolved.
            window.__stepPromise = agent.step().then(() => 'resolved');
            return true;
        });
        console.log('step kicked: ' + kicked);

        await page.waitForSelector('#htc-overlay', { state: 'visible', timeout: 6000 });
        console.log('composer up for Jake');

        // Skip the turn (End Turn) — the run must release to the next character.
        await page.click('#htc-end');
        await page.waitForSelector('#htc-overlay', { state: 'hidden', timeout: 6000 });

        // Wait for the human step to finish, then inspect rotation.
        for (let i = 0; i < 10; i++) await page.waitForTimeout(300);
        const result = await page.evaluate(() => ({
            stepState: (window.__stepPromise || Promise.resolve('missing')).then(r => r),
            controllingPlayer: config.controllingPlayer,
            modeViolet: VW.events.getControlMode('Violet')
        }));
        const controlled = result.controllingPlayer;
        console.log('step resolved: ' + result.stepState);
        console.log('controllingPlayer after skip: ' + controlled);
        console.log('Violet control mode: ' + result.modeViolet);

        const pass = controlled === 'Violet' && errors.length === 0;
        console.log('\nJS page errors: ' + (errors.length ? errors.join(' | ') : 'none'));
        console.log(pass ? 'RESULT: PASS' : 'RESULT: FAIL');
    } finally {
        // Restore the live world exactly as we found it.
        await http('POST', '/api/load', backup).catch(e => console.log('restore failed: ' + e.message));
        await browser.close();
        console.log('Live world restored.');
    }
    process.exit(0);
})();