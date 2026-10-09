---
type: task
status: review
area: ui
priority: high
related: [task-596, task-589, task-647, task-588]
blocked_by: [task-758]
---

# task-759: WorldPainter biome palette: illustrated tile grid, category rail, and a rich detail panel

**Filed:** 2026-10-09
**Related:** task-596, task-589, task-647, task-588
**Blocked by:** task-758 (the record fields the panel renders)

**Design:** `docs/design/world-environment-taxonomy.md` §"Gap analysis: mockups
vs shipped biome palette"; concept art in `docs/design/image mockups/`
(`WorldPainter Biome Selector UI.png`, `WorldPainter Biome Palette Editor.png`).

## What

Replace the WorldPainter's grouped `<select>` with the palette the mockups draw:
a searchable, category-railed tile grid with colour swatches and illustrations,
a persistent detail panel answering what a tile is / does / connects to / what
lives there, and a reach from any tile to the exits it implies. task-596 grew the
dropdown into a filterable, swatched, one-line-detail picker; this is the actual
authoring surface the art shows, not another dropdown.

## Why

The vocabulary is now 106 biomes + features + roads + interiors behind one
`<select>`. task-596 answered "bridge vs road?" and "where is the exit?" in a
single detail line, but the list is still a scroll, and it cannot show what the
mockups show — illustrated tiles and a panel with neighbours, climate, resources
and creatures. `docs/design/world-environment-taxonomy.md` §"Gap analysis"
records the exact shortfall: no tile grid, no detail panel, no climate
matrix, and the records lack the `resources` / `creatures` / `climate_range` /
`neighbours` fields the panel needs (task-758). An author painting a
30-location town should see the palette, the tile, and everything about it
without leaving the canvas.

## How

- **No new module, no Lit.** The painter is plain-DOM classic script; the pure
  view-model lives in the existing tested seam `static/js/worldpainter/grid-model.ts`
  (`paletteSections`, `filterPalette`, `flattenPalette`, `paletteTile`,
  `tileKind`, `tileDetail`, `detailRows`), and the editor renders the surface
  (`_palettePanel`) with the same `_el`/`_btn` helpers the rest of the panel
  uses. A parallel `palette.ts` + Lit component was the original plan; reusing
  the seam is the smallest coherent change and keeps one module contract.
- **One source of truth.** The browser never reads `biomes.json`. Extend the
  existing derived vocabulary route (`handle_painter_vocabulary`,
  `routes/world_grid_ops.py:287`) so it ships the new fields from
  `engine/biomes.biomes()`; the palette consumes the same derivation the editor
  already uses (task-588 Q5). No second copy of the vocabulary.
- **Category rail** derived from the existing `terrain` / tag sets — Ecosystems,
  Terrain & Water, Human & Special, Roads, Interiors. No new taxonomy file; a new
  biome lands in a category by its tags.
- **Tiles** render the colour swatch already computed for the palette, the name,
  a kind glyph (place / building / not-a-place / road), and the one-line "is"
  string task-596 already composes.
- **Detail panel** composes the fields the record carries — prose, kind, ground
  surface, engine tags, entry/exit phrase, natural/unlikely neighbours,
  transition biomes, and climate (temperature / rainfall / elevation, task-758).
  A field the record does not carry renders as "unknown" — never invented. Until
  task-758 lands, the panel shows the subset that exists (prose, kind, surface,
  tags, crossings, entry/exit).
- **Resources / Creatures / Hazards are read from their registries, not copied
  onto the biome** — resources and creatures by tag-intersection with the
  `data/library/resource_distribution/` and `hostile_distribution/` tables
  (task-718/569), hazards from `data/worldpainter/hazards.json` (task-745). The
  panel links to those entries; it does not duplicate them, and it shows nothing
  until the registries exist. This is deliberate: baking resources/creatures into
  the biome would be a second source of truth for spawns.
- **Climate matrix** (temperature × humidity) is rendered only when the climate
  fields exist; it is a view over task-758 data, not a new source.
- **Interactions.** Clicking a tile sets the active brush and closes on pick;
  `Esc` closes; the search box keeps focus for type-to-filter; Space-to-pan
  still arms after a pick (do not regress bug-511). The `<select>`'s keyboard
  path (arrow + Enter) is preserved for accessibility.
- **Reuse, do not fork.** The cell inspector's `exits` row (task-596) stays the
  authority for "where is the exit"; the palette links to it rather than
  re-deriving adjacency.

## Steps to verify

1. Open **🗺️ WorldPainter** on a town scope (`kraktooth_goblin_camp` →
   `eldenford_interior`), open the paint tool.
   - expected: a tile grid with a category rail and a detail panel, not a `<select>`.
   - observed:
2. Type `bridge` in the search.
   - expected: the grid filters to the bridge tile(s); the detail panel shows
     "crosses river, stream, ravine, chasm · cross the bridge" and its kind.
   - observed:
3. Click a biome tile.
   - expected: the brush is set, the palette closes; holding Space pans the view.
   - observed:
4. Inspect the detail panel against a task-758-populated record (e.g. Temperate
   Mixed Forest).
   - expected: neighbours, resources, creatures, climate render from the record;
     a record with no climate shows "unknown", not a fabricated value.
   - observed:

## Acceptance

- [x] A palette surface (tile grid + category rail + detail panel) replaces the
      `<select>` in the WorldPainter paint tool. (Correction: it is not published
      on `VW`; the view-model is on `VW.gridModel` and the editor renders it.)
- [x] Tiles show colour + name; the grid is grouped by a rail derived from
      `terrain`/tags and is searchable by name and id. (The `kind` is shown in
      the detail panel, not yet as a per-tile glyph.)
- [ ] The detail panel renders every field the record carries and invents none —
      done for the fields that exist now; the resources/creatures/hazards panels
      wait on the task-718/745 registries.
- [ ] The vocabulary route serves the task-758 climate/neighbour fields — waits
      on task-758 (the `terrain` field it did need is now served).
- [x] Picking a tile sets the value and drops focus (Space still pans, bug-511);
      `Esc` in the search closes; the search box keeps focus while typing.
- [x] Pure view-model helpers are unit-tested in
      `tools/unit/test_worldpainter.js` (grouping, filter, detail composition).
- [ ] Live browser check on a town scope: tiles, rail, filter, detail and pick
      all behave; screenshot recorded.

## Resolution (2026-10-09)

Shipped in two parts, no new module:

- `static/js/worldpainter/grid-model.ts` — pure view-model: `paletteSections`
  (rail derived from `terrain` + `tags`: wild terrain → rooms by purpose →
  buildings by category → structure), `filterPalette`, `flattenPalette`,
  `paletteTile`, `tileKind`, `tileDetail`, `detailRows`. `@contributes` updated.
- `static/js/worldpainter/editor.ts` — `_valueControl` is now a read-out (swatch
  + current tile + one-line detail) with a button that opens `_palettePanel`:
  rail + search + tile grid + detail panel. Open state, category and query live
  on `state` so a render rebuilds where the author left it. `_biomePalette` and
  `_tileDetail` were removed (logic moved to the view-model).
- `routes/world_grid_ops.py` — `handle_painter_vocabulary` now ships `terrain`,
  which the rail derivation needs.

**Verified:** `npm run build:ts` clean; `npm run typecheck` clean;
`python tools/ts_convert.py check` green; `node tools/unit/run.cjs` → **644
passed** (was 636; +8 palette tests); `pytest tests/test_world_grid_routes.py`
→ 53 passed. Live browser pass still owed.

**Deferred (named, not silent):** per-tile kind glyph, climate matrix, and the
resources/creatures/hazards panels — the last wait on task-718/745 registries;
the climate/neighbour rows wait on task-758; both are tracked, not dropped.

## Files

- `static/js/worldpainter/grid-model.ts` — palette view-model (+ emitted `.js`)
- `static/js/worldpainter/editor.ts` — `_valueControl`, `_palettePanel`
- `routes/world_grid_ops.py` — `handle_painter_vocabulary` ships `terrain`
- `tools/unit/test_worldpainter.js` — 8 view-model tests

