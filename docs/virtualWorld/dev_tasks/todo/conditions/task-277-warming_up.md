---
group: Conditions
---

# Condition: Warming Up (`warming_up`)

**Filed**: 2026-08-17
**Priority**: Medium
**Status**: Planned — task-209 (Arousal State Conditions & Threshold Triggers)
**Source**: Proposed (not yet in `player.py`)

---

## Purpose

First arousal band. Arousal is building — mild Stimulation gain each tick. Applied when Arousal crosses into the 15–30 band.

## Proposed schema

```python
"warming_up": {
    "name": "Warming Up", "description": "Blood warming. Desire beginning to stir.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": [],
    "attack_mod": -1, "defense_mod": -1, "speed_mult": 1.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {"Stimulation": 1},
    "ends_on": ["calm", "threshold_drop"],
    "known": True,
    "symptoms": {1: "You feel warm and a little restless."},
    "stack": "refresh",
    "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown (proposed)

- **Gates**: none hard.
- **Saves/checks**: none yet.
- **Combat**: very light `attack_mod`/`defense_mod −1` (mild distraction).
- **Movement**: full speed.
- **Periodic**: `Stimulation +1` per tick (feeds the arousal loop).
- **Lifecycle**: `stack: "refresh"`. Applied/removed by **threshold checks** in `tick_turn()`: Arousal 15–30 → `warming_up`; drops below 15 → removed.
- **Band transitions** (task-209): 15–30 warming, 30–50 aroused, 50–90 highly, 90+ frantic. Moving up replaces this state; moving down reverts.

## Perception

`known: True` — an early, honest signal of desire.

## Integration points space

- `engine/player.py` — `CONDITION_DEFINITIONS` entry.
- `engine/tick_manager.py` — threshold checks in `tick_turn()` (apply/remove by Arousal).
- `engine/conditions.py` — `process_tick` periodic feedback into Stimulation/Arousal.

## Testing (proposed)

- [ ] Arousal crosses 15 → `warming_up` applied; falls below 15 → removed.
- [ ] `Stimulation +1`/tick feedback.
- [ ] Transitions cleanly to `aroused` at 30 and back down.

## Open questions / things to work out

- Exact Stimulation↔Arousal loop wiring (which vital feeds which).
- Band re-entry timing to avoid flickering at the boundary (hysteresis).
- Is a `defense/attack_mod` appropriate at this mild stage, or zero?
