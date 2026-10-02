"""One authoritative location record, addressed by id (task-581).

A character or unique item's location is the `in` edge to an area. The
display-name `Player.current_area` is a resolution layer; these tests pin that
the edge is the single record, that it is read/written by id, and that a
disagreeing saved string cannot re-home anyone on load.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from graph import EDGE_IN, Edge, Node, WorldGraph
from player import Player
from virtual_world_engine import VirtualWorld

A = "area_a"
B = "area_b"


def _graph():
    graph = WorldGraph()
    graph.add_node(Node(id=A, type="area", name="Alpha"))
    graph.add_node(Node(id=B, type="area", name="Beta"))
    graph.add_node(Node(id="player_One", type="character", name="One"))
    return graph


def test_area_of_reads_the_location_edge_by_id():
    graph = _graph()
    assert graph.area_of("player_One") is None
    graph.add_edge(Edge(source="player_One", target=A, type=EDGE_IN))
    assert graph.area_of("player_One") == A


def test_set_area_of_keeps_exactly_one_record():
    graph = _graph()
    graph.add_edge(Edge(source="player_One", target=A, type=EDGE_IN))
    graph.set_area_of("player_One", B)

    edges = graph.get_edges_for_source("player_One", EDGE_IN)
    assert len(edges) == 1, "location must be a single record"
    assert edges[0].target == B
    assert graph.area_of("player_One") == B


def test_set_area_of_refuses_a_non_area():
    graph = _graph()
    with pytest.raises(ValueError):
        graph.set_area_of("player_One", "player_One")


def test_a_duplicate_display_name_cannot_rehome_a_character():
    world = VirtualWorld()
    world.player_manager.players = {}
    world.graph.add_node(Node(id="area_a_hollow", type="area", name="Hollow",
                              properties={"environment": {"temperature": 10}}))
    world.graph.add_node(Node(id="area_b_hollow", type="area", name="Hollow",
                              properties={"environment": {"temperature": 30}}))
    player = Player("One")
    world.player_manager.add_player(player)

    world.name_matcher._set_player_area("One", "Hollow")
    node_id = world.player_manager.get_player_node_id("One")

    # Deterministic (smallest id), and the id record agrees with the edge.
    assert world.graph.area_of(node_id) == "area_a_hollow"


def test_payload_exposes_the_canonical_location_id():
    world = VirtualWorld()
    world.player_manager.players = {}
    world.graph.add_node(Node(id=A, type="area", name="Alpha"))
    player = Player("One")
    world.player_manager.add_player(player)
    world.name_matcher._set_player_area("One", "Alpha")

    data = world.to_dict()
    entry = next(iter(data["players"].values()))

    assert entry["current_area_id"] == A
    assert entry["current_area"] == "Alpha"


def test_load_prefers_the_location_edge_over_the_saved_name():
    world = VirtualWorld()
    world.player_manager.players = {}
    world.graph.add_node(Node(id=A, type="area", name="Alpha"))
    world.graph.add_node(Node(id=B, type="area", name="Beta"))
    player = Player("One")
    world.player_manager.add_player(player)
    world.name_matcher._set_player_area("One", "Alpha")
    data = world.to_dict()

    # A hand-edited save where the string disagrees with the edge target.
    for entry in data["players"].values():
        entry["current_area"] = "Beta"

    reloaded = VirtualWorld()
    reloaded.load_from_dict(data)

    assert reloaded.players["One"].current_area == "Alpha", \
        "the graph edge is authoritative, not the string"
    assert reloaded.graph.area_of(reloaded.player_manager.get_player_node_id("One")) == A
