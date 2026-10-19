---
type: task
status: inprogress
area: ui
priority: medium
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
  painter already tracks both) — filter `paletteSections` rather than shipping a
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
   - expected: the palette offers no buildings; switch to a settlement → buildings appear; interior → interior entries appear.
   - observed: TODO
2. Apply the genre filter.
   - expected: entries outside the scenario's setting are hidden.
   - observed: TODO
3. Open the cell inspector.
   - expected: the exits row lists diagonal (NE / NW / SE / SW) neighbours as well as cardinal.
   - observed: TODO

## Acceptance

- [ ] Palette entries are filtered by the active layer and map mode.
- [ ] A setting / genre filter limits the palette to the scenario's vocabulary.
- [ ] The exits row reports diagonal (NE / NW / SE / SW) neighbours as well as cardinal.
- [ ] No second vocabulary list; the filter derives from the existing `paletteSections` data.

## Files

- `static/js/worldpainter/grid-model.ts` — `paletteSections` / `filterPalette`.
- `static/js/worldpainter/editor.ts` — `_palettePanel`; cell inspector exits row.
- `routes/world_grid_ops.py` — vocabulary route (genre / setting field if needed).

## Audit note (2026-10-16)

Moved from inprogress back to todo: it was not being worked. No uncommitted changes in the working tree or in any of the eight git worktrees touch this card's files, and nobody is editing it. 0 of 4 acceptance boxes checked; no commit references it.

## Progress (2026-10-19)

Part 1 only (mode filter). Added \GM.paletteForMode(sections, mode)\ in grid-model.ts and applied it inside \_paletteSections\ in editor.ts, the single entry point both the toolbar value picker and the palette panel read through. Rules: world hides oom:*\ and \uilding:*\; town hides oom:*\ except oom:outdoor\ (porch, courtyard, balcony); interior, unknown and missing modes are untouched. Structure is never hidden.

Measured against data/worldpainter/biomes.json (106 tiles): a world scope now offers 21 tiles (was 106), a town 56, an interior 106. Live data supports the rule: deep_woods (world) paints only wild terrain (sparse_forest, dense_forest, stream, river, cliff, hills); eldenford_interior (town) paints terrain plus temple, market, cemetery. 4 mechanism tests and 1 wiring test added (pass).

**Open, not done:** interior is unfiltered on purpose, because bear_den (interior) has 0 painted cells and there is no evidence of which terrain an interior needs. Setting/genre filter (part 2) and diagonal exits (part 3) are untouched. When the active value is filtered out by a mode, the existing _valueControl behavior resets it to the first offered tile; that reset is not yet checked live. Browser steps unrun; acceptance stays unticked.
