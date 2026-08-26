"""Test MCP server skeleton: startup, config, API helper."""

import pytest
import os
import asyncio
from unittest.mock import patch, MagicMock
import json


@pytest.fixture(autouse=True)
def clear_env():
    """Ensure a clean environment for each test."""
    old_url = os.environ.pop("VIRTUAL_WORLD_URL", None)
    old_timeout = os.environ.pop("VIRTUAL_WORLD_TIMEOUT", None)
    yield
    if old_url is not None:
        os.environ["VIRTUAL_WORLD_URL"] = old_url
    if old_timeout is not None:
        os.environ["VIRTUAL_WORLD_TIMEOUT"] = old_timeout


def test_default_config():
    """Default BASE_URL should be localhost:4444."""
    # Re-import to pick up clean env
    import importlib
    import mcp_server
    importlib.reload(mcp_server)
    assert mcp_server.BASE_URL == "http://localhost:4444"


def test_env_config():
    """VIRTUAL_WORLD_URL env var should override default."""
    os.environ["VIRTUAL_WORLD_URL"] = "http://localhost:9999"
    import importlib
    import mcp_server
    importlib.reload(mcp_server)
    assert mcp_server.BASE_URL == "http://localhost:9999"


def test_env_timeout():
    """VIRTUAL_WORLD_TIMEOUT env var should set timeout."""
    os.environ["VIRTUAL_WORLD_TIMEOUT"] = "60"
    import importlib
    import mcp_server
    importlib.reload(mcp_server)
    assert mcp_server.TIMEOUT == 60


def test_mcp_instance():
    """mcp should be a FastMCP instance named 'Virtual World'."""
    import mcp_server
    assert mcp_server.mcp is not None
    assert mcp_server.mcp.name == "Virtual World"


def test_api_helper_success():
    """_api should return parsed JSON on 200."""
    import mcp_server
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"output": "hello"}
    with patch.object(mcp_server.client, "request", return_value=mock_resp):
        result = mcp_server._api("POST", "/api/action", {"command": "look"})
    assert result == {"output": "hello"}


def test_api_helper_error():
    """_api should raise ValueError on 4xx/5xx."""
    import mcp_server
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"error": "bad request"}
    mock_resp.raise_for_status.side_effect = Exception("400")
    with patch.object(mcp_server.client, "request", return_value=mock_resp):
        with pytest.raises(ValueError, match="bad request"):
            mcp_server._api("POST", "/api/action", {})


def test_api_helper_connection_error():
    """_api should raise ConnectionError if server unreachable."""
    import mcp_server
    with patch.object(mcp_server.client, "request", side_effect=Exception("Connection refused")):
        with pytest.raises(ConnectionError, match="Cannot reach Virtual World server"):
            mcp_server._api("GET", "/api/state")


def test_action_helper():
    """_action should call /api/action and return the 'output' field."""
    import mcp_server
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"output": "You see a area."}
    with patch.object(mcp_server.client, "request", return_value=mock_resp):
        result = mcp_server._action("look")
    assert result == "You see a area."


def test_mcp_startup():
    """Server should start and respond to initialize."""
    import mcp_server
    from fastmcp.client import Client

    async def _run():
        async with Client(mcp_server.mcp) as c:
            await c.initialize()
            tools = await c.list_tools()
            return tools

    tools = asyncio.run(_run())
    # Core command tools should be registered
    assert len(tools) > 0
