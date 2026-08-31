"""Scenario source status + commit routes (tasks 367/368).

Tests the top-bar chip backend: dirty tracking (edit_seq vs commit_seq) and
writing the live world into data/scenarios/<name>.json.
"""

import json
import os

import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    application = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})
    # TESTING boots from the repo template with _scenario_source pointing at
    # it — detach so commits land in the tmp scenarios dir, never the repo.
    application.world._scenario_source = None
    application.world._scenario_name = None
    application.world._edit_seq = 0
    application.world._commit_seq = 0
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def test_status_no_source(app, client):
    app.world._scenario_source = None
    resp = client.get("/api/scenario/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["name"] == "unnamed"
    assert data["dirty"] is False
    assert data["source"] == ""


def test_commit_creates_scenario_file(app, client, tmp_path):
    resp = client.post("/api/scenario/commit", json={"name": "My Test World"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["name"] == "My Test World"
    path = os.path.join(tmp_path, "scenarios", "My Test World.json")
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        saved = json.load(f)
    assert "areas" in saved and "players" in saved
    assert app.world._scenario_source == path
    assert getattr(app.world, "_commit_seq", 0) == getattr(app.world, "_edit_seq", 0)


def test_status_dirty_then_clean_after_commit(app, client, tmp_path):
    client.post("/api/scenario/commit", json={"name": "Dirty Test"})
    app.world._edit_seq = getattr(app.world, "_edit_seq", 0) + 1  # simulate a mutation
    st = client.get("/api/scenario/status").get_json()
    assert st["dirty"] is True
    client.post("/api/scenario/commit", json={})
    st = client.get("/api/scenario/status").get_json()
    assert st["dirty"] is False
    assert st["name"] == "Dirty Test"


def test_commit_updates_existing_source(app, client, tmp_path):
    client.post("/api/scenario/commit", json={"name": "Update Test"})
    # mutate the live world (description) like an author would
    area = next(iter(app.world.graph.nodes.values()))
    area.properties["description"] = "Rewritten."
    app.world._edit_seq = getattr(app.world, "_edit_seq", 0) + 1
    client.post("/api/scenario/commit", json={})
    path = os.path.join(tmp_path, "scenarios", "Update Test.json")
    with open(path, encoding="utf-8") as f:
        saved = json.load(f)
    assert any(n.get("properties", {}).get("description") == "Rewritten."
               for n in saved["graph"]["nodes"].values())


def test_commit_scrubs_runtime_state(app, client, tmp_path):
    """to_scenario_dict strips game_log/turn_events — commits stay authorial."""
    client.post("/api/scenario/commit", json={"name": "Clean Test"})
    path = os.path.join(tmp_path, "scenarios", "Clean Test.json")
    with open(path, encoding="utf-8") as f:
        saved = json.load(f)
    assert "game_log" not in saved
    assert "turn_events" not in saved
