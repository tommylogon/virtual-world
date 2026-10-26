---
type: task
status: review
area: ui
priority: high
wiki: "[[World Building/WorldPainter]]"
---

# task-881: WorldPainter: dock the palette to the right-hand side so opening it never pushes the canvas below the fold

**Filed:** 2026-10-19
**Related:** task-776, task-759, task-774

## What

Move the WorldPainter biome/tile palette (`_palettePanel()`) from a stacked vertical document block above the canvas into a dedicated, dockable right-hand sidebar beside the canvas viewport.

## Why

Today in `editor.ts`:
- The modal layout is rendered as a top-to-bottom vertical column:
  `[Toolbar] -> [Palette (when open, up to 380px tall)] -> [Canvas (480px)] -> [Footer]`.
- Opening the palette completely shoves the canvas down, frequently hiding it below the browser viewport fold on standard 1080p screens.
- The author has to scroll down to paint, scroll up to select another tile, and scroll down again to see the result.
- Task-776 Section B explicitly identifies this: "Palette as a side dock (right column with its own scroll) instead of a full-width block above the canvas."

## How

1. Layout container: Structure the main studio area as a flex row with two columns:
   - Left: Tool rail (`_toolRail()`).
   - Center: Canvas viewport (`_grid()` Konva container) with flex-grow: 1.
   - Right: Palette dock (`_palettePanel()`), fixed width (~320px), max-height matching the viewport, with internal overflow scroll.
2. Toggle behavior:
   - When `state.paletteOpen` is true, the right column expands smoothly or renders at 320px width beside the canvas.
   - When false, the right column is hidden or collapsed, letting the canvas take the full available width.
3. Canvas resizing: When the dock toggles, resize the Konva stage to fit the new center column width so no canvas clipping occurs.
4. Keep the single shared view-model and mode filtering from `grid-model.ts` (`paletteSections`, `paletteForMode`, `filterPalette`).

## Browser UI and intended live verification

Intended UI home: WorldPainter modal, right-hand dock

Current availability: Palette renders above the canvas as a full-width vertical block.

Live steps when available:
1. Open WorldPainter on any scope (e.g. `world`).
2. Click the tile value button to open the palette.
   - expected: Palette opens as a right-hand side dock beside the canvas; the canvas remains fully visible in the center without being pushed down.
3. Select different biomes and paint on the canvas.
   - expected: Canvas can be painted while the palette stays open on the right; no vertical page scroll needed.
4. Click close (✕) or toggle value button.
   - expected: Palette dock closes and canvas expands to fill the space.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: TODO
   - observed: TODO
2. Run unit tests `node tools/unit/run.cjs`.
   - expected: All unit tests pass.
   - observed: TODO

## Acceptance

- [ ] Palette renders in a right-hand side dock beside the canvas, not stacked vertically above it.
- [ ] Opening the palette does not push the canvas down or out of view.
- [ ] Palette has its own vertical scroll for categories and tile grid.
- [ ] Toggling the palette open/closed updates the canvas viewport smoothly.
- [ ] Unit tests verify the side dock structure in `editor.ts`.
- [ ] Zero em-dashes introduced.

## Files

- `static/js/worldpainter/editor.ts`
- `tools/unit/test_worldpainter.js`
