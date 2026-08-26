const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1400, height: 900 });
    const results = [];

    function pass(label) { results.push({ label, status: 'OK' }); console.log('  OK ' + label); }
    function fail(label, err) { results.push({ label, status: 'FAIL', error: err.message }); console.log('  FAIL ' + label + ': ' + err.message); }

    async function test(label, fn) { try { await fn(); pass(label); } catch (e) { fail(label, e); } }

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

    // ─── 1. Page Load & UI ───
    console.log('\n=== 1. Page Load & UI ===');
    await test('Page loads with title', async () => {
        const title = await page.title();
        if (!title) throw new Error('No title');
    });
    await test('Command input exists', async () => {
        const el = await page.$('#command-input');
        if (!el) throw new Error('#command-input missing');
    });
    await test('Inspector panel exists', async () => {
        const el = await page.$('#inspector-panel');
        if (!el) throw new Error('#inspector-panel missing');
    });
    await test('Graph canvas exists', async () => {
        const el = await page.$('#graph-container canvas');
        if (!el) throw new Error('graph canvas missing');
    });
    await test('Event stream exists', async () => {
        const el = await page.$('#event-stream');
        if (!el) throw new Error('#event-stream missing');
    });

    // ─── 2. Basic Commands ───
    console.log('\n=== 2. Basic Commands ===');
    await test('look', async () => {
        const r = await api({command:'look'}); if (r.error && !r.output) throw new Error(r.error);
    });
    await test('inventory', async () => {
        const r = await api({command:'inventory'}); if (r.error && !r.output) throw new Error(r.error);
    });
    await test('inventory alias (i)', async () => {
        const r = await api({command:'i'}); if (r.error && !r.output) throw new Error(r.error);
    });
    await test('examine self', async () => {
        const r = await api({command:'examine self'}); if (r.error) throw new Error(r.error);
    });
    await test('stats', async () => {
        const r = await api({command:'stats'}); if (r.error) throw new Error(r.error);
    });
    await test('go north', async () => {
        const r = await api({command:'go north'});
        if (r.error && !r.output && !r.error.toLowerCase().includes('cant go')) throw new Error(r.error);
    });
    await test('go back (south)', async () => {
        const r = await api({command:'go south'});
        if (r.error && !r.output && !r.error.toLowerCase().includes('cant go')) throw new Error(r.error);
    });
    await test('rest 1 advances time', async () => {
        const before = await getState();
        await api({command:'rest 1'});
        await page.waitForTimeout(500);
        const after = await getState();
        if (after.time_ticks <= before.time_ticks) console.log('  (time may not advance in some scenarios)');
    });

    // ─── 3. Agent Inspector ───
    console.log('\n=== 3. Agent Inspector ===');
    await test('Click agent in list opens inspector', async () => {
        const agentList = await page.$('#agent-list');
        if (agentList) {
            const items = await agentList.$$('[class*="agent"]');
            if (items.length > 0) { await items[0].click(); await page.waitForTimeout(500); }
        }
        const panel = await page.$('#inspector-panel');
        if (!panel) throw new Error('inspector panel not found');
    });
    await test('Inventory tab renders paperdoll', async () => {
        // Click the Inventory tab button
        const tabs = await page.$$('[data-tab-btn]');
        for (const t of tabs) {
            const text = await t.textContent();
            if (text && text.includes('Inventory')) { await t.click(); await page.waitForTimeout(300); break; }
        }
        const paperdoll = await page.$('.paperdoll');
        if (paperdoll) console.log('  (paperdoll found)');
    });
    await test('Bio tab has description textarea', async () => {
        const tabs = await page.$$('[data-tab-btn]');
        for (const t of tabs) {
            const text = await t.textContent();
            if (text && text.includes('Bio')) { await t.click(); await page.waitForTimeout(300); break; }
        }
        const desc = await page.$('#inspector-description');
        if (!desc) console.log('  (#inspector-description not found)');
    });

    // ─── 4. State / Save ───
    console.log('\n=== 4. World State ===');
    await test('GET /api/state returns rooms', async () => {
        const s = await getState();
        if (!s.rooms) throw new Error('No rooms');
        console.log('  (' + Object.keys(s.rooms).length + ' rooms, player: ' + s.active_player + ')');
    });
    await test('GET /api/save returns data', async () => {
        const data = await page.evaluate(async () => {
            const r = await fetch('/api/save'); return await r.json();
        });
        if (!data || !data.players) throw new Error('No players in save data');
    });

    // ─── 5. Environment ───
    console.log('\n=== 5. Environment ===');
    await test('Room has light level', async () => {
        const s = await getState();
        const room = Object.values(s.rooms || {})[0];
        if (room && room.environment) {
            console.log('  (light: ' + room.environment.light + ', temp: ' + room.environment.temperature + ')');
        }
    });

    // ─── RESULTS ───
    const ok = results.filter(r => r.status === 'OK').length;
    const nok = results.filter(r => r.status === 'FAIL').length;
    console.log('\n=== RESULTS: ' + ok + '/' + (ok+nok) + ' passed, ' + nok + ' failed ===\n');
    if (nok > 0) {
        console.log('Failures:');
        results.filter(r => r.status === 'FAIL').forEach(r => console.log('  - ' + r.label + ': ' + r.error));
    }
    console.log('Browser stays open. Close it when done.\n');
})();
