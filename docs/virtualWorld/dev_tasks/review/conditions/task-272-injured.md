---
group: Conditions
---

# Condition: Injured (`injured`)

**Filed**: 2026-08-17
**Priority**: High
**Status**: Planned â€” task-190 (More Conditions) + task-253 (body-part targeted injuries)
**Source**: Proposed (not yet in `player.py`)

---

## Purpose

A wounded body part (light/moderate/severe). Uses `level` for severity and `ends_on: ["fix"]` so healing removes it. Core to injury â†’ healing gameplay.

## Proposed schema

```python
"injured": {
    "name": "Injured", "description": "A wounded limb. Hurts and hampers you.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": [],
    "attack_mod": -1, "defense_mod": 0, "speed_mult": 0.95,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {},       # injured itself doesn't drain; bleeding does
    "ends_on": ["fix"],
    "known": True, "symptoms": {
        1: "Your wound throbs.",
        2: "The injury aches with every move.",
        3: "A deep, sharp pain radiates from the wound.",
    },
    "level_periodic": {1: {}, 2: {"Energy": -1}, 3: {"Energy": -2, "HP": -1}},
    "stack": "refresh",
    "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown (proposed)

- **Gates**: none hard, but severity should matter:
  - **light (1)**: minor mods.
  - **moderate (2)**: Energy drain, bigger attack penalty.
  - **severe (3)**: bigger drains + HP bleed; possibly restricts that body part (a severe leg injury hampers movement to near crawl).
- **Saves/checks**: maybe auto-fail physical checks tied to the injured part.
- **Combat**: `attack_mod` penalty that scales with `level` (via `level_*` fields or per-instance override).
- **Movement**: a leg injury â†’ `speed_mult`/`movement_mode` scaling; an arm injury â†’ attack/use penalties.
- **Periodic**: light healing-drag or Energy cost based on `level`.
- **Lifecycle**: `stack: "refresh"` â€” re-injuring the same part bumps level toward severe. Ends on `fix` (bandaging/healing) â€” per-instance `ends_on` (a `fix` ends only the injured instance).

## Perception

`known: True` â€” the agent knows they're hurt; `symptoms` scale with severity.

## Integration points space

- `engine/player.py` â€” `CONDITION_DEFINITIONS` entry (leverage `level_periodic`, `level_speed_mult` like `exhausted`).
- Tie to **body-part targets** (task-253: body-part targeted injuries) â€” the injury should reference which part.
- `engine/movement.py` â€” leg-injury movement gating.
- Healing: `ends_on: ["fix"]` wired to bandage/heal actions and the `end_condition` effect.

## Testing (proposed)

- [ ] Injury levels 1/2/3 differ in drains, attack mods, speed.
- [ ] Re-injuring the same part scales severity, not duplicates.
- [ ] `fix` (heal/bandage) ends the instance.
- [ ] Leg injury hampers movement; arm injury hampers attack/use.

## Open questions / things to work out

- Body-part registry: does the injury track a specific part (source/part field), and which actions/checks that part gates?
- Relationship to **bleeding**: `injured` for long-term healing, `bleeding` for acute HP loss, or combined?
- Is "severe injury" just a high `level`, or a separate condition (e.g. a broken bone â†’ `prone` with `ends_on: ["fix"]`)?
- `speed_mult 0.95` baseline vs. level-scaled â€” decide.

