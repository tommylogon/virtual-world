---
type: task
status: review
area: triggers
priority: high
---

# task-501: Trigger graph compile honesty: preserve NO-branch effects and OR/NOT conditions

**Filed:** 2026-09-24
**Related:** task-442, task-388
**Area:** triggers (editor/compiler; no engine runtime materialisation)

## Goal

Fix the two dishonest trigger-graph compiles so no authored effect is silently dropped and OR/NOT conditions survive the round trip.

## Problem (verified 2026-09-24)

Two defects in `static/js/shared/trigger-graph.js` make the editor's compile lie
about what it saved. Both were filed as task-388 defects #9–#11 and previously
bundled into task-442 Slice 2; split out here because they are a self-contained
editor/compiler fix, independent of the runtime blueprint materialiser.

1. **NO-branch effects are discarded.** `_traceGraph` (`:2082-2113`) walks a
   condition node's `output_no` wire (`:2091-2095`) but keeps only the first
   `message` effect as `fail_message`; every other NO-branch effect is dropped.
   A NO branch with two effects compiles to at most a fail message.
2. **No OR/NOT.** `compileToEngine` (`:1996`) always emits
   `{operator:'and', conditions: [...]}`; `compileToBehaviors` (`:1844`) does
   the same. There is no OR/NOT representation, so an authored branch cannot
   survive a compile.

Evidence: `static/js/shared/trigger-graph.js:1844`, `:1996`, `:2082-2113`.

## Changes

- Compile a NO branch to real engine conditions/effects, **or** make the editor
  refuse to save a NO branch it cannot represent. Silent truncation is not
  acceptable.
- Represent OR/NOT so they round-trip through `compileToEngine`; extend the
  engine condition schema if needed (check `engine/triggers` condition
  evaluation and the task-442 blueprint JSON contract).
- Keep the yes/no trace honest: `_traceGraph` must not borrow a NO-branch
  effect into `fail_message` while dropping the rest.

## Acceptance

- A condition node whose NO branch carries two effects produces two effects (or
  a visible refusal), never one silent loss.
- OR and NOT conditions authored in the graph survive `compileToEngine` and
  evaluate correctly.
- `fail_message` is only set when it is genuinely the only NO-branch content.
- `node --check` clean on touched JS; targeted trigger tests and
  `python -m pytest tests/ -q -k "not mcp"` green.

## Non-goals

- Runtime blueprint materialisation and the blueprint browser — task-442
  slices 1/3.
- Editor pan/zoom/wire-deletion UX — task-388.

## Progress — 2026-09-24

Implemented in `static/js/shared/trigger-graph.js`; no engine change was needed
(the condition tree already evaluates `and`/`or`/`not` —
`engine/triggers/condition_tree.py:655-675`, covered by
`tests/test_trigger_system.py`).

- **`triggerToGraph` (import)** — no longer keeps only `conditions[0]`: every
  leaf condition is drawn as a node in the chain. A `fail_message` is drawn as a
  message effect on the last condition's NO socket, so it round-trips. A
  condition tree the linear chain cannot draw (OR/NOT, or an AND that nests one
  — `_treeIsFlat`) is stored on the trigger node as `condition_tree` +
  `condition_leaves`.
- **`_traceGraph`** — now also collects NO-branch effects and a `problems` list.
  A lone NO message becomes `fail_message`; anything else (two effects, or a NO
  branch that chains another condition) becomes a refusal reason. It no longer
  borrows one NO message while dropping the rest.
- **`compileToEngine`** — re-emits a stored `condition_tree` verbatim when the
  drawn leaves still match it (`_sameShape`, order-insensitive, numeric/string
  tolerant); if the group's conditions were edited in the graph it **refuses**
  with `compile_error` rather than flattening to AND. Only sets `fail_message`
  from a lone NO message. Clean compiles carry no `compile_error`.
- **Refusal surfacing** — `TG.compileError` / `TG.reportCompileError`, wired into
  the four save paths (`shared/trigger-graph.js` apply, `item-library.js`,
  `inspector/trigger-helpers.js`, `shared/trigger-editor.js`), so a refused
  compile cannot be saved silently.
- **Tests** — `tools/unit/test_trigger_compile_honesty.js` (7), module loaded in
  `tools/unit/run.cjs`. Verified: `node tools/unit/run.cjs` 174 passed (13
  pre-existing `test_plan_tracker.js` failures, confirmed on a clean tree);
  `node --check` clean; `npm run lint` clean; `npm run typecheck` clean;
  `python tools/js_module_index.py --check` OK; 208 trigger tests pass.

Deliberately deferred (filed): condition **group nodes** so an imported OR/NOT
group is editable again instead of refused (task-502); behavior-mode compile
honesty, where `_traceBehavior`/`compileToBehaviors` still drop NO-branch
actions (task-503).
