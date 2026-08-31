"""Scenario append (task-383) + health scan (task-385)."""

import os
import json

import pytest

from app import create_app
from graph import Node, EDGE_IN


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})


@pytest.fixture
def client(app):
    return app.test_client()


def _base_area(app, name):
    g = app.world.graph
    aid = f"area_{name.lower().replace(' ', '_')}"
    g.add_node(Node(id=aid, type="area", name=name, properties={"description": name}))
    return aid


def test_append_adds_new_rooms_and_skips_existing(app, client):
    g = app.world.graph
    _base_area(app, "Existing Hall")
    draft = {
        "name": "Append Test",
        "areas": {
            "Existing Hall": {"description": "should skip", "environment": {}},
            "New Cellar": {"description": "fresh room", "environment": {"temperature": 8}},
            "Other Wing": {"description": "second new one", "environment": {}},
        },
        "characters": [],
        "world_lore": [],
    }
    resp = client.post("/api/scenario/append", json=draft)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "New Cellar" in data["added_areas"]
    assert "Other Wing" in data["added_areas"]
    assert "Existing Hall" in data["skipped_areas"]
    # the existing area keeps its original description (no clobber)
    hall = next(n for n in g.nodes.values() if n.name == "Existing Hall")
    assert hall.properties["description"] == "Existing Hall"
    # new areas exist in the graph
    assert any(n.name == "New Cellar" for n in g.nodes.values())


def test_append_builds_ways_and_items(app, client):
    g = app.world.graph
    draft = {
        "name": "Append Items",
        "areas": {
            "Room A": {
                "description": "a", "environment": {},
                "exits": {"north": {"target": "Room B", "state": "open"}},
                "items": [{"name": "Candlestick", "description": "a candle"}],
            },
            "Room B": {"description": "b", "environment": {}, "exits": {}, "items": []},
        },
        "characters": [],
        "world_lore": [],
    }
    resp = client.post("/api/scenario/append", json=draft)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ways_created"] == 1
    assert data["items_created"] == 1
    assert any(n.type == "way" for n in g.nodes.values())
    assert any(n.type == "item" and n.name == "Candlestick" for n in g.nodes.values())


def test_append_characters_and_lore_no_dupes(app, client):
    draft = {
        "name": "Append Cast",
        "areas": {"Studio": {"description": "x", "environment": {}, "exits": {}, "items": []}},
        "characters": [{"name": "Newbie"}],
        "world_lore": [{"category": "places", "content": "A note about the attic."}],
    }
    resp = client.post("/api/scenario/append", json=draft)
    assert resp.status_code == 200
    d1 = resp.get_json()
    assert "Newbie" in d1["characters_added"]
    assert d1["lore_added"] == 1
    # second append: no dupes
    resp2 = client.post("/api/scenario/append", json=draft)
    d2 = resp2.get_json()
    assert "Newbie" not in d2["characters_added"]
    assert d2["lore_added"] == 0


def test_append_pushes_undo_snapshot(app, client):
    draft = {"areas": {"Undo Room": {"description": "u", "environment": {}, "exits": {}, "items": []}}}
    client.post("/api/scenario/append", json=draft)
    entries = client.get("/api/undo/list").get_json()["entries"]
    assert any("append" in e["label"].lower() for e in entries)


def test_scenarios_health_field(app, client):
    # seed a scenario file directly
    sdir = os.path.join(app.config["DATA_DIR"], "scenarios")
    os.makedirs(sdir, exist_ok=True)
    scenario = {
        "areas": {"Room": {"description": "desc", "environment": {}, "exits": {}}},
        "graph": {
            "nodes": {
                "area_room": {"id": "area_room", "type": "area", "name": "Room", "properties": {"description": "desc"}},
                "way_room_door": {"id": "way_room_door", "type": "way", "name": "Door", "properties": {"current_state": "closed"}},
                "trigger_dead": {"id": "trigger_dead", "type": "logic_trigger", "properties": {}},
            },
            "edges": [
                {"source": "area_room", "target": "way_room_door", "type": "connection"},
                {"source": "area_room", "target": "trigger_missing", "type": "triggers"},
            ],
        },
    }
    with open(os.path.join(sdir, "health_lab.json"), "w", encoding="utf-8") as f:
        json.dump(scenario, f)
    resp = client.get("/api/scenarios")
    assert resp.status_code == 200
    entry = next(s for s in resp.get_json() if s["name"] == "health_lab")
    h = entry["health"]
    assert h["ok"] is True
    assert h["trigger_edges"] == 1
    assert h["dangling_trigger_targets"] == 1  # trigger_missing not in nodes
    assert h["ways_missing_description"] == 1   # way has no description
    assert h["issues"] == 2
