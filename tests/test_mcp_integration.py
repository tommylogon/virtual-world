"""Integration test: requires Flask server running on localhost:4444."""
import pytest
import os


@pytest.mark.skipif(
    not os.environ.get("RUN_INTEGRATION"),
    reason="Set RUN_INTEGRATION=1 to run integration tests (requires Flask on :4444)"
)
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
