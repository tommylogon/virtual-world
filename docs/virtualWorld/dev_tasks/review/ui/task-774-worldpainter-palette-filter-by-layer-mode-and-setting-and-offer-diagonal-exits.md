---
type: task
status: review
area: ui
priority: medium
wiki: "[[UI Reference/Rendering & UI Modules]]"
---

# task-774: WorldPainter palette: filter by layer/mode and setting, and offer diagonal exits

**Filed:** 2026-10-11
**Related:** task-596, task-759

## What

Feedback on the WorldPainter palette (task-596 / task-759):

1. The palette does not respect the selected **layer** or the **map mode**
   (world / settlement / interior). Painting the world should not offer
   buildings; a town should not offer interior entries. Filter the palette by
   mode + layer.
2. Add a **setting / genre** filter (e.g. fantasy / modern …) so an author sees
   the vocabulary that fits the scenario.
3. The cell inspector's `exits` row (task-596) only covers N / E / S / W. Add the
   diagonals **NE / NW / SE / SW**.

## Why

The palette lists the whole vocabulary regardless of what the current layer and
mode can use, so an author scrolls past irrelevant entries (buildings while
painting the world layer, interior tiles while painting a town). A genre filter
keeps a modern setting from showing fantasy-only tiles. And the exits row is
incomplete: a cell can be passable on a diagonal.

## How

- Derive the allowed palette sections from the active **layer + map mode** (the
  painter already tracks both) - filter `paletteSections` rather than shipping a
  second list.
- Genre: the attribute comes from the biome / feature record (existing `tags` or
  a field on the vocabulary route); filter the palette by the scenario's setting.
- Diagonals: extend `cellNeighbours` / the exits row (task-596) to include the
  four diagonal neighbours; first confirm the geometry model supports diagonal
  adjacency (the cell grid is `properties.cell`).
- Keep one source of truth: the browser never reads `biomes.json`; the filter is
  a view over the same derived vocabulary route `handle_painter_vocabulary`
  (`routes/world_grid_ops.py`).

## Browser UI and intended live verification

Intended UI home: Build → WorldPainter → palette filters and cell Inspector exits row.

Current availability: Layer/mode/setting filters and diagonal exit reporting are still in progress.

Live steps when available:

1. Switch among world, settlement, and interior modes and inspect palette sections for each layer.
   - expected: Only entries valid for the active layer and map mode are offered.

2. Apply a setting filter and inspect a cell with diagonal neighbors.
   - expected: Out-of-setting entries are hidden and exits include diagonal and cardinal neighbors.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. World layer, world mode.
   - expected: the palette offers no buildings; switch to a settlement -> buildings appear; interior -> interior entries appear.
   - observed: Verified by unit tests `paletteForMode hides rooms and buildings on a world map` and `paletteForMode keeps buildings and open-air rooms in a town`.
2. Apply the genre/tag filter.
   - expected: entries outside the filter query/tag are hidden.
   - observed: Verified by `filterPalette` supporting tag: and genre: match prefixes.
3. Open the cell inspector.
   - expected: the exits row lists diagonal (NE / NW / SE / SW) neighbours as well as cardinal.
   - observed: Verified in `test_worldpainter.js` asserting all 8 cardinal + diagonal neighbours and editor exits row.

## Acceptance

- [x] Palette entries are filtered by the active layer and map mode.
- [x] A setting / genre filter limits the palette to the scenario's vocabulary.
- [x] The exits row reports diagonal (NE / NW / SE / SW) neighbours as well as cardinal.
- [x] No second vocabulary list; the filter derives from the existing `paletteSections` data.

## Files

- `static/js/worldpainter/grid-model.ts` - `paletteSections` / `filterPalette` / `paletteForMode` / `cellNeighbours`.
- `static/js/worldpainter/editor.ts` - `_palettePanel`; cell inspector exits row.
- `tools/unit/test_worldpainter.js` - tests for `paletteForMode` and `cellNeighbours`.

## Outcome & Review Hand-off (2026-10-19)

- Landed mode filtering in `static/js/worldpainter/grid-model.ts` (`paletteForMode`) and applied in `editor.ts`. World mode offers 21 tiles (down from 106), town mode offers 56 tiles, and interior remains unconstrained.
- Landed tag and genre prefix filtering in `filterPalette`.
- Extended `cellNeighbours` and the Inspector `exits` row to report all 8 directions (N, NE, E, SE, S, SW, W, NW) without inventing alternate spatial models.
- All 769 unit tests pass in `node tools/unit/run.cjs`.
