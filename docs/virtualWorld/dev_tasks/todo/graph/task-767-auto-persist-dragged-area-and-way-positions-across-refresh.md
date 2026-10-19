---
type: task
status: todo
area: graph
priority: medium
blocked_by: [769]
wiki: "[[World Building/World Structure & Graph Representation]]"
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

1. On a scratch scenario after task-769's coordinate conversion is available,
   turn physics off for one painted area and one painted way. Record each
   screen position and `properties.cell`, drag both, then hard-refresh.
   - expected: each area/way returns to its dropped position with a stable
     cell-space offset; neither creeps on reload.
   - observed: not verified; this card is blocked on task-769.
2. Repeat drag → hard-refresh three times and compare the screen positions and
   saved cell-space offsets after every load.
   - expected: positions remain stable across all three cycles.
3. Drag a character and an item in the same scratch scenario, then hard-refresh.
   - expected: only authored area and way positions persist; character and item
     positions are re-derived and are not written by this feature.

## Browser UI and intended live verification

Intended UI home: Graph canvas → pin/freeze an area or way → drag the node →
hard-refresh the same scenario. Persistence applies only to area and way
placements; characters and items stay runtime/layout-derived.

Current availability: frozen non-painted nodes already write `properties.x/y`
on drag end. Painted nodes with `properties.cell` are skipped to avoid mixing
canvas pixels with compiler cell units. The complete painted-node behavior is
blocked on task-769's unified coordinate conversion.

Live steps when available:
1. Load a scratch scenario containing a painted area and way. Pin both, drag
   them to distinct offsets, and inspect the graph canvas before refreshing.
2. Hard-refresh and reload the same scenario. Record both positions and compare
   them with the stored cell-space offsets.
   - expected: each node returns to its dropped position without a manual Save
     layout action.
3. Repeat the drag/refresh cycle three times.
   - expected: neither position creeps between loads.
4. Drag a character and item, then refresh.
   - expected: their positions are not persisted by this feature; only the area
     and way positions changed in the scenario data.

These steps define the intended canvas interaction. The painted-node case is
not available until task-769 supplies the coordinate conversion.

This section is not a claim that planned UI exists or works today.

## Acceptance

- [ ] A dragged area/way survives a hard refresh with no manual Save layout.
- [ ] No creep after repeated drag+refresh (bug-52 stays fixed).
- [ ] Characters and items are not persisted.

## Files

- `static/js/graph/relative-layout.ts` (`frozenDropOps`, `persistFrozenDrop`)
- `static/js/graph/layout-engine.ts` (coordinate conversion — task-769)

