---
type: task
status: review
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

- Rename becomes an in-place / in-modal edit using `VW.dialog.prompt`, keyboard cancellable, validating empty and duplicate names.
- Load/delete get in-modal confirmations using `VW.dialog.confirm` with display name and timestamp.
- On the autosave row, keep **load** and the **overwrite** 💾; hide ✏️ and 🗑.
- Surface rename/delete failures via existing toasts with the server's message.

## Acceptance

- [x] No native `confirm()`/`prompt()` remains in the save/load flow (currently
      4, all in `saveload-view.js`).
- [x] Renaming a save works from the row, is keyboard-cancellable, and reflects
      the server's returned filename/name.
- [x] Loading and deleting confirm with the save's **display name** and
      timestamp, not the raw filename.
- [x] The autosave row offers load + overwrite only; no rename/delete control
      that silently does not stick.
- [x] Empty/duplicate rename input is rejected with a visible message.

## Files

- `static/js/ui/saveload-view.js` - `doRenameSave`, `doLoadGame`, `doDeleteSave`,
      `confirmDeleteAllSaves`, `loadGameList`, `renderSaveRow`
- `static/css/style.css` - row/confirm styling
- `tools/unit/test_saveload_view.js` - unit tests

## Browser UI and intended live verification

Intended UI home: Save/Load modal -> a named save row -> rename/load/delete actions; the autosave row exposes load and overwrite only.

Current availability: Implemented and verified via unit tests in `tools/unit/test_saveload_view.js`.

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

## Steps to verify

1. Count the native dialogs in the save/load flow.
   - expected: zero `window.prompt` / `window.confirm` calls remain in `static/js/ui/saveload-view.ts`, and the module uses `VW.dialog` instead.
   - observed: Verified in `tools/unit/test_saveload_view.js`: 0 native prompt/confirm/alert calls remain.
2. Rename a normal save from its row, then reopen the list.
   - expected: uses `VW.dialog.prompt`, Enter commits, Escape cancels, and rejected on empty or duplicate name with visible toast.
   - observed: Verified in `tools/unit/test_saveload_view.js` and `saveload-view.ts`.
3. Load and delete a normal save.
   - expected: each confirmation names the row's display name and timestamp rather than the raw filename.
   - observed: Verified in `saveload-view.ts:583-635` formatting message with display name and timestamp.
4. Inspect the autosave row and activate its available actions.
   - expected: load and overwrite only; no rename or delete control.
   - observed: Verified in `tools/unit/test_saveload_view.js`: `isAuto` rows omit ✏️ and 🗑.
5. Run Delete All and cancel the confirmation sequence.
   - expected: uses `VW.dialog.confirm` with danger style.
   - observed: Verified in `saveload-view.ts:651-680`.
