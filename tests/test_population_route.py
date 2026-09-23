"""Tests for the population route (task-9): POST /api/populate/area/<area_id>.

All library writes go to a per-test TEMP data dir so the real data/library is
never touched.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from graph import Node
from routes.helpers import save_registry

LIB = {
    "shelf": {"name": "Shelf", "tags": ["furniture", "display", "kitchen"],
              "actions": ["examine"], "weight": 5, "description": "A shelf."},
    "cabinet": {"name": "Cabinet", "tags": ["furniture", "container", "storage", "kitchen"],
                "actions": ["examine"], "weight": 10, "description": "A cabinet."},
    "bread": {"name": "Bread", "tags": ["food", "kitchen"],
              "actions": ["examine", "take"], "weight": 1, "description": "Bread."},
    "apple": {"name": "Apple", "tags": ["food", "kitchen"],
              "actions": ["examine", "take"], "weight": 1, "description": "An apple."},
    "sword": {"name": "Sword", "tags": ["weapon", "armory"],
              "actions": ["examine", "take"], "weight": 2, "description": "A sword."},
}

SPATIAL = {"in", "on", "under", "behind", "beside", "at"}


def _fresh_app(tmp_path, area_tags=("kitchen", "food"), area_id="area_test_kitchen"):
    data_dir = str(tmp_path)
    os.makedirs(os.path.join(data_dir, "library", "items"), exist_ok=True)
    save_registry(data_dir, "items.json", {k: dict(v) for k, v in LIB.items()})
    app = create_app({"TESTING": True, "DATA_DIR": data_dir})
    app.world.graph.add_node(Node(
        id=area_id, type="area", name="Test Kitchen",
        properties={"tags": list(area_tags), "description": "A test kitchen."}))
    return app.test_client(), app, area_id


def _area_item_count(app, area_id):
    graph = app.world.graph
    count = 0
    for edge in graph.get_edges_for_target(area_id):
        if edge.type in SPATIAL and graph.get_node(edge.source):
            count += 1
    return count


def test_populate_places_furniture_and_items(tmp_path):
    client, app, area_id = _fresh_app(tmp_path)
    res = client.post(f"/api/populate/area/{area_id}", json={"seed": 5})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "populated"
    assert data["placed_furniture"] >= 1
    assert data["placed_items"] >= 1
    assert set(data["furniture"]) <= {"shelf", "cabinet"}
    assert set(data["items"]) <= {"bread", "apple"}
    assert "sword" not in data["items"], "cross-domain item leaked"
    assert _area_item_count(app, area_id) >= 1


def test_populate_is_deterministic_for_seed(tmp_path):
    client, app, area_id = _fresh_app(tmp_path)
    a = client.post(f"/api/populate/area/{area_id}",
                    json={"seed": 9, "preview": True}).get_json()
    b = client.post(f"/api/populate/area/{area_id}",
                    json={"seed": 9, "preview": True}).get_json()
    assert a["status"] == "preview"
    assert a["furniture"] == b["furniture"]
    assert a["items"] == b["items"]


def test_populate_reports_unresolved_domain(tmp_path):
    client, app, area_id = _fresh_app(
        tmp_path, area_tags=("void_domain",), area_id="area_void")
    data = client.post(f"/api/populate/area/{area_id}", json={}).get_json()
    assert data["status"] == "empty"
    assert data["unresolved_domains"] == ["void_domain"]


def test_populate_is_idempotent(tmp_path):
    client, app, area_id = _fresh_app(tmp_path)
    first = client.post(f"/api/populate/area/{area_id}", json={"seed": 3}).get_json()
    assert first["status"] == "populated"
    count_after_first = _area_item_count(app, area_id)

    second = client.post(f"/api/populate/area/{area_id}", json={"seed": 3}).get_json()
    assert second["status"] == "already_populated"
    assert second.get("placed_furniture", 0) == 0
    assert second.get("placed_items", 0) == 0
    assert _area_item_count(app, area_id) == count_after_first


def test_populate_unknown_area_404(tmp_path):
    client, app, _ = _fresh_app(tmp_path)
    res = client.post("/api/populate/area/area_does_not_exist", json={})
    assert res.status_code == 404
