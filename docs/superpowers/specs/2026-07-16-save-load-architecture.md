# Save/Load Architecture

**Date**: 2026-07-16
**Status**: Draft

## Summary

Separate runtime saves from scenario templates. Two save types:

1. **Save Game** — full runtime snapshot to `saves/` directory (resume progress)
2. **Save Scenario** — authorial content back to the source scenario file (preserve world-building)

## Data Model

### Save Game (`saves/<name>_<timestamp>.json`)

Full `VirtualWorld.to_dict()` output (minus the removed `player` duplicate field).
Contains everything: graph, players with all runtime state, lore, time, logs.

### Save Scenario (source scenario file)

Authorial content only. Same as `to_dict()` but strips clearly transient artifacts:

| Preserved (author may set these) | Stripped (play artifacts only) |
|---|---|
| graph (areas, items, ways, edges) | game_log |
| world_lore | turn_events |
| player vitals (custom starting HP etc.) | recent_hearing (per player) |
| player emotion | speech_log |
| player memories (starting lore dumps) | |
| player inventory (start with items) | |
| player state (start unconscious) | |
| player stats/skills/traits/personality | |
| time_ticks, turn_number (start at dawn) | |
| clock settings, ways, item_registry | |
| ghost_mode, narration_mode | |

## Files

### Backend

| File | Change |
|---|---|
| `virtual_world_engine.py` | Add `_scenario_source` field. Add `to_scenario_dict()` method that returns `to_dict()` minus transient fields. |
| `app.py` | Rename `_save_world_template` -> `_save_scenario`. Lore endpoints call `_save_scenario`. Add save game CRUD endpoints. Add save-scenario endpoint. Auto-detect source on startup. |

### Frontend

| File | Change |
|---|---|
| `static/js/api.js` | Add `saveGame()`, `loadGame()`, `listSaveGames()`, `deleteSaveGame()`, `saveScenario()` |
| `static/js/main.js` | Wire toolbar buttons for save/load scenario and save/load game |
| `static/js/inspector.js` or new widget | Load Game modal — list saves, click to load, delete |

## API Endpoints

### Save Game CRUD

```
GET  /api/save-games              → [{name, scenario, timestamp, tick, turn, player}, ...]
POST /api/save-game               body: {name?: string} → saves to saves/<name>_<ts>.json
POST /api/load-game/<filename>    loads save file, replaces world state
DELETE /api/save-game/<filename>  deletes a save file
```

### Scenario Save

```
POST /api/save-scenario           writes clean scenario data to source file
```

## Implementation Order

1. Rename `_save_world_template` -> `_save_scenario` in app.py; update lore endpoints
2. Add `to_scenario_dict()` to engine
3. Add `_scenario_source` tracking to engine + app startup
4. Add save game CRUD backend endpoints
5. Add frontend API methods
6. Add toolbar buttons + Load Game modal
