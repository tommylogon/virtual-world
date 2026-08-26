---
group: Conditions
---

# Condition: Deaf (`deaf`)

**Filed**: 2026-08-17
**Priority**: Low
**Status**: In code — `player.py` `CONDITION_DEFINITIONS`
**Source**: Existing catalog

---

## Purpose

Can't hear. Hearing cues are lost. The `auto_fail_checks` gate for the `hearing` sense — pairs with `blind` for the senses family.

## Schema (catalog entry)

```python
"deaf": {
    "name": "Deaf", "description": "Can't hear. Hearing cues are lost.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": ["hearing"], "auto_fail_saves": [],
    "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {}, "ends_on": ["duration", "cure"],
    "known": True, "symptoms": {}, "stack": "noop", "default_duration": 5,
    "excludes": [],
}
```

## Behavior breakdown

- **Gates**: none hard.
- **Saves/checks**: auto-fails `hearing` checks (`auto_fail_checks: ["hearing"]`).
- **Combat**: neutral.
- **Movement**: full speed.
- **Periodic**: none.
- **Lifecycle**: `stack: "noop"`; `default_duration: 5`; ends on `duration` or `cure`.

## Perception

`known: True` — the agent is told they're deaf.

## Integration points

- `player.py:175-184` — catalog entry.
- `engine/conditions.py` — `auto_fails_checks(player, "hearing")`, perception.
- Sensory context: hearing-based cues (audio) dropped/gated when deaf.

## Testing

- [ ] Hearing checks auto-fail while deaf.
- [ ] Hearing-based context lines are gated/omitted.
- [ ] Expires after `default_duration` or is cured.

## Open questions / things to work out

- Should deafness gate speech perception differently from sound cue delivery (self vs. incoming audio)?
- Pairs with `blind` for a full sensory-deprivation scenario — any combined handling?
