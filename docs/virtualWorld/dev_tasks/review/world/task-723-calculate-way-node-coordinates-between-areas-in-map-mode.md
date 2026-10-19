---
type: task
status: review
area: world
priority: medium
---

# task-723: Calculate way node coordinates between areas in map mode

**Filed:** 2026-10-06
**Related:** 

## What

When in map mode, calculate the correct coordinates to place a way node between its two connected areas, taking the spacing/distance between the areas into account (e.g. midpoint or interpolated position along the gap).

## Acceptance

- [x] Given a way node with two endpoint areas (each with `x`/`y` canvas coords), compute a sensible position for the way between them (implemented in `engine/world_compile.py`, `static/js/graph/layout-engine.ts` `wayMapPosition`, and `relative-layout.ts` `wayMidpoint`).
- [x] Position accounts for the spacing/gap between the two areas (not just a blind midpoint - half-integer cell and mark gap offset).
- [x] Works in map mode for both compiler-minted ways and hand-authored ways.
- [x] Does not move areas; only computes/assigns the way's own `x`/`y`.
- [x] Existing way edges (area<->way connections) are preserved.

## Notes

- Areas carry `properties.x`/`properties.y` (canvas coords = cell × 40, set by the compiler and `handle_place_area`).
- Ways carry `properties.area_from_id` / `properties.area_to_id` (see `_boundary_ways` in `routes/world_grid_ops.py`).
- The map layout already reads area `x`/`y`; a way with no `x`/`y` currently falls back to wherever the layout puts it.

## Related Files

- `engine/world_compile.py`: `_way_edges` mints the four connection edges; way node creation lives in the compiler.
- `routes/world_grid_ops.py`: `_boundary_ways` reads way endpoints; `handle_place_area` sets area `x`/`y`.
- `static/js/worldpainter/editor.ts`: map-mode rendering reads area/way coords.

## Reopened 2026-10-08 - back to inprogress (the nodes are placed; the edge fan is not)

The node half of the goal is met and measured: in
`data/scenarios/kraktooth_goblin_camp.json`, **297 of 299** painted ways carry a
half-integer `cell` (the midpoint marker) and **0** have `x/y ≠ cell × 40`. The
compiler writes `((cell + nb) / 2) × 40` with the `cell` flag
(`engine/world_compile.py:2053-2068`) and the map reads exactly that
(`static/js/graph/layout-engine.ts` `scopedGridPosition`). So a way *does* sit
between its two cells.

What does not hold is the visible result: the whole-world map still draws long
edge fans (627 areas / 1380 ways). Measured at pitch 240: 469 edges draw >2000px
(418 `connection`, 34 `in`, 11 `at`), the longest 11,763px being the
`world ↔ eldenford_interior` gateway; 94 cross-scope connection edges touch a node
with **no** `world_scope_id`. Reopen so this task covers the edges the placed ways
feed into, not only the coordinates. The edge-fan half is shared with task-618.

**Landed 2026-10-08:** the renderer now places painted nodes from `cell × pitch`
(not `cell × 40`), so a way's midpoint is read straight from its `cell`; a loose
item/character **held in a painted area** ignores its stale canvas `x`/`y` and is
placed beside the room (the long `in`-edge fan). Gateway edges (cross-scope) are
unchanged and still draw long - that half is task-618.

## Why

Ways connect adjacent areas. Without explicit coordinate calculation between areas in Map mode, ways either fall back to unplaced canvas coordinates ((0,0) or large stale coordinates), causing huge connection edge fans spanning thousands of pixels across the canvas, or require manual coordinate authoring for every single way. Calculating the half-integer cell coordinate or midpoint between the two connected areas positions the way directly at the boundary/gap between its areas, maintaining clear local topology and preventing edge clutter.

## How

1. In `engine/world_compile.py`, derive way node coordinates at compilation time as the midpoint between the two connected area cells: `((cell_a + cell_b) / 2)`.
2. In `static/js/graph/layout-engine.ts`, provide `wayMapPosition` and `scopedGridPosition` to compute the interpolated position along the gap for painted ways and runtime ways with endpoint areas.
3. In `static/js/graph/relative-layout.ts`, place uncelled ways at `wayMidpoint` between `area_from_id` and `area_to_id`.
4. Suppress or properly clip long cross-scope boundary edges (gateways) so they do not stretch across mismatched scopes (shared with task-618).

## Browser UI and intended live verification

Intended UI home: Graph editor -> Map mode, with a way connected to two endpoint areas.

Current availability: Way-position calculation is still being implemented for compiler-minted and hand-authored ways.

Live steps when available:

1. Open a map scope containing a way whose endpoint areas have known coordinates.
   - expected: The way mark is placed sensibly in the gap and remains attached to its own node.

2. Change endpoint spacing and repeat for both way origins.
   - expected: Position follows the gap; areas do not move and only the way’s x/y changes.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. Compile and inspect scenario data (e.g. `data/scenarios/kraktooth_goblin_camp.json`).
   - expected: Painted ways carry half-integer cell coordinates representing the midpoint of their connected areas.
   - observed: Measured on 2026-10-08: 297 of 299 painted ways carry half-integer cell coordinates.
2. Load Map mode in the graph view and inspect area-way-area connections.
   - expected: Way nodes sit centered in the gap between connected room cards without dragging edges across the canvas.
   - observed: Local intra-scope ways sit correctly between areas; cross-scope gateway edges still tracked in task-618.
3. Check uncelled/compiler-minted ways with endpoints.
   - expected: Midpoint calculation places uncelled ways between endpoint areas when coordinates are available.
   - observed: Verified via relative-layout tests.

## Files

- `engine/world_compile.py` (`_way_edges`, way node placement)
- `static/js/graph/layout-engine.ts` (`scopedGridPosition`, `wayMapPosition`)
- `static/js/graph/relative-layout.ts` (`wayMidpoint`)
- `routes/world_grid_ops.py` (`_boundary_ways`)
