---
type: task
status: review
area: refactor
priority: high
---

# task-581: Stable area ids and one authoritative location for characters and items

**Filed:** 2026-09-28
**Related:** task-401, task-446

## Goal

Replace the display-name current_area convention with stable area ids, and name exactly one authoritative location record per character and per unique item, so a duplicated human-readable area name can never split an entity's location. This is the precondition for chunk unload: a chunk cannot own a stale copy of a character.

## Acceptance

- TODO

## Implemented (2026-10-02) — location record is id-keyed and single

The chunk-critical half of this task: location is addressed by **id**, and the
graph holds exactly **one** authoritative record per entity.

- `graph.WorldGraph.area_of(entity_id)` — the id of the area an entity occupies
  from its `in` edge. `set_area_of(entity_id, area_id)` — replaces every existing
  `in` edge, so there is exactly one location record; refuses a non-area.
- `engine/matching._set_player_area` resolves the destination **deterministically
  by id, then unambiguous name** (`engine.room_perception.resolve_area_node`,
  task-439) instead of taking the first same-named node in iteration order, and
  keeps the global index's id-keyed `character_location` in step (task-583).
- `engine/serialization._serialize_world` exposes `current_area_id` (the
  canonical id) alongside the display-name `current_area` for every player, and
  `load_from_dict` **prefers the loaded `in` edge over the saved string**, so a
  hand-edited/half-written save cannot re-home a character.

Tests: `tests/test_location_identity.py` (6) — `area_of` reads the edge,
`set_area_of` keeps a single record, a duplicate name cannot re-home, the
payload carries the id, and load prefers the edge over the name.

**Remaining (why this stays in review, not done):** the *field* is still a
display name — `Player.current_area` holds a name and 40+ engine/frontend sites
read it by name. The full "replace the convention" rename (store an id, derive
the name for display) is not done; the id-keyed read side (`area_of`,
`current_area_id`, `world_index.character_location`) is the API a chunk consumer
should use, and the display-name map is documented as a resolution layer. The
`areas`/`rooms` name-keyed frontend projection (task-439) depends on that
rename and cannot be retired first.

Regression: full suite 15 failed / 6660 passed; the **same 15 names fail on a
clean `master` worktree** (task-457 canonical identity + `kraktooth_goblin_camp`
data drift), verified by A/B, so none are from this change.
