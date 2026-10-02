// The gate that makes the manual test plan trustworthy (task-587).
//
// A manual run must not touch a shipped file. After every phase (and at the end
// of a run) this checks:
//
//   1. `git status --porcelain` is empty except the scratch directory and its
//      assets. A phase that trips this voids the run and names the offender.
//   2. Every step in the plan declares a `may-write` value the model allows.
//
// Usage:
//   node tools/test_plan_gate.cjs                       # gate + plan validation
//   node tools/test_plan_gate.cjs --run-id my-run       # allow data/saves/my-run/**
//   node tools/test_plan_gate.cjs --check-plan          # plan only, no git gate
//
// Exit code 1 on any violation.

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const REPO = path.join(__dirname, '..');
const PLAN = path.join(REPO, 'docs', 'virtualWorld', 'testing', 'manual-test-plan.md');
const MAY_WRITE = new Set(['nothing', 'scratch-only', 'scratch+assets']);

function parseArgs(argv) {
    const args = { runId: process.env.VW_RUN_ID || 'manual', checkPlan: false, plan: PLAN };
    for (let i = 2; i < argv.length; i++) {
        if (argv[i] === '--run-id') args.runId = argv[++i];
        else if (argv[i] === '--check-plan') args.checkPlan = true;
        else if (argv[i] === '--plan') args.plan = argv[++i];
    }
    return args;
}

function gitPorcelain() {
    return execSync('git status --porcelain', { cwd: REPO, encoding: 'utf-8' })
        .split('\n').map(l => l.trimEnd()).filter(Boolean);
}

// Allowed dirty paths for a manual run: the scratch world, its assets, and the
// exported evidence the plan names.
function allowedPrefixes(runId) {
    return [
        `data/saves/${runId}/`,
        `data/saves\\${runId}\\`,
        'evidence/',
        'data/exports/',
    ];
}

function stepId(porcelainLine) {
    // " M path" / "?? path" / "R  old -> new"
    const rest = porcelainLine.slice(3);
    return (rest.includes(' -> ') ? rest.split(' -> ')[1] : rest).replace(/^"|"$/g, '');
}

function checkGit(args) {
    const lines = gitPorcelain();
    const allowed = allowedPrefixes(args.runId);
    const offenders = lines.filter(l => {
        const p = stepId(l).replace(/\\/g, '/');
        return !allowed.some(a => p.startsWith(a.replace(/\\/g, '/')));
    });
    if (offenders.length) {
        console.error(`plan gate: FAIL — ${offenders.length} shipped file(s) changed outside the scratch world:`);
        for (const l of offenders.slice(0, 20)) console.error(`  ${l}`);
        return 1;
    }
    console.log(`plan gate: git clean outside data/saves/${args.runId}/ (${lines.length} allowed change(s))`);
    return 0;
}

function parsePlan(file) {
    const text = fs.readFileSync(file, 'utf-8');
    const rows = [];
    let malformed = 0;
    for (const line of text.split('\n')) {
        if (!/^\|\s*\d+\.\d+\s*\|/.test(line)) continue;
        const cols = line.split('|').map(c => c.trim());
        // ["", id, pre, action, expect, may-write, evidence, ""]
        if (cols.length < 7) { malformed++; continue; }
        rows.push({ id: cols[1], pre: cols[2], mayWrite: cols[5] });
    }
    return { rows, malformed };
}

function checkPlan(args) {
    if (!fs.existsSync(args.plan)) {
        console.error(`plan gate: FAIL — plan not found: ${args.plan}`);
        return 1;
    }
    const { rows, malformed } = parsePlan(args.plan);
    const bad = rows.filter(r => !MAY_WRITE.has(r.mayWrite));
    if (malformed || bad.length) {
        console.error(`plan gate: FAIL — ${bad.length} step(s) without a valid may-write, ${malformed} malformed row(s)`);
        for (const r of bad.slice(0, 20)) console.error(`  ${r.id}: may-write=${JSON.stringify(r.mayWrite)}`);
        return 1;
    }
    console.log(`plan gate: ${rows.length} steps, every one declares a may-write value`);
    return 0;
}

function main() {
    const args = parseArgs(process.argv);
    let code = 0;
    code |= checkPlan(args);
    if (!args.checkPlan) code |= checkGit(args);
    console.log(code ? 'plan gate: FAIL' : 'plan gate: OK');
    return code ? 1 : 0;
}

process.exit(main());
