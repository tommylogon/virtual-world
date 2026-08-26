---
group: Equipment & Inventory
wiki: "[[Items & Inventory/Items Overview]]"
---

# Design: Route Food Items to "eat" Action Instead of Generic "use"

**Filed**: 2026-07-15 → **Implemented**: 2026-07-20
**Priority**: Medium
**Status**: ✅ Implemented — see `review/`

---

## Summary

Food items (tagged with `food`, `consumable`, etc.) previously worked through the generic `use` command. Now they have dedicated `eat_item()` and `drink_item()` processing paths that fire `on_eat`/`on_drink` triggers exclusively — no `on_use` fallback.

## What Was Already Done

- `TRIGGER_TYPES` in both engine and frontend already included `on_eat` and `on_drink`
- `ACTION_OPTIONS` and UI already included `eat` and `drink` actions
- `world_template.json` already had food items with `on_eat`/`on_drink` trigger nodes
- `app.py` already had `eat`/`drink` command handlers (but routed to `use_item()`)

## What Changed

### `virtual_world_engine.py`

1. **Added `eat_item(item_name)`** — public method that fires only `on_eat` triggers
2. **Added `drink_item(item_name)`** — public method that fires only `on_drink` triggers
3. **Added `_consume_item(item_name, trigger_type, action_verb)`** — shared internal implementation for both eat/drink:
   - Ghost check with proper action type ("eat"/"drink")
   - Item lookup and state validation
   - Action validation (`"eat" in actions or "food" in tags` / `"drink" in actions or "drink" in tags`)
   - Exhaustion reset on successful consumption
   - **No `on_use` fallback** — fires only the specified trigger type
   - Skill check support
   - Action costs (item-specific `action_costs.eat`/`action_costs.drink`, falling back to `ACTION_COSTS["use"]`)
   - Legacy effects (vital adjustments, environment changes)
   - Consumable decrement (uses tracking)
   - Turn event recording with correct verb (ate/drank)
4. **Refactored `use_item()`** — simplified to handle only `"use"` action; eat/drink validation logic moved to `_consume_item()`
5. **Updated `_check_ghost_action()`** — added `"eat"` and `"drink"` to `physical_actions` list so ghosts can't eat/drink without a Perception check

### `app.py`

- `eat` command now routes to `world.eat_item(item_name)` instead of `world.use_item(item_name, trigger_type="on_eat")`
- `drink` command now routes to `world.drink_item(item_name)` instead of `world.use_item(item_name, trigger_type="on_drink")`

### `static/js/item-library.js`

- ✅ No changes needed — `on_eat` and `on_drink` were already in `TRIGGER_TYPES`

## How to Test

1. Start server: `python app.py`
2. In a game with food items:
   - `take apple` then `eat apple` → should fire `on_eat` triggers ("Cruncy and delicious"), NOT `on_use`
   - `take water_pitcher` then `drink water_pitcher` → should fire `on_drink` triggers ("the cool water quences your thirst"), NOT `on_use`
   - `use apple` → should fire ONLY `on_use` triggers (no food messages from `on_eat`)
   - `eat` a non-food item → should show contextual failure ("I pause — that's not food.")
3. Verify existing food items still work via `eat` command

## Key Design Decisions

- **Option B (proper separation)** chosen over Options A and C
- `on_eat` and `on_drink` triggers fire exclusively — no `on_use` fallback
- This means food items won't trigger traps that listen for `on_use`
- Items can have BOTH `"use"` and `"eat"` in their actions list for dual functionality
- The `_consume_item()` internal method shares ~90% of the logic with `use_item()` without duplicating code

## Files Changed

- `virtual_world_engine.py` — added `eat_item()`, `drink_item()`, `_consume_item()`; updated `_check_ghost_action()`, streamlined `use_item()`
- `app.py` — routing `eat`/`drink` to new methods
- `static/js/item-library.js` — no changes needed (already had trigger types)
