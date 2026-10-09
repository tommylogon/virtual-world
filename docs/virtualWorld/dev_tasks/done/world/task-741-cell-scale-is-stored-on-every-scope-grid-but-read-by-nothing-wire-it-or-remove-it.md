---
type: task
status: done
area: world
priority: medium
---

# task-741: cell_scale is stored on every scope grid but read by nothing: wire it or remove it

**Filed:** 2026-10-08
**Related:** task-495 task-496

## Goal

The WorldPainter grid dialog's scale field writes grid.cell_scale, and it is read by zero engine call sites: engine/world_compile.py:147 states travel time stays one turn per cell and cell_scale is not read by the compiler or movement. Decide the intent: either wire it into movement as turns-per-cell (a real travel-cost change) or delete it from the dialog, the grid record and the round-trip. A field that persists and does nothing is worse than no field.

## Decision

**Remove it.** User direction (2026-10-09): turns-per-cell is not wanted. A grid keeps only `{w, h}`; travel stays one turn per cell.

## Acceptance

- [x] `cell_scale` removed from the model, the dialog, the route payload, the
      player-map payload and the round-trip.
- [x] Legacy data is dropped, not carried: `ensure_grid`/`normalise_grid` write
      `{"w", "h"}` only, and normalise strips a stale `cell_scale` (regression
      test `test_normalise_grid_is_tolerant`).

## Resolution (2026-10-09)

Removed end to end:

- `engine/world_grid.py` — `ensure_grid(record, w, h, mode)` (param dropped),
  normalise writes `{"w","h"}`, model doc updated; the now-unused `_as_float`
  helper deleted.
- `routes/world_grid_ops.py` — grid payload `{"w","h"}`, both `ensure_grid`
  call sites, docstring; `routes/player_ops.py` map scope payload.
- `static/js/worldpainter/editor.ts` — `WpPayload.grid`, the grid dialog's
  `scale` input + `wp-grid-scale` role, and both grid POST bodies; rebuilt to
  `.js`. `static/js/agent/turn-minimap.ts` `MapScope` type.
- Tests: `test_world_grid.py`, `test_world_scopes.py`,
  `test_world_grid_routes.py`, `test_world_compile.py`, `test_player_map.py`,
  `tools/unit/test_worldpainter.js`.
- Data: `cell_scale` stripped from `data/scenarios/mansion.json` and
  `data/scenarios/kraktooth_goblin_camp.json` (10 grid records) via a
  formatting-preserving regex; both reparse.
- Docs: `WorldPainter.md`, `World Scopes.md`.

**Verified:** `pytest test_world_grid/test_world_scopes/test_world_grid_routes/
test_world_compile/test_player_map` → 251 passed; `npm run build:ts` and
`npm run typecheck` clean; `node tools/unit/run.cjs` → 636 passed.

