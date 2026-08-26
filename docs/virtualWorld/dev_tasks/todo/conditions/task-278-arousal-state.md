---
group: Conditions
---

# Condition: Aroused (`aroused`)

**Filed**: 2026-08-17
**Priority**: High
**Status**: Planned — task-209 (Arousal State Conditions & Threshold Triggers)
**Source**: Proposed (not yet in `player.py`)

---

## Purpose

Mid arousal band (Arousal 30–50). Notable Stimulation gain, measurable combat distraction, and auto-failed perception/concentration checks.

## Proposed schema

```python
"aroused": {
    "name": "Aroused", "description": "Clearly aroused. Hard to focus; a little careless.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": ["perception", "concentration"],
    "auto_fail_saves": [],
    "attack_mod": -2, "defense_mod": -2, "speed_mult": 1.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {"Stimulation": 2},
    "ends_on": ["calm", "threshold_drop"],
    "known": True,
    "symptoms": {1: "Heat pools low in your belly and it's hard to think straight."},
    "stack": "refresh",
    "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown (proposed)

- **Gates**: none hard.
- **Saves/checks**: auto-fails `perception` and `concentration` checks (`auto_fail_checks`).
- **Combat**: `attack_mod −2`, `defense_mod −2`.
- **Movement**: full speed.
- **Periodic**: `Stimulation +2` per tick.
- **Lifecycle**: `stack: "refresh"`. Applied at Arousal 30–50; replaced at 50 (`highly_aroused`) or 90 (`frantic`); removed below 30.

## Perception

`known: True` — the agent knows they're aroused.

## Integration points space

- `engine/player.py` — `CONDITION_DEFINITIONS` entry.
- `engine/tick_manager.py` — threshold checks in `tick_turn()`.
- `engine/conditions.py` — `auto_fails_checks(player, "perception"/"concentration")`, combat mods, `process_tick` periodic.

## Testing (proposed)

- [ ] Arousal 30–50 → `aroused`; crossing 50 or 90 transitions; dropping below 30 removes.
- [ ] Perception/concentration checks auto-fail.
- [ ] `attack_mod`/`defense_mod −2` apply.
- [ ] `Stimulation +2`/tick feedback.

## Open questions / things to work out

- Do `perception`/`concentration` checks exist in the engine's check system, and will `auto_fail_checks` pick them up (same pathway as `sight`/`hearing`)?
- Confirm the Stimulation→Arousal feed and handoff to `highly_aroused`.
