---
type: task
status: inprogress
area: world
priority: high
---

# task-496: WorldPainter: grid-to-graph compiler (cells to areas and ways)

**Filed:** 2026-09-24
**Related:** task-495, task-398, task-400
**Design:** `docs/design/worldpainter-knowledge-and-fog.md`,
`docs/design/world-environment-taxonomy.md`

**Overlaps task-398.** task-398 already owns the deterministic generation contract (the `GenerationPatch` shape, provenance, apply-once, "a manual edit survives a second run"). This task is the *painted-grid recipe* — wilderness/road/biome tiles + region-merge — that should emit a `GenerationPatch` through 398's contract rather than a parallel generator. Decide whether to fold it into 398 or keep it as the grid recipe.

## Goal

Compile a painted scope grid into the existing area/way node+edge format: cells become areas (optionally region-merged by biome via flood-fill), adjacent cells get ways (direction, open/see_through, floor), and areas get tags, environment, floor and world_scope_id. Descriptions are deterministic templates over (own tile + 4 neighbours + exits/directions), reusing visible_in_direction (engine/area_description.py); no LLM at lattice scale. Emit into the scenario/library formats so the engine is unchanged. Decide grid-canonical vs baked-and-hand-edited per zone to avoid the task-289/290/317 clobber trap.

## Acceptance

- A painted grid compiles to areas + ways in the existing scenario/library formats, loadable with **no engine change**.
- Optional region-merge collapses contiguous same-biome cells into one area (flood-fill); a test shows fewer nodes with identical topology.
- Ways carry `direction`/open/`see_through`/`floor`; areas carry tags, `environment`, `floor`, `world_scope_id`.
- Descriptions are deterministic from (own tile + neighbours + exits) with **no LLM call**. **Superseded 2026-09-26** by the observer-view model below: every painted cell is a place, a road cell *replaces* the biome, and a description composes the place's *character* from its neighbours + elevation.
- Grid-canonical vs baked-and-hand-edited is decided and enforced (edit-after-bake is not silently clobbered; see task-289/290/317).

## Decisions — 2026-09-24

- **Keep 496 as a separate grid recipe that emits through task-398's
  contract** (do not fold it into task-398). task-398 owns *how* a patch applies
  safely (provenance, once-only); 496 owns the *mapping* cell → area and
  adjacency → way. Folding would put grid painting inside a generic contract
  that an apartment or item-plan recipe does not share.
- **Grid-canonical by default, baked opt-in, per zone.** The policy is
  `paint_policy` on the scope record: `"canonical"` (default) may be re-compiled
  via `apply_patch(allow_regenerate=True)`, but a re-run is still rejected by
  default, so an edit made after baking is never silently overwritten;
  `"baked"` compiles once and is treated as hand-authored thereafter (a second
  compile raises). This is the task-289/290/317 clobber trap answered.

## Decisions — 2026-09-26 (observer-view places, road replaces biome, directions)

Locked with the author. These widen the grid recipe beyond "biome cells → areas,
4 neighbours" and are the target for the compiler's next pass.

- **Every painted cell is a place.** Roads included. A road-only cell is no
  longer dropped (the current `cells = sorted(biome_of)` behaviour): it compiles
  to an area whose terrain is the road.
- **A road cell replaces its biome**, it is not a second node on the same cell.
  One place per cell; the biome underneath is *context* for the description, not
  an extra area (`properties.road` becomes the cell's identity, not a tag on a
  biome area).
- **Descriptions compose the place's character**, not just list neighbours:
  road with woods to the north → "a road along the forest line"; road between
  woods → "a road in the woods"; road between cliffs → "a narrow path, rockface
  rising on one side and dropping away on the other" (read from neighbour
  elevation/floor). May look one hop further to say where a road *goes* ("the
  road west leads back into the sparse woods"). Deterministic, no LLM.
- **Directions: compass outdoors, narrative on feature entry.** Exterior
  cell-to-cell moves stay `north/south/east/west` + diagonals. Entering a
  **feature** uses a narrative phrase (`enter`, `enter the mine`,
  `climb up the rockface`, existing `in`/`out`) sourced from the
  feature/placement, not hardcoded. The engine already keys movement off the
  direction string (gateways use `in`/`out`), so no engine change is needed to
  widen the vocabulary.
- **Elevation is a description input now, a movement gate later.** Floors are
  stored on areas (`properties.elevation`) and should inform cliff prose now; a
  large floor delta gating traversal (climb required past ~3 floors) is deferred
  to **task-525**.

Still to decide/land here: the context classifier (neighbour pattern →
phrase), the feature-entry direction vocabulary, and road-as-place in the
cell list.



- **`engine/world_compile.py`** (new): `compile_grid(manifest, scope_id, *,
  region_merge=False, recipe_id="grid.v1", seed=None, tick=0)` → a
  `GenerationPatch`.
  - Cells with a painted `biome` become areas; 8-neighbour adjacencies
    (orthogonal *and* diagonal) become
    `way` nodes with the **four connection edges** `connect_areas` produces, so
    the engine is unchanged. Optional `region_merge` flood-fills contiguous
    same-biome cells into one area, emitting one passage per region boundary.
  - Disconnected islands are **auto-linked**: each component beyond the main
    landmass gets one way to the closest cell of the main mass
    (`link_islands`, default on), so a lone outpost is reachable instead of
    compiling to a dead end. The report notes `K island(s) linked`.
  - Areas carry `tags` (biome + road feature), `floor`, `environment`,
    `world_scope_id`, optional `elevation`/`road`/`child_scope_id`, and a
    **deterministic description** built from the cell's own biome fragment, the
    road feature, its exits and its neighbouring biomes — no LLM (fragment
    choice is a stable hash of `seed:cell`).
  - Ways carry `direction`, open `current_state`, `see_through`, `floor`,
    `pass_message`, and both `area_from`/`area_to` (display names, the engine's
    convention) and `area_from_id`/`area_to_id` (ids, for scoped tooling).
  - Every generated node carries task-398 provenance.
- `engine/world_scopes.py::boundary_ways` now prefers `area_from_id`/`area_to_id`
  and resolves display names → ids, so generated and hand-authored ways both
  compare correctly.
- **`tests/test_world_compile.py`** (13): area/way counts, properties,
  deterministic descriptions, road tags, region-merge (fewer nodes), baked
  refusal, boundary ways, and a **real-VirtualWorld walkability check** (apply
  the patch, then read the exits — `east`/`south` present, no engine change).
- The grid data model this reads is `engine/world_grid.py` (task-495).

## Progress — 2026-09-24 (generate wiring)

The compiler was reachable only from tests; it is now reachable from the editor.

- **`POST /api/world/scopes/<id>/grid/generate`** (`routes/world_grid_ops.py`):
  compiles the painted grid and applies the patch once. Body
  `{region_merge?, seed?, allow_regenerate?, tick?}`. The once-only guard returns
  **409** when the scope is already `materialized` unless `allow_regenerate` is
  set; pre-apply failures (no grid, no painted cells, baked zone) return 400; a
  missing scope 404s. A pre-state undo snapshot makes generation revertible.
- **`tests/test_world_grid_routes.py`** (+5): draw → generate produces real
  `area`/`way` nodes carrying `world_scope_id` + provenance, the scope flips to
  `materialized` and lists its `area_ids`, the compiled area `build_exits_for_area`
  reports `east`/`south` (walkable with no engine change), region-merge collapses
  same-biome cells, once-only/regenerate, the no-paint/no-grid/404 errors, and
  Undo reverts a generation.
- **Editor** (`static/js/worldpainter/editor.js`): a `⚙ Generate` button plus a
  "merge same-biome" toggle; it reports `N node(s), M edge(s)`, offers a
  `allow_regenerate` re-run on the 409, and refreshes the world sync.
- Live browser run (6 painted cells): 13 nodes / 28 edges — 6 areas, 7 passages;
  scope `materialized`.

Still open here: the "merge" overlap policy if a zone ever needs it. Diagonal
(8-neighbour) ways and materialising a placed child scope's own grid are both
done (see the progress sections below).

## Progress — 2026-09-24 (child-scope gateways)

The placed-feature gap is closed on the compiler side: a child scope you paint
and generate is now **walkable from the parent cell it was placed on**.

- **Entry area.** Compiling any scope records `entry_area_id` / `entry_area_name`
  on the scope (its first region — regions are ordered by `(y, x)`, so the
  top-left-most). A placed child is entered here.
- **Gateway link.** When both a parent and its placed child are materialized, a
  `way` node `way_gateway_<parent>_<child>` links the parent's compiled cell area
  to the child's entry area. Directions are **`in`** (parent → child) and
  **`out`** (child → parent), so `go in` / `go out` work; the four connection
  edges are built explicitly because the two directions are not opposites.
  `see_through` is false — you cannot see a whole child scope from outside it.
- **Emitted exactly once, either order.** The parent records each placement's
  compiled `area_id`/`area_name` (persisted on the scope record, kept by
  `world_grid.normalise_grid`). The gateway is emitted by whichever scope
  compiles second: the parent if the child is already materialized, otherwise
  the child when it compiles against an already-generated parent. A parent-first
  ordering therefore still links; a placement on an unpainted cell links nothing.
- **Fixed a name-collision bug found while testing this.** Generated area names
  were `"<Biome> (x,y)"`, so two scopes (or a zone over a parent cell) both
  compiled to `"Sparse Forest (0,0)"` and name-based resolution picked the wrong
  area. Names are now scope-qualified: `"Sparse Forest (The Inn 0,0)"`. Ids are
  unchanged and stay authoritative.

Tests (`tests/test_world_compile.py` +7): entry-area recording, child-first and
parent-first gateway emission, `in`/`out` walkability read through a real
`VirtualWorld`'s `build_exits_for_area`, no duplicate on regenerate, and no link
for an unpainted cell; `tests/test_world_grid.py` +1 for the link fields
surviving `normalise_grid`.

## Progress — 2026-09-25 (painted positions)

Generated nodes now carry a canvas position, so a compiled scope lays out in the
shape it was painted instead of a physics blob:

- Every area gets `properties.x` / `properties.y` = `cell * CELL_CANVAS_UNITS`
  (40) plus `properties.cell` for the raw coords; every way gets the midpoint of
  its two cells; a gateway sits on the parent cell it opens from.
- The graph view reads `properties.x`/`y` on load, so with **physics off**
  (graph mode) the world appears as painted. This is layout only — travel is
  still one turn per cell, and `cell_scale` remains unread.
- Not aligned yet: the graph's **background image** transform is independent, so
  the nodes form the painted shape but may not overlay the art until the
  background is fitted to the same rect. The `🗺️ Map` (cardinal) layout also
  overrides these positions by design (it derives an XY map from exit
  directions), so use graph mode + physics off to see the painted layout.

### Map layout now reads the grid (2026-09-25)

`GraphLayoutEngine.applyCardinalLayout` gained a **grid mode**: when the payload
has `properties.cell` on its areas (painted, not hand-authored) it places areas
and ways at their exact painted coordinates and leaves physics off — the map is
read, not BFS-derived and force-settled. Hand-authored worlds keep the original
cardinal BFS fallback. Pure helpers `gridPosition`/`hasPaintedGrid` are
unit-tested (`tools/unit/test_graph_layout_engine.js`, 4 tests); the node-moving
path needs a live network and is verified in-app. This supersedes the "Map
overrides painted positions" caveat above for painted worlds.

Tests: `tests/test_world_compile.py` +1 (area `cell`/`x`/`y`, way midpoint) and
the gateway position assertion.
