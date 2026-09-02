const { chromium } = require('playwright');

// Regression: buildBehaviorActionCard renders the edit-form card for every
// behavior action type. Catches undefined-identifier crashes like the
// `weighItem is not defined` breakage (task-388 follow-up, 2026-09-02).
// Client-side only — nothing is saved.

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1400, height: 900 });
    const errors = [];
    page.on('pageerror', e => errors.push('[pageerror] ' + e.message));

    await page.goto('http://127.0.0.1:4444', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForFunction(() => typeof InspectorBehaviors !== 'undefined', null, { timeout: 20000 });
    await page.waitForTimeout(800);

    const res = await page.evaluate(() => {
        const B = window.InspectorBehaviors;
        const types = B.BEHAVIOR_ACTION_TYPES().map(t => t.value);
        // Kitchen-sink action: every param any card builder might read.
        const kitchen = {
            text: 't', state: 'idle', amount: 5, stat: 'HP', item: 'sword', target: 'bob',
            container: 'box', direction: 'north', slot: 'head', recipe: 'pie', subject: 'math',
            where: 'hand', intensity: 'normal', minutes: 10, area: 'kitchen', areas: 'a,b',
            mode: 'goto', item_id: 'torch', character_id: 'miki', name: 'N', description: 'D',
            instructions: 'i', fallback_message: 'f', max_words: 20, importance: 5, tags: ['x'],
            key: 'k', value: 'v', weapon: 'w', relation: 'on', way_action: 'open', kit: 'k',
        };
        const bad = [];
        types.forEach((t, i) => {
            try {
                const html = B.buildBehaviorActionCard(0, i, { type: t, ...kitchen });
                if (!html) bad.push(t + ': empty card');
            } catch (e) {
                bad.push(t + ': ' + e.message);
            }
        });
        return { total: types.length, bad };
    });

    console.log(`Action types tested: ${res.total}`);
    if (res.bad.length) {
        console.log('FAILING TYPES:');
        res.bad.forEach(b => console.log('  ✕ ' + b));
    }
    const noErrors = errors.length === 0;
    if (!noErrors) console.log('JS page errors: ' + errors.join(' | '));
    const ok = res.bad.length === 0 && noErrors;
    console.log('\n' + (ok ? 'RESULT: PASS' : 'RESULT: FAIL'));
    await browser.close();
    process.exit(ok ? 0 : 1);
})();
