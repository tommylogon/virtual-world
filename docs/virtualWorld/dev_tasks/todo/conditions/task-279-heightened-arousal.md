---
group: Conditions
---

# Condition: Highly Aroused (`highly_aroused`)

**Filed**: 2026-08-17
**Priority**: High
**Status**: Planned — task-209 (Arousal State Conditions & Threshold Triggers)
**Source**: Proposed (not yet in `player.py`)

---

## Purpose

High arousal band (Arousal 50–90). Strong stimulation, Energy cost, significant combat distraction, and auto-failed willpower/concentration.

## Proposed schema

```python
"highly_aroused": {
    "name": "Highly Aroused", "description": "Drowning in it. Senses narrowing, body taking over.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": ["perception", "concentration", "willpower"],
    "auto_fail_saves": [],
    "attack_mod": -3, "defense_mod": -3, "speed_mult": 1.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {"Stimulation": 3, "Energy": -2},
    "ends_on": ["calm", "threshold_drop"],
    "known": True,
    "symptoms": {
        1: "Every thought is louder for the heat between your legs. You can barely hold onto a line of thought.",
    },
    "stack": "refresh",
    "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown (proposed)

- **Gates**: none hard.
- **Saves/checks**: auto-fails `perception`, `concentration`, and `willpower` checks.
- **Combat**: `attack_mod −3`, `defense_mod −3`.
- **Movement**: full speed (for now; may drop at `frantic`).
- **Periodic**: `Stimulation +3` and `Energy −2` per tick — the arousal is now taxing.
- **Lifecycle**: `stack: "refresh"`. Applied at Arousal 50–90; replaced at 90 (`frantic`); reverts below 50.

## Perception

`known: True` — intense, obvious.

## Integration points space

- `engine/player.py` — `CONDITION_DEFINITIONS` entry.
- `engine/tick_manager.py` — threshold checks in `tick_turn()`.
- `engine/conditions.py` — auto-fail checks, combat mods, `process_tick`.
- Energy cost interplay with `exhausted` (both drain Energy).

## Testing (proposed)

- [ ] Arousal 50–90 → `highly_aroused`; transitions at 90 / below 50.
- [ ] Perception/concentration/willpower checks auto-fail.
- [ ] `attack_mod`/`defense_mod −3`.
- [ ] Energy −2/tick alongside Stimulation +3.

## Open questions / things to work out

- Does `willpower` share the `auto_fail_checks` pathway, or is it an ability save (`auto_fail_saves`)? Confirm the check taxonomy.
- Energy drain stacking with `exhausted` — should this accelerate collapse?
