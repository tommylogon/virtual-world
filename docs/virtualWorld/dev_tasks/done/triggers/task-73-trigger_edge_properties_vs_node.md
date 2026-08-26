# Trigger Execution: Read from Node When Edge Properties Empty

**Filed**: 2026-07-19
**Priority**: High
**Status**: Done — verified 2026-08-03. Conditions/effects now fall back to the target `logic_trigger` node when the edge properties are empty (engine/trigger_system.py:1192-1201 conditions, :1212 effects), plus a singular `condition` fallback.

## Summary

`_execute_triggers()` reads trigger conditions and effects ONLY from the **edge** properties. When a trigger edge has `"properties": {}` and the actual conditions/effects are on the **target trigger node**, the trigger fires with empty defaults — producing blank output.

## Current State

`virtual_world_engine.py:1276-1287`:

```python
# Parse conditions (array or single, backward compatible)
conditions_list = trigger_edge.properties.get("conditions", None)
if conditions_list is None:
    single_cond = trigger_edge.properties.get("condition", None)
    conditions_list = [single_cond] if single_cond else []

# Parse effects (array or single, backward compatible)
effects_list = trigger_edge.properties.get("effects", None)
if effects_list is None:
    et = trigger_edge.properties.get("effect_type", "message")
    ep = trigger_edge.properties.get("effect_params", {})
    effects_list = [{"type": et, "params": dict(ep)}]
```

When the edge has `"properties": {}`:
- `conditions_list = None` → `[]` (empty = always passes)
- `effects_list = None` → `[{"type": "message", "params": {}}]` → outputs `"Something happens."`

The trigger **executes** but produces an empty message because neither conditions nor effects are found on the edge.

## Affected Triggers

Example: `world_template.json` Stone Table with Heating Rune, `on_take` trigger:

**Edge** (lines 885-887):
```json
{
    "properties": {},
    "source": "item_Stone Table with Heating Rune",
    "target": "trigger_item_Stone Table with Heating Rune_on_take_1784394461775",
    "type": "triggers"
}
```

**Target Node** (lines 5027-5048): has conditions (empty) and effects (`success_message: "The rune stops glowing when you take it."`), but these are never read.

Compare to the `on_examine` trigger edge (lines 799-824) which **does** have all properties inlined on the edge — this one works correctly.

## Fix

When edge properties are empty for conditions/effects, fall back to reading from the **target trigger node**:

```python
conditions_list = trigger_edge.properties.get("conditions", None)
if conditions_list is None:
    # Fall back to target node
    target_node = self.graph.get_node(trigger_edge.target)
    if target_node:
        conditions_list = target_node.properties.get("conditions", None)
if conditions_list is None:
    single_cond = trigger_edge.properties.get("condition", None)
    ...

effects_list = trigger_edge.properties.get("effects", None)
if effects_list is None:
    # Fall back to target node
    target_node = self.graph.get_node(trigger_edge.target)
    if target_node:
        effects_list = target_node.properties.get("effects", None)
if effects_list is None:
    et = trigger_edge.properties.get("effect_type", "message")
    ...
```

Or more cleanly: always prefer edge properties, but if both edge and node lack them, default to empty.

## Files

- `virtual_world_engine.py:1276-1287` — `_execute_triggers()`
- `world_template.json:885-887` — affected trigger edge
