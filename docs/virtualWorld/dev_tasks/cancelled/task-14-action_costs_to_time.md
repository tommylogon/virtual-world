# Action Costs to Time

**Filed**: 2026-07-15
**Priority**: Low
**Status**: Draft / Not Started

---

## Summary

Actions currently cost energy and ticks uniformly. Different actions should take different amounts of game time: walking through a door might take 1 time unit, walking up a long staircase might take 5, examining an item might take 0 (free action).

## Current State

### Action cost system (`virtual_world_engine.py:68`)

```python
BASE_ACTION_COSTS = {
    "look": {"time": 1, "energy": 0},
    "move": {"time": 2, "energy": 3},
    "use": {"time": 2, "energy": 3},
    "take": {"time": 1, "energy": 2},
    "drop": {"time": 1, "energy": 1},
    "examine": {"time": 1, "energy": 0},
    "speak": {"time": 1, "energy": 0},
    "attack": {"time": 3, "energy": 8},
    "rest": {"time": 5, "energy": -15},
}
```

These are fixed for all uses of the action type. A "move" always costs 2 time, whether walking through a door or climbing a long staircase.

### `apply_action()` (`virtual_world_engine.py`)

```python
def apply_action(self, action_type, cost_override=None, player=None):
    cost = cost_override or self.BASE_ACTION_COSTS.get(action_type, {})
    time_cost = cost.get("time", 1)
    energy_cost = cost.get("energy", 0)
    # ... applies costs
```

## Proposed Design

### Per-door time costs

Add a `time_cost` property to door nodes:

```json
{
  "id": "door_stairs",
  "type": "door",
  "properties": {
    "time_cost": 5,
    "description": "A long winding staircase"
  }
}
```

When a player moves through this door, the time cost overrides the default.

### Per-action item costs

The existing `action_costs` property on items already supports per-action stat costs. Extend this to include time:

```json
{
  "action_costs": {
    "use": {"Energy": 5, "time": 3},
    "examine": {"Energy": 0, "time": 1}
  }
}
```

### Per-action type config

Allow the engine to differentiate time costs per action variant:
- `move door`: base 2
- `move stairs`: 5 (from door property)
- `move across room`: 1

### Time vs Ticks

Currently "time" IS ticks (each action advances the game clock). The time cost determines how many game-minutes pass. The distinction is:
- **Time cost**: game minutes that pass
- **Tick**: one unit of simulation (might be multiple actions)

For now, leave this as-is. Time cost = game minutes consumed.

## Audit

**Status**: Partially implemented — items have `action_costs`, doors lack `time_cost`
**Evidence**:
- **Items ✅**: `action_costs` dict supported in frontend (`inspector.js:689-721` cost grid for Energy/Hunger/Thirst/HP) and engine (`apply_action()` at line 2520 reads `cost.get("time")` per-action)
- **Doors ❌**: No `time_cost` property on door nodes, no UI field in door inspector (`inspector.js:1543-1673`), no engine code to read per-door time cost override
- **Time not in cost grid ❌**: The Action Costs UI (`inspector.js:694`) only shows Energy/Hunger/Thirst/HP — `time` is not editable per-item even though the engine supports it
**How to test**: Open an item's inspector, scroll to "Action Costs" — grid shows Energy/Hunger/Thirst/HP per action. Open a door inspector — no time_cost field exists.

## Cancellation Reason

**Cancelled 2026-07-20**: Variable per-action time costs don't fit the turn-based architecture. All actions happen within a single configurable turn duration (default 5 min). Time only advances on turn boundaries — individual actions can't consume time independently without breaking the multi-character sequential-action model. Action costs are now handled via the trigger system instead.

## Files Affected

- `virtual_world_engine.py` — check door/item for time_cost overrides in `apply_action()`
