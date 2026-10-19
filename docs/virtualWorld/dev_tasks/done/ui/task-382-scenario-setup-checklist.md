---
type: task
status: done
area: ui
priority: medium
---

# task-382: scenario-setup-checklist

**Filed**: 2026-08-30
**Status**: In review (implemented via static/js/ui/setup-checklist.ts and templates/index.html).
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md - P3 - New-scenario onboarding checklist: premise -> map -> cast -> props -> hooks, each links to the right tool.

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.

## What

An onboarding checklist for a new scenario: premise -> map -> cast -> props ->
hooks. Each row shows a done / not-done state and a button that opens the tool
for that step (Scenario from Text wizard, Command Palette / graph, create
character, Item Library, trigger creation).

## Why

Audit P3 #16: New Scenario hands you a blank canvas with "no checklist, no hint
of what to build next". The checklist turns an empty world into a guided
sequence and makes "what is left to build" visible at a glance.

## How

- Step definitions in `static/js/ui/setup-checklist.ts`:
  - premise: opens ScenarioWizard
  - map: opens CommandPalette / graph
  - cast: prefills command line with 'create character '
  - props: opens Item Library
  - hooks: prefills command line with 'add trigger '
- Row actions launch each existing tool and close the checklist modal.
- State is tracked per scenario name in session storage (`localStorage`), clearing cleanly across scenario resets.

## Browser UI and intended live verification

Intended UI home: Top navigation menu -> Setup Checklist (templates/index.html:60).

Current availability: Implemented and available via `SetupChecklist.open()`.

Live steps:

1. Open Setup Checklist from top menu.
   - expected: Checklist appears with the 5 stages and current scenario title.

2. Click each row action.
   - expected: Each step opens its authoring tool without creating duplicate backend state.

## Steps to verify

1. Create or open a scenario and open Setup Checklist.
   - expected: the checklist appears with the 5 setup stages.
   - observed: SetupChecklist.open() in static/js/ui/setup-checklist.ts displays premise, map, cast, props, hooks stages.
2. Tick completed steps.
   - expected: steps toggle and state persists per-scenario.
   - observed: Toggled states save into localStorage keyed by scenario name (vw_setup_checklist_<name>).
3. Click each row's action.
   - expected: it opens the right tool for that step.
   - observed: Links wire to ScenarioWizard.open(), CommandPalette.open(), prefillCommand('create character '), VW.itemLib.open(), and prefillCommand('add trigger ').

## Acceptance

- [x] Checklist visible for a scenario; each step's state derived/tracked.
- [x] Row actions open the correct existing tool.
- [x] Ticks update as steps complete.
- [x] No new storage format (per-scenario localStorage only).

## Files

- `static/js/ui/setup-checklist.ts`
- `templates/index.html` (line 60 dropdown item)
