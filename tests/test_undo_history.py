"""Labeled undo history (task-371): labels, /api/undo/list, multi-step undo."""

import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    # Scenario loads write <name>.json into DATA_DIR/scenarios — point it at a
    # temp dir so tests never leak State A/B/C / First / Second files into the
    # real data/scenarios/ folder.
    return create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})


@pytest.fixture
def client(app):
    return app.test_client()


def test_labels_capture_load_and_reset(app, client):
    client.post("/api/load", json={"name": "Undo Lab", "areas": {"A1": {"description": "x"}}})
    client.post("/api/reset")
    entries = client.get("/api/undo/list").get_json()["entries"]
    assert entries[0]["label"] == "reset"
    assert any("Undo Lab" in e["label"] for e in entries)


def test_undo_list_newest_first(app, client):
    client.post("/api/load", json={"name": "First"})
    client.post("/api/load", json={"name": "Second"})
    entries = client.get("/api/undo/list").get_json()["entries"]
    assert "Second" in entries[0]["label"]
    assert "First" in entries[1]["label"]


def test_multi_step_undo(app, client):
    """steps=N pops N snapshots; after two undos the world is State A."""
    client.post("/api/load", json={"name": "State A", "areas": {"AA": {"description": "a"}}})
    client.post("/api/load", json={"name": "State B", "areas": {"BB": {"description": "b"}}})
    client.post("/api/load", json={"name": "State C", "areas": {"CC": {"description": "c"}}})
    resp = client.post("/api/undo", json={"steps": 2})
    assert resp.get_json()["steps"] == 2
    names = list(app.world.serializer._serialize_world()["areas"].keys())
    assert "AA" in names and "BB" not in names and "CC" not in names


def test_undo_redo_roundtrip_preserves_labels(app, client):
    client.post("/api/load", json={"name": "L One", "areas": {"R1": {"description": "1"}}})
    client.post("/api/undo", json={})
    assert app._redo_stack  # redo entry carries the label forward
    assert client.post("/api/redo", json={}).get_json()["status"] == "success"


def test_undo_empty_is_400(app, client):
    app._undo_stack.clear()
    assert client.post("/api/undo", json={}).status_code == 400


def test_load_without_persist_does_not_write_scenario(app, client):
    """Ephemeral loads (tests, MCP import) must never create scenario files."""
    scenarios = app.config['DATA_DIR'] + '/scenarios'
    import os
    os.makedirs(scenarios, exist_ok=True)
    client.post("/api/load", json={"name": "Ghost File", "areas": {"G1": {"description": "x"}}})
    assert not os.path.exists(os.path.join(scenarios, "Ghost File.json"))
    # and the world still loaded in-memory
    assert 'G1' in getattr(app.world, 'areas', {}) or any(
        n.name == 'G1' for n in app.world.graph.nodes.values())


def test_load_with_persist_writes_scenario(app, client):
    """GUI scenario loads (persist:true) still write the source file."""
    scenarios = app.config['DATA_DIR'] + '/scenarios'
    import os
    os.makedirs(scenarios, exist_ok=True)
    client.post("/api/load", json={"persist": True, "name": "Kept File", "areas": {"K1": {"description": "y"}}})
    assert os.path.exists(os.path.join(scenarios, "Kept File.json"))
    assert app.world._scenario_name == "Kept File"


def test_graph_edit_pushes_labeled_snapshot(app, client):
    """Every graph mutation now lands in undo history with a label (bug fix:
    minor edits never showed up before)."""
    area = next(n for n in app.world.graph.nodes.values() if n.type == "area")
    client.patch(f"/api/graph/node/{area.id}", json={"properties": {"description": "history test"}})
    entries = client.get("/api/undo/list").get_json()["entries"]
    assert entries and f"edited node {area.id}" in entries[0]["label"]
