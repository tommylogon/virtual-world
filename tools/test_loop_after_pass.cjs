const { chromium } = require('playwright');

(async () => {
    const BASE = 'http://127.0.0.1:4444';
    const http = (method, path, body) => fetch(BASE + path, {
        method,
        headers: body ? { 'Content-Type': 'application/json' } : {},
        body: body ? JSON.stringify(body) : undefined
    }).then(r => r.json());

    const backup = await http('GET', '/api/save');
    console.log('Backed up live world.');

    const probe = {
        areas: { tavern: { name: 'tavern', description: 'quiet', players: ['Jake', 'Violet'] } },
        items: {}, ways: {}, connections: {},
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
        await page.waitForTimeout(2000);

        // Start the non-turn run loop on Jake (human).
        await page.evaluate(() => {
            events._characterAutonomy['Jake'] = false;
            config.controllingPlayer = 'Jake';
            config.turnBased = false;
            config.running = false;
            config.busy = false;
            agent.start(); // async; loop begins
        });

        // Human composer should pop; skip it.
        await page.waitForSelector('#htc-overlay', { state: 'visible', timeout: 8000 });
        console.log('composer visible (Jake turn)');
        await page.click('#htc-end');
        await page.waitForSelector('#htc-overlay', { state: 'hidden', timeout: 8000 });
        console.log('skipped Jake turn');

        // Let the loop run a few iterations.
        for (let i = 0; i < 6; i++) await page.waitForTimeout(1500);

        const state1 = await page.evaluate(() => ({
            running: config.running, busy: config.busy,
            controlling: config.controllingPlayer,
            tick: worldState.data?.game_time?.tick
        }));
        console.log('After ~6s of loop: ' + JSON.stringify(state1));

        // Now press the real Step button (⏭) like the user did.
        await page.click('#sim-step');
        await page.waitForTimeout(2000);
        const state2 = await page.evaluate(() => ({
            running: config.running, busy: config.busy,
            controlling: config.controllingPlayer,
            lastLog: Array.from(document.querySelectorAll('#event-log-lines .event-line')).slice(-2).map(e => e.textContent)
        }));
        console.log('After Step click: running=' + state2.running + ' busy=' + state2.busy + ' controlling=' + state2.controlling);
        console.log('Last log lines:');
        (state2.lastLog || []).forEach(l => console.log('  ' + l));

        // If still running, press Pause (the same button toggles) to test the toggle works.
        if (state2.running) {
            await page.evaluate(() => { agent.stop(); });
            await page.waitForTimeout(500);
            const state3 = await page.evaluate(() => ({ running: config.running, busy: config.busy }));
            console.log('After explicit stop(): ' + JSON.stringify(state3));
        }

        console.log('\nJS page errors: ' + (errors.length ? errors.join(' | ') : 'none'));
        console.log('RESULT: probe complete');
    } finally {
        await http('POST', '/api/load', backup).catch(e => console.log('restore failed: ' + e.message));
        await browser.close();
        console.log('Live world restored.');
    }
    process.exit(0);
})();