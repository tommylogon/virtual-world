/**
 * tools/unit/run.cjs — zero-dependency unit test runner for browser-global JS modules.
 *
 * The sandbox's global object IS `window` (exactly like a browser classic
 * script), so modules written as `window.Foo = ...` resolve their bare
 * cross-module references naturally.
 *
 * Test files call the injected globals:
 *   test('name', () => { ... });
 *   assertEq(got, want, 'label');  assertTrue/assertFalse(v, 'label');
 *
 * Usage:  node tools/unit/run.cjs        (exit 0 = green, 1 = failures)
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
    // browser globals used by shared helpers but absent from a bare vm context
    URL, URLSearchParams,
    // stubs used by plan-tracker.js
    worldState: { data: { time_ticks: 0 } },
    events: { log: () => {}, trackPhase: () => {}, trackAction: () => {} },
    // test API (populated below)
    test: null,
    assertEq: null,
    assertTrue: null,
    assertFalse: null,
    // Test affordance for reading repo files from inside the vm sandbox, where
    // `require` does not exist. Guard tests that check the *sources* (rather
    // than a runtime registry) use these; nothing under test reads a file.
    __readFile: (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf8'),
    __exists: (rel) => fs.existsSync(path.join(ROOT, rel)),
    __listDir: (rel) => fs.readdirSync(path.join(ROOT, rel), { withFileTypes: true })
        .map((d) => (d.isDirectory() ? d.name + '/' : d.name)),
    // `vm` contexts do not inherit the host's timers, and several modules
    // schedule work (a layout redraw, a debounce). Synchronous stubs keep a test
    // from having to care: nothing under test depends on the delay.
    setTimeout: (fn) => { fn(); return 0; },
    clearTimeout: () => {},
    setInterval: () => 0,
    clearInterval: () => {},
    // help-center.js runs `init()` at load, which installs document listeners and
    // reads the seen-flags out of localStorage. Neither exists in a bare vm
    // context, so both are stubbed permissively: a fake element absorbs any
    // createElement/appendChild chain and the listener registrations are no-ops.
    // Nothing under test touches the DOM — the registry is plain data.
    localStorage: {
        _v: new Map(),
        getItem(k) { return this._v.has(k) ? this._v.get(k) : null; },
        setItem(k, val) { this._v.set(k, String(val)); },
        removeItem(k) { this._v.delete(k); },
    },
    document: {
        readyState: 'complete',
        addEventListener: () => {},
        removeEventListener: () => {},
        querySelector: () => null,
        querySelectorAll: () => [],
        getElementById: () => null,
        createElement: () => makeStubEl(),
        head: makeStubEl(),
        body: makeStubEl(),
    },
};
function makeStubEl() {
    const el = {
        style: {}, dataset: {}, classList: { add: () => {}, remove: () => {} },
        children: [], textContent: '', innerHTML: '', className: '',
        setAttribute() {}, getAttribute: () => null, removeAttribute() {},
        appendChild(c) { this.children.push(c); return c; },
        removeChild() {}, remove() {}, insertBefore(c) { this.children.push(c); return c; },
        addEventListener() {}, removeEventListener() {},
        querySelector: () => null, querySelectorAll: () => [],
        getBoundingClientRect: () => ({ left: 0, top: 0, width: 0, height: 0 }),
        scrollIntoView() {},
    };
    return el;
}
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
load('static/js/shared/item-containment.js');
load('static/js/shared/trigger-suggest-ai.js');
load('static/js/shared/trigger-graph.js');
load('static/js/agent/vital-thresholds.js');
load('static/js/agent/simultaneous.js');
load('static/js/agent/sim-round.js');
load('static/js/agent/turn-queue.js');
load('static/js/agent/action-normalizer.js');
load('static/js/agent/response-parser.js');
load('static/js/agent/plan-tracker.js');
load('static/js/agent/involuntary.js');
load('static/js/character-art.js');
load('static/js/inspector/sprite-sheet.js');
load('static/js/agent/prompt-builder/character-state.js');
load('static/js/agent/prompt-builder/conversation-context.js');
load('static/js/context-window.js');
load('static/js/nl-editor/staging.js');
load('static/js/nl-editor/diff.js');
load('static/js/nl-editor/tools.js');
load('static/js/nl-editor/agent-loop.js');
load('static/js/graph/graph-background.js');
load('static/js/graph/graph-export.js');
load('static/js/graph/event-handlers.js');
load('static/js/graph/tooltips.js');
load('static/js/graph/separation.js');
load('static/js/graph/relative-layout.js');
load('static/js/graph/layout-engine.js');
load('static/js/graph/toolbar.js');
load('static/js/graph/scope-tree.js');
load('static/js/soak/soak-format.js');
load('static/js/soak/soak-charts.js');
load('static/js/soak/soak-spacetime.js');
load('static/js/ui/timeskip.js');
// Loads after the document/localStorage stubs above; its `init()` only installs
// listeners, so the registry it exports is intact for the guard test.
load('static/js/ui/help-center.js');
load('static/js/worldpainter/grid-model.js');

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
