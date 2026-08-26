const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    await page.goto('http://127.0.0.1:4444', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);

    async function cmd(command) {
        const result = await page.evaluate(async (c) => {
            const r = await fetch('/api/action', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ command: c }) });
            return await r.json();
        }, command);
        return result.output || result.error;
    }

    async function state() {
        return await page.evaluate(async () => {
            const r = await fetch('/api/state');
            return await r.json();
        });
    }

    // Get initial state
    const before = await state();
    console.log('Before rest — Player:', before.active_player);
    console.log('  Room:', before.current_room);
    console.log('  Ticks:', before.time_ticks);
    console.log('  Energy:', before.players?.[before.active_player]?.vitals?.Energy);

    // Rest for 10 minutes (2 ticks at 5 min/tick)
    console.log('\n=== rest 10 ===');
    const result = await cmd('rest 10');
    console.log('Output:', result);

    const after = await state();
    console.log('\nAfter rest —');
    console.log('  Ticks:', after.time_ticks);
    console.log('  Energy:', after.players?.[after.active_player]?.vitals?.Energy);
    console.log('  Ticks advanced:', after.time_ticks - before.time_ticks);

    const ticksAdvanced = after.time_ticks - before.time_ticks;
    const expectedTicks = Math.ceil(10 / 5);  // 10 min / 5 min per tick = 2
    const energy = after.players?.[after.active_player]?.vitals?.Energy;
    const energyBefore = before.players?.[before.active_player]?.vitals?.Energy;

    console.log('\n=== VERIFICATION ===');
    console.log(`Expected ticks: ${expectedTicks}, Actual: ${ticksAdvanced} — ${ticksAdvanced === expectedTicks ? '✓' : '✗'}`);
    console.log(`Energy change: ${energyBefore} → ${energy} (${energy - energyBefore})`);
    console.log(`Player awake: ${after.players?.[after.active_player]?.state === 'awake' ? '✓' : '✗'}`);

    // Test with longer rest
    console.log('\n=== rest 30 ===');
    const before2 = await state();
    const result2 = await cmd('rest 30');
    console.log('Output:', result2);
    const after2 = await state();
    const ticks2 = after2.time_ticks - before2.time_ticks;
    const expected2 = Math.ceil(30 / 5);
    console.log(`Expected ticks: ${expected2}, Actual: ${ticks2} — ${ticks2 === expected2 ? '✓' : '✗'}`);

    await browser.close();
})();
