---
type: task
status: review
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

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO
