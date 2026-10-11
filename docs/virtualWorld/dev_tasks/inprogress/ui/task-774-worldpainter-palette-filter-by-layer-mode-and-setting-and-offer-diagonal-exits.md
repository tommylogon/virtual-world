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
