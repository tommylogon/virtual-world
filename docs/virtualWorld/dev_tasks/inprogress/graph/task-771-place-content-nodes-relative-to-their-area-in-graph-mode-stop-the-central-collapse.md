---
type: task
status: inprogress
area: graph
priority: high
---

# task-771: Place content nodes relative to their area in Graph mode (stop the central collapse)

**Filed:** 2026-10-10
**Related:** 

## What

In Graph mode the pinned areas sit on the map art, but the unpinned content nodes (items, triggers, characters, uncelled ways) have no home, so the solver pulls them into a central pile and every edge fans out to it (observed: 2763 nodes, 6340 edges). Place each content node in a ring/offset around its owning area the way Map mode already does (relative-layout offsetsPxFor), so the graph does not collapse and physics has almost nothing to do. Investigate whether relative-layout apply() runs in Graph mode or only Map.

## Why

TODO

## How

TODO

## Browser UI and intended live verification

Intended UI home: Graph editor → Graph mode with a multi-area painted scope.

Current availability: Content-node placement relative to owning areas is still open.

Live steps when available:

1. Open a painted scope in Graph mode and inspect characters, items, triggers, and uncelled ways around their areas.
   - expected: Content nodes form local groups rather than collapsing into a central pile.

2. Enable physics briefly and then disable it.
   - expected: The graph stays readable, edges remain local, and authored area positions stay fixed.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO

**Operator verification (2026-10-10) — reopened, in progress.** Reproduced: the **West Woods** items were pulled to the **centre** when Graph mode was pressed — they did not stay by their areas. So the ring/offset placement is still not running (or not holding) for content whose area is pinned away from the centre. Confirm whether `GraphRelativeLayout.apply()` runs in Graph mode and why West Woods' contents are not ringed to their area.
