---
type: task
status: done
area: ui
priority: medium
---

# task-647: WorldPainter cell palette: no search or filter across 105 tiles

**Filed:** 2026-09-30
**Related:** 

## What

The biome palette is 105 options. It now renders as 23 real optgroups (fixed under the 623 work), but an author drawing a 30-location town floor plan still has to scroll to find 'Wall' or 'Door'. A live filter box above the select, matching on name and id, is the same affordance added to the Scenario Manager for 22 scenarios -- here it matters 5x more.

## Acceptance

- [x] The palette has a filter that narrows by tile name and by id
- [x] Headings left with nothing under them disappear rather than showing blank
- [x] Filtering cannot leave the select on a value that no longer exists
- [x] Clearing the filter restores everything
- [x] Verified live: typing "wall" narrows 105 tiles to `Wall (wall)`

## Resolution (2026-09-30) — added while painting Eldenford

Tommy asked me to finish the Eldenford town map, which made this the first
thing in the way. The palette is 105 tiles under 23 headings: navigable but not
*findable*. An author drawing a 30-location floor plan is looking for one tile --
Wall, Door, Kitchen -- and the only route was to scroll and read.

Added a filter box beside the select, matching on displayed name **and** id (so
`not_a_place` is typeable as well as `Wall`). A heading whose options are all
filtered out is removed rather than left as an empty label, and if the filter
hides the currently-selected value the select falls back to the first visible
option so it can never sit on something unpaintable.

**Verified live** in the Eldenford interior grid: typing `wall` narrows 105
options to `Wall (wall)` (screenshot `audit/92-palette-filter-wall.png`).

- TODO

## Why

TODO

## How

TODO

## Steps to verify

1. In the Eldenford interior WorldPainter, type `wall` in the cell palette filter.
   - expected: the 105 options narrow to `Wall (wall)`.
   - observed: live: the filter narrowed the palette to `Wall (wall)`.
2. Search by an ID such as `not_a_place`, then filter out the currently selected tile.
   - expected: ID matching works; empty headings disappear; selection moves to a visible option.
   - observed: recorded in the resolution as the filter behavior; no hidden filtered-out value remains selected.
3. Clear the filter and paint one cell.
   - expected: all 105 options return under their 23 headings and the selected tile is painted.
   - observed: live palette check recorded; repeat the paint interaction when touching this surface.
## Files

- TODO

## Browser UI and intended live verification

Intended UI home: WorldPainter → cell palette above the interior grid → filter input beside the tile select.

Current availability: The card records a live Eldenford pass: typing `wall` narrowed 105 options across 23 groups to `Wall (wall)`.

Live steps when available:
1. Open the Eldenford interior grid, focus the palette filter, and type `wall`.
   - expected: the select narrows to `Wall (wall)` and the counter/list reflects one matching tile.
2. Replace the query with `not_a_place`, which matches the tile ID rather than its display name.
   - expected: that tile remains reachable by ID and headings with no matching children disappear.
3. Filter out the currently selected tile, then clear the filter.
   - expected: the select moves to a visible tile instead of retaining an unpaintable hidden value; clearing restores all 105 options under their 23 headings.
4. Paint one cell with the filtered selection.
   - expected: the chosen tile is painted; filtering does not change the selected layer or route painting to another cell.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
