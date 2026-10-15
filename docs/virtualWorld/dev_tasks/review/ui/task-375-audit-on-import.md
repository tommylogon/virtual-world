---
type: task
status: review
area: ui
priority: medium
---

# task-375: audit-on-import

**Filed**: 2026-08-30
**Status**: In Review — implemented 2026-08-30 as part of task-369's import preview.

## What was built

- The `🔬 Deep audit` button in the import-preview dialog (`static/js/ui/saveload-view.js`)
  runs `TriggerValidator` against the *incoming* world dict BEFORE any state mutation —
  issues are listed in the preview with severity (err/warn/info); the user can still
  `[Apply anyway]` (undo-protected) or cancel.
- No separate route: reuses `POST /api/triggers/validate` (validator panel path) on an
  in-memory copy.

## Note

Filed separately from 369 but landed in the same dialog. Task 369's doc is the canonical
entry; this file records the distinction (validate-before-load vs preview counts).

## What

TODO

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Save/Load → import preview → “🔬 Deep audit” in that preview. Findings belong to the incoming-world preview, before the user applies any imported state.

Current availability: The card records the button and incoming-world validation implementation, reusing `POST /api/triggers/validate`; it does not record a browser observation proving that the preview is non-mutating.

Live steps when available:
1. Open an import preview for a scratch scenario containing one invalid trigger and one valid trigger; note the current world state before starting the audit.
   - expected: the preview shows the incoming scenario and the current world remains unchanged.
2. Click “🔬 Deep audit”.
   - expected: the preview lists trigger findings with `err`, `warn`, or `info` severity from the incoming world, and the current loaded world is still unchanged.
3. Cancel the import, then repeat and choose “Apply anyway”.
   - expected: cancel leaves the world unchanged; Apply anyway applies the previewed import through the undo-protected path despite audit findings.
4. Inspect the Network panel for the validation request.
   - expected: the request is `POST /api/triggers/validate` using the incoming world payload; no separate audit route or pre-audit state mutation occurs.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
