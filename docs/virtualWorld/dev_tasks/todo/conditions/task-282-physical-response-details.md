---
group: Conditions
---

# Condition: Nipple Hard (`nipple_hard`)

**Filed**: 2026-08-17
**Priority**: Low
**Status**: Planned — task-209 (Arousal State Conditions & Threshold Triggers)
**Source**: Proposed (not yet in `player.py`)

---

## Purpose

A local, self-evident physical marker of arousal — a periodic Arousal feed with a visible tell. Minor, known, low-stakes.

## Proposed schema

```python
"nipple_hard": {
    "name": "Nipple Hard", "description": "Hard and sensitive.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": [],
    "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {"Arousal": 1},
    "ends_on": ["calm", "release"],
    "known": True,
    "symptoms": {1: "Your nipples are stiff and unusually sensitive."},
    "stack": "noop",
    "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown (proposed)

- **Gates**: none.
- **Saves/checks**: none.
- **Combat**: neutral.
- **Movement**: full speed.
- **Periodic**: `Arousal +1` per tick — a steady, small feed into the arousal loop.
- **Lifecycle**: `stack: "noop"` (already hard — nothing more to apply). Ends on calming or release. Applied by touch/arousal triggers.

## Perception

`known: True` — self-evident, visible.

## Integration points space

- `engine/player.py` — `CONDITION_DEFINITIONS` entry.
- `engine/conditions.py` — `process_tick` Arousal feed.
- Source: nipple/touch actions (Nipple & Erogenous Zone design Phase 2).

## Testing (proposed)

- [ ] `Arousal +1`/tick while active.
- [ ] `known: True` renders to the agent.
- [ ] Calming/release clears it.

## Open questions / things to work out

- Is a gentle Arousal feed enough value to be a condition, or is it pure flavor? (task-209 lists it, so keep as authored.)
- `stack: "noop"` — confirm re-stimulation doesn't need to escalate anything.
