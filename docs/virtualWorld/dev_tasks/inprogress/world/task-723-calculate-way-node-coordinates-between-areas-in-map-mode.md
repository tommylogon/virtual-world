---
type: task
status: inprogress
area: world
priority: medium
---

# task-723: Calculate way node coordinates between areas in map mode

**Filed:** 2026-10-06
**Related:** 

## Goal

When in map mode, calculate the correct coordinates to place a way node between its two connected areas, taking the spacing/distance between the areas into account (e.g. midpoint or interpolated position along the gap).

## Acceptance

- Given a way node with two endpoint areas (each with `x`/`y` canvas coords), compute a sensible position for the way between them.
- Position accounts for the spacing/gap between the two areas (not just a blind midpoint — e.g. offset toward the narrower gap, or interpolated along the connecting edge).
- Works in map mode for both compiler-minted ways and hand-authored ways.
- Does not move areas; only computes/assigns the way's own `x`/`y`.
- Existing way edges (area↔way connections) are preserved.

## Notes

- Areas carry `properties.x`/`properties.y` (canvas coords = cell × 40, set by the compiler and `handle_place_area`).
- Ways carry `properties.area_from_id` / `properties.area_to_id` (see `_boundary_ways` in `routes/world_grid_ops.py`).
- The map layout already reads area `x`/`y`; a way with no `x`/`y` currently falls back to wherever the layout puts it.

## Related Files

- `engine/world_compile.py`: `_way_edges` mints the four connection edges; way node creation lives in the compiler.
- `routes/world_grid_ops.py`: `_boundary_ways` reads way endpoints; `handle_place_area` sets area `x`/`y`.
- `static/js/worldpainter/editor.ts`: map-mode rendering reads area/way coords.

## Reopened 2026-10-08 — back to inprogress (the nodes are placed; the edge fan is not)

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
unchanged and still draw long — that half is task-618.
