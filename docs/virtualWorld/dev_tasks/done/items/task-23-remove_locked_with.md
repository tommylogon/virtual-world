---
group: Items & Crafting
wiki: "[[World Building/Doors & Connections]]"
---

# Remove Legacy `locked_with` Property — Review

**Filed**: 2026-07-12 (updated 2026-07-20)
**Status**: Ready for Review
**Priority**: Low

## Changes Made

### Engine (`virtual_world_engine.py`)

- Way unlock path (`_create_locked_with_unlocks()`) is a **no-op** — door unlocking is handled entirely by triggers (`on_use_on` → `unlock_way` effect)
- The remaining `locked_with` check (`line 2563`) is for **item-to-item lockboxes** only (e.g. locked chest with a key), not ways — kept as-is because that's a separate feature

### Frontend (`inspector.js`)

- Removed the 🔑 hint badge that displayed `locked_with` on exit names in the room inspector (was display-only, now meaningless)
- Removed dead `lockedWith` variable read in door inspector (`line 1736` — declared but unused)

### Tools (`tools/game_tools.py`)

- Updated `tool_get_state` to show generic "Try using a key item on it" hint instead of checking `locked_with` property

### Not Changed

- **Scenario JSON files** (`manison2.json`, `heist.json`, `corsair.json`, `manison.json`) — still have stale `locked_with` data. Harmless, the engine ignores it. Can be cleaned up separately.
- **Item-to-item lockboxes** in engine — still uses `locked_with` for chest/container key matching. Separate feature, not related to ways.
- **Documentation** (`GAME_MECHANICS_GUIDE.md`) — still references `locked_with`. Should be updated when documentation is overhauled.

## How to Test

1. Open any room in the inspector (e.g. Living Area) — verify **no 🔑 badge** appears on locked exits
2. Open a door inspector — verify no errors in console about `lockedWith`
3. Create a trigger: `on_use_on` on a key item with `unlock_way` effect targeting a locked door — verify the door unlocks when using the key
4. Type `use brass_key on front_way` — verify it unlocks via trigger (legacy `locked_with` is not consulted)