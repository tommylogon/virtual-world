---
type: bug
status: review
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

Stopped click event propagation on action buttons and explicitly blurred inline editable fields prior to commit handler execution.

## Browser UI and intended live verification

Intended UI home: Scenario Manager header commit controls.

Current availability: Implemented in scenario-manager.ts; click propagation stopped.

Live steps when available:
1. Open Scenario Manager and click Commit.
   - expected: Scenario saves cleanly and name input does not activate.
