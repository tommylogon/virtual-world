---
group: Conditions
---

# Condition: Stunned (`stunned`)

**Filed**: 2026-08-17
**Priority**: Medium
**Status**: In code — `player.py` `CONDITION_DEFINITIONS`
**Source**: Existing catalog

---

## Purpose

Reeling from a blow or effect. Can't act or move, fails STR/DEX saves. A fresh stun **extends the countdown** (`stack: refresh`).

## Schema (catalog entry)

```python
"stunned": {
    "name": "Stunned", "description": "Reeling. Can't act or move; fails STR/DEX saves. A fresh stun extends the countdown.",
    "blocks_actions": True, "blocks_movement": True, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": ["STR", "DEX"],
    "attack_mod": 0, "defense_mod": -5, "speed_mult": 0.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {}, "ends_on": ["duration"],
    "known": True, "symptoms": {}, "stack": "refresh", "default_duration": 2,
    "excludes": [],
}
```

## Behavior breakdown

- **Gates**: blocks actions and movement; speech remains open.
- **Saves/checks**: auto-fails STR/DEX.
- **Combat**: `defense_mod -5` (helpless while stunned).
- **Movement**: `speed_mult: 0.0`; keeps grip.
- **Periodic**: none.
- **Lifecycle**: `stack: "refresh"` — re-application extends duration (fresh stun perpetuates). `default_duration: 2` ticks; ends on `duration` only.

## Perception

`known: True` — self-evident.

## Integration points

- `player.py:71-80` — catalog entry.
- `engine/conditions.py` — combat mods, saves, speed.
- `process_tick` countdown.
- Chance-to-stun hooks (task-165 done) that apply this.

## Testing

- [ ] Stun blocks actions/movement; speech allowed.
- [ ] Fresh stun refreshes/extends the countdown, not a new instance.
- [ ] Auto-expires after `default_duration` ticks (or extended duration).
- [ ] `defense_mod -5` applies.

## Open questions / things to work out

- Should damage end stun early (add `damage` to `ends_on`)? Currently only timed.
- Confirm the extension math when a fresh stun is applied to an existing one.
