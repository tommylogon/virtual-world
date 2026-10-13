---
type: task
status: todo
area: characters
priority: medium
wiki: "[[Character Pursuits]]"
---

# task-818: Retire the pursuit node type: a pursuit is character data, only its templates stay in the library

**Filed:** 2026-10-12
**Related:** task-426, task-807

<!-- deps:start -->
**Related:** [[task-426-plan-archetypes-and-group-goals]], [[task-807-gimp-the-goal-model-and-its-serialization]]
<!-- deps:end -->

## What

The `pursuit` node type models an actor-bound undertaking as a world node. Per the 2026-10-12 decision, a pursuit is character-private data, not a physical entity in the world, so it does not belong in the graph. Retire the node type: keep `data/library/pursuit_templates/` as the template library, and leave the character's own state where it already is on `Player.active_pursuit` / `Player.plan` / `Player.completed_pursuits`.

## Why

Nodes are physical entities in the world (areas, ways, items, characters). A pursuit is an intention, and intentions live in the mind of the character. The `pursuit` node type is authored by no scenario (0 across `data/`), so it is a dead end that additionally forces a legacy coercion on load.

## How

Remove `PURSUIT_NODE_TYPE` and the assignment-node path in `engine/background_plans.py` (selection currently scans `pursuit` nodes). Drop the legacy `plan` / `schedule_template` -> `pursuit` node coercion in `engine/serialization.py` (the `_coerce_*` block around lines 78-97). Keep `data/library/pursuit_templates/` and the character-side state untouched. Update `tests/test_background_plans.py`, which authors `pursuit` nodes via its `_plan_node` helper, to drive the character-side path instead.

## Steps to verify

1. Run `python -m pytest tests/test_background_plans.py tests/test_serialization.py`.
   - expected: a background pursuit still starts, advances and completes, and the suite passes with no `pursuit` node authored.
   - observed: TODO

## Acceptance

- No `pursuit` node type remains in `engine/`.
- `engine/background_plans.py` selects and advances a pursuit from character data, not from graph nodes.
- The `plan`/`schedule_template` -> `pursuit` coercion is gone and no legacy save depends on it.
- `tests/test_background_plans.py` passes without authoring a node.

## Files

- `engine/background_plans.py`
- `engine/serialization.py`
- `tests/test_background_plans.py`
- `docs/virtualWorld/design/Character Pursuits.md`
