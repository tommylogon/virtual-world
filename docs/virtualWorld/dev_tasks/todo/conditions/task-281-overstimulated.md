---
group: Conditions
---

# Condition: Overstimulated (`overstimulated`)

**Filed**: 2026-08-17
**Priority**: Medium
**Status**: Planned — task-209 (Arousal State Conditions & Threshold Triggers)
**Source**: Proposed (not yet in `player.py`)

---

## Purpose

Too much, too fast — overstimulation. Drains Pleasure and costs Energy; excludes `satisfied`/`numb`. A negative/aversive state contrasted with the pleasant arousal bands.

## Proposed schema

```python
"overstimulated": {
    "name": "Overstimulated", "description": "Too much. Every touch is too much.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": ["concentration"],
    "auto_fail_saves": [],
    "attack_mod": -2, "defense_mod": -3, "speed_mult": 0.9,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {"Pleasure": -3, "Energy": -1},
    "ends_on": ["ease_off", "rest"],
    "known": True,
    "symptoms": {
        1: "Even gentle touch feels like too much.",
        2: "Sensitive to the point of pain. You need a moment.",
    },
    "stack": "refresh",
    "default_duration": None,
    "excludes": ["satisfied", "numb"],
}
```

## Behavior breakdown (proposed)

- **Gates**: none hard.
- **Saves/checks**: auto-fails `concentration` (can't focus through the overload).
- **Combat**: `attack_mod −2`, `defense_mod −3` — flinchy/exposed.
- **Movement**: slight `speed_mult 0.9`.
- **Periodic**: `Pleasure −3` and `Energy −1` per tick — it actively drains pleasure.
- **Lifecycle**: `stack: "refresh"`. Excludes `satisfied` and `numb` (applying this removes them — you can't be satisfied and overstimulated at once). Ends on easing off / resting.

## Perception

`known: True` — intensely aversive and obvious.

## Integration points space

- `engine/player.py` — `CONDITION_DEFINITIONS` entry + `excludes` into `CONDITION_EXCLUSIONS`.
- `engine/conditions.py` — `process_tick`, combat mods, auto-fail checks.
- Trigger/ovenstim sources: prolonged edging, repeated stimulation past a cap.
- Relief: `ease_off`/rest ends it, potentially leaving `sensitized` or `satisfied`.

## Testing (proposed)

- [ ] Overstimulation drains Pleasure and Energy per tick.
- [ ] Applies to remove `satisfied`/`numb` (`excludes`).
- [ ] Concentration checks auto-fail; combat mods `-2`/`-3`.
- [ ] `ease_off`/`rest` ends it.

## Open questions / things to work out

- Is there a `numb` condition (referenced in `excludes`) yet? If not, the exclusion entry references something undefined.
- Onset criteria — what triggers overstimulation vs. crossing into `frantic`? (Sustained stimulation vs. a spike.)
- Recovery path: straight to `satisfied`, or through `sensitized`?
