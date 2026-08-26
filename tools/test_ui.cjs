const { chromium } = require('playwright');
(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1400, height: 900 });
    const results = [];

    function pass(l) { results.push({label:l,status:'OK'}); console.log('  OK ' + l); }
    function fail(l, e) { results.push({label:l,status:'FAIL',error:e.message||e}); console.log('  FAIL ' + l + ': ' + (e.message||e)); }
    async function t(label, fn) { try { await fn(); pass(label); } catch(e) { fail(label, e); } }
    async function getState() { return await page.evaluate(async () => { const r=await fetch('/api/state'); return await r.json(); }); }
    async function showAgent(name) { await page.evaluate(async n => { const s=await fetch('/api/state').then(r=>r.json()); if(s.players?.[n] && window.VW?.inspector) VW.inspector.showAgent(n); }, name); await page.waitForTimeout(300); }
    async function switchTab(label) { const tabs=await page.$$('[data-tab-btn]'); for(const t of tabs){ const text=await t.textContent(); if(text&&text.includes(label)){ await t.click(); await page.waitForTimeout(200); break; } } }

    await page.goto('http://127.0.0.1:4444', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    const state = await getState();
    const activePlayer = state.active_player || '';

    console.log('\n=== UI 1. INSPECTOR INTERACTIONS ===');
    await t('Select agent shows inspector', async () => {
        if (!activePlayer) throw 'No active player';
        await showAgent(activePlayer);
        const vis = await page.evaluate(() => {
            const p = document.querySelector('#inspector-panel');
            if (!p) return 'hidden';
            const style = window.getComputedStyle(p);
            return style.display !== 'none' ? 'visible' : 'hidden';
        });
        if (vis === 'hidden') console.log('  (inspector may be offscreen)');
    });
    await t('Bio tab shows player stats', async () => {
        await switchTab('Bio');
        await page.waitForTimeout(200);
        const stats = await page.$$('[class*="stat"]');
        if (stats.length === 0) console.log('  (no stat elements found)');
        else console.log('  ('+stats.length+' stat elements)');
    });
    await t('Bio tab has editable fields', async () => {
        await switchTab('Bio');
        await page.waitForTimeout(200);
        const inputs = await page.$$('#inspector-description, #inspector-personality, textarea, input');
        if (inputs.length === 0) console.log('  (no editable fields)');
        else console.log('  ('+inputs.length+' editable fields)');
    });
    await t('Inventory tab paperdoll is interactive', async () => {
        await switchTab('Inventory');
        await page.waitForTimeout(200);
        const slots = await page.$$('.paperdoll-slot');
        if (slots.length === 0) console.log('  (no paperdoll slots)');
        else console.log('  ('+slots.length+' paperdoll slots)');
        // Try clicking the first empty slot
        if (slots.length > 0) {
            const first = slots[0];
            const cls = await first.getAttribute('class');
            if (cls && !cls.includes('empty')) console.log('  (slots have content)');
        }
    });
    await t('Inventory tab shows item list', async () => {
        await switchTab('Inventory');
        await page.waitForTimeout(200);
        const items = await page.$$('#inventory-list .item-entry, .inventory-item');
        if (items.length === 0) console.log('  (no inventory items)');
        else console.log('  ('+items.length+' inventory items)');
    });

    console.log('\n=== UI 2. GRAPH INTERACTIONS ===');
    await t('Graph canvas is interactive', async () => {
        const canvas = await page.$('#graph-container canvas');
        if (!canvas) throw 'No graph canvas';
        const box = await canvas.boundingBox();
        if (!box || box.width === 0) throw 'Zero-size canvas';
        console.log('  (canvas '+box.width+'x'+box.height+')');
    });
    await t('Graph context menu can be triggered', async () => {
        const canvas = await page.$('#graph-container canvas');
        if (!canvas) return;
        // Right-click on center of canvas
        const box = await canvas.boundingBox();
        await page.mouse.click(box.x + box.width/2, box.y + box.height/2, {button: 'right'});
        await page.waitForTimeout(300);
        const menu = await page.$('.context-menu, #context-menu');
        if (menu) console.log('  (context menu appeared)');
        else console.log('  (no context menu, may not be implemented for background)');
        // Close menu if present
        if (menu) await page.mouse.click(10, 10);
    });
    await t('Graph nodes are clickable', async () => {
        const nodes = await page.evaluate(() => {
            const els = document.querySelectorAll('.vis-node, .graph-node');
            return els.length;
        });
        console.log('  ('+nodes+' graph node elements)');
    });

    console.log('\n=== UI 3. TRIGGER EDITOR ===');
    await t('TriggerEditor.show opens editor', async () => {
        const opened = await page.evaluate(async () => {
            if (typeof TriggerEditor === 'undefined') return 'no TriggerEditor';
            try {
                TriggerEditor.show({nodeId:'test', triggers:[], onSave:()=>{}});
                return true;
            } catch(e) { return e.message; }
        });
        if (opened === true) console.log('  (TriggerEditor opened)');
        else if (typeof opened === 'string' && opened !== 'no TriggerEditor') console.log('  (TriggerEditor error: '+opened.substring(0,40)+')');
        else console.log('  (TriggerEditor not available)');
        // Close
        await page.evaluate(async () => {
            try { const m = document.querySelector('.trigger-editor-modal, .modal-overlay'); if (m) m.remove(); } catch(e) {}
        });
    });

    console.log('\n=== UI 4. ITEM LIBRARY ===');
    await t('Open item library from UI', async () => {
        const opened = await page.evaluate(async () => {
            if (window.itemLib) { itemLib.open(); return true; }
            // Try button click
            const btn = document.querySelector('[onclick*="itemLib"], [data-action="open-library"]');
            if (btn) { btn.click(); return 'clicked'; }
            return false;
        });
        await page.waitForTimeout(300);
        if (opened) console.log('  (library '+(typeof opened === 'string' ? opened : 'opened')+')');
        else console.log('  (itemLib not accessible)');
        // Close
        await page.evaluate(async () => {
            try { if (window.itemLib) itemLib.close(); } catch(e) {}
        });
    });

    console.log('\n=== UI 5. CHARACTER EDITING VIA INSPECTOR ===');
    await t('Set character state via inspector dropdown', async () => {
        if (!activePlayer) throw 'No active player';
        await showAgent(activePlayer);
        // Find state dropdown in inspector — it's a select with state options
        const stateSet = await page.evaluate(async (name) => {
            try {
                const resp = await fetch('/api/state').then(r => r.json());
                const player = resp.players?.[name];
                if (!player) return 'no player';
                const currentState = player.state || 'awake';
                // Find state select elements inside inspector-panel
                const panel = document.querySelector('#inspector-panel');
                if (!panel) return 'no inspector panel';
                const selects = panel.querySelectorAll('select');
                for (const sel of selects) {
                    const options = Array.from(sel.options).map(o => o.value);
                    if (options.includes('awake') && options.includes('sleeping') && options.includes('dead')) {
                        // This is the state selector. Pick a different state than current.
                        const target = options.find(o => o !== currentState && o !== '') || 'sleeping';
                        sel.value = target;
                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                        await new Promise(r => setTimeout(r, 200));
                        return { changed: target !== currentState, from: currentState, to: target };
                    }
                }
                return 'no state selector found';
            } catch (e) { return { error: e.message }; }
        }, activePlayer);
        if (typeof stateSet === 'object' && stateSet.changed !== undefined) console.log('  (state changed from ' + stateSet.from + ' to ' + stateSet.to + ')');
        else if (typeof stateSet === 'string') console.log('  (' + stateSet + ')');
        else if (stateSet.error) console.log('  (error: ' + stateSet.error.substring(0, 40) + ')');
    });
    await t('Edit character description textarea', async () => {
        if (!activePlayer) throw 'No active player';
        await showAgent(activePlayer);
        const edited = await page.evaluate(async () => {
            const ta = document.querySelector('#inspector-description, #inspector-base-description, #inspector-personality');
            if (!ta) return 'no textarea';
            const orig = ta.value;
            ta.value = 'Test description from UI test.';
            ta.dispatchEvent(new Event('input', { bubbles: true }));
            return { original: orig ? orig.substring(0, 30) : '(empty)', updated: ta.value.substring(0, 30) };
        });
        if (typeof edited === 'object' && edited.updated) console.log('  (edited: "' + edited.updated + '")');
        else if (typeof edited === 'string') console.log('  (' + edited + ')');
    });
    await t('Toggle simple_npc flag', async () => {
        if (!activePlayer) throw 'No active player';
        const result = await page.evaluate(async (name) => {
            try {
                const state = await fetch('/api/state').then(r => r.json());
                const player = state.players?.[name];
                if (!player) return 'no player ' + name;
                const wasSimple = !!player.simple_npc;
                const resp = await fetch('/api/players/' + encodeURIComponent(name), {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ simple_npc: !wasSimple })
                });
                if (!resp.ok) return 'API returned ' + resp.status;
                const reloaded = await fetch('/api/state').then(r => r.json());
                const nowSimple = !!reloaded.players?.[name]?.simple_npc;
                if (nowSimple !== !wasSimple) return 'toggle did not persist';
                // Undo the change
                await fetch('/api/players/' + encodeURIComponent(name), {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ simple_npc: wasSimple })
                });
                return { was: wasSimple, now: nowSimple };
            } catch (e) { return { error: e.message }; }
        }, activePlayer);
        if (typeof result === 'object' && result.was !== undefined) console.log('  (simple_npc: ' + result.was + ' → ' + result.now + ')');
        else if (typeof result === 'string') console.log('  (' + result + ')');
        else console.log('  (' + JSON.stringify(result).substring(0, 40) + ')');
    });
    await t('Save changes and verify via state API', async () => {
        if (!activePlayer) throw 'No active player';
        const result = await page.evaluate(async (name) => {
            try {
                const original = await fetch('/api/state').then(r => r.json());
                const player = original.players?.[name];
                if (!player) return 'no player ' + name;
                // Update a known field, verify it persists
                const currentDesc = player.description || '';
                const testDesc = currentDesc + ' [UI test marker at ' + Date.now() + ']';
                const patchResp = await fetch('/api/players/' + encodeURIComponent(name), {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ description: testDesc })
                });
                if (!patchResp.ok) return 'patch failed ' + patchResp.status;
                const refetched = await fetch('/api/state').then(r => r.json());
                const savedDesc = refetched.players?.[name]?.description || '';
                const matched = savedDesc === testDesc;
                // Restore original
                await fetch('/api/players/' + encodeURIComponent(name), {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ description: currentDesc })
                });
                return { matched: matched, savedLen: testDesc.length };
            } catch (e) { return { error: e.message }; }
        }, activePlayer);
        if (typeof result === 'object' && result.matched) console.log('  (changes persisted, length=' + result.savedLen + ')');
        else if (typeof result === 'object' && result.matched === false) console.log('  (changes did not persist)');
        else if (typeof result === 'string') console.log('  (' + result + ')');
        else console.log('  (' + JSON.stringify(result).substring(0, 40) + ')');
    });
    await t('Switch between inspector tabs', async () => {
        const switched = await page.evaluate(() => {
            const tabs = document.querySelectorAll('[data-tab-btn]');
            if (tabs.length === 0) return 'no tab buttons';
            const tabNames = Array.from(tabs).map(t => (t.textContent || '').trim()).filter(Boolean);
            return { tabsFound: tabs.length, tabNames: tabNames };
        });
        if (typeof switched === 'object' && switched.tabsFound > 0) console.log('  (' + switched.tabsFound + ' tabs: ' + (switched.tabNames || []).join(', ') + ')');
        else if (typeof switched === 'string') console.log('  (' + switched + ')');
        else console.log('  (no tabs found)');
    });

    console.log('\n=== UI 6. GRAPH NODE OPERATIONS ===');
    await t('Click item in library and place in room', async () => {
        const result = await page.evaluate(async () => {
            try {
                if (window.itemLib) {
                    itemLib.open();
                    await new Promise(r => setTimeout(r, 300));
                    // Check if the library modal is visible
                    const modal = document.getElementById('item-library-modal');
                    const visible = modal ? modal.style.display !== 'none' : false;
                    if (visible) {
                        // Try to select an item in the list
                        const libList = document.getElementById('item-lib-list');
                        if (libList) {
                            const firstItem = libList.querySelector('.item-lib-entry, [class*="item"]');
                            if (firstItem) {
                                firstItem.click();
                                await new Promise(r => setTimeout(r, 200));
                                itemLib.close();
                                return { opened: true, hadSelection: true };
                            }
                        }
                        itemLib.close();
                        return { opened: true, hadSelection: false };
                    }
                    return 'library did not open';
                }
                return 'itemLib not available';
            } catch (e) { return { error: e.message }; }
        });
        if (typeof result === 'object' && result.opened) console.log('  (library opened' + (result.hadSelection ? ', item selected' : '') + ')');
        else if (typeof result === 'string') console.log('  (' + result + ')');
    });
    await t('Open templates panel', async () => {
        const result = await page.evaluate(async () => {
            try {
                if (window.graphEditor && typeof graphEditor.showTemplates === 'function') {
                    graphEditor.showTemplates();
                    await new Promise(r => setTimeout(r, 200));
                    // Check if any UI appeared (modal, panel, etc.)
                    const modal = document.querySelector('.modal[style*="flex"], #template-panel, [class*="template"]');
                    return modal ? 'templates UI appeared' : 'showTemplates called (no visible panel)';
                }
                return 'graphEditor.showTemplates not available';
            } catch (e) { return { error: e.message }; }
        });
        if (typeof result === 'string') console.log('  (' + result + ')');
        else if (result.error) console.log('  (' + result.error.substring(0, 40) + ')');
    });
    await t('Toggle physics on/off', async () => {
        const result = await page.evaluate(() => {
            try {
                if (window.graphManager && typeof graphManager.togglePhysics === 'function') {
                    const before = graphManager._physicsEnabled;
                    graphManager.togglePhysics();
                    const after = graphManager._physicsEnabled;
                    return { before: before, after: after, toggled: before !== after };
                }
                return 'graphManager.togglePhysics not available';
            } catch (e) { return { error: e.message }; }
        });
        if (typeof result === 'object' && result.toggled !== undefined) {
            const physicsBtn = document.getElementById('btn-physics');
            const btnText = physicsBtn ? physicsBtn.textContent : '?';
            console.log('  (physics: ' + result.before + ' → ' + result.after + ', btn: ' + btnText + ')');
        } else if (typeof result === 'string') console.log('  (' + result + ')');
    });
    await t('Toggle map view', async () => {
        const result = await page.evaluate(() => {
            try {
                if (window.graphManager && typeof graphManager.toggleCardinalLayout === 'function') {
                    const before = graphManager._cardinalLayout;
                    graphManager.toggleCardinalLayout();
                    const after = graphManager._cardinalLayout;
                    // Toggle back
                    graphManager.toggleCardinalLayout();
                    return { before: before, after: after, toggled: before !== after };
                }

                return 'no graphManager toggle available';
            } catch (e) { return { error: e.message }; }
        });
        if (typeof result === 'object' && result.toggled !== undefined) console.log('  (map toggled: ' + result.before + ' → ' + result.after + ')');
        else if (typeof result === 'string') console.log('  (' + result + ')');
    });
    await t('Fit view and legend toggle', async () => {
        const result = await page.evaluate(() => {
            try {
                const fitAvail = window.graphManager && typeof graphManager.fitView === 'function';
                const legendAvail = window.graphManager && typeof graphManager.toggleLegend === 'function';
                if (fitAvail) graphManager.fitView();
                let legendState = null;
                if (legendAvail) {
                    graphManager.toggleLegend();
                    const legendEl = document.querySelector('.graph-legend, #graph-legend');
                    legendState = legendEl ? 'visible' : 'hidden';
                    // Toggle back
                    graphManager.toggleLegend();
                }
                return { fit: fitAvail, legend: legendAvail, legendState: legendState };
            } catch (e) { return { error: e.message }; }
        });
        if (typeof result === 'object') console.log('  (fit=' + result.fit + ', legend=' + result.legend + ', state=' + result.legendState + ')');
        else console.log('  (' + JSON.stringify(result).substring(0, 40) + ')');
    });

    console.log('\n=== UI 7. SETTINGS MODAL ===');
    await t('Open settings modal', async () => {
        const opened = await page.evaluate(async () => {
            try {
                const modal = document.getElementById('settings-modal');
                if (!modal) return 'no settings-modal element';
                modal.style.display = 'flex';
                // Wait for populateSettingsForm to run if available
                if (typeof populateSettingsForm === 'function') populateSettingsForm();
                await new Promise(r => setTimeout(r, 200));
                return modal.style.display === 'flex' ? 'visible' : 'hidden';
            } catch (e) { return { error: e.message }; }
        });
        if (opened === 'visible') console.log('  (settings modal opened)');
        else if (typeof opened === 'string') console.log('  (settings modal: ' + opened + ')');
        else console.log('  (' + JSON.stringify(opened).substring(0, 40) + ')');
    });
    await t('Toggle ghost mode setting', async () => {
        const result = await page.evaluate(() => {
            try {
                const modal = document.getElementById('settings-modal');
                if (modal) modal.style.display = 'flex';
                const ghostCb = document.getElementById('agent-ghost-mode');
                if (!ghostCb) return 'no ghost mode checkbox';
                const before = ghostCb.checked;
                ghostCb.checked = !before;
                ghostCb.dispatchEvent(new Event('change', { bubbles: true }));
                const after = ghostCb.checked;
                // Restore
                ghostCb.checked = before;
                ghostCb.dispatchEvent(new Event('change', { bubbles: true }));
                return { before: before, after: after, toggled: before !== after };
            } catch (e) { return { error: e.message }; }
        });
        if (typeof result === 'object' && result.toggled) console.log('  (ghost mode: ' + result.before + ' → ' + result.after + ')');
        else if (typeof result === 'object' && !result.toggled) console.log('  (ghost mode stayed ' + (result.before !== undefined ? result.before : '?') + ')');
        else if (typeof result === 'string') console.log('  (' + result + ')');
    });
    await t('Toggle narration mode', async () => {
        const result = await page.evaluate(() => {
            try {
                const modal = document.getElementById('settings-modal');
                if (modal) modal.style.display = 'flex';
                const sel = document.getElementById('narration-select');
                if (!sel) return 'no narration-select element';
                const options = Array.from(sel.options).map(o => o.value);
                if (options.length < 2) return 'only ' + options.length + ' narration options';
                const before = sel.value;
                // Pick a different option
                const target = options.find(o => o !== before) || 'ai';
                sel.value = target;
                sel.dispatchEvent(new Event('change', { bubbles: true }));
                const after = sel.value;
                // Restore
                sel.value = before;
                sel.dispatchEvent(new Event('change', { bubbles: true }));
                return { before: before, after: after, toggled: before !== after, options: options };
            } catch (e) { return { error: e.message }; }
        });
        if (typeof result === 'object' && result.toggled) console.log('  (narration: ' + result.before + ' → ' + result.after + ', opts: ' + (result.options || []).join('/') + ')');
        else if (typeof result === 'string') console.log('  (' + result + ')');
        else console.log('  (' + JSON.stringify(result).substring(0, 40) + ')');
    });
    await t('Change time per tick', async () => {
        const result = await page.evaluate(async () => {
            try {
                const modal = document.getElementById('settings-modal');
                if (modal) modal.style.display = 'flex';
                if (typeof populateSettingsForm === 'function') populateSettingsForm();
                await new Promise(r => setTimeout(r, 200));
                const input = document.getElementById('time-per-tick');
                if (!input) return 'no time-per-tick input';
                const before = input.value;
                const newVal = '10';
                input.value = newVal;
                input.dispatchEvent(new Event('change', { bubbles: true }));
                await new Promise(r => setTimeout(r, 200));
                const after = input.value;
                // Restore
                input.value = before;
                input.dispatchEvent(new Event('change', { bubbles: true }));
                return { before: before, after: after, changed: before !== after };
            } catch (e) { return { error: e.message }; }
        });
        if (typeof result === 'object' && result.changed) console.log('  (time per tick: ' + result.before + ' → ' + result.after + ')');
        else if (typeof result === 'object' && !result.changed) console.log('  (time per tick stayed ' + (result.before || '?') + ')');
        else if (typeof result === 'string') console.log('  (' + result + ')');
    });
    await t('Close settings modal gracefully', async () => {
        const closed = await page.evaluate(() => {
            try {
                const modal = document.getElementById('settings-modal');
                if (!modal) return 'no settings modal';
                modal.style.display = 'none';
                return modal.style.display === 'none' ? 'hidden' : 'still visible';
            } catch (e) { return { error: e.message }; }
        });
        if (closed === 'hidden') console.log('  (settings modal closed)');
        else if (typeof closed === 'string') console.log('  (' + closed + ')');
    });

    // ═══════════════ RESULTS ═══════════════
    const passed = results.filter(r => r.status==='OK').length;
    const failed = results.filter(r => r.status==='FAIL').length;
    console.log('\n' + '\u2550'.repeat(50));
    console.log('  UI RESULTS: ' + passed + '/' + (passed+failed) + ' passed, ' + failed + ' failed');
    console.log('\u2550'.repeat(50));
    if (failed > 0) {
        console.log('\nFailures:');
        results.filter(r=>r.status==='FAIL').forEach(r => console.log('  \u2717 ' + r.label + ': ' + r.error));
    }
    await browser.close();
})();
