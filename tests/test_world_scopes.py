"""Tests for world scopes and scoped projections (task-397)."""

import sys
from types import SimpleNamespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import world_scopes
from graph import Edge, Node, WorldGraph

MANIFEST = {
    "millbrook_falls": {"id": "millbrook_falls", "name": "Millbrook Falls",
                        "kind": "settlement", "children": ["downtown", "the_pines"]},
    "downtown": {"id": "downtown", "name": "Downtown District",
                 "kind": "district", "parent_id": "millbrook_falls"},
    "the_pines": {"id": "the_pines", "name": "The Pines Apartment Complex",
                  "kind": "building", "parent_id": "downtown",
                  "children": ["pines_floor_3"]},
    "pines_floor_3": {"id": "pines_floor_3", "name": "Floor 3", "kind": "floor",
                      "parent_id": "the_pines", "children": ["apartment_3b"]},
    "apartment_3b": {"id": "apartment_3b", "name": "Apartment 3B",
                     "kind": "apartment", "parent_id": "pines_floor_3",
                     "state": "unmade", "area_ids": ["area_3b_living"]},
}


def _graph():
    g = WorldGraph()
    g.add_node(Node(id="area_hall3", type="area", name="Hallway 3",
                    properties={"world_scope_id": "pines_floor_3"}))
    g.add_node(Node(id="area_3b_living", type="area", name="3B Living",
                    properties={"world_scope_id": "apartment_3b"}))
    g.add_node(Node(id="item_sofa", type="item", name="Sofa", properties={"tags": ["furniture"]}))
    g.add_edge(Edge(source="item_sofa", target="area_3b_living", type="in"))
    g.add_node(Node(id="way_hall3_3b", type="way", name="Hallway 3 to 3B",
                    properties={"area_from": "area_hall3", "area_to": "area_3b_living"}))
    g.add_node(Node(id="way_outside", type="way", name="Outside to Hallway 3",
                    properties={"area_from": "area_outside", "area_to": "area_hall3"}))
    return g


def _players():
    return {"alice": SimpleNamespace(current_area="3B Living", name="Alice")}


def test_root_scopes_are_parentless():
    m = world_scopes.normalise_manifest(MANIFEST)
    assert world_scopes.root_scope_ids(m) == ["millbrook_falls"]


def test_direct_children_union_declared_and_parent_field():
    m = world_scopes.normalise_manifest(MANIFEST)
    assert world_scopes.direct_child_ids(m, "the_pines") == ["pines_floor_3"]
    # downtown declares no children but is parented to millbrook_falls
    assert "downtown" in world_scopes.direct_child_ids(m, "millbrook_falls")


def test_area_ids_recurse_through_children():
    m = world_scopes.normalise_manifest(MANIFEST)
    g = _graph()
    assert world_scopes.area_ids_in_scope(m, g, "apartment_3b") == {"area_3b_living"}
    assert world_scopes.area_ids_in_scope(m, g, "the_pines") == {"area_hall3", "area_3b_living"}
    assert world_scopes.area_ids_in_scope(m, g, "millbrook_falls") == {"area_hall3", "area_3b_living"}


def test_scope_summary_counts_and_state():
    m = world_scopes.normalise_manifest(MANIFEST)
    card = world_scopes.scope_summary(m, _graph(), _players(), "apartment_3b")
    assert card["state"] == "unmade"
    assert card["area_count"] == 1
    assert card["item_count"] == 1
    assert card["character_count"] == 1
    assert card["has_character"] is True


def test_project_root_lists_top_scopes_only():
    m = world_scopes.normalise_manifest(MANIFEST)
    out = world_scopes.project(m, _graph(), _players(), "root")
    assert out["scope"] is None
    assert [c["id"] for c in out["children"]] == ["millbrook_falls"]


def test_project_building_returns_child_cards_not_leaf_nodes():
    m = world_scopes.normalise_manifest(MANIFEST)
    out = world_scopes.project(m, _graph(), _players(), "the_pines")
    assert [c["id"] for c in out["children"]] == ["pines_floor_3"]
    assert "nodes" not in out


def test_project_leaf_returns_areas_and_boundary_ways():
    m = world_scopes.normalise_manifest(MANIFEST)
    out = world_scopes.project(m, _graph(), _players(), "apartment_3b", include_items=True)
    area_ids = [a["id"] for a in out["areas"]]
    assert area_ids == ["area_3b_living"]
    assert [w["id"] for w in out["ways"]] == ["way_hall3_3b"]
    assert out["ways"][0]["outside"] == "area_hall3"


def test_project_leaf_include_items_emits_spatial_nodes():
    m = world_scopes.normalise_manifest(MANIFEST)
    out = world_scopes.project(m, _graph(), _players(), "apartment_3b", include_items=True)
    assert "item_sofa" in out["nodes"]
    assert {"source": "item_sofa", "target": "area_3b_living",
            "type": "in", "properties": {}} in out["edges"]


def test_missing_manifest_is_safe():
    m = world_scopes.normalise_manifest(None)
    out = world_scopes.project(m, _graph(), _players(), "root")
    assert out["scope"] is None and out["children"] == []


def test_route_scope_endpoints(tmp_path):
    from app import create_app
    app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})
    app.world.world_scopes = dict(MANIFEST)
    app.world.graph.add_node(Node(
        id="area_3b_living", type="area", name="3B Living",
        properties={"world_scope_id": "apartment_3b", "tags": ["residential"]}))
    client = app.test_client()

    root = client.get("/api/world/scopes").get_json()
    assert [c["id"] for c in root["children"]] == ["millbrook_falls"]

    detail = client.get("/api/world/scopes/the_pines").get_json()
    assert [c["id"] for c in detail["children"]] == ["pines_floor_3"]

    graph_view = client.get(
        "/api/world/scopes/apartment_3b/graph?include_items=1").get_json()
    assert [a["id"] for a in graph_view["areas"]] == ["area_3b_living"]

    assert client.get("/api/world/scopes/nope").status_code == 404


def _minimal_scenario(extra=None):
    scenario = {
        "active_player": "alice",
        "players": {"alice": {"name": "Alice", "current_area": "3B Living",
                              "vitals": {}, "stats": {}, "skills": {}, "tags": []}},
        "graph": {"nodes": {
            "area_3b_living": {"id": "area_3b_living", "type": "area",
                               "name": "3B Living",
                               "properties": {"world_scope_id": "apartment_3b"}},
        }, "edges": []},
    }
    scenario.update(extra or {})
    return scenario


def test_manifest_survives_scenario_load(tmp_path):
    from app import create_app
    app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})
    client = app.test_client()
    scenario = _minimal_scenario({
        "world_scopes": {"apartment_3b": {"id": "apartment_3b", "name": "Apartment 3B",
                                          "kind": "apartment", "state": "unmade"}},
    })
    assert client.post("/api/load", json=scenario).status_code == 200
    data = client.get("/api/world/scopes/apartment_3b").get_json()
    assert data["scope"]["name"] == "Apartment 3B"
    assert data["scope"]["state"] == "unmade"


def test_load_without_manifest_is_backward_compatible(tmp_path):
    from app import create_app
    app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})
    client = app.test_client()
    assert client.post("/api/load", json=_minimal_scenario()).status_code == 200
    root = client.get("/api/world/scopes").get_json()
    assert root["scope"] is None and root["children"] == []
