"""Chunk lifecycle end-to-end (task-401 umbrella acceptance).

Load two adjacent chunks, move an agent across a gateway, unload and reload
both, and retain exactly one authoritative location — plus a save/load round
trip that preserves gateway links and due events.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import EDGE_CONNECTION, EDGE_IN, Edge, Node
from player import Player
from virtual_world_engine import VirtualWorld

TOWN = "town"
INN = "inn"
TOWN_AREA = "area_town"
INN_AREA = "area_inn_hall"
GATE = "way_gate"


def _inn_payload():
    return {"nodes": {INN_AREA: Node(
        id=INN_AREA, type="area", name="Inn Hall",
        properties={"world_scope_id": INN,
                    "environment": {"temperature": 20, "light": 40}}).to_dict()},
        "edges": []}


def _town_payload():
    nodes = {
        TOWN_AREA: Node(id=TOWN_AREA, type="area", name="Town",
                        properties={"world_scope_id": TOWN,
                                    "environment": {"temperature": 15, "light": 80}}).to_dict(),
        GATE: Node(id=GATE, type="way", name="Inn Door",
                   properties={"world_scope_id": TOWN, "direction": "enter the inn",
                               "return_direction": "leave", "current_state": "open",
                               "target_area_id": INN_AREA,
                               "target_scope_id": INN}).to_dict(),
    }
    edges = [
        {"source": TOWN_AREA, "target": GATE, "type": EDGE_CONNECTION,
         "properties": {"direction": "enter the inn"}},
        {"source": GATE, "target": TOWN_AREA, "type": EDGE_CONNECTION,
         "properties": {"direction": "leave"}},
    ]
    return {"nodes": nodes, "edges": edges}


def _world():
    world = VirtualWorld()
    world.player_manager.players = {}
    world.graph.add_node(Node(
        id=TOWN_AREA, type="area", name="Town",
        properties={"world_scope_id": TOWN,
                    "environment": {"temperature": 15, "light": 80}}))
    world.graph.add_node(Node(
        id=GATE, type="way", name="Inn Door",
        properties={"world_scope_id": TOWN, "direction": "enter the inn",
                    "return_direction": "leave", "current_state": "open",
                    "target_area_id": INN_AREA, "target_scope_id": INN}))
    for source, target, direction in (
            (TOWN_AREA, GATE, "enter the inn"), (GATE, INN_AREA, "enter the inn"),
            (INN_AREA, GATE, "leave"), (GATE, TOWN_AREA, "leave")):
        world.graph.add_edge(Edge(source=source, target=target,
                                  type=EDGE_CONNECTION,
                                  properties={"direction": direction}))
    player = Player("Traveler")
    world.player_manager.add_player(player)
    world.player_manager.active_player = "Traveler"
    world.name_matcher._set_player_area("Traveler", "Town")
    world.world_index.reindex(world.graph, {TOWN: {"id": TOWN}, INN: {"id": INN}})
    slices = {TOWN: _town_payload(), INN: _inn_payload()}
    world.world_index.register_loader(lambda scope_id: slices.get(scope_id))
    return world


def _player_node(world):
    return world.player_manager.get_player_node_id("Traveler")


def test_move_across_a_gateway_loads_the_chunk():
    world = _world()
    assert world.graph.get_node(INN_AREA) is None

    world.move_to_area("enter the inn")

    assert world.graph.get_node(INN_AREA) is not None
    assert world.graph.area_of(_player_node(world)) == INN_AREA


def test_unload_and_reload_retains_exactly_one_location():
    world = _world()
    world.move_to_area("enter the inn")
    node = _player_node(world)

    # Evict both chunks; the character survives and its location is remembered.
    world.world_index.unload(world.graph, TOWN)
    world.world_index.unload(world.graph, INN)
    assert world.graph.get_node(node) is not None
    assert world.world_index.character_location(node) == INN_AREA
    assert world.graph.get_edges_for_source(node, EDGE_IN) == []

    # Reload both; the location edge is restored exactly once.
    assert world.world_index.ensure_scope_loaded(TOWN, world.graph)
    assert world.world_index.ensure_scope_loaded(INN, world.graph)
    location_edges = world.graph.get_edges_for_source(node, EDGE_IN)
    assert len(location_edges) == 1, "exactly one authoritative location"
    assert location_edges[0].target == INN_AREA


def test_save_load_preserves_gateway_links_and_due_events():
    world = _world()
    world.move_to_area("enter the inn")
    world.world_index.schedule({"fire_tick": 42, "target_node_id": INN_AREA,
                                "trigger_type": "on_tick", "label": "due"})

    data = world.to_dict()
    reloaded = VirtualWorld()
    reloaded.load_from_dict(data)

    gateway = reloaded.world_index.gateway(GATE)
    assert gateway is not None, "the gateway link must survive a round trip"
    assert gateway["target_area_id"] == INN_AREA
    assert gateway["target_scope_id"] == INN
    due = [e for e in reloaded.world_index.scheduled()
           if e.get("target_node_id") == INN_AREA]
    assert due and due[0]["fire_tick"] == 42, "due events must not be lost"


def test_gateways_are_not_dead_ui_shortcuts():
    # The gateway names a remote end, and crossing it actually loads that end.
    world = _world()
    assert world.world_index.gateway(GATE)["target_area_id"] == INN_AREA
    world.move_to_area("enter the inn")
    assert world.player.current_area == "Inn Hall"
