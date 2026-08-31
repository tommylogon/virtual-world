"""Presence window tests (task-360 slice): per-area presence ledger
world.area_presence[area][char] = entry_tick, set on movement entry,
persisted through save/load."""

from area import Area


def make_world():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.movement.add_area(Area("Room A", "First room.", []))
    world.movement.add_area(Area("Room B", "Second room.", []))
    pname = world.active_player
    world.name_matcher._set_player_area(pname, "Room A")
    return world, pname


def area_id(world, name):
    for n in world.graph.nodes.values():
        if n.type == "area" and n.name == name:
            return n.id
    return None


def test_presence_records_entry_tick():
    world, pname = make_world()
    world.time_ticks = 7
    world._record_area_presence(pname, "Room A")
    assert world.area_presence.get(area_id(world, "Room A"), {}).get(pname) == 7


def test_movement_updates_presence_ledger():
    world, pname = make_world()
    world.name_matcher._set_player_area(pname, "Room A")
    assert world.area_presence == {}
    world.time_ticks = 4
    # add a way between Room A and Room B
    from graph import Node, Edge
    way = Node(id="way_door", type="way", name="door", properties={"current_state": "open"})
    world.graph.add_node(way)
    aid = area_id(world, "Room A")
    bid = area_id(world, "Room B")
    world.graph.add_edge(Edge(source=aid, target=way.id, type="connection", properties={"direction": "north"}))
    world.graph.add_edge(Edge(source=way.id, target=bid, type="connection", properties={"direction": "north"}))
    world.graph.add_edge(Edge(source=bid, target=way.id, type="connection", properties={"direction": "south"}))
    world.graph.add_edge(Edge(source=way.id, target=aid, type="connection", properties={"direction": "south"}))
    world.move_to_area("north")
    assert world.area_presence.get(bid, {}).get(pname) == 4
    # left Room A -> removed from it
    assert pname not in world.area_presence.get(aid, {})


def test_presence_serializes_and_restores():
    world, pname = make_world()
    world._record_area_presence(pname, "Room B")
    data = world.to_scenario_dict()
    assert data.get("area_presence", {}).get(area_id(world, "Room B")) == {pname: 0}

    world2 = make_world()[0]
    world2.load_from_dict(data)
    assert world2.area_presence.get(area_id(world2, "Room B"), {}).get(pname) is not None
