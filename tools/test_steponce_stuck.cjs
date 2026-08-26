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
        areas: { tavern: { name: 'tavern', description: 'quiet tavern', players: ['Jake', 'Violet'] } },
        items: {}, ways: {}, connections: {},
        players: {
            Jake: { name: 'Jake', current_area: 'tavern', state: 'awake', autonomy: false, simple_npc: false, personality: 'shy', vitals: {}, stats: {} },
            Violet: { name: 'Violet', current_area: 'tavern', state: 'awake', autonomy: true, simple_npc: true, npc_behavior: 'wander', npc_action_interval: 1, personality: '', vitals: {}, stats: {} }
        },
        game_time: { tick: 0, display: '08:00' },
        active_player: 'Jake',
        _scenario_name: 'probe_steponce'
    };

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push('[pageerror] ' + e.message));
    page.on('console', m => { const t = m.text(); if (t && /error|reject|throw/i.test(t)) errors.push('[console] ' + t); });

    try {
        await http('POST', '/api/load', probe);
        await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 });
        await page.waitForTimeout(2000);

        // Select Jake (human) as controlling player, then click the REAL Step-Once button.
        await page.evaluate(() => { events._characterAutonomy['Jake'] = false; config.controllingPlayer = 'Jake'; });
        await page.click('#sim-step');
        console.log('Step-Once clicked');

        await page.waitForSelector('#htc-overlay', { state: 'visible', timeout: 8000 });
        console.log('composer visible');
        // Clicking inputs must NOT close the modal (regression: modal is child of
        // overlay, whose click handler used to end the turn).
        for (const sel of ['#htc-action', '#htc-item', '#htc-target', '#htc-speech', '#htc-emote']) {
            await page.click(sel);
            const stillOpen = await page.evaluate(() => getComputedStyle(document.getElementById('htc-overlay')).display === 'flex');
            console.log(`click ${sel} → modal still open: ${stillOpen}`);
            if (!stillOpen) { console.log('FAIL: input click closed modal'); await browser.close(); process.exit(1); }
        }
        await page.fill('#htc-action', 'wait');
        await page.click('#htc-submit');
        await page.waitForSelector('#htc-overlay', { state: 'hidden', timeout: 8000 });
        console.log('action submitted, modal hidden');

        // Let any async work settle.
        for (let i = 0; i < 6; i++) await page.waitForTimeout(1000);

        const s1 = await page.evaluate(() => ({
            busy: config.busy, running: config.running,
            controlling: config.controllingPlayer,
            status: document.getElementById('status') ? document.getElementById('status').textContent : 'n/a'
        }));
        console.log('State after submit: ' + JSON.stringify(s1));

        // Now try a SECOND Step-Once, exactly like the user does.
        await page.click('#sim-step');
        await page.waitForTimeout(2000);
        const s2 = await page.evaluate(() => ({
            busy: config.busy, running: config.running,
            controlling: config.controllingPlayer,
            composer: (document.getElementById('htc-overlay')) ? getComputedStyle(document.getElementById('htc-overlay')).display : 'no-node',
            status: document.getElementById('status') ? document.getElementById('status').textContent : 'n/a'
        }));
        console.log('After 2nd Step: ' + JSON.stringify(s2));

        console.log('\nJS page errors: ' + (errors.length ? errors.join(' | ') : 'none'));
        console.log('RESULT: probe complete');
    } finally {
        await http('POST', '/api/load', backup).catch(e => console.log('restore failed: ' + e.message));
        await browser.close();
        console.log('Live world restored.');
    }
    process.exit(0);
})();