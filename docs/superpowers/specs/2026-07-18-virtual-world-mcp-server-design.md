# Virtual World MCP Server — Design Spec

## Architecture

A FastMCP server that proxies commands to an already-running VirtualWorld Flask server via HTTP.

```
┌──────────────┐     MCP Proto     ┌─────────────────┐     HTTP/JSON     ┌──────────────────┐
│   MCP Client  │◄─────────────────►│  mcp_server.py   │◄────────────────►│  Flask App        │
│ (OpenCode,    │                    │  (FastMCP 2.x)   │                    │  (port 4444)      │
│  Claude, etc) │                    │  httpx client    │                    │  VirtualWorld     │
└──────────────┘                    └─────────────────┘                    └──────────────────┘
```

## Files

- `mcp_server.py` — single file, entry point, ~600-800 lines
- `.opencode/mcp.json` (or user's MCP client config) — registration snippet

## Configuration

| Env Var | Default | Description |
|---|---|---|
| `VIRTUAL_WORLD_URL` | `http://localhost:4444` | Flask server base URL |
| `VIRTUAL_WORLD_TIMEOUT` | `30` | HTTP request timeout in seconds |

## Tool Reference

### 1. Core Commands (Action Wrappers)

All call `POST /api/action` with `{"command": "<cmd>"}`.

| Tool | Params | Command |
|---|---|---|
| `look()` | none | `look` |
| `go(direction)` | `direction: str` | `go {direction}` |
| `take(item_name)` | `item_name: str` | `take {item_name}` |
| `drop(item_name)` | `item_name: str` | `drop {item_name}` |
| `use(item_name, target?)` | `item_name: str, target: str = ""` | `use {item_name} [on {target}]` |
| `examine(target)` | `target: str` | `examine {target}` |
| `inventory()` | none | `i` |
| `stats()` | none | `stats` |
| `speak(text)` | `text: str` | `say {text}` |
| `attack(target)` | `target: str` | `attack {target}` |
| `rest(minutes)` | `minutes: int = 10` | `rest {minutes}` |
| `open_door(door)` | `door: str` | `open {door}` |
| `close_door(door)` | `door: str` | `close {door}` |
| `toggle(item_name)` | `item_name: str` | `toggle {item_name}` |

### 2. World State

| Tool | Params | Endpoint |
|---|---|---|
| `get_state()` | none | `GET /api/state` |
| `get_graph_nodes()` | none | `GET /api/graph/nodes` |
| `get_graph_edges()` | none | `GET /api/graph/edges` |
| `list_players()` | none | `GET /api/players` |
| `get_game_time()` | none | `GET /api/state` (extract `game_time`) |
| `get_area_description()` | none | `GET /api/room/description` |
| `find_path(from_room, to_room)` | `from_room: str, to_room: str` | `POST /api/path` |
| `get_debug_state()` | none | `GET /api/debug/state` |

### 3. Player Management

| Tool | Params | Endpoint |
|---|---|---|
| `create_player(name, ...)` | `name, stats?, vitals?, skills?, traits?` | `POST /api/players` |
| `set_active_player(name)` | `name: str` | `POST /api/players/active` |
| `update_player(name, ...)` | `name, new_name?, state?, room?, stats?, skills?, traits?, behaviors?, personality?, description?, emotion?, relationships?` | `POST /api/players/{name}` |
| `delete_player(name)` | `name: str` | `DELETE /api/players/{name}` |
| `kill_player(name)` | `name: str` | `POST /api/players/{name}/kill` |
| `move_player(name, room)` | `name: str, room: str` | `POST /api/players/{name}/move` |
| `player_speak(name, text, room?)` | `name, text, room?` | `POST /api/players/{name}/speak` |
| `import_player(data)` | `data: dict` | `POST /api/players/import` |
| `import_character(char_id, active?)` | `char_id: str, active: bool = True` | `POST /api/registry/characters/import` |
| `get_player_knowledge(name)` | `name: str` | `GET /api/players/{name}/knowledge` |
| `set_player_knowledge(name, data)` | `name: str, data: dict` | `PUT /api/players/{name}/knowledge` |

### 4. Memory System

| Tool | Params | Endpoint |
|---|---|---|
| `get_player_memories(name)` | `name: str` | `GET /api/players/{name}/memories` |
| `set_player_memories(name, memories)` | `name: str, memories: list` | `PUT /api/players/{name}/memories` |
| `add_player_memory(name, text, ...)` | `name, text, type?, importance?, tick?` | `POST /api/players/{name}/memories/entry` |
| `update_player_memory(name, entry_id, ...)` | `name, entry_id, text?, type?, importance?` | `POST /api/players/{name}/memories/entry/{id}` |
| `delete_player_memory(name, entry_id)` | `name, entry_id` | `DELETE /api/players/{name}/memories/entry/{id}` |
| `clear_player_memories(name)` | `name: str` | `POST /api/players/{name}/memories/clear` |

### 5. World Editing — Graph Nodes & Edges

| Tool | Params | Endpoint |
|---|---|---|
| `create_node(type, name, properties?)` | `type, name, properties?` | `POST /api/graph/node` |
| `update_node(node_id, properties?)` | `node_id, properties?, name?` | `PATCH /api/graph/node/{id}` |
| `rename_node(node_id, new_id)` | `node_id, new_id` | `POST /api/graph/node/{id}/rename` |
| `delete_node(node_id)` | `node_id: str` | `DELETE /api/graph/node/{id}` |
| `create_edge(source, target, type, properties?)` | `source, target, type, properties?` | `POST /api/graph/edge` |
| `update_edge(source, target, old_type, ...)` | `source, target, old_type, new_type?, properties?` | `POST /api/graph/edge/update` |
| `delete_edge(source, target, type)` | `source, target, type` | `DELETE /api/graph/edge` |

### 6. World Editing — Higher-Level Builders

| Tool | Params | Endpoint |
|---|---|---|
| `build_room(name, description, ...)` | `name, description, light?, temp?, air?, smell?, noise?` | `POST /api/build/room` |
| `build_item(name, room?, description?, ...)` | `name, room?, description?, actions?, uses?, weight?, hidden?, contents?, ...` | `POST /api/build/item` |
| `connect_rooms(room1, room2, dir1, dir2, ...)` | `room1, room2, dir1, dir2, state?, description?, cost?, way_id?` | `POST /api/build/connect` |
| `reconnect_door(way_id, room_a, room_b, ...)` | `way_id, room_a, room_b, dir_a?, dir_b?` | `POST /api/graph/door/reconnect` |
| `move_item(node_id, room?, container?)` | `node_id, room?, container?` | `POST /api/graph/item/{id}/move` |
| `build_item_from_library(room, item_id)` | `room: str, item_id: str` | `POST /api/build/item-from-library` |

### 7. Item Registry (Library)

| Tool | Params | Endpoint |
|---|---|---|
| `list_library_items()` | none | `GET /api/registry/items` |
| `add_to_library(item_id, data)` | `item_id: str, data: dict` | `POST /api/registry/items` |
| `remove_from_library(item_id)` | `item_id: str` | `DELETE /api/registry/items/{id}` |

### 8. Character & Trait Registry

| Tool | Params | Endpoint |
|---|---|---|
| `list_registry_traits()` | none | `GET /api/registry/traits` |
| `add_registry_trait(trait_id, data)` | `trait_id: str, data: dict` | `POST /api/registry/traits` |
| `list_registry_characters()` | none | `GET /api/registry/characters` |
| `add_registry_character(char_id, data)` | `char_id: str, data: dict` | `POST /api/registry/characters` |

### 9. World Lore

| Tool | Params | Endpoint |
|---|---|---|
| `get_world_lore()` | none | `GET /api/world/lore` |
| `set_world_lore(entries)` | `entries: list` | `POST /api/world/lore` |
| `add_lore_entry(category, content, title?)` | `category, content, title?` | `POST /api/world/lore/entry` |
| `update_lore_entry(entry_id, ...)` | `entry_id, category?, content?, title?` | `POST /api/world/lore/entry/{id}` |
| `delete_lore_entry(entry_id)` | `entry_id: str` | `DELETE /api/world/lore/entry/{id}` |

### 10. Save / Load / Reset

| Tool | Params | Endpoint |
|---|---|---|
| `list_saves()` | none | `GET /api/save-games` |
| `save_game(filename)` | `filename: str` | `POST /api/save-game` |
| `load_game(filename)` | `filename: str` | `POST /api/load-game/{filename}` |
| `delete_save(filename)` | `filename: str` | `DELETE /api/save-game/{filename}` |
| `save_scenario(filename?)` | `filename?: str` | `POST /api/save-scenario` |
| `export_world()` | none | `GET /api/save` (returns full dict) |
| `import_world(data)` | `data: dict` | `POST /api/load` |
| `reset_world()` | none | `POST /api/reset` |

### 11. Settings

| Tool | Params | Endpoint |
|---|---|---|
| `get_ghost_mode()` | none | `GET /api/settings/ghost_mode` |
| `set_ghost_mode(enabled)` | `enabled: bool` | `POST /api/settings/ghost_mode` |
| `get_narration_mode()` | none | `GET /api/settings/narration` |
| `set_narration_mode(mode)` | `mode: 'none' | 'player' | 'ai'` | `POST /api/settings/narration` |

### 12. NPC Behavior & Editing

NPC behavior is edited through `update_player(name, ...)` which supports:
- `behaviors: list[str]` — behavior tags (e.g. `["wander", "hostile"]`)
- `npc_state: str` — e.g. `'idle'`, `'patrolling'`
- `npc_behavior: str` — e.g. `'wander'`, `'guard'`
- `npc_action_interval: int` — ticks between NPC actions
- `personality: str` — personality description
- `state: str` — game state (`awake`, `sleeping`, etc.)
- `current_area: str` — NPC location

Way properties (for editing visual direction, pass message, state) are on door nodes:
- `update_node(way_id, properties={...})` — edit `current_state`, `description`, `pass_message`, `cost`, etc.
- `reconnect_door(...)` — change which rooms a door connects to

Item editing (state, name, properties):
- `update_node(item_id, name=..., properties={...})` — edit `current_state`, `description`, `actions`, `uses`, `hidden`, `weight`, etc.

Trigger editing:
- Triggers are `logic_trigger` nodes with edges of type `triggers`
- Create: `create_node("logic_trigger", name, properties={trigger_type, effect_type, effect_params, ...})` + `create_edge(item_id, trigger_id, "triggers")`
- Edit: `update_node(trigger_id, properties={...})`
- Delete: `delete_node(trigger_id)` (also deletes incident edges)

## Error Handling

- HTTP errors (4xx/5xx) return the Flask JSON error body as the MCP tool error message
- Connection errors (`httpx.ConnectError`) return "Cannot reach Virtual World server at {url}"
- Timeouts return "Request timed out after {timeout}s"
- The `_api(method, path, body?)` helper centralizes all HTTP interaction

## MCP Resources (optional)

Could expose:
- `virtualworld://state` → full world state
- `virtualworld://players` → player list
- `virtualworld://nodes` → graph nodes
- `virtualworld://time` → game clock

## Example MCP Client Config

```json
{
  "mcpServers": {
    "virtual-world": {
      "command": "python",
      "args": ["mcp_server.py"],
      "env": {
        "VIRTUAL_WORLD_URL": "http://localhost:4444"
      }
    }
  }
}
```

## Non-Goals

- Starting/stopping the Flask server — that remains separate
- Authentication/authorization — runs on localhost only
- WebSocket streaming — all tools are request/response
