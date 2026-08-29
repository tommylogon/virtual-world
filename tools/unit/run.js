/**
 * tools/unit/run.js — zero-dependency unit test runner for browser-global JS modules.
 *
 * The sandbox's global object IS `window` (exactly like a browser classic
 * script), so modules written as `window.Foo = ...` resolve their bare
 * cross-module references naturally.
 *
 * Test files call the injected globals:
 *   test('name', () => { ... });
 *   assertEq(got, want, 'label');  assertTrue/assertFalse(v, 'label');
 *
 * Usage:  node tools/unit/run.js        (exit 0 = green, 1 = failures)
 */
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..', '..');
const UNIT_DIR = __dirname;

// The window object doubles as the vm global — browser semantics.
const win = {
    console,
    // stubs used by plan-tracker.js
    worldState: { data: { time_ticks: 0 } },
    events: { log: () => {}, trackPhase: () => {}, trackAction: () => {} },
    // test API (populated below)
    test: null,
    assertEq: null,
    assertTrue: null,
    assertFalse: null,
};
win.window = win;
vm.createContext(win);

function load(relPath) {
    const src = fs.readFileSync(path.join(ROOT, relPath), 'utf8');
    vm.runInContext(src, win, { filename: relPath });
}

// ── test API ──
const tests = [];
let currentFile = '';
win.test = (name, fn) => tests.push({ file: currentFile, name, fn });
win.assertEq = (got, want, label) => {
    const g = JSON.stringify(got);
    const w = JSON.stringify(want);
    if (g !== w) throw new Error(`${label || 'assertEq'}: got ${g}, want ${w}`);
};
win.assertTrue = (value, label) => {
    if (!value) throw new Error(`${label || 'assertTrue'}: expected truthy, got ${value}`);
};
win.assertFalse = (value, label) => {
    if (value) throw new Error(`${label || 'assertFalse'}: expected falsy, got ${value}`);
};

// ── load production modules (browser-global style) ──
load('static/js/shared/json-utils.js');
load('static/js/agent/vital-thresholds.js');
load('static/js/agent/action-normalizer.js');
load('static/js/agent/response-parser.js');
load('static/js/agent/plan-tracker.js');
load('static/js/agent/prompt-builder/character-state.js');
load('static/js/agent/prompt-builder/conversation-context.js');

// ── discover + run test files ──
const testFiles = fs.readdirSync(UNIT_DIR).filter(f => /^test_.*\.js$/.test(f)).sort();
for (const file of testFiles) {
    currentFile = file;
    const src = fs.readFileSync(path.join(UNIT_DIR, file), 'utf8');
    vm.runInContext(src, win, { filename: `tools/unit/${file}` });
}

let passed = 0;
const failures = [];
for (const t of tests) {
    try {
        t.fn();
        passed++;
        console.log(`  ok  ${t.file} :: ${t.name}`);
    } catch (err) {
        failures.push({ t, err });
        console.error(`FAIL  ${t.file} :: ${t.name}\n      ${err.message}`);
    }
}

console.log(`\n${passed} passed, ${failures.length} failed (${testFiles.length} test files)`);
process.exit(failures.length ? 1 : 0);
