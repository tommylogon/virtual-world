---
type: task
status: todo
area: refactor
priority: medium
wiki: "[[Feature Map]]"
---

# task-456: Split saveload-view concerns and extract the save-row template

**Filed:** 2026-09-22
**Related:** task-441, bug-40

## What

`static/js/ui/saveload-view.js` is 648 lines and mixes four unrelated concerns: savegame CRUD (`saveGame`, `saveGameToSlot`, `doRenameSave`, `loadGameList`, `doLoadGame`, `doDeleteSave`, `confirmDeleteAllSaves`); scenario import/export (`downloadWorld`, `uploadWorld`, `inspectImport`, `openImportPreview`, `saveScenarioToFile`, `persistScenarioName`, `initScenarioNameEditor`); world settings toggles (`toggleSpectator`, `updateTimePerTick`, `updateClockStart`, `restartScenario`) - which are not save/load at all; and the list template, a single large Lit expression with per-row inline styles and `window.SaveLoadView` global refs. Two concrete extractions: move the settings toggles to their own module (a world/settings view; `restartScenario` may belong with the world toolbar), and extract `renderSaveRow(save)` as a small sub-template returning a Lit template using CSS classes instead of the inline style string - the natural home for bug-40's badge fix and task-455's row interactions, so land those together. Follow the repo module conventions: keep the `@module`/`@contributes` header current (`python tools/js_module_index.py --write`), add the `<script>` tag in `templates/index.html` for any new module, and check `tools/unit/run.cjs`'s module list if portable logic is introduced.

## Reconnaissance (2026-10-20) - VERDICT: STILL_VALID

Re-measured the host and checked for the two extractions. Neither has landed.

**The file has grown, not shrunk.** `static/js/ui/saveload-view.ts` is **657**
lines (the emitted `saveload-view.js` is 737). The card originally cited 648 for
the `.js`; the `.ts` source is the one to measure, and it is 9 lines past the
card's own figure. No extraction has removed a concern.

**All four concerns are still in the same file.** Measured 2026-10-20:

| Concern | Live location | Still present? |
|---|---|---|
| Savegame CRUD | `saveload-view.js:416` (`saveGame`), `:436` (`saveGameToSlot`), `:450` (`doRenameSave`), `:480` (`loadGameList`), `:545` (`doLoadGame`), `:574` (`doDeleteSave`), `:593` (`confirmDeleteAllSaves`) | yes |
| Scenario import/export | `saveload-view.js:119` (`downloadWorld`), `:130` (`uploadWorld`), `:154` (`inspectImport`), `:235` (`openImportPreview`), `:363` (`saveScenarioToFile`), `:82` (`persistScenarioName`), `:36` (`initScenarioNameEditor`) | yes |
| World settings toggles | `saveload-view.js:628` (`restartScenario`), `:658` (`toggleSpectator`), `:671` (`updateTimePerTick`), `:692` (`updateClockStart`) | yes |
| List template | `saveload-view.js:480-539`, one inline `saveLoadViewTag` expression with per-row inline styles | yes |

`renderSaveRow` does not exist: a repo-wide search for the name returns zero
hits. The row is still built as concatenated template strings with inline
`style="..."` attributes, exactly as the card describes.

**The settings toggles have no second home.** `static/js/ui/settings-view.ts`
exists (251 lines) and owns the Settings *modal*, but it does not own
`toggleSpectator` / `updateTimePerTick` / `updateClockStart` / `restartScenario`
- those four functions and their `window.SaveLoadView` exports at
`saveload-view.js:731-734` are still in the save module. The card's acceptance
item "spectator/time/clock moved out and still reachable from wherever they are
rendered today" is therefore untouched.

**No sibling task has absorbed this.** task-441 (split the frontend giants) is
still `todo` and its remeasured table (2026-10-16) does not list
`saveload-view.ts` at all - it sits below the 1500-line scan threshold, so it
was never a target. task-455 (the UX half) is still `todo` and its acceptance
items are all unchecked. bug-40's badge fix is still unfixed: the AUTO badge and
version badge are still emitted as inline `<span>` HTML inside the row template
(`saveload-view.js:518, 521`), not as CSS classes.

The card stays in `todo`.

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

- `static/js/ui/saveload-view.js` - split
- `static/js/ui/<new settings view>.js` - extracted toggles
- `templates/index.html` - script tags
- `static/css/style.css` - `.save-game-item` row classes

## Why

`static/js/ui/saveload-view.js` is 648 lines and mixes four unrelated concerns, and the mix is the problem: savegame CRUD and scenario import/export belong together as save/load, but the world settings toggles (`toggleSpectator`, `updateTimePerTick`, `updateClockStart`, `restartScenario`) are not save/load at all, and the list template is a single large Lit expression with per-row inline styles and `window.SaveLoadView` global refs. Splitting by concern means the Save/Load modal stops being a grab-bag and the settings stop living inside the save module, so each surface has one owner and an agent editing one does not pull the whole 648-line file into context. The `renderSaveRow` extraction is the reusable bit: a small sub-template returning a Lit template using CSS classes instead of concatenated HTML strings, which is also the natural home for bug-40's badge fix and task-455's row interactions - land those together rather than as two more inline-style patches. Behaviour is unchanged apart from the bug-40 badge fix: autosave pinned top, stats line, 💾/✏️/🗑 buttons.

## How

1. **Move the world settings toggles to their own owner.** `toggleSpectator`
   (`:616`), `updateTimePerTick` (`:629`) and `updateClockStart` (`:650`) are
   settings, not save/load; `restartScenario` (`:587`) is a world action.
   `static/js/ui/settings-view.ts` already owns the Settings modal and is the
   natural home for the first three, while `restartScenario` can go with the
   world toolbar. Re-export the old `window.SaveLoadView` names as thin
   delegates (`:688-691`) so every existing caller keeps working - the
   refactor discipline in this card requires the public surface to stay
   stable through an extraction.
2. **Extract `renderSaveRow(save)`.** The list is currently one inline
   `saveLoadViewTag` expression - `saves.map(...)` at
   `static/js/ui/saveload-view.ts:465` - that builds each row as concatenated
   template strings with inline `style="..."` attributes (the row div at
   `:489`). Replace it with a named function returning a Lit template and move
   the row styling into CSS classes in `static/css/style.css`. The row
   already carries `class="save-game-item"`, but no rule for it exists in the
   stylesheet yet, so the classes are new work rather than a move.
3. **Land bug-40's badge fix here.** The AUTO badge (`:484`) and the version
   badge (`:487`) are emitted as inline `<span>` HTML; they become
   class-marked elements so a badge reads as a badge rather than as literal
   markup.
4. **Land task-455's row interactions here too.** The in-place rename editor,
   the display-name confirmations and the narrowed autosave row are all
   row-level behaviour, so they belong in the extracted template rather than
   in another inline-style patch.
5. **Follow the module conventions.** Keep the `@module` / `@contributes`
   header current (`python tools/js_module_index.py --write`), add a
   `<script>` tag in `templates/index.html` only if a new module was actually
   created, and add any portable logic to `tools/unit/run.cjs`'s module list.
6. **No behaviour change beyond the badge fix.** Autosave stays pinned top,
   the stats line stays, and the 💾 / ✏️ / 🗑 buttons keep their behaviour.

## Steps to verify

1. Confirm the module split: count the concerns left in
   `static/js/ui/saveload-view.ts` and locate the moved toggles.
   - expected: save/load and scenario import/export remain in the save
     module; spectator, time-per-tick, clock-start and restart live in their
     new owner and stay reachable from wherever they are rendered today.
   - observed: not run. Measured 2026-10-20: all four concerns are still in
     `saveload-view.ts` - savegame CRUD at `:396`-`:555`, scenario
     import/export at `:81`-`:350`, the world settings toggles at `:587`-`:650`
     - and the `window.SaveLoadView` exports still carry all four toggles
     (`:688-691`; emitted `.js:731-734`).
2. Check that `renderSaveRow` exists and that the row markup is no longer
   concatenated HTML strings.
   - expected: a named `renderSaveRow` function, CSS classes on the row, and
     the AUTO and version badges emitted as class-marked elements rather than
     inline `<span>` HTML.
   - observed: not run. Measured 2026-10-20: `renderSaveRow` does not exist
     (zero hits repo-wide), the row is still one inline `saveLoadViewTag`
     expression (`saveload-view.ts:465`), and the badges are still inline
     spans (`:484`, `:487`).
3. Run the gates.
   - expected: `node tools/unit/run.cjs` passes, `npm run lint` passes, and
     `python tools/js_module_index.py --check` passes.
   - observed: not run. This card is a filing step; no gate run is recorded
     for it.
4. Exercise the modal after the split.
   - expected: autosave pinned top, the stats line rendered, 💾 / ✏️ / 🗑
     behaviour unchanged, scenario import/export still reachable, and the
     settings controls still reachable in their existing location.
   - observed: not run live. Measured 2026-10-20: the extraction has not
     landed, so the current behaviour is the pre-split behaviour, which the
     card's own acceptance makes the baseline to compare against.

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
