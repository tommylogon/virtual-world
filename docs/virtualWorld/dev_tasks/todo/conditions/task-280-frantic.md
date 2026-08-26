---
group: Conditions
---

# Condition: Frantic (`frantic`)

**Filed**: 2026-08-17
**Priority**: High
**Status**: Planned — task-209 (Arousal State Conditions & Threshold Triggers)
**Source**: Proposed (not yet in `player.py`)

---

## Purpose

Peak arousal band (Arousal 90+). Overwhelming — strong Stimulation, heavy Energy and Sanity cost, big combat distraction, auto-failed self-control. Edge of composure.

## Proposed schema

```python
"frantic": {
    "name": "Frantic", "description": "Out of control. Nothing matters but this.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": ["perception", "concentration", "willpower", "self_control"],
    "auto_fail_saves": [],
    "attack_mod": -5, "defense_mod": -5, "speed_mult": 0.9,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {"Stimulation": 4, "Energy": -3, "Sanity": -2},
    "ends_on": ["release", "climax", "calm"],
    "known": True,
    "symptoms": {
        1: "You're lost in it — thought dissolving into pure, burning need.",
    },
    "stack": "refresh",
    "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown (proposed)

- **Gates**: none hard, but the mental cost is severe.
- **Saves/checks**: auto-fails `perception`, `concentration`, `willpower`, and `self_control`.
- **Combat**: `attack_mod −5`, `defense_mod −5` — very exposed.
- **Movement**: slight `speed_mult 0.9` (single-minded, less careful).
- **Periodic**: `Stimulation +4`, `Energy −3`, `Sanity −2` per tick — rapidly draining once frenzied.
- **Lifecycle**: `stack: "refresh"`. Applied at Arousal 90+. Ends on `release`/`climax` (resolves to `satisfied`) or falling below the band.

## Perception

`known: True` — unmistakable.

## Integration points space

- `engine/player.py` — `CONDITION_DEFINITIONS` entry.
- `engine/tick_manager.py` — threshold checks in `tick_turn()`.
- `engine/conditions.py` — auto-fail checks, combat mods, `process_tick`.
- Climax/release actions resolving to `satisfied` and clearing arousal conditions.

## Testing (proposed)

- [ ] Arousal 90+ → `frantic`; drops below 90 revert.
- [ ] Self-control/perception/etc. checks auto-fail.
- [ ] `attack_mod`/`defense_mod −5`.
- [ ] Stimulation +4, Energy −3, Sanity −2 per tick.
- [ ] Release/climax → `satisfied` and clears frantic + lower bands.

## Open questions / things to work out

- Is a `defense_mod −5` + heavy Sanity/Energy drain intended to be genuinely dangerous (accident/collapse risk), or just roleplay fluff?
- Does extreme arousal feed into involuntary actions (task-166) or self-control saves?
- `self_control` check pathway — ability check vs. save.
