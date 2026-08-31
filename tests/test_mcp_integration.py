"""Integration tests for the MCP server tools.

Two of the tools (`get_state`, `list_players`) proxy HTTP calls to a running
VirtualWorld Flask server. Instead of leaving these tests permanently skipped
behind `RUN_INTEGRATION=1`, this module boots a real Flask server in a fixture
(on an ephemeral port) so the full HTTP path is exercised automatically.

`test_tools_list` uses FastMCP's in-process client and needs no HTTP server.
"""
import os
import socket
import threading
import time
import urllib.request

import pytest


def _free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="class", autouse=True)
def flask_server():
    """Boot a real Flask server on an ephemeral port for the HTTP-backed tools.

    Sets VIRTUAL_WORLD_URL and reloads mcp_server so its module-level httpx
    client points at the test server (mcp_server may already be imported by
    other test modules with the default localhost:4444 URL).
    """
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    os.environ["VIRTUAL_WORLD_URL"] = base_url

    import importlib
    import mcp_server
    importlib.reload(mcp_server)

    from app import create_app
    app = create_app()
    t = threading.Thread(
        target=app.run,
        kwargs={"host": "127.0.0.1", "port": port, "debug": False, "use_reloader": False},
        daemon=True,
    )
    t.start()

    deadline = time.time() + 30
    ready = False
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/api/health", timeout=2) as r:
                if r.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(0.2)
    if not ready:
        pytest.fail("Flask test server did not become ready")
    yield


class TestIntegration:
    def test_tools_list(self):
        from mcp_server import mcp
        from fastmcp.client import Client
        import asyncio

        async def check():
            async with Client(mcp) as c:
                tools = await c.list_tools()
                names = {t.name for t in tools}
                for t in ["look", "go", "take", "drop", "use", "examine",
                          "inventory", "stats", "speak", "attack", "rest",
                          "open_way", "close_way", "toggle"]:
                    assert t in names
                assert len(tools) >= 50

        asyncio.run(check())

    def test_get_state_returns_dict(self):
        from mcp_server import get_state
        state = get_state.fn()
        assert isinstance(state, dict)
        assert "graph" in state

    def test_list_players_works(self):
        from mcp_server import list_players
        players = list_players.fn()
        assert "players" in players
