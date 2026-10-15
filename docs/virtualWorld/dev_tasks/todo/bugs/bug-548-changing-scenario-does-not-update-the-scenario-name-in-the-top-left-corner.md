---
type: bug
status: todo
area: bugs
priority: medium
---

# bug-548: Changing scenario does not update the scenario name in the top-left corner

**Filed:** 2026-10-12
**Related:** 

## What

scenario-status refresh() writes the chip but never #scenario-name-text, so the top-left name stays stale until the scenario is committed.

## Why

TODO

## How

TODO

## Steps to verify

1. Load a scenario, open Scenario Manager, load a different named scenario, and
   read the top-left `#scenario-name-text` before committing either scenario.
   - expected: the label changes to the newly loaded scenario name as soon as
     scenario status refreshes; it does not keep the previous name until Commit.
   - observed: not yet measured in a browser.
2. Rename the loaded scenario through the supported scenario-name control and
   refresh the scenario status without reloading the page.
   - expected: the top-left label matches the current scenario name, while the
     source/status chip continues to describe the current scenario source.
   - observed: not yet measured in a browser.

## Browser UI and intended live verification

Intended UI home: top-left scenario header, updated by Scenario Manager load
and the scenario-name editor.

Current availability: the card identifies `scenario-status.refresh()` as
updating the status chip without updating `#scenario-name-text`. The stale-name
report has not been reproduced live in this turn.

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

- [ ] TODO

## Files

- TODO
