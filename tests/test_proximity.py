"""Proximity detection tests (task-10): BFS room distance + narrative report."""

from area import Area
from graph import Node, Edge, EDGE_IN


def make_world():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.movement.add_area(Area("Room A", "First room.", []))
    world.movement.add_area(Area("Room B", "Second room.", []))
    world.movement.add_area(Area("Room C", "Third room.", []))
    pname = world.active_player
    world.name_matcher._set_player_area(pname, "Room A")
    return world, pname


def area_id(world, name):
    """Resolve the actual area node id (ids are lowercased)."""
    for node in world.graph.nodes.values():
        if node.type == "area" and node.name == name:
            return node.id
    return None


def connect(world, a, b, way_name):
    way = Node(id=f"way_{way_name.replace(' ', '_')}", type="way", name=way_name,
               properties={"current_state": "open"})
    world.graph.add_node(way)
    world.graph.add_edge(Edge(source=area_id(world, a), target=way.id, type="connection",
                              properties={"direction": "north"}))
    world.graph.add_edge(Edge(source=area_id(world, b), target=way.id, type="connection",
                              properties={"direction": "south"}))
    return way


def test_room_distance_bfs():
    from engine.proximity import room_distance
    world, pname = make_world()
    connect(world, "Room A", "Room B", "door ab")
    connect(world, "Room B", "Room C", "door bc")
    aid = area_id(world, "Room A")
    bid = area_id(world, "Room B")
    cid = area_id(world, "Room C")
    assert room_distance(world.graph, aid, aid) == 0
    assert room_distance(world.graph, aid, bid) == 1
    assert room_distance(world.graph, aid, cid) == 2
    assert room_distance(world.graph, aid, "area_nowhere") is None


def test_report_same_room_sharp_and_adjacent_moderate():
    from engine.proximity import proximity_report
    from player import Player
    world, pname = make_world()
    connect(world, "Room A", "Room B", "door ab")
    item = Node(id="item_emf", type="item", name="EMF Scanner", properties={
        "proximity_effect": {"max_areas": 3, "detects": ["character"]},
    })
    world.graph.add_node(item)
    # a second real player in Room B (adjacent)
    bob = Player()
    bob.name = "Bob"
    bob.current_area = world.player_manager.get_player(pname).current_area  # same Player obj area string
    # move Bob to Room B: give Bob its own area string
    bob.current_area = "Room B"
    world.player_manager.players["Bob"] = bob

    report = proximity_report(world.player_manager, item, world.graph, world)
    assert "needle jumps" in report
    # move Bob next to the player → sharp reading
    bob.current_area = "Room A"
    report2 = proximity_report(world.player_manager, item, world.graph, world)
    assert "right here" in report2
