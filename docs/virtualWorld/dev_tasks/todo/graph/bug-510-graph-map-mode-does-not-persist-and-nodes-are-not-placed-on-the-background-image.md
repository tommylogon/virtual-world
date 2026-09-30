---
type: bug
status: todo
area: graph
priority: high
---

# bug-510: Graph map mode does not persist, and nodes are not placed on the background image

**Filed:** 2026-09-30
**Related:** 

## Goal

Two defects in one area. (1) Selecting map mode for the graph does not save - the choice is lost on reload or re-render. (2) Nodes are not correctly placed or spaced relative to the background image, so they must be nudged by hand every time the map is loaded. Determine whether the placement is a stored coordinate that is being lost, a projection/scale mismatch between node coordinates and image pixels, or a layout pass that is not reading the map's coordinate space at all.

## Acceptance

- TODO
