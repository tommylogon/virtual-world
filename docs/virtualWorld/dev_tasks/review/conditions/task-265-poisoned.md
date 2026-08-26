---
group: Conditions
---

# Condition: Poisoned (`poisoned`)

**Filed**: 2026-08-17
**Priority**: High
**Status**: In code — `player.py` `CONDITION_DEFINITIONS`
**Source**: Existing catalog

---

## Purpose

Toxin in the blood. You're losing HP. The canonical accumulating condition (5 vials of poison = 5 instances, drains sum) and the hidden-symptom reference.

## Schema (catalog entry)

```python
"poisoned": {
    "name": "Poisoned", "description": "Toxin in the blood. You're losing HP.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": [],
    "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {"HP": -5}, "ends_on": ["duration", "antidote"],
    "known": False, "stack": "accumulate", "default_duration": 10,
    "symptoms": {
        6: "A queasy twist in your stomach.",
        3: "Cold sweat. Your gut cramps and your head swims.",
        1: "Everything spins. Your limbs feel wrong.",
    },
    "excludes": [],
}
```

## Behavior breakdown

- **Gates**: none hard.
- **Saves/checks**: none.
- **Combat**: neutral.
- **Movement**: full speed.
- **Periodic**: `HP -5` per tick per instance — **4 poisons = −20 HP/tick** (drains sum across instances).
- **Lifecycle**: `stack: "accumulate"`; `default_duration: 10`; ends on `duration` (each instance) or `antidote`.
- **Hidden/unknown**: `known: False` — agent sees symptoms only.

## Perception

`known: False` → symptom-driven at 6/3/1 ticks: "queasy twist" → "cold sweat, cramps, head swims" → "everything spins". Fresh dose shows nothing until first threshold.

## Integration points

- `player.py:150-164` — catalog entry.
- `engine/conditions.py` — `process_tick` drains summed across instances; `symptom_for`/`perceived_conditions`.
- Poison delivery: `use poison on wine` (`on_use_on`), poisonous creatures, traps.
- Antidote: `neutralizing_draught` → `remove_condition poisoned`; `ends_on: ["antidote"]`.
- Task-190 composition: poison + paralysis/unconscious/blind via parameters on an `on_eat` effect (bundled `extra_conditions`).

## Testing

- [ ] Poison drains HP each tick.
- [ ] Multiple poison instances sum drains.
- [ ] Symptoms show at 6/3/1 ticks; nothing before.
- [ ] Antidote clears all `poisoned` instances.

## Open questions / things to work out

- Should different poisons carry different severity (via `periodic` instance override and `level`)?
- `−5` HP/tick baseline — is that the right default vs. per-source override?
