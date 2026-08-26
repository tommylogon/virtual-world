// Shared Playwright test helpers.
//
// Provides a startSession() that wires up console/page error capture for the
// entire session, plus convenience wrappers for common actions (agent
// inspector, tab switching, API calls, state fetch).
//
// Usage:
//   const { chromium } = require('playwright');
//   const H = require('./test_helpers.cjs');
//   (async () => {
//       const { browser, page, errors } = await H.startSession(chromium, 'http://127.0.0.1:4444');
//       await H.api(page, { command: 'look' });
//       H.checkConsoleErrors(errors, 'after look');
//       await browser.close();
//   })();

const BASE = 'http://127.0.0.1:4444';

/** Launch a page with error capture wired up.
 * Network "Failed to load resource" messages (from intentional 4xx/5xx
 * failure-path tests) are ignored — only genuine page errors and explicit
 * console.error() calls are captured.
 * @returns {{ browser, page, errors: Array<{type:string,message:string}> }}
 */
async function startSession(chromium, url = BASE, opts = {}) {
    const browser = await chromium.launch({ headless: opts.headless !== false });
    const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
    const errors = [];
    page.on('pageerror', err => errors.push({ type: 'pageerror', message: err.message }));
    page.on('console', msg => {
        if (msg.type() !== 'error') return;
        // Filter browser-injected network status noise from intentional failure tests
        if (msg.text().startsWith('Failed to load resource')) return;
        errors.push({ type: 'console', message: msg.text() });
    });
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(1000);
    return { browser, page, errors };
}

/** Throw if any JS/console errors accumulated during the session. */
function checkConsoleErrors(errors, context = '') {
    if (errors.length === 0) return;
    const summary = errors.map(e => `[${e.type}] ${e.message}`).join(' | ');
    throw new Error((context ? context + ': ' : '') + 'Console/page errors: ' + summary);
}

/** Click a tab by its visible label (matches [data-tab-btn] content). */
async function switchTab(page, label) {
    const tabs = await page.$$('[data-tab-btn]');
    for (const tab of tabs) {
        const text = (await tab.textContent()) || '';
        if (text.includes(label)) {
            await tab.click();
            await page.waitForTimeout(200);
            return true;
        }
    }
    throw new Error(`Tab "${label}" not found`);
}

/** Open a character in the inspector panel. */
async function showAgent(page, name) {
    await page.evaluate(async n => {
        const s = await fetch('/api/state').then(r => r.json());
        if (s.players?.[n] && window.VW?.inspector) VW.inspector.showAgent(n);
    }, name);
    await page.waitForTimeout(300);
}

/** POST a game command to /api/action. */
async function api(page, body) {
    return await page.evaluate(async b => {
        const r = await fetch('/api/action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(b)
        });
        return await r.json();
    }, body);
}

/** Fetch the full world state. */
async function getState(page) {
    return await page.evaluate(async () => (await fetch('/api/state')).json());
}

/** Run a game command and return its output text. */
async function gameCmd(page, cmd) {
    const r = await api(page, { command: cmd });
    return r.output || r.error || JSON.stringify(r);
}

module.exports = {
    BASE,
    startSession,
    checkConsoleErrors,
    switchTab,
    showAgent,
    api,
    getState,
    gameCmd
};
