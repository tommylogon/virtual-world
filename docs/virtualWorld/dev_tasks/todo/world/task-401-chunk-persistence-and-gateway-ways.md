---
type: task
status: todo
area: world
priority: medium
children: [task-581, task-582, task-583, task-584]
---

# task-401: Chunk persistence, scoped indexes, and gateway ways

**Filed:** 2026-09-08  
**Depends on:** task-397 through task-400.  
**Split 2026-09-28** into the four sub-tasks below. This file is the umbrella: the
goal, the reasoning and the acceptance for the whole effort stay here, the work
does not.

## Sub-tasks

| Sub-task | Covers |
|---|---|
| [task-581](../../refactor/task-581-stable-area-ids-and-one-authoritative-location-for-characters-and-items.md) | Stable area ids; one authoritative location record per character and unique item. The precondition — display-name `current_area` cannot survive duplicate names across chunks. |
| [task-582](../../world/task-582-chunk-load-unload-and-merge-apis-on-worldgraph.md) | `WorldGraph` load / unload / merge APIs with ownership checks. `load_from_dict()` clears the graph, so it cannot be the chunk loader. |
| [task-583](../../world/task-583-global-scope-index-gateway-ways-and-load-before-you-move.md) | The global index, gateway ways naming a remote `target_area_id` + `target_scope_id`, load-before-resolve in movement, and replacing global node/edge scans. |
| [task-584](../../world/task-584-cross-chunk-ownership-rules-for-carried-items-triggers-and-delayed-events.md) | Ownership and transaction rules for carried/equipped items, triggers and delayed events across an unload; the deferred-event policy. |

Order: 581 → 582 → 583 → 584. Each is independently reviewable, and 581 is
worth landing on its own merits: it removes a real correctness hazard (a
duplicate area name splitting a character's location) whether or not chunking
ever happens.

## Goal

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
