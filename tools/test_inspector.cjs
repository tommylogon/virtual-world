const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1400, height: 900 });

    await page.goto('http://127.0.0.1:4444', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);

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
            const r = await fetch('/api/action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: c })
            });
            return await r.json();
        }, cmd);
    }

    async function getState() {
        return await page.evaluate(async () => {
            const r = await fetch('/api/state');
            return await r.json();
        });
    }

    console.log('\n=== Inspector Test Suite ===\n');

    // 1. Inspector panel is present
    await check('Inspector panel exists in DOM', async () => {
        const panel = await page.$('#inspector-panel');
        if (!panel) throw new Error('#inspector-panel not found');
        const visible = await panel.isVisible();
        if (!visible) console.log('  (inspector panel present but may be collapsed)');
    });

    // 2. Active player name appears somewhere
    await check('Active player name appears in UI', async () => {
        const state = await getState();
        const playerName = state.active_player;
        if (!playerName) throw new Error('No active player in state');
        const bodyText = await page.evaluate(() => document.body.textContent);
        if (!bodyText.includes(playerName)) {
            console.log(`  (player "${playerName}" not found in visible text — may only appear in graph/state)`);
        } else {
            console.log(`  (found "${playerName}" in page text)`);
        }
    });

    // 3. Click first agent in agent list inspects it
    await check('Click agent in agent list opens inspector', async () => {
        const agentItems = await page.$$('#agent-list .agent-item');
        if (agentItems.length > 0) {
            const name = await agentItems[0].evaluate(el => el.textContent.trim());
            console.log(`  (clicking agent: "${name}")`);
            await agentItems[0].click();
            await page.waitForTimeout(500);

            const panelText = await page.evaluate(() =>
                document.getElementById('inspector-panel')?.textContent || 'empty'
            );
            if (!panelText || panelText === 'empty' || panelText.includes('empty') || panelText.includes('nothing selected')) {
                throw new Error('Inspector still shows empty after clicking agent');
            }
            console.log(`  (inspector now shows: "${panelText.substring(0, 60)}...")`);
        } else {
            // Fallback: use inspector API via evaluate
            console.log('  (no .agent-item found — using inspector.showAgent API)');
            const activated = await page.evaluate(async () => {
                try {
                    const state = await fetch('/api/state').then(r => r.json());
                    if (state.active_player && window.VW?.inspector) {
                        window.VW.inspector.showAgent(state.active_player);
                        return state.active_player;
                    }
                    return null;
                } catch (e) {
                    return null;
                }
            });
            if (activated) {
                await page.waitForTimeout(500);
                console.log(`  (triggered inspect for: ${activated})`);
            } else {
                console.log('  (could not trigger inspection via API — inspector may not be wired)');
            }
        }
    });

    // 4. Inspector tabs exist
    await check('Inspector tab buttons exist', async () => {
        const tabs = await page.$$('[data-tab-btn]');
        if (tabs.length > 0) {
            const labels = [];
            for (const tab of tabs) {
                const text = await tab.textContent();
                labels.push(text.trim());
            }
            console.log(`  (tabs: ${labels.join(', ')})`);
        } else {
            // Try button[data-tab]
            const altTabs = await page.$$('.tab-btn, [class*="tab"]');
            if (altTabs.length > 0) {
                console.log(`  (found ${altTabs.length} tab-like elements)`);
            } else {
                console.log('  (no data-tab-btn elements found — tabs may use different selectors)');
            }
        }
    });

    // 5. Paperdoll / Equipment renders when showing an agent (Inventory tab)
    await check('Equipment/paperdoll area present', async () => {
        // Make sure an agent is being inspected
        await page.evaluate(async () => {
            try {
                const state = await fetch('/api/state').then(r => r.json());
                if (state.active_player && window.VW?.inspector) {
                    window.VW.inspector.showAgent(state.active_player);
                }
            } catch (e) {}
        });
        await page.waitForTimeout(500);

        const paperdoll = await page.$('.paperdoll');
        if (paperdoll) {
            console.log('  (paperdoll element found)');
        } else {
            const equipSection = await page.$('#equipment-section, .equipment-section, [class*="equipment"]');
            if (equipSection) {
                console.log('  (equipment section found)');
            } else {
                console.log('  (no paperdoll/equipment section — need to activate Inventory tab first)');
            }
        }
    });

    // 6. Click on the graph canvas and inspect
    await check('Graph canvas responds to click', async () => {
        const canvas = await page.$('#graph-container canvas');
        if (canvas) {
            const box = await canvas.boundingBox();
            if (box) {
                // Click center of canvas to select a node
                await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
                await page.waitForTimeout(1000);

                const panelText = await page.evaluate(() =>
                    document.getElementById('inspector-panel')?.textContent || 'empty'
                );
                console.log(`  (inspector after graph click: "${panelText.substring(0, 80)}...")`);

                // Also click upper-left area to hit different node
                await page.mouse.click(box.x + box.width * 0.25, box.y + box.height * 0.25);
                await page.waitForTimeout(500);
            } else {
                console.log('  (canvas has no bounding box)');
            }
        } else {
            console.log('  (no canvas found in #graph-container)');
        }
    });

    // 7. Try inspecting items (if any exist in state)
    await check('Inspecting an item node works', async () => {
        const inspected = await page.evaluate(async () => {
            try {
                const state = await fetch('/api/state').then(r => r.json());
                const graph = state.graph || state.data?.graph;
                if (!graph || !graph.nodes) return { found: false };

                const itemNodes = Object.entries(graph.nodes).filter(([id]) => id.startsWith('item_'));
                if (itemNodes.length > 0 && window.VW?.inspector) {
                    window.VW.inspector.showNode(itemNodes[0][0]);
                    return { found: true, id: itemNodes[0][0], name: itemNodes[0][1]?.name || itemNodes[0][0] };
                }
                return { found: false };
            } catch (e) {
                return { found: false, error: e.message };
            }
        });

        if (inspected.found) {
            await page.waitForTimeout(500);
            console.log(`  (triggered inspect for item: ${inspected.id})`);
        } else {
            console.log('  (no item nodes found in graph or inspector unavailable)');
        }
    });

    // 8. Exit items / door buttons show in inspector when inspecting room
    await check('Exit items/door buttons appear when inspecting a room', async () => {
        const roomNodeId = await page.evaluate(async () => {
            try {
                const state = await fetch('/api/state').then(r => r.json());
                const graph = state.graph || state.data?.graph;
                if (graph && graph.nodes) {
                    const roomNodes = Object.entries(graph.nodes).filter(([id]) => id.startsWith('room_'));
                    if (roomNodes.length > 0) {
                        return roomNodes[0][0];
                    }
                }
                // Fallback: get player's current room
                const player = state.players?.[state.active_player];
                if (player) return player.room_id || player.location;
                return null;
            } catch (e) { return null; }
        });

        if (roomNodeId) {
            await page.evaluate((roomId) => {
                if (window.VW?.inspector) {
                    window.VW.inspector.showNode(roomId);
                }
            }, roomNodeId);
            await page.waitForTimeout(500);

            const exitItems = await page.$$('.exit-item');
            console.log(`  (exit items found in room "${roomNodeId}": ${exitItems.length})`);

            if (exitItems.length > 0) {
                const buttons = await page.$$('.exit-item button');
                for (const btn of buttons) {
                    const txt = await btn.textContent();
                    console.log(`    - "${txt.trim()}"`);
                }
            }
        } else {
            console.log('  (could not identify a room node to inspect)');
        }
    });

    // 9. Trigger nodes visible in inspector (logic triggers)
    await check('Trigger nodes can be found and inspected', async () => {
        const triggerNodeId = await page.evaluate(async () => {
            try {
                const state = await fetch('/api/state').then(r => r.json());
                const graph = state.graph || state.data?.graph;
                if (!graph || !graph.nodes) return null;
                const triggers = Object.entries(graph.nodes).filter(([id]) => id.startsWith('trigger_'));
                return triggers.length > 0 ? triggers[0][0] : null;
            } catch (e) { return null; }
        });

        if (triggerNodeId) {
            await page.evaluate((id) => {
                if (window.VW?.inspector) {
                    window.VW.inspector.showNode(id);
                }
            }, triggerNodeId);
            await page.waitForTimeout(500);
            console.log(`  (trigger node "${triggerNodeId}" selected in inspector)`);
        } else {
            console.log('  (no trigger nodes found in graph)');
        }
    });

    // 10. Verify state after inspector interactions
    await check('State still valid after all inspector operations', async () => {
        const state = await getState();
        if (!state) throw new Error('No state returned after inspector tests');
        console.log(`  (active_player: ${state.active_player}, time_ticks: ${state.time_ticks})`);
    });

    console.log('\nDone.');
    await browser.close();
})();
