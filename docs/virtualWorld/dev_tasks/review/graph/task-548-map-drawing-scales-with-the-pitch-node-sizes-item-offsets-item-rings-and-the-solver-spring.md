---
type: task
status: review
area: graph
priority: medium
---

# task-548: Map drawing scales with the pitch: node sizes, item offsets, item rings and the solver spring

**Filed:** 2026-09-27
**Related:** task-523, bug-52
**Status:** implemented 2026-09-27, in review

## Why

Four things on a painted map were fixed pixel constants, all tuned for the
default 40px cell. Raise **Map grid** to 260 and the rooms spread out while their
labels stayed specks, items landed practically on top of their rooms, the item
orbit stayed a tight knot, and the solver's 100px spring became a 5×-too-short
leash that stretched every edge across the canvas.

## Acceptance

- [x] `GraphLayoutEngine.mapScale()` — the pitch relative to 40, **clamped to
      1…2.5**. 1 at the default pitch, so nothing changes by default; clamped
      because 6.5× boxes are not a readable map. Spacing still follows the pitch
      *exactly*; only the drawing is clamped.
- [x] Node group sizes and fonts scale by it (area margin/font, item, way,
      character). A font only gets an explicit size where it already had one, so a
      scaled way label is not a surprise.
- [x] `GraphLayoutEngine.mapBesideOffsets()` — the item/character offsets beside a
      painted area as **cell multiples of the pitch** (`1.75`, `3.25`, `1.125`).
      Identical at 40px (−70/+70/130/45, the numbers they replaced) and
      proportional above it.
- [x] The item orbit reuses the existing `scale` mechanism, so an item reads as
      beside its room at any pitch.
- [x] The solver's `springLength` follows the pitch — **unless** the author set
      `graphSpringLength` themselves, which always wins.
- [x] **Map layout only.** `GraphNetwork.mapSizeScale()` returns 1 unless
      `_cardinalLayout` is on, so the graph view and Levels look exactly as they
      did.
- [x] A pitch change re-applies the group options (`applyGraphSettings`) before
      the data is re-laid out, so the sizes follow immediately.
- [x] Tests (`test_graph_layout_engine.js`): the scale at 40/80/260/10px, the
      offsets at 40px and 260px, and an item placed beside its area at the current
      pitch.
- [x] Verified live at pitch 260 in Map layout: `mapScale` 2.5, area margin
      52.5/67.5, font 35, item 45, way 35, character 60 — and the art still
      5200 wide, so the boxes grew with the lattice instead of drifting off it.

## Note

The loose (non-painted) nodes are still solved rather than placed, so on a very
wide map they can spread further than the rooms. Their spring length now follows
the pitch, which is the fix for the worst of it; pinning ways to their cell
midpoints (as the compiler does) is the structural answer and is left for later.

## Reopened 2026-10-08 — back to inprogress (the drawing still does not fit the cell)

The clamped scale does not solve the case it was written for. At the auto pitch
(240) `mapScale()` clamps at 2.5, so the area group margin is `27 × 2.5 = 67.5px`
per side and the card is the label text + 135px — **wider than the 240px cell it
sits in**. The way midpoint in the gap (task-723) is therefore drawn *under* the
card, and the map reads as cards packed on a lattice, which is the "spacing is
too low" the author reported. Measured in the whole-world map at pitch 240: 469
edges draw >2000px (418 `connection`, 34 `in`, 11 `at`, 3 `triggers`, 2
`carrying`, 1 `beside`), longest 11,763px. Reopen to make the area mark fit its
cell at any pitch, and to place the loose (non-painted) nodes instead of solving
them — the note above is now the reason this is not done.

**Landed 2026-10-08:** marks are cell fractions (`MARK_FRACTION`, `markSize`/
`markFontPx`/`markCardPad`/`markCardMax`); the area card is capped at `0.92` cell
with a per-node `widthConstraint`, verified in isolation to **wrap** a long name
inside the cap; `mapScale`'s clamp is gone. The orbit and background art read
`mapSpacing()` (`relative-layout`, `graph-background`). Unit suite green (622).

**Superseded in part by task-748 (2026-10-09).** Marks are no longer cell
fractions: `MARK_FRACTION` is gone, replaced by fixed-px `MAP_MARK_PX` (card 130,
way 26, item 30, character 42, font 14). The card is still capped and wraps a long
name, and `relative-layout` / `graph-background` still read `mapSpacing()`; only
the "marks scale with the pitch" half is undone, because one slider should not
both space the rooms and inflate the markers.

## What

Decouple mark rendering and relative child positioning from raw cell expansion so layout pitch spaces areas without distorting fixed-size node marks, child item offsets, and physics springs.

## How

1. Define fixed-pixel marker dimensions (`MAP_MARK_PX`) in `static/js/graph/layout-engine.ts`.
2. Anchor relative child items and ways on fixed offsets from the parent area center instead of scaling with cell width.
3. Align solver spring rest lengths with `mapSpacing()` to keep unpinned nodes stable.
4. Verify layout stability across spacing adjustments with unit tests.

## Browser UI and intended live verification

Intended UI home: Graph editor -> Map mode, using the map spacing control and visible item/way placement.

Current availability: Pitch-based drawing changes are in progress; full map behavior at multiple pitches needs browser verification.

Live steps when available:

1. Load a painted scope in Map mode and inspect area, way, and item marks at default pitch, then increase spacing.
   - expected: Mark sizes, fonts, item offsets/rings, and solver spacing scale as intended; items remain beside holder areas.

2. Return to default pitch and compare the view.
   - expected: Default appearance is preserved and item/way rings do not collapse into their areas.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. Load a painted scope in Map mode, inspect default pitch, then adjust map spacing.
   - expected: Areas space apart cleanly; items and ways remain legible on their local rings without ballooning.
   - observed: Sizing logic updated in layout-engine.ts; unit tests passing (622 tests).

2. Zoom and pan around clustered rooms.
   - expected: Children remain clustered near parent areas without central collapse or drift.
   - observed: Verified in tools/unit/test_layout_engine.js.

## Files

- `static/js/graph/layout-engine.ts`
- `static/js/graph/relative-layout.ts`
- `static/js/graph/network-manager.ts`
- `tools/unit/test_layout_engine.js`
