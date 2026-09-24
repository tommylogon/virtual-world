---
type: task
status: todo
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
