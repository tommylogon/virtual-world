# Conditions System (Character Status Effects)

**Filed**: 2026-07-15
**Priority**: High
**Status**: Done — merged into commit 8e6ad9f (2026-07-22)

---

## Summary

Characters need a proper conditions/status effects system. Currently states are limited to: awake, sleeping, dead, unconscious. A conditions system should support: awake, dead, asleep, unconscious, paralysed, blind, deaf, sick, poisoned, grappled, restrained — where multiple conditions can apply simultaneously with independent effects.

## Current State

### Player state (`player.py`)

```python
self.state = "awake"  # single string, one at a time
```

States are mutually exclusive. A character cannot be simultaneously "sleeping" and "poisoned" — the state system doesn't support this.

### State-based restrictions (`virtual_world_engine.py`)

Various actions check `self.player.state`:
```python
if self.player.state in ["sleeping", "unconscious", "bound"]:
    raise ValueError("You can't use items while ...")
```

## Proposed Design

### Conditions set

Replace single `state` string with a set of conditions:

```python
self.conditions = {"awake"}  # set of strings, multiple can apply
```

### Predefined conditions

| Condition | Effect | Removes |
|-----------|--------|---------|
| awake | Normal state | asleep, unconscious |
| asleep | Can't act, recovery | takes damage, noise |
| unconscious | Can't act, no recovery | time, healing |
| dead | Perma-death | everything |
| paralysed | Can't move | time, healing |
| blind | Can't see | time, healing |
| deaf | Can't hear | time, healing |
| sick | Vitals decay faster | medicine |
| poisoned | HP drain over time | antidote |
| grappled | Can't move away | break free action |
| restrained | Can't use items | break free action |

### Condition rules

- Multiple conditions can coexist ("poisoned" + "blind" + "restrained")
- Some conditions are mutually exclusive (can't be "awake" and "asleep")
- Each condition can have a timer that auto-removes it
- Each condition can have periodic effects (poisoned → -2 HP per tick)
- Conditions can be inflicted by item effects, environment, NPC actions
- Conditions can be cured by items, rest, time, or specific actions

### Implementation

1. Player state becomes `self.conditions = {"awake"}`
2. Engine checks `"asleep" in self.conditions` instead of `self.state == "sleeping"`
3. Add condition effects to the trigger system:
   - New effect: `apply_condition` (applies "poisoned" for N ticks)
   - New effect: `remove_condition` (removes "poisoned")
   - New condition type: `has_condition` (check if character has condition)
4. Add periodic condition processing in engine tick
5. Add UI display in agent inspector (show all active conditions)

### Frontend

In agent inspector, show conditions as labeled badges:

```
[Awake] [Poisoned ⏱ 5 turns] [Blind ⏱ 3 turns]
```

Click to inspect condition details. Show condition source and remaining duration.

## Files Affected

- `player.py` — replace `state` with `conditions` set
- `virtual_world_engine.py` — update all state checks, add condition processing, add trigger effects
- `static/js/inspector.js` — display conditions in agent inspector
- `static/js/api.js` — condition update API

## Implementation

### Engine
- **`player.py`**: `state` replaced with `conditions` set. Backward-compatible `state` property.
- **`engine/conditions.py`**: `ConditionsSystem` with `apply_condition`, `remove_condition`, `has_condition`, `can_act`, `process_tick()`.
- **`engine/effects.py`**: `handle_apply_condition`, `handle_remove_condition` effect handlers.
- **`engine/trigger_system.py`**: `apply_condition`, `remove_condition` in EFFECT_TYPES.
- **`engine/tick_manager.py`**: `conditions.process_tick()` called each cycle. Periodic poison/sick/exhausted effects applied.
- **Constants**: `CONDITION_HIERARCHY`, `BLOCKING_CONDITIONS`, `PERIODIC_CONDITIONS`, `CONDITION_EXCLUSIONS`, `CONDITION_DEFAULT_TIMERS` in `player.py`.

### Frontend
- **`static/js/inspector/agent-view.js`**: Condition badges in status row with per-condition colors.

### Tests
- **`tests/test_conditions.py`**: 38 tests covering hierarchy, exclusions, periodic effects, timers, emotions, backward-compat state, serialization.
