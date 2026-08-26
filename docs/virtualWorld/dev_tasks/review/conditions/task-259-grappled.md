---
group: Conditions
---

# Condition: Grappled (`grappled`)

**Filed**: 2026-08-17
**Priority**: High
**Status**: In code — `player.py` `CONDITION_DEFINITIONS`
**Source**: Existing catalog

---

## Purpose

Physically held by someone. Speed 0 until you escape. Source-gated: the active player (or grappler) relates to the held target.

## Schema (catalog entry)

```python
"grappled": {
    "name": "Grappled", "description": "Held by someone. Speed 0 until you escape.",
    "blocks_actions": True, "blocks_movement": True, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": [],
    "attack_mod": -2, "defense_mod": 0, "speed_mult": 0.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {}, "ends_on": ["escape", "grappler_incapacitated"],
    "known": True, "symptoms": {}, "stack": "noop", "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown

- **Gates**: blocks actions and movement; speech stays open.
- **Saves/checks**: none autofailed by the condition itself (escape usually runs a check).
- **Combat**: `attack_mod -2` (fighting from a grapple is clumsy).
- **Movement**: `speed_mult: 0.0` until escape.
- **Periodic**: none.
- **Lifecycle**: `stack: "noop"` (can't re-grab someone already grappled). `default_duration: None` (persistent). Ends on `escape` (victim breaks free) or `grappler_incapacitated` (the grappler is knocked out/dies, releasing the hold).

## Perception

`known: True` but in `_PERCEPTION_SKIP` — not rendered as a symptom line.

## Integration points

- `player.py:81-90` — catalog entry.
- `engine/conditions.py` — speed, combat mods, `_PERCEPTION_SKIP`.
- Grapple/restrain system (task-4 done) that applies/removes it.
- `end_instances("escape")` and grappler-incapacitation wiring to auto-release.

## Testing

- [ ] Grappled: speed 0, cannot act/move.
- [ ] Escape ends only that instance.
- [ ] Grappler incapacitated/dead releases the hold.
- [ ] `attack_mod -2` while grappled.

## Open questions / things to work out

- How is `grappler_incapacitated` triggered reliably (event when the source goes down)?
- Is the grappler tracked in `source`, and does `source_type: "character"` gate anything?
