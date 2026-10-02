---
type: bug
status: review
area: ui
priority: high
---

# bug-511: Worldpainter: pressing space after selecting a biome opens the dropdown instead of panning the view

**Filed:** 2026-09-30
**Related:** 

## Goal

In the fullscreen worldpainter, choosing a biome from the dropdown leaves the control focused, so the next space press is consumed as 'open the focused dropdown' rather than panning the view. Find where the key handler should suppress the browser default for space and blur the dropdown after a selection, and confirm the same bug does not exist in the other fullscreen tools.

## Acceptance

- [x] The value/brush `<select>` blurs on change, so the next Space reaches the
      pan handler (`document.activeElement` is BODY after a pick).
- [x] The key handler suppresses the browser default for Space while a toolbar
      `<select>` has focus, so panning still arms even for a select reached by Tab.
- [x] Live proof (Playwright, `localhost:4465`): hold Space after picking a biome
      → Konva stage `draggable()` is `true`; released → `false`; same with the
      select focused by Tab.
- [x] No other fullscreen tool binds Space-to-pan — `rg "code === 'Space'"` finds
      only `static/js/worldpainter/editor.js`.

## Notes

The key handler is `state._keyDown` in `static/js/worldpainter/editor.js`; the
blur is in `_valueControl` (value picker) and the brush select's change handler.
