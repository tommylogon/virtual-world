---
type: task
status: review
area: refactor
priority: medium
wiki: "[[Feature Map]]"
---

# task-456: Split saveload-view concerns and extract the save-row template

**Filed:** 2026-09-22
**Related:** task-441, bug-40

## What

`static/js/ui/saveload-view.js` is 648 lines and mixes four unrelated concerns: savegame CRUD (`saveGame`, `saveGameToSlot`, `doRenameSave`, `loadGameList`, `doLoadGame`, `doDeleteSave`, `confirmDeleteAllSaves`); scenario import/export (`downloadWorld`, `uploadWorld`, `inspectImport`, `openImportPreview`, `saveScenarioToFile`, `persistScenarioName`, `initScenarioNameEditor`); world settings toggles (`toggleSpectator`, `updateTimePerTick`, `updateClockStart`, `restartScenario`) - which are not save/load at all; and the list template, a single large Lit expression with per-row inline styles and `window.SaveLoadView` global refs. Two concrete extractions: move the settings toggles to their own module (a world/settings view; `restartScenario` may belong with the world toolbar), and extract `renderSaveRow(save)` as a small sub-template returning a Lit template using CSS classes instead of the inline style string - the natural home for bug-40's badge fix and task-455's row interactions, so land those together. Follow the repo module conventions: keep the `@module`/`@contributes` header current (`python tools/js_module_index.py --write`), add the `<script>` tag in `templates/index.html` for any new module, and check `tools/unit/run.cjs`'s module list if portable logic is introduced.

## Acceptance

- [x] `saveload-view.js` contains only save/load concerns; spectator/time/clock
      moved out and still reachable from wherever they are rendered today.
- [x] `renderSaveRow` is a named function; the list render no longer builds badge/row
      markup as concatenated HTML strings.
- [x] Behavior is unchanged apart from the bug-40 badge fix: autosave pinned top,
      stats line, 💾/✏️/🗑 buttons.
- [x] `node tools/unit/run.cjs` passes, `npm run lint` passes, and
      `python tools/js_module_index.py --check` passes.
- [x] No new lines added to `templates/index.html` script list unless a new module was
      actually created.

## Files

- `static/js/ui/saveload-view.ts` - split and extracted `renderSaveRow`
- `static/js/ui/settings-view.ts` - extracted toggles
- `static/css/style.css` - `.save-game-item` row classes
- `tools/unit/test_saveload_view.js` - unit tests

## Steps to verify

1. Verify `renderSaveRow` is extracted and used in `saveload-view.ts`.
   - expected: `renderSaveRow` is a named function producing structured Lit template with CSS classes.
   - observed: Verified in `tools/unit/test_saveload_view.js` and `static/js/ui/saveload-view.ts:503-546`.
2. Verify settings toggles are housed in `settings-view.ts` and delegated in `saveload-view.ts`.
   - expected: `SettingsView` implements `toggleSpectator`, `updateTimePerTick`, `updateClockStart`.
   - observed: Verified in `tools/unit/test_saveload_view.js` and `static/js/ui/settings-view.ts`.
3. Run test suites and lint checks.
   - expected: `node tools/unit/run.cjs` passes, `python tools/js_module_index.py --check` passes.
   - observed: Passed cleanly.
