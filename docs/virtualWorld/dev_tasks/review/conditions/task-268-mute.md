---
group: Conditions
---

# Condition: Mute (`mute`)

**Filed**: 2026-08-17
**Priority**: Low
**Status**: In code — `player.py` `CONDITION_DEFINITIONS`
**Source**: Existing catalog

---

## Purpose

Can't speak. No sound comes out. The speech-blocking condition.

## Schema (catalog entry)

```python
"mute": {
    "name": "Mute", "description": "Can't speak. No sound comes out.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": True,
    "auto_fail_checks": [], "auto_fail_saves": [],
    "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {}, "ends_on": ["duration", "cure"],
    "known": True, "symptoms": {}, "stack": "noop", "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown

- **Gates**: `blocks_speech: True` (cannot speak).
- **Saves/checks**: none.
- **Combat**: neutral.
- **Movement**: full speed.
- **Periodic**: none.
- **Lifecycle**: `stack: "noop"`; `default_duration: None` (permanent until countered/removed); ends on `duration` or `cure`.

## Perception

`known: True` — the agent is told they can't speak.

## Integration points

- `player.py:185-194` — catalog entry.
- `engine/conditions.py` — `can_speak` (iterates conditions with `blocks_speech`).
- Action input: speech actions should be rejected/blocked while mute.

## Testing

- [ ] `can_speak` returns False while mute.
- [ ] Speech/volume actions are blocked or natively handled.
- [ ] Cured/expired → speech restored.

## Open questions / things to work out

- Should mute be enforced in the action layer (reject `speech`), or just prompt-hinted? Verify actual enforcement path.
- `default_duration: None` — should natural recovery ever apply, or is it always explicit cure/removal?
