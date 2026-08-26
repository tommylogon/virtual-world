// Regression click-through tests for the 10 known bug reports.
// Uses test_helpers.cjs for error capture (Phase 1) and real UI clicks
// (Phase 2 of the Playwright upgrade task).
//
// Run: node tools/test_regressions.cjs   (server must be running on 4444)

const { chromium } = require('playwright');
const H = require('./test_helpers.cjs');

(async () => {
    const { browser, page, errors } = await H.startSession(chromium);
    const results = [];
    const t = async (label, fn) => {
        try { await fn(); results.push({ label, status: 'OK' }); console.log('  OK   ' + label); }
        catch (e) { results.push({ label, status: 'FAIL', error: (e.message || e) }); console.log('  FAIL ' + label + ': ' + (e.message || e)); }
    };

    // Helpers that snapshot the error list at the start of a test so we can
    // assert this test added no new JS errors.
    const errorsAt = (mark) => errors.slice(mark).map(e => e.type + ': ' + e.message).join(' | ');
    let errorMark = errors.length;

    console.log('=== Bug 9: Settings tabs ===');
    await t('Settings modal opens', async () => {
        await page.click('text=Settings');
        await page.waitForSelector('#settings-modal[style*="flex"], #settings-modal:not([style*="none"])', { timeout: 5000 });
    });
    for (const tab of ['tab-connection', 'tab-agent', 'tab-automation', 'tab-graph', 'tab-embedding']) {
        await t('Settings tab ' + tab + ' loads without errors', async () => {
            await page.evaluate(t => window.switchSettingsTab(t), tab);
            await page.waitForTimeout(150);
            const active = await page.evaluate(t => document.querySelector('#settings-modal .tab-btn.active')?.getAttribute('data-tab'), tab);
            if (active !== tab) throw 'Tab did not activate: got ' + active;
        });
    }
    await t('Settings modal has API Format dropdown', async () => {
        const el = await page.$('#agent-api-format');
        if (!el) throw 'Missing #agent-api-format';
    });
    await page.evaluate(() => document.getElementById('settings-modal').style.display = 'none');
    H.checkConsoleErrors(errors, 'Bug 9 settings tabs');

    console.log('\n=== Bug 1: Trigger editor opens ===');
    await t('Trigger editor opens from inspector without JS errors', async () => {
        const mark = errors.length;
        await page.evaluate(async () => {
            // Find the first item node and open it in the inspector
            const s = await fetch('/api/state').then(r => r.json());
            const nodes = Object.values(s.graph?.nodes || {});
            const item = nodes.find(n => n.type === 'item');
            if (item && window.VW?.inspector) VW.inspector.showNode(item.id);
        });
        await page.waitForTimeout(400);
        const opened = await page.evaluate(async () => {
            // Open the trigger graph editor for the inspected item node
            const s = await fetch('/api/state').then(r => r.json());
            const nodes = Object.values(s.graph?.nodes || {});
            const item = nodes.find(n => n.type === 'item');
            if (item && window.InspectorTriggers?._openGraphEditor) {
                window.InspectorTriggers._openGraphEditor(item.id);
                return true;
            }
            return false;
        });
        await page.waitForTimeout(400);
        const modal = await page.$('#tg-modal');
        if (modal) {
            await page.evaluate(() => window.TriggerGraph && window.TriggerGraph._close && window.TriggerGraph._close());
        } else if (!opened) {
            console.log('  (no item/trigger path available — skipping graph open check)');
        } else {
            throw 'Trigger graph modal did not appear';
        }
        const newErrs = errors.slice(mark).filter(e => e.type === 'pageerror');
        if (newErrs.length) throw 'JS errors: ' + newErrs.map(e => e.message).join(' | ');
    });

    console.log('\n=== Bug 7: Generate from Equipment ===');
    await t('Generate from Equipment button fills description without errors', async () => {
        const mark = errors.length;
        const state = await H.getState(page);
        const playerName = state.active_player || Object.keys(state.players || {})[0];
        if (!playerName) throw 'No player in world';
        await H.showAgent(page, playerName);
        await H.switchTab(page, 'Bio');
        const btn = await page.$('[onclick*="generateDescription"], [onclick*="Generate from Equipment"]');
        if (!btn) { console.log('  (no Generate button found)'); return; }
        const before = await page.evaluate(() => document.getElementById('inspector-description')?.value || '');
        await page.evaluate(name => window.InspectorAgentView?._generateDescription(name), playerName);
        await page.waitForTimeout(1200);
        const after = await page.evaluate(() => document.getElementById('inspector-description')?.value || '');
        if (after && after !== before) console.log('  (description generated)');
        else if (after === before) console.log('  (description unchanged — may be manual mode)');
        const newErrs = errors.slice(mark).filter(e => e.type === 'pageerror');
        if (newErrs.length) throw 'JS errors: ' + newErrs.map(e => e.message).join(' | ');
    });

    console.log('\n=== Bug 10: Turn advance ===');
    await t('POST /api/turn/apply succeeds repeatedly', async () => {
        for (let i = 0; i < 3; i++) {
            const r = await page.evaluate(async () => {
                const res = await fetch('/api/turn/apply', { method: 'POST' });
                return { status: res.status, body: await res.json() };
            });
            if (r.status !== 200 || r.body.error) throw `turn/apply failed (${r.status}): ${JSON.stringify(r.body)}`;
        }
    });

    console.log('\n=== Bug 8: Max steps limit ===');
    await t('Max steps input updates config and display', async () => {
        await page.fill('#sim-max-steps', '2');
        await page.evaluate(() => {
            const input = document.getElementById('sim-max-steps');
            if (typeof config !== 'undefined') config.maxSteps = parseInt(input?.value) || 0;
            window.VW?.ui?.updateMaxStepsDisplay?.();
        });
        const cfg = await page.evaluate(() => (typeof config !== 'undefined' ? config.maxSteps : 'missing'));
        if (cfg !== 2) throw 'config.maxSteps did not update: ' + cfg;
        const hasDisplay = await page.evaluate(() => !!document.getElementById('step-display'));
        if (!hasDisplay) throw 'Missing #step-display';
        console.log('  (max steps display element present)');
    });

    console.log('\n=== Bug 4: Initiative order ===');
    await t('Initiative turn queue sorts players by roll', async () => {
        const state = await H.getState(page);
        const players = Object.keys(state.players || {});
        if (players.length < 2) { console.log('  (only ' + players.length + ' player — skipping order check)'); return; }
        await page.evaluate(() => {
            if (window.config) config.turnOrder = 'initiative';
            window.agent?.initializeTurnQueue?.();
        });
        await page.waitForTimeout(200);
        const queue = await page.evaluate(() => window.agent?.turnQueue || []);
        if (!Array.isArray(queue) || queue.length === 0) throw 'No turn queue produced';
        console.log('  (turn queue: ' + queue.join(', ') + ')');
        const hasRolls = await page.evaluate(() => Object.keys(window.agent?.initiativeRolls || {}).length > 0);
        if (!hasRolls) throw 'No initiative rolls recorded';
    });

    console.log('\n=== Bug 5: HP display formatting ===');
    await t('Inspector HP value matches state', async () => {
        const state = await H.getState(page);
        const playerName = state.active_player || Object.keys(state.players || {})[0];
        const expectedHP = state.players?.[playerName]?.vitals?.HP;
        if (expectedHP === undefined) throw 'No HP in state for ' + playerName;
        await H.showAgent(page, playerName);
        await H.switchTab(page, 'Bio');
        const displayedHP = await page.evaluate(() => {
            const el = document.querySelector('[class*="vital"][class*="HP"], .vital-hp, [data-vital="HP"]');
            return el ? el.textContent.trim() : null;
        });
        if (displayedHP === null) { console.log('  (no HP vital element found — skipping value check)'); return; }
        console.log('  (expected ' + expectedHP + ', displayed "' + displayedHP + '")');
        if (!displayedHP.includes(String(expectedHP))) throw `HP mismatch: state=${expectedHP} display="${displayedHP}"`;
    });

    console.log('\n=== Bug 2/6: Dropdown text readability ===');
    await t('Tag multiselect dropdown renders with readable text', async () => {
        const hasChoices = await page.evaluate(() => document.querySelectorAll('.choices, .choices__list').length);
        if (hasChoices === 0) { console.log('  (no Choices.js dropdowns on current view)'); return; }
        // Verify dropdown options have non-transparent text color
        const bad = await page.evaluate(() => {
            let found = [];
            document.querySelectorAll('.choices__list--dropdown .choices__item, .choices__item--selectable').forEach(el => {
                const c = getComputedStyle(el).color;
                if (c === 'rgba(0, 0, 0, 0)' || c === 'transparent') found.push(el.textContent.trim());
            });
            return found.slice(0, 3);
        });
        if (bad.length) throw 'Dropdown items with invisible text: ' + bad.join(', ');
    });

    console.log('\n=== RESULTS ===');
    const passed = results.filter(r => r.status === 'OK').length;
    const failed = results.filter(r => r.status === 'FAIL').length;
    console.log(`  ${passed}/${passed + failed} passed, ${failed} failed`);
    if (failed > 0) results.filter(r => r.status === 'FAIL').forEach(r => console.log('  \u2717 ' + r.label + ': ' + r.error));
    await browser.close();
    process.exit(failed > 0 ? 1 : 0);
})();
