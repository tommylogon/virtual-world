"""Test registry, lore, save/load, settings MCP tools."""
import pytest
import asyncio
from unittest.mock import patch


@pytest.fixture
def mock_api():
    with patch("mcp_server._api") as mock:
        yield mock


def test_list_library_items(mock_api):
    mock_api.return_value = {"sword": {}}
    from mcp_server import list_library_items
    assert list_library_items.fn() == {"sword": {}}
    mock_api.assert_called_with("GET", "/api/library/items")


def test_add_to_library(mock_api):
    from mcp_server import add_to_library
    add_to_library.fn("sword_01", {"name": "Iron Sword", "description": "A blade"})
    mock_api.assert_called_with("POST", "/api/library/items",
                                {"id": "sword_01", "data": {"name": "Iron Sword", "description": "A blade"}})


def test_remove_from_library(mock_api):
    from mcp_server import remove_from_library
    remove_from_library.fn("sword_01")
    mock_api.assert_called_with("DELETE", "/api/library/items/sword_01")


def test_get_set_world_lore(mock_api):
    from mcp_server import get_world_lore, set_world_lore
    mock_api.return_value = [{"category": "general", "content": "lore"}]
    assert get_world_lore.fn() == [{"category": "general", "content": "lore"}]
    mock_api.assert_called_with("GET", "/api/world/lore")

    set_world_lore.fn([{"category": "general", "content": "new lore"}])
    mock_api.assert_called_with("POST", "/api/world/lore",
                                [{"category": "general", "content": "new lore"}])


def test_add_lore_entry(mock_api):
    from mcp_server import add_lore_entry
    add_lore_entry.fn("history", "The castle was built in 1400.", title="Castle History")
    mock_api.assert_called_with("POST", "/api/world/lore/entry",
                                {"category": "history", "content": "The castle was built in 1400.",
                                 "title": "Castle History"})


def test_save_load_cycle(mock_api):
    from mcp_server import save_game, load_game, list_saves, delete_save
    mock_api.return_value = {"status": "success"}
    save_game.fn("test_save")
    mock_api.assert_called_with("POST", "/api/save-game", {"filename": "test_save"})

    load_game.fn("test_save")
    mock_api.assert_called_with("POST", "/api/load-game/test_save")

    mock_api.return_value = ["test_save"]
    saves = list_saves.fn()
    assert "test_save" in saves

    delete_save.fn("test_save")
    mock_api.assert_called_with("DELETE", "/api/save-game/test_save")


def test_export_import_world(mock_api):
    from mcp_server import export_world, import_world
    mock_api.return_value = {"areas": {}}
    data = export_world.fn()
    assert data == {"areas": {}}
    mock_api.assert_called_with("GET", "/api/save")

    import_world.fn({"areas": {}})
    mock_api.assert_called_with("POST", "/api/load", {"areas": {}})


def test_reset_world(mock_api):
    from mcp_server import reset_world
    reset_world.fn()
    mock_api.assert_called_with("POST", "/api/reset")


def test_ghost_mode(mock_api):
    from mcp_server import get_ghost_mode, set_ghost_mode
    mock_api.return_value = {"ghost_mode": True}
    assert get_ghost_mode.fn() == {"ghost_mode": True}
    mock_api.assert_called_with("GET", "/api/settings/ghost_mode")

    set_ghost_mode.fn(True)
    mock_api.assert_called_with("POST", "/api/settings/ghost_mode", {"ghost_mode": True})


def test_narration_mode(mock_api):
    from mcp_server import get_narration_mode, set_narration_mode
    mock_api.return_value = {"mode": "none"}
    assert get_narration_mode.fn() == {"mode": "none"}
    set_narration_mode.fn("ai")
    mock_api.assert_called_with("POST", "/api/settings/narration", {"mode": "ai"})


def test_all_misc_tools_registered():
    from mcp_server import mcp
    from fastmcp.client import Client

    async def _run():
        async with Client(mcp) as c:
            tools = await c.list_tools()
            return {t.name for t in tools}

    names = asyncio.run(_run())
    for name in ["list_library_items", "add_to_library", "remove_from_library",
                  "list_registry_traits", "add_registry_trait",
                  "list_registry_characters", "add_registry_character",
                  "get_world_lore", "set_world_lore", "add_lore_entry",
                  "update_lore_entry", "delete_lore_entry",
                  "list_saves", "save_game", "load_game", "delete_save",
                  "save_scenario", "export_world", "import_world", "reset_world",
                  "get_ghost_mode", "set_ghost_mode",
                  "get_narration_mode", "set_narration_mode",
                  "clear_turn_events", "apply_turn_decay"]:
        assert name in names
