"""
Virtual World MCP Server
========================
FastMCP server that proxies commands to an already-running VirtualWorld Flask server.
"""
import os
import httpx
from fastmcp import FastMCP

BASE_URL = os.environ.get("VIRTUAL_WORLD_URL", "http://localhost:4444")
TIMEOUT = int(os.environ.get("VIRTUAL_WORLD_TIMEOUT", "30"))

mcp = FastMCP("Virtual World")

client = httpx.Client(base_url=BASE_URL, timeout=TIMEOUT)


def _api(method: str, path: str, body: dict = None) -> dict:
    """Make an HTTP request to the Flask API and return parsed JSON."""
    try:
        resp = client.request(method, path, json=body)
    except Exception as e:
        raise ConnectionError(
            f"Cannot reach Virtual World server at {BASE_URL}. "
            f"Make sure `python app.py` is running.\nDetails: {e}"
        )
    if resp.status_code >= 400:
        try:
            err = resp.json().get("error", resp.text)
        except Exception:
            err = resp.text
        raise ValueError(f"API error ({resp.status_code}): {err}")
    return resp.json()


def _action(command: str) -> str:
    """Send a text command to the game and return the output."""
    data = _api("POST", "/api/action", {"command": command})
    return data.get("output", "")


# ──────────────────────────────────────────────
# 1. Core Commands
# ──────────────────────────────────────────────
@mcp.tool()
def look() -> str:
    """Describe your current surroundings."""
    return _action("look")


@mcp.tool()
def go(direction: str) -> str:
    """Move in a direction (e.g. north, south, east, west)."""
    return _action(f"go {direction}")


@mcp.tool()
def take(item_name: str) -> str:
    """Pick up an item from the current area."""
    return _action(f"take {item_name}")


@mcp.tool()
def drop(item_name: str) -> str:
    """Drop an item from your inventory into the current area."""
    return _action(f"drop {item_name}")


@mcp.tool()
def use(item_name: str, target: str = "") -> str:
    """Use an item, optionally on a target (e.g. 'key' on 'door')."""
    cmd = f"use {item_name}"
    if target:
        cmd += f" on {target}"
    return _action(cmd)


@mcp.tool()
def examine(target: str) -> str:
    """Get a detailed description of an item, door, or area."""
    return _action(f"examine {target}")


@mcp.tool()
def inventory() -> str:
    """List all items you are carrying."""
    return _action("i")


@mcp.tool()
def stats() -> str:
    """Show your character's vitals, state, and status."""
    return _action("stats")


@mcp.tool()
def speak(text: str) -> str:
    """Broadcast speech to the current area and adjacent areas through open doors."""
    return _action(f"say {text}")


@mcp.tool()
def whisper(text: str) -> str:
    """Whisper speech, only heard in the current room. Use for secrets or quiet conversation."""
    return _action(f"whisper {text}")


@mcp.tool()
def shout(text: str) -> str:
    """Shout speech, heard through closed doors and 2 rooms away. Use to be heard at distance."""
    return _action(f"shout {text}")


@mcp.tool()
def scream(text: str) -> str:
    """Scream at maximum volume, alerts characters 3 rooms away. Use for emergencies."""
    return _action(f"scream {text}")


@mcp.tool()
def attack(target: str) -> str:
    """Attack another character in the same area."""
    return _action(f"attack {target}")


@mcp.tool()
def rest(minutes: int = 10) -> str:
    """Rest or sleep for a number of minutes to recover energy."""
    return _action(f"rest {minutes}")


@mcp.tool()
def open_way(way_name: str) -> str:
    """Open a door in the current area."""
    return _action(f"open {way_name}")


@mcp.tool()
def close_way(way_name: str) -> str:
    """Close a door in the current area."""
    return _action(f"close {way_name}")


@mcp.tool()
def toggle(item_name: str) -> str:
    """Toggle an item on or off (e.g. flashlight, lamp)."""
    return _action(f"toggle {item_name}")

@mcp.tool()
def emote(text: str) -> str:
    """Perform a narrative roleplay action (pure flavor, no game effect). E.g. 'kisses Alice gently'."""
    return _action(f"do {text}")


# ──────────────────────────────────────────────
# 2. World State
# ──────────────────────────────────────────────
@mcp.tool()
def get_state() -> dict:
    """Return the full world state as a dict."""
    return _api("GET", "/api/state")


@mcp.tool()
def get_graph_nodes() -> list:
    """Return all graph nodes (areas, items, ways, players, triggers)."""
    return _api("GET", "/api/graph/nodes")


@mcp.tool()
def get_graph_edges() -> list:
    """Return all graph edges (connections between nodes)."""
    return _api("GET", "/api/graph/edges")


@mcp.tool()
def list_players() -> dict:
    """List all player characters and the active one."""
    return _api("GET", "/api/players")


@mcp.tool()
def get_game_time() -> str:
    """Get the current in-game clock time (HH:MM format)."""
    state = _api("GET", "/api/state")
    return state.get("game_time", "")


@mcp.tool()
def get_area_description() -> str:
    """Get the full description of the current area."""
    data = _api("GET", "/api/area/description")
    return data.get("description", "")


@mcp.tool()
def find_path(from_area: str, to_area: str) -> dict:
    """Find the first direction to move from one area to another."""
    return _api("POST", "/api/path", {"from": from_area, "to": to_area})


@mcp.tool()
def get_debug_state() -> dict:
    """Get a compact debug dump of the world state."""
    return _api("GET", "/api/debug/state")


# ──────────────────────────────────────────────
# 3. Player Management
# ──────────────────────────────────────────────
@mcp.tool()
def create_player(name: str, stats: dict = None, vitals: dict = None,
                  skills: dict = None, traits: list = None) -> dict:
    """Create a new player character."""
    body = {"name": name}
    if stats is not None: body["stats"] = stats
    if vitals is not None: body["vitals"] = vitals
    if skills is not None: body["skills"] = skills
    if traits is not None: body["traits"] = traits
    return _api("POST", "/api/players", body)


@mcp.tool()
def set_active_player(name: str) -> dict:
    """Switch the active player character."""
    return _api("POST", "/api/players/active", {"name": name})


@mcp.tool()
def update_player(name: str, new_name: str = None, state: str = None,
                  area: str = None, stats: dict = None, skills: dict = None,
                  traits: list = None, behaviors: list = None,
                  personality: str = None, description: str = None,
                  emotion: dict = None, relationships: dict = None,
                  npc_state: str = None, npc_behavior: str = None,
                  npc_action_interval: int = None) -> dict:
    """Update a player character's properties."""
    body = {}
    if new_name is not None: body["new_name"] = new_name
    if state is not None: body["state"] = state
    if area is not None: body["current_area"] = area
    if stats is not None: body["stats"] = stats
    if skills is not None: body["skills"] = skills
    if traits is not None: body["traits"] = traits
    if behaviors is not None: body["behaviors"] = behaviors
    if personality is not None: body["personality"] = personality
    if description is not None: body["description"] = description
    if emotion is not None: body["emotion"] = emotion
    if relationships is not None: body["relationships"] = relationships
    if npc_state is not None: body["npc_state"] = npc_state
    if npc_behavior is not None: body["npc_behavior"] = npc_behavior
    if npc_action_interval is not None: body["npc_action_interval"] = npc_action_interval
    return _api("POST", f"/api/players/{name}", body)


@mcp.tool()
def delete_player(name: str) -> dict:
    """Delete a player character (cannot delete the last one)."""
    return _api("DELETE", f"/api/players/{name}")


@mcp.tool()
def kill_player(name: str) -> dict:
    """Kill a player character (sets HP to 0, state to dead)."""
    return _api("POST", f"/api/players/{name}/kill")


@mcp.tool()
def move_player(name: str, area: str) -> dict:
    """Teleport a player to a specific area."""
    return _api("POST", f"/api/players/{name}/move", {"area": area})


@mcp.tool()
def player_speak(name: str, text: str, area: str = None) -> dict:
    """Broadcast speech from a player to a area."""
    body = {"text": text}
    if area is not None: body["area"] = area
    return _api("POST", f"/api/players/{name}/speak", body)


@mcp.tool()
def import_player(data: dict) -> dict:
    """Import a player with full data (stats, inventory, personality, etc.)."""
    return _api("POST", "/api/players/import", data)


@mcp.tool()
def import_character(char_id: str, active: bool = True) -> dict:
    """Import a character from the registry as a playable player."""
    return _api("POST", f"/api/library/import/character/{char_id}", {"active": active})


# ──────────────────────────────────────────────
# 4. Memory System
# ──────────────────────────────────────────────
@mcp.tool()
def get_player_memories(name: str) -> list:
    """Get all memories for a player."""
    return _api("GET", f"/api/players/{name}/memories")


@mcp.tool()
def set_player_memories(name: str, memories: list) -> dict:
    """Replace all memories for a player."""
    return _api("PUT", f"/api/players/{name}/memories", {"memories": memories})


@mcp.tool()
def add_player_memory(name: str, text: str, memory_type: str = "action",
                      importance: int = 3, tick: int = None) -> dict:
    """Add a memory entry for a player."""
    body = {"text": text, "type": memory_type, "importance": importance}
    if tick is not None: body["tick"] = tick
    return _api("POST", f"/api/players/{name}/memories/entry", body)


@mcp.tool()
def update_player_memory(name: str, entry_id: str, text: str = None,
                         memory_type: str = None, importance: int = None) -> dict:
    """Update a specific memory entry."""
    body = {}
    if text is not None: body["text"] = text
    if memory_type is not None: body["type"] = memory_type
    if importance is not None: body["importance"] = importance
    return _api("POST", f"/api/players/{name}/memories/entry/{entry_id}", body)


@mcp.tool()
def delete_player_memory(name: str, entry_id: str) -> dict:
    """Delete a specific memory entry."""
    return _api("DELETE", f"/api/players/{name}/memories/entry/{entry_id}")


@mcp.tool()
def clear_player_memories(name: str) -> dict:
    """Clear all memories for a player."""
    return _api("POST", f"/api/players/{name}/memories/clear")


# ──────────────────────────────────────────────
# 5. World Editing — Graph CRUD
# ──────────────────────────────────────────────
@mcp.tool()
def create_node(type: str, name: str, properties: dict = None) -> dict:
    """Create a new graph node (area, item, door, logic_trigger, etc.)."""
    body = {"type": type, "name": name}
    if properties is not None: body["properties"] = properties
    return _api("POST", "/api/graph/node", body)


@mcp.tool()
def update_node(node_id: str, properties: dict = None, name: str = None) -> dict:
    """Update a node's properties and/or name."""
    body = {}
    if properties is not None: body["properties"] = properties
    if name is not None: body["name"] = name
    return _api("PATCH", f"/api/graph/node/{node_id}", body)


@mcp.tool()
def rename_node(node_id: str, new_id: str) -> dict:
    """Rename a node ID, updating all edges and references."""
    return _api("POST", f"/api/graph/node/{node_id}/rename", {"new_id": new_id})


@mcp.tool()
def delete_node(node_id: str) -> dict:
    """Delete a node and all its incident edges."""
    return _api("DELETE", f"/api/graph/node/{node_id}")


@mcp.tool()
def create_edge(source: str, target: str, type: str, properties: dict = None) -> dict:
    """Create a new edge between two nodes."""
    body = {"source": source, "target": target, "type": type}
    if properties is not None: body["properties"] = properties
    return _api("POST", "/api/graph/edge", body)


@mcp.tool()
def update_edge(source: str, target: str, old_type: str,
                new_type: str = None, properties: dict = None) -> dict:
    """Update an edge's type and/or properties."""
    body = {"source": source, "target": target, "old_type": old_type}
    if new_type is not None: body["new_type"] = new_type
    if properties is not None: body["properties"] = properties
    return _api("POST", "/api/graph/edge/update", body)


@mcp.tool()
def delete_edge(source: str, target: str, type: str) -> dict:
    """Delete an edge."""
    return _api("DELETE", "/api/graph/edge",
                {"source": source, "target": target, "type": type})


# ──────────────────────────────────────────────
# 6. World Editing — High-Level Builders
# ──────────────────────────────────────────────
@mcp.tool()
def build_area(name: str, description: str, light: int = None,
               temperature: int = None, air: str = None,
               smell: str = None, noise: str = None) -> dict:
    """Create or update a area with environment settings."""
    body = {"name": name, "description": description}
    if light is not None: body["light"] = light
    if temperature is not None: body["temperature"] = temperature
    if air is not None: body["air"] = air
    if smell is not None: body["smell"] = smell
    if noise is not None: body["noise"] = noise
    return _api("POST", "/api/build/area", body)


@mcp.tool()
def build_item(name: str, area: str = None, description: str = "",
               actions: str = "examine,take,use", uses: int = -1,
               weight: float = 0.1, hidden: bool = False,
               contents: list = None, container: str = None,
               character: str = None) -> dict:
    """Create or update an item, optionally placing it in a area/container/character."""
    body = {"name": name, "description": description, "actions": actions,
            "uses": uses, "weight": weight, "hidden": hidden}
    if area is not None: body["area"] = area
    if contents is not None: body["contents"] = contents
    if container is not None: body["container"] = container
    if character is not None: body["character"] = character
    return _api("POST", "/api/build/item", body)


@mcp.tool()
def connect_areas(room1: str, room2: str, dir1: str, dir2: str,
                  state: str = "open", description: str = "",
                  cost: dict = None, way_id: str = None,
                  one_way: bool = False) -> dict:
    """Create a bidirectional door connection between two areas."""
    body = {"room1": room1, "room2": room2, "dir1": dir1, "dir2": dir2,
            "state": state, "description": description}
    if cost is not None: body["cost"] = cost
    if way_id is not None: body["way_id"] = way_id
    if one_way: body["one_way"] = True
    return _api("POST", "/api/build/connect", body)


@mcp.tool()
def reconnect_way(way_id: str, area_a: str, area_b: str,
                   dir_a: str = None, dir_b: str = None) -> dict:
    """Change which two areas a door connects to."""
    body = {"way_id": way_id, "area_a": area_a, "area_b": area_b}
    if dir_a is not None: body["dir_a"] = dir_a
    if dir_b is not None: body["dir_b"] = dir_b
    return _api("POST", "/api/graph/way/reconnect", body)


@mcp.tool()
def move_item(node_id: str, area: str = None, container: str = None) -> dict:
    """Move an item to a area or into a container item."""
    body = {}
    if area is not None: body["area"] = area
    if container is not None: body["container"] = container
    return _api("POST", f"/api/graph/item/{node_id}/move", body)


@mcp.tool()
def build_item_from_library(area: str, item_id: str) -> dict:
    """Place a library item into a area (creates graph node + triggers)."""
    return _api("POST", f"/api/library/items/{item_id}/place", {"area": area})


# ──────────────────────────────────────────────
# 7. Item Registry (Library)
# ──────────────────────────────────────────────
@mcp.tool()
def list_library_items() -> dict:
    """List all items in the library registry."""
    return _api("GET", "/api/library/items")


@mcp.tool()
def add_to_library(item_id: str, data: dict) -> dict:
    """Add or update an item in the library registry."""
    return _api("POST", "/api/library/items", {"id": item_id, "data": data})


@mcp.tool()
def remove_from_library(item_id: str) -> dict:
    """Remove an item from the library registry."""
    return _api("DELETE", f"/api/library/items/{item_id}")


@mcp.tool()
def list_registry_traits() -> dict:
    """List all traits in the registry."""
    return _api("GET", "/api/library/traits")


@mcp.tool()
def add_registry_trait(trait_id: str, data: dict) -> dict:
    """Add or update a trait in the registry."""
    return _api("POST", "/api/library/traits", {"id": trait_id, "data": data})


@mcp.tool()
def list_registry_characters() -> dict:
    """List all characters in the registry."""
    return _api("GET", "/api/library/characters")


@mcp.tool()
def add_registry_character(char_id: str, data: dict) -> dict:
    """Add or update a character in the registry."""
    return _api("POST", "/api/library/characters", {"id": char_id, "data": data})


# ──────────────────────────────────────────────
# 8. World Lore
# ──────────────────────────────────────────────
@mcp.tool()
def get_world_lore() -> list:
    """Get all world lore entries."""
    return _api("GET", "/api/world/lore")


@mcp.tool()
def set_world_lore(entries: list) -> dict:
    """Replace all world lore entries."""
    return _api("POST", "/api/world/lore", {"lore": entries})


@mcp.tool()
def add_lore_entry(category: str, content: str, title: str = None) -> dict:
    """Add a new world lore entry."""
    body = {"category": category, "content": content}
    if title is not None: body["title"] = title
    return _api("POST", "/api/world/lore/entry", body)


@mcp.tool()
def update_lore_entry(entry_id: str, category: str = None,
                      content: str = None, title: str = None) -> dict:
    """Update a specific world lore entry."""
    body = {}
    if category is not None: body["category"] = category
    if content is not None: body["content"] = content
    if title is not None: body["title"] = title
    return _api("POST", f"/api/world/lore/entry/{entry_id}", body)


@mcp.tool()
def delete_lore_entry(entry_id: str) -> dict:
    """Delete a specific world lore entry."""
    return _api("DELETE", f"/api/world/lore/entry/{entry_id}")


# ──────────────────────────────────────────────
# 9. Save / Load / Reset
# ──────────────────────────────────────────────
@mcp.tool()
def list_saves() -> list:
    """List all saved games."""
    return _api("GET", "/api/save-games")


@mcp.tool()
def save_game(filename: str) -> dict:
    """Save the current game state."""
    return _api("POST", "/api/save-game", {"filename": filename})


@mcp.tool()
def load_game(filename: str) -> dict:
    """Load a saved game by filename."""
    return _api("POST", f"/api/load-game/{filename}")


@mcp.tool()
def delete_save(filename: str) -> dict:
    """Delete a saved game."""
    return _api("DELETE", f"/api/save-game/{filename}")


@mcp.tool()
def save_scenario(filename: str = None) -> dict:
    """Save the current world as a reusable scenario."""
    body = {}
    if filename is not None: body["filename"] = filename
    return _api("POST", "/api/save-scenario", body)


@mcp.tool()
def export_world() -> dict:
    """Export the full world state as a JSON dict."""
    return _api("GET", "/api/save")


@mcp.tool()
def import_world(data: dict) -> dict:
    """Import a full world state from a JSON dict."""
    return _api("POST", "/api/load", data)


@mcp.tool()
def reset_world() -> dict:
    """Reset the world to its initial state."""
    return _api("POST", "/api/reset")


# ──────────────────────────────────────────────
# 10. Settings
# ──────────────────────────────────────────────
@mcp.tool()
def get_ghost_mode() -> dict:
    """Check if ghost mode is enabled."""
    return _api("GET", "/api/settings/ghost_mode")


@mcp.tool()
def set_ghost_mode(enabled: bool) -> dict:
    """Enable or disable ghost mode (dead characters can act)."""
    return _api("POST", "/api/settings/ghost_mode", {"ghost_mode": enabled})


@mcp.tool()
def get_narration_mode() -> dict:
    """Get the current narration mode."""
    return _api("GET", "/api/settings/narration")


@mcp.tool()
def set_narration_mode(mode: str) -> dict:
    """Set narration mode: 'none', 'player', or 'ai'."""
    return _api("POST", "/api/settings/narration", {"mode": mode})


# ──────────────────────────────────────────────
# 11. Turn Management
# ──────────────────────────────────────────────
@mcp.tool()
def clear_turn_events() -> dict:
    """Clear turn events for a new turn."""
    return _api("POST", "/api/turn/clear")


@mcp.tool()
def apply_turn_decay() -> dict:
    """Apply baseline vital decay and environmental effects to all characters."""
    return _api("POST", "/api/turn/apply")


if __name__ == "__main__":
    mcp.run()
