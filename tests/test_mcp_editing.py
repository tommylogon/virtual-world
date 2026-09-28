"""Test world editing MCP tools."""

# NOTE: FastMCP >= 3 returns the plain function from @mcp.tool(), so a tool is
# called directly. Older FastMCP returned a wrapper whose .fn held the function,
# which is why these tests once read `tool.fn(...)`. See
# docs/design/typescript-migration-plan.md for the parallel hub-file lesson in
# static/js/types/globals.d.ts; the shape here is version-sensitive, not a bug.

import pytest
from unittest.mock import patch


@pytest.fixture
def mock_api():
    with patch("mcp_server._api") as mock:
        yield mock


def test_create_node(mock_api):
    mock_api.return_value = {"status": "success", "id": "area_test"}
    from mcp_server import create_node
    result = create_node("area", "Test Area", {"description": "A test area"})
    assert result["status"] == "success"
    mock_api.assert_called_with("POST", "/api/graph/node",
                                {"type": "area", "name": "Test Area",
                                 "properties": {"description": "A test area"}})


def test_update_node(mock_api):
    from mcp_server import update_node
    update_node("area_test", {"description": "Updated"})
    mock_api.assert_called_with("PATCH", "/api/graph/node/area_test",
                                {"properties": {"description": "Updated"}})


def test_rename_node(mock_api):
    from mcp_server import rename_node
    rename_node("area_test", "area_new")
    mock_api.assert_called_with("POST", "/api/graph/node/area_test/rename",
                                {"new_id": "area_new"})


def test_delete_node(mock_api):
    from mcp_server import delete_node
    delete_node("area_test")
    mock_api.assert_called_with("DELETE", "/api/graph/node/area_test")


def test_create_edge(mock_api):
    from mcp_server import create_edge
    create_edge("area_a", "area_b", "connection", {"direction": "north"})
    mock_api.assert_called_with("POST", "/api/graph/edge",
                                {"source": "area_a", "target": "area_b",
                                 "type": "connection",
                                 "properties": {"direction": "north"}})


def test_update_edge(mock_api):
    from mcp_server import update_edge
    update_edge("area_a", "way_1", "connection", new_type="connection",
                properties={"direction": "south"})
    mock_api.assert_called_with("POST", "/api/graph/edge/update",
                                {"source": "area_a", "target": "way_1",
                                 "old_type": "connection",
                                 "new_type": "connection",
                                 "properties": {"direction": "south"}})


def test_delete_edge(mock_api):
    from mcp_server import delete_edge
    delete_edge("area_a", "way_1", "connection")
    mock_api.assert_called_with("DELETE", "/api/graph/edge",
                                {"source": "area_a", "target": "way_1",
                                 "type": "connection"})


def test_build_area(mock_api):
    from mcp_server import build_area
    build_area("Kitchen", "A warm kitchen", light=80, temperature=22)
    mock_api.assert_called_with("POST", "/api/build/area",
                                {"name": "Kitchen", "description": "A warm kitchen",
                                 "light": 80, "temperature": 22})


def test_build_item(mock_api):
    from mcp_server import build_item
    build_item("Sword", area="Living Area", description="A sharp blade")
    mock_api.assert_called_with("POST", "/api/build/item",
                                {"name": "Sword", "description": "A sharp blade",
                                 "actions": "examine,take,use", "uses": -1,
                                 "weight": 0.1, "hidden": False,
                                 "area": "Living Area"})


def test_connect_areas(mock_api):
    from mcp_server import connect_areas
    connect_areas("Living Area", "Kitchen", "north", "south", state="open")
    mock_api.assert_called_with("POST", "/api/build/connect",
                                {"room1": "Living Area", "room2": "Kitchen",
                                 "dir1": "north", "dir2": "south",
                                 "state": "open", "description": ""})


def test_reconnect_way(mock_api):
    from mcp_server import reconnect_way
    reconnect_way("way_1", "area_a", "area_b", dir_a="north", dir_b="south")
    mock_api.assert_called_with("POST", "/api/graph/way/reconnect",
                                {"way_id": "way_1", "area_a": "area_a",
                                 "area_b": "area_b", "dir_a": "north",
                                 "dir_b": "south"})


def test_move_item(mock_api):
    from mcp_server import move_item
    move_item("item_sword", area="Kitchen")
    mock_api.assert_called_with("POST", "/api/graph/item/item_sword/move",
                                {"area": "Kitchen"})


def test_build_item_from_library(mock_api):
    from mcp_server import build_item_from_library
    build_item_from_library("Living Area", "sword_01")
    mock_api.assert_called_with("POST", "/api/library/items/sword_01/place",
                                {"area": "Living Area"})


def test_all_editing_tools_registered():
    from mcp_server import mcp
    from fastmcp.client import Client
    import asyncio

    async def _run():
        async with Client(mcp) as c:
            tools = await c.list_tools()
            return {t.name for t in tools}

    names = asyncio.run(_run())
    for name in ["create_node", "update_node", "rename_node", "delete_node",
                  "create_edge", "update_edge", "delete_edge",
                  "build_area", "build_item", "connect_areas",
                  "reconnect_way", "move_item", "build_item_from_library"]:
        assert name in names
