---
group: Conditions
---

# Condition: Hypothermia (`hypothermia`)

**Filed**: 2026-08-17
**Priority**: Medium
**Status**: Planned â€” task-190 (More Conditions)
**Source**: Proposed (not yet in `player.py`)

---

## Purpose

Dangerous cold â€” the body's temperature drops. Built from the sickness family: escalating, symptom-driven, drains vitals, becomes lethal if untreated. Closely tied to `wet` and the temperature/insulation system.

## Proposed schema

```python
"hypothermia": {
    "name": "Hypothermia", "description": "Your body is dangerously cold.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": [],
    "attack_mod": -1, "defense_mod": 0, "speed_mult": 0.9,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {"Energy": -2, "HP": -1},   # escalate with level
    "level_periodic": {
        1: {"Energy": -2},
        2: {"Energy": -3, "HP": -1},
        3: {"Energy": -4, "HP": -3},
    },
    "level_speed_mult": {1: 0.9, 2: 0.7, 3: 0.3},
    "ends_on": ["warm", "shelter", "remove_wet_clothes"],
    "known": True, "symptoms": {
        1: "A deep chill you can't shake.",
        2: "Shivering wracks you and your fingers go numb.",
        3: "Warmth feels like a distant memory. A grey haze edges your vision.",
    },
    "stack": "refresh",   # continued exposure escalates level toward 3
    "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown (proposed)

- **Gates**: none hard until severe.
- **Saves/checks**: possibly auto-fail DEX (trembling) at high level.
- **Combat**: shrinking `attack_mod`, `defense_mod` as cognition/motor fail.
- **Movement**: `level_speed_mult` drops with severity (0.9 â†’ 0.3).
- **Periodic**: escalating Energy + HP drain (level-scaled, like `exhausted`).
- **Onset & driver**: temperature system â†’ once body temp crosses a threshold, apply `hypothermia`; `wet` accelerates it; insulation/warmth (fire, shelter, dry clothes) reverses it toward `ends_on: ["warm"]`.
- **Lifecycle**: `stack: "refresh"` â€” sustained cold bumps level toward 3; ends on warming up / shelter / removing wet clothes. `default_duration: None` (persistent until warmed).

## Perception

`known: True` â€” symptom scaling with severity.

## Integration points space

- `engine/player.py` â€” `CONDITION_DEFINITIONS` entry (leverage `level_periodic`/`level_speed_mult`).
- Temperature/insulation system â€” the driver (see `task-215 environmental-clothing-effects`, `wet`, environment temperature).
- `engine/movement.py` â€” severe-speed gating.
- Warming actions: fire near, shelter, dry clothes, hot food.
- Sickness family: reuse the `sick` composition/disease pattern per task-190 ("a sickness condition built from the sickness family").

## Testing (proposed)

- [ ] Cold exposure builds `hypothermia`; `wet` accelerates onset.
- [ ] Level escalation under sustained cold; drains/speed scale.
- [ ] Warming (fire, shelter, dry clothes) ends it; level drops on partial warmth.
- [ ] Unchecked severe hypothermia can collapse the character (HP 0 â†’ unconscious/dead).
- [ ] Interaction: wet clothing worsens onset; dry clothing/insulation delays it.

## Open questions / things to work out

- What is the body/temperature model that decides **when** hypothermia applies (needs the temperature/insulation system up first, ties to `wet`)?
- Separate mild "chilled" â†’ `hypothermia`, or all one condition with levels?
- Recovery speed and whether a heat source is required vs. gradual outdoor warming.
- Composition with `unconscious` at severe level (collapse) â€” who applies it?

