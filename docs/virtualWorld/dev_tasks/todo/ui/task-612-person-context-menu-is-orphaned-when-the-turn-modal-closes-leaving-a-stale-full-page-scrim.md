---
type: task
status: todo
area: ui
priority: medium
---

# task-612: Person context menu is orphaned when the turn modal closes, leaving a stale full-page scrim

**Filed:** 2026-09-30
**Related:** 

## What

Open a person menu in the HTC modal, then dismiss the modal. The THE WOMAN / Talk to / Examine / Attack panel stays rendered with no owner, and a transient .tsv-scrim (z-index 1390, position fixed, pointer-events auto, full viewport) swallows the next click before clearing. Symptom is a one-click tax or a double-click-to-act, not a lockout.

## Acceptance

- TODO

## Browser UI and intended live verification

Intended UI home: Human Turn Composer/HTC modal → click a person in the scene → that person's context menu. The turn modal's close action must also close the person menu and its scrim.

Current availability: The card records the orphaned “THE WOMAN / Talk to / Examine / Attack” menu and a one-click scrim tax as the reported symptom; no fix or live recheck is recorded.

Live steps when available:
1. Open the human-turn modal, click a person, and confirm the context menu shows that person's name and actions.
   - expected: the menu is attached to the selected person and the modal remains interactive.
2. Close the turn modal using its close control, then click a different visible world control once.
   - expected: both the context menu and full-page `.tsv-scrim` are gone; the first click reaches the intended control.
3. Repeat by dismissing the modal with Escape and by clicking its backdrop.
   - expected: each dismissal removes the same menu and scrim without leaving a stale pointer-blocking layer.
4. Reopen the modal and open a second person's menu.
   - expected: only the second person's menu remains; the first person's actions are not retained.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## REOPENED 2026-10-04 — reproduced live; the shipped fix is dead code

Was `done` (folder). Moved back to `todo` after a clean browser repro on the
mansion scenario (read-only session, own client tab):

1. Zero `.tsv-scrim` elements (counted). Reopen the composer, click the kayla
   jenkins person chip → body gains exactly `DIV.tsv-scrim` + `DIV.tsv-ctx`.
2. One Escape keydown (the overlay-dismiss path). The modal closes.
3. Counted after: `.tsv-scrim` = 1 and `.tsv-ctx` = 1, both visible. The scrim
   is full-viewport (1280×720), z-index 1390, `pointer-events: auto`, and
   `document.elementFromPoint` at viewport centre returns the scrim — the next
   click is swallowed, then the scrim's own click handler clears it. The exact
   "one-click tax" from the original goal.

Root cause — the fix at `human-turn-composer.ts:679` (`hidePanel`) guards with
`typeof _scene.closeMenu === 'function'`, but `_scene` is the **scene data
payload** assigned at `human-turn-composer.ts:727` (`_scene = scene` from
`TurnSceneView.fetch`). A JSON payload has no `closeMenu`; the method is on the
**TurnSceneView module export** (`turn-scene-view.ts:602`). The guard can never
pass, so `closeMenu()` never runs from `hidePanel()` on ANY close path. This is
guard check #4 ("can the guard's lookup ever match what the caller passes?").

Fix direction: call the module (`TurnSceneView.closeMenu()`), not the payload.
Also add the regression test this task never had (its acceptance was left
TODO when it was marked done): open a person menu, hide the panel, assert
`document.querySelector('.tsv-scrim')` is null.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO
