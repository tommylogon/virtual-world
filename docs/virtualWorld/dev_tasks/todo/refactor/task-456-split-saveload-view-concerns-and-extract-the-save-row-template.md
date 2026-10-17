---
type: task
status: todo
area: refactor
priority: medium
---

# task-456: Split saveload-view concerns and extract the save-row template

**Filed:** 2026-09-22
**Related:** task-441, bug-40

## What

`static/js/ui/saveload-view.js` is 648 lines and mixes four unrelated concerns: savegame CRUD (`saveGame`, `saveGameToSlot`, `doRenameSave`, `loadGameList`, `doLoadGame`, `doDeleteSave`, `confirmDeleteAllSaves`); scenario import/export (`downloadWorld`, `uploadWorld`, `inspectImport`, `openImportPreview`, `saveScenarioToFile`, `persistScenarioName`, `initScenarioNameEditor`); world settings toggles (`toggleSpectator`, `updateTimePerTick`, `updateClockStart`, `restartScenario`) — which are not save/load at all; and the list template, a single large Lit expression with per-row inline styles and `window.SaveLoadView` global refs. Two concrete extractions: move the settings toggles to their own module (a world/settings view; `restartScenario` may belong with the world toolbar), and extract `renderSaveRow(save)` as a small sub-template returning a Lit template using CSS classes instead of the inline style string — the natural home for bug-40's badge fix and task-455's row interactions, so land those together. Follow the repo module conventions: keep the `@module`/`@contributes` header current (`python tools/js_module_index.py --write`), add the `<script>` tag in `templates/index.html` for any new module, and check `tools/unit/run.cjs`'s module list if portable logic is introduced.

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

`static/js/ui/saveload-view.js` is 648 lines and mixes four unrelated concerns, and the mix is the problem: savegame CRUD and scenario import/export belong together as save/load, but the world settings toggles (`toggleSpectator`, `updateTimePerTick`, `updateClockStart`, `restartScenario`) are not save/load at all, and the list template is a single large Lit expression with per-row inline styles and `window.SaveLoadView` global refs. Splitting by concern means the Save/Load modal stops being a grab-bag and the settings stop living inside the save module, so each surface has one owner and an agent editing one does not pull the whole 648-line file into context. The `renderSaveRow` extraction is the reusable bit: a small sub-template returning a Lit template using CSS classes instead of concatenated HTML strings, which is also the natural home for bug-40's badge fix and task-455's row interactions — land those together rather than as two more inline-style patches. Behaviour is unchanged apart from the bug-40 badge fix: autosave pinned top, stats line, 💾/✏️/🗑 buttons.

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

## Refactor discipline (applies to this task)

Applies to every refactor in this repo, per the 2026-10-16 card refresh:

1. **Dedup & reuse pass (mandatory).** While working, scan the touched concern and its
   neighbours for duplicate logic, parallel data homes, and near-identical helpers;
   consolidate onto one owner instead of copying. Prefer reusing an existing seam over
   creating a second one. Record any dedup decision in the move table / notes.
2. **Agent-experience & cleanliness (mandatory).** Name modules/files by concern (not
   by size), keep each under ~600 lines where the seam allows, add a one-line module
   docstring stating its owner and public surface, and ensure a fresh agent session can
   understand it without reading the host. No new abstraction unless an existing seam
   already represents the concept.
3. **No behaviour change unless the card says so.** Extraction and consolidation only;
   keep public imports/API stable and re-export moved members as thin delegates.
4. **One file/concern at a time**, verified with a targeted test selection (never the
   full suite by default, never -q).
