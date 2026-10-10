---
type: bug
status: review
area: graph
priority: high
---

# bug-543: Changing map spacing snaps every painted area and way off its cell onto a stale saved position

**Filed:** 2026-10-10
**Related:** task-526 (map pitch ownership), task-748, task-769

## What

Nudge the Map spacing and every painted area/way lands on its cell for a moment,
then a few seconds later jumps to a different place — off the painted label and
off the art. It happens to all areas and ways in the scope, not just one.

## Why

The grid derives a painted node's position (`cell * pitch`,
`GraphLayoutEngine.scopedGridPosition`); a saved canvas snapshot is a copy from
whatever pitch it was captured at. Two things re-apply that snapshot over the
grid:

`setMapSpacing()` (`graph-manager.ts`) runs `loadGraphData()` (grid lays every
area/way on its cell) then `GraphBackground.fitToPaintedGrid()`, which calls
`saveToWorld()` — an API write. That write fires the `world_changed` SSE →
`worldState.fetch()` → `state:updated` → `GraphBackground._onWorldRefetched()`,
which does `_restore()` (reloads the block's `positions`) then
`_applyPositions()` — `moveNode()` for every node to its **saved** position.
The snapshot predates the pitch change, so it is a different frame; the areas
jump onto it. They stay there because grid areas are `fixed`, so the solver
never pulls them back.

Measured live on `goblin_camp`, `area_scrap_pile` (cell 5,7):

| | position |
|---|---|
| on its cell at pitch 176 | `(-4996, 2240)` — over "8. Scrap Pile" |
| after `setMapSpacing(+20)` (pitch 196) | rendered at `(-6756, 3029)` = `state.positions['area_scrap_pile']` |
| the new grid pos it should be | `(-5564, 2495)` — held in the DataSet, ignored by the rendered node |

`persistPositionsToWorld()` already refuses painted nodes on the way out ("a
painted area is not a target", `hasPaintedCoords`); `_applyPositions()` had the
matching guard missing on the way in.

## How

`static/js/graph/graph-background.ts` — `_applyPositions()` skips a node whose
position the painted grid owns (has a `cell`, and `graphManager._cardinalLayout`
is on). Scoped to Map mode so Graph-mode saved positions are untouched.

## Steps to verify

1. Open `goblin_camp`, read `area_scrap_pile`, then nudge the spacing.
   - expected: it stays on its cell / the "8. Scrap Pile" label.
   - observed (before fix): renders at the stale saved position `(-6756, 3029)`;
     the correct new-grid position `(-5564, 2495)` is discarded.

## Acceptance

- [ ] A spacing nudge leaves every painted area and way on its cell.
- [ ] Graph-mode dragged positions are unaffected.
- [ ] Unit + `ts_convert.py check` remain green.

## Files

- `static/js/graph/graph-background.ts` — `_applyPositions()` skips grid-owned nodes
- `static/js/graph/graph-background.js` — emitted
