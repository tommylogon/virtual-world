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
surfacestill using native browser dialogs.

Current behavior in `static/js/ui/saveload-view.js`:

- **Rename** is `prompt()` (`doRenameSave`, line 413) — blocking, unstyled, and it
  cannot show validation (empty name, name already taken, filename stays for slot
  saves).
- **Load** confirms with `confirm('Load game "<filename>"? ...')` (line 492) even
  though the row shows a display name; the user is asked to approve a filename.
- **Delete** is `confirm()` (line 511).
- **Delete All** is two `confirm()`s (lines 525-526) — see bug-42 for the behavioral
  bug in the same code.
- The **autosave row** exposes ✏️ rename and 🗑 delete, but a rename of the autosave
  label is overwritten on the next autosave, and deleting the slot contradicts the
  "always current" promise (bug-42).

## Proposal

- Rename becomes an **in-place row edit** (click ✏️ → the title becomes an input;
  Enter commits, Escape cancels) — the top-bar scenario chip already does exactly
  this (`initScenarioNameEditor`), so reuse that interaction.
- Load/delete get a small in-modal confirmation (display name, timestamp, one line of
  stats), matching the import-preview pattern in `openImportPreview` (task-369).
- On the autosave row, keep **load** and the **overwrite** 💾; hide ✏️ and 🗑 (or make
  delete-autosave an explicit, separately-worded action if it should exist at all).
- Surface rename/delete failures via the existing toasts with the server's message.

## Acceptance

- [ ] No native `confirm()`/`prompt()` remains in the save/load flow.
- [ ] Renaming a save works from the row, is keyboard-cancellable, and reflects the
      server's returned filename/name.
- [ ] Loading and deleting confirm with the save's **display name** and timestamp, not
      the raw filename.
- [ ] The autosave row offers load + overwrite only; no rename/delete control that
      silently does not stick.
- [ ] Empty/duplicate rename input is rejected with a visible message.

## Files

- `static/js/ui/saveload-view.js` — `doRenameSave`, `doLoadGame`, `doDeleteSave`,
      `confirmDeleteAllSaves`, `loadGameList`
- `templates/index.html` — modal markup if new in-modal elements are added
- `static/css/style.css` — row/confirm styling

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

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO
