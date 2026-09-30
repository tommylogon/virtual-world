---
type: bug
status: todo
area: ui
priority: high
---

# bug-511: Worldpainter: pressing space after selecting a biome opens the dropdown instead of panning the view

**Filed:** 2026-09-30
**Related:** 

## Goal

In the fullscreen worldpainter, choosing a biome from the dropdown leaves the control focused, so the next space press is consumed as 'open the focused dropdown' rather than panning the view. Find where the key handler should suppress the browser default for space and blur the dropdown after a selection, and confirm the same bug does not exist in the other fullscreen tools.

## Acceptance

- TODO
