---
group: Conditions
---

# Condition: Busy (`busy`)

**Filed**: 2026-08-17
**Priority**: Low
**Status**: In code — `player.py` `CONDITION_DEFINITIONS`
**Source**: Existing catalog

---

## Purpose

Occupied with a persistent multi-turn activity. Non-blocking and interruptible; the activity carries the flavor + regen mix rather than this condition. Shared across all activities that need an "occupied" marker.

## Schema (catalog entry)

```python
"busy": {
    "name": "Busy", "description": "Occupied with something. Interruptible.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": [],
    "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {}, "ends_on": ["stop"],
    "known": True, "symptoms": {}, "stack": "noop", "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown

- **Gates**: **none** — busy does not block action/movement/speech on its own.
- **Saves/checks**: none.
- **Combat**: neutral.
- **Movement**: full speed.
- **Periodic**: none.
- **Lifecycle**: `stack: "noop"`, `default_duration: None`, ends on `stop` (end the activity → clear the marker).

## Perception

`known: True` — rendered as "occupied".

## Integration points

- `player.py:111-120` — catalog entry. Uses `"busy"` for `rest`/`sleep`/`wait`/`bathe`/`meditate`/`sit`/`lie down`.
- `engine/activities.py` — applies/removes `busy` as activities start/finish; the activity stores flavor + regen separately.
- Interruptibility: ending an activity calls `end_conditions`/`end_instances("stop")`.

## Testing

- [ ] Being `busy` does not prevent acting (interruptible by design).
- [ ] Ending an activity clears the `busy` marker.

## Open questions / things to work out

- Does `busy` actually gate anything, or is it purely informational now? (Activities themselves, not the condition, likely own interrupt behavior.)
- Duplicated `busy` instances from stacked activities — does `stack: "noop"` leave stale markers?
