---
group: Items & Crafting
wiki: "[[Items & Inventory/Items Overview]]"
---

# Item Parameters System — Dynamic Properties Displayed in Triggers

**Filed**: 2026-07-17
**Priority**: High
**Status**: ✅ Implemented

---

## Summary

Items now support dynamic template variables in trigger messages. The primary use case — grandfather clock showing current game time — is live and working.

## Engine (virtual_world_engine.py)

Task 16 (`_render_template()`) was already fully implemented. The engine already had:

- **`_render_template(text, context)`** at line 4236 — replaces `{variable}` placeholders from context dict, plus `{param:<key>}` for item parameters
- **Context building** in `_execute_triggers()` at line 1338 — already included `game_time`, `player_name`, `area_name`, `item_name`, `item_state`, `time_ticks`, `turn_number`, `player_hp`, `player_energy`, `player_sanity`, `area_light`, `area_temp`, `area_smell`

**What was added to the engine:**

1. **`item_description`** — added to context at line 1348
2. **`item_params`** — added to context at line 1351-1352, reads `item_node.properties.parameters` dict. This enables `{param:<key>}` syntax in trigger messages (e.g., `{param:format}`).

The `{param:<key>}` pattern is handled by `_render_template()`'s regex substitution: `re.sub(r"\{param:(\w+)\}", ...)` looks up the key in `context["item_params"]`.

## Template (world_template.json)

Both the **trigger edge** (line 141) and the **trigger node** (line 6393) for the grandfather clock's `on_examine` trigger were updated from:
```
"The clock reads 08:15. Through the glass you can see a small brass key..."
```
to:
```
"The clock reads {game_time}. Through the glass you can see a small brass key..."
```

The library entry in `data/items.json` was also updated.

## Inspector UI (static/js/inspector.js)

Added a **"Parameters" section** to the item inspector (`_showItem()`) with:
- Key-value pair list with inline editing
- Add/delete buttons
- Helper methods: `_addParam`, `_removeParam`, `_updateParamKey`, `_updateParamValue`

Parameters are stored in node properties as `{"parameters": {"key1": "value1", "key2": "value2"}}` and saved via the existing `api.updateNode()` endpoint.

## Files Changed

| File | Change |
|------|--------|
| `virtual_world_engine.py` | Added `item_params` and `item_description` to trigger context |
| `world_template.json` | Updated clock trigger message to use `{game_time}` (edge + node) |
| `data/items.json` | Updated library entry clock trigger message to use `{game_time}` |
| `static/js/inspector.js` | Added Parameters UI section + 4 helper methods |

## How to Test

1. Start the server (`python app.py`)
2. Examine the grandfather clock in-game: `examine grandfather_clock`
3. The output should show the current game time (e.g., "The clock reads 08:15:00...") instead of a hardcoded "08:15"
4. Open the Inspector panel and click on the grandfather clock node
5. Scroll to the "Parameters" section to see/edit key-value pairs
6. Add a parameter like `chime: bong` — it becomes accessible via `{param:chime}` in trigger messages

## Available Template Variables

| Variable | Description |
|----------|-------------|
| `{game_time}` | Current in-game time (HH:MM:SS) |
| `{player_name}` | Active player's name |
| `{area_name}` | Current room name |
| `{item_name}` | Item being examined/used |
| `{item_description}` | Item's description |
| `{item_state}` | Item's current_state |
| `{player_hp}` | Player's HP |
| `{player_energy}` | Player's energy |
| `{player_sanity}` | Player's sanity |
| `{area_light}` | Area light level |
| `{area_temp}` | Area temperature |
| `{area_smell}` | Area smell |
| `{time_ticks}` | Total game ticks |
| `{turn_number}` | Current turn number |
| `{param:<key>}` | Custom parameter from item's `parameters` property |

## Note

No new API endpoints were needed — the existing `api.updateNode()` (which calls `PATCH /api/graph/node/{id}`) already supports updating arbitrary node properties, including `parameters`.