---
type: task
status: todo
area: testing
priority: high
---

# task-693: E2E verification harness: one command that boots the app, drives the browser and asserts live state

**Filed:** 2026-10-04
**Related:** task-444,bug-520,bug-521

## Goal

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

