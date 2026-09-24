---
type: task
status: review
area: world
priority: medium
---

# task-495: WorldPainter: recursive scope grids and 3-mode editor

**Filed:** 2026-09-24
**Related:** task-397, task-398, task-400
**Design:** `docs/design/worldpainter-knowledge-and-fog.md`,
`docs/design/world-environment-taxonomy.md`

## Goal

Authoring layer: every world scope owns a bounded grid at its own resolution, with three modes - world (zones as cells, no interiors), town (paint settlement grid: walls, gates, roads, markets, buildings), interior (building/floor grid: rooms, doors, windows, tags). Zones ARE world_scopes (engine/world_scopes.py); select a zone to set its scale and open its drawn grid. Paint layers: biome/feature/road/elevation. Features are child scopes placed at a cell (e.g. a village inside a forest) that can be moved/added/deleted. Data model: per-scope grid_w/grid_h, cell_scale, layers, child placements; stable frames so references survive moves; a rule for move-overlap. UI renders each scope's grid.

## Acceptance

- A scope can be selected; its grid (`grid_w`/`grid_h`, `cell_scale`, layers) opens in the matching mode (world/town/interior).
- A feature (child scope) can be placed at a cell, moved, added and deleted; the parent's placements update.
- Grids are recursive: a parent cell can hold a child scope whose own grid opens in the next mode.
- Moving a feature over occupied cells follows a documented rule (forbid / displace / merge) and preserves ids/references.
- The scope manifest + child placements serialize and round-trip, covered by tests.

## Progress — 2026-09-24 (grid model)

**Started with the data model**, the piece both the editor (this task) and the
compiler (task-496) need and the one independent of the still-open
grid-canonical-vs-baked decision.

- **`engine/world_grid.py`** (new) — pure helpers over the scope manifest:
  - `cell_id(scope_id,x,y)` / `parse_cell_id` — a cell's stable identity
    (`"<scope>:<x>,<y>"`), the compiler's future area id; stable across edits
    elsewhere on the grid.
  - `ensure_grid(record, w, h, cell_scale, mode)` — creates/resizes; a shrink
    drops out-of-bounds paint and placements rather than dangling them.
    `has_grid`, `grid_size`, `in_bounds`.
  - Paint layers `biome` / `road` / `elevation` via `paint` / `painter_at`
    (bounds-checked; erasing a cell removes empty layers).
  - Features are **child scopes placed at a cell** (`placements`), not a stored
    layer: `place` / `move` / `remove` / `cell_of` / `occupant_at` /
    `feature_layer` (the derived `feature` paint view the editor draws).
  - **Overlap rule chosen: `forbid` by default** (raise), with
    `on_overlap="displace"` as the opt-in; `merge` is deliberately deferred to
    the compiler because it redefines child-scope identity (documented in the
    module docstring). Returns `placed` / `moved` / `displaced`.
  - `validate(manifest)` — bounds, unknown layers, unknown/duplicate children.
  - `normalise_grid(record)` — tolerant load-time cleanup, wired into
    `engine/world_scopes.py::normalise_manifest` (a scope that never had a grid
    is left untouched, so existing saves are byte-identical).
- **`tests/test_world_grid.py`** (18) — cell identity, resize pruning, paint,
  place/move/displace/remove, overlap forbidding, validation, malformed-data
  cleanup, and a JSON + `normalise_manifest` round-trip.

Still open in this task: the editor UI (render each scope's grid in the
matching mode, select/place/move/delete features), recursive drill-down into a
child scope's grid, and the "merge" overlap policy if the compiler needs it.

## Progress — 2026-09-24 (authoring API + editor UI)

**Backend** (`routes/world_grid_ops.py`, thin registrar `routes/world_grid.py`,
registered in `app.py`):

- `GET  /api/world/scopes/<id>/grid` — scope + grid + layers + placements +
  derived feature view + child cards + parent + breadcrumb.
- `POST /api/world/scopes` — create a scope (a feature is a child scope); id
  disambiguated on collision, display name never renamed.
- `POST /api/world/scopes/<id>/grid` — create/resize (`w`,`h`,`cell_scale`,`mode`);
  a shrink prunes out-of-bounds paint/placements (via `world_grid.ensure_grid`).
- `POST /api/world/scopes/<id>/grid/paint` — set/erase one cell on a layer.
- `POST /api/world/scopes/<id>/grid/place` — place/move a child (`on_overlap`
  forbid default, `displace` opt-in).
- `POST /api/world/scopes/<id>/grid/remove` — remove a placement only (never the
  child scope record).
- Each mutating handler pushes its own **pre-state** undo snapshot; `app.py`'s
  after-mutation hook skips these paths so the first Undo is not a no-op (the
  same reason the NL batch path is special-cased).

**Front end:**

- `static/js/worldpainter/grid-model.js` — pure view-model: cell keys/ids,
  `nextMode` drill-down suggestion, render rows, deterministic layer colours,
  resize-prune preview, available children.
- `static/js/worldpainter/editor.js` — plain-DOM overlay: scope chooser,
  breadcrumb, mode badge, paint/erase/feature tools, layer + value picker, grid
  dialog, add-feature, grid render, place/move/remove, child drill-down.
  Overlap follows the documented rule (forbid, then a displace confirmation).
- `templates/index.html` — toolbar button + script tags.
- `static/js/main.js` — register `VW.worldPainter`, `VW.gridModel` and (fixing a
  pre-existing regression found while wiring this) `VW.structures`, since
  `main.js` resets `window.VW` after module scripts run and the bare globals are
  what survives.

**Tests / verification:** `tests/test_world_grid_routes.py` (8),
`tools/unit/test_worldpainter.js` (10). A live browser smoke test exercised
select → create grid → paint → add/place feature → drill into the child's town
grid end-to-end (and caught a dialog-input append bug, now fixed). `npm run
lint`, `npm run typecheck`, `python tools/js_module_index.py --check`, and
`node tools/unit/run.cjs` are clean (the 13 pre-existing `test_plan_tracker`
failures are unrelated).

Still open: the "merge" overlap policy is deferred to the compiler by design
(see the module docstring); no editor work needs it yet.
