---
type: task
status: todo
area: world
priority: medium
---

# task-401: Chunk persistence, scoped indexes, and gateway ways

**Filed:** 2026-09-08  
**Depends on:** task-397 through task-400.

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

- Load two adjacent chunks, move an agent/item across a gateway, unload and
  reload both, and retain exactly one authoritative location.
- A save/load round-trip preserves gateway links and due events.
- An editor scope request never returns the whole world graph.
- Benchmark/report node/edge counts loaded for the requested scope.

## Non-goal

This task is not required to prove task-400. It is the first step that makes a
million-node world technically credible.
