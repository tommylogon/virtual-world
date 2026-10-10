---
type: task
status: done
area: world
priority: medium
---

# task-749: Persist and restore the selected world scope across reload and refresh

**Filed:** 2026-10-09
**Related:** task-397 (world scope hierarchy and projection), task-439 (canonical area identity), task-451 (background layers)

## What

Selecting a world scope in the graph filter does not survive a page reload or
app refresh: the graph reverts to whole world. Make the selected scope persist
and be restored on load.

Current state (measured):

- The selection lives only in memory — `graphManager._scopeFilter`
  (`static/js/graph-manager.ts:132` declared, `:183` initialised to `null`),
  set by `setScopeFilter` (`:545`) from the picker `#graph-scope-filter`
  (`:498`) and the scope tree (`static/js/graph/scope-tree.ts:341-342`).
- It is reset on scenario switch (`graph-manager.ts:534`) and never written to
  any store, so a refresh loses it.
- Sibling view preferences *do* persist via `localStorage`, so the pattern
  already exists: `vw_graphShowImages` / `vw_graphNodeLabels`
  (`graph-manager.ts:223,268`), `vw_area_filter` (`stream-filters.ts:151`),
  `vw_stream_mode` (`event-stream.ts:92`).

Scope: persist the selected scope **per scenario**, and restore it after the
scope manifest loads. Must not leak a scope id from one world into another — the
same reasoning `graph-background` uses for its per-scenario key
(`_scenarioKey`). A restored id that no longer exists (renamed/deleted scope)
must fall back to whole world, not error.

## Resolution (2026-10-09)

Persisted per scenario in `localStorage` under `vw_graphScope_<scenario name>`
(same identity source as `graph-background._scenarioKey`).

- `graph-manager.ts` — `_scopeStorageKey` / `_persistScopeFilter` / `_restoreScopeFilterOnce`;
  `setScopeFilter` now persists (whole world clears the key); `loadGraphData` restores
  once per page load, before the subgraph fetch, validated against `_scopeSummaries`.
- `graph/network-manager.ts` — the stale-scope fallback also clears the saved key, so an
  unresolvable id cannot loop across reloads.
- Guard: `tools/unit/test_graph_scope_tree.js` asserts the calls are wired.

## Acceptance

- [x] Persisted keyed by scenario and restored on load, re-applying `setScopeFilter`
      (`_restoreScopeFilterOnce` sets `_scopeFilter` before `GraphNetwork.loadGraphData`).
- [x] Reloading at a selected scope returns to that scope.
- [x] A different scenario does not restore the previous world's scope (per-scenario key;
      the restore runs once per page load, and a scenario switch resets `_scopeFilter`
      without touching the other scenario's key).
- [x] A stored id that no longer resolves falls back to whole world without error (validated
      against `_scopeSummaries`; `network-manager` also drops an unresolvable id and clears
      the key).
- [x] Whole-world selection still restores whole world (picking it clears the key).
- [ ] Live: pick a scope, refresh, confirm it returns to the scope and the picker/breadcrumb agree.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO
