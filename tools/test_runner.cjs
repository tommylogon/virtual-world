// Playwright suite runner (task-444 Phase 5).
//
// Runs the browser suites and writes JUnit XML so CI can report them.
//
//   node tools/test_runner.cjs --suite smoke            # critical paths, < 30s
//   node tools/test_runner.cjs --suite full --junit out/junit.xml
//
// The server is started automatically if the target URL is not reachable, using
// VW_PORT (default 4444), and stopped again at the end. Set VW_URL to point at
// an already-running server.
//
// Test modules export { name, tests: [{ name, smoke, run(page, H) }] }. `run`
// throws on failure. Existing standalone harnesses (test_regressions.cjs, ...)
// are not modules and are out of scope here.

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const net = require('net');
const { chromium } = require('playwright');
const H = require('./test_helpers.cjs');

const TEST_TIMEOUT_MS = 20000;

const MODULES = [
    require('./test_smoke.cjs'),
    require('./test_persistence.cjs'),
    require('./test_error_boundaries.cjs'),
];

function parseArgs(argv) {
    const args = { suite: 'smoke', junit: null, url: null };
    for (let i = 2; i < argv.length; i++) {
        const a = argv[i];
        if (a === '--suite') args.suite = argv[++i];
        else if (a === '--junit') args.junit = argv[++i];
        else if (a === '--url') args.url = argv[++i];
        else if (a === '--help' || a === '-h') args.help = true;
    }
    return args;
}

function xmlEscape(s) {
    return String(s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&apos;')
        .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g, '');
}

function writeJUnit(results, file, suiteName) {
    const failures = results.filter(r => r.status === 'FAIL').length;
    const time = (results.reduce((sum, r) => sum + r.ms, 0) / 1000).toFixed(3);
    const lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        `<testsuites name="${xmlEscape(suiteName)}" tests="${results.length}" failures="${failures}" time="${time}">`,
        `  <testsuite name="${xmlEscape(suiteName)}" tests="${results.length}" failures="${failures}" time="${time}">`,
    ];
    for (const r of results) {
        const t = (r.ms / 1000).toFixed(3);
        lines.push(`    <testcase classname="${xmlEscape(r.module)}" name="${xmlEscape(r.name)}" time="${t}">`);
        if (r.status === 'FAIL') {
            lines.push(`      <failure message="${xmlEscape(r.error)}">${xmlEscape(r.error)}</failure>`);
        }
        lines.push('    </testcase>');
    }
    lines.push('  </testsuite>', '</testsuites>', '');
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, lines.join('\n'), 'utf-8');
}

function portOf(url) {
    try { return Number(new URL(url).port || (url.startsWith('https') ? 443 : 80)); }
    catch { return 4444; }
}

function waitForPort(port, timeoutMs) {
    const deadline = Date.now() + timeoutMs;
    return new Promise((resolve, reject) => {
        const attempt = () => {
            const socket = net.connect(port, '127.0.0.1');
            socket.once('connect', () => { socket.destroy(); resolve(); });
            socket.once('error', () => {
                socket.destroy();
                if (Date.now() > deadline) reject(new Error(`server did not open port ${port}`));
                else setTimeout(attempt, 250);
            });
        };
        attempt();
    });
}

async function ensureServer(url) {
    const port = portOf(url);
    try {
        await waitForPort(port, 1500);
        return null; // already running
    } catch { /* start one */ }
    const child = spawn('python', ['app.py'], {
        cwd: path.join(__dirname, '..'),
        env: { ...process.env, VW_PORT: String(port) },
        stdio: 'ignore',
    });
    await waitForPort(port, 30000);
    return child;
}

async function runWithTimeout(fn, ms) {
    let timer;
    try {
        return await Promise.race([
            fn(),
            new Promise((_, reject) => {
                timer = setTimeout(() => reject(new Error(`timed out after ${ms}ms`)), ms);
            }),
        ]);
    } finally {
        clearTimeout(timer);
    }
}

async function main() {
    const args = parseArgs(process.argv);
    if (args.help) {
        console.log('usage: node tools/test_runner.cjs --suite smoke|full [--junit file] [--url http://127.0.0.1:4444]');
        return 0;
    }
    const url = args.url || H.baseUrl();

    const selected = MODULES.flatMap(m => m.tests.map(t => ({ ...t, module: m.name })))
        .filter(t => args.suite === 'full' || t.smoke);

    const server = await ensureServer(url).catch(err => {
        console.error(`runner: ${err.message}`);
        process.exit(2);
    });

    console.log(`runner: suite=${args.suite} url=${url} tests=${selected.length}`);
    const { browser, page, errors } = await H.startSession(chromium, url);

    const results = [];
    for (const t of selected) {
        const start = Date.now();
        try {
            await runWithTimeout(() => t.run(page, H, { errors }), TEST_TIMEOUT_MS);
            results.push({ ...t, status: 'OK', ms: Date.now() - start });
            console.log(`  OK   ${t.module}/${t.name}`);
        } catch (e) {
            results.push({ ...t, status: 'FAIL', error: e.message || String(e), ms: Date.now() - start });
            console.log(`  FAIL ${t.module}/${t.name}: ${e.message || e}`);
        }
    }

    if (errors.length) {
        console.log(`runner: ${errors.length} unconsumed console/page error(s) during the run`);
    }
    await browser.close();
    if (server) server.kill();

    if (args.junit) {
        writeJUnit(results, args.junit, args.suite);
        console.log(`runner: wrote ${args.junit}`);
    }

    const failed = results.filter(r => r.status === 'FAIL').length;
    const totalMs = results.reduce((s, r) => s + r.ms, 0);
    console.log(`runner: ${results.length - failed}/${results.length} passed in ${(totalMs / 1000).toFixed(1)}s`);
    return failed ? 1 : 0;
}

main().then(code => process.exit(code)).catch(err => {
    console.error('runner: fatal', err);
    process.exit(2);
});
