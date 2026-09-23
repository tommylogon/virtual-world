---
type: task
status: todo
area: ui
priority: medium
---

# task-455: Save-load dialog UX: in-modal rename and confirms, autosave row actions

**Filed:** 2026-09-22
**Related:** task-369, bug-40, bug-42

## Goal

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
