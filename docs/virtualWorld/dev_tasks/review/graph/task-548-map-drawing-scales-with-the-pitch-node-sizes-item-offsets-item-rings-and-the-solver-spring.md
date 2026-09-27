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

## Problem

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
