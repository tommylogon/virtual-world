"""Scope/chunk load, unload and merge on WorldGraph (task-582).

`load_from_dict()` clears the whole graph, so it cannot materialise one scope
into a live world. These operations add a scope slice and remove it again
without touching another scope's nodes, and they refuse an operation that would
touch a node this scope does not own.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from graph import EDGE_CONNECTION, EDGE_IN, Edge, Node, ScopeOwnershipError, WorldGraph


def _area(area_id, scope, name=None):
    return Node(id=area_id, type="area", name=name or area_id,
                properties={"world_scope_id": scope})


def _alpha():
    a = _area("area_alpha_0_0", "alpha", "Alpha Field")
    b = _area("area_alpha_1_0", "alpha", "Alpha Wood")
    way = Node(id="way_alpha", type="way", name="Alpha Path",
               properties={"world_scope_id": "alpha"})
    edges = [Edge(source=a.id, target=way.id, type=EDGE_CONNECTION),
             Edge(source=way.id, target=b.id, type=EDGE_CONNECTION)]
    return {"nodes": {n.id: n.to_dict() for n in (a, b, way)}, "edges": [e.to_dict() for e in edges]}


def _beta():
    area = _area("area_beta_0_0", "beta", "Beta Field")
    return {"nodes": {area.id: area.to_dict()}, "edges": []}


def test_merge_adds_a_scope_without_touching_the_rest():
    graph = WorldGraph()
    graph.merge_scope("beta", _beta())

    result = graph.merge_scope("alpha", _alpha())

    assert result["scope_id"] == "alpha"
    assert set(result["added"]) == {"area_alpha_0_0", "area_alpha_1_0", "way_alpha"}
    assert graph.get_node("area_beta_0_0") is not None
    assert graph.get_node("way_alpha") is not None
    assert len(graph.get_edges_for_source("way_alpha", EDGE_CONNECTION)) == 1
    assert graph.is_scope_loaded("alpha") and graph.is_scope_loaded("beta")


def test_scope_owners_groups_by_owner():
    graph = WorldGraph()
    graph.merge_scope("alpha", _alpha())
    graph.merge_scope("beta", _beta())
    owners = graph.scope_owners()
    assert owners["alpha"] == ["area_alpha_0_0", "area_alpha_1_0", "way_alpha"]
    assert owners["beta"] == ["area_beta_0_0"]


def test_loading_the_same_scope_twice_is_refused():
    graph = WorldGraph()
    graph.merge_scope("alpha", _alpha())
    with pytest.raises(ScopeOwnershipError, match="already loaded"):
        graph.merge_scope("alpha", _alpha())
    # Rejected before mutating: still exactly one copy.
    assert len([n for n in graph.nodes.values() if n.type == "area"]) == 2


def test_reload_with_replace_restamps_in_place():
    graph = WorldGraph()
    graph.merge_scope("alpha", _alpha())
    changed = _alpha()
    changed["nodes"]["area_alpha_0_0"]["properties"]["description"] = "revision"
    result = graph.merge_scope("alpha", changed, replace=True)
    assert set(result["replaced"]) == {"area_alpha_0_0", "area_alpha_1_0", "way_alpha"}
    assert set(result["added"]) == set()
    assert graph.get_node("area_alpha_0_0").properties["description"] == "revision"
    assert len(graph.nodes) == 3


def test_merge_refuses_a_node_owned_by_another_scope():
    graph = WorldGraph()
    graph.merge_scope("beta", _beta())
    hostile = _alpha()
    hostile["nodes"]["area_beta_0_0"] = _area("area_beta_0_0", "alpha").to_dict()
    with pytest.raises(ScopeOwnershipError):
        graph.merge_scope("alpha", hostile)
    assert graph.get_node("area_beta_0_0").properties["world_scope_id"] == "beta"


def test_merge_refuses_a_node_declaring_a_different_scope():
    graph = WorldGraph()
    data = _alpha()
    data["nodes"]["area_lier"] = _area("area_lier", "beta").to_dict()
    with pytest.raises(ScopeOwnershipError, match="declares scope 'beta'"):
        graph.merge_scope("alpha", data)
    assert graph.get_node("area_lier") is None


def test_unload_removes_only_the_named_scope():
    graph = WorldGraph()
    graph.merge_scope("alpha", _alpha())
    graph.merge_scope("beta", _beta())
    graph.add_node(Node(id="player_one", type="character", name="One"))
    graph.add_edge(Edge(source="player_one", target="area_alpha_0_0", type=EDGE_IN))

    result = graph.unload_scope("alpha")

    assert set(result["removed"]) == {"area_alpha_0_0", "area_alpha_1_0", "way_alpha"}
    assert result["edges_removed"] >= 1
    assert graph.get_node("area_beta_0_0") is not None
    # A scope-less node is never unloaded; only its edge into the scope is.
    assert graph.get_node("player_one") is not None
    assert graph.get_edges_for_source("player_one", EDGE_IN) == []
    assert not graph.is_scope_loaded("alpha") and graph.is_scope_loaded("beta")


def test_slice_round_trips_through_unload_and_merge():
    graph = WorldGraph()
    graph.merge_scope("alpha", _alpha())
    slice_data = graph.slice_scope("alpha")
    assert set(slice_data["nodes"]) == {"area_alpha_0_0", "area_alpha_1_0", "way_alpha"}
    assert len(slice_data["edges"]) == 2

    graph.unload_scope("alpha")
    assert not graph.is_scope_loaded("alpha")

    graph.merge_scope("alpha", slice_data)
    assert graph.is_scope_loaded("alpha")
    assert graph.get_node("way_alpha") is not None
    assert len(graph.get_edges_for_source("way_alpha", EDGE_CONNECTION)) == 1


def test_scope_id_is_required():
    graph = WorldGraph()
    with pytest.raises(ScopeOwnershipError):
        graph.merge_scope("", {"nodes": {}, "edges": []})
    with pytest.raises(ScopeOwnershipError):
        graph.unload_scope("")
