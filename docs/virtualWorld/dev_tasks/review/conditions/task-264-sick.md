---
group: Conditions
---

# Condition: Sick (`sick`)

**Filed**: 2026-08-17
**Priority**: High
**Status**: In code — `player.py` `CONDITION_DEFINITIONS`
**Source**: Existing catalog

---

## Purpose

Generic illness. Hunger and thirst worsen over time. The canonical hidden (`known: False`) symptom-driven condition, and the building block for diseases/contagion.

## Schema (catalog entry)

```python
"sick": {
    "name": "Sick", "description": "Ill. Hunger and thirst worsen.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": [],
    "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {"Hunger": -2, "Thirst": -2}, "ends_on": ["duration", "cure"],
    "known": False, "stack": "accumulate", "default_duration": 8,
    "symptoms": {
        5: "You feel a little off.",
        3: "You ache and your stomach churns.",
        1: "Feverish and weak. You need to lie down.",
    },
    "excludes": [],
}
```

## Behavior breakdown

- **Gates**: none hard.
- **Saves/checks**: none.
- **Combat**: neutral.
- **Movement**: full speed.
- **Periodic**: `Hunger -2`, `Thirst -2` per tick (summed across instances — multiple sick exposures stack drains).
- **Lifecycle**: `stack: "accumulate"` — re-exposure appends a new instance (drains sum). `default_duration: 8`. Ends on `duration` (each instance ticks out) or `cure`.
- **Hidden/unknown**: `known: False` — the agent only ever sees `symptoms`, never the raw `sick` id.

## Perception

`known: False` → symptom-driven. `symptom_for` picks the highest threshold reached (5/3/1 ticks remaining): "feel a little off" → "ache and stomach churns" → "feverish and weak". A fresh dose with no threshold yet shows nothing.

## Integration points

- `player.py:135-149` — catalog entry.
- `engine/conditions.py` — `effective_symptoms`, `symptom_for`, `perceived_conditions`, `process_tick` (level/symptom resolution).
- Disease/contagion authoring (`Conditions System.md` §Diseases & Contagion): carrier items + `apply_condition sick` via `on_tick`/`on_examine`.
- Cure: `bitterweed_tonic` → `remove_condition sick`.

## Testing

- [ ] Sick drains Hunger/Thirst each tick.
- [ ] Multiple sick instances sum their drains (`accumulate`).
- [ ] Symptoms show at 5/3/1 ticks; nothing before the first threshold.
- [ ] Cure clears all `sick` instances.

## Open questions / things to work out

- Should specific diseases (flu, food poisoning) be separate conditions or instances/`source`-variants of generic `sick`? (Catalog stays small — prefer param via source/level.)
- Relationship to task-190's `hypothermia` — sickness-family reuse vs. separate condition.
