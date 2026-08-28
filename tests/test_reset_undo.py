"""Tests for undo/redo after destructive operations (reset, load).

Regression: clicking Undo after Reset Scenario did nothing — it just
refreshed the graph view from the already-reset server state because there
was no server-side undo stack.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from area import Area


def _make_app():
    app = create_app({"TESTING": True})
    return app


def _area_ids(world):
    """Return the set of area node IDs currently in the world graph."""
    return {n.id for n in world.graph.nodes.values() if n.type == "area"}


def _add_test_area(world, name):
    world.add_area(Area(name, f"A test area called {name}.", items=[]))


def test_undo_restores_state_after_reset():
    """Reset wipes the world; Undo must restore the pre-reset state."""
    app = _make_app()
    client = app.test_client()
    world = app.world

    _add_test_area(world, "Secret Laboratory")
    _add_test_area(world, "Abandoned Observatory")
    world.connect_areas("Secret Laboratory", "Abandoned Observatory",
                        "east", "west", state="open", desc="A rusted door.")
    pre_area_ids = _area_ids(world)
    assert "area_secret_laboratory" in pre_area_ids
    assert "area_abandoned_observatory" in pre_area_ids

    # Reset — should snapshot pre-state, then wipe
    resp = client.post("/api/reset")
    assert resp.status_code == 200
    post_reset_ids = _area_ids(app.world)
    assert "area_secret_laboratory" not in post_reset_ids
    assert "area_abandoned_observatory" not in post_reset_ids

    # Undo — should restore the pre-reset state
    resp = client.post("/api/undo")
    assert resp.status_code == 200
    restored_ids = _area_ids(app.world)
    assert "area_secret_laboratory" in restored_ids
    assert "area_abandoned_observatory" in restored_ids
    assert restored_ids == pre_area_ids


def test_undo_empty_returns_error():
    """Undo with an empty stack returns 400."""
    app = _make_app()
    client = app.test_client()
    resp = client.post("/api/undo")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_undo_redo_roundtrip():
    """Undo then Redo restores the reset state, then undo is available again."""
    app = _make_app()
    client = app.test_client()
    world = app.world

    _add_test_area(world, "Echo Chamber")
    pre_ids = _area_ids(world)
    assert "area_echo_chamber" in pre_ids

    assert client.post("/api/reset").status_code == 200
    assert "area_echo_chamber" not in _area_ids(app.world)

    assert client.post("/api/undo").status_code == 200
    assert "area_echo_chamber" in _area_ids(app.world)

    assert client.post("/api/redo").status_code == 200
    assert "area_echo_chamber" not in _area_ids(app.world)


def test_reset_then_undo_restores_connections():
    """Connections (edges) between new areas are restored by undo."""
    app = _make_app()
    client = app.test_client()
    world = app.world

    _add_test_area(world, "Tower Base")
    _add_test_area(world, "Tower Top")
    world.connect_areas("Tower Base", "Tower Top", "up", "down",
                        state="open", desc="A spiral staircase.")

    pre_edges = len(world.graph.edges)

    assert client.post("/api/reset").status_code == 200
    assert len(app.world.graph.edges) < pre_edges

    assert client.post("/api/undo").status_code == 200
    assert len(app.world.graph.edges) == pre_edges


def test_scenario_source_preserved_after_undo():
    """Undo restores _scenario_source so a subsequent reset still works."""
    app = _make_app()
    client = app.test_client()
    world = app.world

    original_source = world._scenario_source
    _add_test_area(world, "Lab Rat Maze")

    assert client.post("/api/reset").status_code == 200
    assert client.post("/api/undo").status_code == 200
    assert app.world._scenario_source == original_source
