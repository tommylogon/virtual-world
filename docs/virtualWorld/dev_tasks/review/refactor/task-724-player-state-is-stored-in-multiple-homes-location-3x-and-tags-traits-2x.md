---
type: task
status: review
area: refactor
priority: high
wiki: "[[Feature Map]]"
---

# task-724: Player state is stored in multiple homes: location (3x) and tags/traits (2x)

**Filed:** 2026-10-06
**Related:** task-625, task-446, task-716, task-725

## What

A character's state is stored in more than one home and the read paths do not all agree. Measured on `kraktooth_goblin_camp.json`: location had three representations - `player.current_area` (name), `player.current_area_id`, and the graph `in` edge - all consistent, but the `in` edge alone suffices as the positional source and the two Player fields were redundant copies. `tags` and `traits` existed on both the Player object and the character node's properties. `personality`/`description`/`base_description` are authored on the node only - the players block correctly omits them - but the LLM prompt (`room-context.ts:143,606`) and the Mind/Bio surfaces read them off the Player, so they were silently absent from every prompt.

Resolved model:
- **Authored definition** (`personality`, `base_description`/`description` prose, authored `tags`/`traits`) -> the **character node's `properties`**. One persisted home. The Player reads it for prompts and the UI (a projection, not a second source).
- **Runtime state** (`vitals`, `memories`, `emotion`, `plan`, `position`, `fear_tags`) -> the **Player**. Not duplication.
- **Derived** (`current_area` name / `current_area_id`; the Player's mirrored `tags`/`traits`) -> **not persisted**; recomputed from the `in` edge / node on load.
- `to_scenario_dict` strips definition (`personality`, `base_description`, `description`, `tags`, `traits`) and derived location (`current_area`, `current_area_id`) from the `players` block.
- `handle_update_player` mirrors edits to `tags` and `traits` directly to the character node properties alongside prose definition.
- `_serialize_player` publishes `current_area`, `current_area_id`, `tags`, and `traits` projection synchronously for UI and prompt builder.

## Acceptance

- [x] Decide the single authoritative home for a character's location, and either feed or retire the other two (the graph `in` edge is the single persisted spatial source; `current_area` and `current_area_id` are derived and stripped from scenario files).
- [x] Decide whether `tags`/`traits` on the character node are authoritative, a mirror, or a leak; make the AGENTS.md invariant statement match reality (character node `properties` is the single persisted home for authored definition; Player has runtime cache/projection).
- [x] Authoring edits via `handle_update_player` mirror `tags` and `traits` to the character node properties.
- [x] `to_scenario_dict` strips `current_area`, `current_area_id`, `tags`, and `traits` from `players[pname]`.
- [x] `load_from_dict` hydrates `p.tags` and `p.traits` from node properties, triggers `p.sync_vitals_with_tags()`, and sets `p.current_area` from the `in` edge.
- [x] Unit and regression tests prove single persisted home and roundtrip survival (`test_task_724_single_persisted_home_for_location_and_definition` in `tests/test_serialization.py`).

## Non-goals

- Merging the `Player` model with the character node (intended split, task-463).
- Retiring `__`-suffixed identities (task-446).
- The general duplicated-concept inventory (task-625).

## How

1. Location: Made the graph `in` edge the single positional source. `to_scenario_dict` strips `current_area` and `current_area_id` from the `players` block. `load_from_dict` derives `p.current_area` from `graph.area_of(pnode_id)` on boot.
2. Definition (tags/traits): Updated `handle_update_player` in `routes/player_ops.py` to mirror `tags` and `traits` to the character node properties.
3. In `engine/serialization.py:to_scenario_dict`, ensured active player definition is reflected on the character node before serialization, then stripped redundant `tags`, `traits`, `current_area`, and `current_area_id` from `pdata`.
4. In `engine/serialization.py:load_from_dict`, ensured `p.sync_vitals_with_tags()` executes upon tag hydration from node properties.
5. In `tests/test_serialization.py`, added regression test `test_task_724_single_persisted_home_for_location_and_definition` verifying all 4 redundant fields are absent from scenario player blocks and restored on reload.

## Steps to verify

1. `python -m pytest tests/test_serialization.py` (20 passed).
2. `python -m pytest tests/test_traits.py` (75 passed).
3. `python -m pytest tests/test_scenario_graph_only.py` (9 passed).
4. `python -m pytest tests/test_player_map.py` (21 passed).
5. `node tools/unit/run.cjs` (780 passed across 57 files).

## Files

- `engine/serialization.py`
- `routes/player_ops.py`
- `tests/test_serialization.py`
