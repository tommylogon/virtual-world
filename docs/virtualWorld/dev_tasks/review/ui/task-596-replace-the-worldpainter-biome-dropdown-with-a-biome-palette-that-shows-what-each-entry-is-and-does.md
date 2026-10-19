---
type: task
status: review
area: ui
priority: medium
---

# task-596: Replace the worldpainter biome dropdown with a biome palette that shows what each entry is and does

**Filed:** 2026-09-30
**Related:** 

## What

The current single dropdown hides the difference between palette entry types. Replace it with a visible palette that can be filtered or grouped by kind - buildings, biomes, roads, ways - and that offers the information a person actually needs at paint time: what each entry is, what it does, and what it connects to. Two questions the palette must answer without opening anything else: 'what is the difference between a bridge and a road?' and 'where is the exit from here?'. Related to the palette: the inspector has no reach from a painted cell to the exits and ways touching it.

## Acceptance

- [x] The palette is grouped by kind (real `<optgroup>`s) and filterable by name
      or id (already shipped by task-561/task-647); the picker now also shows a
      **colour swatch** of what will be painted.
- [x] A per-tile detail line says what the entry **is** and **does**, from the
      vocabulary the compiler reads: prose, kind (place/building/not-a-place),
      ground material, and - on the road layer - the terrain it crosses and the
      phrase you arrive with.
- [x] "What is the difference between a bridge and a road?" is answered without
      opening anything else: *Bridge - A span carries the road over the gap ·
      crosses river, stream, ravine, chasm · "cross the bridge"* vs *Road - A
      worn track cut through the land · crosses sparse_forest, dense_forest,
      farmland, hills*.
- [x] "Where is the exit from here?" is answered by the cell inspector's new
      `exits` row: the passable neighbours N/E/S/W with their kind, so a solid
      neighbour reads as a wall and the map edge reads as an edge.
- [x] Vocabulary payload extended with `descriptions`/`surface` on biomes and
      `tags`/`biomes`/`entry_phrase`/`exit_phrase`/`descriptions` on features
      (same records the compiler reads, so the preview cannot drift).
- [x] Live proof (Playwright, `localhost:4465`): detail strings above; cell
      (14,8) panel reads `exits  N: empty · E: empty · S: road · W: road`.
- [x] Unit test `cellNeighbours names the exits around a cell (task-596)`.

## Why

A plain text dropdown concealed biome colors, environmental properties, and generated vegetation types.

## How

Replaced dropdown with a visual biome palette swatch bar showing biome swatch colors, tooltips, and associated tags.

## Steps to verify

1. Open WorldPainter tool and inspect biome selector
   - expected: Visual palette displays swatches with tooltip descriptions and tags
   - observed: Biome palette renders and selects active paint swatch

## Files

- `static/js/worldpainter/editor.ts`
- `static/js/worldpainter/canvas-view.ts`

## Browser UI and intended live verification

Intended UI home: WorldPainter → terrain/road paint palette; after painting a cell, inspect it with the cell inspector. The palette answers what an entry is and does; the cell inspector answers which exits touch that cell.

Current availability: The task records a live pass on localhost:4465: bridge and road detail text was visible, and the cell at (14,8) showed `N: empty · E: empty · S: road · W: road`.

Live steps when available:
1. Open WorldPainter, choose the road layer, and select Bridge; then select Road without opening another panel.
   - expected: the palette shows each entry's colour swatch, description, kind, terrain crossings, and arrival phrase; the bridge text distinguishes an elevated span from a worn track.
2. Filter the palette by a name fragment and then by an ID fragment.
   - expected: only entries whose name or ID matches remain, and their swatches and descriptions stay attached to the correct option.
3. Paint or select cell (14,8), open its cell inspector, and read the `exits` row.
   - expected: N and E read empty, S and W read road; a solid neighbour reads as a wall and the map boundary as an edge.
4. Switch from road to biome layer and inspect a biome entry.
   - expected: its prose and surface come from the compiler vocabulary record, matching the palette content rather than a second UI-only definition.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
