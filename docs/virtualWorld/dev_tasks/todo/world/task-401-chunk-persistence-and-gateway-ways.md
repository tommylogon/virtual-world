---
type: task
status: todo
area: world
priority: medium
children: [task-581, task-582, task-583, task-584]
blocked_by: [task-397, task-398, task-399, task-400]
wiki: "[[World Building/World Scopes]]"
---

# task-401: Chunk persistence, scoped indexes, and gateway ways

**Filed:** 2026-09-08  
**Depends on:** task-397 through task-400.  
**Split 2026-09-28** into the four sub-tasks below. This file is the umbrella: the
goal, the reasoning and the acceptance for the whole effort stay here, the work
does not.

<!-- deps:start -->
**Blocked by:** [[task-397-world-scope-hierarchy-and-projection]], [[task-398-deterministic-structure-generation]], [[task-399-background-character-simulation-and-reactivation]], [[task-400-pines-world-scale-vertical-slice]]
**Children:** [[task-581-stable-area-ids-and-one-authoritative-location-for-characters-and-items]], [[task-582-chunk-load-unload-and-merge-apis-on-worldgraph]], [[task-583-global-scope-index-gateway-ways-and-load-before-you-move]], [[task-584-cross-chunk-ownership-rules-for-carried-items-triggers-and-delayed-events]]
<!-- deps:end -->

## Sub-tasks

| Sub-task | Covers |
|---|---|
| [task-581](../../refactor/task-581-stable-area-ids-and-one-authoritative-location-for-characters-and-items.md) | Stable area ids; one authoritative location record per character and unique item. The precondition - display-name `current_area` cannot survive duplicate names across chunks. |
| [task-582](../../world/task-582-chunk-load-unload-and-merge-apis-on-worldgraph.md) | `WorldGraph` load / unload / merge APIs with ownership checks. `load_from_dict()` clears the graph, so it cannot be the chunk loader. |
| [task-583](../../world/task-583-global-scope-index-gateway-ways-and-load-before-you-move.md) | The global index, gateway ways naming a remote `target_area_id` + `target_scope_id`, load-before-resolve in movement, and replacing global node/edge scans. |
| [task-584](../../world/task-584-cross-chunk-ownership-rules-for-carried-items-triggers-and-delayed-events.md) | Ownership and transaction rules for carried/equipped items, triggers and delayed events across an unload; the deferred-event policy. |

Order: 581 → 582 → 583 → 584. Each is independently reviewable, and 581 is
worth landing on its own merits: it removes a real correctness hazard (a
duplicate area name splitting a character's location) whether or not chunking
ever happens.

## What

Turn the proven scope model into real scale: materialized scopes can be loaded
and evicted independently while remaining part of one persistent world.

## Requirements

- Store graph subsets by scope/chunk plus a small global index for scope ids,
  area ownership, character location, unique item location, boundary ways, and
  scheduled/due work.
- Load a destination chunk before the existing movement system resolves a way.
- A boundary/gateway way identifies its remote `target_area_id` and
  `target_scope_id`; it is not a dead UI shortcut.
- Replace global node/edge scans with indexes for loaded chunks before claiming
  large-world support.
- Define cross-chunk ownership/transaction rules for characters, carried and
  equipped items, triggers, and delayed events.
- Preserve direct/fast-travel ways and route/grid ways as authored choices.

## Critical constraints

`WorldGraph.load_from_dict()` clears the current graph, so it cannot be used as
the chunk loader. Add explicit merge/unload APIs with ownership checks and
tests. Similarly, the current editor fetches all graph nodes/edges and must
use task-397's projection endpoints once chunks exist.

Characters are authoritative in the serialized `players` block as well as
having graph anchors. Chunk movement must update both consistently; a chunk
cannot independently serialize a stale copy of a character. Before unloading,
introduce stable area IDs and one authoritative character/item-location rule:
many current systems still use display-name `current_area`, which is unsafe
when separate chunks can contain duplicate human-readable names.

Delayed events targeting unloaded nodes must be globally indexed and either
load the relevant scope when due or resolve through an explicit safe deferred
policy. Silently dropping them is forbidden.

## Acceptance

This umbrella is satisfied when all four sub-tasks are in `done`. The criteria
below are the aggregate the sub-tasks have to add up to; the last one is
task-402's to measure and is only claimed here as a dependency, not re-done.

- Load two adjacent chunks, move an agent/item across a gateway, unload and
  reload both, and retain exactly one authoritative location.
- A save/load round-trip preserves gateway links and due events.
- An editor scope request never returns the whole world graph.
- Benchmark/report node/edge counts loaded for the requested scope.

## Non-goal

This task is not required to prove task-400. It is the first step that makes a
million-node world technically credible.

## Aggregate verification (2026-10-02)

The four sub-tasks are implemented and in **review** (581, 582, 583, 584); this
umbrella stays `todo` per its own rule ("satisfied when all four sub-tasks are in
`done`" - that final move is the reviewers', not this lane's).

What *is* demonstrated now, end-to-end, by `tests/test_chunk_lifecycle.py` (4):

- **"Load two adjacent chunks, move an agent across a gateway, unload and reload
  both, retain exactly one authoritative location."** A `town` chunk with a
  gateway to an `inn` chunk; `move_to_area("enter the inn")` loads `inn` on
  demand (task-583); unloading both leaves the character alive with its location
  remembered by id (task-584); reloading restores **exactly one** `in` edge to
  `area_inn_hall` (task-581/582).
- **"A save/load round-trip preserves gateway links and due events."**
  `to_dict()` → `load_from_dict()` keeps `world_index.gateway(way_gate)` with
  its `target_area_id`/`target_scope_id` and the scheduled event at tick 42.
- **"A gateway is not a dead UI shortcut."** Crossing it actually materialises
  the remote area and moves the character.

Still open for the umbrella to close: the benchmark/report half (task-402
territory) and the editor-scope-request half; the global node/edge **scans** are
not yet fully replaced by the index (noted in task-583). Those are the reasons
the sub-tasks are in review rather than done.

## Why

The scope model (task-397-400) needs to support real scale: materialized scopes loaded/evicted independently while remaining part of one persistent world. Chunk persistence requires explicit merge/unload APIs (load_from_dict clears graph), stable area IDs and one authoritative location rule (display-name current_area is unsafe across duplicate names), gateway ways with target_area_id/target_scope_id, load-before-resolve in movement, index-based lookups replacing global scans, and cross-chunk ownership rules for carried/equipped items, triggers and delayed events.

## How

1. **Sub-task execution order**: 581 (stable IDs/authoritative location) → 582 (chunk load/unload/merge APIs with ownership checks) → 583 (global index, gateway ways, load-before-move, replace global scans) → 584 (cross-chunk ownership/transaction rules, delayed event policy).
2. **Implementation**: Follow sub-task definitions (see table). Ensure merge/unload APIs (not load_from_dict) for chunks; use gateway ways with target_area_id/target_scope_id; movement loads destination chunk before resolving; delayed events indexed globally with safe deferred policy.
3. **Integration**: Keep character authoritative in players block; location stored by stable area ID; editor scope requests use projection/indexes (not whole-world graph).

## Steps to verify

1. Chunk lifecycle
   - expected: Load two adjacent chunks, move agent/item across gateway (loads remote), unload and reload both, retain exactly one authoritative location.
   - observed: Demonstrated by tests/test_chunk_lifecycle.py (4 tests) per reconnaissance; umbrella remains todo until sub-tasks done.
2. Save/load round-trip
   - expected: Gateway links (target_area_id/target_scope_id) and due events preserved through to_dict()/load_from_dict().
   - observed: Demonstrated in tests/test_chunk_lifecycle.py per reconnaissance.
3. Scoped editor responses
   - expected: Editor scope request never returns whole world graph; only requested scope + explicit gateway boundaries.
   - observed: Not fully verified; global node/edge scans not yet fully replaced by index (noted in task-583 review context).
4. Benchmark/report
   - expected: Node/edge counts loaded for requested scope reported; bounded payload behavior.
   - observed: Task-402 territory; not claimed complete.

## Acceptance

- [ ] All four sub-tasks (581, 582, 583, 584) are in done.
- [ ] Load two adjacent chunks, move agent/item across gateway, unload/reload both, retain exactly one authoritative location.
- [ ] Save/load preserves gateway links and due events.
- [ ] Editor scope request never returns whole world graph.
- [ ] Bounded payload behavior; node/edge counts for requested scope are reportable.

## Files

- `graph.py` / chunk merge/unload/load-by-chunk APIs, ownership checks
- `engine/movement.py` - load-before-resolve for gateway moves
- Global index modules - scope index, gateway indexing, entity location indexes
- Character/item location model - stable area IDs (authoritative)
- Delayed event handling - global indexing and deferred policy
- `tests/test_chunk_lifecycle.py` - end-to-end lifecycle
- Sub-tasks 581-584 files (implementation)

- `graph.py` / `world_graph.py` (or `engine/world_graph.py`) - merge/unload/load-by-chunk APIs, ownership checks
- `engine/movement.py` - load-before-resolve for gateway moves
- Global index module(s) - scope index, gateway indexing, entity location indexes
- Character/item location model - move from display-name current_area to stable area IDs
- Delayed event handling - global indexing and deferred policy
- `tests/test_chunk_lifecycle.py` - end-to-end chunk lifecycle (referenced)
- Sub-tasks 581-584 files (implementation)

## Browser UI and intended live verification

Intended UI home: WorldPainter/Graph scope selector → load two adjacent chunks → inspect their gateway ways and loaded node sets → move an agent/item across the gateway → unload and reload each chunk.

Current availability: the task is an umbrella dependent on four sub-tasks; its acceptance requires gateway movement, save/load persistence, scoped editor responses, and bounded node/edge counts. The combined chunk-persistence workflow is not claimed as complete.

Live steps when available:
1. Select two adjacent chunks and record each scope's areas, ways, items, and residents in the graph and `/api/state`.
   - expected: the editor response contains only the requested scope and its explicit gateway boundary, not the full world graph.
2. Move one agent and one item across the gateway, then unload and reload both chunks.
   - expected: each entity has exactly one authoritative location after each load; gateway links remain usable across the seam.
3. Save and reload the world with a due event scheduled on one chunk.
   - expected: both gateway links and the due event survive the round trip and the event fires once.
4. Compare loaded node/edge counts with the requested-scope benchmark report.
   - expected: the browser graph and report agree on the bounded scope payload; no unrelated child scope is silently loaded.

This section is not a claim that the chunk-persistence umbrella is complete today.


## Plan position (2026-10-20): umbrella remains, sub-tasks in review

**Which NEWER cards (higher number, in `done/` or `review/`) bear on this card, and what did each one actually do?**
- Sub-tasks task-581, task-582, task-583, task-584 (review, higher numbers related to this umbrella) are implemented and in review; they cover stable IDs, chunk load/unload/merge APIs, gateway ways/load-before-move, and cross-chunk ownership rules.
- task-439 (review), task-500 (done) referenced in context - task-500 says "task-401 already owns chunk load/evict" in that note context, but umbrella itself is not marked done; task-439 says "task-401 is the real remaining dependent".

**Did that newer work CHANGE THE APPROACH of this card, or does it merely IMPLEMENT PART OF IT, or is it UNRELATED?**
- The four sub-tasks implement parts of this umbrella; the approach (split into 581-584) is the change implemented by that split. The umbrella's aggregate requirements remain valid.

**Does this card still stand as a DISTINCT piece of the overall plan, or has a newer card absorbed its scope?**
- Remains as the umbrella. It should stay open until all four sub-tasks land in done; it has not been absorbed.

**Verdict:** holds, distinct (umbrella; must remain until sub-tasks complete).
