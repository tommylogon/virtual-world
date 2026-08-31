"""Item-gated ways (task-243 shortcuts / task-109 abilities): requires_item
on a way node — a name/id gate ("bike") or a tag gate ("tag:fly")."""

import pytest

from area import Area
from graph import Node, Edge, EDGE_CARRYING, EDGE_IN


def make_world():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.movement.add_area(Area("Room A", "First room.", []))
    world.movement.add_area(Area("Bike Lane", "A fast shortcut.", []))
    world.movement.add_area(Area("Sky Path", "A fly-only route.", []))
    pname = world.active_player
    world.name_matcher._set_player_area(pname, "Room A")
    return world, pname


def area_id(world, name):
    for n in world.graph.nodes.values():
        if n.type == "area" and n.name == name:
            return n.id
    return None


def add_way(world, a, b, name, props=None):
    way = Node(id=f"way_{name.replace(' ', '_')}", type="way", name=name,
               properties={"current_state": "open"})
    if props:
        way.properties.update(props)
    world.graph.add_node(way)
    # Real authoring writes all four connection edges (area ↔ way both ways).
    world.graph.add_edge(Edge(source=area_id(world, a), target=way.id, type="connection",
                              properties={"direction": "north", "visible_in_direction": ""}))
    world.graph.add_edge(Edge(source=way.id, target=area_id(world, b), type="connection",
                              properties={"direction": "north"}))
    world.graph.add_edge(Edge(source=area_id(world, b), target=way.id, type="connection",
                              properties={"direction": "south", "visible_in_direction": ""}))
    world.graph.add_edge(Edge(source=way.id, target=area_id(world, a), type="connection",
                              properties={"direction": "south"}))
    return way


def add_item(world, name, tags=None, place="Room A"):
    n = Node(id=f"item_{name.replace(' ', '_')}", type="item", name=name, properties={
        "name": name, "weight": 1.0, "tags": tags or [], "current_state": "normal",
        "actions": ["take", "use"],
    })
    world.graph.add_node(n)
    world.graph.add_edge(Edge(source=n.id, target=area_id(world, place), type=EDGE_IN))
    return n


def test_blocked_without_item():
    world, pname = make_world()
    add_way(world, "Room A", "Bike Lane", "bike lane", {"requires_item": "bike"})
    with pytest.raises(ValueError, match="bike"):
        world.move_to_area("bike lane")


def test_area_item_satisfies_gate():
    world, pname = make_world()
    add_way(world, "Room A", "Bike Lane", "bike lane", {"requires_item": "bike"})
    add_item(world, "bike")
    result = world.move_to_area("bike lane")
    assert "bike lane" in result.lower() or "north" in result.lower()


def test_carried_item_satisfies_gate():
    world, pname = make_world()
    add_way(world, "Room A", "Bike Lane", "bike lane", {"requires_item": "bike"})
    bike = add_item(world, "bike", place="Room A")
    pid = world._player_node_id(pname)
    world.graph.add_edge(Edge(source=bike.id, target=pid, type=EDGE_CARRYING))
    result = world.move_to_area("bike lane")
    assert isinstance(result, str) and result


def test_tag_gate_requires_ability_item():
    world, pname = make_world()
    add_way(world, "Room A", "Sky Path", "sky path", {"requires_item": "tag:fly"})
    with pytest.raises(ValueError, match="fly"):
        world.move_to_area("sky path")
    wings = add_item(world, "wings", tags=["fly"])
    pid = world._player_node_id(pname)
    world.graph.add_edge(Edge(source=wings.id, target=pid, type=EDGE_CARRYING))
    result = world.move_to_area("sky path")
    assert isinstance(result, str) and result


def test_way_editor_serializes_requires_item():
    from graph import WorldGraph
    g = WorldGraph()
    way = Node(id="way_test", type="way", name="test", properties={"requires_item": "tag:swim"})
    g.add_node(way)
    data = g.to_dict()["nodes"][way.id]
    assert data["properties"].get("requires_item") == "tag:swim"
