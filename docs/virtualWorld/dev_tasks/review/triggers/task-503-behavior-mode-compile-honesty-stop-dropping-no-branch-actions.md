---
type: task
status: review
area: triggers
priority: medium
---

# task-503: Behavior-mode compile honesty: stop dropping NO-branch actions

**Filed:** 2026-09-24
**Related:** task-501, task-388

## Goal

Make compileToBehaviors honest: a condition NO branch that carries actions must compile or be visibly refused, never silently dropped.

## Context (verified 2026-09-24)

`_traceBehavior` (`static/js/shared/trigger-graph.js`) walks a condition's
`output_no` wire but explicitly discards what it finds ("there's no else in the
behavior model, so we don't fold NO actions into the YES path. Kept for
structural parity"). `compileToBehaviors` therefore silently drops any authored
NO-branch action. task-501 fixed the trigger-mode path (`_traceGraph` /
`compileToEngine`); this is the behavior-mode twin.

Behaviors are an array, so a refusal has to be surfaced the way task-501 does for
triggers — a visible error rather than a silent drop.

## Acceptance

- A behavior whose condition NO branch carries actions either compiles those
  actions honestly or is visibly refused; it is never silently dropped.
- `compileToBehaviors` reports the refusal through the same surfacing path as
  `compileToEngine` (`compileError`/`reportCompileError` or equivalent), and the
  behaviors editor refuses to save.
- JS unit coverage for the NO-branch case; `node --check` clean; lint/typecheck
  clean.

## Non-goals

- Condition group nodes (task-502).
- Engine-side behavior evaluation changes.

## Progress — 2026-09-24

Implemented in `static/js/shared/trigger-graph.js`; no engine change (the
behavior model genuinely has no else, so the honest outcome is a refusal).

- `_traceBehavior` now accumulates a `problems` list and flags a condition whose
  NO branch carries any action(s) or chains another condition, instead of
  discarding it ("Kept for structural parity").
- New `TG.compileToBehaviorsWithIssues(graph)` returns `{behaviors,
  compile_error}`; `TG.compileToBehaviors(graph)` delegates and returns just the
  array, so existing callers are unchanged.
- `inspector/behaviors-view.js` saves through the detailed form and refuses the
  save via `TriggerGraph.reportCompileError` — the same surfacing path as
  task-501.
- Tests: two added to `tools/unit/test_trigger_compile_honesty.js` (a NO-branch
  action is refused; a clean graph compiles without a refusal). Verified:
  `node tools/unit/run.cjs` 176 passed (13 pre-existing `test_plan_tracker.js`
  failures); `node --check`/`npm run lint`/`npm run typecheck` clean.
