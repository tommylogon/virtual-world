---
type: task
status: cancelled
area: ui
priority: low
---

# task-613: Closed HTC modal stays in the DOM at 0x0 with zero visible children

**Filed:** 2026-09-30
**Related:** 

## Goal

After a turn closes, #htc-modal remains in the DOM with a 0x0 rect and no offsetParent-bearing children while #htc-overlay is display:none. Element presence is therefore not a valid 'is the modal open' test -- the stale innerText still reads a phase marker. Anything probing this surface (tests included) will read a closed modal as open.

## Acceptance

- TODO

## Cancellation

Cancelled 2026-09-30 after writing the fix. A hidden overlay's child legitimately
reports a 0x0 rect and a null ``offsetParent`` -- that is standard DOM behaviour,
not an application defect. The actual fault was in the audit probe, which tested
``document.getElementById('htc-modal')`` for presence and read a closed modal as
open. Nothing to fix in the app; the lesson is recorded in the live audit README
as the ninth DOM-vs-pixels disagreement.