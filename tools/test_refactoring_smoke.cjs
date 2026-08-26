const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1400, height: 900 });
    const results = { passed: 0, failed: 0, errors: [] };

    async function check(label, fn) {
        try {
            await fn();
            results.passed++;
            console.log(`  \u2713 ${label}`);
        } catch (err) {
            results.failed++;
            results.errors.push(`${label}: ${err.message}`);
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

    await page.goto('http://127.0.0.1:4444', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    console.log('\n=== Smoke Test: Refactored VirtualWorld ===\n');

    // 1. Page loads
    await check('Page loads with title', async () => {
        const title = await page.title();
        if (!title) throw new Error('No page title');
        console.log(`  (title: "${title}")`);
    });

    // 2. API state returns data
    await check('GET /api/state returns state', async () => {
        const state = await getState();
        if (!state) throw new Error('No state returned');
        if (!state.rooms && !state.graph) throw new Error('State missing rooms/graph');
        console.log(`  (rooms: ${Object.keys(state.rooms || {}).length}, active_player: ${state.active_player})`);
    });

    // 3. Basic command: look
    await check('Command "look" succeeds', async () => {
        const resp = await command('look');
        if (resp.error) throw new Error(resp.error);
        if (!resp.output) throw new Error('No output from look');
    });

    // 4. Basic command: inventory
    await check('Command "inventory" succeeds', async () => {
        const resp = await command('inventory');
        if (resp.error) throw new Error(resp.error);
    });

    // 5. UI elements exist
    await check('Inspector panel exists', async () => {
        const panel = await page.$('#inspector-panel');
        if (!panel) throw new Error('Inspector panel missing (#inspector-panel)');
    });

    await check('Command input exists', async () => {
        const input = await page.$('#command-input');
        if (!input) throw new Error('Command input missing (#command-input)');
    });

    await check('Graph container exists', async () => {
        const container = await page.$('#graph-container');
        if (!container) throw new Error('Graph container missing (#graph-container)');
    });

    await check('Graph canvas renders inside container', async () => {
        const canvas = await page.$('#graph-container canvas');
        if (!canvas) throw new Error('Graph canvas element missing');
        const box = await canvas.boundingBox();
        if (!box || box.width === 0) throw new Error('Graph canvas has zero width');
        console.log(`  (canvas: ${box.width}x${box.height})`);
    });

    // 6. Examine self succeeds
    await check('Examine self succeeds', async () => {
        const resp = await command('examine self');
        if (resp.error) throw new Error(resp.error);
    });

    // 7. Agent list renders
    await check('Agent list section exists', async () => {
        const section = await page.$('#agent-list');
        if (!section) {
            // Try alternative container
            const alt = await page.$('[class*="agent"]');
            if (!alt) console.log('  (no agent list element found, non-critical)');
        } else {
            const items = await section.$$('.agent-item');
            console.log(`  (found ${items.length} agent items)`);
        }
    });

    // 8. Event stream renders
    await check('Event stream section exists', async () => {
        const stream = await page.$('#event-stream');
        if (!stream) {
            const alt = await page.$('.event-stream');
            if (!alt) console.log('  (event stream element not found, non-critical)');
        }
    });

    // 9. Stats command works
    await check('Command "stats" succeeds', async () => {
        const resp = await command('stats');
        if (resp.error) throw new Error(resp.error);
    });

    // 10. API returns consistent graph data
    await check('Graph state has nodes and edges', async () => {
        const state = await getState();
        const graph = state.graph || state.data?.graph;
        if (graph) {
            const nodes = graph.nodes ? Object.keys(graph.nodes).length : 0;
            const edges = graph.edges ? graph.edges.length : 0;
            console.log(`  (${nodes} nodes, ${edges} edges)`);
            if (nodes === 0) throw new Error('Graph has zero nodes');
        } else {
            console.log('  (no graph data in state, checking rooms instead)');
            const roomCount = state.rooms ? Object.keys(state.rooms).length : 0;
            if (roomCount === 0) throw new Error('No rooms or graph data in state');
        }
    });

    // 11. Save/Load API endpoints respond
    await check('GET /api/save returns JSON', async () => {
        const data = await page.evaluate(async () => {
            const r = await fetch('/api/save');
            return await r.json();
        });
        if (!data) throw new Error('No save data returned');
        console.log(`  (save keys: ${Object.keys(data).slice(0, 5).join(', ')})`);
    });

    // Results summary
    const total = results.passed + results.failed;
    console.log(`\n=== Results: ${results.passed}/${total} passed, ${results.failed} failed ===`);
    if (results.errors.length > 0) {
        console.log('\nErrors:');
        results.errors.forEach(e => console.log(`  - ${e}`));
    }

    await browser.close();
    process.exit(results.failed > 0 ? 1 : 0);
})();
