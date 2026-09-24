---
type: task
status: todo
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
