const { chromium } = require('playwright');
(async () => {
    const BASE = 'http://127.0.0.1:4444';
    const http = (m, p, b) => fetch(BASE + p, { method: m, headers: b ? { 'Content-Type': 'application/json' } : {}, body: b ? JSON.stringify(b) : undefined }).then(r => r.json());
    const backup = await http('GET', '/api/save');
    const probe = {
        areas: { tavern: { name: 'tavern', description: 'quiet tavern', players: ['Jake', 'Violet'] } },
        items: {}, ways: {}, connections: {},
        players: {
            Jake: { name: 'Jake', current_area: 'tavern', state: 'awake', autonomy: false, simple_npc: false, personality: 'shy', vitals: {}, stats: {} },
            Violet: { name: 'Violet', current_area: 'tavern', state: 'awake', autonomy: true, simple_npc: true, npc_behavior: 'wander', npc_action_interval: 1, personality: '', vitals: {}, stats: {} }
        }, game_time: { tick: 0, display: '08:00' }, active_player: 'Jake', _scenario_name: 'probe_nowait'
    };
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    const errs = [];
    page.on('pageerror', e => errs.push('[pageerror] ' + e.message));
    try {
        await http('POST', '/api/load', probe);
        await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 });
        await page.waitForTimeout(1500);

        const trace = await page.evaluate(async () => {
            const logs = [];
            const mark = (name, stage) => logs.push(`${new Date().toISOString().slice(11,19)} ${name} ${stage} busy=${config.busy}`);
            // Instrument the awaits in the human action path + stepOnce tail.
            const origFetch = ApiClient.action.bind(ApiClient);
            ApiClient.action = async (...a) => { mark('Api.action', 'START'); try { const r = await origFetch(...a); mark('Api.action', 'END'); return r; } catch (e) { mark('Api.action', 'ERR ' + e.message); throw e; } };
            const of = worldState.fetch.bind(worldState);
            worldState.fetch = async (...a) => { mark('ws.fetch', 'START'); try { const r = await of(...a); mark('ws.fetch', 'END'); return r; } catch (e) { mark('ws.fetch', 'ERR'); throw e; } };
            const oa = ApiClient.applyTurn.bind(ApiClient);
            ApiClient.applyTurn = async (...a) => { mark('applyTurn', 'START'); try { const r = await oa(...a); mark('applyTurn', 'END'); return r; } catch (e) { mark('applyTurn', 'ERR'); throw e; } };

            events._characterAutonomy['Jake'] = false;
            config.controllingPlayer = 'Jake';
            window.__s = agent.stepOnce();
            await new Promise(r => setTimeout(r, 300));
            return { logs };
        }).catch(e => { errs.push('eval: ' + e.message); return { logs: [] }; });

        await page.waitForFunction(() => { const o = document.getElementById('htc-overlay'); return o && getComputedStyle(o).display === 'flex'; }, { timeout: 8000 }).catch(() => {});
        const disp = await page.evaluate(() => document.getElementById('htc-overlay') ? getComputedStyle(document.getElementById('htc-overlay')).display : 'no-node');
        console.log('composer display: ' + disp);

        await page.fill('#htc-action', 'wait');
        await page.click('#htc-submit');
        await page.waitForFunction(() => { const o = document.getElementById('htc-overlay'); return !o || getComputedStyle(o).display === 'none'; }, { timeout: 8000 }).catch(() => {});
        console.log('submit clicked — waiting 5s');
        await new Promise(r => setTimeout(r, 5000));

        const out = await page.evaluate(async () => {
            const settled = await Promise.race([window.__s.then(() => 'SETTLED'), new Promise(r => setTimeout(() => r('STILL PENDING'), 50))]);
            return { settled, busy: config.busy, running: config.running };
        });
        console.log('stepOnce promise: ' + out.settled + ' | busy=' + out.busy + ' running=' + out.running);
        (trace.logs || []).forEach(l => console.log('  ' + l));

        console.log('\npage errors: ' + (errs.length ? errs.join(' | ') : 'none'));
    } finally {
        await http('POST', '/api/load', backup).catch(e => console.log('restore failed'));
        await browser.close();
    }
    process.exit(0);
})();