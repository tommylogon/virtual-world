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

TODO

## How

TODO

## Browser UI and intended live verification

Intended UI home: TODO — name the page, panel, tab, or control where this behavior belongs. If no browser UI is appropriate, write 'Not applicable' here, explain why below, and give an observable alternative.

Current availability: TODO — for example, planned/not implemented, present but not live-checked, or live-checked with date and evidence.

Live steps when available:
1. TODO — describe how to reach the surface and the interaction to perform.
   - expected: TODO — describe what the user can see or do.

Why no browser UI: (only when Intended UI home is Not applicable) TODO — explain why browser interaction is not appropriate.

Alternative verification steps: (only when Intended UI home is Not applicable)
1. TODO — describe an observable alternative.
   - expected: TODO — describe the result.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: TODO
   - observed: TODO
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: TODO
   - observed: TODO
3. Run the targeted regression test for the mechanism.
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO
