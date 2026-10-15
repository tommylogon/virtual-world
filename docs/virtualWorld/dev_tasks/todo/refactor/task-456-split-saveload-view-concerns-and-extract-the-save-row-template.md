---
type: task
status: todo
area: refactor
priority: low
---

# task-456: Split saveload-view concerns and extract the save-row template

**Filed:** 2026-09-22
**Related:** task-441, bug-40

## What

`static/js/ui/saveload-view.js` is 648 lines and mixes four unrelated concerns:

1. **Savegame CRUD** — `saveGame`, `saveGameToSlot`, `doRenameSave`,
   `loadGameList`, `doLoadGame`, `doDeleteSave`, `confirmDeleteAllSaves`.
2. **Scenario import/export** — `downloadWorld`, `uploadWorld`, `inspectImport`,
   `openImportPreview`, `saveScenarioToFile`, `persistScenarioName`,
   `initScenarioNameEditor`.
3. **World settings toggles** — `toggleSpectator`, `updateTimePerTick`,
   `updateClockStart`, `restartScenario` — these are not save/load at all.
4. **The list template** — a single large Lit expression with per-row inline styles
   and `window.SaveLoadView` global refs.

Two concrete extractions:

- Move the settings toggles (3) to their own module (e.g. a world/settings view).
  `restartScenario` may belong with the world toolbar rather than either.
- Extract `renderSaveRow(save)` as a small sub-template returning a Lit template,
  using CSS classes instead of the inline style string. This is also the natural home
  for bug-40's badge fix and for task-455's row interactions, so land those together
  if the timing allows.

Follow the repo module conventions: keep the `@module`/`@contributes` header current
(`python tools/js_module_index.py --write`), add the `<script>` tag in
`templates/index.html` for any new module, and check `tools/unit/run.cjs`'s module list
if portable logic is introduced.

## Acceptance

- [ ] `saveload-view.js` contains only save/load concerns; spectator/time/clock
      moved out and still reachable from wherever they are rendered today.
- [ ] `renderSaveRow` is a named function; the list render no longer builds badge/row
      markup as concatenated HTML strings.
- [ ] Behavior is unchanged apart from the bug-40 badge fix: autosave pinned top,
      stats line, 💾/✏️/🗑 buttons.
- [ ] `node tools/unit/run.cjs` passes, `npm run lint` passes, and
      `python tools/js_module_index.py --check` passes.
- [ ] No new lines added to `templates/index.html` script list unless a new module was
      actually created.

## Files

- `static/js/ui/saveload-view.js` — split
- `static/js/ui/<new settings view>.js` — extracted toggles
- `templates/index.html` — script tags
- `static/css/style.css` — `.save-game-item` row classes

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Browser UI and intended live verification

Intended UI home: Game menu → Save/Load modal; Scenario Manager import/export controls; Settings controls for spectator/time/clock. Each existing control must remain reachable after the module split.

Current availability: the card identifies the current mixed `saveload-view.js` responsibilities and requires behavior preservation except for bug-40 badges. The code extraction is planned; no changed UI architecture is claimed.

Live steps when available:
1. Open Save/Load and inspect the autosave, one named save, and one malformed save row; click the save, rename, and delete controls on scratch data.
   - expected: autosave stays pinned, stats render, and 💾/✏️/🗑 actions keep their current behavior; badges render as badges rather than literal HTML.
2. Use Scenario Manager to import a scenario and inspect its preview before saving.
   - expected: upload, preview, and save remain reachable and do not appear as save-row actions.
3. Open Settings and toggle spectator mode and change time-per-tick/clock start.
   - expected: these settings remain reachable in their existing location after moving out of the Save/Load module.
4. Reopen Save/Load after each operation and inspect the modal for duplicate controls or a missing script entry.
   - expected: one save list is rendered through `renderSaveRow`; no `templates/index.html` script entry is added unless a new module requires it.

This section is not a claim that the refactor is complete or live-verified today.
