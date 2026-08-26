---
group: Items & Crafting
wiki: "[[Characters/Characters Overview]]"
---

# Character Import From Exported JSON File

**Filed**: 2026-07-17
**Priority**: Low → **Completed 2026-07-17**
**Status**: Done

---

## Summary

The character inspector has an **Export JSON** button that saves a character card (personality, stats, inventory, memories, agent history, etc.) to a `.json` file. There's no corresponding **Import** button to load that file back in.

There IS `/api/registry/characters/import` but it only imports from the saved characters registry, not from an exported JSON file. The export contains much richer data (room context, inventory, agent history, memory store, etc.) that the registry import doesn't handle.

## Changes Made

### Frontend

- **`static/js/inspector.js`**: 
  - Added "Import JSON" button in the Import/Export section of the character panel
  - Added `_importCharacter()` method: opens file picker, reads JSON, posts to `/api/players/import`, refreshes world state, opens the imported character's panel
  - Added `_saveDescription()` method for the new Appearance textarea
  - Added Appearance (description) textarea in the character inspector section

- **`static/js/api.js`**: Added `importPlayer(charData)` method that POSTs to `/api/players/import`

### Backend

- **`app.py`**: Added `POST /api/players/import` endpoint:
  - Accepts full exported character card
  - Creates or updates Player with: personality, description, stats, vitals, skills, traits, emotion, relationships, world_knowledge, behaviors, npc config, item_statuses, decay_rates
  - Handles inventory: creates graph nodes + location edges for each item, creates basic item nodes if they don't exist
  - Validates current_area exists; falls back to first available room
  - Sets as active player

- Fields SKIPPED on import: agent_history, area_description/environment/exits/items, time_ticks/game_time, memory_store

## Files Changed

- `static/js/inspector.js` — import button + `_importCharacter()`, `_saveDescription()`, Appearance textarea
- `static/js/api.js` — `importPlayer()` method
- `app.py` — `/api/players/import` endpoint