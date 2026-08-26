---
group: Conditions
---

# Condition: Exhausted (`exhausted`)

**Filed**: 2026-08-17
**Priority**: High
**Status**: In code — `player.py` `CONDITION_DEFINITIONS`
**Source**: Existing catalog

---

## Purpose

Bone-tired. Leveled (1–6) with escalating Energy drain and movement penalty; each fresh bout of exhaustion stacks a level. A core fatigue/energy feedback loop.

## Schema (catalog entry)

```python
"exhausted": {
    "name": "Exhausted", "description": "Bone-tired. Energy drains away. Each fresh bout of exhaustion stacks a level (1–6).",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": [],
    "attack_mod": 0, "defense_mod": 0, "speed_mult": 0.5,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {"Energy": -3},
    "level_periodic": {1: {"Energy": -1}, 2: {"Energy": -2}, 3: {"Energy": -3},
                       4: {"Energy": -4}, 5: {"Energy": -4}, 6: {"Energy": -4}},
    "level_speed_mult": {1: 0.5, 2: 0.5, 3: 0.25, 4: 0.25, 5: 0.1, 6: 0.0},
    "ends_on": ["rest", "sleep"],
    "known": True, "symptoms": {}, "stack": "refresh", "default_duration": 5,
    "excludes": [],
}
```

## Behavior breakdown

- **Gates**: none hard.
- **Saves/checks**: none.
- **Combat**: neutral mods.
- **Movement**: `speed_mult` scales with level (0.5 → 0.0 at level 6). Dash blocked when `effective_speed < 0.5`; movement blocked at `<= 0` (exhaustion level 6).
- **Periodic**: Energy drain scales by level via `level_periodic` (L1 −1 → L3 −3 → L6 −4). `effective_periodic_for` resolves level-scaled before catalog default.
- **Lifecycle**: `stack: "refresh"` — re-exhaustion bumps `level` toward 6 and refreshes the timer. `default_duration: 5`. Ends on `rest`/`sleep`.

## Perception

`known: True` — self-evident.

## Integration points

- `player.py:121-134` — catalog entry (leveled via `level_periodic`/`level_speed_mult`).
- `engine/conditions.py` — `effective_periodic_for`, `effective_speed_mult`, `effective_speed`, `symptom_for` (level-keyed).
- `engine/activities.py` — `rest`/`sleep` clear exhaustion.
- `engine/movement.py` — dash/movement gating at low `effective_speed`.
- Energy collapse → may trigger `unconscious`.

## Testing

- [ ] Re-exhaustion bumps level (1→2→…→6), not a new instance.
- [ ] Drain scales with level (L1 −1, L3 −3, L6 −4).
- [ ] Dash blocked below speed 0.5; movement blocked at level 6.
- [ ] `rest`/`sleep` clears the condition.

## Open questions / things to work out

- Where is the exhaustion level set from (energy threshold in `tick_manager`)?
- Does reaching level 6 collapse into `unconscious`? If so, who applies that transition?
- `symptom_for` can key-off `level` for leveled diseases — do we want exhaustion symptoms by level?
