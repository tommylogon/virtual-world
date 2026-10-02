// Persistence suite (task-444 Phase 3).
//
// Each test mutates state through the same endpoint the UI uses, then either
// reloads the page or round-trips through a save file on disk, and asserts the
// value came back. A broken save/reload path fails here rather than merely
// exercising the handler.

async function reloadShell(page) {
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForSelector('#command-input', { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(500);
}

async function firstAreaId(page) {
    const state = await page.evaluate(async () => (await fetch('/api/state')).json());
    const node = Object.values(state.graph?.nodes || {}).find(n => n.type === 'area');
    if (!node) throw new Error('no area node to test with');
    return node.id;
}

async function patchNode(page, id, properties) {
    const res = await page.evaluate(async ({ id, properties }) => {
        const r = await fetch(`/api/graph/node/${encodeURIComponent(id)}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ properties }),
        });
        return { status: r.status, body: await r.json().catch(() => ({})) };
    }, { id, properties });
    if (res.status !== 200) {
        throw new Error(`PATCH ${id} -> ${res.status} ${JSON.stringify(res.body).slice(0, 120)}`);
    }
}

async function nodeDescription(page, id) {
    const state = await page.evaluate(async () => (await fetch('/api/state')).json());
    return state.graph?.nodes?.[id]?.properties?.description;
}

module.exports = {
    name: 'persistence',
    tests: [
        {
            name: 'a description edit survives save-game -> mutate -> load-game',
            smoke: true,
            run: async (page) => {
                const id = await firstAreaId(page);
                const marker = `task444-${Date.now()}`;
                let filename = null;
                try {
                    await patchNode(page, id, { description: marker });

                    const saved = await page.evaluate(async () => (await fetch('/api/save-game', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: `task444-temp-${Date.now()}` }),
                    })).json());
                    filename = saved.filename;
                    if (!filename) throw new Error('save-game returned no filename');

                    // Change it, then load the file back: only disk persistence
                    // can restore the marker.
                    await patchNode(page, id, { description: 'task444-overwritten' });
                    const loaded = await page.evaluate(async fn => (await fetch(
                        `/api/load-game/${encodeURIComponent(fn)}`, { method: 'POST' })).json(), filename);
                    if (loaded.status && loaded.status !== 'success') {
                        throw new Error(`load-game -> ${JSON.stringify(loaded).slice(0, 120)}`);
                    }
                    await reloadShell(page);

                    const after = await nodeDescription(page, id);
                    if (after !== marker) {
                        throw new Error(`description did not persist through disk: ${JSON.stringify(after)}`);
                    }
                } finally {
                    if (filename) {
                        await page.evaluate(async fn => {
                            await fetch(`/api/save-game/${encodeURIComponent(fn)}`, { method: 'DELETE' });
                        }, filename).catch(() => {});
                    }
                }
            },
        },
        {
            name: 'a narration dropdown change reaches the backend and survives reload',
            run: async (page) => {
                const before = await page.evaluate(async () => (await fetch('/api/settings/narration')).json());
                const target = before.mode === 'ai' ? 'none' : 'ai';
                await page.evaluate(async mode => {
                    await fetch('/api/settings/narration', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ mode }),
                    });
                }, target);
                const after = await page.evaluate(async () => (await fetch('/api/settings/narration')).json());
                if (after.mode !== target) throw new Error(`backend mode is ${after.mode}, expected ${target}`);
                await reloadShell(page);
                const uiMode = await page.evaluate(() => window.narrationUI && window.narrationUI.getMode());
                if (uiMode !== target) throw new Error(`UI mode after reload is ${uiMode}, expected ${target}`);
            },
        },
        {
            name: 'toggling a checkbox changes the backend',
            run: async (page) => {
                const before = await page.evaluate(async () => (await fetch('/api/settings/ghost_mode')).json());
                const target = !before.ghost_mode;
                await page.evaluate(async value => {
                    await fetch('/api/settings/ghost_mode', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ghost_mode: value }),
                    });
                }, target);
                const after = await page.evaluate(async () => (await fetch('/api/settings/ghost_mode')).json());
                if (after.ghost_mode !== target) {
                    throw new Error(`ghost_mode is ${after.ghost_mode}, expected ${target}`);
                }
                // restore
                await page.evaluate(async value => {
                    await fetch('/api/settings/ghost_mode', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ ghost_mode: value }),
                    });
                }, before.ghost_mode);
            },
        },
        {
            name: 'deleting a trigger is persisted',
            run: async (page) => {
                const id = await firstAreaId(page);
                const original = await page.evaluate(async id => {
                    const s = await fetch('/api/state').then(r => r.json());
                    return s.graph?.nodes?.[id]?.properties?.triggers || [];
                }, id);
                const marker = `task444_trig_${Date.now()}`;
                const trigger = {
                    id: marker, type: 'on_enter', conditions: {},
                    actions: [{ type: 'message', text: 'task444 probe' }],
                };
                try {
                    await patchNode(page, id, { triggers: [...original, trigger] });
                    await reloadShell(page);
                    const withTrigger = await page.evaluate(async id => {
                        const s = await fetch('/api/state').then(r => r.json());
                        return s.graph?.nodes?.[id]?.properties?.triggers || [];
                    }, id);
                    if (!withTrigger.some(t => t.id === marker)) {
                        throw new Error('the created trigger did not persist');
                    }

                    await patchNode(page, id, { triggers: original });
                    await reloadShell(page);
                    const after = await page.evaluate(async id => {
                        const s = await fetch('/api/state').then(r => r.json());
                        return s.graph?.nodes?.[id]?.properties?.triggers || [];
                    }, id);
                    if (after.some(t => t.id === marker)) {
                        throw new Error('the deleted trigger came back after reload');
                    }
                } finally {
                    await patchNode(page, id, { triggers: original }).catch(() => {});
                }
            },
        },
        {
            name: 'equipping an item is reflected in the paperdoll and persists',
            run: async (page) => {
                const runCmd = async cmd => page.evaluate(async c => (await fetch('/api/action', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: c }),
                })).json(), cmd);

                const info = await page.evaluate(async () => {
                    const s = await fetch('/api/state').then(r => r.json());
                    const equipped = s.players[s.active_player].equipped || {};
                    for (const [slot, ids] of Object.entries(equipped)) {
                        if (ids && ids.length) {
                            return { active: s.active_player, slot, id: ids[0], name: s.graph.nodes[ids[0]]?.name };
                        }
                    }
                    return null;
                });
                if (!info) throw new Error('no equipped item to exercise the paperdoll with');

                const slotContents = async () => page.evaluate(async ({ active, slot }) => {
                    const s = await fetch('/api/state').then(r => r.json());
                    return (s.players[active].equipped || {})[slot] || [];
                }, { active: info.active, slot: info.slot });

                await runCmd(`unequip ${info.name}`);
                if ((await slotContents()).includes(info.id)) {
                    throw new Error(`unequip ${info.name} left it in ${info.slot}`);
                }

                await runCmd(`equip ${info.name}`);
                if (!(await slotContents()).includes(info.id)) {
                    throw new Error(`equip ${info.name} did not put it in ${info.slot}`);
                }

                await reloadShell(page);
                if (!(await slotContents()).includes(info.id)) {
                    throw new Error(`the equipped ${info.slot} slot did not persist across reload`);
                }
            },
        },
        {
            name: 'moving a character changes the room and survives reload',
            run: async (page) => {
                const state = await page.evaluate(async () => (await fetch('/api/state')).json());
                const active = state.active_player;
                const from = state.players[active].current_area;
                const other = Object.values(state.graph?.nodes || {})
                    .find(n => n.type === 'area' && n.name !== from);
                if (!other) throw new Error('no second area to move to');

                const res = await page.evaluate(async ({ active, area }) => {
                    const r = await fetch(`/api/players/${encodeURIComponent(active)}/move`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ area }),
                    });
                    return { status: r.status, body: await r.json().catch(() => ({})) };
                }, { active, area: other.name });
                if (res.status !== 200) throw new Error(`move -> ${res.status} ${JSON.stringify(res.body)}`);

                await reloadShell(page);
                const after = await page.evaluate(async () => {
                    const s = await fetch('/api/state').then(r => r.json());
                    return s.players[s.active_player].current_area;
                });
                if (after !== other.name) throw new Error(`after reload in ${after}, expected ${other.name}`);

                // restore
                await page.evaluate(async ({ active, area }) => {
                    await fetch(`/api/players/${encodeURIComponent(active)}/move`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ area }),
                    });
                }, { active, area: from });
            },
        },
    ],
};
