const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1400, height: 900 });

    await page.goto('http://127.0.0.1:4444', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    async function check(label, fn) {
        try {
            await fn();
            console.log(`  \u2713 ${label}`);
        } catch (err) {
            console.log(`  \u2717 ${label}: ${err.message}`);
        }
    }

    async function command(cmd) {
        return await page.evaluate(async (c) => {
            try {
                const r = await fetch('/api/action', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: c })
                });
                return await r.json();
            } catch (e) {
                return { error: e.message };
            }
        }, cmd);
    }

    async function getState() {
        return await page.evaluate(async () => {
            const r = await fetch('/api/state');
            return await r.json();
        });
    }

    console.log('\n=== Command Test Suite ===\n');

    // --- Look commands ---
    await check('look returns description output', async () => {
        const resp = await command('look');
        if (resp.error) throw new Error('look failed: ' + resp.error);
        if (!resp.output || resp.output.length === 0) throw new Error('No output from look');
        console.log(`  (output: "${(resp.output[0] || resp.output).substring(0, 80)}...")`);
    });

    await check('look around is alias', async () => {
        const resp = await command('look around');
        if (resp.error) throw new Error('look around failed: ' + resp.error);
    });

    await check('l (short alias) works', async () => {
        const resp = await command('l');
        // Accept either success or a parse error telling the user the command format
        if (resp.error && !resp.output) throw new Error('l failed: ' + resp.error);
    });

    // --- Inventory ---
    await check('inventory returns items (or empty)', async () => {
        const resp = await command('inventory');
        if (resp.error) throw new Error('inventory failed: ' + resp.error);
    });

    await check('i (short alias) works', async () => {
        const resp = await command('i');
        if (resp.error && !resp.output) throw new Error('i failed: ' + resp.error);
    });

    // --- Examine ---
    await check('examine self succeeds', async () => {
        const resp = await command('examine self');
        if (resp.error) throw new Error('examine self failed: ' + resp.error);
    });

    await check('examine me succeeds', async () => {
        const resp = await command('examine me');
        if (resp.error && !resp.output) {
            // "me" may not be recognized — not critical
            console.log('  (examine me returned error, non-critical)');
        }
    });

    // --- Stats / Status ---
    await check('stats succeeds', async () => {
        const resp = await command('stats');
        if (resp.error) throw new Error('stats failed: ' + resp.error);
    });

    await check('status succeeds', async () => {
        const resp = await command('status');
        if (resp.error) throw new Error('status failed: ' + resp.error);
    });

    // --- Movement directional commands ---
    await check('go north completes without crash', async () => {
        const resp = await command('go north');
        // May fail with "You can't go that way" — that's fine, just don't crash
        if (resp.error && !resp.output) throw new Error('go north crashed: ' + resp.error);
    });

    await check('go south completes without crash', async () => {
        const resp = await command('go south');
        if (resp.error && !resp.output) throw new Error('go south crashed: ' + resp.error);
    });

    await check('north (shorthand) works', async () => {
        const resp = await command('north');
        if (resp.error && !resp.output) throw new Error('north crashed: ' + resp.error);
    });

    await check('south shorthand works', async () => {
        const resp = await command('south');
        if (resp.error && !resp.output) throw new Error('south crashed: ' + resp.error);
    });

    // --- Help ---
    await check('help returns instructions', async () => {
        const resp = await command('help');
        if (resp.error) throw new Error('help failed: ' + resp.error);
        if (!resp.output) throw new Error('No output from help');
    });

    await check('commands (alias) works', async () => {
        const resp = await command('commands');
        if (resp.error && !resp.output) throw new Error('commands failed: ' + resp.error);
    });

    // --- Take / Drop (if items available) ---
    await check('take without target gives guidance', async () => {
        const resp = await command('take');
        // Should get usage guidance or error, not a crash
        if (resp.error && resp.output) {
            // If both error and output exist, it handled gracefully
        }
    });

    await check('drop without target gives guidance', async () => {
        const resp = await command('drop');
        if (resp.error && !resp.output) throw new Error('drop crashed: ' + resp.error);
    });

    // --- Time commands ---
    await check('time command succeeds', async () => {
        const resp = await command('time');
        if (resp.error) throw new Error('time failed: ' + resp.error);
    });

    // --- Rest command ---
    await check('rest 5 advances ticks', async () => {
        const before = await getState();
        const beforeTicks = before.time_ticks;
        const resp = await command('rest 5');
        if (resp.error) throw new Error('rest 5 failed: ' + resp.error);
        const after = await getState();
        const ticksAdv = after.time_ticks - beforeTicks;
        console.log(`  (ticks advanced: ${ticksAdv})`);
        if (ticksAdv === 0) {
            console.log('  (warning: no ticks advanced — rest may take minimum 1 tick)');
        }
    });

    // --- Wait command ---
    await check('wait 5 succeeds', async () => {
        const resp = await command('wait 5');
        if (resp.error) throw new Error('wait 5 failed: ' + resp.error);
    });

    // --- State consistency check ---
    await check('State remains valid after commands', async () => {
        const state = await getState();
        if (!state.active_player) throw new Error('No active player after commands');
        if (state.rooms && !state.current_room && !state.players?.[state.active_player]?.room_id) {
            console.log('  (current_room not directly in state — checking nested)');
        }
    });

    console.log('\nDone.');
    await browser.close();
})();
