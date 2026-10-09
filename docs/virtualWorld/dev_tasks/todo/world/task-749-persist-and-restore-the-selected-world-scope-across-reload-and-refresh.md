---
type: task
status: todo
area: world
priority: medium
---

# task-749: Persist and restore the selected world scope across reload and refresh

**Filed:** 2026-10-09
**Related:** task-397 (world scope hierarchy and projection), task-439 (canonical area identity), task-451 (background layers)

## Goal

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

## Acceptance

- [ ] The selected scope id is persisted (localStorage is sufficient) keyed by
      scenario, and restored on load, re-applying `setScopeFilter`.
- [ ] Reloading/refreshing at a selected scope returns to that scope.
- [ ] Switching to a different scenario does **not** restore the previous
      world's scope.
- [ ] A stored scope id that no longer resolves falls back to whole world
      without error.
- [ ] Existing behavior preserved: whole-world selection still restores whole
      world; the picker and breadcrumb agree with the restored value.
