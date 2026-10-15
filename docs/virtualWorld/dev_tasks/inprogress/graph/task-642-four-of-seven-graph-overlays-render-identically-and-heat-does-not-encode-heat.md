---
type: task
status: inprogress
area: graph
priority: medium
---

# task-642: Four of seven graph overlays render identically, and Heat does not encode heat

**Filed:** 2026-09-30
**Related:** 

## What

Overlay modes for heat, sound, inhabited, way-direction and light produce indistinguishable output, so the overlay choice is meaningless for four of seven.

## Acceptance

- TODO

**Operator verification (2026-10-10) — reopened, in progress.** The overlay modes still need work: they are not distinct enough to be meaningful, and Heat does not encode a heat value.

## Why

TODO

## How

TODO

## Browser UI and intended live verification

Intended UI home: Graph editor → overlay selector and graph canvas.

Current availability: Overlay choices remain insufficiently distinct; Heat does not yet encode the measured heat value.

Live steps when available:

1. Select each overlay mode in the graph toolbar and inspect the same scenario and scope.
   - expected: Each overlay communicates its named data distinctly; Heat varies with underlying heat values.

2. Change one source value in a scratch scenario and refresh the overlay.
   - expected: The corresponding visual encoding changes without altering unrelated overlays.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO
