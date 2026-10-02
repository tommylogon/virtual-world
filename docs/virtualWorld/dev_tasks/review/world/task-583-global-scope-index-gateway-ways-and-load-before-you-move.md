---
type: task
status: review
area: world
priority: high
---

# task-583: Global scope index, gateway ways and load-before-you-move

**Filed:** 2026-09-28
**Related:** task-401, task-582

## Goal

Keep a small global index outside any chunk: scope ids, area ownership, character and unique-item location, boundary ways, and scheduled work. Gateway ways name a remote target_area_id and target_scope_id, and the movement system loads the destination scope before it resolves the way. Replace the global node and edge scans that make loaded-chunk support a claim rather than a fact.

## Acceptance

- TODO

## Implemented (2026-10-02)

New package `engine/world/`:

- `engine/world/index.py::GlobalScopeIndex` — the small resident index:
  scope parents, **area ownership** (`scope_for_area`, `areas_in_scope`),
  **id-keyed character/unique-item location** (`character_location`,
  `item_location`), **gateways** (`target_area_id`/`target_scope_id`), and
  **scheduled/due work** (`schedule`, `due_events`). `reindex(graph, manifest)`
  derives it from a whole graph; `augment_from_graph` overlays the loaded half
  without dropping entries for scopes that are not loaded; `to_dict`/`from_dict`
  persist it. A registered loader (`register_loader`) is how a scope is
  materialised on demand.
- `ensure_scope_loaded(scope_id, graph)` merges the loader's slice via
  `WorldGraph.merge_scope` (task-582). `ensure_destination_loaded(graph, way_id)`
  loads the gateway's target scope first, and returns `None` when the remote
  scope cannot be materialised.
- `virtual_world_engine.VirtualWorld.world_index` is constructed in `__init__`,
  written/restored by `engine/serialization.py` (scenario files rederive it),
  and kept in step by `NameMatching._set_player_area`.
- **Gateway ways name their remote end**: `world_compile._gateway`, the
  building-entrance way and `world_scopes.promote_to_scope` now write
  `target_area_id` + `target_scope_id` (alongside the legacy
  `area_to_id`/`child_scope_id`).
- **Load-before-you-move**: `MovementSystem.move_to_area` calls
  `ensure_destination_loaded` before resolving the target area node, and
  refuses cleanly ("leads to a place that is not loaded here") when the scope
  cannot be loaded, instead of dereferencing `None`.

Tests: `tests/test_global_scope_index.py` (9) — reindex derivation, dict
round-trip, augment preserving unloaded-scope entries, ensure-destination with
and without a loader, due-event draining, an **end-to-end crossing through a
gateway into an evicted scope** (loaded, player arrives) and the clean refusal
with no loader, plus the compiler naming the remote end.

**Remaining (not claimed):** the global node/edge *scans* in movement/matching/
serialization are not yet replaced by the index for loaded chunks — the index
exists and the load-before-move path uses it, but the "scans replaced"
acceptance needs a follow-up. The index is a derived cache, not a second source
of truth: the graph remains authoritative when whole.
