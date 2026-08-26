---
group: Conditions
---

# Condition: Sensitized (`sensitized`)

**Filed**: 2026-08-17
**Priority**: Medium
**Status**: Planned — task-209 (Arousal State Conditions & Threshold Triggers)
**Source**: Proposed (not yet in `player.py`)

---

## Purpose

The edging stack. Repeated stimulation near the edge makes the character progressively more sensitive — every touch hits harder. Stacks by design.

## Proposed schema

```python
"sensitized": {
    "name": "Sensitized", "description": "Your skin is raw with wanting. Every touch echoes.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": ["concentration"],
    "auto_fail_saves": [],
    "attack_mod": -1, "defense_mod": -1, "speed_mult": 0.95,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {"Stimulation": 1},   # escalating per stack level
    "level_periodic": {
        1: {"Stimulation": 1},
        2: {"Stimulation": 2},
        3: {"Stimulation": 3},
    },
    "ends_on": ["release", "rest"],
    "known": True,
    "symptoms": {
        1: "A lingering ache of want.",
        2: "Needier than before. Tingling and raw.",
        3: "Barely contained. Any touch is electric.",
    },
    "stack": "accumulate",   # the edging stack — each edge-approach adds a level
    "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown (proposed)

- **Gates**: none hard.
- **Saves/checks**: auto-fails `concentration` (distracting need).
- **Combat**: light `attack_mod`/`defense_mod −1` and slight speed dip — distractible.
- **Periodic**: escalating `Stimulation` feed by stack level (via `level_periodic`).
- **Lifecycle**: `stack: "accumulate"` — the whole point is that edging **stacks** sensitivity. Ends on release or rest (dropping off once the edge resolves).

## Perception

`known: True` — self-evident, escalating symptoms.

## Integration points space

- `engine/player.py` — `CONDITION_DEFINITIONS` entry (leverage `level_periodic`/`level_speed_mult`).
- `engine/conditions.py` — `process_tick`, symptoms.
- Edging/closeness mechanics (task-208 release-edging-friction, task-94 closeness-as-behavioral-gate).
- Release/climax clears the stack and typically hands off to `satisfied`.

## Testing (proposed)

- [ ] Repeated edge-approaches raise the stack level (accumulate, not noop).
- [ ] Stimulation feed scales with level.
- [ ] Concentration checks auto-fail; light combat mods.
- [ ] Release/rest clears the stack.

## Open questions / things to work out

- Exact accumulation trigger: does reaching a closeness threshold once bump the level, or per tick in the edge zone (task-208 friction)?
- Cap — is there a maximum stack (e.g. level 3) before forced release/overstimulation (`overstimulated` interplay)?
- Does high `sensitized` push toward `frantic` or `overstimulated`? (Sensitivity feeding either is a design lever.)
