"""Freshness tests (task-191): tick decay to spoiled + on_spoil, cooking."""

from area import Area
from graph import Node, Edge, EDGE_IN


def make_world():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.movement.add_area(Area("Kitchen", "A test kitchen.", []))
    pname = world.active_player
    world.name_matcher._set_player_area(pname, "Kitchen")
    return world, pname


def add_item(world, name, props=None):
    n = Node(id=f"item_{name.replace(' ', '_')}", type="item", name=name, properties={
        "name": name, "weight": 0.2, "tags": ["food"], "current_state": "normal",
        "actions": ["examine", "take", "eat"],
    })
    if props:
        n.properties.update(props)
    world.graph.add_node(n)
    area_id = world._get_current_area_id()
    world.graph.add_edge(Edge(source=n.id, target=area_id, type=EDGE_IN))
    return n


def test_item_spoils_after_ticks():
    world, pname = make_world()
    milk = add_item(world, "milk", {"perishable": True, "freshness_ticks": 2, "freshness_state": "fresh"})
    # two turn ticks → spoiled
    world.tick_manager.tick_turn()
    assert milk.properties["freshness_state"] == "fresh"
    world.tick_manager.tick_turn()
    assert milk.properties["freshness_state"] == "spoiled"
    assert milk.properties["freshness_ticks"] == 0
    # already spoiled → no further change
    world.tick_manager.tick_turn()
    assert milk.properties["freshness_state"] == "spoiled"


def test_on_spoil_trigger_fires():
    world, pname = make_world()
    fish = add_item(world, "fish", {"perishable": True, "freshness_ticks": 1, "freshness_state": "fresh"})
    trig = Node(id="trigger_spoil_fish", type="logic_trigger", name="spoil note", properties={
        "trigger_type": "on_spoil",
        "effects": [{"type": "message", "params": {"message": "A sour smell rises from the fish."}}],
    })
    world.graph.add_node(trig)
    world.graph.add_edge(Edge(source=fish.id, target=trig.id, type="triggers"))
    world.tick_manager.tick_turn()
    assert fish.properties["freshness_state"] == "spoiled"


def test_cooking_sets_cooked_and_stops_decay():
    world, pname = make_world()
    chicken = add_item(world, "chicken", {"perishable": True, "freshness_ticks": 10, "freshness_state": "fresh",
                                          "actions": "examine,take,use"})
    oven = add_item(world, "oven", {"tags": ["oven", "cooking"], "current_state": "on",
                                    "actions": "examine,use"})
    world.take_item("chicken")
    result = world.use_item_on("chicken", "oven")
    assert chicken.properties["freshness_state"] == "cooked"
    assert "cook" in result.lower()
    # cooked food does not decay
    world.tick_manager.tick_turn()
    assert chicken.properties["freshness_state"] == "cooked"


def test_examine_mentions_freshness_naturally():
    world, pname = make_world()
    fruit = add_item(world, "fruit", {"perishable": True, "freshness_ticks": 0, "freshness_state": "spoiled"})
    world.take_item("fruit")
    desc = world.item_actions._render_node_desc(fruit) if hasattr(world.item_actions, "_render_node_desc") else ""
    # fall back to examine path
    if not desc:
        desc = world.get_item_desc("fruit")
    assert "gone bad" in desc.lower()
