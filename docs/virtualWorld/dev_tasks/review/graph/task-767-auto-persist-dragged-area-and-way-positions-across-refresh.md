---
type: task
status: review
area: graph
priority: medium
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

- In `static/js/graph/relative-layout.ts` (`frozenDropOps`), filter to only areas and ways:
  `if (node.type !== 'area' && node.type !== 'way') continue;`. Characters and items are never persisted.
- For painted nodes (`hasPaintedCoords(props)`), canvas coordinates are converted back to cell coordinates using `engine.mapSpacing()` and `engine.offsetPxFor(node, null, pitch)`:
  `cx = (bx - off.x) / pitch; cy = (by - off.y) / pitch;`.
  The patch updates `properties.cell: { x: Math.round(cx * 100) / 100, y: Math.round(cy * 100) / 100 }` and does not overwrite `properties.x/y` engine units, eliminating bug-52 creep.
- For unpainted areas and ways, persists `properties.x/y`.

## Steps to verify

1. Verified unit tests in `tools/unit/test_relative_layout.js` (test `dropping a painted node never overwrites its engine units`):
   - dropping a painted way converts canvas coords (400, 800) at pitch 800 into `properties.cell: { x: 0.5, y: 1 }` without touching `properties.x/y`.
   - dropping an unpainted way writes `properties.x/y: { x: 12.3, y: 56.8 }`.
   - dropping a painted character produces zero ops (characters/items never persisted).
2. Ran `node tools/unit/run.cjs test_relative_layout.js`: 30/30 passed.

## Acceptance

- [x] A dragged area/way survives a hard refresh with no manual Save layout.
- [x] No creep after repeated drag+refresh (bug-52 stays fixed).
- [x] Characters and items are not persisted.

## Files

- `static/js/graph/relative-layout.ts` (`frozenDropOps`, `persistFrozenDrop`)
- `static/js/graph/relative-layout.js`
- `tools/unit/test_relative_layout.js`
