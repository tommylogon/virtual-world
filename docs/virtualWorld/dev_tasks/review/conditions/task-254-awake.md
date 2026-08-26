---
group: Conditions
---

# Condition: Awake (`awake`)

**Filed**: 2026-08-17
**Priority**: Low
**Status**: In code — `player.py` `CONDITION_DEFINITIONS`
**Source**: Existing catalog

---

## Purpose

The default resting state. Present when no other condition is active; `Player.state` reads back as `"awake"` when nothing else applies. Mostly a bookkeeping sentinel rather than a gameplay effect.

## Schema (catalog entry)

```python
"awake": {
    "name": "Awake", "description": "Conscious and alert.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": [],
    "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {}, "ends_on": [],
    "known": True, "symptoms": {}, "stack": "noop", "default_duration": None,
    "excludes": ["unconscious"],
}
```

## Behavior breakdown

- **Gates**: none (all three `blocks_*` False).
- **Saves/checks**: none autofailed.
- **Combat**: neutral (`attack_mod`/`defense_mod` 0).
- **Movement**: full speed (`speed_mult` 1.0).
- **Periodic**: none.
- **Lifecycle**: `stack: "noop"`, `default_duration: None` (persistent until replaced). Excludes `unconscious` — becoming awake clears any unconscious instance.
- **Exclusions note**: `dead` sets `excludes: []`, so applying `awake` after `dead` cannot revive a corpse; the no-conditions path re-adds `awake` when `player.conditions` empties.

## Perception

`known: True` — self-evident. Skipped by `perceived_conditions` via `_PERCEPTION_SKIP`.

## Integration points

- `player.py:31-40` — catalog entry.
- `engine/conditions.py:120` `_PERCEPTION_SKIP` — `awake` is not rendered to agents.
- `player.py` `remove_condition` (line ~507) and `process_tick` — re-add default `awake` when the last condition clears.
- Condition hierarchy order in `CONDITION_HIERARCHY` (lowest priority, listed last).

## Testing

- [ ] Clearing the last non-awake condition restores an `awake` instance.
- [ ] `Player.state` reads `"awake"` with no conditions.

## Open questions / things to work out

- Should `awake`'s `excludes: ["unconscious"]` remain, or is that the only exclusion source that matters?
