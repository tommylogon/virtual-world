---
type: task
status: inprogress
area: ui
priority: medium
---

# task-382: scenario-setup-checklist

**Filed**: 2026-08-30
**Status**: Not started (card complete; no implementation yet).
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md — P3 — New-scenario onboarding checklist: premise → map → cast → props → hooks, each links to the right tool.

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.

## What

An onboarding checklist for a new scenario: premise → map → cast → props →
hooks. Each row shows a done / not-done state derived from the current world and
a button that opens the tool for that step (Scenario from Text wizard,
WorldPainter, create-modal, trigger editor).

## Why

Audit P3 #16: New Scenario hands you a blank canvas with "no checklist, no hint
of what to build next". The checklist turns an empty world into a guided
sequence and makes "what is left to build" visible at a glance.

## How

- Derive each step's state from data already present — never store checklist
  state:
  - **premise** — the scenario name is set and/or `world_lore` is non-empty.
  - **map** — at least one area exists and is placed (has a cell / is on a grid).
  - **cast** — at least one character (player) exists.
  - **props** — at least one item exists and is placed or held.
  - **hooks** — at least one trigger exists on any node.
- Each row's action opens the corresponding existing surface (the Scenario from
  Text wizard, WorldPainter, the create-modal, the trigger editor).
- Show the panel when the scenario is empty (or on demand). Derived only; no
  new storage.

## Browser UI and intended live verification

Intended UI home: Scenario Manager → create-scenario flow → setup checklist.

Current availability: The checklist and its world-derived step states are still in progress.

Live steps when available:

1. Create a new scratch scenario and inspect the setup checklist before adding content.
   - expected: The checklist appears with incomplete steps derived from the empty world.

2. Add and place an area, then use the action on each remaining checklist row.
   - expected: Relevant steps update from world state and each row opens its existing authoring tool without duplicate stored checklist state.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. Create a new scenario.
   - expected: the checklist appears with every step incomplete.
   - observed: TODO
2. Add an area and place it.
   - expected: the "map" step ticks.
   - observed: TODO
3. Click each row's action.
   - expected: it opens the right tool for that step.
   - observed: TODO

## Acceptance

- [ ] Checklist visible for an empty scenario; each step's state derived from existing world data.
- [ ] Row actions open the correct existing tool.
- [ ] Ticks update as the world gains content.
- [ ] No new storage (nothing persisted).

## Files

- `static/js/ui/` — the checklist panel (new).
- `templates/index.html`.
- Reuses the scenario-wizard / WorldPainter / create-modal entry points.
