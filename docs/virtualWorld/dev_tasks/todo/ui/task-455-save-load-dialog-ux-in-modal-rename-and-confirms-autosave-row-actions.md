---
type: task
status: todo
area: ui
priority: medium
wiki: "[[UI & Settings/Settings & Configuration]]"
blocked_by: [task-751]
---

# task-455: Save-load dialog UX: in-modal rename and confirms, autosave row actions

**Filed:** 2026-09-22
**Related:** task-369, bug-40, bug-42

<!-- deps:start -->
**Blocked by:** [[task-751-replace-native-alert-confirm-prompt-popups-with-a-promise-based-in-app-dialog]]
<!-- deps:end -->
## What

Bring the Save / Load modal in line with the rest of the UI: it is the last major
surface still using native browser dialogs.

Current behavior in `static/js/ui/saveload-view.js` (measured 2026-10-20: **737
lines**, up from the 648 the card originally cited):

- **Rename** is `prompt()` (`doRenameSave`, line 451) - blocking, unstyled, and it
  cannot show validation (empty name, name already taken, filename stays for slot
  saves).
- **Load** confirms with `confirm('Load game "<filename>"? ...')` (line 546) even
  though the row shows a display name; the user is asked to approve a filename.
- **Delete** is `confirm()` (line 575).
- **Delete All** is two `confirm()`s (line 608) - see bug-42 for the behavioral
  bug in the same code.
- The **autosave row** exposes ✏️ rename and 🗑 delete (buttons at lines 497 and
  498), but a rename of the autosave label is overwritten on the next autosave,
  and deleting the slot contradicts the "always current" promise (bug-42).

Measured count of native dialogs in the save/load flow: **4** (`window.prompt`
x1 at line 451, `window.confirm` x3 at lines 546, 575, 608). A scan of
`static/js/ui/*.js` for `window.confirm|window.prompt|confirm(|prompt(` returns
only those four; `static/js/ui/saveload-view.js` is the sole file carrying them.

## Proposal

- Rename becomes an **in-place row edit** (click ✏️ → the title becomes an input;
  Enter commits, Escape cancels) - the top-bar scenario chip already does exactly
  this (`initScenarioNameEditor` at `saveload-view.js:36`), so reuse that
  interaction.
- Load/delete get a small in-modal confirmation (display name, timestamp, one
  line of stats), matching the import-preview pattern in `openImportPreview`
  (task-369).
- On the autosave row, keep **load** and the **overwrite** 💾; hide ✏️ and 🗑 (or
  make delete-autosave an explicit, separately-worded action if it should exist at
  all).
- Surface rename/delete failures via the existing toasts with the server's
  message.

## Acceptance

- [ ] No native `confirm()`/`prompt()` remains in the save/load flow (currently
      4, all in `saveload-view.js`).
- [ ] Renaming a save works from the row, is keyboard-cancellable, and reflects
      the server's returned filename/name.
- [ ] Loading and deleting confirm with the save's **display name** and
      timestamp, not the raw filename.
- [ ] The autosave row offers load + overwrite only; no rename/delete control
      that silently does not stick.
- [ ] Empty/duplicate rename input is rejected with a visible message.
## Files

- `static/js/ui/saveload-view.js` - `doRenameSave`, `doLoadGame`, `doDeleteSave`,
      `confirmDeleteAllSaves`, `loadGameList`
- `templates/index.html` - modal markup if new in-modal elements are added
- `static/css/style.css` - row/confirm styling

## Browser UI and intended live verification

Intended UI home: Save/Load modal → a named save row → rename/load/delete actions; the autosave row exposes load and overwrite only.

Current availability: The card records native `prompt()`/`confirm()` behavior in `saveload-view.js`; the in-modal replacement controls are planned and not claimed as available.

Live steps when available:
1. Open Save/Load, rename a normal save to a unique display name, then reopen the list.
   - expected: an in-modal text field accepts the new name, Enter saves it, Escape cancels, and the refreshed row shows the server-returned display name/filename.
2. Try an empty name and a name already used by another save.
   - expected: both are rejected with a visible message and the existing save rows are unchanged.
3. Choose Load and Delete on a normal save.
   - expected: each confirmation names the row's display name and timestamp, not its raw filename; cancelling leaves the save untouched.
4. Inspect the autosave row and activate its available actions.
   - expected: it offers load and overwrite, with no rename/delete action that would be lost on the next autosave.
5. Run Delete All and cancel the confirmation sequence.
   - expected: cancellation preserves the autosave slot and every other save.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Why

The Save/Load modal is the last major surface in the app still driving the
browser's native dialogs, and native `prompt()`/`confirm()` are the wrong tool
for the three things this flow does: they cannot show validation (an empty
name, a name already taken, a slot save whose filename must not change), they
put a raw filename in front of the user when the row already carries a
display name and a timestamp, and they block the whole page while they are
up. The in-app dialog module this card waits on already exists and is
already used elsewhere in the app, so what is left is adoption in one file
rather than a new platform, which is why `blocked_by: [task-751]` is still
accurate even though the module itself has shipped. The autosave row is a
separate problem: it offers rename and delete for a slot that the next
autosave overwrites and that the "always current" promise says should always
be there, so those two buttons promise something they cannot deliver.

## How

1. **Adopt the existing dialog module.** `static/js/shared/dialog.ts`
   publishes `Dialog.alert` (`:101`), `Dialog.confirm` (`:112`) and
   `Dialog.prompt` (`:126`) as `window.Dialog`, and `static/js/main.ts:86`
   republishes it as `VW.dialog`. `static/js/ui/timeskip.ts:252-256` already
   prefers `VW.dialog` over a native `window.prompt`; use the same shape
   here, including the `danger` option for the destructive confirms.
2. **Rename in place, reusing the pattern already in this file.**
   `initScenarioNameEditor` (`static/js/ui/saveload-view.ts:40`) is the
   model the card names: click the title, it becomes an input, Enter commits,
   Escape cancels. `doRenameSave` (`:429`) is the native `prompt()` today
   (`:430`). Route the row's ✏️ through the same in-place editor and show the
   server's returned filename and name - the rename path already logs the
   server's result (`:437`).
3. **Confirm with the display name and timestamp, not the filename.**
   `doLoadGame` (`:511`, native `confirm` at `:512`) and `doDeleteSave`
   (`:537`, confirm at `:538`) both confirm with a raw `filename`; the row
   already carries a display name and a timestamp, so the confirmation body
   should quote those plus one line of stats, following the import-preview
   pattern in `openImportPreview` (`:224`). `confirmDeleteAllSaves` (`:555`,
   confirm at `:569`) keeps its wording about keeping the autosave but loses
   the native dialog.
4. **Narrow the autosave row.** The row template emits 💾 / ✏️ / 🗑 for
   every row (`static/js/ui/saveload-view.ts:496-498`); for the autosave
   entry emit load and overwrite only, so the row never offers a control
   that the next autosave would silently undo.
5. **Validate the rename.** Reject an empty name and a name already used by
   another save with a visible message, using the existing toast helpers
   (`saveload-view.ts:27-33`) and the server's own message rather than a
   silent no-op.
6. **Do not build a second modal.** The shared dialog module is the
   mechanism; the import-preview panel is the styling reference. No new
   modal surface is needed for this card.

## Reconnaissance (2026-10-20) - VERDICT: PARTI_DONE

**What landed.** `static/js/shared/dialog.ts` exists and is the promise-based
in-app dialog task-751 asks for: `Dialog.alert`, `Dialog.confirm`,
`Dialog.prompt`, published as `window.VW.dialog`. It is loaded and used by
`static/js/ui/timeskip.ts:255-261` (which explicitly prefers `VW.dialog` over a
native `window.prompt`), and `static/js/shared/trigger-graph.ts:2142` reads
`window.Dialog` for a prompt. So the *platform* task-751 needed is done even
though task-751 itself is still filed `todo`.

**What did not land.** The save/load flow is untouched. Measured 2026-10-20:
`static/js/ui/saveload-view.js` is 737 lines (the card originally cited 648) and
still contains all four native dialogs at lines 451, 546, 575, 608. It does not
call `VW.dialog` or `Dialog.confirm`/`Dialog.prompt` at all (zero hits). The
card's `blocked_by: [task-751]` frontmatter is therefore still accurate in
effect: the dependency is the *adoption* of the existing dialog module in this
flow, not the module's existence.

**Line-number drift corrected in place.** The card's original line references
(413, 492, 511, 525-526) are stale; the live lines are 451, 546, 575, 608, and
the autosave ✏️/🗑 buttons are at 497/498. The `renderSaveRow` extraction this
card's sibling task-456 wants has also not happened: the list is still one big
inline `saveLoadViewTag` expression (lines 480-539) with per-row inline styles,
and there is no named `renderSaveRow` function anywhere in `static/js/`.

**What is still in scope.** The rename/delete UX, the autosave-row action
narrowing, and the display-name confirmations. The `initScenarioNameEditor`
in-place-edit pattern the card proposes already exists at
`saveload-view.js:36-73` and is the right model to reuse; nothing newer has
replaced it.

The card stays in `todo`.

## Steps to verify

1. Count the native dialogs in the save/load flow.
   - expected: zero `window.prompt` / `window.confirm` calls remain in
     `static/js/ui/saveload-view.ts`, and the module uses `VW.dialog` instead.
   - observed: not run. Measured 2026-10-20: 4 native dialogs remain - a
     `prompt()` at `saveload-view.ts:430` and `confirm()` calls at `:512`,
     `:538` and `:569` (emitted `.js` lines 451, 546, 575, 608). A scan of
     `static/js/ui/*.js` for the same pattern returns only those four, and
     `saveload-view.ts` has zero hits for `VW.dialog` or `Dialog.`.
2. Rename a normal save from its row, then reopen the list.
   - expected: the title becomes an input, Enter commits, Escape cancels, and
     the refreshed row shows the server-returned name and filename; an empty
     or duplicate name is rejected with a visible message and the rows are
     unchanged.
   - observed: not run live. Measured 2026-10-20: the row still calls
     `doRenameSave` (`:429`), which opens a native `prompt()` (`:430`).
3. Load and delete a normal save.
   - expected: each confirmation names the row's display name and timestamp
     rather than the raw filename, and cancelling leaves the save untouched.
   - observed: not run live. Measured 2026-10-20: both still confirm with
     `filename` (`:512`, `:538`).
4. Inspect the autosave row and activate its available actions.
   - expected: load and overwrite only; no rename or delete control that
     would be lost on the next autosave.
   - observed: not run live. Measured 2026-10-20: the row template emits 💾 /
     ✏️ / 🗑 for every row including the autosave (`:496-498`).
5. Run Delete All and cancel the confirmation sequence.
   - expected: cancellation preserves the autosave slot and every other save.
   - observed: not run live. Measured 2026-10-20: the sequence is still a
     native `confirm()` (`:569`), and bug-42's behavioural bug in that same
     code path is still open, so the autosave-preservation promise is not
     yet demonstrated by this code.
