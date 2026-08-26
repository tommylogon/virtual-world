---
group: Conditions
---

# Condition: Wetness (`wetness`)

**Filed**: 2026-08-17
**Priority**: Medium
**Status**: Planned — task-209 (Arousal State Conditions & Threshold Triggers)
**Source**: Proposed (not yet in `player.py`)

---

## Purpose

Physical arousal wetness. A steady Arousal feed that is **hidden (`known: False`) unless exposed** — the character may not know, and others only see it if clothing/situation reveals it. (Distinct from the thermal `wet` condition in task-190 — different domain.)

## Proposed schema

```python
"wetness": {
    "name": "Wetness", "description": "Arousal wetness.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": [],
    "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {"Arousal": 2},
    "ends_on": ["dry", "release"],
    "known": False,   # hidden unless exposed
    "symptoms": {
        1: "A slick warmth gathers between your thighs.",
        2: "You're unmistakably wet.",
    },
    "stack": "refresh",
    "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown (proposed)

- **Gates**: none.
- **Saves/checks**: none.
- **Combat**: neutral.
- **Movement**: full speed.
- **Periodic**: `Arousal +2` per tick — a meaningful feed into the arousal loop.
- **Lifecycle**: `stack: "refresh"` (re-exposure refreshes). Ends on drying off or release.
- **Hidden/unknown**: `known: False` — the agent perceives only `symptoms` (and only once a threshold is reached). Others perceive it only when **exposed** (garment off / revealing situation).

## Perception

`known: False` → symptom-driven for the self. Observer visibility gated on exposure — an area for design: how does the engine decide "exposed" (clothing removed, `strip`/`undress`)?

## Integration points space

- `engine/player.py` — `CONDITION_DEFINITIONS` entry (`known: False`).
- `engine/conditions.py` — `perceived_conditions`, `symptom_for`.
- Observer perception + clothing/exposure state (ties into `strip`/`undress` and clothing).
- Note the **name collision**: `wetness` vs. task-190's `wet`. Confirm distinct ids and no `CONDITION_DEFINITIONS` key clash.

## Testing (proposed)

- [ ] `Arousal +2`/tick while active.
- [ ] Self: hidden — only symptoms show, and only after a threshold.
- [ ] Observer: only visible when exposed (clothing off / revealing).
- [ ] Drying/release clears it; re-exposure refreshes.

## Open questions / things to work out

- **Exposure logic**: what determines if the condition is perceivable to others (clothing `strip`/`undress` state)?
- **Name clash**: this `wetness` vs. task-190 `wet` — distinct ids? Consider `arousal_wetness` if collision risk.
- Does `known` need to vary per-observer (self knows vs. others know), which the catalog can't express — how to handle exposure-then-knowledge?
