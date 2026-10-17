---
type: task
status: review
area: gameplay
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-702, task-691, task-714, task-810, task-811, task-812]
blocked_by: [task-807]
---

# task-809: GIMP: create goals at runtime from verbs and free actions

**Filed:** 2026-10-12
**Related:** task-702

<!-- deps:start -->
**Blocked by:** [[task-807-gimp-the-goal-model-and-its-serialization]]
**Related:** [[task-702-plan-executor-runtime-the-engine-runs-typed-plans-for-any-character-with-invalidation-and-needs-override]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]], [[task-810-gimp-the-goal-graph-links-blocks-and-chaining]], [[task-811-gimp-achievement-log-and-goal-replay]], [[task-812-mosiac-per-character-context-assembly-m-o-s-i-a-c]]
<!-- deps:end -->

## What

A character (or a player) can set a new goal, complete one, or drop one during play - hand-authored not required.

## Why

Goals chain up from need: a verb or free action creates a goal, which MOSIAC then works toward. Editor-only authoring would freeze goals at design time.

## How

A set_goal / complete_goal / drop_goal free action (or verb) writing the Goal model. Validate against world state (a goal is a want, not a world change).

## Steps to verify

1. In a live session, issue the set-goal action, then complete one, then drop one.
   - expected: the goal appears, changes status and disappears in the 🧠 Mind panel (`InspectorMindView`) and in GET /api/state.
   - observed: TODO

## Acceptance

- [x] A goal can be created, completed and dropped at runtime.
- [x] The action is authorable in the action tiers.

## Progress (2026-10-12)

- `engine/goals.py`: `find`, `set_goal`, `set_status` (completing is `reached`, dropping is `dropped`).
- `engine/action_tiers.py`: `goal` classified `free`; the browser mirror `static/js/agent/action-tiers.ts` regenerated.
- `routes/action_handlers.py`: the `goal` verb - bare `goal` lists, `goal set <what>`, `goal complete <goal>`, `goal drop <goal>`. It reads the raw command so a runtime goal keeps the player's capitalisation (the dispatcher lower-cases `cmd`).
- `tests/test_goals.py`: the engine helpers plus one wiring test that posts to `/api/action` and asserts the character's goals change.

Not yet: the Mind panel does not show a goal (task-714), so verify step 1 cannot be observed end-to-end until 714 lands.

## Files

- `engine/action_tiers.py`
- `engine/goals.py`
- `engine/serialization.py`
- `routes/action_handlers.py`
- `tests/test_goals.py`
- `static/js/agent/action-tiers.ts`
