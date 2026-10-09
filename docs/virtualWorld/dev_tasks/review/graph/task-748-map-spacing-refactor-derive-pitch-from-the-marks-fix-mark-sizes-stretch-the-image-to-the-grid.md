---
type: task
status: review
area: graph
priority: high
related: [task-526, task-548, task-527, bug-528, bug-529, task-618, task-723]
---

# task-748: Map spacing refactor: derive pitch from the marks, fix mark sizes, stretch the image to the grid

**Filed:** 2026-10-09
**Related:** task-526 task-548 task-527 bug-528 bug-529 task-618 task-723

## Problem

The map's pitch (px between painted cells) is derived from the wrong things, and the marks drawn on it scale with the pitch. Three independent anchors are in play and none of them is the thing that actually matters.

- **Canvas.** `GraphLayoutEngine.autoMapSpacing` (`static/js/graph/layout-engine.ts:402`) computes `pitch = min(paneW, paneH) / AUTO_CELLS_ACROSS (10)`, clamped to `[AUTO_SPACING_MIN 40, AUTO_SPACING_MAX 200]`. On the current window (graph pane 718x263) that is `263 / 10 = 26.3`, floored to 40. The pitch ends up a property of the browser window, not the map, and auto can never exceed 200.
- **Marks.** `MARK_FRACTION` (`layout-engine.ts:313`) makes every mark a fraction of the pitch (area 0.92, way 0.26, item 0.30, character 0.42). Raising the spacing to make room therefore also inflates every way/item/character. The area name is separately capped (`FONT_MAX_PX`, `:323`), so labels and shapes disagree about whether they follow the pitch.
- **Image.** `GraphBackground._fitLayerToRect` (`static/js/graph/graph-background.ts:1120`) contain-fits the reference image, preserving its aspect ratio, inside the grid rect. The picture's shape then decides where the art lands instead of the grid.

This state is the tail of a chain of fixes. task-526 originally derived the pitch from the painted extent (`AUTO_SPAN_PX / longest`, clamp 24-300); the constants drifted (`AUTO_SPAN_PX 10000`, floor 240, cap 600) so auto clamped up and could not reach its own target; and the 2026-10-08 landing replaced the extent anchor with the viewport heuristic above. The pitch moved from the world to the canvas, and the clamp failure mode moved from "clamps up to 240" to "clamps down to 40".

## Intended model

1. **Marks are fixed size**, owned by their own settings (the node-size / item / character tools). They do not follow the pitch.
2. **The pitch is derived from the marks.** The binding constraints are:
   - `pitch >= area_card_width` - adjacent cards do not overlap;
   - `pitch >= area_card + way_mark` - a way sits at the midpoint between two areas, so the way radius plus the card radius must fit in half a pitch;
   - `pitch >= item/character cluster footprint` - the children laid beside a room fit in its cell.
   For a fixed mark configuration this is a **constant**: the same number for a 200x400 image, a 6000x300 image, a 40-cell camp and a 160-cell world. No dependence on image resolution, canvas size or painted extent.
3. **The image is a texture stretched over `grid_cells x pitch`.** The grid is authoritative; the reference art is scaled (non-uniformly where the aspect differs) to fill the grid rect. Aspect-preserving contain-fit is the bug here, not the feature.
4. **Auto is the mark envelope, not a viewport fit.** `autoMapSpacing` should return the constant from (2), re-derived when the mark sizes change - not `paneShort / 10`.

## Two distinct guarantees

Keep these separate; conflating them is how the current code failed.

- **No overlap (cell space).** A property of `pitch` versus `marks`. Holds for every world and every image once the pitch is the mark envelope.
- **No crowding (screen space).** Fixed marks plus a large world means a large canvas (a 160-cell world at a 120px pitch is ~19,200px wide). Zoomed out, fixed marks crowd because zoom shrinks the gaps but not the marks. The fix is LOD (hide or shrink marks below a zoom threshold), not a larger pitch. This is a deliberate return of the dots behaviour task-526 removed; bug-528 is the label-LOD half.

## Evidence (measured 2026-10-09, live app, 2737-node world)

- Payloads: `/api/state` 13,994,214 bytes; `/api/state?lite=1` 3,370,121; `/api/graph/nodes` 2,166,549; `/api/graph/edges` 1,162,276.
- Graph pane `#graph-container` is 718x263 inside a `.app-main` of 718x557 (the event section pins 200px, the toolbar 65px). The pane is correctly sized; the formula is what is small.
- `autoMapSpacing`: `min(718, 263) = 263`, `263 / 10 = 26.3`, floored to 40. The Tune stepper reads `40 auto`.
- Marks at pitch 40: way 10px, item 12px, character 17px. At pitch 660: way 172px, item 198px, character 277px - a 16.5x growth for a 16.5x pitch change.
- Scope grids vs reference-image aspect: `world` 20x10 (2.0) vs `kraktooth world map.png` 1536x513 (2.99); `goblin_camp` 20x10 (2.0) vs 1536x515 (2.98); `abandoned_farms` 160x100 (1.6) vs 771x291 (2.65); `west_woods` 20x40 (0.5) vs 291x373 (0.78). Matched: `deep_woods` 45x30 (1.5), `eldenford_interior` 30x20 (1.5), `raven_river` 168x112 (1.5). Every reference has `rect: null`, so `_applyReferenceLayout` always takes the contain-fit branch; where the aspect differs the art is letterboxed and stops covering the edge cells. For `world`, a 2.99-aspect image in a 2.0-aspect grid is drawn 20 cells wide by ~6.7 cells tall in a 10-cell-tall grid.

## Acceptance

- [x] `autoMapSpacing` (or its replacement) returns a pitch derived from the mark footprint, with no `paneShort` term and no image term.
- [x] Marks are fixed size: changing the pitch from 40 to 660 must not change the drawn size of any area, way, item or character.
- [x] A way mark fits between two adjacent area cards at every pitch, asserted on the numbers rather than by eye.
- [x] The background reference image is stretched to the grid rect; at a mismatched aspect it fills the grid instead of letterboxing.
- [x] The manual stepper and the `A` override still round-trip (task-526's surviving acceptance).
- [x] LOD is a decision, not an accident: marks are allowed to crowd when zoomed out; a zoom-gated hide/shrink is deferred (bug-528 / task-527). No silent middle ground.
- [x] Unit tests for the pitch derivation and the fixed-mark invariant replace the current viewport-clamp and pitch-fraction tests in `tools/unit/test_graph_layout_engine.js`.
- [x] Live check: load the 2737-node world in Map mode, confirm no overlap at the derived pitch and that the reference art covers its painted cells.

## Files

- `static/js/graph/layout-engine.ts` - `mapSpacing`, `MARK_FRACTION`, `markSize` / `markFontPx` / `markCardMax`, `autoMapSpacing`, `AUTO_CELLS_ACROSS` / `AUTO_SPACING_MIN` / `AUTO_SPACING_MAX`, `gridPosition`, `wayMapPosition`.
- `static/js/graph/network-manager.ts` - `applyAutoMapSpacing`, `_markSizes`, `buildNodeConfig`, `_nodeLabelPolicy`, `nodeSizeScale`.
- `static/js/graph-manager.ts` - `setMapSpacing`, `setAutoMapSpacing`, `_syncMapSpacingButton`.
- `static/js/graph/graph-background.ts` - `_fitLayerToRect`, `_mapUnitsPerCell`, `paintedGridRect`, `_applyReferenceLayout`.
- `tools/unit/test_graph_layout_engine.js`, `tools/unit/test_graph_tuning.js`.

## Landed 2026-10-09

- Replaced the pitch-fraction size model with fixed `MAP_MARK_PX` (card 130, pad 8, font 14, way 26, item 30, character 42) plus `MARK_ENVELOPE_GAP` 20. `markSize` / `markFontPx` / `markCardPad` / `markCardMax` now return those constants; `MARK_FRACTION` and `FONT_MAX_PX` are gone.
- Added `markEnvelopePitch()` = `(card + way + gap) * nodeSizeScale` = 176 at node-size 1. `mapSpacing()` falls back to it, `autoMapSpacing()` returns it (viewport arg ignored), and `AUTO_CELLS_ACROSS` / `AUTO_SPACING_MIN` / `AUTO_SPACING_MAX` are deleted.
- `_fitLayerToRect` stretches the reference to fill the grid rect instead of contain-fitting, so a mismatched aspect no longer letterboxes.
- Doc comments updated across `layout-engine.ts` / `network-manager.ts` / `graph-manager.ts`; the `window.GraphLayoutEngine` self-reference change is recorded in `tools/window-usage-reviewed.json`.

Verified live (2737-node world, Map mode):

- Marks fixed: way / item / character render 26 / 30 / 42 at BOTH pitch 660 and the 176 envelope (they were 172 / 198 / 277 at 660 before).
- Envelope is viewport- and world-independent: `autoMapSpacing` = 176 for viewports 400x400, 1400x1400 and 100000x100000, and for a 1-cell vs a 200-cell world. The `A` button sets `_mapSpacingAuto = true` and the pitch to 176.
- Image fills the grid: after a re-derive every layer rect's aspect equals its GRID's, not the image's - `world map` 20x10 -> 13200x6600 (AR 2.0, image 2.99), `abandoned farms` 160x100 -> 105600x66000 (AR 1.6, image 2.65), `west woods` 0.5, `eldenford_interior` 1.5.
- Unit: 632 pass (new envelope, fixed-mark and way-clearance tests). Gate: build / typecheck / lint / unit / header-survival / window-guards pass; the only failure is the pre-existing `module:check` pair (`engine/activities_loader.py`, `engine/effect_handlers/movement.py`), unchanged by this diff.

Residuals:

- **LOD deferred.** Fixed marks plus whole-world zoom means 1380 sub-pixel way borders overlap into a haze when zoomed out. The pitch invariant (no overlap) still holds in cell space; on-screen crowding is bug-528 / task-527's subject.
- `mapSizeScale()` (the solver spring length) still tracks the pitch, so at 176 the spring is 528px. Map-mode painted nodes are physics-off, so only loose nodes see it; not re-measured live.
- On reload in the whole-world view the persisted layer rects are used until the pitch moves (task-526's `reconcileAllForGapChange` gap), so the fill only shows after a re-derive.
