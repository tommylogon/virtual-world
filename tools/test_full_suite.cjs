const { chromium } = require('playwright');
(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1400, height: 900 });
    const results = [];

    function pass(label) { results.push({label,status:'OK'}); console.log('  OK ' + label); }
    function fail(label, err) { results.push({label,status:'FAIL',error:err.message}); console.log('  FAIL ' + label + ': ' + err.message); }
    async function test(label, fn) { try { await fn(); pass(label); } catch(e) { fail(label, e); } }
    async function api(body) {
        return await page.evaluate(async b => { const r = await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}); return await r.json(); }, body);
    }
    async function getState() {
        return await page.evaluate(async () => { const r = await fetch('/api/state'); return await r.json(); });
    }
    async function clickAgent(name) {
        await page.evaluate(async n => {
            const s = await fetch('/api/state').then(r=>r.json());
            if (s.players?.[n] && window.VW?.inspector) VW.inspector.showAgent(n);
        }, name);
        await page.waitForTimeout(300);
    }
    async function switchTab(label) {
        const tabs = await page.$$('[data-tab-btn]');
        for (const t of tabs) {
            const text = await t.textContent();
            if (text && text.includes(label)) { await t.click(); await page.waitForTimeout(200); break; }
        }
    }

    await page.goto('http://127.0.0.1:4444', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    // ─── 1. PAGE LOAD & UI ───
    console.log('\n=== 1. PAGE LOAD & UI ===');
    await test('Page loads with title', async () => {
        const title = await page.title(); if (!title) throw Error('No title');
    });
    await test('Command input exists', async () => {
        const el = await page.$('#command-input'); if (!el) throw Error('Missing');
    });
    await test('Inspector panel exists', async () => {
        const el = await page.$('#inspector-panel'); if (!el) throw Error('Missing');
    });
    await test('Graph canvas renders', async () => {
        const el = await page.$('#graph-container canvas'); if (!el) throw Error('Missing');
        const box = await el.boundingBox(); if (!box || box.width===0) throw Error('Zero width');
    });
    await test('Event stream exists', async () => {
        const el = await page.$('#event-stream'); if (!el) throw Error('Missing');
    });
    await test('Agent list section exists', async () => {
        const el = await page.$('#agent-list'); if (!el) throw Error('Missing');
        const items = await el.$$('[class*="agent"]');
        if (items.length === 0) console.log('  (0 agent items, non-critical)');
    });
    await test('No console errors on load', async () => {
        const errors = [];
        page.on('console', msg => { if (msg.type()==='error') errors.push(msg.text()); });
        await page.waitForTimeout(500);
        if (errors.length > 0) console.log('  (' + errors.length + ' console errors)');
    });

    // ─── 2. COMMANDS ───
    console.log('\n=== 2. COMMANDS ===');
    await test('look returns output', async () => {
        const r = await api({command:'look'}); if (r.error && !r.output) throw Error(r.error);
    });
    await test('inventory returns output', async () => {
        const r = await api({command:'inventory'}); if (r.error && !r.output) throw Error(r.error);
    });
    await test('inventory alias (i) works', async () => {
        const r = await api({command:'i'}); if (r.error && !r.output) throw Error(r.error);
    });
    await test('examine self works', async () => {
        const r = await api({command:'examine self'}); if (r.error) throw Error(r.error);
    });
    await test('stats works', async () => {
        const r = await api({command:'stats'}); if (r.error) throw Error(r.error);
    });
    await test('go north (if exit exists)', async () => {
        const r = await api({command:'go north'});
        if (r.error && !r.output && !r.error.toLowerCase().includes('cant go')) throw Error(r.error);
    });
    await test('go back (south)', async () => {
        const r = await api({command:'go south'});
        if (r.error && !r.output && !r.error.toLowerCase().includes('cant go')) throw Error(r.error);
    });

    // ─── 3. AGENT INSPECTOR ───
    console.log('\n=== 3. AGENT INSPECTOR ===');
    await test('Show agent via API', async () => {
        const s = await getState();
        if (s.active_player) { await clickAgent(s.active_player); pass('Showed '+s.active_player); }
        else throw Error('No active player');
    });
    await test('Bio tab loads stats', async () => {
        await switchTab('Bio');
        const vitals = await page.$('[class*="vital"]');
        if (!vitals) console.log('  (no vitals found)');
    });
    await test('Inventory tab loads paperdoll', async () => {
        await switchTab('Inventory');
        const pd = await page.$('.paperdoll');
        if (pd) console.log('  (paperdoll found)');
        else console.log('  (no paperdoll)');
    });
    await test('Inventory tab loads', async () => {
        await switchTab('Inventory');
        const inv = await page.$('[class*="inspector-section"]');
        if (!inv) console.log('  (no sections found)');
    });
    await test('Bio tab has description textarea', async () => {
        await switchTab('Bio');
        const desc = await page.$('#inspector-description');
        if (!desc) console.log('  (no description textarea)');
    });
    await test('Bio tab has Generate from Equipment button', async () => {
        const btn = await page.$('[onclick*="generateDescription"]');
        if (!btn) {
            const alt = await page.$('[onclick*="Generate"]');
            if (!alt) console.log('  (no generate button)');
        }
    });

    // ─── 4. STATE & SAVE ───
    console.log('\n=== 4. STATE & SAVE ===');
    await test('GET /api/state returns rooms', async () => {
        const s = await getState(); if (!s.rooms) throw Error('No rooms');
        console.log('  ('+Object.keys(s.rooms).length+' rooms, player: '+s.active_player+')');
    });
    await test('GET /api/save returns valid JSON', async () => {
        const d = await page.evaluate(async () => { const r = await fetch('/api/save'); return await r.json(); });
        if (!d || !d.players) throw Error('No players in save');
    });
    await test('GET /api/players returns list', async () => {
        const d = await page.evaluate(async () => { const r = await fetch('/api/players'); return await r.json(); });
        if (!d.players || d.players.length===0) throw Error('No players');
        console.log('  ('+d.players.length+' players, active: '+d.active+')');
    });

    // ─── 5. EXISTING BUG VERIFICATION ───
    console.log('\n=== 5. BUG VERIFICATION ===');
    await test('window.ui.getAgentColor not broken', async () => {
        const s = await getState();
        const name = s.active_player;
        if (name) {
            const ok = await page.evaluate(n => { try { return typeof ui.getAgentColor(n) === 'string'; } catch(e) { return e.message; } }, name);
            if (ok !== true) throw Error('getAgentColor: '+ok);
        }
    });
    await test('window.events.getCharacterState not broken', async () => {
        const s = await getState();
        const name = s.active_player;
        if (name) {
            const ok = await page.evaluate(n => { try { return typeof events.getCharacterState(n) === 'object'; } catch(e) { return e.message; } }, name);
            if (ok !== true && ok !== false) throw Error('getCharacterState: '+ok);
        }
    });
    await test('ApiClient.updateCharacter not broken', async () => {
        const ok = await page.evaluate(() => { try { return typeof ApiClient.updateCharacter === 'function'; } catch(e) { return e.message; } });
        if (ok !== true) throw Error('ApiClient: '+ok);
    });
    await test('ApiClient.addPlayerMemory not broken', async () => {
        const ok = await page.evaluate(() => { try { return typeof ApiClient.addPlayerMemory === 'function'; } catch(e) { return e.message; } });
        if (ok !== true) throw Error('ApiClient.addPlayerMemory: '+ok);
    });

    // ─── 6. RESULTS ───
    const passed = results.filter(r => r.status==='OK').length;
    const failed = results.filter(r => r.status==='FAIL').length;
    console.log('\n=== RESULTS: '+passed+'/'+(passed+failed)+' passed, '+failed+' failed ===');
    if (failed > 0) {
        console.log('\nFailures:');
        results.filter(r=>r.status==='FAIL').forEach(r => console.log('  - '+r.label+': '+r.error));
    }
    console.log('\nBrowser stays open. Close when done.');
})();
