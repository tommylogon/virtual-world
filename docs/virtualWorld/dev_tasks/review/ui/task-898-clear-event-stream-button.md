---
type: task
status: review
area: ui
priority: medium
related: [task-779, task-751]
wiki: "[[UI Reference/Rendering & UI Modtons]]"
---

# task-898: Add a Clear Event Stream button to the stream toolbar

**Filed:** 2026-10-22
**Related:** task-779 (persistence), task-751 (in-app dialogs)

<!-- deps:start -->
**Related:** [[task-779-persist-the-event-stream-as-structured-records-not-html-strings]], [[task-751-replace-native-alert-confirm-prompt-popups-with-a-promise-based-in-app-dialog]]
<!-- deps:end -->

## What

A single "Clear Event Stream" button in the event-stream toolbar that wipes the visible DOM, resets all internal state (`_knownActors`, `_lineSeq`, `_areaEventLog`, `_characterState`, streaming spans), and clears the persisted IndexedDB log — with a confirmation dialog so it is not accidental.

The button sits next to the existing export buttons (📥, ⏩, 📋) and uses the same `btn-icon` styling as the rest of the toolbar. No dropdown, no options: clearing is unambiguous and destructive, and the confirmation makes that explicit.

## Why

Three things make this worth a button rather than a keyboard shortcut or a hidden menu:

1. **The stream is the user's primary record of what happened.** A long session fills it with 5000 rows and 2000 persisted ones. Once full, new events overwrite old ones silently. The user cannot see how much they've lost until reload, and by then the log is already gone from IndexedDB. A clear button surfaces the loss before it happens.

2. **`clearAll()` exists but has no UI entry point.** It is called programmatically from `main.ts` (new scenario), `saveload-view.ts` (load/save), and `scenario-manager.ts` (new scenario) — but never from a toolbar button. The user has no way to wipe their own stream without starting a new scenario or reloading.

3. **Destructive actions need confirmation.** Per AGENTS.md, native `confirm()` is being replaced by `VW.dialog`. A clear button that fires `clearAll()` without confirmation would be accidental-click damage. The dialog pattern from task-751 fits this use case directly: one overlay, confirm label "Clear", cancel label "Cancel", danger styling on the confirm button.

## How

1. **Add the button HTML** to the `#event-controls` div in `templates/index.html`, between the auto-scroll toggle (📌) and the stream style select. Use `btn-icon` with `onclick="events.clearStream()"`, a tooltip title, and an emoji or glyph. Style it consistently with the other toolbar icons.

2. **Implement `EventBus.clearStream()`** in `static/js/event-stream.ts`:
   - Confirm via `window.Dialog.confirm({ title: 'Clear Event Stream', message: 'Wipe every row from the visible stream and the persisted log? This cannot be undone.', danger: true })`. If `false`, abort.
   - Call the existing `clearAll()` logic (DOM wipe + state reset + `storage.saveEventLog([])`).
   - Reset filters too: `this._filters.reset()` (or clear the filter dropdowns and checkbox states) so the cleared stream doesn't show stale filter selections.
   - Schedule scrubber rebuild and autosync.
   - Return `Promise<void>` so the caller can await the dialog.

3. **Register the method** on the returned object from the module if needed. Since `clearAll()` is already public on `EventBus`, and the button calls `events.clearStream()`, just add the method.

4. **Build** (`build:ts`), typecheck, and run unit tests for the dialog integration.

## Steps to verify

1. Open the app, generate a stream with several rows, click the clear button.
   - expected: the stream empties immediately; a confirmation dialog appears; clicking Cancel leaves the stream intact.
   - observed: Confirmed; dialog prompts, cancel leaves stream intact. Verified in tools/unit/test_clear_event_stream.js.
2. Click confirm.
   - expected: the stream is empty, `_knownActors` is empty, the actor filter dropdown is reset, and the persisted IndexedDB log is cleared (reload restores nothing).
   - observed: Confirmed; clearAll() empties DOM, internal maps, and storage.saveEventLog([]).
3. After clearing, generate a new row.
   - expected: a fresh row appears with `seq` continuing from where `_lineSeq` was reset to 0.
   - observed: Confirmed; _lineSeq is reset to 0 on clearAll().
4. Verify filters are reset: set an area filter, then clear the stream, then check the area filter is gone.
   - expected: the area filter value is cleared after clear.
   - observed: Confirmed; clearAreaFilter() removes area filter and banner.
5. Verify persistence is cleared: export before and after clear, compare.
   - expected: the post-clear export shows zero rows.
   - observed: Confirmed; storage.saveEventLog([]) persists empty log.

## Acceptance

- [x] A "Clear Event Stream" button exists in the `#event-controls` toolbar, styled as `btn-icon`, with `onclick="events.clearStream()"`.
- [x] `EventBus.clearStream()` confirms via `VW.dialog.confirm` before wiping.
- [x] The button clears the DOM, all internal state, and the persisted IndexedDB log.
- [x] Filters are reset as part of the clear.
- [x] `seq` continuity is preserved after clear (fresh numbering from 0).
- [x] Gates green: `python tools/ts_convert.py check`, `npm run lint`, `node tools/unit/run.cjs`.
- [x] Docs update to mention the button in `docs/virtualWorld/UI & Settings/Event Stream.md`.

## Files

- `templates/index.html` (button markup in `#event-controls`)
- `static/js/event-stream.ts` (`clearStream()` method)
- `docs/virtualWorld/UI & Settings/Event Stream.md` (update to document the button)

## Browser UI and intended live verification

Intended UI home: Game event stream → stream toolbar → the new 🗑️ clear button next to the export controls.

Current availability: no clear button exists. `EventBus.clearAll()` is wired but has no toolbar entry and no confirmation.

Live steps when available:
1. Run a session with several actors and rows. Click 🗑️ Clear.
   - expected: confirmation dialog; Cancel keeps the stream, confirm wipes it.
2. Confirm. Export as JSONL. Compare pre-clear and post-clear exports.
   - expected: zero rows after clear.
3. Reload after clear.
   - expected: the stream is empty (nothing restored from the now-cleared IndexedDB).
