---
type: task
status: review
area: graph
priority: high
---

# task-523: Map layout: move a whole zone in the graph canvas (per-scope offset)

**Filed:** 2026-09-25
**Related:** task-397, task-496, task-524

## Goal

In the graph canvas, a zone (scope) should behave like a background layer you can
grab and move, with its grid of areas following (local vs global space). Store a
per-scope offset that the map layout adds to the painted lattice coords, persisted
in the world so a drag survives reload and does not desync from WorldPainter.
Decide whether moving a zone also moves its subtree.

## What shipped

- **Storage:** a scope record carries an optional `map_offset: {x, y}` in **cell**
  units. Absent or zero = the painted position, so an unmoved scope keeps a
  minimal manifest. `engine/world_grid.py` gains `map_offset(record)`,
  `set_map_offset(record, x, y, reset=)`, and `normalise_grid` cleans/drops it.
- **API:** `POST /api/world/scopes/<id>/offset` — `{x, y}` cells, or
  `{reset: true}`. The scope's grid payload and `scope_summary` (including the
  flat `/api/world/scopes?flat=1` list) both carry `map_offset`.
- **Layout:** `GraphLayoutEngine` adds **each node's own scope offset**
  (`properties.world_scope_id`, falling back to `generated.scope_id`) to its
  painted coords, so the whole-world/descendant view places every zone correctly;
  `offsetPxFor`/`scopedGridPosition` are pure and unit-tested.
  `refreshGridLayout` re-places nodes live without refitting the camera.
- **Interaction:** in Map mode with a painted scope selected, right-click empty
  canvas → **✥ Move zone** enables a drag overlay. Dragging moves the zone's
  nodes live and nudges the active map art with it; releasing persists the offset
  (`ApiClient.setScopeOffset`). Esc or the on-canvas **✔ Done** ends the mode.
- **Art:** `▦ Fit to painted grid` fits the reference to the **offset** grid, and
  `_applyReferenceLayout` adds the scope offset, so the art follows a moved zone.
- **Subtree decision:** moving a zone moves **only that scope's own lattice**.
  Children keep their own offsets, matching the level-scoped view where a placed
  child is a single feature cell authored separately. No cascade.

## Acceptance

- [x] A scope stores a cell-unit `map_offset`; absent/zero = painted position; it
  survives `normalise_manifest` and a JSON save round-trip.
- [x] `POST /api/world/scopes/<id>/offset` sets/resets it, 400s on nonsense,
  404s on an unknown scope; the offset appears on the grid payload and the flat
  scope list.
- [x] The map layout adds the per-node scope offset; `refreshGridLayout` re-places
  without a camera refit.
- [x] Dragging the zone persists the offset and it re-applies on reload (offsets
  are loaded before the first layout).
- [x] `▦ Fit to painted grid` includes the offset so the reference art tracks the
  zone.
- [x] Moving a zone does not move its subtree (documented above).

## Files

- `engine/world_grid.py`, `engine/world_scopes.py`
- `routes/world_grid.py`, `routes/world_grid_ops.py`
- `static/js/api.js`, `static/js/graph-manager.js`
- `static/js/graph/{layout-engine,network-manager,graph-background.ts,graph-background.js}.js`
- `static/js/types/globals.d.ts`
- `tests/test_world_grid.py`, `tests/test_world_grid_routes.py`,
  `tools/unit/test_graph_layout_engine.js`
- `docs/design/worldpainter-knowledge-and-fog.md`

## Verification

- `python -m pytest tests/test_world_grid.py tests/test_world_grid_routes.py tests/test_world_scopes.py tests/test_world_compile.py -q` → 95 passed.
- `node tools/unit/run.cjs` → 240 passed, 13 failed (all pre-existing
  `test_plan_tracker`).
- `npm run lint`, `npm run typecheck`, `python tools/js_module_index.py --check`
  → clean.
