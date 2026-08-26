---
group: Conditions
---

# Condition: Satisfied (`satisfied`)

**Filed**: 2026-08-17
**Priority**: Medium
**Status**: Planned — task-209 (Arousal State Conditions & Threshold Triggers)
**Source**: Proposed (not yet in `player.py`)

---

## Purpose

The pleasant post-release state. Arousal resolves and the character is contented, calm, and (briefly) resistant to further arousal. The natural endpoint of `frantic`/`release`/climax.

## Proposed schema

```python
"satisfied": {
    "name": "Satisfied", "description": "Drained but content. A pleasant calm.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": [],
    "auto_fail_saves": [],
    "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {"Arousal": -3, "Stimulation": -2},
    "ends_on": ["rest", "new_stimulation"],
    "known": True,
    "symptoms": {
        1: "Weightless and slow. The heat has passed.",
    },
    "stack": "noop",
    "default_duration": None,
    "excludes": ["overstimulated"],
}
```

## Behavior breakdown (proposed)

- **Gates**: none.
- **Saves/checks**: none.
- **Combat**: neutral.
- **Movement**: full speed.
- **Periodic**: **drains** Arousal/Stimulation back down — the resolution to baseline. This is what pulls Arousal below the threshold bands so `aroused`/etc. clear.
- **Lifecycle**: `stack: "noop"` (already satisfied). Excludes `overstimulated` (mutually exclusive). Ends when rest resumes normal or fresh stimulation re-engages.
- **Refractory**: briefly resistant — re-arousal is slower while `satisfied` (the drain fights the re-feed).

## Perception

`known: True` — self-evident contentment.

## Integration points space

- `engine/player.py` — `CONDITION_DEFINITIONS` entry + `excludes`.
- `engine/conditions.py` — `process_tick` Arousal/Stimulation decay.
- Climax/release flow: `frantic` + release → clear arousal bands, apply `satisfied` (task-208 release/edging/friction).
- Threshold logic: `satisfied`'s drain helps drop Arousal below 15 → cleaner removal of band states.

## Testing (proposed)

- [ ] After release/climax, `satisfied` applies and arousal bands (`aroused`/etc.) clear.
- [ ] Arousal/Stimulation decay per tick toward baseline.
- [ ] Mutually exclusive with `overstimulated` (`excludes`).
- [ ] Fresh strong stimulation or rest ends it.

## Open questions / things to work out

- Refractory period: how long before the character can be re-aroused (drain rate vs. `default_duration`)?
- Should `satisfied` carry any combat/behavioral "relaxed" trait (fewer aggressive options), or stay neutral?
- Does `satisfied` interact with `overstimulated`'s exclusion both ways (overstimulated excludes satisfied)? Currently only one direction is declared.
