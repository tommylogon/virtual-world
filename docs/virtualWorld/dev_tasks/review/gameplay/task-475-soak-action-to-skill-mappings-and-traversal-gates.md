---
type: task
status: review
area: gameplay
priority: high
---

# task-475: Soak action to skill mappings and traversal gates

**Filed:** 2026-09-23
**Related:** task-472, task-474, task-470, task-464

## Goal

Give the soak tier real checks on risky actions instead of only forage: hazard travel (Survival), climb/jump/swim/force (Athletics), balance/squeeze (Acrobatics), sneak/avoid notice (Stealth), calm/ride a beast (Animal Handling), treat/diagnose (Medicine), read a mood before approaching (Insight), identify a safe plant (Nature), investigate a body or scene (Investigation/Medicine). Failure must change the path (lost time, a detour, a minor condition), never spiral into starvation; routine maintenance takes 10 and never rolls.

## Acceptance

- [x] `engine/traversal.py` is the mapping and the decision layer: `SOAK_ACTIONS` (action -> skill), `ROUTINE_ACTIONS` (take 10, never roll), `skill_for` / `is_routine`.
- [x] **Hazard ground** rolls the skill that carries you: `HAZARD_SKILLS` maps an area tag (Survival for wild country, Athletics for height/water, Acrobatics for balance/squeeze, Stealth for watched ground) at `HAZARD_DC`, and a failure leaves exactly one minor condition (`HAZARD_CONDITION`: `wet` for water, `injured` for height/rubble).
- [x] **Way verbs**: a way needing crawl/climb/jump is crossed with that verb (`way_kind`) instead of stalling on "you need to climb through the north".
- [x] **Failure changes the path**: the turn is spent, the way is remembered (`note_refusal` / `avoid`, 30 game minutes) and one alternative hop is tried immediately as a detour. A refusal can never starve anyone and never repeats forever.
- [x] **Routine ground takes 10 and never rolls**: `attempt` returns without touching the dice when nothing about the ground is hazardous (verified by a `roll_fn` that raises).
- [x] Wired everywhere the soak tier moves: `BackgroundSimulation._travel_toward` / `_travel_to_area` (both via the new `_hop`) and `timeskip._move` (explore and heading travel) cross through `traversal.hop`, which returns a result instead of raising. `_target_step` takes `avoid`, so a refused way is routed around.

## Remaining

- [ ] `engine/npc_behaviors.py` still calls `movement.move_to_area` directly (the simple-NPC tier) — the same verb choice and refusal handling is not applied there.
- [ ] Actions in `SOAK_ACTIONS` that need a policy hook before they can roll: calm/ride (task-476), treat/diagnose/identify_plant (task-478), read_mood and investigate (task-468).
- [ ] Swim/force have no verb yet: `move_to_area` understands crawl/climb/jump only, so water is modelled as an Athletics hazard on the area rather than a swim verb.

## Verification

`python -m pytest tests/test_traversal.py -q` -> 12 passed; traversal/soak/timeskip/background/forage/loot/checks/skills slice -> 331 passed.
