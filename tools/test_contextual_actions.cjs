// tools/test_contextual_actions.cjs
// Regression test for task-293: the character system prompt is trimmed (no static
// ACTIONS verb table) and the per-turn room context carries === AVAILABLE ACTIONS ===
// plus per-item action brackets.
//
// World-state agnostic: it asserts structural invariants that hold regardless of which
// scenario is loaded, using the pure prompt-builder functions in-page (no LLM call).
//
// Requires the server on :4444. Run: node tools/test_contextual_actions.cjs

const { chromium } = require('playwright');
const http = require('http');

async function waitForServer(url, maxWaitSec = 30) {
    const start = Date.now();
    while (Date.now() - start < maxWaitSec * 1000) {
        try {
            await new Promise((resolve, reject) => {
                const req = http.get(url + '/api/health', (res) => { res.resume(); resolve(); });
                req.on('error', reject);
                req.setTimeout(2000, () => { req.destroy(); reject(new Error('timeout')); });
            });
            return;
        } catch {
            await new Promise(r => setTimeout(r, 1000));
        }
    }
    throw new Error('Server did not become ready within ' + maxWaitSec + 's');
}

(async () => {
    await waitForServer('http://127.0.0.1:4444');

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    const results = [];
    const jsErrors = [];
    page.on('pageerror', e => jsErrors.push('[pageerror] ' + e.message));
    page.on('console', msg => {
        if (msg.type() !== 'error') return;
        if (msg.text().startsWith('Failed to load resource')) return;
        jsErrors.push('[console] ' + msg.text());
    });

    function pass(label) { results.push({ label, status: 'OK' }); console.log('  OK ' + label); }
    function fail(label, e) { results.push({ label, status: 'FAIL', error: e && (e.message || e) }); console.log('  FAIL ' + label + ': ' + (e && (e.message || e))); }

    try {
        await page.goto('http://127.0.0.1:4444/', { waitUntil: 'load', timeout: 60000 });
        await page.waitForFunction(() => typeof worldState !== 'undefined' && !!worldState.data && !!window.PromptBuilder, { timeout: 20000 });

        const data = await page.evaluate(() => {
            const P = window.PromptBuilder;
            const d = worldState.data;
            const charName = Object.keys(d.players || {}).find(n => !(d.players[n] || {}).simple_npc) || Object.keys(d.players || {})[0];
            const player = d.players[charName];
            let area = null;
            if (player && player.current_area) {
                for (const [id, n] of Object.entries(d.graph.nodes || {})) {
                    if (n.type === 'area' && (n.name === player.current_area || id === player.current_area)) { area = n; break; }
                }
            }
            const sys = player ? P.buildCharacterSystemPrompt(charName, player, 512) : '';
            const room = player ? P.buildRoomContext(d, charName, player, area) : '';
            return {
                charName,
                hasPlayer: !!player,
                sys,
                room,
                itemsHeader: room.split('\n').find(l => l.startsWith('Items that catch your attention:')) || '',
                carrying: room.split('\n').find(l => l.startsWith('Carrying:')) || '',
                hasAvailable: room.includes('=== AVAILABLE ACTIONS ===')
            };
        });

        if (!data.hasPlayer) { fail('Found an agent player to build prompts for', new Error('no non-simple_npc player in loaded world')); }
        else {
            // 1. Static system prompt trimmed: no markdown verb-table rows remain.
            const hasVerbTableRow = /\n\| (go|dash|crawl|climb|jump|take|drop|use) \|/i.test(data.sys);
            if (hasVerbTableRow) fail('System prompt no longer contains the static ACTIONS verb table'); else pass('System prompt has no static ACTIONS verb table');

            if (data.sys.includes('=== ACTIONS ===') && data.sys.includes('=== ACTION STRUCTURE ===')) pass('System prompt still has ACTIONS core + ACTION STRUCTURE safety net');
            else fail('System prompt keeps ACTIONS core + ACTION STRUCTURE safety net', new Error('missing sections'));

            if (data.sys.includes('=== AVAILABLE ACTIONS ===')) pass('System prompt points at per-turn === AVAILABLE ACTIONS ==='); else fail('System prompt references per-turn AVAILABLE ACTIONS');

            // 2. Per-turn room context carries the AVAILABLE ACTIONS block.
            if (data.hasAvailable) pass('Room context contains === AVAILABLE ACTIONS ==='); else fail('Room context contains AVAILABLE ACTIONS', new Error('block missing'));

            if (/\n=== ACTIONS ===/.test(data.sys)) pass('ACTIONS core present in system'); else fail('ACTIONS core present');
        }

        // 3. Items vs flavor: the block or the no-items line is present, and either
        //    item lines carry brackets or the room reports nothing to take.
        if (!data.hasPlayer) {
            // skip item assertions
        } else if (/\nAlways available: examine, look, inventory, stats, wait( |\n|$)/.test(data.room) || /\s+\[\w+[,\s\w]*\]/.test(data.room)) {
            pass('Room context has always-available line and/or item action brackets');
        } else {
            fail('Room context surfaces available actions', new Error('no always-available line and no [bracket] found'));
        }

        if (data.carrying) {
            if (/\S\[\w+[,\s\w]*\]/.test(data.carrying)) pass('Carrying line shows per-item action brackets'); else fail('Carrying line shows brackets', new Error(data.carrying));
        } else {
            pass('No carrying line (fine — nothing carried)');
        }

        // 4. JS errors guard.
        if (jsErrors.length) fail('No JS/console errors', new Error(jsErrors.join('; '))); else pass('No JS/console errors');
    } catch (err) {
        fail('Harness ran without throwing', err);
    }

    const passed = results.filter(r => r.status === 'OK').length;
    const failed = results.filter(r => r.status === 'FAIL').length;
    console.log('\n' + '═'.repeat(50));
    console.log('  RESULTS: ' + passed + '/' + (passed + failed) + ' passed, ' + failed + ' failed');
    console.log('═'.repeat(50));
    if (failed > 0) {
        results.filter(r => r.status === 'FAIL').forEach(r => console.log('  ✗ ' + r.label + ': ' + r.error));
    }
    await browser.close();
    if (failed > 0) process.exitCode = 1;
})();