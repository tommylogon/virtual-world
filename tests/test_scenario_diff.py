"""Scenario diff endpoint (task-373): live world vs scenario source."""

import os

import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    application = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})
    application.world._scenario_source = None
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def test_diff_no_source(app, client):
    resp = client.get("/api/scenario/diff")
    assert resp.get_json()["source"] is None


def test_diff_shows_changes_after_commit_then_edit(app, client, tmp_path):
    client.post("/api/scenario/commit", json={"name": "Diff Lab"})
    # no changes right after commit
    g = client.get("/api/scenario/diff").get_json()["groups"]
    assert g["added_areas"] == [] and g["changed_areas"] == []
    # mutate: rename an area + edit another's description
    area = next(n for n in app.world.graph.nodes.values() if n.type == "area")
    area.properties["environment"] = {"temperature": -5}
    node = app.world.graph.get_node(area.id)
    node.properties["description"] = "Changed."
    g = client.get("/api/scenario/diff").get_json()["groups"]
    assert area.name in g["changed_areas"]


def test_diff_detects_added_and_removed_areas(app, client):
    from graph import Node, EDGE_IN
    client.post("/api/scenario/commit", json={"name": "Area Diff"})
    node = Node(id="area_extra_room", type="area", name="Extra Room", properties={"description": "new"})
    app.world.graph.add_node(node)
    g = client.get("/api/scenario/diff").get_json()["groups"]
    assert "Extra Room" in g["added_areas"]


def test_diff_player_drift(app, client):
    client.post("/api/scenario/commit", json={"name": "Player Diff"})
    client.post("/api/players", json={"name": "Yolo", "current_area": "Foyer"})
    g = client.get("/api/scenario/diff").get_json()["groups"]
    assert "Yolo" in g["added_players"]
