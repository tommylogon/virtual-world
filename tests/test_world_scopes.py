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


def test_delete_scope_releases_a_hand_placed_area_but_keeps_it():
    """task-528: the cell was reserved by the record being deleted."""
    m = world_scopes.normalise_manifest(MANIFEST)
    g = _graph()
    g.add_node(Node(id="area_hills", type="area", name="Northern Hills",
                    properties={"world_scope_id": "apartment_3b", "tags": ["wild"],
                                "cell": {"x": 2, "y": 3}, "x": 80, "y": 120}))

    result = world_scopes.delete_scope(m, g, "apartment_3b")

    assert result["released_areas"] == ["area_hills"]
    node = g.get_node("area_hills")
    assert node is not None                       # the area itself survives
    assert "cell" not in node.properties          # its reservation is gone
    assert "x" not in node.properties and "y" not in node.properties
    assert node.properties["tags"] == ["wild"]    # unrelated props untouched


def test_delete_scope_leaves_a_placed_area_of_a_survivor_alone():
    m = world_scopes.normalise_manifest(MANIFEST)
    g = _graph()
    g.add_node(Node(id="area_hills", type="area", name="Northern Hills",
                    properties={"world_scope_id": "the_pines", "cell": {"x": 1, "y": 1},
                                "x": 40, "y": 40}))

    world_scopes.delete_scope(m, g, "apartment_3b")
    node = g.get_node("area_hills")
    assert node.properties["cell"] == {"x": 1, "y": 1}


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


# ── promote_to_scope (task-535) ────────────────────────────────────────────

def _promote_manifest():
    """A painted world scope with a village and a road parked on cells."""
    return {
        "world": {
            "id": "world", "name": "World", "kind": "scope", "mode": "world",
            "state": "materialized",
            "grid": {"w": 20, "h": 10, "cell_scale": 1.0},
            "layers": {"biome": {"9,5": "sparse_forest", "17,3": "sparse_forest"},
                       "road": {}},
            "area_ids": ["area_eldenford_village", "area_human_road"],
            "area_placements": {"area_eldenford_village": {"x": 17, "y": 3},
                                "area_human_road": {"x": 9, "y": 5}},
            "placements": {},
            "children": [],
        }
    }


def _promote_graph():
    g = WorldGraph()
    g.add_node(Node(id="area_eldenford_village", type="area", name="Eldenford",
                    properties={"world_scope_id": "world", "cell": {"x": 17, "y": 3}}))
    g.add_node(Node(id="area_human_road", type="area", name="Human Road",
                    properties={"world_scope_id": "world"}))
    g.add_node(Node(id="way_1", type="way", name="A to B"))
    return g


def test_promote_makes_the_areas_a_scope_of_the_parent():
    m, g = _promote_manifest(), _promote_graph()
    res = world_scopes.promote_to_scope(
        m, g, scope_id="eldenford_interior", name="Eldenford",
        area_ids=["area_eldenford_village"], parent_id="world", cell=(17, 3),
        entry_area_id="area_eldenford_village", mode="interior")

    record = m["eldenford_interior"]
    assert res["scope_id"] == "eldenford_interior"
    assert record["parent_id"] == "world" and "eldenford_interior" in m["world"]["children"]
    assert record["entry_area_id"] == "area_eldenford_village"
    assert record["entry_area_name"] == "Eldenford"
    # Authored, not compiled — so Generate and Ungenerate both refuse it.
    assert record["paint_policy"] == "baked"
    # Membership moves at both ends, and the old scope lets go of the cell.
    assert g.get_node("area_eldenford_village").properties["world_scope_id"] == "eldenford_interior"
    assert m["eldenford_interior"]["area_ids"] == ["area_eldenford_village"]
    assert m["world"]["area_ids"] == ["area_human_road"]
    assert m["world"]["area_placements"] == {"area_human_road": {"x": 9, "y": 5}}
    assert res["released_from"] == {"area_eldenford_village": "world"}
    # The painted marker is cleared: inside the scope, position is canvas space.
    assert "cell" not in g.get_node("area_eldenford_village").properties


def test_promote_of_a_placed_area_makes_no_way_to_itself():
    """The selection is the thing on the cell, so there is nothing to walk from.

    A gateway here resolved to the promoted area itself and produced a way named
    "Eldenford - Eldenford" that left and re-entered one area. The scope takes
    the cell and no way is minted; the village's own ways out are its entrance.
    """
    m, g = _promote_manifest(), _promote_graph()
    res = world_scopes.promote_to_scope(
        m, g, scope_id="eldenford_interior", name="Eldenford",
        area_ids=["area_eldenford_village"], parent_id="world", cell=(17, 3),
        entry_area_id="area_eldenford_village", mode="interior")

    assert res["way_id"] == ""
    assert g.get_node("way_gateway_world_eldenford_interior") is None
    assert not [n for n in g.nodes.values()
                if getattr(n, "type", "") == "way" and n.name == "Eldenford - Eldenford"]
    # Placed on the cell, with no gateway claim attached to the placement.
    assert m["world"]["placements"] == {"eldenford_interior": {"x": 17, "y": 3}}


def test_promote_mints_a_gateway_from_a_doorstep_that_stays_in_the_parent():
    m, g = _promote_manifest(), _promote_graph()
    res = world_scopes.promote_to_scope(
        m, g, scope_id="camp_interior", name="goblin camp",
        area_ids=["area_eldenford_village"], parent_id="world", cell=(9, 5),
        entry_area_id="area_eldenford_village", mode="interior")

    way = g.get_node(res["way_id"])
    assert way.name == "Human Road - goblin camp"
    assert way.properties["area_from_id"] == "area_human_road"
    assert way.properties["area_to_id"] == "area_eldenford_village"
    # The author's own way: a parent-stamped `generated` block would let
    # Ungenerate on the parent delete it.
    assert "generated" not in way.properties
    assert way.properties["authored"] is True
    placed = m["world"]["placements"]["camp_interior"]
    assert placed["gateway_from"] == "area_human_road"
    # The road shares the cell with the new scope, which is the one overlap
    # policy that allows it.
    assert m["world"]["area_placements"]["area_human_road"] == {"x": 9, "y": 5}


def test_promote_gateway_survives_ungenerating_the_parent():
    m, g = _promote_manifest(), _promote_graph()
    res = world_scopes.promote_to_scope(
        m, g, scope_id="camp_interior", name="goblin camp",
        area_ids=["area_eldenford_village"], parent_id="world", cell=(9, 5),
        entry_area_id="area_eldenford_village", mode="interior")
    world_scopes.ungenerate_scope(m, g, "world")
    assert g.get_node(res["way_id"]) is not None


def test_promote_refuses_everything_before_it_mutates():
    m, g = _promote_manifest(), _promote_graph()
    before = repr(m)

    def promote(**kw):
        args = {"scope_id": "s", "name": "S", "area_ids": ["area_eldenford_village"],
                "parent_id": "world", "cell": (17, 3)}
        args.update(kw)
        with pytest.raises(ValueError):
            world_scopes.promote_to_scope(m, g, **args)
        assert repr(m) == before, "a refusal must leave the manifest untouched"

    promote(scope_id="")
    promote(name="")
    promote(area_ids=[])
    promote(scope_id="world")
    promote(area_ids=["way_1"])
    promote(area_ids=["nope"])
    promote(entry_area_id="area_human_road")
    promote(cell=(99, 99))
    promote(parent_id="nowhere")
    assert g.get_node("area_eldenford_village").properties["world_scope_id"] == "world"


def test_promote_refuses_a_cell_that_is_not_a_painted_place():
    m, g = _promote_manifest(), _promote_graph()
    with pytest.raises(ValueError, match="painted place"):
        world_scopes.promote_to_scope(
            m, g, scope_id="s", name="S", area_ids=["area_eldenford_village"],
            parent_id="world", cell=(4, 4),
            entry_area_id="area_eldenford_village")


def test_promote_without_a_parent_groups_without_placing():
    m, g = _promote_manifest(), _promote_graph()
    res = world_scopes.promote_to_scope(
        m, g, scope_id="grouping", name="Grouping",
        area_ids=["area_eldenford_village"], entry_area_id="area_eldenford_village")
    assert res["way_id"] == "" and res["cell"] is None
    assert "grouping" not in m["world"]["placements"]
    assert m["grouping"]["parent_id"] is None


def test_promote_entry_defaults_to_the_first_selected_area_by_id():
    m, g = _promote_manifest(), _promote_graph()
    m["world"]["area_ids"].append("area_barn")
    g.add_node(Node(id="area_barn", type="area", name="Barn",
                    properties={"world_scope_id": "world"}))
    res = world_scopes.promote_to_scope(
        m, g, scope_id="stead", name="Stead", parent_id="world",
        area_ids=["area_barn", "area_eldenford_village"])
    # Deterministic, and not "top-left-most" as the compiler picks.
    assert res["entry_area_id"] == "area_barn"

