---
type: task
status: done
area: ui
priority: medium
---

# task-647: WorldPainter cell palette: no search or filter across 105 tiles

**Filed:** 2026-09-30
**Related:** 

## Goal

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
