---
group: Conditions
---

# Condition: Petrified (`petrified`)

**Filed**: 2026-08-17
**Priority**: Low
**Status**: Planned — task-190 (More Conditions)
**Source**: Proposed (not yet in `player.py`)

---

## Purpose

Turned to stone (magical). A total, deliberate incapacitation — immobile, unable to act, all STR/DEX checks fail. Usually from a magical effect (medusa-style gaze, cursed artifact), not combat.

## Proposed schema

```python
"petrified": {
    "name": "Petrified", "description": "Turned to stone. Frozen solid.",
    "blocks_actions": True, "blocks_movement": True, "blocks_speech": True,
    "auto_fail_checks": [],
    "auto_fail_saves": ["STR", "DEX", "CON"],
    "attack_mod": 0, "defense_mod": -5, "speed_mult": 0.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {},
    "ends_on": ["restore", "stone_to_flesh"],
    "known": True, "symptoms": {},
    "stack": "noop",
    "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown (proposed)

- **Gates**: `blocks_actions`/`blocks_movement`/`blocks_speech` all True — fully locked.
- **Saves/checks**: auto-fails STR/DEX/CON (you're not resisting anything as stone).
- **Combat**: `defense_mod -5` (helpless — essentially a statue target).
- **Movement**: `speed_mult 0.0`; keeps grip (items you hold are frozen onto you).
- **Periodic**: none (you don't drain as stone; you're inert).
- **Lifecycle**: `stack: "noop"`; `default_duration: None` — only a specific counter (restore / stone-to-flesh effect) ends it, per task-190 "gate conditions that block or restrict actions".

## Perception

`known: True` — observers see a statue; the character is incapacitated.

## Integration points space

- `engine/player.py` — `CONDITION_DEFINITIONS` entry (escapes creature gaze, cursed artifact triggers).
- `engine/conditions.py` — `BLOCKING_CONDITIONS`, combat mods, saves.
- Reverse: a `restore`/`stone_to_flesh` effect calling `remove_condition petrified` (see `remove_condition` effect and cure/ally-administered pattern).

## Testing (proposed)

- [ ] Petrified: no actions/movement/speech; all STR/DEX/CON saves fail.
- [ ] `defense_mod -5`, held items kept.
- [ ] Only an explicit restore/stone-to-flesh ends it (not time).
- [ ] No periodic drain (inert).

## Open questions / things to work out

- Should petrification auto-fail ALL checks/saves, or a specific subset?
- Held items: frozen onto the statue or dropped? (Proposed: kept — compare `paralysed`.)
- Does a petrified character keep their `busy`/activity state frozen, or does petrification need to clear other conditions?
- Source types (creature/artifact) and the reverse trigger — where does `stone_to_flesh` live?
