---
type: task
status: review
area: ui
priority: medium
---

# task-597: Worldpainter: better grid preview, with drag to move and handles to resize

**Filed:** 2026-09-30
**Related:** 

## Goal

The grid overlay does not communicate its extent or origin clearly, and moving or resizing it means editing numbers by hand. Show a clearer preview of the grid's bounds relative to the painted cells, and let it be dragged to reposition and resized by edge/corner handles rather than only through a dialog.

## Acceptance

- [x] The grid's **extent and origin** are always visible: a bold frame, a marker
      at cell (0,0) labelled `0,0 · W×H`, and a shaded/dashed box around the
      painted content so "how much of this grid is used" is readable at a glance.
- [x] `✥ grid` adjust mode puts E/S/SE handles on the frame. Dragging a handle
      resizes the grid, snapped to whole cells, with the prune count confirmed
      before anything is lost; dragging the frame sets the scope's **map offset**
      (task-523) so the scope can be repositioned without typing numbers.
- [x] The origin is fixed, so only the far edges/corner offer handles — the near
      edges are absent rather than present-and-broken.
- [x] Pure geometry is unit-tested:
      `paintedBounds frames everything the author put on the grid` and
      `grid resize handles snap to whole cells and never vanish`.
- [x] Live proof (Playwright, `localhost:4465`): screenshot shows the frame,
      origin label, and handles; dragging the SE handle produced
      `Grid resized to 44×29`.
