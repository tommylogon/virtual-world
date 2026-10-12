---
type: task
status: todo
area: gameplay
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-702, task-691, task-714]
---

# task-812: MOSIAC: per-character context assembly (M O S I A C)

**Filed:** 2026-10-12
**Related:** task-702

<!-- deps:start -->
**Related:** [[task-702-plan-executor-runtime-the-engine-runs-typed-plans-for-any-character-with-invalidation-and-needs-override]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]]
<!-- deps:end -->

## What

For one character and one turn, assemble the decision context: M and I from GIMP, O, S, and the moment's A and C.

## Why

This is the runtime state machine that feeds the actor. It is where the letters actually become one object the soak policy or the LLM reads.

## How

Read the character's GIMP (active goals, motivation, intention), their obligations and schedules, compute attention (salience) and choices (the gated verb set). Emit one context object.

## Steps to verify

1. In the 🧠 Mind panel (`InspectorMindView`), open one character's context.
   - expected: all six letters populated from real state (M and I from GIMP, O, S, and the moment's A and C).
   - observed: TODO
2. In the app, open the LLM Inspector (`VW.inspector.showAgent`) for that character.
   - expected: the built request renders the same context.
   - observed: TODO

## Acceptance

- [ ] The context carries all six letters from real sources.
- [ ] The same context is what the LLM prompt renders.

## Files

- `engine/disposition.py`
- `engine/background_simulation.py`
