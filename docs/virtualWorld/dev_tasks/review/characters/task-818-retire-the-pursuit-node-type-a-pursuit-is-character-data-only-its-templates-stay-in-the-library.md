---
type: task
status: review
area: characters
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-426, task-807, task-702, task-716]
---

# task-818: Retire the pursuit node type: a pursuit is character data, only its templates stay in the library

**Filed:** 2026-10-12
**Related:** task-426, task-807

<!-- deps:start -->
**Related:** [[task-426-plan-archetypes-and-group-goals]], [[task-807-gimp-the-goal-model-and-its-serialization]], [[task-702-plan-executor-runtime-the-engine-runs-typed-plans-for-any-character-with-invalidation-and-needs-override]], [[task-716-fisherman-vertical-slice-reusable-water-activity-and-pursuit-loop]]
<!-- deps:end -->

## What

The `pursuit` node type modeled an actor-bound undertaking as a world node. Per the 2026-10-12 decision, a pursuit is **character-private data, not a physical entity**, so the node type is retired.

`engine/background_plans.py` no longer declares `PURSUIT_NODE_TYPE` or scans the graph: the runner resumes the character's own `Player.active_pursuit`, rebuilding `Player.plan` from the assignment's template and bindings. `Player.active_pursuit` / `Player.plan` / `Player.completed_pursuits` and `data/library/pursuit_templates/` are untouched. The legacy `type: "plan"` (and `template` / `schedule_template`) → `pursuit` node coercion is dropped from serialization.

## Why

Nodes are physical entities in the world (areas, ways, items, characters). A pursuit is an intention, and intentions live in the mind of the character. The `pursuit` node type is authored by no scenario (0 across `data/`; kraktooth already carried `active_pursuit`, not a node), so it was a dead end that additionally forced a legacy coercion on load.

## How

- `build_plan(pursuit)` now takes the character-side assignment dict and resolves it with `pursuit_templates.bind` (the raw bindings - `source` / `item` / `sink` / `source_tags` / `home` / `rally_area` - are the same authored shape the node props used). The plan carries `assignment_id`, not `node_id`.
- `maybe_assign(sim, p)` only resumes `Player.active_pursuit`; it emits `pursuit:<label>:start` when the plan first runs (`step_index == 0`), so the trace vocabulary is unchanged.
- `_finish` / `_sync_pursuit_step` key on `assignment_id`.
- Removed `PURSUIT_NODE_TYPE`, the node scan, `_is_actor`, `_source_reachable`, `MAX_PARTICIPANTS`, and `_migrate_legacy_pursuit_nodes` (plus its load-time call).
- `tools/add_scrap_run.py` writes the assignment onto the player block instead of a `pursuit` node.
- `tests/test_background_plans.py` sets `Player.active_pursuit` directly (`_assign`) and adds a regression test that a leftover `pursuit` node starts nothing.

## Steps to verify

1. Run `python -m pytest tests/test_background_plans.py tests/test_serialization.py`.
   - expected: a background pursuit still starts, advances and completes, and the suite passes with no `pursuit` node authored.
   - observed: PASS 2026-10-13 - **24 passed** (8 + 16). `test_a_pursuit_node_is_no_longer_selected` additionally proves a leftover `pursuit`-typed node now starts nothing (an unassigned character keeps `plan is None` and `active_pursuit is None`).

## Acceptance

- [x] No `pursuit` node type remains in `engine/` (only the lived-log record *kind* `"pursuit"`, which is not a node type).
- [x] `engine/background_plans.py` selects and advances a pursuit from character data (`Player.active_pursuit`), not graph nodes.
- [x] The `plan` / `schedule_template` -> `pursuit` coercion is gone; no live save holds a `pursuit` node (kraktooth: 0).
- [x] `tests/test_background_plans.py` passes without authoring a node.

## Files

- `engine/background_plans.py` (character-data resume; node path removed)
- `engine/serialization.py` (legacy coercion removed)
- `tests/test_background_plans.py` (character-side path + the ignored-node regression)
- `tools/add_scrap_run.py` (authors `Player.active_pursuit`, not a node)
- `docs/virtualWorld/design/Character Pursuits.md` (the seam description)

## Browser UI and intended live verification

Intended UI home: Select a character in the world, then open Inspector → Mind → Pursuit & plan. The graph remains the physical-world view; it is not the home for a character's pursuit.

Current availability: Character-side assignment and plan rendering are implemented. This card records engine and serialization tests, but no browser check for this retirement is recorded here.

Live steps when available:
1. Load `kraktooth_goblin_camp`, select Vekka, open Mind, and scroll to Pursuit & plan.
   - expected: Vekka's active pursuit is shown from her character record with its plan; the panel does not require a pursuit graph node.
2. Open `/api/state` in the same running app and inspect `graph.nodes` and `players.Vekka`.
   - expected: Vekka's `active_pursuit` is in the player record and no graph node has `type: "pursuit"`.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
