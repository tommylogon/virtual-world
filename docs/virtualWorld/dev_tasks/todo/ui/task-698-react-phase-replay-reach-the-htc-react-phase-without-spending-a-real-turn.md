---
type: task
status: todo
area: ui
priority: low
---

# task-698: React phase replay: reach the HTC react phase without spending a real turn

**Filed:** 2026-10-04
**Related:** task-679,task-333

## What

TODO

## Acceptance

The react phase (and task-679's wall-of-text fix) cannot be verified without
committing a real action, which spends a turn and mutates the world. The
verification session of 2026-10-04 had to rely on the user's screenshot.

- [ ] The composer can open directly in the react phase with a supplied result
      string (e.g. `HumanTurnComposer.preview(charName, resultText)` or an
      `opts.dryRun` on `request`) that resolves to NOTHING — no action, no
      endTurn, no memory write; closing it is a pure client dismissal.
- [ ] The engine path is untouched: `setPhase('react')` via the real
      compose->Act->react flow behaves exactly as today.
- [ ] Used by the e2e harness (task-693) to assert task-679's acceptance: split
      movement/prose/exits, clamped height, no raw way tail.
- [ ] The affordance is hidden behind a flag or a dev-only entry point so normal
      play cannot trigger it accidentally.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: A dev-only Human Turn Composer preview action that opens the react phase with supplied character/result text, marked as a preview so normal play cannot invoke it accidentally.

Current availability: No react-phase replay affordance is claimed as implemented. The user-supplied screenshot was the only evidence available during the 2026-10-04 verification session because a real action spends a turn.

Live steps when available:
1. Record `/api/state` and the current turn number; open the dev-only react preview for a named character with a supplied movement/result string.
   - expected: the HTC displays the react phase without calling `/api/action`, ending a turn, advancing the clock, or writing a memory.
2. Close the preview with its close control and compare state with the before snapshot.
   - expected: dismissal is client-only; turn, world state, and memory count are unchanged.
3. Use the preview with the crowded mansion result from task-679, then inspect its separated prose and hidden way tail.
   - expected: the real task-679 browser assertions run without spending an action or altering the normal `compose → Act → react` path.
4. Confirm the entry point is absent in normal play and available only in the e2e/dev harness.
   - expected: players cannot accidentally trigger the supplied-result preview during an ordinary turn.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
