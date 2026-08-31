---
group: Conditions
---

# Condition: Bleeding (`bleeding`)

**Filed**: 2026-08-17
**Priority**: High
**Status**: Planned â€” task-190 (More Conditions)
**Source**: Proposed (not yet in `player.py`)

---

## Purpose

Actively losing HP from a wound. A periodic-drain condition whose effects leave visible marks (blood pool, blood trails) and which must be stopped by treating it.

## Proposed schema

```python
"bleeding": {
    "name": "Bleeding", "description": "You're losing blood fast.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": [],
    "attack_mod": -1, "defense_mod": 0, "speed_mult": 1.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {"HP": -3},      # escalate via level for severe hemorrhage
    "level_periodic": {1: {"HP": -2}, 2: {"HP": -3}, 3: {"HP": -5}},
    "ends_on": ["bandage", "heal", "cauterize"],
    "known": True, "symptoms": {
        1: "Your blood seeps, hot and fast.",
        2: "A red stain spreads through your clothes.",
        3: "Wetness pooling where you stand.",
    },
    "stack": "accumulate",       # multiple wounds = multiple bleeding instances, drains sum
    "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown (proposed)

- **Gates**: none hard â€” you can still act (gasping, but functional).
- **Saves/checks**: none mechanical here; prolonged blood loss drives HP toward 0.
- **Combat**: light `attack_mod` penalty from weakness.
- **Movement**: full speed (blood trail is passive, not a movement gate).
- **Periodic**: HP drain per tick per instance â€” multiple wounds sum (e.g. two wounds = âˆ’6 HP/tick). Severe hemorrhage via `level`.
- **World footprint (task-190)**: periodic symptom spawns a `blood_pool` item in the current area each tick, and a go-hook leaves blood trails behind as the character moves.
- **Lifecycle**: `stack: "accumulate"`; `default_duration: None`; ends on `bandage`/`heal`/`cauterize`.

## Perception

`known: True` â€” agent knows they're bleeding; symptoms by remaining time.

## Integration points space

- `engine/player.py` â€” `CONDITION_DEFINITIONS` entry.
- `engine/conditions.py` â€” `process_tick` drains summed across instances; blood pooling needs a **spawn hook** (new?) in tick processing or a dedicated effect.
- `engine/movement.py` â€” go-hook that drops a blood trail on each move (task-190).
- `engine/item_actions.py` â€” bandages/cauterization ending the condition.
- Item spawn: `blood_pool` node creation.

## Testing (proposed)

- [ ] Bleeding drains HP each tick; multiple instances sum.
- [ ] A `blood_pool` item appears each tick / moving leaves trails.
- [ ] `bandage`/`heal`/`cauterize` end the bleeding instance.
- [ ] Severe (`level` 3) hemorrhages drain faster.
- [ ] Bleeding alone (unchecked) can drive HP to 0 / collapse.

## Open questions / things to work out

- How are the blood-pool spawn and movement blood-trail implemented â€” new hooks in `process_tick`/movement, or scene/item triggers?
- Does bleeding coexist with `injured`, and does stopping bleeding require also treating `injured`?
- Drain balance: base `âˆ’3`/tick reasonably lethal but survivable with fast treatment.
- Should `bleeding` auto-stop when HP hits 0 (death) â€” handled by `dead` excludes or explicit logic?

