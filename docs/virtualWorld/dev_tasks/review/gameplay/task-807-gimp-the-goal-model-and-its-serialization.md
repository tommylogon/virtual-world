---
type: task
status: review
area: gameplay
priority: high
wiki: "[[Character Pursuits]]"
related: [task-700, task-702, task-691, task-714]
---

# task-807: GIMP: the Goal model and its serialization

**Filed:** 2026-10-12
**Related:** task-700, task-702

<!-- deps:start -->
**Related:** [[task-700-grounded-plan-contract-the-llm-plan-phase-emits-typed-steps-validated-against-world-facts]], [[task-702-plan-executor-runtime-the-engine-runs-typed-plans-for-any-character-with-invalidation-and-needs-override]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]]
<!-- deps:end -->

## What

The goal layer's data: a Goal (what a character wants to achieve), its status, and its links to Motivation and Intention. Authored and runtime-created.

## Why

Goals live outside MOSIAC but there is no model for them. Everything in GIMP needs it first.

## How

A Goal record with target, status (proposed/active/reached/blocked/dropped), and refs to motivation/intention. Round-trip through serialization; default absent for existing saves.

## Steps to verify

1. In the graph editor, author a goal on a character; save; reload the scenario.
   - expected: the goal round-trips with its status and its Motivation/Intention links.
   - observed: TODO
2. In the app, open the 🧠 Mind panel (`InspectorMindView`) for that character.
   - expected: the goal is listed (the goals section is task-714's addition to this panel).
   - observed: TODO

## Acceptance

- [x] A Goal round-trips through save/load.
- [x] A character can hold zero, one or many goals.

## Progress (2026-10-12) - the model and its serialization

- `engine/goals.py`: `GOAL_STATUSES`, `slug`, `normalize` (drops a goal with neither an
  id nor a `what`, derives the id from `what`, coerces an unknown status to `proposed`),
  `active`, `describe`.
- `Player.goals` on the character record, beside `schedule`. Serialized in the players
  block and normalised on load (`engine/serialization.py`).
- `tests/test_goals.py` - 5 tests, including a full scenario round-trip.

Not yet, and by design of the cards: no surface reads a goal (the Mind panel is task-714),
no scenario authors one (the editor is task-808, runtime creation is task-809), and MOSIAC
does not consume it yet (task-812).

## Files

- `engine/goals.py`
- `engine/serialization.py`
- `player.py`
- `tests/test_goals.py`
