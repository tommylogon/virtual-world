---
type: bug
status: done
area: ui
priority: medium
wiki: "[[Scenario Workflows & UI Audit]]"
---

# bug-552: scenario commit button triggers name editor (accidental rename)

**Filed:** 2026-10-16
**Related:** 

## What

Clicking the scenario status chip's Commit button bubbles up into the scenario-name-container click handler, opening the rename input with the name selected, so a stray keystroke renames the scenario.

## Why

Clicking the scenario Commit button triggered focus events on adjacent editable labels, inadvertently opening inline rename inputs.

## How

The rename editor is a click handler on `#scenario-name-container`
(`static/js/ui/saveload-view.ts:45`), and the status chip lives *inside* that
container (`templates/index.html:40`). The chip's Commit button now stops
propagation before committing (`static/js/ui/scenario-status.ts:69`,
`commit.onclick = (e) => { e.stopPropagation(); commitScenario(); }`), so the
container never sees the click. The implementation is in `scenario-status.ts`,
not `scenario-manager.ts` as this card first said.

## Verified 2026-10-21

- `templates/index.html:40` confirms the chip is a descendant of
  `#scenario-name-container`, so bubbling was the only way the rename editor
  could open.
- `static/js/ui/scenario-status.ts:69` stops propagation on the Commit button
  before calling `commitScenario()`.
- The handler that opens the rename input is only on the container
  (`static/js/ui/saveload-view.ts:45-54`), so no other listener fires on a
  commit-button click.
- Verified live on 2026-10-21: clicking the chip's commit button commits without
  opening the rename editor, confirmed in the browser by the user. The steps
  below record what was checked.

## Browser UI and intended live verification

UI home: the scenario status chip inside the top-left scenario name container
(`#scenario-name-container`, title "Click to rename scenario"). The chip
(`#scenario-status-chip`) shows `📦 <scenario>`, and when the live world has
drifted from its source it adds an amber `●` plus a `💾 Commit` button
(`data-role="scenario-commit"`). The rename editor is a click handler on the
container (`saveload-view.ts:45`), so a bubbling button click used to open it.

1. Load a scenario so it has a source.
2. Make any world edit (move a character, take/drop an item, edit a node) and
   wait about a second for the status poll.
   - expected: `●` and `💾 Commit` appear inside the scenario name container.
3. Click the chip's `💾 Commit` button.
   - expected: the commit toast appears, a `💾 Scenario ... committed.` line is
     logged, and the rename input does **not** open.
4. Regression control: click the scenario name text itself.
   - expected: the rename input opens and is selected. This proves the container
     handler is alive, so step 3 is not passing because the handler is dead.
   Press Escape to cancel.
5. Confirm the menu path still works: `☰` menu -> `💾 Commit Scenario`.
