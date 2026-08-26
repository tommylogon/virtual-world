---
group: Conditions
---

# Condition: Restrained (`restrained`)

**Filed**: 2026-08-17
**Priority**: Medium
**Status**: In code — `player.py` `CONDITION_DEFINITIONS`
**Source**: Existing catalog

---

## Purpose

Tied, bound, or held fast. Speed 0, attacks at disadvantage, DEX saves fail. Differentiated from `grappled` (grappled is person-held and has no DEX autofail; restrained is binding with a DEX autofail).

## Schema (catalog entry)

```python
"restrained": {
    "name": "Restrained", "description": "Tied or held fast. Speed 0; attacks at disadvantage.",
    "blocks_actions": True, "blocks_movement": True, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": ["DEX"],
    "attack_mod": -2, "defense_mod": -2, "speed_mult": 0.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {}, "ends_on": ["escape"],
    "known": True, "symptoms": {}, "stack": "noop", "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown

- **Gates**: blocks actions and movement; speech open.
- **Saves/checks**: auto-fails DEX.
- **Combat**: `attack_mod -2` and `defense_mod -2` (easier to hit AND clumsier attacks).
- **Movement**: `speed_mult: 0.0`; keeps grip.
- **Periodic**: none.
- **Lifecycle**: `stack: "noop"`, `default_duration: None`, ends on `escape` only.

## Perception

`known: True` — self-evident.

## Integration points

- `player.py:91-100` — catalog entry.
- `engine/conditions.py` — saves, speed, combat mods.
- Rope/binding use flows, capture mechanics.

## Testing

- [ ] Restrained: speed 0, cannot act/move, DEX saves fail.
- [ ] Combat mods `-2`/`-2` apply.
- [ ] Escape ends the instance.

## Open questions / things to work out

- Intentional overlap/contrast with `grappled` — when is a hold a grapple vs. a restraint (roots/traps/person?)?
- Should escaping restraints be possible by strength without an explicit `escape` action name?
