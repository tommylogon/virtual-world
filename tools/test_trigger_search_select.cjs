// Verify SearchSelect rollout across the trigger editor (unlock_way, set_state,
// condition node/state fields, on_use_on target).
const { chromium } = require('playwright');
const H = require('./test_helpers.cjs');

(async () => {
    const { browser, page, errors } = await H.startSession(chromium, 'http://127.0.0.1:4444');
    try {
        // ── 1. unlock_way way_id SearchSelect ──
        await page.evaluate(() => {
            window.__teResult = null;
            TriggerEditor.show({
                mode: 'single',
                triggerTypes: ['on_use'],
                effectTypes: [
                    { value: 'message', label: '💬 Message' },
                    { value: 'unlock_way', label: '🔓 Unlock Way' }
                ],
                conditionTypes: [],
                onSave: (data) => { window.__teResult = data; }
            });
            const sel = document.querySelector('.eff-type');
            sel.value = 'unlock_way';
            sel.dispatchEvent(new Event('change'));
        });
        await page.waitForTimeout(100);

        await page.click('.eff-select[data-kind="ways"] input[type="text"]');
        await page.waitForTimeout(150);
        const wayRows = await page.evaluate(() =>
            [...document.querySelector('.eff-select[data-kind="ways"]').querySelectorAll('[data-value]')].length
        );
        if (wayRows === 0) throw new Error('unlock_way way picker has no options');
        await page.click('.eff-select[data-kind="ways"] [data-value]');
        await page.waitForTimeout(100);
        const wayPicked = await page.evaluate(() => document.querySelector('.eff-unlock')?.value || '');
        if (!wayPicked) throw new Error('unlock_way pick did not set eff-unlock');

        // After picking a way, the success message field must be clickable
        // (regression: SearchSelect used to steal focus back on blur).
        await page.click('#te-success-msg');
        await page.type('#te-success-msg', 'The lock clicks open!');
        await page.waitForTimeout(100);
        const msgState = await page.evaluate(() => ({
            value: document.getElementById('te-success-msg').value,
            activeIsMsg: document.activeElement?.id === 'te-success-msg'
        }));
        console.log('Success message after pick:', JSON.stringify(msgState));
        if (msgState.value !== 'The lock clicks open!' || !msgState.activeIsMsg) {
            throw new Error('Success message field not clickable after way pick');
        }

        // ── 2. set_state node_id + state SearchSelects ──
        await page.evaluate(() => {
            window.__teResult = null;
            TriggerEditor.show({
                mode: 'single',
                triggerTypes: ['on_use'],
                effectTypes: [
                    { value: 'message', label: '💬 Message' },
                    { value: 'set_state', label: '🔧 Set State' }
                ],
                conditionTypes: [],
                onSave: (data) => { window.__teResult = data; }
            });
            const sel = document.querySelector('.eff-type');
            sel.value = 'set_state';
            sel.dispatchEvent(new Event('change'));
        });
        await page.waitForTimeout(100);
        const setStateFields = await page.evaluate(() => {
            const nodeWrap = document.querySelector('.eff-select[data-kind="nodes"]');
            const stateWrap = document.querySelector('.eff-select[data-kind="states"]');
            return {
                nodeHidden: !!document.querySelector('.eff-state-node'),
                stateHidden: !!document.querySelector('.eff-state-val'),
                nodeHasInput: !!nodeWrap?.querySelector('input[type="text"]'),
                stateHasInput: !!stateWrap?.querySelector('input[type="text"]')
            };
        });
        console.log('set_state fields:', JSON.stringify(setStateFields));
        if (!setStateFields.nodeHidden || !setStateFields.stateHidden || !setStateFields.nodeHasInput || !setStateFields.stateHasInput) {
            throw new Error('set_state node/state are not SearchSelects');
        }
        // Pick the state "closed"
        await page.click('.eff-select[data-kind="states"] input[type="text"]');
        await page.waitForTimeout(100);
        await page.click('.eff-select[data-kind="states"] [data-value="closed"]');
        await page.waitForTimeout(100);
        const stateVal = await page.evaluate(() => document.querySelector('.eff-state-val')?.value || '');
        if (stateVal !== 'closed') throw new Error(`state pick failed, got "${stateVal}"`);

        // Save and verify payload
        await page.evaluate(() => {
            const btn = [...document.querySelectorAll('button')].find(b => b.getAttribute('onclick')?.includes('_onSaveClick'));
            btn?.click();
        });
        await page.waitForTimeout(100);
        const saved = await page.evaluate(() => window.__teResult);
        console.log('Saved payload:', JSON.stringify(saved));
        if (saved?.effects?.[0]?.type !== 'set_state') throw new Error('Saved trigger effect type changed unexpectedly');
        if (saved.effects[0].params.state !== 'closed') throw new Error('Saved state_equals state missing');
        if (!saved.effects[0].params.node_id) throw new Error('Saved node_id missing');

        // ── 3. state_equals condition: node + state SearchSelects ──
        await page.evaluate(() => {
            window.__teResult = null;
            TriggerEditor.show({
                mode: 'single',
                triggerTypes: ['on_use'],
                effectTypes: [{ value: 'message', label: '💬 Message' }],
                conditionTypes: [
                    { value: 'skill_check', label: 'Skill Check' },
                    { value: 'state_equals', label: 'State Equals' }
                ],
                onSave: (data) => { window.__teResult = data; }
            });
        });
        // Add a condition leaf, set it to state_equals
        await page.evaluate(() => TriggerEditor._addCondLeaf());
        await page.waitForTimeout(100);
        await page.evaluate(() => {
            const sel = document.querySelector('.cond-type');
            sel.value = 'state_equals';
            sel.dispatchEvent(new Event('change'));
        });
        await page.waitForTimeout(100);
        const condFields = await page.evaluate(() => ({
            nodeHidden: !!document.querySelector('.cond-node'),
            stateHidden: !!document.querySelector('.cond-state'),
            nodeWrap: !!document.querySelector('.cond-field .eff-select[data-kind="nodes"]'),
            stateWrap: !!document.querySelector('.cond-field .eff-select[data-kind="states"]')
        }));
        console.log('condition fields:', JSON.stringify(condFields));
        if (!condFields.nodeHidden || !condFields.stateHidden || !condFields.nodeWrap || !condFields.stateWrap) {
            throw new Error('state_equals node/state are not SearchSelects');
        }
        // Pick a node
        await page.click('.cond-field .eff-select[data-kind="nodes"] input[type="text"]');
        await page.waitForTimeout(100);
        await page.click('.cond-field .eff-select[data-kind="nodes"] [data-value]');
        await page.waitForTimeout(100);
        const condNode = await page.evaluate(() => document.querySelector('.cond-node')?.value || '');
        if (!condNode) throw new Error('condition node pick did not set cond-node');
        // Pick a state
        await page.click('.cond-field .eff-select[data-kind="states"] input[type="text"]');
        await page.waitForTimeout(100);
        await page.click('.cond-field .eff-select[data-kind="states"] [data-value="open"]');
        await page.waitForTimeout(100);
        const condState = await page.evaluate(() => document.querySelector('.cond-state')?.value || '');
        if (condState !== 'open') throw new Error(`condition state pick failed, got "${condState}"`);

        // Save and verify the condition carries target+value
        await page.evaluate(() => {
            const btn = [...document.querySelectorAll('button')].find(b => b.getAttribute('onclick')?.includes('_onSaveClick'));
            btn?.click();
        });
        await page.waitForTimeout(100);
        const condSaved = await page.evaluate(() => window.__teResult);
        console.log('Condition saved:', JSON.stringify(condSaved));
        const cond = condSaved?.conditions?.conditions?.[0] || condSaved?.conditions?.[0];
        if (!cond || cond.type !== 'state_equals' || !cond.target || cond.value !== 'open') {
            throw new Error(`Saved condition missing state_equals target/state: ${JSON.stringify(cond)}`);
        }

        // ── 4. on_use_on target SearchSelect ──
        await page.evaluate(() => {
            window.__teResult = null;
            TriggerEditor.show({
                mode: 'single',
                triggerTypes: ['on_use_on'],
                effectTypes: [{ value: 'message', label: '💬 Message' }],
                conditionTypes: [],
                targetDatalistHtml: '<option value="door_south">🚪 door_south</option><option value="north">🚪 north → Kitchen</option>',
                onSave: (data) => { window.__teResult = data; }
            });
        });
        await page.waitForTimeout(100);
        const targetField = await page.evaluate(() => ({
            id: !!document.getElementById('te-target-name'),
            wrap: !!document.querySelector('.eff-select[data-kind="targets"]')
        }));
        console.log('target field:', JSON.stringify(targetField));
        if (!targetField.id || !targetField.wrap) throw new Error('on_use_on target is not a SearchSelect');
        await page.click('.eff-select[data-kind="targets"] input[type="text"]');
        await page.waitForTimeout(100);
        await page.click('.eff-select[data-kind="targets"] [data-value="door_south"]');
        await page.waitForTimeout(100);
        const targetVal = await page.evaluate(() => document.getElementById('te-target-name')?.value || '');
        if (targetVal !== 'door_south') throw new Error(`target pick failed, got "${targetVal}"`);

        H.checkConsoleErrors(errors, 'SearchSelect sweep');
        console.log('ALL PASS: SearchSelect sweep across trigger editor');
    } finally {
        await browser.close();
    }
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
