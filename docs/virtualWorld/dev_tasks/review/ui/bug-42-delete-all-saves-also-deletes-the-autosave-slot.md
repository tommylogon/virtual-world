---
type: bug
status: review
area: ui
priority: medium
---

# bug-42: Delete All saves also deletes the autosave slot

**Filed:** 2026-09-22
**Related:** task-365

## Symptom

The modal tells the user "🔄 Autosave is always current (pinned top)". The **🗑 All**
button contradicts that: after two confirms it deletes **every** file in `saves/`,
including `autosave.json`. The safety net the messaging promises is gone, and there is
no undo.

Two smaller problems in the same path:

- It issues one `DELETE /api/save-game/<filename>` per save — an N+1 round trip that
  also re-lists on each failure and can stop half-way, leaving a partial wipe.
- The double `confirm()` cannot be cancelled differentially (no "keep autosave"
  option), and deleting the autosave slot is not surfaced as its own choice.

## Root cause

`confirmDeleteAllSaves` (`static/js/ui/saveload-view.js:524-537`) lists all saves and
loops `api.deleteSaveGame(saves[i].filename)` with no exclusion for
`save.autosave === true`.

## Fix

1. Exclude the autosave slot from Delete All (`saves.filter(s => !s.autosave)`), and
   make that explicit in the confirm text ("Delete all N saves? Autosave is kept.").
2. Add a single bulk endpoint (e.g. `POST /api/save-games/delete-all` with an
   `include_autosave` flag) so the wipe is one request and can't half-complete.
3. Deleting the autosave specifically, if it should be possible at all, belongs on the
   autosave row itself (see task-455), not in the global wipe.

## Acceptance

- [ ] Delete All removes user saves but leaves `saves/autosave.json` in place and
      visible after the list refreshes.
- [ ] The confirm text states the count and that autosave is kept.
- [ ] A bulk delete is a single request; a mid-way failure does not leave a silently
      partial wipe.
- [ ] Cancelling either confirm deletes nothing.

## Files

- `static/js/ui/saveload-view.js` — `confirmDeleteAllSaves` (524-537)
- `routes/saveload.py` — save-game routes (new bulk endpoint)
- `static/js/api.js` — client method for the bulk endpoint
- `tests/test_saveload.py` — bulk-delete + autosave-retention coverage

## Fix — 2026-09-24

- **`routes/saveload.py`** — new `POST /api/save-games/delete-all` with an
  `include_autosave` flag (default false). It deletes every `.json` in the saves
  dir in one pass, keeping `autosave.json` unless explicitly asked; a mid-way
  `OSError` returns an error listing what was deleted, so the wipe is never
  silently partial.
- **`static/js/api.js`** — `deleteAllSaveGames(includeAutosave = false)`.
- **`static/js/ui/saveload-view.js`** — `confirmDeleteAllSaves` now lists saves,
  filters out the autosave row, states the count and that autosave is kept, and
  makes a single bulk request (one confirm, not a non-differential double
  confirm). An empty user-save set is a no-op with a toast.
- **Tests** — `tests/test_saveload.py::TestDeleteAllSaves` (4): autosave kept and
  listed in `kept`; `include_autosave: true` removes it; non-JSON files are
  ignored; no saves is a no-op. `pytest tests/test_saveload.py` → 14 passed.
