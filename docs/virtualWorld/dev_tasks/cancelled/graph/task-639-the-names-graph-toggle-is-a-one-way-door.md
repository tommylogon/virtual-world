---
type: task
status: cancelled
area: graph
priority: medium
---

# task-639: The Names graph toggle is a one-way door

**Filed:** 2026-09-30
**Related:** 

## Goal

Turning the label toggle off does not restore the prior state.

## Acceptance

- TODO

## Cancellation

Cancelled 2026-09-30. The finding does not reproduce. Driving
``graphManager.toggleNodeLabels()`` and reading the canvas:

  _showNodeLabels / localStorage / aria-pressed

  initial  true  / "1" / true   -> node labels rendered
  toggle   false / "0" / false  -> nodes render as EMPTY rectangles
  toggle   true  / "1" / true   -> labels return

Bidirectional, with correct persistence and correct ARIA. The original "one-way
door" claim came from reading a static screenshot, and the button's own title
("Names auto-hide at overview zoom on a dense painted map") explains why labels
can be absent without anything being broken.

This is the fifth finding in the live audit retracted for the same reason --
judged without interacting with the surface. Recorded in the audit README's
method-limitation section.