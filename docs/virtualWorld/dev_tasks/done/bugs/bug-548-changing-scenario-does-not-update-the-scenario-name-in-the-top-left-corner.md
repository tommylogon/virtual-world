---
type: bug
status: done
area: bugs
priority: medium
wiki: "[[Feature Map]]"
---

# bug-548: Changing scenario does not update the scenario name in the top-left corner

**Filed:** 2026-10-12
**Related:** 

## What

**RESOLVED.** `scenario-status.refresh()` now writes `#scenario-name-text` as
well as the status chip, so the top-left name follows the loaded scenario
immediately. The original defect (refresh wrote the chip but never
`#scenario-name-text`, so the top-left name stayed stale until Commit) no longer
holds.

## Why

The scenario name in the top-left is a display projection of the loaded
scenario. It was wired to the commit path rather than the refresh path, so any
scenario change that was not a commit left the label describing the previous
scenario.

## How

`static/js/ui/scenario-status.ts` `refresh()` fetches `/api/scenario/status` and
then, when the payload carries a `name`, sets `#scenario-name-text.textContent`
to it (guarded by a textContent comparison so a no-op refresh does not touch the
DOM) and writes `document.body.dataset.scenarioName`. The pre-existing
`world-state.ts` path also updates the same element from `_scenario_name`, so the
label refreshes on every state fetch as well.

## Steps to verify

1. Load a scenario, open Scenario Manager, load a different named scenario, and
   read the top-left `#scenario-name-text` before committing either scenario.
   - expected: the label changes to the newly loaded scenario name as soon as
     scenario status refreshes; it does not keep the previous name until Commit.
   - observed: not yet measured in a browser. The code path is confirmed
     (`static/js/ui/scenario-status.ts:41-48`); the live click-through was not run.
2. Rename the loaded scenario through the supported scenario-name control and
   refresh the scenario status without reloading the page.
   - expected: the top-left label matches the current scenario name, while the
     source/status chip continues to describe the current scenario source.
   - observed: not yet measured in a browser. Same as above.

## Browser UI and intended live verification

Intended UI home: top-left scenario header, updated by Scenario Manager load
and the scenario-name editor.

Current availability: the refresh path writes `#scenario-name-text` from the
`/api/scenario/status` payload, so the label tracks the loaded scenario without
a commit. The live browser click-through for steps 1 and 2 was not run here;
the fix is confirmed by reading the code.

Live steps when available:
1. Open scenario A and record the visible top-left scenario name. Use Scenario
   Manager to load scenario B without committing scenario A.
   - expected: the top-left name changes to B immediately after the load; the
     status/source chip also describes B.
2. Rename B using the scenario-name editor, then close the editor without a
   page reload.
   - expected: the top-left name shows the edited name, not A or B's old name.
3. Read `#scenario-name-text` in the rendered header and compare it with the
   current scenario name in `/api/state` after each operation.
   - expected: the displayed name matches the loaded/renamed scenario value at
     each step; no Commit action is needed to refresh the label.

These steps define intended access and live acceptance. They are not a claim
that the report has been reproduced in a browser.

## Acceptance

- [x] `scenario-status.refresh()` updates `#scenario-name-text` to the current scenario name.

## Files

- `static/js/ui/scenario-status.ts` (`refresh`)

## Reconciliation (2026-10-20) - FIXED, closed by newer work

**Verdict: FIXED.** The card's premise is now false: `scenario-status.refresh()` already writes the top-left name.

**What landed.** Commit `8a1f0143` (chore: bulk sync worktree, 2026-10-19) added the missing block to `ScenarioStatus.refresh()` in `static/js/ui/scenario-status.ts:41-48`. After fetching `/api/scenario/status`, it reads `st.name`, sets `#scenario-name-text.textContent` to it (guarded by a textContent comparison so a no-op refresh does not touch the DOM), and writes `document.body.dataset.scenarioName`. The card's cited defect - "refresh() writes the chip but never #scenario-name-text" - no longer holds.

**Measured.** `grep -n "scenario-name-text" static/js/ui/scenario-status.ts` returns 2 hits (lines 43, 45), both inside `refresh()`. The pre-existing `world-state.ts:266-269` path (`_fetchNow`) also updates the same element from `_scenario_name`, so the label is refreshed on every state fetch as well.

**Cited line drift.** The card did not cite a line number for `refresh()`, so nothing to correct there. The card's `How` section (TODO) and `Steps to verify` (observed: TODO) are superseded by the fix and are left as historical record.

**Status:** moved to `done` 2026-10-20. No further work required.
