---
type: bug
status: done
area: ui
priority: high
---

# bug-511: Worldpainter: pressing space after selecting a biome opens the dropdown instead of panning the view

**Filed:** 2026-09-30
**Related:** 

## What

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

## Why

TODO

## How

TODO

## Steps to verify

1. Open WorldPainter, choose a biome from the value picker, hold Space over the
   canvas, then release it; inspect the active element and Konva stage's
   `draggable()` value.
   - expected: the picker blurs to `BODY`; Space sets `draggable()` true only
     while held, then returns it to false.
   - observed (2026-09-30): Playwright on localhost:4465 confirmed this after a
     biome pick.
2. Tab-focus the value or brush select and repeat the Space hold/release.
   - expected: the browser does not open the select; canvas panning still arms
     only while Space is held.
   - observed (2026-09-30): Playwright confirmed the Tab-focused case; source
     search found the Space-to-pan binding only in `editor.js`.

## Browser UI and intended live verification

Intended UI home: WorldPainter → biome value picker / brush picker → map canvas.

Current availability: The biome-pick and Tab-focused flows were live-checked
with Playwright on 2026-09-30. The task also records that no other fullscreen
tool binds Space to pan.

Live steps when available:
1. Choose a biome, hold Space over the Konva canvas, and release; read
   `document.activeElement` and `stage.draggable()` at each point.
   - expected: focus is `BODY` after selection; draggable is true while held
     and false after release.
2. Tab to the value picker, hold Space, and release; repeat for the brush picker.
   - expected: Space does not open either select and pans only during the hold.
3. Open each other fullscreen tool and repeat the Space hold over its canvas.
   - expected: no unrelated fullscreen tool has a Space-to-pan handler.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.

## Files

- TODO
