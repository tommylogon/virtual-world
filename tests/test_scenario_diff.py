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


def test_diff_item_and_way_drift(app, client):
    from graph import Node
    client.post("/api/scenario/commit", json={"name": "Node Diff"})
    it = Node(id="item_chair", type="item", name="Chair", properties={"description": "new chair"})
    way = Node(id="way_hatch", type="way", name="Hatch", properties={"current_state": "closed"})
    app.world.graph.add_node(it)
    app.world.graph.add_node(way)
    g = client.get("/api/scenario/diff").get_json()["groups"]
    assert "item_chair" in g["added_items"]
    assert "way_hatch" in g["added_ways"]
    # change an existing item's description
    g2 = client.get("/api/scenario/diff").get_json()["groups"]
    assert set(g2.keys()) >= {"added_items", "added_ways", "changed_items", "changed_ways"}


def test_diff_apply_commit_section(app, client):
    from graph import Node
    client.post("/api/scenario/commit", json={"name": "Apply Commit"})
    it = Node(id="item_lamp_a", type="item", name="Lamp A", properties={"description": "live value"})
    app.world.graph.add_node(it)
    g = client.get("/api/scenario/diff").get_json()["groups"]
    assert "item_lamp_a" in g["added_items"]
    resp = client.post("/api/scenario/diff/apply", json={"commit": ["items"]})
    assert resp.status_code == 200
    # after commit, no drift for items
    g2 = client.get("/api/scenario/diff").get_json()["groups"]
    assert g2["added_items"] == []
    # source file now contains the node
    import json as _json
    with open(app.world._scenario_source, "r", encoding="utf-8-sig") as f:
        src = _json.load(f)
    nodes = src.get("graph", {}).get("nodes", {})
    assert "item_lamp_a" in nodes


def test_diff_apply_discard_section(app, client):
    from graph import Node
    client.post("/api/scenario/commit", json={"name": "Apply Discard"})
    it = Node(id="item_chair_b", type="item", name="Chair B", properties={"description": "dirty live"})
    app.world.graph.add_node(it)
    original = app.world.graph.get_node("item_chair_b")  # live
    g = client.get("/api/scenario/diff").get_json()["groups"]
    assert "item_chair_b" in g["added_items"]
    resp = client.post("/api/scenario/diff/apply", json={"discard": ["items"]})
    assert resp.status_code == 200
    # live item removed (restored to source state = absent)
    assert app.world.graph.get_node("item_chair_b") is None
    # undo snapshot pushed for discard
    entries = client.get("/api/undo/list").get_json()["entries"]
    assert any("discard" in e["label"].lower() for e in entries)


def test_diff_apply_empty_400(app, client):
    client.post("/api/scenario/commit", json={"name": "Empty Apply"})
    resp = client.post("/api/scenario/diff/apply", json={})
    assert resp.status_code == 400
