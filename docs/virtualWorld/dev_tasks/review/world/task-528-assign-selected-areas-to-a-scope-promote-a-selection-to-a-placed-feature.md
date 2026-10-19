---
type: task
status: review
area: world
priority: high
related: ['task-496', 'task-397', 'task-378', 'task-523', 'task-495', 'task-535', 'task-539']
---

# task-528: Place authored areas onto a painted cell (scope membership + map placement)

**Filed:** 2026-09-26
**Related:** task-496 task-397 task-378 task-523 task-495

<!-- deps:start -->
**Related:** [[task-496-worldpainter-grid-to-graph-compiler-cells-to-areas-and-ways]], [[task-397-world-scope-hierarchy-and-projection]], [[task-378-bulk-selection-mode]], [[task-523-map-layout-move-a-whole-zone-in-the-graph-canvas-per-scope-offset]], [[task-495-worldpainter-recursive-scope-grids-and-3-mode-editor]], [[task-535-promote-a-graph-selection-into-a-new-child-scope-with-a-gateway]], [[task-539-reassign-an-area-to-a-scope-membership-only-plus-a-scope-picker-on-the-node]]
<!-- deps:end -->

## What

An area the author wrote by hand exists in the graph but has no place on a painted map:
the map is a WorldPainter reference image with biome cells, and `compile_grid` only
ever creates areas *from* cells. Nothing could put an existing area *onto* one, so
`world_scope_id`, `properties.cell` and `x/y` had no producer outside the compiler.

This closes it: pick an existing area, click a cell on the map, and it becomes a
member of that scope placed on that cell - visible in Map mode, aligned with the
painted art, and safe against Generate.

**Decided 2026-09-27 (with the author):**
- Placement is manual: a WorldPainter tool, pick area → click cell. Not a graph bulk
  action; "add to scope" without positioning was rejected as not useful.
- Painting + generating the **world** grid stays allowed. That makes the collision
  rule mandatory, not optional (see below): a cell holding a hand-placed area is
  skipped by `compile_grid`, so Generate never creates a second area there.

## Acceptance

### Store and rules (engine)

- [x] `record["area_placements"]`: `{area_id: {"x","y"}}` - the mirror of `placements`
      (which is keyed by child scope). Normalised in `world_grid.normalise_grid` like
      `placements` is, so a malformed record self-heals on load.
- [x] `world_grid.area_placements(record)`, `area_placement_at(record, x, y)` and
      `area_placement_of(record, area_id)` mirror `placements()` / `occupant_at()`.
- [x] `compile_grid` **skips** a region whose anchor cell is occupied by an
      `area_placements` entry. Without this, painting that cell and generating would
      produce a second area on top of the hand-placed one.
- [x] A placed area keeps NO `properties.generated` (it is hand-authored), so
      `ungenerate_scope` / `delete_scope` leave it alone - that is already how those
      predicates work, and it is why placement must refuse generated nodes instead.

### One undoable operation (routes)

- [x] `POST /api/world/scopes/<id>/grid/place_area` `{area_id, x, y, on_overlap?}`
      does the whole thing in one request: node properties (`world_scope_id`,
      `cell`, `x`, `y` in `CELL_CANVAS_UNITS`), manifest `area_ids` membership
      (appending to the new scope, removing from the previous one), and the
      `area_placements` entry.
- [x] `POST /api/world/scopes/<id>/grid/unplace_area` `{area_id}` frees the cell and
      clears the node's `cell`/`x`/`y`, keeping scope membership.
- [x] Both live under `/grid/`, where `app.py:112-117` suppresses the automatic
      post-state snapshot, and each pushes exactly **one** pre-state snapshot - so
      one undo reverts the whole op (bulk delete's N-entries mistake avoided).
- [x] Refusals, each with a message the UI can show verbatim:
      unknown area · not an area node · **generated** area (regenerating its source
      scope would re-create it) · scope has no grid · cell out of bounds · cell
      already taken (unless `on_overlap: "displace"`, which moves the other area off
      the cell) · area already placed elsewhere in this scope.

### Painter (frontend)

- [x] A fifth WorldPainter tool "📍 Area": a picker of unplaced hand-authored areas,
      then click a cell to place. Placed areas render in the decor layer with their
      name, so the map shows what is where.
- [x] Clicking a cell that already holds a placed area offers to unplace it (no
      second mode to learn).
- [x] After placing, the tool stays armed for the next area; Escape returns to paint.
- [x] The grid payload carries `area_placements` (id, name, x, y) and
      `unplaced_areas` (hand-authored areas with no placement), so the picker needs
      no extra round trip.
- [x] Bridge: the area context menu gets "📍 Place on map…", which opens the painter
      at that area's scope with the tool armed and the area pre-selected.

### Tests

- [x] `tests/test_world_grid.py`: the new accessors + `normalise_grid` on a
      malformed `area_placements`.
- [x] `tests/test_world_grid_routes.py`: place / unplace / every refusal / one undo
      step / membership moves between scopes / generate skips an occupied cell.
- [x] `tools/unit/test_worldpainter.js`: any new pure view-model helpers.
- [x] `python -m pytest -q` at the documented baseline, `node tools/unit/run.cjs`,
      `npm run lint`, `npm run typecheck`, `python tools/js_module_index.py --check`.
- [x] Verified in the browser: place an authored area on the painted world map, see
      it in Map mode, and see Generate refuse to duplicate the cell.

## Deferred (filed as task-535)

The other half of the original goal - promoting a selection into a **new child scope**
placed on a parent cell, with a gateway way and an entry area - is a separate op: it
needs child-scope creation from existing nodes, a gateway whose provenance is not the
parent's, and entry-area bookkeeping. `world_compile._gateway` is private and
generation-owned, so it wants its own public helper rather than a reuse of that one.

## Notes

- `world` scope caveat for the author: its grid is 200×133 cells while a zone grid is
  e.g. 20×40, so the two live at very different scales. Zone placement on the world
  map is therefore the zone `map_offset`'s job (task-523) - place areas in the scope
  they belong to, then drag the zone onto the world map.
- `hasPaintedGrid` (`layout-engine.js:317`) is a whole-payload mode switch: the first
  hand-placed area flips the entire world view into grid mode. Areas without a `cell`
  are then placed by physics rather than the lattice, which is the intended
  "grid where it exists, physics elsewhere" behaviour.
- Deleting a scope **releases** its hand-placed areas' cells (the reservation lived in
  the record being deleted) while keeping the areas. Without that, a phantom `cell`
  would keep `hasPaintedGrid` true for a map nothing reserves any more, and a
  re-created scope of the same id could generate a second area on it. Covered by
  `test_delete_scope_releases_a_hand_placed_area_but_keeps_it`.
- The painter's compile estimate drops occupied cells too, so the header's
  "≈ N areas" matches what Generate actually mints.
- Verified live on a 12×12 scope: the tool opens pre-armed from the graph, a click
  placed `Bathroom` on (5,3) (`cell`, `x/y = 200/120`, membership, one undo step),
  and Generate with biomes painted on (5,3) and (6,3) minted only `area_testmap_6_3`.

## Why

Authors need to place existing hand-authored areas onto WorldPainter grid cells without re-generating them, establishing both spatial coordinates (cell, x/y) and scope membership in one atomic, undoable operation.

## How

Added route POST /api/scopes/<scope_id>/place_area updating node cell and properties.world_scope_id and reserving the grid cell in manifest.json. Implemented place tool in painter UI.

## Steps to verify

1. Place an authored area on a painted cell
   - expected: Area gains cell coordinates and scope membership; cell is reserved from procedural generation
   - observed: Verified on 12x12 scope live check (area_testmap_6_3)
2. Verify scope deletion releases hand-placed cell
   - expected: Deleting scope frees cell reservation while preserving authored area node
   - observed: Verified by test_delete_scope_releases_a_hand_placed_area_but_keeps_it

## Files

- 
outes/world_grid_ops.py
- engine/world_scopes.py
- static/js/worldpainter/grid-model.ts
- 	ests/test_world_grid_routes.py
