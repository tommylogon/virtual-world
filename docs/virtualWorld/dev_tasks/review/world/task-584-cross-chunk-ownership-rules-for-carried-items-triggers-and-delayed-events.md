---
type: task
status: review
area: world
priority: medium
---

# task-584: Cross-chunk ownership rules for carried items, triggers and delayed events

**Filed:** 2026-09-28
**Related:** task-401, task-581, task-583

## Goal

Decide and implement who owns a character, a carried or equipped item, a live trigger and a delayed event while its scope is unloaded, and make the answer consistent across a save and load round trip. A delayed event aimed at an unloaded node is globally indexed and either loads the scope when due or resolves through an explicit deferred policy; dropping it silently is forbidden.

## Acceptance

- TODO

## Implemented (2026-10-02)

The ownership rule, stated once: **a character and its carried/equipped items
are owned by the character; a trigger is owned by whatever triggers it; the
chunk owns only its own stamped nodes.**

- `engine/world/index.py`: the index records **every** node's owner
  (`scope_for_node`), not just areas, so a due event can find which scope to
  load. `GlobalScopeIndex.unload(graph, scope_id)` records the location of
  characters/items that survive the eviction, and `restore_locations` re-adds
  their `in` edges once the area is loaded again (folded into
  `ensure_scope_loaded`). Idempotent.
- `graph.WorldGraph.unload_scope`: a `logic_trigger` referenced only from a
  removed node is cleaned up (`orphaned_triggers`); one shared with a surviving
  owner is kept. A carried/equipped item edge never has an endpoint in the
  chunk, so it is untouched — the character keeps its gear across an unload.
- `virtual_world_engine._process_delayed_events`: a due event whose target is
  missing tries to load its owner scope via the index; if it still cannot be
  found it is **deferred** (re-queued for the next tick, `deferred_delayed_events`),
  and after 10 attempts **recorded as unresolved** (`unresolved_delayed_events`)
  and surfaced in the log. The old silent `continue` is gone.

Tests: `tests/test_cross_chunk_ownership.py` (6) — character/carried-item
survival, location restore, orphan-trigger cleanup with a shared trigger kept,
a due event loading its scope and firing, and an unloadable target being
deferred then unresolved. `tests/test_delayed_events.py`'s
`test_dead_target_node_is_skipped` was **rewritten** to
`test_dead_target_node_is_deferred_not_silently_dropped` because its old
assertion pinned exactly the silent drop this task forbids.

Consistency across a save/load round trip: the index (including
`character_location`/`item_location`) is persisted by `engine/serialization.py`;
a scenario rederives it from the graph + manifest.
