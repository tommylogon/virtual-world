---
type: task
status: todo
area: ui
priority: medium
---

# task-717: WorldPainter grid resize: numbered w/h fields are buried at the modal bottom while the promoted adjust affordance is imprecise drag handles

**Filed:** 2026-10-05
**Related:** 

## Goal

Make precise grid resize discoverable: the Grid... dialog (w/h/scale/Apply) verified working in both directions by real keyboard input (168x112 -> 120x80 -> 168x112, no confirm needed on an unpainted scope), but it renders as a small strip at the very bottom of a tall scrolling modal, far below the canvas and the Grid... button. The ✥ grid adjust mode (drag frame + E/S/SE handles) is the affordance an author finds first and cannot size precisely (verified live: status hint only says 'drag the frame to move the scope on the graph map, drag the E/S/SE handles to resize' — it never mentions the dialog). Fix options: surface the w/h fields in the adjust-mode HUD or near the canvas, or open the dialog directly from the grid-dims label (160x100 - 1 cell = 1 turn).

## Acceptance

- TODO
