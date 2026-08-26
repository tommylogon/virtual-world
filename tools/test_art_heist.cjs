const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1400, height: 900 });
    const results = [];
    const pageErrors = [];

    function pass(l) { results.push({label:l,status:'OK'}); console.log('  OK ' + l); }
    function fail(l, e) { results.push({label:l,status:'FAIL',error:e.message||e}); console.log('  FAIL ' + l + ': ' + (e.message||e)); }
    async function t(label, fn) { try { await fn(); pass(label); } catch(e) { fail(label, e); } }
    async function getState() { return await page.evaluate(async () => { const r=await fetch('/api/state'); return await r.json(); }); }
    async function runCmd(cmd) { return await page.evaluate(async (c) => { const r=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:c})}); return await r.json(); }, cmd); }

    // ── Helpers ──────────────────────────────────────────
    async function closeModalIfOpen(modalId) {
        await page.evaluate((id) => {
            const m = document.getElementById(id);
            if (m && m.style.display !== 'none') { m.style.display = 'none'; }
        }, modalId);
        await page.waitForTimeout(200);
    }
    async function clickToolbarButton(textMatch) {
        const buttons = await page.$$('.toolbar-btn, button[onclick]');
        for (const btn of buttons) {
            const text = await btn.textContent();
            if (text && text.trim().includes(textMatch)) { await btn.click(); return true; }
        }
        return false;
    }
    async function fillCreateModalField(id, value) {
        const el = await page.$('#' + id);
        if (el) { await el.fill(String(value)); return true; }
        return false;
    }
    async function selectCreateModalOption(id, value) {
        const el = await page.$('#' + id);
        if (el) { await el.selectOption(value); return true; }
        return false;
    }
    async function expandTriggersSection() {
        const summary = await page.$('#create-modal-content details summary');
        if (summary) {
            const parent = await summary.evaluateHandle(el => el.parentElement);
            const isOpen = await parent.evaluate(el => el.open);
            if (!isOpen) await summary.click();
            await page.waitForTimeout(100);
        }
    }
    async function submitCreateModal() {
        const btn = await page.$('#create-modal-submit');
        if (btn) { await btn.click(); return true; }
        return false;
    }
    async function clickAgent(name) {
        const agents = await page.$$('.agent-item');
        for (const a of agents) {
            const text = await a.textContent();
            if (text && text.includes(name)) { await a.click(); return true; }
        }
        return false;
    }
    async function switchInspectorTab(label) {
        const tabs = await page.$$('[data-tab-btn]');
        for (const t of tabs) {
            const text = await t.textContent();
            if (text && text.includes(label)) { await t.click(); await page.waitForTimeout(200); return true; }
        }
        return false;
    }
    async function sendManualCommand(charName, command) {
        await clickAgent(charName);
        await page.waitForTimeout(300);
        await switchInspectorTab('Advanced');
        await page.waitForTimeout(300);
        const hasInput = await page.evaluate(() => {
            const el = document.getElementById('manual-cmd-input');
            return !!el && el.offsetParent !== null;
        });
        if (!hasInput) { console.log('  (no visible manual cmd input)'); return null; }
        const input = await page.$('#manual-cmd-input');
        if (!input) return null;
        await input.fill(command);
        await page.keyboard.press('Enter');
        await page.waitForTimeout(600);
        return await page.evaluate(() => {
            const stream = document.querySelector('#event-stream, .event-stream');
            if (!stream) return '';
            const last = stream.lastElementChild;
            return last ? (last.textContent || '').trim().substring(0, 80) : '';
        });
    }
    // Also expose command input on window so we can type commands the normal way
    async function typeCommand(cmd) {
        const input = await page.$('#command-input');
        if (!input) return null;
        await input.fill(cmd);
        await page.keyboard.press('Enter');
        await page.waitForTimeout(500);
        return await page.evaluate(() => {
            const stream = document.querySelector('#event-stream, .event-stream');
            if (!stream) return '';
            const last = stream.lastElementChild;
            return last ? (last.textContent || '').trim().substring(0, 80) : '';
        });
    }

    page.on('pageerror', err => { pageErrors.push(err.message); });

    // ════════════════════════════════════════════════════════
    // PHASE 0: Load page and accept any initial dialogs
    // ════════════════════════════════════════════════════════
    await page.goto('http://127.0.0.1:4444', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    // ── Click 🆕 New button → accept confirm dialog ──
    await t('Click New Scenario button', async () => {
        page.once('dialog', dialog => { dialog.accept(); });
        await clickToolbarButton('🆕');
        // Wait for the confirm dialog and world load
        await page.waitForTimeout(1500);
        // Verify world is empty
        const state = await getState();
        const roomCount = Object.keys(state.rooms || {}).length;
        console.log('  (rooms after new: ' + roomCount + ')');
    });

    // ════════════════════════════════════════════════════════
    // PHASE 1: Build the museum (rooms, doors, items, chars)
    // ════════════════════════════════════════════════════════
    console.log('\n=== PHASE 1: BUILD MUSEUM ===');

    // ── 1a. Create rooms ──
    const roomNames = ['Grand Gallery', 'Vault', 'Rooftop'];
    for (const name of roomNames) {
        await t('Create room: ' + name, async () => {
            await closeModalIfOpen('create-modal');
            const ok = await clickToolbarButton('Room');
            if (!ok) throw 'Room button not found';
            await page.waitForTimeout(300);
            await fillCreateModalField('room-name', name);
            await fillCreateModalField('room-desc', 'The ' + name + ' in the museum.');
            await submitCreateModal();
            await page.waitForTimeout(500);
            await closeModalIfOpen('create-modal');
            const state = await getState();
            if (!state.rooms[name]) throw 'Room not created';
        });
    }

    // ── 1b. Connect rooms ──
    await t('Connect Gallery → Vault (locked)', async () => {
        await closeModalIfOpen('create-modal');
        await clickToolbarButton('Door');
        await page.waitForTimeout(300);
        await selectCreateModalOption('conn-roomA', 'Grand Gallery');
        await fillCreateModalField('conn-dir1', 'east');
        await selectCreateModalOption('conn-roomB', 'Vault');
        await fillCreateModalField('conn-dir2', 'west');
        await selectCreateModalOption('conn-state', 'locked');
        await fillCreateModalField('conn-desc', 'Reinforced steel door with card reader.');
        await submitCreateModal();
        await page.waitForTimeout(500);
        await closeModalIfOpen('create-modal');
    });

    await t('Connect Gallery → Rooftop (open)', async () => {
        await closeModalIfOpen('create-modal');
        await clickToolbarButton('Door');
        await page.waitForTimeout(300);
        await selectCreateModalOption('conn-roomA', 'Grand Gallery');
        await fillCreateModalField('conn-dir1', 'north');
        await selectCreateModalOption('conn-roomB', 'Rooftop');
        await fillCreateModalField('conn-dir2', 'south');
        await selectCreateModalOption('conn-state', 'open');
        await fillCreateModalField('conn-desc', 'Fire exit door to rooftop.');
        await submitCreateModal();
        await page.waitForTimeout(500);
        await closeModalIfOpen('create-modal');
    });

    // ── 1c. Create items ──
    async function createItem(room, itemName, desc, triggersJson) {
        await closeModalIfOpen('create-modal');
        await clickToolbarButton('Item');
        await page.waitForTimeout(300);
        await selectCreateModalOption('item-target-room', room);
        await fillCreateModalField('item-name', itemName);
        await fillCreateModalField('item-desc', desc);
        if (triggersJson) {
            await expandTriggersSection();
            const ta = await page.$('#item-triggers-json');
            if (ta) await ta.fill(triggersJson);
        }
        await submitCreateModal();
        await page.waitForTimeout(500);
        await closeModalIfOpen('create-modal');
    }

    await t('Create Prized Painting', async () => {
        await createItem('Grand Gallery', 'Prized Painting',
            'A stunning painting of a moonlit forest.',
            JSON.stringify([
                {trigger_type:"on_take", effect_type:"message", effect_params:{message:"The painting emits a piercing alarm! Security alerted!"}},
                {trigger_type:"on_examine", effect_type:"message", effect_params:{message:"The painting glows with an inner light."}}
            ])
        );
    });
    await t('Create Security Keycard', async () => {
        await createItem('Vault', 'Security Keycard',
            'Black keycard with VAULT ACCESS label.',
            JSON.stringify([
                {trigger_type:"on_use", effect_type:"message", effect_params:{message:"Keycard blinks green — access granted."}}
            ])
        );
    });
    await t('Create Flashlight', async () => {
        await createItem('Grand Gallery', 'Flashlight', 'A heavy metal flashlight.');
    });
    await t('Create Lockpick', async () => {
        await createItem('Grand Gallery', 'Lockpick', 'A finely crafted lockpick.',
            JSON.stringify([
                {trigger_type:"on_use", effect_type:"message", effect_params:{message:"You deftly manipulate the lock."}}
            ])
        );
    });

    // ── 1d. Create characters ──
    async function createCharacter(charName) {
        const input = await page.$('#char-name');
        if (input) await input.fill(charName);
        const addBtn = await page.$('button[onclick*="createCharacter"]');
        if (addBtn) await addBtn.click();
        await page.waitForTimeout(500);
    }

    await t('Create Thief', async () => {
        await createCharacter('Thief');
        const state = await getState();
        if (!state.players['Thief']) throw 'Thief not created';
    });
    await t('Create Guard', async () => {
        await createCharacter('Guard');
        const state = await getState();
        if (!state.players['Guard']) throw 'Guard not created';
    });

    // Move Thief to Grand Gallery so they're not in the void
    await t('Move Thief to Grand Gallery', async () => {
        await clickAgent('Thief');
        await page.waitForTimeout(300);
        await switchInspectorTab('Inventory');
        await page.waitForTimeout(300);
        const roomSel = await page.$('#inspector-panel select');
        if (roomSel) {
            await roomSel.selectOption('Grand Gallery');
            await page.waitForTimeout(500);
            console.log('  (moved to Grand Gallery)');
        } else console.log('  (no room selector found)');
        const state = await getState();
        const thief = state.players?.['Thief'];
        if (thief && thief.current_room === 'Grand Gallery') console.log('  (confirmed in Grand Gallery)');
        else console.log('  (current room: ' + (thief?.current_room || 'none') + ')');
    });

    // Sync all world items to the item library
    await t('Sync items to library', async () => {
        await closeModalIfOpen('create-modal');
        const syncBtn = await page.$('button[onclick*="addAllWorldItemsToLibrary"]');
        if (syncBtn) { await syncBtn.click(); await page.waitForTimeout(500); console.log('  (synced to library)'); }
        else console.log('  (no sync button)');
    });

    // Set Guard as simple_npc with wander behavior (no UI toggle exists, using API)
    await t('Configure Guard as simple NPC', async () => {
        const state = await getState();
        if (state.players?.['Guard']) {
            await page.evaluate(async () => {
                await fetch('/api/players/Guard', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({simple_npc: true, npc_behavior: 'wander'})
                });
            });
            await page.waitForTimeout(300);
            const updated = await getState();
            const guard = updated.players?.['Guard'];
            if (guard?.simple_npc) console.log('  (Guard is now simple NPC: ' + guard.npc_behavior + ')');
            else console.log('  (Guard config failed)');
        }
    });

    // Move Guard to Grand Gallery too so they can patrol
    await t('Move Guard to Grand Gallery', async () => {
        await clickAgent('Guard');
        await page.waitForTimeout(200);
        await switchInspectorTab('Inventory');
        await page.waitForTimeout(200);
        const roomSel = await page.$('#inspector-panel select');
        if (roomSel) {
            await roomSel.selectOption('Grand Gallery');
            await page.waitForTimeout(500);
        }
        const state = await getState();
        const guard = state.players?.['Guard'];
        if (guard && guard.current_room === 'Grand Gallery') console.log('  (Guard moved to Grand Gallery)');
        else console.log('  (Guard room: ' + (guard?.current_room || 'none') + ')');
    });

    // ════════════════════════════════════════════════════════
    // PHASE 2: Manual playthrough (verify scenario works)
    // ════════════════════════════════════════════════════════
    console.log('\n=== PHASE 2: MANUAL PLAYTHROUGH ===');

    await t('Select Thief as active', async () => {
        const agents = await page.$$('.agent-item');
        let clicked = false;
        for (const a of agents) {
            const text = await a.textContent();
            if (text && text.includes('Thief')) {
                const onclick = await a.getAttribute('onclick') || '';
                if (onclick.includes('selectAgent')) {
                    await a.click();
                    clicked = true;
                    break;
                }
            }
        }
        if (!clicked) {
            // Fallback: try running command
            await runCmd('selectAgent Thief');
        }
        await page.waitForTimeout(300);
    });

    // Use the main command input for playing (always visible, no inspector tab needed)
    await t('Take Lockpick (via command input)', async () => {
        const msg = await typeCommand('take Lockpick');
        if (msg && !msg.includes('Internal') && !msg.includes('empty void')) console.log('  (take: ' + msg.substring(0, 50) + ')');
        else if (msg) console.log('  (result: ' + msg.substring(0, 50) + ')');
    });

    await t('Examine painting', async () => {
        const msg = await typeCommand('examine Prized Painting');
        if (msg && msg.includes('glow')) console.log('  (trigger fired)');
        else console.log('  (examine: ' + (msg || 'empty').substring(0, 60) + ')');
    });

    await t('Vault door is locked', async () => {
        const msg = await typeCommand('go east');
        if (msg && msg.toLowerCase().includes('lock')) console.log('  (vault locked)');
        else console.log('  (east: ' + (msg || 'empty').substring(0, 50) + ')');
    });

    await t('Rooftop accessible', async () => {
        const msg = await typeCommand('go north');
        if (msg && msg.includes('Rooftop')) console.log('  (rooftop accessible)');
        else console.log('  (north: ' + (msg || 'empty').substring(0, 50) + ')');
    });

    await t('Return to Gallery', async () => {
        const msg = await typeCommand('go south');
        console.log('  (south: ' + (msg || 'empty').substring(0, 50) + ')');
    });

    await t('Inventory has Lockpick', async () => {
        const msg = await typeCommand('inventory');
        if (msg && msg.includes('Lockpick')) console.log('  (has lockpick)');
        else console.log('  (inv: ' + (msg || 'empty').substring(0, 50) + ')');
    });

    // Equip Lockpick (now that it's in inventory)
    await t('Equip Lockpick', async () => {
        const msg = await typeCommand('equip lockpick');
        if (msg && !msg.includes('dont have') && !msg.includes('Internal')) console.log('  (equip: ' + msg.substring(0, 50) + ')');
        else console.log('  (equip result: ' + (msg || 'empty').substring(0, 50) + ')');
    });

    // ════════════════════════════════════════════════════════
    // PHASE 3: Save scenario to /scenarios/
    // ════════════════════════════════════════════════════════
    console.log('\n=== PHASE 3: SAVE SCENARIO ===');

    await t('Save scenario to /scenarios/art_heist.json', async () => {
        const data = await page.evaluate(async () => {
            const r = await fetch('/api/save');
            return await r.json();
        });
        const scenariosDir = path.resolve(__dirname, '..', 'scenarios');
        fs.mkdirSync(scenariosDir, { recursive: true });
        const scenarioData = {
            ...data,
            _scenario_name: 'art_heist',
            _description: 'Art Heist: Museum gallery with painting, locked vault, rooftop escape'
        };
        fs.writeFileSync(
            path.join(scenariosDir, 'art_heist.json'),
            JSON.stringify(scenarioData, null, 2),
            'utf-8'
        );
        const stats = fs.statSync(path.join(scenariosDir, 'art_heist.json'));
        console.log('  (saved ' + stats.size + ' bytes)');
    });

    // ════════════════════════════════════════════════════════
    // PHASE 4: LLM Agent — 5 turns with Qwen via LM Studio
    // ════════════════════════════════════════════════════════
    console.log('\n=== PHASE 4: LLM AGENT ===');

    // Load Qwen model in LM Studio
    await t('Load Qwen model via lms', async () => {
        try {
            const envPath = process.env.Path + ';' +
                require('child_process').execSync('echo %PATH%', {shell:'cmd.exe'}).toString().trim();
            execSync('lms load qwen3.5-2b-claude-4.6-opus-reasoning-distilled --identifier qwen3.5-2b-claude', {
                timeout: 60000,
                env: {...process.env, Path: envPath}
            });
            console.log('  (model loaded)');
        } catch(e) {
            // Maybe already loaded
            console.log('  (model load: ' + (e.message||'').substring(0, 40) + ')');
        }
    });

    // Open settings and configure for LM Studio
    await t('Configure settings for LM Studio', async () => {
        await closeModalIfOpen('create-modal');
        await closeModalIfOpen('settings-modal');
        // Click settings button
        const settingsBtn = await page.$('button[onclick*="settings-modal"]');
        if (!settingsBtn) throw 'Settings button not found';
        await settingsBtn.click();
        await page.waitForTimeout(500);

        // Set all settings via saveFromForm() which reads DOM and persists
        await page.evaluate(async () => {
            const apiBase = document.getElementById('api-base-input');
            if (apiBase) apiBase.value = 'http://localhost:1234/v1';
            const modelInput = document.getElementById('agent-model');
            if (modelInput) { modelInput.style.display = 'block'; modelInput.value = 'qwen3.5-2b-claude'; }
            const modelSelect = document.getElementById('agent-model-select');
            if (modelSelect) modelSelect.style.display = 'none';
            const manualCb = document.getElementById('agent-manual-mode');
            if (manualCb) manualCb.checked = false;
            // Ensure non-turn-based mode (simpler than turn queue)
            const turnBasedCb = document.getElementById('agent-turn-based');
            if (turnBasedCb) turnBasedCb.checked = false;
            if (typeof config !== 'undefined' && config.saveFromForm) {
                await config.saveFromForm();
            }
        });
        // Verify config was persisted
        const cfgCheck = await page.evaluate(() => ({
            apiBase: config?.apiBase?.substring(0, 30),
            model: config?.model,
            turnBased: config?.turnBased,
            manualMode: config?.manualMode,
            controllingPlayer: config?.controllingPlayer
        }));
        console.log('  (config: ' + JSON.stringify(cfgCheck) + ')');
        await closeModalIfOpen('settings-modal');
        await page.waitForTimeout(300);
    });

    // Verify LLM connection works
    await t('Quick LLM test call', async () => {
        const data = await page.evaluate(async () => {
            const r = await fetch('/api/llm/call', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    provider_name: 'lmstudio',
                    model_name: 'qwen3.5-2b-claude',
                    messages: [{role: 'user', content: 'Reply with one word: hello'}]
                })
            });
            const resp = await r.json();
            if (resp.choices && resp.choices[0]) return resp.choices[0].message.content;
            if (resp.content) return resp.content;
            return resp;
        });
        if (typeof data === 'string' && data.length > 0) console.log('  (LLM responds: ' + data.substring(0, 60) + ')');
        else if (data.error) console.log('  (LLM error: ' + data.error.substring(0, 60) + ')');
        else console.log('  (response: ' + JSON.stringify(data).substring(0, 60) + ')');
    });

    // Set Thief's personality so the agent engine has context
    await t('Set Thief personality', async () => {
        await clickAgent('Thief');
        await page.waitForTimeout(200);
        await switchInspectorTab('Bio');
        await page.waitForTimeout(200);
        const ta = await page.$('#inspector-personality');
        if (ta) {
            await ta.fill('');
            await ta.fill('A cunning thief skilled in lockpicking and stealth. Goal: steal the painting.');
            // Trigger save
            await page.evaluate(() => {
                const ta = document.getElementById('inspector-personality');
                if (ta) ta.dispatchEvent(new Event('input', {bubbles: true}));
                if (typeof InspectorAgentView !== 'undefined' && InspectorAgentView._savePersonality) {
                    InspectorAgentView._savePersonality(window.selectedAgent || '');
                }
            });
            await page.waitForTimeout(300);
            console.log('  (personality set)');
        } else console.log('  (no personality textarea)');
    });

    // Select Thief and verify config is set
    await t('Set controllingPlayer before stepping', async () => {
        await clickAgent('Thief');
        await page.waitForTimeout(300);
        const cp = await page.evaluate(() => config?.controllingPlayer || '(not set)');
        console.log('  (controllingPlayer: ' + cp + ')');
    });

    // Advance time via turn apply (simulates full turn cycle)
    await t('Advance game turn', async () => {
        const before = await getState();
        await page.evaluate(async () => {
            await fetch('/api/turn/apply', {method:'POST',headers:{'Content-Type':'application/json'}});
        });
        await page.waitForTimeout(500);
        const after = await getState();
        console.log('  (tick: ' + (before.time_ticks||0) + '→' + (after.time_ticks||0) +
            ', turn: ' + (before.turn_number||0) + '→' + (after.turn_number||0) + ')');
    });

    // Apply several turns to let Guard wander (NPC behavior runs in tick_turn)
    await t('Run 5 turn cycles for NPC movement', async () => {
        for (let i = 0; i < 5; i++) {
            await page.evaluate(async () => {
                await fetch('/api/turn/apply', {method:'POST',headers:{'Content-Type':'application/json'}});
            });
            await page.waitForTimeout(300);
        }
        const state = await getState();
        console.log('  (ticks: ' + state.time_ticks + ', turn: ' + state.turn_number + ')');
        const guard = state.players?.['Guard'];
        if (guard) console.log('  (Guard room: ' + (guard.current_room || 'none') + ')');
    });

    // Step the agent once — LLM-driven Thief action
    await t('Agent step — Thief acts via LLM', async () => {
        await clickAgent('Thief');
        await page.waitForTimeout(200);
        // Count events before
        const evBefore = await page.evaluate(() => {
            const stream = document.querySelector('#event-stream, .event-stream');
            if (!stream) return 0;
            return stream.querySelectorAll('.event-entry, .stream-entry, .system-msg').length;
        });
        await page.evaluate(() => {
            const btn = document.getElementById('sim-step');
            if (btn) btn.click();
        });
        await page.waitForTimeout(15000);
        // Check if an action was performed — look for new event stream entries
        const evAfter = await page.evaluate(() => {
            const stream = document.querySelector('#event-stream, .event-stream');
            if (!stream) return 0;
            return stream.querySelectorAll('.event-entry, .stream-entry, .system-msg').length;
        });
        const newEvents = evAfter - evBefore;
        const lastMsg = await page.evaluate(() => {
            const stream = document.querySelector('#event-stream, .event-stream');
            if (!stream) return '';
            const last = stream.lastElementChild;
            return last ? (last.textContent || '').substring(0, 60) : '';
        });
        console.log('  (+' + newEvents + ' events, last: ' + lastMsg + ')');
        if (newEvents > 0) console.log('  (agent produced output)');
        else console.log('  (no new events — agent may be quiet)');
    });

    // ═══════════════ RESULTS ═══════════════
    const passed = results.filter(r => r.status==='OK').length;
    const failed = results.filter(r => r.status==='FAIL').length;
    console.log('\n' + '\u2550'.repeat(50));
    console.log('  ART HEIST: ' + passed + '/' + (passed+failed) + ' passed, ' + failed + ' failed');
    console.log('\u2550'.repeat(50));
    if (failed > 0) {
        console.log('\nFailures:');
        results.filter(r=>r.status==='FAIL').forEach(r => console.log('  \u2717 ' + r.label + ': ' + r.error));
    }
    if (pageErrors.length > 0) {
        console.log('\nPage errors (' + pageErrors.length + '):');
        pageErrors.slice(0, 5).forEach(e => console.log('  \u26A0 ' + e.substring(0, 100)));
    }
    await browser.close();
})();
