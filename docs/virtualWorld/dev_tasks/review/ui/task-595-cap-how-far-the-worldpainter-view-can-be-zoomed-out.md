---
type: task
status: review
area: ui
priority: low
---

# task-595: Cap how far the worldpainter view can be zoomed out

**Filed:** 2026-09-30
**Related:** 

## Goal

Zoom-out currently has no floor, so the view can be reduced to an unusable state. Clamp the minimum zoom to a level where the painted grid and at least one biome remain legible, and show a disabled zoom control (or snap back) rather than letting the user reach the clamp.

## Acceptance

- [x] The zoom floor is a legibility floor: `MIN_SCALE = 0.25` (a cell stays
      5.5px, so the lattice `_drawGridLines` still draws; the old 0.12 put a cell
      under 3px and dissolved the grid into paint blobs).
- [x] The `−` control disables at the floor rather than silently doing nothing.
- [x] Every zoom path clamps (`_zoomBy`, wheel handler, `_fitGrid`) and calls
      `_syncZoomButtons()`.
- [x] Live proof (Playwright, `localhost:4465`): 30 clicks on `−` →
      `stage.scaleX() === 0.25`, `−` `disabled === true`, screenshot legible.

## Notes

The floor existed at 0.12; the ticket's "no floor" premise was stale, but the
floor was not legible and the control never reflected it. Both are now true.
