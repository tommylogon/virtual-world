"""Test world state and player management MCP tools."""
import pytest
import asyncio
from unittest.mock import patch


@pytest.fixture
def mock_api():
    with patch("mcp_server._api") as mock:
        yield mock


def _check_tool_registered(name):
    from mcp_server import mcp
    from fastmcp.client import Client

    async def _run():
        async with Client(mcp) as c:
            tools = await c.list_tools()
            return {t.name for t in tools}

    names = asyncio.run(_run())
    assert name in names, f"Tool '{name}' not registered"


def test_get_state(mock_api):
    mock_api.return_value = {"areas": {}}
    from mcp_server import get_state
    result = get_state.fn()
    assert result == {"areas": {}}
    mock_api.assert_called_with("GET", "/api/state")


def test_get_graph_nodes(mock_api):
    mock_api.return_value = [{"id": "area_1"}]
    from mcp_server import get_graph_nodes
    result = get_graph_nodes.fn()
    assert len(result) == 1


def test_get_graph_edges(mock_api):
    mock_api.return_value = [{"source": "a", "target": "b"}]
    from mcp_server import get_graph_edges
    result = get_graph_edges.fn()
    assert len(result) == 1


def test_list_players(mock_api):
    mock_api.return_value = {"players": ["Kaelen"], "active": "Kaelen"}
    from mcp_server import list_players
    result = list_players.fn()
    assert result["active"] == "Kaelen"


def test_get_game_time(mock_api):
    mock_api.return_value = {"game_time": "08:45"}
    from mcp_server import get_game_time
    result = get_game_time.fn()
    assert result == "08:45"


def test_get_area_description(mock_api):
    mock_api.return_value = {"description": "A dark area."}
    from mcp_server import get_area_description
    result = get_area_description.fn()
    assert result == "A dark area."


def test_find_path(mock_api):
    mock_api.return_value = {"direction": "north"}
    from mcp_server import find_path
    result = find_path.fn("Living Area", "Kitchen")
    assert result["direction"] == "north"
    mock_api.assert_called_with("POST", "/api/path", {"from": "Living Area", "to": "Kitchen"})


def test_create_player(mock_api):
    mock_api.return_value = {"status": "success", "player": "TestChar"}
    from mcp_server import create_player
    result = create_player.fn("TestChar")
    assert result["status"] == "success"


def test_set_active_player(mock_api):
    from mcp_server import set_active_player
    set_active_player.fn("Kaelen")
    mock_api.assert_called_with("POST", "/api/players/active", {"name": "Kaelen"})


def test_delete_player(mock_api):
    mock_api.return_value = {"status": "deleted"}
    from mcp_server import delete_player
    result = delete_player.fn("TestChar")
    assert result["status"] == "deleted"


def test_kill_player(mock_api):
    from mcp_server import kill_player
    kill_player.fn("TestChar")
    mock_api.assert_called_with("POST", "/api/players/TestChar/kill")


def test_move_player(mock_api):
    from mcp_server import move_player
    move_player.fn("Kaelen", "Kitchen")
    mock_api.assert_called_with("POST", "/api/players/Kaelen/move", {"area": "Kitchen"})


def test_get_player_memories(mock_api):
    mock_api.return_value = [{"text": "found a key"}]
    from mcp_server import get_player_memories
    result = get_player_memories.fn("Kaelen")
    assert len(result) == 1


def test_add_player_memory(mock_api):
    mock_api.return_value = {"status": "success"}
    from mcp_server import add_player_memory
    result = add_player_memory.fn("Kaelen", "found a key")
    assert result["status"] == "success"


def test_all_tools_registered():
    for name in ["get_state", "get_graph_nodes", "get_graph_edges",
                  "list_players", "get_game_time", "get_area_description",
                  "find_path", "get_debug_state", "create_player",
                  "set_active_player", "update_player", "delete_player",
                  "kill_player", "move_player", "player_speak",
                  "import_player", "import_character",
                  "get_player_memories", "set_player_memories",
                   "add_player_memory", "update_player_memory",
                   "delete_player_memory", "clear_player_memories",
                   "create_node", "update_node", "rename_node", "delete_node",
                   "create_edge", "update_edge", "delete_edge",
                   "build_area", "build_item", "connect_areas",
                   "reconnect_way", "move_item", "build_item_from_library",
                   "list_library_items", "add_to_library", "remove_from_library",
                   "list_registry_traits", "add_registry_trait",
                   "list_registry_characters", "add_registry_character",
                   "get_world_lore", "set_world_lore", "add_lore_entry",
                   "update_lore_entry", "delete_lore_entry",
                   "list_saves", "save_game", "load_game", "delete_save",
                   "save_scenario", "export_world", "import_world", "reset_world",
                   "get_ghost_mode", "set_ghost_mode",
                   "get_narration_mode", "set_narration_mode",
                   "clear_turn_events", "apply_turn_decay"]:
        _check_tool_registered(name)
