const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push('[pageerror] ' + e.message));

    await page.goto('http://127.0.0.1:4444', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2500);

    // Pick the active player and force them to 'human' (autonomy off).
    const name = await page.evaluate(() => worldState.data?.active_player);
    if (!name) { console.log('FAIL no active player'); await browser.close(); process.exit(1); }
    console.log('Active player: ' + name);

    // Make them human (autonomy off) + wire up, then kick a manual step.
    const kick = await page.evaluate(async (n) => {
        await ApiClient.updateCharacter(n, { simple_npc: false, autonomy: false });
        if (events?._characterAutonomy) events._characterAutonomy[n] = false;
        config.controllingPlayer = n; config.turnBased = false; config.running = false; config.busy = false;
        window.__stepPromise = agent.step().then(() => ({ ok: true }));
        return { autonomous: events.isAutonomous ? events.isAutonomous(n) : 'n/a' };
    }, name);
    console.log('isAutonomous after flag: ' + kick.autonomous);

    // The run must PAUSE (composer visible), not skip.
    await page.waitForSelector('#htc-overlay', { state: 'visible', timeout: 6000 });
    const visible = await page.$eval('#htc-overlay', el => getComputedStyle(el).display === 'flex');
    console.log('Composer visible (paused, not skipped): ' + visible);
    if (!visible) { console.log('FAIL composer not shown — human turn was NOT paused'); }

    const title = await page.$eval('#htc-title', el => el.textContent);
    console.log('Composer title: ' + title);

    // Fill the form: speech + a no-op action, then Act.
    await page.fill('#htc-action', 'wait');
    await page.fill('#htc-speech', 'Hello from my human turn');
    await page.click('#htc-submit');
    await page.waitForSelector('#htc-overlay', { state: 'hidden', timeout: 6000 });

    await page.waitForTimeout(1500);
    const body = await page.evaluate(() => document.body.innerText || '');
    const speechLogged = /Hello from my human turn/.test(body);
    console.log('Speech executed + logged: ' + speechLogged);

    // Composer should return to idle and clean up.
    const stepOk = await page.evaluate(() => window.__stepPromise.then(r => r.ok));
    console.log('Step promise resolved cleanly: ' + stepOk);

    console.log('\nJS page errors: ' + (errors.length ? errors.join(' | ') : 'none'));
    const allOk = visible && speechLogged && stepOk && errors.length === 0;
    console.log(allOk ? 'RESULT: PASS' : 'RESULT: FAIL');
    await browser.close();
    process.exit(allOk ? 0 : 1);
})();