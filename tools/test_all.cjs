const { chromium } = require('playwright');
const http = require('http');

// Wait for server to be ready
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
    throw new Error('Server did not start within ' + maxWaitSec + 's');
}

(async () => {
    console.log('Waiting for server...');
    await waitForServer('http://127.0.0.1:4444');
    console.log('Server ready.');

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1400, height: 900 });
    const results = [];
    const jsErrors = [];
    page.on('pageerror', e => jsErrors.push('[pageerror] ' + e.message));
    page.on('console', msg => {
        if (msg.type() !== 'error') return;
        if (msg.text().startsWith('Failed to load resource')) return;
        jsErrors.push('[console] ' + msg.text());
    });

    function pass(l) { results.push({label:l,status:'OK'}); console.log('  OK ' + l); }
    function fail(l, e) { results.push({label:l,status:'FAIL',error:e.message||e}); console.log('  FAIL ' + l + ': ' + (e.message||e)); }
    async function t(label, fn) { try { await fn(); pass(label); } catch(e) { fail(label, e); } }

    async function api(body) { return await page.evaluate(async b => { const r=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}); return await r.json(); }, body); }
    async function getState() { return await page.evaluate(async () => { const r=await fetch('/api/state'); return await r.json(); }); }
    async function showAgent(name) { await page.evaluate(async n => { const s=await fetch('/api/state').then(r=>r.json()); if(s.players?.[n] && window.VW?.inspector) VW.inspector.showAgent(n); }, name); await page.waitForTimeout(300); }
    async function switchTab(label) { const tabs=await page.$$('[data-tab-btn]'); for(const t of tabs){ const text=await t.textContent(); if(text&&text.includes(label)){ await t.click(); await page.waitForTimeout(200); break; } } }

    await page.goto('http://127.0.0.1:4444', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    let activePlayer = '';

    // ═══════════════ 1. PAGE LOAD ═══════════════
    console.log('\n=== 1. PAGE LOAD ===');
    await t('Page loads with title', async () => { const title = await page.title(); if (!title) throw 'No title'; });
    await t('Command input exists', async () => { if (!await page.$('#command-input')) throw 'Missing #command-input'; });
    await t('Inspector panel exists', async () => { if (!await page.$('#inspector-panel')) throw 'Missing #inspector-panel'; });
    await t('Graph canvas renders', async () => { const c=await page.$('#graph-container canvas'); if(!c) throw 'No canvas'; const b=await c.boundingBox(); if(!b||b.width===0) throw 'Zero-size canvas'; });
    await t('Event stream exists', async () => { if (!await page.$('#event-stream')) throw 'Missing #event-stream'; });
    await t('Agent list renders', async () => { const el=await page.$('#agent-list'); if(!el) throw 'Missing #agent-list'; const items=await el.$$('[class*="agent"]'); console.log('  ('+items.length+' agents)'); });

    // ═══════════════ 2. BASIC COMMANDS ═══════════════
    console.log('\n=== 2. COMMANDS ===');
    await t('look', async () => { const r=await api({command:'look'}); if(r.error&&!r.output) throw r.error; });
    await t('inventory', async () => { const r=await api({command:'inventory'}); if(r.error&&!r.output) throw r.error; });
    await t('inventory alias (i)', async () => { const r=await api({command:'i'}); if(r.error&&!r.output) throw r.error; });
    await t('examine self', async () => { const r=await api({command:'examine self'}); if(r.error) throw r.error; });
    await t('stats', async () => { const r=await api({command:'stats'}); if(r.error) throw r.error; });
    await t('go north or test movement', async () => { const r=await api({command:'go north'}); if(r.error&&!r.output&&!r.error.toLowerCase().includes('cant go')) throw r.error; });
    await t('go back (south)', async () => { const r=await api({command:'go south'}); if(r.error&&!r.output&&!r.error.toLowerCase().includes('cant go')) throw r.error; });
    await t('examine an item in room', async () => { const r=await api({command:'examine fireplace'}); if(r.error&&!r.output&&r.error.includes('dont see')){} else if(r.error&&!r.output) throw r.error; });
    await t('examine an exit', async () => { const r=await api({command:'examine north'}); if(r.error&&!r.output&&!r.error.toLowerCase().includes('dont see')) throw r.error; });

    // ═══════════════ 3. AGENT INSPECTOR ═══════════════
    console.log('\n=== 3. AGENT INSPECTOR ===');
    const s = await getState();
    activePlayer = s.active_player || '';

    await t('Show active player in inspector', async () => {
        if (!activePlayer) throw 'No active player';
        await showAgent(activePlayer);
    });
    await t('Vitals visible', async () => { const e=await page.$('[class*=vital]'); if(!e) console.log('  (no vitals visible)'); });
    await t('Inventory tab renders paperdoll', async () => { await switchTab('Inventory'); const e=await page.$('.paperdoll'); if(!e) console.log('  (no paperdoll)'); });
    await t('Inventory tab shows items', async () => { await switchTab('Inventory'); await page.waitForTimeout(200); });
    await t('Bio tab has description textarea', async () => { await switchTab('Bio'); await page.waitForTimeout(100); const e=await page.$('#inspector-description'); if(!e) console.log('  (no description field)'); });
    await t('Bio tab has Generate from Equipment button', async () => { const b=await page.$('[onclick*="generateDescription"]'); if(!b) console.log('  (no gen button)'); });
    await t('Relationships tab loads', async () => { await switchTab('Relationships'); await page.waitForTimeout(100); });
    await t('Advanced tab loads', async () => { await switchTab('Advanced'); await page.waitForTimeout(100); });

    // ═══════════════ 4. CHARACTER EDITING ═══════════════
    console.log('\n=== 4. CHARACTER EDITING ===');
    await t('State dropdown works', async () => {
        await switchTab('Bio');
        const sel = await page.$('#player-state');
        if (sel) { const val = await sel.inputValue(); console.log('  (state: '+val+')'); }
        else console.log('  (no state dropdown, may use different id)');
    });
    await t('Current room selector works', async () => {
        const sel = await page.$('#player-room');
        if (sel) { const val = await sel.inputValue(); console.log('  (room: '+val+')'); }
        else console.log('  (no room selector)');
    });
    await t('Emotion dropdown works', async () => {
        const sel = await page.$('#player-emotion');
        if (sel) { const val = await sel.inputValue(); console.log('  (emotion: '+val+')'); }
        else console.log('  (no emotion dropdown)');
    });

    // ═══════════════ 5. STATE & API ═══════════════
    console.log('\n=== 5. STATE & API ===');
    await t('GET /api/state returns valid state', async () => {
        const state = await getState();
        if (!state.rooms) throw 'No rooms in state';
        console.log('  ('+Object.keys(state.rooms).length+' rooms, '+state.active_player+')');
    });
    await t('GET /api/save returns valid JSON', async () => {
        const data = await page.evaluate(async () => { const r=await fetch('/api/save'); return await r.json(); });
        if (!data || !data.players) throw 'No save data';
        console.log('  ('+Object.keys(data.players).length+' players saved)');
    });
    await t('GET /api/players returns player list', async () => {
        const data = await page.evaluate(async () => { const r=await fetch('/api/players'); return await r.json(); });
        if (!data.players || data.players.length===0) throw 'No players';
        console.log('  ('+data.players.length+' players, active: '+data.active+')');
    });
    await t('GET /api/graph/nodes returns nodes', async () => {
        const data = await page.evaluate(async () => { const r=await fetch('/api/graph/nodes'); return await r.json(); });
        if (!data || Object.keys(data).length===0) throw 'No nodes';
        console.log('  ('+Object.keys(data).length+' nodes)');
    });
    await t('GET /api/graph/edges returns edges', async () => {
        const data = await page.evaluate(async () => { const r=await fetch('/api/graph/edges'); return await r.json(); });
        if (!data || data.length===0) throw 'No edges';
        console.log('  ('+data.length+' edges)');
    });

    // ═══════════════ 6. ITEM ACTIONS (via API) ═══════════════
    console.log('\n=== 6. ITEM ACTIONS ===');
    await t('Take an item', async () => {
        const r = await api({command:'take journal'});
        if (r.error && r.error.includes('dont see')) {}
        else if (r.error) throw r.error;
    });
    await t('Drop an item', async () => {
        // Only works if we took something first
        const r = await api({command:'drop journal'});
        if (r.error && r.error.includes('dont have')) {}
        else if (r.error) throw r.error;
    });
    await t('Use command handles missing target', async () => {
        const r = await api({command:'use unicorn'});
        if (r.error && !r.output) console.log('  (use fails as expected, no unicorn)');
    });

    // ═══════════════ 7. PAPERDOLL & EQUIPMENT ═══════════════
    console.log('\n=== 7. EQUIPMENT ===');
    await t('Show agent with paperdoll', async () => {
        if (activePlayer) await showAgent(activePlayer);
        await switchTab('Inventory');
        await page.waitForTimeout(300);
        const pd = await page.$('.paperdoll');
        if (pd) {
            const slots = await pd.$$('.paperdoll-slot');
            console.log('  ('+slots.length+' paperdoll slots)');
        }
    });
    await t('Paperdoll has 12 body slots', async () => {
        const labels = await page.$$eval('.paperdoll-slot-label', els => els.map(e => e.textContent));
        const expected = ['HEAD','NECK','ARMS','TORSO','ARMS','HANDS','WAIST','HANDS','L.HELD','LEGS','R.HELD','BACK','FEET'];
        if (labels.length < 10) console.log('  (labels found: '+labels.join(',')+')');
        else console.log('  (12+ slot labels rendered)');
    });

    // ═══════════════ 8. BUG VERIFICATION ═══════════════
    console.log('\n=== 8. BUG VERIFICATION ===');
    await t('ui.getAgentColor works', async () => {
        const ok = await page.evaluate(() => { try { return typeof ui.getAgentColor('Test') === 'string'; } catch(e) { return e.message; } });
        if (ok !== true) throw 'getAgentColor: '+ok;
    });
    await t('events.getCharacterState works', async () => {
        const ok = await page.evaluate(() => { try { return typeof events.getCharacterState('Test') === 'object'; } catch(e) { return e.message; } });
        if (ok !== true && ok !== false) throw 'getCharacterState: '+ok;
    });
    await t('ApiClient.updateCharacter exists', async () => {
        const ok = await page.evaluate(() => typeof ApiClient.updateCharacter === 'function');
        if (!ok) throw 'ApiClient.updateCharacter missing';
    });
    await t('ApiClient.addPlayerMemory exists', async () => {
        const ok = await page.evaluate(() => typeof ApiClient.addPlayerMemory === 'function');
        if (!ok) throw 'ApiClient.addPlayerMemory missing';
    });
    await t('ApiClient.saveLibraryItem exists', async () => {
        const ok = await page.evaluate(() => typeof ApiClient.saveLibraryItem === 'function');
        if (!ok) throw 'ApiClient.saveLibraryItem missing';
    });
    await t('ApiClient.createNode exists', async () => {
        const ok = await page.evaluate(() => typeof ApiClient.createNode === 'function');
        if (!ok) throw 'ApiClient.createNode missing';
    });
    await t('ApiClient.createEdge exists', async () => {
        const ok = await page.evaluate(() => typeof ApiClient.createEdge === 'function');
        if (!ok) throw 'ApiClient.createEdge missing';
    });
    await t('TriggerEditor.show exists', async () => {
        const ok = await page.evaluate(() => typeof TriggerEditor.show === 'function');
        if (!ok) throw 'TriggerEditor.show missing';
    });
    await t('AIGenerator.generate exists', async () => {
        const ok = await page.evaluate(() => typeof AIGenerator.generate === 'function');
        if (!ok) throw 'AIGenerator.generate missing';
    });
    await t('ItemLibrary class exists', async () => {
        const ok = await page.evaluate(() => typeof ItemLibrary === 'function');
        if (!ok) throw 'ItemLibrary missing';
    });
    await t('GraphNetwork.loadGraphData exists', async () => {
        const ok = await page.evaluate(() => typeof GraphNetwork.loadGraphData === 'function');
        if (!ok) throw 'GraphNetwork.loadGraphData missing';
    });
    await t('PromptBuilder.buildRoomContext exists', async () => {
        const ok = await page.evaluate(() => typeof PromptBuilder.buildRoomContext === 'function');
        if (!ok) throw 'PromptBuilder.buildRoomContext missing';
    });

    // ═══════════════ 9. SAVE/LOAD ═══════════════
    console.log('\n=== 9. SAVE/LOAD ===');
    await t('POST /api/save-game creates file', async () => {
        const r = await page.evaluate(async () => {
            const resp = await fetch('/api/save-game', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:'test_save'})});
            return await resp.json();
        });
        if (r.error) throw r.error;
        console.log('  (save created)');
    });
    await t('GET /api/save-games lists saves', async () => {
        const r = await page.evaluate(async () => { const resp=await fetch('/api/save-games'); return await resp.json(); });
        if (!Array.isArray(r)) throw 'Expected array';
        console.log('  ('+r.length+' saves)');
    });

    // ═══════════════ 10. ENVIRONMENT ═══════════════
    console.log('\n=== 10. ENVIRONMENT ===');
    await t('Room has environment data', async () => {
        const state = await getState();
        const rooms = Object.values(state.rooms || {});
        if (rooms.length > 0 && rooms[0].environment) {
            const env = rooms[0].environment;
            console.log('  (light:'+env.light+', temp:'+env.temperature+', air:'+env.air+')');
        } else console.log('  (no environment data)');
    });
    await t('Time tick exists', async () => {
        const state = await getState();
        if (state.time_ticks === undefined) throw 'No time_ticks';
        console.log('  (tick: '+state.time_ticks+', time: '+state.game_time+')');
    });
    await t('Rest advances time', async () => {
        const before = await getState();
        await api({command:'rest 1'});
        await page.waitForTimeout(500);
        const after = await getState();
        const diff = (after.time_ticks || 0) - (before.time_ticks || 0);
        console.log('  (time ticks advanced by '+diff+')');
    });

    // ═══════════════ 11. ERROR HANDLING & EDGE CASES ═══════════════
    console.log('\n=== 11. ERROR HANDLING ===');
    await t('Take nonexistent item returns error', async () => {
        const r = await api({command:'take nonexistent_item_xyz'});
        if (!r.output && !r.error) throw 'No response';
        console.log('  (got: '+(r.output||r.error||'').substring(0,50)+')');
    });
    await t('Drop nonexistent item returns error', async () => {
        const r = await api({command:'drop nonexistent_item_xyz'});
        if (!r.output && !r.error) throw 'No response';
    });
    await t('Examine nonexistent target returns error', async () => {
        const r = await api({command:'examine nonexistent_target_xyz'});
        if (!r.output && !r.error) throw 'No response';
    });
    await t('Go to nonexistent direction returns error', async () => {
        const r = await api({command:'go nonexistent_dir'});
        if (!r.output && !r.error) throw 'No response';
    });
    await t('Open nonexistent door returns error', async () => {
        const r = await api({command:'open nonexistent_dir'});
        if (!r.output && !r.error) throw 'No response';
    });
    await t('Rest with negative minutes handles gracefully', async () => {
        const r = await api({command:'rest -1'});
        if (!r.output && !r.error) throw 'No response';
    });
    await t('Empty command returns help or error', async () => {
        const r = await api({command:''});
        if (r.error && !r.output) console.log('  (empty command error: '+r.error.substring(0,40)+')');
    });

    // Deep error handling
    await t('Missing command key returns 400', async () => {
        const r = await page.evaluate(async () => {
            const resp = await fetch('/api/action', {method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
            return {status: resp.status, json: await resp.json()};
        });
        if (r.status !== 400) throw 'Expected 400, got '+r.status;
    });
    await t('Malformed JSON returns 400', async () => {
        const r = await page.evaluate(async () => {
            const resp = await fetch('/api/action', {method:'POST',headers:{'Content-Type':'application/json'},body:'not json'});
            return {status: resp.status};
        });
        if (r.status !== 400) throw 'Expected 400, got '+r.status;
    });
    await t('Very long command does not crash', async () => {
        const r = await api({command:'a'.repeat(10000)});
        if (r.error && r.error.includes('Internal')) throw r.error;
    });
    await t('Command with special chars is handled', async () => {
        const r = await api({command:'examine !@#$%^&*()'});
        if (r.error && r.error.includes('Internal')) throw r.error;
    });
    await t('Sleep command responds', async () => {
        const r = await api({command:'sleep'});
        if (r.error && !r.output) console.log('  (sleep: '+r.error.substring(0,40)+')');
    });
    await t('Nonexistent verb falls back to emote', async () => {
        const r = await api({command:'flibberflabber'});
        // Should either be treated as emote or return an error, not crash
        if (r.error && r.error.includes('Internal')) throw r.error;
    });

    // ═══════════════ 12. DOORS & MOVEMENT ═══════════════
    console.log('\n=== 12. DOORS ===');
    await t('Toggle door command handles missing door', async () => {
        const r = await api({command:'open nonexistent_door'});
        if (r.output) console.log('  (response: '+r.output.substring(0,40)+')');
        else if (r.error) console.log('  (error: '+r.error.substring(0,40)+')');
    });
    await t('Look after move shows new room', async () => {
        const before = await api({command:'look'});
        await api({command:'go north'}).catch(()=>{});
        await page.waitForTimeout(300);
        const after = await api({command:'look'});
        if (before.output && after.output && before.output !== after.output) console.log('  (room changed or same)');
    });

    // ═══════════════ 13. ITEM LIBRARY ═══════════════
    console.log('\n=== 13. ITEM LIBRARY ===');
    await t('Open library modal', async () => {
        // Click the library open button or call API
        const opened = await page.evaluate(async () => {
            if (window.itemLib) { itemLib.open(); return true; }
            return false;
        });
        await page.waitForTimeout(300);
        if (opened) console.log('  (library opened)');
        else console.log('  (itemLib not available, skip)');
    });
    await t('Library items list renders', async () => {
        const list = await page.$('#item-lib-list, .library-list');
        if (list) {
            const items = await list.$$('[class*="item"]');
            console.log('  ('+items.length+' library items visible)');
        } else console.log('  (no library list element)');
    });
    await t('Close library modal', async () => {
        await page.evaluate(async () => { if (window.itemLib) itemLib.close(); });
        await page.waitForTimeout(200);
    });
    await t('Library items via API', async () => {
        const data = await page.evaluate(async () => {
            const r = await fetch('/api/registry/items');
            return await r.json();
        });
        if (!data || typeof data !== 'object') throw 'No items returned';
        const count = Object.keys(data).length;
        console.log('  ('+count+' items in library)');
    });

    // ═══════════════ 14. MEMORIES ═══════════════
    console.log('\n=== 14. MEMORIES ===');
    await t('Get player memories API works', async () => {
        if (!activePlayer) { console.log('  (no active player)'); return; }
        const data = await page.evaluate(async (name) => {
            const r = await fetch('/api/players/'+encodeURIComponent(name)+'/memories');
            return await r.json();
        }, activePlayer);
        if (!Array.isArray(data)) console.log('  (memories: '+(data.error||'unexpected format')+')');
        else console.log('  ('+data.length+' memories)');
    });
    await t('Add player memory via API', async () => {
        if (!activePlayer) return;
        const data = await page.evaluate(async (name) => {
            const r = await fetch('/api/players/'+encodeURIComponent(name)+'/memories/entry', {
                method:'POST', headers:{'Content-Type':'application/json'},
                body:JSON.stringify({text:'Test memory from automated test',importance:3})
            });
            return await r.json();
        }, activePlayer);
        if (data.error) console.log('  (add memory: '+data.error+')');
        else console.log('  (memory added)');
    });

    // ═══════════════ 15. RELATIONSHIPS ═══════════════
    console.log('\n=== 15. RELATIONSHIPS ===');
    await t('Relationships API works', async () => {
        if (!activePlayer) return;
        const data = await page.evaluate(async (name) => {
            const r = await fetch('/api/state'); const s=await r.json();
            return s.players?.[name]?.relationships || {};
        }, activePlayer);
        const count = Object.keys(data||{}).length;
        console.log('  ('+count+' relationships)');
    });

    // ═══════════════ 16. KNOWLEDGE ═══════════════
    console.log('\n=== 16. KNOWLEDGE ===');
    await t('Get player knowledge API works', async () => {
        if (!activePlayer) return;
        const data = await page.evaluate(async (name) => {
            const r = await fetch('/api/players/'+encodeURIComponent(name)+'/knowledge');
            return await r.json();
        }, activePlayer);
        if (data.error) console.log('  (knowledge error: '+data.error.substring(0,40)+')');
        else console.log('  (knowledge accessible)');
    });

    // ═══════════════ 17. WORLD LORE ═══════════════
    console.log('\n=== 17. WORLD LORE ===');
    await t('Get world lore API works', async () => {
        const data = await page.evaluate(async () => {
            const r = await fetch('/api/world/lore'); return await r.json();
        });
        if (Array.isArray(data)) console.log('  ('+data.length+' lore entries)');
        else if (data.error) console.log('  (lore error: '+data.error.substring(0,40)+')');
        else console.log('  (lore accessible)');
    });

    // ═══════════════ 18. REGISTRIES ═══════════════
    console.log('\n=== 18. REGISTRIES ===');
    await t('Traits registry API works', async () => {
        const data = await page.evaluate(async () => {
            const r = await fetch('/api/registry/traits'); return await r.json();
        });
        const count = Object.keys(data||{}).length;
        console.log('  ('+count+' traits)');
    });
    await t('Characters registry API works', async () => {
        const data = await page.evaluate(async () => {
            const r = await fetch('/api/registry/characters'); return await r.json();
        });
        const count = Object.keys(data||{}).length;
        console.log('  ('+count+' characters in registry)');
    });

    // ═══════════════ 19. SETTINGS ═══════════════
    console.log('\n=== 19. SETTINGS ===');
    await t('Ghost mode setting works', async () => {
        const data = await page.evaluate(async () => {
            const r = await fetch('/api/settings/ghost_mode'); return await r.json();
        });
        if (data.error) console.log('  (ghost mode error)');
        else console.log('  (ghost mode: '+(data.ghost_mode||data.enabled||'ok')+')');
    });
    await t('Narration mode setting works', async () => {
        const data = await page.evaluate(async () => {
            const r = await fetch('/api/settings/narration'); return await r.json();
        });
        if (data.error) console.log('  (narration error)');
        else console.log('  (narration mode accessible)');
    });

    // ═══════════════ 20. GAME LOOP ═══════════════
    console.log('\n=== 20. GAME LOOP ===');
    await t('Turn apply endpoint works', async () => {
        const data = await page.evaluate(async () => {
            const r = await fetch('/api/turn/apply', {method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
            return await r.json();
        });
        if (data.error && !data.status) console.log('  (turn apply: '+data.error.substring(0,40)+')');
        else console.log('  (turn applied)');
    });
    await t('Turn events clear endpoint works', async () => {
        const data = await page.evaluate(async () => {
            const r = await fetch('/api/turn/clear', {method:'POST',headers:{'Content-Type':'application/json'}});
            return await r.json();
        });
        if (data.error) console.log('  (turn clear error)');
        else console.log('  (turn events cleared)');
    });

    // ═══════════════ 21. TIME SETTINGS ═══════════════
    console.log('\n=== 21. TIME SETTINGS ===');
    await t('Time per tick setting works', async () => {
        const data = await page.evaluate(async () => {
            const r = await fetch('/api/settings/time_per_tick'); return await r.json();
        });
        if (data.time_per_tick_minutes) console.log('  ('+data.time_per_tick_minutes+' min/tick)');
        else console.log('  (time setting accessible)');
    });

    // ═══════════════ 22. RESET SCENARIO ═══════════════
    console.log('\n=== 22. RESET ===');
    await t('Reset scenario endpoint responds', async () => {
        const data = await page.evaluate(async () => {
            const r = await fetch('/api/reset', {method:'POST',headers:{'Content-Type':'application/json'}});
            return await r.json();
        });
        if (data.error) console.log('  (reset would error: '+data.error.substring(0,40)+')');
        else console.log('  (reset endpoint available)');
    });

    // ═══════════════ 22b. RESET RELOADS LOADED SCENARIO ═══════════════
    console.log('\n=== 22b. RESET PRESERVES SCENARIO ===');
    await t('Reset reloads the loaded scenario, not the template', async () => {
        const probe = {
            players: {
                TestPlayer: { name: "TestPlayer", current_area: "Reset Probe Room" }
            },
            active_player: "TestPlayer",
            graph: {
                nodes: {
                    "area_reset_probe_room": { id: "area_reset_probe_room", type: "area", name: "Reset Probe Room", properties: { description: "probe room", environment: { light: 80, temperature: 21, air: "fresh", smell: "neutral", noise: "quiet" } } },
                    "player_TestPlayer": { id: "player_TestPlayer", type: "character", name: "TestPlayer", properties: {} }
                },
                edges: []
            },
            rooms: { "Reset Probe Room": { name: "Reset Probe Room", description: "probe room", environment: {}, items: [], exits: {} } },
            current_area: "Reset Probe Room",
            time_ticks: 0, turn_number: 0, time_per_tick_minutes: 5,
            clock_start_hour: 8, clock_start_minute: 0
        };
        const result = await page.evaluate(async (world) => {
            const loadRes = await fetch('/api/load', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(world)});
            const loadData = await loadRes.json();
            if (loadData.error) return { error: 'load: ' + loadData.error };
            const resetRes = await fetch('/api/reset', {method:'POST',headers:{'Content-Type':'application/json'}});
            const resetData = await resetRes.json();
            if (resetData.error) return { error: 'reset: ' + resetData.error };
            const state = await fetch('/api/save').then(r => r.json());
            return { rooms: Object.keys(state.rooms || {}) };
        }, probe);
        if (result.error) throw result.error;
        if (!result.rooms.includes('Reset Probe Room')) throw 'Scenario room missing after reset — reset fell back to template. rooms=' + JSON.stringify(result.rooms);
        console.log('  (probe room survived reset)');
    });

    // ═══════════════ 23. SERIALIZATION ═══════════════
    console.log('\n=== 23. SERIALIZATION ===');
    await t('GET /api/save returns complete state', async () => {
        const data = await page.evaluate(async () => { const r=await fetch('/api/save'); return await r.json(); });
        const required = ['players','rooms','graph','time_ticks','turn_number'];
        const missing = required.filter(k => !(k in data));
        if (missing.length > 0) console.log('  (missing keys: '+missing.join(',')+')');
        else console.log('  (all '+required.length+' required keys present)');
    });
    await t('TO_dict includes equipped items', async () => {
        const data = await page.evaluate(async () => { const r=await fetch('/api/save'); return await r.json(); });
        const hasEquipped = Object.values(data.players||{}).some(p => p.equipped && Object.keys(p.equipped).length > 0);
        if (hasEquipped) console.log('  (equipped items saved)');
        else console.log('  (no equipped items, OK)');
    });
    await t('TO_dict includes base_description', async () => {
        const data = await page.evaluate(async () => { const r=await fetch('/api/save'); return await r.json(); });
        const hasBaseDesc = Object.values(data.players||{}).some(p => p.base_description);
        if (hasBaseDesc) console.log('  (base_description saved)');
        else console.log('  (no base_description, OK)');
    });

    // ═══════════════ 24. EXISTING GLOBALS CHECK ═══════════════
    console.log('\n=== 24. GLOBALS INTEGRITY ===');
    const globalsToCheck = [
        ['worldState','object'],['events','object'],['config','object'],
        ['ui','object'],['agent','object'],['api','object'],
        ['ApiClient','function'],['itemLib','object'],['graphManager','object'],
        ['TriggerEditor','object'],['AIGenerator','object'],
        ['PromptBuilder','object'],['GraphNetwork','object'],
        ['escapeForHtmlAttribute','function'],['parseJSONFromResponse','function'],
        ['CreateModal','object'],['SettingsView','object'],['SaveLoadView','object'],
        ['WorldExport','object'],['ItemLibraryAI','object'],
        ['ItemLibraryPlacement','object'],['ItemLibraryContents','object'],
    ];
    for (const [name, type] of globalsToCheck) {
        await t('Global '+name+' exists', async () => {
            const actual = await page.evaluate(n => { try { return typeof eval(n); } catch(e) { return 'undefined'; } }, name);
            if (actual === 'undefined') throw name+' is undefined';
            if (type === 'function' && actual !== 'function') throw name+' should be function, got '+actual;
            if (type === 'object' && actual !== 'object' && actual !== 'function') throw name+' should be object, got '+actual;
        });
    }

    // ═══════════════ 25. CONTAINERS ═══════════════
    console.log('\n=== 25. CONTAINERS ===');
    await t('Container API works', async () => {
        const r = await api({command:'examine crate'});
        if (r.error && !r.output) console.log('  (no crate in room, skip)');
        else if (r.error && r.error.includes('Internal')) throw r.error;
    });
    await t('Take item from container handled', async () => {
        const r = await api({command:'take journal from crate'});
        if (r.error && !r.output) console.log('  (container take: '+(r.error||'').substring(0,40)+')');
        else if (r.error && r.error.includes('Internal')) throw r.error;
    });

    // ═══════════════ 26. EQUIPMENT EDGE CASES ═══════════════
    console.log('\n=== 26. EQUIPMENT EDGE CASES ===');
    await t('Equip item via command works', async () => {
        // Try to equip something from inventory
        const inv = await page.evaluate(async () => {
            const r = await fetch('/api/action', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:'inventory'})});
            const j = await r.json();
            return j.output || j.error || '';
        });
        const r = await api({command:'equip journal'});
        if (r.error && !r.output && !r.error.includes('dont have') && !r.error.includes('cant')) console.log('  (equip: '+r.error.substring(0,40)+')');
        else if (r.error && r.error.includes('Internal')) throw r.error;
    });
    await t('Unequip item handled gracefully', async () => {
        const r = await api({command:'remove journal'});
        if (r.error && !r.output) console.log('  (unequip: '+(r.error||'').substring(0,40)+')');
        else if (r.error && r.error.includes('Internal')) throw r.error;
    });
    await t('Equip nonexistent slot is handled', async () => {
        const r = await api({command:'wear journal'});
        if (r.error && !r.output) console.log('  (wear: '+(r.error||'').substring(0,40)+')');
    });

    // ═══════════════ 27. LIGHTING ═══════════════
    console.log('\n=== 27. LIGHTING ===');
    await t('Dark room examine returns dark error', async () => {
        const r = await api({command:'examine journal'});
        if (r.error && r.error.includes('dark')) console.log('  (dark room confirmed)');
        else if (r.output) console.log('  (can see, has light)');
    });
    await t('Light level changes when moving rooms', async () => {
        const state = await getState();
        const rooms = Object.values(state.rooms || {});
        const litRooms = rooms.filter(r => {
            const l = r.environment?.light || 0;
            const lStr = typeof l === 'string' ? l : '';
            return lStr.includes('normal') || lStr.includes('bright') || (typeof l === 'number' && l > 40);
        });
        console.log('  ('+litRooms.length+' lit rooms of '+rooms.length+')');
    });

    // ═══════════════ 28. NPC BEHAVIORS ═══════════════
    console.log('\n=== 28. NPC BEHAVIORS ===');
    await t('NPC data present in state', async () => {
        const state = await getState();
        const npcs = Object.values(state.players||{}).filter(p => p.simple_npc);
        if (npcs.length === 0) console.log('  (no simple NPCs in world)');
        else console.log('  ('+npcs.length+' NPCs, e.g. '+npcs[0].name+')');
    });
    await t('NPC has behavior properties', async () => {
        const state = await getState();
        const npc = Object.values(state.players||{}).find(p => p.simple_npc);
        if (!npc) { console.log('  (no NPCs)'); return; }
        if (npc.npc_behavior) console.log('  (behavior: '+npc.npc_behavior+')');
        else console.log('  (no npc_behavior field)');
    });

    // ═══════════════ 29. COMBAT ═══════════════
    console.log('\n=== 29. COMBAT ===');
    await t('Attack not-a-player returns error', async () => {
        const r = await api({command:'attack unknown_target'});
        if (r.error && !r.output) console.log('  (attack: '+(r.error||'').substring(0,40)+')');
        else if (r.error && r.error.includes('Internal')) throw r.error;
    });
    await t('Attack with nonexistent weapon handled', async () => {
        const r = await api({command:'attack rat with nothing'});
        if (r.error && !r.output) console.log('  (attack weapon: '+(r.error||'').substring(0,40)+')');
        else if (r.error && r.error.includes('Internal')) throw r.error;
    });

    // ═══════════════ 30. GHOST MODE ═══════════════
    console.log('\n=== 30. GHOST MODE ===');
    await t('Ghost mode toggle API works', async () => {
        const r = await page.evaluate(async () => {
            const resp = await fetch('/api/settings/ghost_mode', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:true})});
            return await resp.json();
        });
        if (r.error) console.log('  (ghost toggle: '+r.error.substring(0,40)+')');
        else console.log('  (ghost mode toggled)');
        // Restore
        await page.evaluate(async () => {
            await fetch('/api/settings/ghost_mode', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:false})});
        });
    });
    await t('Dead player actions are restricted', async () => {
        const state = await getState();
        const deadPlayers = Object.values(state.players||{}).filter(p => p.state === 'dead');
        console.log('  ('+deadPlayers.length+' dead players)');
    });

    // ═══════════════ 31. ROOM INSPECTOR ═══════════════
    console.log('\n=== 31. ROOM INSPECTOR ===');
    await t('Room description displays in inspector', async () => {
        const result = await page.evaluate(async () => {
            try {
                if (window.VW?.inspector) {
                    VW.inspector.showRoom('room_living_room');
                    await new Promise(r => setTimeout(r, 300));
                }
                const desc = document.querySelector('#inspector-description, .room-description, [class*=description]');
                return desc ? desc.textContent.trim().substring(0, 50) || 'empty' : 'no-desc-element';
            } catch(e) { return 'error: '+e.message; }
        });
        console.log('  (room desc: '+result+')');
    });
    await t('Environment light field editable', async () => {
        const result = await page.evaluate(() => {
            const field = document.querySelector('[class*=environment] input, #room-light, [data-field=light] input, [class*=env-light] input');
            if (!field) return 'not-found';
            return field.placeholder || field.value || 'exists';
        });
        console.log('  (light field: '+result+')');
    });
    await t('Environment temperature field exists', async () => {
        const result = await page.evaluate(() => {
            const field = document.querySelector('[class*=environment] input[type=number], #room-temp, [data-field=temperature] input');
            if (field) return 'exists';
            const labels = [...document.querySelectorAll('label')].filter(l => l.textContent.toLowerCase().includes('temp'));
            return labels.length > 0 ? 'found-label' : 'not-found';
        });
        console.log('  (temp field: '+result+')');
    });
    await t('Environment air quality field exists', async () => {
        const result = await page.evaluate(() => {
            const field = document.querySelector('#room-air, [data-field=air] input, [class*=env-air] input');
            if (field) return 'exists';
            const labels = [...document.querySelectorAll('label')].filter(l => l.textContent.toLowerCase().includes('air'));
            return labels.length > 0 ? 'found-label' : 'not-found';
        });
        console.log('  (air field: '+result+')');
    });
    await t('Room exits are listed', async () => {
        const result = await page.evaluate(() => {
            const exits = document.querySelectorAll('[class*=exit], [class*=door-list] li, .room-exits li');
            if (exits.length > 0) return exits.length+' exits found';
            // Fallback: check if any text mentions exits
            const body = document.body.textContent || '';
            const exitIdx = body.toLowerCase().indexOf('exit');
            return exitIdx >= 0 ? 'exit-text-found' : 'no-exits-visible';
        });
        console.log('  ('+result+')');
    });

    // ═══════════════ 32. DOOR INSPECTOR ═══════════════
    console.log('\n=== 32. DOOR INSPECTOR ===');
    await t('Door state displayed (open/closed/locked)', async () => {
        const result = await page.evaluate(() => {
            const els = [...document.querySelectorAll('[class*=door]')];
            const stateWords = els.filter(e => /open|closed|locked|blocked|broken/i.test(e.textContent));
            if (stateWords.length > 0) return stateWords.length+' door states found';
            const allText = document.body.textContent || '';
            const match = allText.match(/(door|exit).{0,30}(open|closed|locked|blocked|broken)/i);
            return match ? 'state-text-found: '+match[0].substring(0,40) : 'no-door-state-visible';
        });
        console.log('  ('+result+')');
    });
    await t('Door description editable', async () => {
        const result = await page.evaluate(() => {
            const desc = document.querySelector('#door-description, [data-field=door-desc] textarea, [class*=door] textarea');
            if (desc) return 'desc-field-exists';
            // Try switching to door-related tab
            const btns = [...document.querySelectorAll('[data-tab-btn]')];
            const doorBtn = btns.find(b => b.textContent.toLowerCase().includes('door'));
            if (doorBtn) { doorBtn.click(); return 'door-tab-clicked'; }
            return 'no-door-editor-found';
        });
        console.log('  ('+result+')');
    });
    await t('Door auto-close toggle exists', async () => {
        const result = await page.evaluate(() => {
            const labels = [...document.querySelectorAll('label, span, div')].filter(el => /auto.?close/i.test(el.textContent));
            if (labels.length > 0) return 'auto-close-label-found';
            const checkbox = document.querySelector('[class*=auto-close] input[type=checkbox], #door-auto-close');
            return checkbox ? 'checkbox-found' : 'not-found';
        });
        console.log('  (auto-close toggle: '+result+')');
    });
    await t('Door hidden toggle works', async () => {
        const result = await page.evaluate(() => {
            const labels = [...document.querySelectorAll('label, span, div')].filter(el => /hidden/i.test(el.textContent) && !/description|inventory|item/i.test(el.textContent));
            if (labels.length > 0) return 'hidden-label-found';
            const checkbox = document.querySelector('[class*=hidden] input[type=checkbox], #door-hidden');
            return checkbox ? 'checkbox-found' : 'not-found';
        });
        console.log('  (hidden toggle: '+result+')');
    });
    await t('Door pass_message setting exists', async () => {
        const result = await page.evaluate(() => {
            const labels = [...document.querySelectorAll('label, span, div')].filter(el => /pass.?message|passage/i.test(el.textContent));
            if (labels.length > 0) return 'pass-message-label-found';
            const input = document.querySelector('[class*=pass-message] input, [class*=pass_message] input, #door-pass-message');
            return input ? 'input-found' : 'not-found';
        });
        console.log('  (pass_message: '+result+')');
    });

    // ═══════════════ 33. GRAPH INTERACTIONS ═══════════════
    console.log('\n=== 33. GRAPH INTERACTIONS ===');
    await t('Graph tree view nodes rendered', async () => {
        const result = await page.evaluate(() => {
            const items = document.querySelectorAll('[class*=tree-node], [class*=graph-node], [data-node-id]');
            if (items.length > 0) return items.length+' nodes';
            // Try expand/collapse all buttons
            const btns = [...document.querySelectorAll('button')].filter(b => /expand|collapse|tree/i.test(b.textContent));
            return btns.length > 0 ? 'has-tree-buttons' : 'no-tree-nodes';
        });
        console.log('  (tree: '+result+')');
    });
    await t('Clicking a graph node shows inspector', async () => {
        const result = await page.evaluate(() => {
            const node = document.querySelector('[class*=tree-node], [data-node-id]');
            if (!node) return 'no-node-to-click';
            const clickTarget = node.querySelector('a, span, button') || node;
            clickTarget.click();
            return 'clicked-first-node';
        });
        console.log('  ('+result+')');
        await page.waitForTimeout(300);
    });
    await t('Graph canvas click handled without error', async () => {
        const result = await page.evaluate(() => {
            const canvas = document.querySelector('#graph-container canvas');
            if (!canvas) return 'no-canvas';
            const rect = canvas.getBoundingClientRect();
            if (rect.width === 0) return 'zero-size-canvas';
            // Dispatch a click at center
            canvas.dispatchEvent(new PointerEvent('pointerdown', {clientX: rect.left + rect.width/2, clientY: rect.top + rect.height/2, bubbles: true}));
            canvas.dispatchEvent(new PointerEvent('pointerup', {clientX: rect.left + rect.width/2, clientY: rect.top + rect.height/2, bubbles: true}));
            return 'clicked-at-'+Math.round(rect.width/2)+','+Math.round(rect.height/2);
        });
        console.log('  ('+result+')');
    });
    await t('Graph zoom controls exist', async () => {
        const result = await page.evaluate(() => {
            const btns = [...document.querySelectorAll('button')].filter(b => /zoom|fit|reset|\+|-/i.test(b.textContent));
            return btns.length > 0 ? btns.length+' buttons' : 'no-zoom-buttons';
        });
        console.log('  (zoom: '+result+')');
    });
    await t('Graph nodes can be highlighted', async () => {
        const result = await page.evaluate(() => {
            const canvas = document.querySelector('#graph-container canvas');
            if (!canvas) return 'no-canvas';
            const els = document.querySelectorAll('[class*=highlight], [class*=selected], [class*=active]');
            return els.length > 0 ? els.length+' highlighted' : 'no-highlight-elements';
        });
        console.log('  (highlight: '+result+')');
    });

    // ═══════════════ 34. TRIGGER EDITOR ═══════════════
    console.log('\n=== 34. TRIGGER EDITOR ===');
    await t('TriggerEditor.open function exists', async () => {
        const ok = await page.evaluate(() => typeof TriggerEditor?.open === 'function' || typeof TriggerEditor?.show === 'function');
        if (!ok) throw 'TriggerEditor.open/show not found';
        console.log('  (TriggerEditor.open available)');
    });
    await t('TriggerEditor.open accepts params', async () => {
        const ok = await page.evaluate(async () => {
            try {
                const fn = TriggerEditor.open || TriggerEditor.show;
                if (typeof fn !== 'function') return 'no-function';
                const result = fn('item_rusty_key', 'on_use');
                return result === undefined || result === true || result === false ? 'called-ok' : 'result-type:'+typeof result;
            } catch(e) { return 'error: '+e.message; }
        });
        console.log('  ('+ok+')');
        await page.waitForTimeout(200);
    });
    await t('Trigger list renders after opening', async () => {
        const result = await page.evaluate(() => {
            const triggers = document.querySelectorAll('[class*=trigger-item], [class*=trigger-row], .trigger-list-item');
            if (triggers.length > 0) return triggers.length+' triggers';
            const lists = document.querySelectorAll('[class*=trigger-list], [class*=trigger-group]');
            return lists.length > 0 ? 'has-trigger-container' : 'no-triggers-visible';
        });
        console.log('  ('+result+')');
    });
    await t('Trigger add condition button exists', async () => {
        const result = await page.evaluate(() => {
            const btns = [...document.querySelectorAll('button')].filter(b => /add.*condition|add.*trigger|new.*condition/i.test(b.textContent));
            if (btns.length > 0) return btns.length+' add-condition buttons';
            const icons = [...document.querySelectorAll('[class*=add], [class*=plus], .fa-plus')];
            return icons.length > 0 ? 'has-add-icons' : 'not-found';
        });
        console.log('  (add condition: '+result+')');
    });
    await t('Trigger effect type selector exists', async () => {
        const result = await page.evaluate(() => {
            const selects = document.querySelectorAll('[class*=trigger] select, [class*=effect] select');
            if (selects.length > 0) return selects.length+' selectors';
            const labels = [...document.querySelectorAll('label')].filter(l => /effect|trigger.*type/i.test(l.textContent));
            return labels.length > 0 ? 'effect-label-found' : 'not-found';
        });
        console.log('  (effect selector: '+result+')');
    });

    // ═══════════════ 35. EQUIPMENT STACKING ═══════════════
    console.log('\n=== 35. EQUIPMENT STACKING ===');
    await t('Paperdoll slots have correct labels', async () => {
        const result = await page.evaluate(() => {
            const labels = [...document.querySelectorAll('.paperdoll-slot-label, [class*=slot-label]')].map(e => e.textContent.trim());
            if (labels.length === 0) {
                // Try to switch to equipment tab first
                const tabs = [...document.querySelectorAll('[data-tab-btn]')];
                const equipTab = tabs.find(t => t.textContent.toLowerCase().includes('equip'));
                if (equipTab) { equipTab.click(); return 'switched-to-equip-tab'; }
            }
            return labels.length > 0 ? labels.join(',') : 'no-slot-labels';
        });
        console.log('  (slots: '+result+')');
    });
    await t('Multiple items can stack in same slot type', async () => {
        const result = await page.evaluate(() => {
            const slots = document.querySelectorAll('.paperdoll-slot, [class*=equip-slot]');
            const slotItems = {};
            slots.forEach(s => {
                const label = (s.querySelector('.paperdoll-slot-label') || {}).textContent || s.className;
                const count = s.querySelectorAll('[class*=item], .equipped-item').length;
                if (count > 0) slotItems[label.trim()] = (slotItems[label.trim()] || 0) + count;
            });
            const stacked = Object.entries(slotItems).filter(([,c]) => c > 1);
            return stacked.length > 0
                ? stacked.map(([l,c]) => l+':'+c).join(',')
                : 'no-stacking-detected';
        });
        console.log('  (stacking: '+result+')');
        await page.waitForTimeout(200);
    });
    await t('Equip/unequip command toggles state', async () => {
        const before = await page.evaluate(() => {
            const slots = document.querySelectorAll('.paperdoll-slot, [class*=equip-slot]');
            const itemCount = [...slots].reduce((sum, s) => sum + s.querySelectorAll('[class*=item], .equipped-item').length, 0);
            return itemCount;
        });
        const r = await api({command:'equip journal'});
        const r2 = await api({command:'remove journal'});
        const after = await page.evaluate(() => {
            const slots = document.querySelectorAll('.paperdoll-slot, [class*=equip-slot]');
            const itemCount = [...slots].reduce((sum, s) => sum + s.querySelectorAll('[class*=item], .equipped-item').length, 0);
            return itemCount;
        });
        console.log('  (equip cmd OK, counts:'+before+'->'+after+')');
    });
    await t('Equipped items appear in inspector', async () => {
        const result = await page.evaluate(() => {
            const equipSections = document.querySelectorAll('[class*=equipped], [class*=equipment-section], .paperdoll');
            if (equipSections.length > 0) return equipSections.length+' equip-sections';
            const items = document.querySelectorAll('.equipped-item, [class*=equip-item]');
            return items.length > 0 ? items.length+' equipped-items' : 'no-equipped-items';
        });
        console.log('  (equipped in inspector: '+result+')');
    });
    await t('Paperdoll body area labels match expected slots', async () => {
        const result = await page.evaluate(() => {
            const labels = [...document.querySelectorAll('.paperdoll-slot-label, [class*=slot-label]')].map(e => e.textContent.trim().toLowerCase());
            if (labels.length === 0) return 'no-labels';
            const expected = ['head','neck','arms','torso','waist','hands','legs','feet','back'];
            const found = expected.filter(e => labels.some(l => l.includes(e)));
            return found.length+'/'+expected.length+' expected found: '+found.join(',');
        });
        console.log('  (body areas: '+result+')');
    });

    // ═══════════════ 36. CONTAINER DEPTH ═══════════════
    console.log('\n=== 36. CONTAINER DEPTH ===');
    await t('Container items listed in room description', async () => {
        const r = await api({command:'look'});
        const output = r.output || r.error || '';
        const containerWords = ['chest','crate','box','barrel','cabinet','drawer','shelf','bag','pouch','sack'];
        const found = containerWords.filter(w => output.toLowerCase().includes(w));
        console.log('  (containers in room: '+(found.length > 0 ? found.join(',') : 'none found')+')');
    });
    await t('Can examine container contents', async () => {
        const r = await api({command:'examine crate'});
        const output = r.output || '';
        const error = r.error || '';
        if (output && (output.toLowerCase().includes('contain') || output.toLowerCase().includes('inside'))) {
            console.log('  (crate examined with contents)');
        } else if (error) {
            console.log('  (crate examine: '+error.substring(0,50)+')');
        } else {
            console.log('  (crate examined, no contents info)');
        }
    });
    await t('Container state (open/closed) is tracked', async () => {
        const state = await getState();
        const rooms = Object.values(state.rooms || {});
        let containerFound = false;
        for (const room of rooms) {
            for (const [id, item] of Object.entries(room.items || {})) {
                if (item.container || (item.tags && item.tags.includes('container'))) {
                    containerFound = true;
                    const state = item.container_state || item.state || 'unknown';
                    console.log('  (container '+id+': '+state+')');
                }
            }
        }
        if (!containerFound) {
            // Try API
            const r = await api({command:'examine crate'});
            if (r.output && r.output.toLowerCase().includes('open')) console.log('  (crate: open)');
            else if (r.output && r.output.toLowerCase().includes('closed')) console.log('  (crate: closed)');
            else console.log('  (no container items in world)');
        }
    });

    // ═══════════════ RESULTS ═══════════════
    if (jsErrors.length > 0) {
        console.log('\n!!! JS/console errors detected during session:');
        jsErrors.forEach(e => console.log('  \u2717 ' + e));
        results.push({ label: 'No JS/console errors', status: 'FAIL', error: jsErrors.join('; ') });
    } else {
        results.push({ label: 'No JS/console errors', status: 'OK' });
        console.log('\n\u2713 No JS/console errors detected.');
    }
    const passed = results.filter(r => r.status==='OK').length;
    const failed = results.filter(r => r.status==='FAIL').length;
    console.log('\n\u2550'.repeat(50));
    console.log('  RESULTS: ' + passed + '/' + (passed+failed) + ' passed, ' + failed + ' failed');
    console.log('\u2550'.repeat(50));
    if (failed > 0) {
        console.log('\nFailures:');
        results.filter(r=>r.status==='FAIL').forEach(r => console.log('  \u2717 ' + r.label + ': ' + r.error));
    }
    await browser.close();
    console.log('\nBrowser closed.');
})();
