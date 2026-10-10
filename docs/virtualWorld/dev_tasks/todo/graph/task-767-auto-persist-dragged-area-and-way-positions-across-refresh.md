---
type: task
status: todo
area: graph
priority: medium
blocked_by: [769]
---

# task-767: Auto-persist dragged area and way positions across refresh

**Filed:** 2026-10-10
**Related:** task-769, task-766

## What

When physics is off for an area or way and the user drags it, the position should
survive a hard refresh without manually pressing Save layout. Persist only areas
and ways (not characters or items), keyed to the scenario.

## Why

A dragged authored placement should stay where it was put. Today a hard refresh
re-seeds or re-simulates, throwing the drag away.

## How

Mostly built already, with one blocked case:

- For a **non-painted** frozen node, `GraphRelativeLayout.frozenDropOps`
  (`relative-layout.ts:722`) already writes `properties.x/y` on `dragEnd` — so
  this part works.
- For a **painted** node (has `properties.cell`) it deliberately **skips**: the
  compiler's `cell * 40` are engine units, and writing canvas pixels over them
  double-converts, so a node dragged once creeps further on every later save
  (bug-52). Persisting a dragged painted position therefore needs a real
  cell-space conversion — the unified coordinate system in **task-769**.
- Blocked on 769. Once 769 lands, teach `frozenDropOps` (or a sibling) to store
  the dragged offset in cell space for `type in {area, way}`.

## Steps to verify

1. Pin an area/way, drag it, hard refresh.
   - expected: it stays where it was dropped.
   - observed: TODO (blocked — painted case still re-seeds; bug-52).

## Acceptance

- [ ] A dragged area/way survives a hard refresh with no manual Save layout.
- [ ] No creep after repeated drag+refresh (bug-52 stays fixed).
- [ ] Characters and items are not persisted.

## Files

- `static/js/graph/relative-layout.ts` (`frozenDropOps`, `persistFrozenDrop`)
- `static/js/graph/layout-engine.ts` (coordinate conversion — task-769)

