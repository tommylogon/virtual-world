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

The soak-tier hazard check (`attempt` in `engine/traversal.py`) is reached only through `traversal.hop`, and `hop` is called only from `engine/background_simulation.py:1235` and `engine/timeskip.py:694`. The human and LLM command path (`/api/action` -> `world.move_to_area` -> `movement.move_to_area`) never calls it.

Specifically, the difference consists of three runtime behaviors present in soak/timeskip that normal play completely ignores:
1. **D20 Skill Check vs DC 12 (`checks.resolve`):** When crossing a way or entering an area with hazard tags (`ford`, `river`, `cliff`, `swamp`, `guarded`, etc.), `traversal.attempt` resolves a DC 12 skill check against `Athletics`, `Survival`, `Acrobatics`, or `Stealth`. Normal play performs no roll.
2. **Turn Refusal & Hazard Avoidance (`note_refusal`):** Failing the DC 12 roll blocks the move (`ok=False`), prevents entry into the target area, consumes the turn action, and records the refusal in `player.traversal_avoid` so pathfinding routes around it for `AVOID_MINUTES` (30 mins). In normal play, any character can step directly into a `cliff` or `rapids` area without check or refusal unless a hard gate (like `requires: climb` or locked door) is attached to the way.
3. **Minor Condition Infliction (`HAZARD_CONDITION`):** On check failure, `traversal.attempt` can inflict minor conditions (e.g. `wet` from `ford`/`river`/`swamp`, or `injured` from `cliff`/`steep`/`rubble`). Normal play never inflicts hazard conditions on entry unless authored custom `save_on` triggers exist.

## Why

One character, one movement: `controller` and `simulation_mode` are orthogonal axes (task-399:21-22; `Characters/Background Simulation.md:241`, "same characters, two fidelities"). A resolution that exists only in the unattended tier means the character resolves the same crossing differently depending on who is driving, and the difference is invisible in normal play, so the mechanic reads as unimplemented there. It may be intended tiering (interactive play is gate-checked, and the soak tier adds a dice model for unattended travel) or an unwired path. That has not been decided, which is why this card exists.

## How

Decide first, implement only if the answer is "unify". Options: (a) intended tiering - document the rule on the movement feature page and on the Background Simulation page, and say why the interactive path is gate-checked rather than rolled; (b) unify - route the normal-play move through the same `traversal.attempt` seam the hop uses, or move the hazard decision inside `movement.move_to_area` so every caller gets it once. Whichever is chosen, do not add a second check for the interactive path; reuse `attempt`.

## Browser UI and intended live verification

Intended UI home: The command line / Game Action Log (event stream) in the main game view.

Current availability: Present for deterministic gates (doors, locks, climb/crawl requirements); hazard dice checks and condition penalties are planned / missing for interactive player commands.

Live steps when available:
1. Position a player character next to an area or way with hazard tags (e.g., `river` or `cliff`).
2. Issue a move command into that area via the command line (`go north` or click exit).
   - expected: If unified, an event log entry shows the skill check roll (e.g. `Athletics DC 12 vs ...`), resulting in success (entry allowed) or failure (turned back, turn spent, minor condition applied like `wet` or `injured`). If tiered by design, movement proceeds without a roll as documented.
3. Check character vitals and conditions in the Inspector.
   - expected: Condition reflects hazard outcome if check failed.

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
