"""Tests for world scopes and scoped projections (task-397)."""

import sys
from types import SimpleNamespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

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


def test_project_subgraph_keeps_only_scope_members():
    m = world_scopes.normalise_manifest(MANIFEST)
    out = world_scopes.project_subgraph(m, _graph(), _players(), "apartment_3b")
    # Only the leaf area is inside; the hallway way crosses the boundary.
    assert set(out["nodes"]) == {"area_3b_living", "item_sofa"}
    assert out["edges"] == [{"source": "item_sofa", "target": "area_3b_living",
                             "type": "in", "properties": {}}]


def test_own_area_ids_ignores_descendants():
    g = _graph()
    assert world_scopes.own_area_ids(g, "pines_floor_3") == {"area_hall3"}
    assert world_scopes.own_area_ids(g, "the_pines") == set()


def test_project_subgraph_is_level_scoped_by_default():
    m = world_scopes.normalise_manifest(MANIFEST)
    g = _graph()
    # pines_floor_3 owns area_hall3; apartment_3b (a descendant) is not pulled in.
    out = world_scopes.project_subgraph(m, g, _players(), "pines_floor_3")
    assert set(out["nodes"]) == {"area_hall3"}
    # An organisational scope with no painted cells of its own shows nothing.
    assert world_scopes.project_subgraph(m, g, _players(), "the_pines")["nodes"] == {}


def test_project_subgraph_descendants_includes_the_subtree():
    m = world_scopes.normalise_manifest(MANIFEST)
    out = world_scopes.project_subgraph(m, _graph(), _players(), "the_pines",
                                        descendants=True)
    assert {"area_hall3", "area_3b_living", "way_hall3_3b"} <= set(out["nodes"])
    # A way with one endpoint outside the scope is a boundary way, not a member.
    assert "way_outside" not in out["nodes"]
    # No edge may dangle to a node the caller never received.
    for edge in out["edges"]:
        assert edge["source"] in out["nodes"]
        assert edge["target"] in out["nodes"]


def test_project_subgraph_respects_include_items():
    m = world_scopes.normalise_manifest(MANIFEST)
    out = world_scopes.project_subgraph(m, _graph(), _players(), "apartment_3b",
                                        include_items=False)
    assert "item_sofa" not in out["nodes"]
    assert out["edges"] == []


def test_flat_scopes_lists_depth_first_with_depth():
    m = world_scopes.normalise_manifest(MANIFEST)
    flat = world_scopes.flat_scopes(m, _graph(), _players())
    by_id = {s["id"]: s["depth"] for s in flat}
    assert by_id["millbrook_falls"] == 0
    assert by_id["the_pines"] == 2
    assert by_id["apartment_3b"] == 4


def test_rename_scope_changes_the_display_name_only():
    m = world_scopes.normalise_manifest(MANIFEST)
    rec = world_scopes.rename_scope(m, "apartment_3b", "Apartment 3C")
    assert rec["name"] == "Apartment 3C"
    assert "apartment_3b" in m          # the id — and every reference — stays
    with pytest.raises(ValueError):
        world_scopes.rename_scope(m, "ghost", "x")
    with pytest.raises(ValueError):
        world_scopes.rename_scope(m, "apartment_3b", "   ")


def test_delete_scope_refuses_a_scope_with_children_unless_cascading():
    m = world_scopes.normalise_manifest(MANIFEST)
    with pytest.raises(ValueError):
        world_scopes.delete_scope(m, _graph(), "the_pines")
    assert "the_pines" in m


def test_delete_scope_unplaces_and_removes_generated_nodes_only():
    m = world_scopes.normalise_manifest(MANIFEST)
    m["pines_floor_3"]["placements"] = {"apartment_3b": {"x": 1, "y": 1}}
    g = _graph()
    g.add_node(Node(id="area_gen", type="area", name="Gen",
                    properties={"generated": {"scope_id": "apartment_3b"}}))
    g.add_node(Node(id="area_hand", type="area", name="Hand",
                    properties={"world_scope_id": "apartment_3b"}))

    result = world_scopes.delete_scope(m, g, "apartment_3b")

    assert result["scope_ids"] == ["apartment_3b"]
    assert result["deleted_nodes"] == 1
    assert "apartment_3b" not in m
    assert "apartment_3b" not in m["pines_floor_3"].get("placements", {})
    assert g.get_node("area_gen") is None        # generated → deleted
    assert g.get_node("area_hand") is not None   # hand-authored → left alone


def test_delete_scope_cascades_to_descendants():
    m = world_scopes.normalise_manifest(MANIFEST)
    result = world_scopes.delete_scope(m, _graph(), "the_pines", cascade=True)
    assert set(result["scope_ids"]) == {"the_pines", "pines_floor_3", "apartment_3b"}
    for dead in result["scope_ids"]:
        assert dead not in m


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

    flat = client.get("/api/world/scopes?flat=1").get_json()
    assert flat["scopes"][0]["id"] == "millbrook_falls"

    sub = client.get("/api/world/scopes/apartment_3b/subgraph").get_json()
    assert sub["scope"]["id"] == "apartment_3b"
    assert set(sub["nodes"]) == {"area_3b_living"}

    # Level-scoped by default: a parent is not flattened into its subtree.
    assert client.get("/api/world/scopes/the_pines/subgraph").get_json()["nodes"] == {}
    deep = client.get(
        "/api/world/scopes/the_pines/subgraph?descendants=1").get_json()
    assert "area_3b_living" in deep["nodes"]

    assert client.get("/api/world/scopes/nope/subgraph").status_code == 404

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
