---
type: task
status: review
area: gameplay
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-702, task-691, task-714, task-809, task-810, task-811, task-801]
---

# task-812: MOSIAC: per-character context assembly (M O S I A C)

**Filed:** 2026-10-12
**Related:** task-702

<!-- deps:start -->
**Related:** [[task-702-plan-executor-runtime-the-engine-runs-typed-plans-for-any-character-with-invalidation-and-needs-override]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]], [[task-809-gimp-create-goals-at-runtime-from-verbs-and-free-actions]], [[task-810-gimp-the-goal-graph-links-blocks-and-chaining]], [[task-811-gimp-achievement-log-and-goal-replay]], [[task-801-disposition-action-features-verb-score-contributions]]
<!-- deps:end -->

## What

For one character and one turn, assemble the decision context: M and I from GIMP, O, S, and the moment's A and C.

## Why

This is the runtime state machine that feeds the actor. It is where the letters actually become one object the soak policy or the LLM reads.

## How

Read the character's GIMP (active goals, motivation, intention), their obligations and schedules, compute attention (salience) and choices (the gated verb set). Emit one context object.

## Steps to verify

1. In the 🧠 Mind panel (`InspectorMindView`), open one character's context.
   - expected: the six letters, read from real state (M and I from the goal layer, O the obligations, S the schedule, A the salient vitals, C the affordable verbs).
   - observed: VERIFIED 2026-10-13, live on localhost:4444. The panel's "MOSIAC - the decision context" block rendered M/I/O/S/A/C: Intention "obligation to Elder Mara", Obligations "Burn the warrant", Schedule "08:00 patrol at Gate", Attention "nothing pressing", Choices "activity 12 / free 27 / major 31 / minor 19". M was empty because that goal carries no authored motivation - the honest empty, not a blank filled in.
2. The same context is what the LLM prompt renders.
   - observed: VERIFIED 2026-10-13. `PromptBuilder.buildMosiacContext(player)` returns `=== YOUR MIND (MOSIAC) ===` with the same letters; it is registered as a context section and included in the think/decide prompt (`turn-prompts.ts`), reading `Player.mosiac` from state rather than re-deriving it.

## Acceptance

- [x] The context carries all six letters from real sources.
- [x] The same context is what the LLM prompt renders.

## Files

- `engine/mosiac.py`
- `engine/serialization.py`
- `static/js/inspector/mind-view.ts`
- `static/js/agent/prompt-builder/character-state.ts`
- `static/js/agent/prompt-builder/context-sections.ts`
- `static/js/agent/prompt-builder/turn-prompts.ts`

## Progress (2026-10-13)

- `engine/mosiac.assemble(gs, player)` reads the six letters from `Player.goals` / `obligations` / `schedule`, the vitals and the clock, and the tier table against `turn_slots`. Shipped on the player payload as `mosiac`.
- Mind panel: a MOSIAC block at the top of the left column.
- LLM: a `mosiac` context section, included in the think/decide prompt.
- `tests/test_mosiac.py`: 5 tests (attention salience and its empty case, all six letters from state, the fallbacks, a spent tier dropping its verbs).
