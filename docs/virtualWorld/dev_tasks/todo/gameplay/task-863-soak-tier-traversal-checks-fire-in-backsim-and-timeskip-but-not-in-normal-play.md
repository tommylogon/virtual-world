---
type: task
status: todo
area: gameplay
priority: medium
wiki: "[[Movement]]"
related: [task-775]
---

# task-863: Soak-tier traversal checks fire in backsim and timeskip but not in normal play

**Filed:** 2026-10-18
**Related:** task-775

<!-- deps:start -->
**Related:** [[task-775-sibling-scope-traversal-border-seam-remap-and-footprint-placement]]
<!-- deps:end -->

## What

The soak-tier hazard check (`attempt` in `engine/traversal.py`) is reached only through `traversal.hop`, and `hop` is called only from `engine/background_simulation.py:1235` and `engine/timeskip.py:694`. The human and LLM command path (`/api/action` -> `world.move_to_area` -> `movement.move_to_area`) never calls it. So the same character crossing the same hazard (a ford, a cliff, a watched path) rolls the hazard skill check under backsim or timeskip, and does not under normal play.

## Why

One character, one movement: `controller` and `simulation_mode` are orthogonal axes (task-399:21-22; `Characters/Background Simulation.md:241`, "same characters, two fidelities"). A resolution that exists only in the unattended tier means the character resolves the same crossing differently depending on who is driving, and the difference is invisible in normal play, so the mechanic reads as unimplemented there. It may be intended tiering (interactive play is gate-checked, and the soak tier adds a dice model for unattended travel) or an unwired path. That has not been decided, which is why this card exists.

## How

Decide first, implement only if the answer is "unify". Options: (a) intended tiering - document the rule on the movement feature page and on the Background Simulation page, and say why the interactive path is gate-checked rather than rolled; (b) unify - route the normal-play move through the same `traversal.attempt` seam the hop uses, or move the hazard decision inside `movement.move_to_area` so every caller gets it once. Whichever is chosen, do not add a second check for the interactive path; reuse `attempt`.

## Browser UI and intended live verification

Observable in the game view: move into a hazard-tagged area from the command line or a turn action and read the resulting log line. There is no authoring surface for this; the check is a live outcome, so verify it on a loaded scenario rather than by reading the code.

## Steps to verify

1. In normal play, move into a hazard-tagged area (for example a `ford` or a `cliff`) via `/api/action` and read the log.
   - expected: either the same hazard skill check the backsim gets, or a recorded decision that the interactive path deliberately does not roll.
   - observed: TODO
2. Drive the same crossing through `traversal.attempt` from a soak.
   - expected: the check fires, and the two paths agree, or the difference is the documented one.
   - observed: TODO

## Acceptance

- [ ] The intended behaviour is decided and written down (tiered by design, or unified), with the reason.
- [ ] If unified, a normal-play move into hazard ground runs the same check the backsim does, through `traversal.attempt` and not a second implementation.
- [ ] The movement feature page states the final rule.

## Files

- `engine/traversal.py`
- `engine/movement.py`
- `engine/background_simulation.py`
- `engine/timeskip.py`
- `routes/action_handlers.py`
- `docs/virtualWorld/World Building/Movement.md`
