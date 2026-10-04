---
type: task
status: todo
area: ui
priority: low
---

# task-698: React phase replay: reach the HTC react phase without spending a real turn

**Filed:** 2026-10-04
**Related:** task-679,task-333

## Goal

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
