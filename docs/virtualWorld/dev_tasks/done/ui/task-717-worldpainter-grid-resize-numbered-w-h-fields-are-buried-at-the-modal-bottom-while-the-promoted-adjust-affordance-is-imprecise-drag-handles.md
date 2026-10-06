---
type: task
status: done
area: ui
priority: medium
---

# task-717: WorldPainter grid resize: numbered w/h fields are buried at the modal bottom while the promoted adjust affordance is imprecise drag handles

**Filed:** 2026-10-05
**Related:** 

## Goal

Make precise grid resize discoverable: the Grid... dialog (w/h/scale/Apply) verified working in both directions by real keyboard input (168x112 -> 120x80 -> 168x112, no confirm needed on an unpainted scope), but it renders as a small strip at the very bottom of a tall scrolling modal, far below the canvas and the Grid... button. The ✥ grid adjust mode (drag frame + E/S/SE handles) is the affordance an author finds first and cannot size precisely (verified live: status hint only says 'drag the frame to move the scope on the graph map, drag the E/S/SE handles to resize' — it never mentions the dialog). Fix options: surface the w/h fields in the adjust-mode HUD or near the canvas, or open the dialog directly from the grid-dims label (160x100 - 1 cell = 1 turn).

## Acceptance

- Precise grid resize is reachable from the canvas, not only from a control
  buried at the modal bottom.
- The grid-adjust mode names the exact-size path instead of only the handles.

## Status (2026-10-06)

Already improved since filing (task-597, `bb015e65`, `3d1befed`): the `▦ Grid…`
button now sits in the tool row, and the adjust-mode handles got a live preview.
That addresses the pain but **not** the task's two named fixes, which were still
missing:

- the HUD dims readout `${w}×${h} · 1 cell = 1 turn` was inert text
  (`editor.ts:2029`), not clickable;
- the adjust-mode hint (`editor.ts:1568`) still said only "drag the frame /
  E/S/SE handles" and never mentioned the dialog.

Both are now done:

- the dims readout is a `_btn` that calls `_openGridDialog(p)` — the same dialog
  the toolbar uses — with the title "Set the exact grid size…". So the exact
  numbers are one click from the canvas HUD.
- the adjust-mode status now reads "…drag the E/S/SE handles to resize; click the
  size (or ▦ Grid…) to type exact numbers."

`build:ts` clean; unit runner **618 passed, 0 failed**.

**Live-confirmed 2026-10-06.** The adjust-mode hint shows in the modal
("…click the size (or ▦ Grid…) to type exact numbers") and the HUD size readout
opens the exact-size dialog. Built source: `editor.js:1651` (the `_btn`) and
`:1201` (the hint).

**Follow-up observation, not part of this task:** the WorldPainter modal is taller
than the viewport — the status line and Child scopes sit below the fold, so the
whole modal needs a browser zoom-out to see at once. That is the "tall modal"
context the task was filed around; the discoverability fix (size control at the
top of the canvas) does not depend on it, but the modal height is its own issue.
