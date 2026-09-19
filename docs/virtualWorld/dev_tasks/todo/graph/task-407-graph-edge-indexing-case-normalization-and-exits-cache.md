---
type: task
status: review
area: graph
priority: high
---

# task-407: Graph edge indexing, boundary case normalization, cached exits

**Filed:** 2026-09-19  
**Depends on:** nothing. Additive; keeps the public graph API.  
**Evidence:** goblin soak profile (`graph.py:98–155`; `engine/legacy_compat.py:57`).

## Goal

Make edge lookup and exit building cheap and predictable, and lowercase ids
**once at the boundary** instead of on every call.

## Problem

- `get_edges_for_source` (`graph.py:130`) and `get_edges_for_target` (`:140`)
  scan the entire edge list and call `.lower()` on both endpoints of every
  edge per call. `add_edge` (`:98`) and `remove_edge` (`:107`) do the same to
  dedupe/remove.
- `build_exits_for_area` is recomputed on demand, reached through the
  `current_area` property (`engine/legacy_compat.py:57`).
- Measured over 100 ticks in the goblin soak: ~876 exit rebuilds and ~1M
  `str.lower()` calls **per tick**. Nodes already have a case-insensitive
  `_id_index` (`graph.py:57`); edges do not, and the existing lowercase index is
  not used by the hot lookups.

## Changes

1. **Edge indexes.** Maintain edges keyed by lowercased `source` and `target`
   (and by type), updated in `add_edge` / `remove_edge` / `load_from_dict` /
   `clear`. `get_edges_for_*` consult the index instead of scanning
   `self.edges`.
2. **Normalize at the boundary.** Normalize id case once on insert/load/save so
   hot paths compare pre-normalized keys and never call `.lower()` per edge.
3. **Exits cache.** Cache `build_exits_for_area(area)` results, invalidated on
   any mutation that can change exits (node/edge add/remove/load).

## Acceptance

- `get_edges_for_source` / `_target` no longer iterate `self.edges` or call
  `.lower()` per edge.
- Indexes and the exits cache stay correct across add/remove/load; save/load
  round-trips equal.
- The exits cache invalidates on every mutation that changes exits (test with a
  deliberately mutated edge).
- Per-tick `.lower()` calls drop by orders of magnitude, with profiler
  evidence.

## Non-goals

- Changing edge types, spatial-edge semantics, or trigger behaviour.
- Removing the `current_area` property from the public API (task-411/task-401
  own the longer-term decision).

## Verification

- Unit: index correctness after add/remove/load; exits-cache invalidation.
- Profile: same 100-tick run before/after (ranking only).
- Full suite excluding `test_mcp_*`.

## Progress — 2026-09-19

Implemented.

- `graph.py`: `_edges_by_source` / `_edges_by_target` / `_spatial_edges` indexes
  keyed on lowercased endpoints; `get_edges_for_source` / `get_edges_for_target`
  consult them and never call `.lower()` per edge. A `_indexed_edge_count`
  length check forces a lazy rebuild if external code mutates `self.edges`
  directly (a few effect handlers still do). `_revision` is bumped on every
  mutation for cache invalidation.
- `engine/area_description.py`: `build_exits_for_area(..., include_hidden=True)`
  is cached and invalidated on graph revision. **The game-facing default
  (`include_hidden=False`) is deliberately not cached**, because it depends on
  per-player discovery state (`Player.discovered_exits`) that changes without a
  graph mutation.

Verified: full suite 2835 passed (excluding pre-existing `test_mcp_*`); the
trigger/exit cost that dominated the old profile is gone from the hot path.
