"""Functional smoke for engine/area_statuses.py (task-233)."""
import sys
sys.path.insert(0, '.')

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


def test_apply_and_tick_fire():
    world, pname = make_world()
    aid = area_id(world, "Room A")
    ok = world.area_statuses.apply_status(aid, "on_fire", severity=2, duration=3, source="test")
    assert ok, "apply_status failed"
    area = world.graph.get_node(aid)
    temp0 = area.properties["environment"].get("temperature", 21)
    world.area_statuses.process_tick()
    temp1 = area.properties["environment"].get("temperature")
    assert temp1 > temp0, f"temperature did not rise: {temp0} -> {temp1}"
    assert area.properties["environment"].get("air") == "smoke"
    # duration ticks down
    assert area.properties["statuses"][0]["duration"] == 2
    # expiry after duration runs out
    world.area_statuses.process_tick()
    world.area_statuses.process_tick()
    assert area.properties["statuses"] == [], "status should have expired"


def test_damage_applies_to_present_character():
    world, pname = make_world()
    aid = area_id(world, "Room A")
    world.area_statuses.apply_status(aid, "poison_gas", severity=1)
    hp0 = world.players[pname].vitals["HP"]
    world.area_statuses.process_tick()
    assert world.players[pname].vitals["HP"] < hp0, "character took no damage"
    cond = world.players[pname].conditions
    assert cond.get("poisoned"), "poisoned condition not applied"


def test_propagation_through_open_ways():
    world, pname = make_world()
    from graph import Node, Edge
    way = Node(id="way_door", type="way", name="door", properties={"current_state": "open"})
    world.graph.add_node(way)
    aid, bid = area_id(world, "Room A"), area_id(world, "Room B")
    world.graph.add_edge(Edge(source=aid, target=way.id, type="connection"))
    world.graph.add_edge(Edge(source=way.id, target=bid, type="connection"))
    world.graph.add_edge(Edge(source=bid, target=way.id, type="connection"))
    world.graph.add_edge(Edge(source=way.id, target=aid, type="connection"))
    world.area_statuses.apply_status(aid, "smoke", severity=1)
    # force propagation deterministically
    import engine.area_statuses as mod
    old_random = mod.random.random
    mod.random.random = lambda: 0.0  # always spread
    try:
        world.area_statuses.process_tick()
    finally:
        mod.random.random = old_random
    assert world.area_statuses.has_status(bid, "smoke"), "smoke did not spread to Room B"


def test_clear_and_has():
    world, pname = make_world()
    aid = area_id(world, "Room A")
    world.area_statuses.apply_status(aid, "flooded")
    assert world.area_statuses.has_status(aid, "flooded")
    assert world.area_statuses.clear_status(aid, "flooded")
    assert not world.area_statuses.has_status(aid, "flooded")


def test_area_has_status_condition():
    world, pname = make_world()
    aid = area_id(world, "Room A")
    world.area_statuses.apply_status(aid, "on_fire")
    result = world.triggers._evaluate_conditions(
        {"operator": "and", "conditions": [{"type": "area_has_status", "status_type": "on_fire"}]},
        {}, game_state=world)
    assert result is True, "area_has_status condition failed"


def test_drying_and_effects():
    world, pname = make_world()
    from graph import Node, Edge
    aid = area_id(world, "Room A")
    item = Node(id="item_coat", type="item", name="coat", properties={"wet": True})
    world.graph.add_node(item)
    world.graph.add_edge(Edge(source=item.id, target=aid, type="in"))
    world._process_item_drying()
    # dry air: chance 0.25 — force deterministic
    import random as _r
    _r.seed(1)
    dried = False
    for _ in range(50):
        item.properties["wet"] = True
        world._process_item_drying()
        if not item.properties.get("wet"):
            dried = True
            break
    assert dried, "wet item never dried"
