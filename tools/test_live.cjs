const { chromium } = require('playwright');
(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1400, height: 900 });
    let passed = 0, failed = 0;

    async function check(label, fn) {
        try { await fn(); passed++; console.log('  OK ' + label); }
        catch (err) { failed++; console.log('  FAIL ' + label + ': ' + err.message); }
    }

    async function api(body) {
        return await page.evaluate(async (b) => {
            const r = await fetch('/api/action', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(b) });
            return await r.json();
        }, body);
    }
    async function getState() {
        return await page.evaluate(async () => {
            const r = await fetch('/api/state'); return await r.json();
        });
    }

    await page.goto('http://127.0.0.1:4444', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    console.log('\n=== LIVE TESTS ===\n');

    // Movement
    console.log('--- Movement ---');
    await check('look', async () => {
        const r = await api({command:'look'}); if (r.error && !r.output) throw r.error;
    });
    await check('go north', async () => {
        const r = await api({command:'go north'});
        if (r.error && !r.output && !r.error.includes('cant go')) throw r.error;
    });
    await check('go south (back)', async () => {
        const r = await api({command:'go south'});
        if (r.error && !r.output && !r.error.includes('cant go')) throw r.error;
    });

    // Character
    console.log('\n--- Character ---');
    await check('click agent in list', async () => {
        const agentList = await page.$('#agent-list');
        if (agentList) {
            const items = await agentList.$$('[class*="agent"]');
            if (items.length > 0) { await items[0].click(); await page.waitForTimeout(500); }
        }
        // Also try graph click
        const canvas = await page.$('#graph-container canvas');
        if (canvas) await canvas.click({position:{x:300,y:200}});
        await page.waitForTimeout(500);
    });

    // Items
    console.log('\n--- Items ---');
    await check('examine self', async () => {
        const r = await api({command:'examine self'});
        if (r.error) throw r.error;
    });
    await check('inventory', async () => {
        const r = await api({command:'inventory'});
        if (r.error && !r.output) throw r.error;
    });
    await check('stats', async () => {
        const r = await api({command:'stats'});
        if (r.error) throw r.error;
    });

    // State
    console.log('\n--- State ---');
    await check('state endpoint', async () => {
        const s = await getState();
        if (!s || !s.rooms) throw new Error('No rooms in state');
        console.log('  (' + Object.keys(s.rooms).length + ' rooms, active: ' + s.active_player + ')');
    });

    // Results
    console.log('\n=== ' + passed + ' passed, ' + failed + ' failed ===');
    console.log('Browser stays open. Close it when done exploring.\n');
})();
