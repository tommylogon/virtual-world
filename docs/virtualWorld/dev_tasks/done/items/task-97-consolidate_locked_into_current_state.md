---
group: Tech Debt & Testing
wiki: "[[World Building/Doors & Connections]]"
---

# Task 97: Consolidate `locked` Boolean into `current_state`

## Bug

Items had two properties expressing the same concept: `locked` (boolean) and `current_state: "locked"` (string). They could contradict each other (e.g., `desk.json` had `"locked": false` + `"current_state": "locked"`), and the boolean was what the code actually checked, making `current_state` decorative for lock behavior.

The old unlock path (`locked_with` key-matching, `locked = False`) was dead code — replaced by trigger-based unlocking.

## Changes

### `engine/item_actions.py`
- Removed dead unlock path (~lines 716-725): `properties.get("locked")` → `locked_with` match → `locked = False`
- `examine` line 81: `properties.get("locked")` → `properties.get("current_state") == "locked"`
- `examine` line 101: `not properties.get("locked")` → `properties.get("current_state") != "locked"`
- `take_item` line 264: `properties.get("locked")` → `properties.get("current_state") == "locked"`
- `drop_item` line 291: `properties.get("locked")` → `properties.get("current_state") == "locked"`

### `engine/player_manager.py`
- `find_item_node` line 143: `properties.get("locked")` → `properties.get("current_state") == "locked"`
- `find_item_node` line 154: `properties.get("locked")` → `properties.get("current_state") == "locked"`

### Frontend JS
- `item-library.js`: Removed `#lib-item-locked` checkbox, `locked:` from save payload, `locked: !!props.locked` from normalize
- `ai-generation.js`: Removed `lockedEl` checkbox sync, removed `locked (bool)` from both AI generation prompts
- `shared/ai-generator.js`: Removed `locked (bool)` from shared AI prompt
- `world-export.js`: `properties?.locked` → `properties?.current_state === 'locked'`
- `room-view.js`: `properties?.locked` → `properties?.current_state === 'locked'`
- `main.js`: Removed `"locked":false` from item format hint

### Data files
- `data/items.json`: Removed `"locked": false` from everflame_ember entry
- `data/library/items/everflame_ember.json`: Removed `"locked": false`

(desk.json and create_flame.json were already clean.)

## Verification

- [ ] No `properties.get("locked")` remains in any `.py` file under `engine/`
- [ ] No `"locked":` remains in any `.json` under `data/library/items/`
- [ ] `pytest tests/test_emote.py` passes
- [ ] Manual: examine a `current_state: "locked"` item → shows locked message, hides contents
- [ ] Manual: `use key on locked_item` → works via triggers (no longer relies on `locked_with`)
