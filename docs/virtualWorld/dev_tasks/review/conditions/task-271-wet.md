---
group: Conditions
---

# Condition: Wet (`wet`)

**Filed**: 2026-08-17
**Priority**: Medium
**Status**: Planned â€” task-190 (More Conditions)
**Source**: Proposed (not yet in `player.py`)

---

## Purpose

Body part or garment is soaked. Feeds into the insulation/clothing math â€” a wet coat provides less insulation, and being wet accelerates chilling (hypothermia).

## Proposed schema

```python
"wet": {
    "name": "Wet", "description": "Drenched. Soaked clothing insulates far worse.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": [],
    "attack_mod": 0, "defense_mod": 0, "speed_mult": 0.9,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {"Warmth": -2},   # placeholder â€” depends on the vital/temperature design
    "ends_on": ["dry", "remove_clothes"],
    "known": True, "symptoms": {},
    "stack": "refresh",           # soaking again re-soaks, fresh shower refreshes the timer
    "default_duration": 12,
    "excludes": [],
}
```

## Behavior breakdown (proposed)

- **Gates**: none hard.
- **Saves/checks**: none by itself; may worsen cold saves.
- **Combat**: minor or no mechanical hit (keep it simple â€” wet is an environmental/thermal state).
- **Movement**: optionally slight `speed_mult` dip (soaked clothes drag) â€” verify whether desired.
- **Periodic**: thin placeholder â€” real effect is **insulation modifier** on clothing, not a direct drain. Insulation math: a wet garment's insulation value is multiplied down; wet body parts chill faster â†’ feeds `hypothermia` onset.
- **Attachment**: task-190 says "attach to an equip slot / garment" â€” this condition may need an **item/garment target**, not just players (see "killer extension": conditions could attach to items/ways/areas).
- **Lifecycle**: `stack: "refresh"` (re-soaking extends); ends on `dry` (dry near a fire/wait) or `remove_clothes` (shed the wet garment).

## Perception

`known: True` â€” the agent knows they're wet.

## Integration points space

- `engine/player.py` â€” `CONDITION_DEFINITIONS` entry.
- `engine/*` insulation/temperature math â€” wire `wet` as a multiplier on garment insulation (see `task-215 environmental-clothing-effects`).
- `engine/item_actions.py` â€” condition interactions with garments; drying clothes.
- `engine/movement.py` â€” optional speed interaction.

## Testing (proposed)

- [ ] Wet garment provides substantially less insulation than dry.
- [ ] Being wet accelerates chilling â†’ hypothermia onset faster.
- [ ] `dry` (wait near fire) and `remove_clothes` end the condition.
- [ ] Re-soaking refreshes rather than stacking duplicates.

## Open questions / things to work out

- Is `wet` per-body-part (head/torso/legs) or a single state? Task-190 says attach to equip slot/garment â€” confirm granularity.
- Which unit drives the insulation multiplier (a `Warmth`/`Temperature` vital, or garment `insulation` field)?
- Does the engine currently support conditions on **items/garments**, or is that the killer-extension work (attach target types)?
- Separate "damp" vs. "soaked" levels, or one `wet` with `level`/severity?

