"""Global scope index and load-before-you-move (task-583).

The index survives an evicted scope: ownership, character/item location,
gateway targets and due work. A gateway names its remote target_area_id and
target_scope_id, and movement materialises the destination scope before it
resolves the way.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.world.index import GlobalScopeIndex
from graph import EDGE_CONNECTION, EDGE_IN, Edge, Node, WorldGraph
from player import Player
from virtual_world_engine import VirtualWorld


def _indexed_graph():
    graph = WorldGraph()
    manifest = {"town": {"id": "town", "parent_id": "world"}}
    graph.add_node(Node(id="area_town", type="area", name="Town",
                        properties={"world_scope_id": "town"}))
    graph.add_node(Node(id="way_gate", type="way", name="Inn Door",
                        properties={"target_area_id": "area_inn_hall",
                                    "target_scope_id": "inn",
                                    "world_scope_id": "town"}))
    graph.add_node(Node(id="player_Traveler", type="character", name="Traveler"))
    graph.add_edge(Edge(source="player_Traveler", target="area_town", type=EDGE_IN))
    graph.add_node(Node(id="item_lamp", type="item", name="Lamp"))
    graph.add_edge(Edge(source="item_lamp", target="area_town", type=EDGE_IN))
    index = GlobalScopeIndex()
    index.reindex(graph, manifest)
    return graph, index


def test_reindex_derives_ownership_location_and_gateways():
    _graph, index = _indexed_graph()
    assert index.scope_for_area("area_town") == "town"
    assert index.areas_in_scope("town") == ["area_town"]
    assert index.scope_parent("town") == "world"
    assert index.character_location("player_Traveler") == "area_town"
    assert index.item_location("item_lamp") == "area_town"
    gateway = index.gateway("way_gate")
    assert gateway["target_area_id"] == "area_inn_hall"
    assert gateway["target_scope_id"] == "inn"


def test_index_round_trips_through_dict():
    _graph, index = _indexed_graph()
    index.schedule({"fire_tick": 10, "target_node_id": "item_lamp"})
    restored = GlobalScopeIndex.from_dict(index.to_dict())
    assert restored.scope_for_area("area_town") == "town"
    assert restored.character_location("player_Traveler") == "area_town"
    assert restored.gateway("way_gate")["target_scope_id"] == "inn"
    assert restored.scheduled()[0]["fire_tick"] == 10


def test_augment_keeps_entries_for_unloaded_scopes():
    index = GlobalScopeIndex()
    index.own_area("area_faraway", "far")
    index.augment_from_graph(WorldGraph(), {})
    assert index.scope_for_area("area_faraway") == "far"


def test_ensure_destination_loads_the_target_scope():
    index = GlobalScopeIndex()
    index.add_gateway("way_gate", target_area_id="area_inn_hall",
                      target_scope_id="inn")
    graph = WorldGraph()
    payload = {"nodes": {"area_inn_hall": Node(
        id="area_inn_hall", type="area", name="Inn Hall",
        properties={"world_scope_id": "inn"}).to_dict()}, "edges": []}
    index.register_loader(lambda scope_id: payload if scope_id == "inn" else None)

    target = index.ensure_destination_loaded(graph, "way_gate")

    assert target == "area_inn_hall"
    assert graph.get_node("area_inn_hall") is not None


def test_ensure_destination_without_a_loader_is_a_clean_refusal():
    index = GlobalScopeIndex()
    index.add_gateway("way_gate", target_area_id="area_inn_hall",
                      target_scope_id="inn")
    graph = WorldGraph()
    assert index.ensure_destination_loaded(graph, "way_gate") is None
    assert graph.get_node("area_inn_hall") is None
    # A non-gateway way is never touched.
    assert index.ensure_destination_loaded(graph, "way_plain") is None


def test_due_events_are_returned_and_removed():
    index = GlobalScopeIndex()
    index.schedule({"fire_tick": 5, "target_node_id": "a"})
    index.schedule({"fire_tick": 50, "target_node_id": "b"})
    assert [e["target_node_id"] for e in index.due_events(5)] == ["a"]
    assert [e["target_node_id"] for e in index.due_events(100)] == ["b"]


# ── load-before-you-move, end to end ────────────────────────────────────


def _world_with_gateway_to_unloaded_inn():
    world = VirtualWorld()
    world.player_manager.players = {}
    world.graph.add_node(Node(
        id="area_town", type="area", name="Town",
        properties={"world_scope_id": "town",
                    "environment": {"temperature": 15, "light": 80}}))
    world.graph.add_node(Node(
        id="way_gate", type="way", name="Inn Door",
        properties={"world_scope_id": "town",
                    "direction": "enter the inn",
                    "return_direction": "leave",
                    "current_state": "open",
                    "target_area_id": "area_inn_hall",
                    "target_scope_id": "inn"}))
    world.graph.add_edge(Edge(source="area_town", target="way_gate",
                              type=EDGE_CONNECTION, properties={"direction": "enter the inn"}))
    world.graph.add_edge(Edge(source="way_gate", target="area_inn_hall",
                              type=EDGE_CONNECTION, properties={"direction": "enter the inn"}))
    world.graph.add_edge(Edge(source="area_inn_hall", target="way_gate",
                              type=EDGE_CONNECTION, properties={"direction": "leave"}))
    world.graph.add_edge(Edge(source="way_gate", target="area_town",
                              type=EDGE_CONNECTION, properties={"direction": "leave"}))
    player = Player("Traveler")
    world.player_manager.add_player(player)
    world.player_manager.active_player = "Traveler"
    world.name_matcher._set_player_area("Traveler", "Town")

    child = {"nodes": {"area_inn_hall": Node(
        id="area_inn_hall", type="area", name="Inn Hall",
        properties={"world_scope_id": "inn",
                    "environment": {"temperature": 20, "light": 40}}).to_dict()},
        "edges": []}
    world.world_index.reindex(world.graph, {"town": {"id": "town"}})
    world.world_index.register_loader(lambda scope_id: child if scope_id == "inn" else None)
    return world


def test_crossing_a_gateway_loads_the_destination_scope():
    world = _world_with_gateway_to_unloaded_inn()
    assert world.graph.get_node("area_inn_hall") is None, "premise: inn is unloaded"

    world.move_to_area("enter the inn")

    assert world.graph.get_node("area_inn_hall") is not None
    assert world.player.current_area == "Inn Hall"


def test_crossing_a_gateway_with_no_loader_refuses_cleanly():
    world = _world_with_gateway_to_unloaded_inn()
    world.world_index.register_loader(lambda scope_id: None)
    try:
        world.move_to_area("enter the inn")
    except ValueError as exc:
        assert "not loaded" in str(exc)
    else:
        raise AssertionError("an unloadable destination must not silently succeed")
    assert world.player.current_area == "Town"


# ── the compiler names the remote end ───────────────────────────────────


def test_compiled_gateway_names_target_area_and_scope():
    from engine import world_compile

    node, _edges = world_compile._gateway(
        "town", "inn", "area_town_0_0", "Town", "area_inn_0_0", "Inn Hall",
        "The Inn", "grid.v1", "seed", 0)
    assert node.properties["target_area_id"] == "area_inn_0_0"
    assert node.properties["target_scope_id"] == "inn"
