const { chromium } = require('playwright');

// task-388 Phase 1 — TriggerGraph viewport smoke test.
// Exercises pan (empty-canvas / middle / space), zoom-to-cursor, fit, the dot
// grid, wire gluing + source-socket coloring, context-menu spawn position
// (including after search filtering), viewport persistence, and zoom clamps.
// Client-side only: nothing is saved to the backend, localStorage is cleared
// at the start and restored-free profile is used.

const TOL = 3; // px tolerance for screen-space assertions

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1400, height: 900 });
    const errors = [];
    page.on('pageerror', e => errors.push('[pageerror] ' + e.message));

    let failed = 0;
    const check = (name, ok, detail = '') => {
        if (!ok) failed++;
        console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? ' — ' + detail : ''));
    };

    const vp = () => page.evaluate(() => {
        const m = /translate\(([-\d.e]+)px,\s*([-\d.e]+)px\)\s*scale\(([-\d.e]+)\)/
            .exec(document.getElementById('tg-world').style.transform || '');
        return m ? { x: +m[1], y: +m[2], k: +m[3] } : null;
    });
    const nodeRect = (id) => page.evaluate((nid) => {
        const el = document.querySelector(`.tg-node[data-node-id="${nid}"]`);
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return { x: r.left, y: r.top, w: r.width, h: r.height, cx: r.left + r.width / 2, cy: r.top + r.height / 2, left: +el.style.left.replace('px', ''), top: +el.style.top.replace('px', '') };
    }, id);
    const canvasRect = () => page.evaluate(() => {
        const r = document.getElementById('tg-canvas').getBoundingClientRect();
        return { left: r.left, top: r.top, width: r.width, height: r.height };
    });

    await page.goto('http://127.0.0.1:4444', { waitUntil: 'domcontentloaded', timeout: 30000 });
    // The app holds a persistent event stream open, so networkidle never fires.
    await page.waitForFunction(() => typeof TriggerGraph !== 'undefined' && window.Lit, null, { timeout: 20000 });
    await page.waitForTimeout(1500);
    await page.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
    // Help-center tip cards float above everything and eat mouse events —
    // dismiss any that pop up (fresh profile => several queue up).
    const dismissTips = () => page.evaluate(() => {
        document.querySelectorAll('.hc-card, .hc-modal').forEach(el => el.remove());
    });
    await dismissTips();

    // ── Open the editor with a small two-behavior graph ──
    await page.evaluate(() => {
        TriggerGraph.show({ mode: 'behavior', graph: {
            nodes: [
                { id: 'n0', type: 'behavior', x: 0, y: 0, w: 260, props: { trigger: 'on_tick', priority: 3, interval: 2 } },
                { id: 'n1', type: 'condition', x: 360, y: 0, w: 260, props: { condition_type: 'proximity', max_areas: 1 } },
                { id: 'n2', type: 'action', x: 720, y: -40, w: 260, props: { action_type: 'speak', text: 'Eep?' } },
                { id: 'n3', type: 'behavior', x: 0, y: 300, w: 260, props: { trigger: 'on_player_enter_area', priority: 2, interval: 1 } },
                { id: 'n4', type: 'action', x: 360, y: 300, w: 260, props: { action_type: 'message', text: 'The rat twitches.' } },
            ],
            wires: [
                { id: 'w0', from: ['n0', 'output'], to: ['n1', 'input'] },
                { id: 'w1', from: ['n1', 'output_yes'], to: ['n2', 'input'] },
                { id: 'w2', from: ['n3', 'output'], to: ['n4', 'input'] },
            ],
        } });
    });
    await page.waitForTimeout(250);

    // 1. Auto-fit on first open: world transformed, every node inside the canvas
    const v0 = await vp();
    const cr = await canvasRect();
    check('world container + transform after auto-fit', !!v0 && v0.k > 0, JSON.stringify(v0));
    const inBounds = [];
    for (const id of ['n0', 'n1', 'n2', 'n3', 'n4']) {
        const r = await nodeRect(id);
        inBounds.push(r && r.x >= cr.left - 1 && r.y >= cr.top - 1 &&
            r.x + r.w <= cr.left + cr.width + 1 && r.y + r.h <= cr.top + cr.height + 1);
    }
    check('auto-fit: all 5 nodes visible in canvas', inBounds.every(Boolean), inBounds.join(','));

    // 2. Grid follows zoom
    const gs0 = await page.evaluate(() => document.getElementById('tg-canvas').style.backgroundSize);
    await page.evaluate(() => TriggerGraph._zoomCentered(1.25));
    await page.waitForTimeout(350); // animated
    const gs1 = await page.evaluate(() => document.getElementById('tg-canvas').style.backgroundSize);
    const v1 = await vp();
    check('grid scales with zoom', gs0 !== gs1 && gs1.startsWith('32.5'), `${gs0} -> ${gs1}`);
    check('zoom badge shows 125%', await page.evaluate(() => document.getElementById('tg-zoom-badge').textContent) === '125%');

    // 3. Zoom-to-cursor: the world point under the pointer stays put
    const anchor = await nodeRect('n2'); // zoom in with pointer on n2's center
    await page.mouse.move(anchor.cx, anchor.cy);
    await page.mouse.wheel(0, -240);
    await page.waitForTimeout(80);
    const after = await nodeRect('n2');
    const v2 = await vp();
    check('wheel zoom increases scale', v2.k > v1.k + 0.1, `k ${v1.k.toFixed(3)} -> ${v2.k.toFixed(3)}`);
    check('zoom anchored to cursor (node stays put)',
        Math.abs(after.cx - anchor.cx) < TOL && Math.abs(after.cy - anchor.cy) < TOL,
        `d=(${(after.cx - anchor.cx).toFixed(1)}, ${(after.cy - anchor.cy).toFixed(1)})`);

    // 4. Node drag tracks cursor 1:1 at zoom != 1  (the old editor drifted here)
    const hdr = await page.evaluate(() => {
        const r = document.querySelector('.tg-node[data-node-id="n2"] > div').getBoundingClientRect();
        return { x: r.left + r.width / 2, y: r.top + 8 };
    });
    const before = await nodeRect('n2');
    await page.mouse.move(hdr.x, hdr.y);
    await page.mouse.down();
    await page.mouse.move(hdr.x + 120, hdr.y + 60, { steps: 8 });
    await page.mouse.up();
    await page.waitForTimeout(60);
    const dragged = await nodeRect('n2');
    check('node drag 1:1 at zoom ' + v2.k.toFixed(2),
        Math.abs(dragged.cx - before.cx - 120) < TOL && Math.abs(dragged.cy - before.cy - 60) < TOL,
        `screen d=(${(dragged.cx - before.cx).toFixed(1)}, ${(dragged.cy - before.cy).toFixed(1)}), expected (120, 60)`);
    check('node world coords moved by screen/k',
        Math.abs(dragged.left - before.left - 120 / v2.k) < 1 && Math.abs(dragged.top - before.top - 60 / v2.k) < 1,
        `world d=(${(dragged.left - before.left).toFixed(1)}, ${(dragged.top - before.top).toFixed(1)}), expected ( ${(120 / v2.k).toFixed(1)}, ${(60 / v2.k).toFixed(1)})`);

    // 5. Wires stay glued to sockets after zoom + drag; YES wire is green
    const wireCheck = await page.evaluate(() => {
        const path = [...document.querySelectorAll('#tg-svg path')].find(p => p.getAttribute('stroke') === '#3fb950');
        if (!path) return { found: false };
        const m = /M([-\d.e]+),([-\d.e]+)/.exec(path.getAttribute('d'));
        const sock = document.querySelector('.tg-socket[data-node-id="n1"][data-socket-id="output_yes"]');
        const sr = sock.getBoundingClientRect();
        const cr = document.getElementById('tg-canvas').getBoundingClientRect();
        const t = document.getElementById('tg-world').style.transform;
        const mm = /translate\(([-\d.e]+)px,\s*([-\d.e]+)px\)\s*scale\([-\d.e]+\)/.exec(t);
        const k = +/scale\(([-\d.e]+)\)/.exec(t)[1];
        const sx = cr.left + (+mm[1]) + (+m[1]) * k;
        const sy = cr.top + (+mm[2]) + (+m[2]) * k;
        return {
            found: true,
            dist: Math.hypot(sx - (sr.left + sr.width / 2), sy - (sr.top + sr.height / 2)),
        };
    });
    check('YES wire rendered green (#3fb950)', wireCheck.found === true);
    check('wire glued to source socket after zoom+drag', wireCheck.found && wireCheck.dist < TOL, 'dist=' + (wireCheck.dist || -1).toFixed(2) + 'px');

    // 6. Empty-canvas pan: view moves, world coords untouched
    await dismissTips();
    const vpBefore = await vp();
    const worldBefore = await nodeRect('n0');
    const corner = { x: cr.left + cr.width * 0.9, y: cr.top + cr.height * 0.9 };
    await page.mouse.move(corner.x, corner.y);
    await page.mouse.down();
    await page.mouse.move(corner.x - 150, corner.y - 90, { steps: 6 });
    await page.mouse.up();
    await page.waitForTimeout(60);
    const vpAfter = await vp();
    const worldAfter = await nodeRect('n0');
    check('empty-canvas drag pans the view',
        Math.abs(vpAfter.x - vpBefore.x + 150) < TOL && Math.abs(vpAfter.y - vpBefore.y + 90) < TOL,
        `d=(${(vpAfter.x - vpBefore.x).toFixed(1)}, ${(vpAfter.y - vpBefore.y).toFixed(1)})`);
    check('pan does not move nodes in world space',
        worldAfter.left === worldBefore.left && worldAfter.top === worldBefore.top);

    // 7. Middle-mouse pan (works over a node too)
    const mid = await nodeRect('n4');
    const vb = await vp();
    await page.mouse.move(mid.cx, mid.cy);
    await page.mouse.down({ button: 'middle' });
    await page.mouse.move(mid.cx - 100, mid.cy - 50, { steps: 5 });
    await page.mouse.up({ button: 'middle' });
    const va = await vp();
    check('middle-mouse pan', Math.abs(va.x - vb.x + 100) < TOL && Math.abs(va.y - vb.y + 50) < TOL,
        `d=(${(va.x - vb.x).toFixed(1)}, ${(va.y - vb.y).toFixed(1)})`);

    // 8. Space+drag pan
    await dismissTips();
    const sb = await vp();
    await page.keyboard.down(' ');
    await page.mouse.move(corner.x, corner.y);
    await page.mouse.down();
    await page.mouse.move(corner.x + 200, corner.y + 100, { steps: 5 });
    await page.mouse.up();
    await page.keyboard.up(' ');
    const sa = await vp();
    check('space+drag pan', Math.abs(sa.x - sb.x - 200) < TOL && Math.abs(sa.y - sb.y - 100) < TOL,
        `d=(${(sa.x - sb.x).toFixed(1)}, ${(sa.y - sb.y).toFixed(1)})`);

    // 9. Context menu spawns the node under the cursor (world-correct at zoom),
    //    including after typing in the search filter (previously spawned at 0,0).
    await dismissTips();
    const spawnAt = { x: cr.left + cr.width * 0.6, y: cr.top + cr.height * 0.35 };
    await page.mouse.click(spawnAt.x, spawnAt.y, { button: 'right' });
    await page.waitForTimeout(80);
    await page.fill('#tg-cm-search', 'state');
    await page.waitForTimeout(60);
    await page.click('.tg-cm-item');
    await page.waitForTimeout(80);
    const spawnedOk = await page.evaluate(([px, py, tol]) => {
        return [...document.querySelectorAll('.tg-node')].some(n => {
            const r = n.getBoundingClientRect();
            return Math.abs(r.left - px) < tol && Math.abs(r.top - py) < tol;
        });
    }, [spawnAt.x, spawnAt.y, TOL]);
    const nodeCount = await page.evaluate(() => document.querySelectorAll('.tg-node').length);
    check('context-menu node spawns at cursor (after search filter)',
        spawnedOk && nodeCount === 6, `nodes=${nodeCount}, expected one at (${spawnAt.x.toFixed(0)}, ${spawnAt.y.toFixed(0)})`);

    // 10. Zoom clamps at 0.25..2.0
    await page.evaluate(() => { for (let i = 0; i < 25; i++) TriggerGraph._zoomCentered(1.25); });
    let clampHi = (await vp()).k;
    await page.evaluate(() => { for (let i = 0; i < 40; i++) TriggerGraph._zoomCentered(1 / 1.25); });
    let clampLo = (await vp()).k;
    check('zoom clamped to 0.25..2.0', clampHi === 2.0 && clampLo === 0.25, `hi=${clampHi} lo=${clampLo}`);

    // 11. Fit button brings everything back into view
    await page.click('#tg-zoomctl button:last-child'); // ⤢ Fit
    await page.waitForTimeout(400); // animated fit
    const fitOk = [];
    for (const id of ['n0', 'n1', 'n2', 'n3', 'n4']) {
        const r = await nodeRect(id);
        fitOk.push(r && r.x >= cr.left - 1 && r.y >= cr.top - 1 &&
            r.x + r.w <= cr.left + cr.width + 1 && r.y + r.h <= cr.top + cr.height + 1);
    }
    check('Fit button shows all nodes', fitOk.every(Boolean));

    // 12. Viewport persists across close/reopen of the same-mode editor
    const savedVp = await vp();
    await page.evaluate(() => TriggerGraph._close());
    await page.waitForTimeout(50);
    await page.evaluate(() => {
        TriggerGraph.show({ mode: 'behavior', graph: { nodes: [
            { id: 'n0', type: 'behavior', x: 0, y: 0, w: 260, props: { trigger: 'on_tick', priority: 1, interval: 1 } },
        ], wires: [] } });
    });
    await page.waitForTimeout(120);
    const restored = await vp();
    check('viewport persisted across close/reopen',
        Math.abs(restored.x - savedVp.x) < 2 && Math.abs(restored.y - savedVp.y) < 2 && restored.k === savedVp.k,
        `saved=${JSON.stringify(savedVp)} restored=${JSON.stringify(restored)}`);

    // 13. Wires glue immediately after reopen — regression for the stale-viewport
    // wire offset (wires used to be drawn against the previous session's
    // transform; after the viewport changed they were left scattered).
    await page.evaluate(() => TriggerGraph._close());
    await page.evaluate(() => {
        TriggerGraph.show({ mode: 'behavior', graph: {
            nodes: [
                { id: 'n0', type: 'behavior', x: 0, y: 0, w: 260, props: { trigger: 'on_tick', priority: 3, interval: 2 } },
                { id: 'n1', type: 'condition', x: 360, y: 0, w: 260, props: { condition_type: 'proximity', max_areas: 1 } },
                { id: 'n2', type: 'action', x: 720, y: -40, w: 260, props: { action_type: 'speak', text: 'Eep?' } },
                { id: 'n3', type: 'behavior', x: 0, y: 300, w: 260, props: { trigger: 'on_player_enter_area', priority: 2, interval: 1 } },
                { id: 'n4', type: 'action', x: 360, y: 300, w: 260, props: { action_type: 'message', text: 'The rat twitches.' } },
            ],
            wires: [
                { id: 'w0', from: ['n0', 'output'], to: ['n1', 'input'] },
                { id: 'w1', from: ['n1', 'output_yes'], to: ['n2', 'input'] },
                { id: 'w2', from: ['n3', 'output'], to: ['n4', 'input'] },
            ],
        } });
    });
    await page.waitForTimeout(200);
    const glue = await page.evaluate(() => {
        const cr = document.getElementById('tg-canvas').getBoundingClientRect();
        const t = document.getElementById('tg-world').style.transform;
        const mm = /translate\(([-\d.e]+)px,\s*([-\d.e]+)px\)\s*scale\(([-\d.e]+)\)/.exec(t);
        const vx = +mm[1], vy = +mm[2], k = +mm[3];
        const socks = [...document.querySelectorAll('.tg-socket')].map(s => {
            const r = s.getBoundingClientRect();
            return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
        });
        let unglued = 0, total = 0;
        for (const p of document.querySelectorAll('#tg-svg path')) {
            const m = /M([-\d.e]+),([-\d.e]+)/.exec(p.getAttribute('d'));
            if (!m) continue;
            total++;
            const sx = cr.left + vx + (+m[1]) * k;
            const sy = cr.top + vy + (+m[2]) * k;
            const nearest = Math.min(...socks.map(s => Math.hypot(s.x - sx, s.y - sy)));
            if (nearest > 3) unglued++;
        }
        return { total, unglued };
    });
    check('wires glued immediately after reopen (no interaction)',
        glue.total === 3 && glue.unglued === 0, JSON.stringify(glue));

    // ── Cleanup: close editor without saving ──
    await page.evaluate(() => TriggerGraph._close());

    const noErrors = errors.length === 0;
    check('no JS page errors', noErrors, errors.join(' | '));
    console.log('\n' + (failed === 0 && noErrors ? 'RESULT: PASS' : `RESULT: FAIL (${failed} failed)`));
    await browser.close();
    process.exit(failed === 0 && noErrors ? 0 : 1);
})();
