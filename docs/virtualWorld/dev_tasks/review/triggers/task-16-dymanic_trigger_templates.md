---
group: Trigger System
wiki: "[[Rules Engine/Triggers & Effects]]"
---
		
# Dynamic Trigger Templates — Variable Substitution in Trigger Messages

**Filed**: 2026-07-17 (completed 2026-07-21)
**Priority**: Low
**Status**: ✅ Complete — implemented as part of task-21 (item parameters system)

---

## Summary

Trigger messages support `{variable_name}` template substitution referencing game state, item properties, player stats, and environment data. Fully implemented in engine.

## What Was Implemented

### 1. `_render_template(text, context)` — `virtual_world_engine.py:4474`

Replaces `{variable}` placeholders from context dict. Supports three patterns:
- `{variable_name}` — direct lookup in context dict
- `{param:<key>}` — lookup in `context['item_params']` (custom parameters)
- `{prop:<key>}` — lookup in `context['item_properties']`

Unrecognized variables are left unchanged in the output.

### 2. Context building in `_execute_triggers()` — `virtual_world_engine.py:1376`

Context dict built once per trigger execution with all available variables:

| Variable | Source |
|----------|--------|
| `{game_time}` | `world.get_current_time()` |
| `{time_ticks}` | `world.time_ticks` |
| `{turn_number}` | `world.turn_number` |
| `{player_name}` | `world.active_player` |
| `{area_name}` | `world.current_area.name` |
| `{item_name}` | trigger source item name |
| `{item_state}` | source item `current_state` |
| `{item_description}` | source item `description` |
| `{target_name}` | target of `on_use_on` |
| `{player_hp}` | player's HP vital |
| `{player_energy}` | player's Energy vital |
| `{player_sanity}` | player's Sanity vital |
| `{area_light}` | room light level |
| `{area_temp}` | room temperature |
| `{area_smell}` | room smell |
| `{prop:<key>}` | any property on the source item |
| `{param:<key>}` | custom parameters on the item |

### 3. Wired to all trigger message outputs

`_render_template()` is called for every trigger message, failure message, and description update across all effect types.

## Example Usage

A grandfather clock's `on_examine` trigger message:
```
The clock reads: {game_time}. The pendulum swings steadily.
```
→ "The clock reads: 14:32:00. The pendulum swings steadily."

A container with custom params:
```
{param:content_type} — {param:quantity} remaining
```
→ "Gold Coins — 5 remaining"

## Files Changed

- `virtual_world_engine.py` — `_render_template()` method, context expansion in `_execute_triggers()`