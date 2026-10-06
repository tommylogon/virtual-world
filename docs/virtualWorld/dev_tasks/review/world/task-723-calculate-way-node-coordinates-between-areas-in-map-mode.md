---
type: task
status: review
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
