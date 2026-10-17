---
type: task
status: review
area: world
priority: high
related: ['task-401', 'task-582', 'task-584', 'task-581', 'task-439']
wiki: "[[World Building/World Scopes|World Scopes]]"
---

# task-583: Global scope index, gateway ways and load-before-you-move

**Filed:** 2026-09-28
**Related:** task-401, task-582

<!-- deps:start -->
**Related:** [[task-401-chunk-persistence-and-gateway-ways]], [[task-582-chunk-load-unload-and-merge-apis-on-worldgraph]], [[task-584-cross-chunk-ownership-rules-for-carried-items-triggers-and-delayed-events]], [[task-581-stable-area-ids-and-one-authoritative-location-for-characters-and-items]], [[task-439-canonical-area-identity-in-save-and-lookups]]
<!-- deps:end -->

## What

Keep a small global index outside any chunk: scope ids, area ownership, character and unique-item location, boundary ways, and scheduled work. Gateway ways name a remote target_area_id and target_scope_id, and the movement system loads the destination scope before it resolves the way. Replace the global node and edge scans that make loaded-chunk support a claim rather than a fact.

## Acceptance

- Production app startup and world replacement register a durable scope loader.
- Unloading a loaded scope persists its graph slice before eviction; a missing
  chunk remains an explicit load failure.
- A scope can be evicted, loaded from disk after process/world reconstruction,
  and crossed through a gateway without duplicating character location.
- The Kraktooth fixture benchmark reports its actual scope/node/edge counts,
  saved chunk bytes, focused response bytes, and elapsed times.
- Remaining global graph scans in movement, matching, and serialization are
  separately identified and not claimed complete by the loader work.

## Implemented (2026-10-16)

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
- `engine/world/store.py::WorldChunkStore` persists each unloaded scope as an
  atomically replaced JSON slice under the configured data directory. The
  app registers the store on startup and re-registers it whenever a world is
  replaced or restored. A stable storage id survives savegame adoption and is
  omitted from authored scenario files. `GlobalScopeIndex.unload()` writes the
  current slice before removing its nodes; a missing or corrupt persisted slice
  is not treated as a successful load.
- The character runtime route uses the registered loader when its character's
  owning area has been evicted. This is a focused reload from disk, not a
  projection filtered out of a fully materialized graph.
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

**Remaining (not claimed):** some global node/edge scans in movement, matching,
and serialization still need to be replaced by indexed lookups. Scope selection
in the graph editor is a client-side projection and does not unload data from the
authoritative server graph. The index is a derived cache, not a second source of
truth: loaded graph data remains authoritative, while persisted slices supply
scopes explicitly loaded after eviction.

## Why

The resident graph is the working set, not necessarily the entire world. Gateway
movement and focused runtime reads need to materialise an evicted scope from
durable data; an in-memory callback registered only in tests cannot do that.
The global index remains the authority for finding the unloaded scope and its
gateway/location metadata.

## How

Persist one owned-node graph slice per scope under a stable per-world directory.
Register its loader and saver on the world's `GlobalScopeIndex` at app startup
and after any world replacement. The saver runs before eviction; the loader
returns the stored slice for `merge_scope()`. Keep scope-less characters and
unique items canonical, and restore their indexed location edges when the area
is loaded. Use the Kraktooth scenario for a practical fixture benchmark rather
than treating a hypothetical million-area world as a prerequisite for this
loader.

## Steps to verify

1. Run `python -m pytest tests/test_chunk_lifecycle.py tests/test_runtime_state.py tests/test_global_scope_index.py tests/test_world_chunks.py tests/test_world_scopes.py tests/test_world_grid_routes.py`.
   - expected: production storage survives unload/restart, gateway and location are restored, and the runtime route reloads an evicted character scope.
   - observed: 121 passed in 20.36s (2026-10-16).
2. Run `python tools/benchmark_scope_loader.py`.
   - expected: Kraktooth scopes are saved, then a single focused request reloads only the selected character's scope and reports response size and timings.
   - observed: 629 areas, 2,766 nodes, 6,342 edges in 6 scopes; whole-state response 8,644,489 bytes / 434.05 ms; 6 chunks / 3,168,272 bytes saved during unload-all (322.59 ms); focused reload returned 129 nodes / 97 edges in 222,494 bytes, loading only `goblin_camp` in 20.78 ms (single local run, not a general scale claim).

## Browser UI and intended live verification

Intended UI home: Live turn interface; character focus and gateway movement
request scopes through the focused runtime endpoint.

Current availability: The runtime route is wired to the production scope store
and is exercised through Flask's test client, including loading an evicted
character scope. A scheduler-driven Kraktooth human turn also loaded
`goblin_camp`, moved Arix through an open way, and refreshed the same scope
without a whole-state action refresh. The graph editor's scope picker selects a
client-side graph projection; it is not an eviction control.

Live steps when available:

1. Focus a character whose area scope was evicted, then cross a gateway into an
   evicted destination.
   - expected: each requested scope is loaded from disk and its character
     location remains canonical.
   - observed: the focused route reload and gateway/load lifecycle pass in
     targeted tests. The live browser movement stayed within the already-loaded
     `goblin_camp`; live eviction and cross-scope materialization remain untested.

This section defines the intended access point and acceptance path. It is not a
claim that the UI or complete behavior exists or works today; Current
availability records the present state, and these steps describe how to verify
the intended behavior when it is available.

## Files

- `engine/world/index.py`
- `engine/world/store.py`
- `engine/world_scopes.py`
- `engine/serialization.py`
- `graph.py`
- `virtual_world_engine.py`
- `app.py`
- `routes/saveload.py`
- `routes/world_grid_ops.py`
- `routes/runtime_ops.py`
- `tests/test_chunk_lifecycle.py`
- `tests/test_runtime_state.py`
- `tools/benchmark_scope_loader.py`
