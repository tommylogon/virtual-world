# Library Browser — Unified UI for All Entity Types

**Filed**: 2026-07-22
**Priority**: High
**Status**: Done — verified 2026-08-03. LibraryBrowser (static/js/library-browser.js:10), /api/library/entities CRUD (routes/library_routes.py:39), import character/area, per-file registry.

---

## Summary

Replaced the monolithic JSON registry files (`data/items.json` at 3819 lines, `data/characters.json`) with per-entity files under `data/library/`, and built a unified tabbed library browser UI covering Items, Characters, Rooms, Traits, Conditions, and Behaviours.

## Key Design Decisions

### Per-file library format (no inheritance)
Each entity type gets a subdirectory under `data/library/`. Each entry is its own `.json` file. No cross-file references — a character file can hold its inventory inline; a room file holds its items inline. This is NOT Unity prefabs — copies are independent after import. The "sync to library" function still works transparently.

### Unified modal, not separate modals
The old `item-library-modal` was replaced with a single `library-modal` with tab navigation. Items tab reuses the existing 961-line ItemLibrary class (AI generation, triggers, containers, placement all preserved). Other tabs have simpler list+editor patterns built into LibraryBrowser.

### Backend is generic CRUD
A single `/api/library/<type>` route handles all entity types. Import endpoints for characters and rooms create full graph nodes with inventory/items inline.

## Changes Made

### Data Migration
- **`tools/migrate_library.py`** — one-time script splitting monolithic JSONs into per-entity files
- `data/items.json` (3819 lines, 231 items) → `data/library/items/*.json` (231 files)
- `data/characters.json` (2 chars) → `data/library/characters/Miki.json`, `Kaelen Voss.json`
- Standalone files (`jake.json`, `kyrie.json`, etc.) copied to `data/library/characters/`
- `data/traits.json` (empty) → `data/library/traits/` (ready)
- New empty dirs: `data/library/rooms/`, `data/library/areas/`, `data/library/ways/`
- Scenario files (`mansion.json`, `world_template.json`) also copied to `library/rooms/`

### Backend — `routes/helpers.py`
- `load_registry(data_dir, filename)` now reads per-entity JSON files from `data/library/<type>/` instead of a single monolithic file
- `save_registry(data_dir, filename, data)` writes one file per entry, removes files for deleted keys
- All existing API endpoints (`/api/registry/items`, `/api/registry/characters`, `/api/registry/traits`) continue to work unchanged

### Backend — `routes/library_routes.py` (new)
- `GET /api/library/entities` — returns summary of all entity types and counts
- `GET/POST/DELETE /api/library/<type>` — generic CRUD for items, characters, rooms, traits, conditions, behaviours
- `POST /api/library/import/character/<id>` — imports a character from library into the world as active player, including inventory items
- `POST /api/library/import/room/<id>` — imports a room from library into the world graph, including items

### Frontend — `static/js/library-browser.js` (new)
- `LibraryBrowser` class with tab switching, list rendering, inline editors
- Items tab delegates to existing `ItemLibrary` (no duplication)
- Characters tab: list + editor (name, personality, description, behaviours, NPC config) + Import to World + Save from World
- Rooms tab: list + editor (name, description, tags, items) + Import to World
- Traits tab: list + editor (name, description, category, modifier JSON)
- Conditions tab: list + editor (name, description, duration, severity, stat effects JSON)
- Behaviours tab: list + editor (name, description, pattern, config JSON)
- Each editor generates forms dynamically from field configs

### Frontend — `static/js/api.js`
- Added `saveCharacterToRegistry()` — POST to `/api/registry/characters`
- Added `getLibraryEntities()`, `getLibraryType()`, `saveLibraryType()`, `deleteLibraryType()`
- Added `importCharacterFromLibrary()`, `importRoomFromLibrary()`

### Frontend — `templates/index.html`
- Replaced `#item-library-modal` with `#library-modal` containing tabbed panes
- Items pane keeps all legacy element IDs (`item-lib-list`, `item-lib-editor`, etc.) for backward compat
- Added script include for `library-browser.js`
- Toolbar button changed from "📚 Item Library" to "📚 Library" (opens unified browser)

### Frontend — `static/js/item-library.js`
- Updated `open()` and `close()` to reference `#library-modal` instead of `#item-library-modal`
- `open()` now calls `VW.libraryBrowser.switchTab('items')` to ensure Items tab is selected

### Frontend — `static/js/main.js`
- Added `VW.libraryBrowser` to the global namespace
- Added `openLibraryBrowser()` and `closeLibraryBrowser()` wrapper functions

### CSS — `static/css/style.css`
- Added `.lib-tab`, `.lib-tab.selected`, `.lib-tab-pane`, `.lib-tab-pane.active` styles
- Responsive: `.library-tabs` wraps on narrow screens

## UI Flow

### Opening the Library Browser
1. User clicks **📚 Library** toolbar button → `openLibraryBrowser()` → `libraryBrowser.open()`
2. LibraryBrowser calls `refreshAll()` to load all entity types from `/api/library/entities`
3. Switches to Items tab (default) → delegates to `itemLib.open()` which refreshes items data and renders the item list
4. Modal displays with 6 tabs at top: 📦 Items | 🧍 Characters | 🏠 Rooms | 🏷️ Traits | 💊 Conditions | 🤖 Behaviours

### Items Tab (existing ItemLibrary)
1. Search box filters 231 library items by name/description/tags
2. Sort dropdown: A-Z, By Type, Recent
3. Click list item → right panel shows full editor with: AI generation, name/description/tags, action checkboxes, properties (uses, weight, state, hidden, locked, equip slots), container contents editor, trigger editor (multi-effect with conditions)
4. "📌 Place in Area" button — single or multi-select placement
5. "📋 Sync to Library" — saves all world items not already in library
6. "➕ New" — creates blank item template

### Characters Tab
1. Lists 6 library characters (Miki, Kaelen Voss, jake, kyrie, kayla, sammy)
2. Click a character → editor shows: Name, Personality, Description, Default Area, Behaviours JSON, NPC Behavior dropdown, Simple NPC toggle
3. **🌍 Import to World** — prompts for target room, calls `POST /api/library/import/character/<id>` which creates a Player node, sets stats/vitals/skills/traits/personality, spawns inventory items as graph nodes with `carried_by` edges, places in room, sets as active player
4. **📤 Save from World** — prompts for which world character to save, collects full character card (personality, stats, vitals, skills, traits, inventory, emotion, memories, relationships, behaviours) and POSTs to library
5. **💾 Save to Library** — saves current editor content
6. **🗑️ Delete** — removes from library (prompts confirmation)

### Rooms Tab
1. Lists 2 room entries (mansion.json, world_template.json)
2. Click a room → editor shows: Name, Description, Tags, Item IDs
3. **🌍 Import to World** — prompts for new room name, calls `POST /api/library/import/room/<id>`, creates Area + room node, spawns referenced items from library as graph nodes with `location` edges
4. **💾 Save** / **🗑️ Delete** — standard library CRUD

### Traits Tab
1. Lists traits (empty initially — `data/library/traits/` is empty)
2. Editor: Name, Description, Category (physical/mental/social/combat/exploration/custom), Modifiers JSON
3. **💾 Save** → creates `data/library/traits/<id>.json`

### Conditions Tab
1. Lists conditions (empty initially)
2. Editor: Name, Description, Duration (ticks), Severity (1-5), Stat Effects JSON
3. **💾 Save** → creates `data/library/conditions/<id>.json`

### Behaviours Tab
1. Lists behaviours (empty initially)
2. Editor: Name, Description, Pattern (wander/still/patrol/flee/guard/follow/flee_from/investigate), Config JSON
3. **💾 Save** → creates `data/library/behaviours/<id>.json`

## Files Changed

- `tools/migrate_library.py` — new, one-time migration script
- `routes/helpers.py` — per-file load_registry/save_registry
- `routes/library_routes.py` — new, unified CRUD + import routes
- `app.py` — register library routes
- `static/js/library-browser.js` — new, LibraryBrowser class
- `static/js/api.js` — new API methods for library CRUD + import
- `static/js/item-library.js` — updated modal ID references
- `static/js/main.js` — VW namespace + global wrappers
- `templates/index.html` — tabbed library modal, updated toolbar button
- `static/css/style.css` — .lib-tab / .lib-tab-pane styles
- `data/library/` — directory structure with 231 item files, 6 character files, 2 room files

## Open Issues / Future Work

- Library browser should support drag-and-drop from library into graph canvas
- Character import currently creates item nodes from library item IDs referenced in the character's inventory — inline item data (full dicts) also supported
- Area import creates items from library item IDs — inline item dicts also supported
- Areas and Ways directories exist but have no UI tab yet — could be added when the concept is implemented
- Library entries can be bulk-imported from world via existing "Sync to Library" on items tab
- Trigger templates as a standalone library type could be useful for reusing trigger configs across items/rooms
