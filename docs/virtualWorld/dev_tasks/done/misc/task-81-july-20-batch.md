# July 20 Batch — Cross-Entity Effects, Inspector UI, Item Library

## Engine (`virtual_world_engine.py`)

- Added `set_hidden` effect — `{ node_id, hidden: true/false }`
- Added `adjust_uses` effect — `{ node_id, delta: -1 }`
- Added `end_scenario` effect — sets `scenario_ended` flag, stops agent
- Added `restart_scenario` effect — sets flag, frontend auto-reloads via `/api/reset`
- Added `locked` to item state dropdown options
- `state_equals` condition checks `current_state` on trigger source node

## Inspector (`inspector.js`)

- **has_item condition**: datalist now includes world graph items + library items (was library-only)
- **Locked checkbox**: added to item Properties section (🔒)
- **Locked state**: added "locked" to item state dropdown
- **Can Unlock section**: REMOVED from both item and door inspectors (legacy unlock system)
- **`_buildUnlockHtml()`**, `_addUnlockEdge()`, `_saveUnlockEdge()`: all removed

## Item Library (`item-library.js`)

- **has_item condition**: same fix as inspector (world + library items)
- **Locked checkbox**: added to library editor
- **Place in World**: now supports containers and characters (not just areas)
- **`_pickRoom()` replaced with `_pickTarget()`**: tabbed picker (Rooms / Containers / Characters) with search
- **Button label**: "📌 Place in Area" → "📌 Place in World"

## Create Item Modal (`main.js`)

- Added **tags input field** (comma-separated)
- Tags populated from AI generation result
- Tags saved in the build item payload

## Agent Engine (`agent-engine.js`)

- **Cancel Step** button: ✕ appears when busy, interrupts LLM calls via AbortController
- **`end_scenario` / `restart_scenario` detection**: checks `worldState.data?.scenario_ended` and `_restart_requested`, auto-restarts on restart flag
- Cancel checks at 6 await points in `step()`
- **`cancel()` method**: sets flag, aborts controller, resets state

## UI (`ui-controller.js`, `index.html`)

- Cancel button (✕) in sim controls, shown when `config.busy || config.running`
- `updateButtons()` shows/hides cancel button

## API (`api.js`, `app.py`)

- `ApiClient.resetWorld()` — new method
- `ApiClient.placeItemFromLibrary()` — now accepts `{ type, name/id }` for room/container/character
- `app.py` `/api/build/item-from-library` — accepts `container`/`character` fields, creates appropriate edge
- `/api/action` and `/api/state` — now return `scenario_ended` and `_restart_requested` flags

## Graph Context Menu (`graph-manager.js`)

- Removed "🔓 Add Unlocks Edge" from item and door context menus

## Prompt Docs (`prompt-docs.js`)

- Added `set_hidden`, `adjust_uses`, `end_scenario`, `restart_scenario` docs

## Task Tracking

- **Cancelled**: task-14 (action_costs_to_time) — doesn't fit turn-based model
- **Updated**: task-15 (way_trigger_events → cross-entity trigger effects)
