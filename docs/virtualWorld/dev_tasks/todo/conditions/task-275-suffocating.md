---
group: Conditions
---

# Condition: Suffocating (`suffocating`)

**Filed**: 2026-08-17
**Priority**: Medium
**Status**: Planned — task-190 (More Conditions)
**Source**: Proposed (not yet in `player.py`)

---

## Purpose

Can't breathe — drowning, choking, airless area. A hard, urgent gate with a short lethal countdown.

## Proposed schema

```python
"suffocating": {
    "name": "Suffocating", "description": "You can't get air.",
    "blocks_actions": True, "blocks_movement": False, "blocks_speech": True,
    "auto_fail_checks": [], "auto_fail_saves": ["CON"],
    "attack_mod": 0, "defense_mod": -3, "speed_mult": 0.5,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {"HP": -4, "Energy": -3},
    "ends_on": ["breathe", "reach_air", "breath_of_air"],
    "known": True, "symptoms": {
        1: "Your chest burns. You're drowning.",
        2: "Black spots crowd your vision.",
        3: "You're going to black out.",
    },
    "stack": "noop",
    "default_duration": 4,   # short — lethal if not treated
    "excludes": [],
}
```

## Behavior breakdown (proposed)

- **Gates**: `blocks_actions: True` — you can't do much while suffocating; speech blocked (can't talk underwater). Movement stays possible (struggle toward air).
- **Saves/checks**: auto-fails CON saves.
- **Combat**: `defense_mod -3` (helpless-ish while choking).
- **Movement**: `speed_mult 0.5` (struggling).
- **Periodic**: heavy HP + Energy drain — designed **lethal quickly** if the condition isn't broken (`default_duration 4` then collapse).
- **Lifecycle**: `stack: "noop"` (already suffocating); ends on reaching air / breathing / `breath_of_air` spell or effect; otherwise the countdown runs out.

## Perception

`known: True` — agent knows they can't breathe.

## Integration points space

- `engine/player.py` — `CONDITION_DEFINITIONS` entry.
- **Air/area design** (task-130 air/vacuum area effects cancelled/considered): underwater, flooded, or airless areas apply it via triggers (`on_enter`, `on_tick`, area `air` property).
- `engine/conditions.py` — `BLOCKING_CONDITIONS` (blocks actions), `process_tick`.
- Rescue: drag to surface, `breath_of_air`-style effect ending it.

## Testing (proposed)

- [ ] Suffocating blocks actions and speech; movement (toward air) still works.
- [ ] Heavy periodic drain; short countdown → collapse if untreated.
- [ ] Reaching air / a breath effect ends it promptly.
- [ ] Applies automatically in water/airless areas (via area triggers).

## Open questions / things to work out

- What triggers it — an `air`/area property, submersion state, or gameplay items (choke hold, gas)? Tie to the air/vacuum area modeling.
- Should suffocation pause recovery/countdown while able to take a breath, or is it all-or-nothing?
- Default `4` ticks with `HP -4` — confirm lethality target (fast but survivable with prompt rescue).
- Any interactions with `wet`/`unconscious` (blacking out).
