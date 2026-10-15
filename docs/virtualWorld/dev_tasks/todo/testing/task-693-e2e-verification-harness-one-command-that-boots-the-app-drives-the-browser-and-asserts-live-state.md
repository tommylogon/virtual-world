---
type: task
status: todo
area: testing
priority: high
---

# task-693: E2E verification harness: one command that boots the app, drives the browser and asserts live state

**Filed:** 2026-10-04
**Related:** task-444,bug-520,bug-521

## What

TODO

## Acceptance

- [ ] `python tools/e2e.py --scenario <name>` boots the app on a scratch port
      (`VW_PORT`, never 4444), waits for the mid-boot state to clear, and runs the
      requested check in a driven browser.
- [ ] The harness documents and uses the session-verified recipe: the turn queue is
      CLIENT-side, so a second tab is a safe sandbox; nothing mutates world state
      unless a turn is committed; `HumanTurnComposer.request()` opens the turn card
      directly; turn-based mode + max-steps=1 is the safe startup.
- [ ] Asserts read the client (`worldState.players`, DOM counts with
      getBoundingClientRect, never `element exists`) and the server truth
      (`data/autosave.json`, `/api/state` via a scoped query).
- [ ] Ship it with the regression checks this session produced live: library
      browser opens (bug-520), importing a duplicate-named character twice with an
      explicit area puts BOTH in that area (bug-521), person menu exposes the
      task-610 verbs, hidden ways stay out of WAYS OUT (bug-23), no orphaned
      `.tsv-scrim` after closing the modal with a menu open (task-612).
- [ ] Runs green headlessly on this machine; a clean-checkout A/B is not required
      for UI checks but failures must name the interaction that failed.

## Why

TODO

## How

TODO

## Steps to verify

1. Run `python tools/e2e.py --scenario <name>` for one documented fixture and
   capture the process output and selected scratch port.
   - expected: the harness starts the app on a free `VW_PORT` (never 4444),
     waits for mid-boot state to clear, launches a driven browser, and reports
     each named interaction and assertion.
2. Run the library-browser, duplicate-character-import, person-menu,
   hidden-way, and modal-scrim checks listed in Acceptance.
   - expected: each check performs its named browser interaction and validates
     both visible DOM state using rendered bounds and the corresponding client
     or server state; failures identify the check and failed assertion.
3. Cause one selected assertion to fail in a scratch run and read the harness
   output.
   - expected: the report names the scenario, interaction, expected result, and
     observed value; it does not pass because a hidden DOM node exists.

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: the scenario page in the harness-driven browser, launched
from the repository root with `python tools/e2e.py --scenario <name>`. The
harness boots a scratch app instance and opens the selected scenario there.

Current availability: the task specifies the expected command and browser
checks, but the one-command harness is planned. This section does not claim the
command currently exists or succeeds.

Live steps when available:
1. Run the command with a named fixture while port 4444 is occupied.
   - expected: the harness chooses a free port, reports the URL/port it uses,
     and leaves the existing server on 4444 untouched.
2. Read the named check output while the harness exercises each fixture
   interaction: open Library Browser, import the duplicate-named character
   twice into an explicit area, open the person action menu, inspect WAYS OUT
   with a hidden way, and close the modal with the menu open.
   - expected: each check reports its DOM result and corresponding
     `worldState`/`/api/state` value; the hidden way is absent from WAYS OUT
     and closing the modal removes `.tsv-scrim`.
3. Trigger one expected-value mismatch in a scratch fixture.
   - expected: the run exits as a failure and identifies the specific
     interaction and mismatched value.

These are the intended CLI-to-browser verification steps. They do not assert
that the harness is implemented today.

This section is not a claim that planned UI exists or works today.
