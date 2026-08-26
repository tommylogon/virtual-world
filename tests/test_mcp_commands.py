"""Test core command MCP tools."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_api():
    """Patch _api helper in mcp_server."""
    with patch("mcp_server._api") as mock:
        mock.return_value = {"output": "ok"}
        yield mock


@pytest.fixture
def mock_action():
    """Patch _action helper in mcp_server."""
    with patch("mcp_server._action") as mock:
        mock.return_value = "result"
        yield mock


def test_look(mock_action):
    from mcp_server import look
    assert look.fn() == "result"
    mock_action.assert_called_with("look")


def test_go(mock_action):
    from mcp_server import go
    assert go.fn("north") == "result"
    mock_action.assert_called_with("go north")


def test_take(mock_action):
    from mcp_server import take
    assert take.fn("apple") == "result"
    mock_action.assert_called_with("take apple")


def test_drop(mock_action):
    from mcp_server import drop
    assert drop.fn("apple") == "result"
    mock_action.assert_called_with("drop apple")


def test_use_no_target(mock_action):
    from mcp_server import use
    assert use.fn("potion") == "result"
    mock_action.assert_called_with("use potion")


def test_use_with_target(mock_action):
    from mcp_server import use
    assert use.fn("key", "door") == "result"
    mock_action.assert_called_with("use key on door")


def test_examine(mock_action):
    from mcp_server import examine
    assert examine.fn("painting") == "result"
    mock_action.assert_called_with("examine painting")


def test_inventory(mock_action):
    from mcp_server import inventory
    assert inventory.fn() == "result"
    mock_action.assert_called_with("i")


def test_stats(mock_action):
    from mcp_server import stats
    assert stats.fn() == "result"
    mock_action.assert_called_with("stats")


def test_speak(mock_action):
    from mcp_server import speak
    assert speak.fn("hello") == "result"
    mock_action.assert_called_with("say hello")


def test_attack(mock_action):
    from mcp_server import attack
    assert attack.fn("goblin") == "result"
    mock_action.assert_called_with("attack goblin")


def test_rest_default(mock_action):
    from mcp_server import rest
    assert rest.fn() == "result"
    mock_action.assert_called_with("rest 10")


def test_rest_custom(mock_action):
    from mcp_server import rest
    assert rest.fn(30) == "result"
    mock_action.assert_called_with("rest 30")


def test_open_way(mock_action):
    from mcp_server import open_way
    assert open_way.fn("front door") == "result"
    mock_action.assert_called_with("open front door")


def test_close_way(mock_action):
    from mcp_server import close_way
    assert close_way.fn("front door") == "result"
    mock_action.assert_called_with("close front door")


def test_toggle(mock_action):
    from mcp_server import toggle
    assert toggle.fn("flashlight") == "result"
    mock_action.assert_called_with("toggle flashlight")


def test_tools_registered():
    """All 52 tools should be registered on the MCP server."""
    from mcp_server import mcp
    from fastmcp.client import Client

    async def _run():
        async with Client(mcp) as c:
            tools = await c.list_tools()
            return {t.name for t in tools}

    names = asyncio.run(_run())
    for name in ["look", "go", "take", "drop", "use", "examine",
                  "inventory", "stats", "speak", "attack", "rest",
                  "open_way", "close_way", "toggle",
                  "get_state", "get_graph_nodes", "get_graph_edges",
                  "list_players", "get_game_time", "get_area_description",
                  "find_path", "get_debug_state", "create_player",
                  "set_active_player", "update_player", "delete_player",
                  "kill_player", "move_player", "player_speak",
                  "import_player", "import_character",
                  "get_player_knowledge", "set_player_knowledge",
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
        assert name in names, f"Tool '{name}' not registered"
