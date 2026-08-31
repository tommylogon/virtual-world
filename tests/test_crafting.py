"""Crafting system tests (task-2): recipe nodes, learning, inputs, gates,
skill checks, discovery, outputs via give_item."""

import pytest

from area import Area
from graph import Node, Edge, EDGE_CARRYING, EDGE_IN


def make_world():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.movement.add_area(Area("Kitchen", "A test kitchen.", []))
    pname = world.active_player
    world.name_matcher._set_player_area(pname, "Kitchen")
    return world, pname


def add_world_item(world, name, props=None):
    n = Node(id=f"item_{name}", type="item", name=name, properties={
        "name": name, "weight": 0.1, "tags": [], "current_state": "normal",
        "actions": ["examine", "take", "use"],
    })
    if props:
        n.properties.update(props)
    world.graph.add_node(n)
    area_id = world._get_current_area_id()
    world.graph.add_edge(Edge(source=n.id, target=area_id, type=EDGE_IN))
    return n


def add_recipe(world, name, props):
    n = Node(id=f"recipe_{name.replace(' ', '_')}", type="recipe", name=name, properties=props)
    world.graph.add_node(n)
    return n


def test_unknown_recipe_errors():
    world, _ = make_world()
    with pytest.raises(ValueError, match="don't know any recipe"):
        world.craft_item("fried eggs")


def test_global_recipe_requires_inputs_and_conditions():
    world, pname = make_world()
    add_recipe(world, "Fried Eggs", {
        "inputs": [{"item": "egg", "count": 1, "consumed": True},
                   {"item": "pan", "count": 1, "consumed": False}],
        "conditions": [{"type": "state_equals", "target": "oven", "value": "on"}],
        "outputs": [{"item": "apple", "count": 1}],
        "learned_by": ["global"],
    })
    # no egg → fail
    add_world_item(world, "pan")
    oven = add_world_item(world, "oven")
    with pytest.raises(ValueError, match="You need 1 egg"):
        world.craft_item("fried eggs")


def test_recipe_condition_gate_blocks():
    world, pname = make_world()
    add_recipe(world, "Fried Eggs", {
        "inputs": [{"item": "egg", "count": 1, "consumed": True}],
        "conditions": [{"type": "state_equals", "target": "oven", "value": "on"}],
        "outputs": [{"item": "apple", "count": 1}],
        "learned_by": ["global"],
    })
    add_world_item(world, "egg")
    oven = add_world_item(world, "oven")
    with pytest.raises(ValueError, match="conditions"):
        world.craft_item("fried eggs")


def test_global_recipe_success_spawns_output_and_consumes_input():
    world, pname = make_world()
    add_recipe(world, "Fried Eggs", {
        "inputs": [{"item": "egg", "count": 1, "consumed": True},
                   {"item": "pan", "count": 1, "consumed": False}],
        "conditions": [{"type": "state_equals", "target": "oven", "value": "on"}],
        "outputs": [{"item": "apple", "count": 1}],
        "learned_by": ["global"],
    })
    egg = add_world_item(world, "egg")
    add_world_item(world, "pan")
    oven = add_world_item(world, "oven")
    oven.properties["current_state"] = "on"

    result = world.craft_item("fried eggs")
    assert "craft" in result.lower()
    # egg consumed (node removed)
    assert world.graph.get_node(egg.id) is None
    # output spawned into inventory (apple from library)
    player_id = world._player_node_id(pname)
    carried = [e.source for e in world.graph.get_edges_for_target(player_id, EDGE_CARRYING)]
    assert any((world.graph.get_node(i).name or '').lower() == "apple" for i in carried)


def test_skill_check_fumble_does_not_consume():
    world, pname = make_world()
    add_recipe(world, "Fried Eggs", {
        "inputs": [{"item": "egg", "count": 1, "consumed": True}],
        "conditions": [],
        "outputs": [{"item": "apple", "count": 1}],
        "learned_by": ["global"],
        "skill_check": {"skill": "Cooking", "dc": 9999},
    })
    egg = add_world_item(world, "egg")
    result = world.craft_item("fried eggs")
    assert "fumble" in result.lower()
    assert world.graph.get_node(egg.id) is not None


def test_discoverable_recipe_records_after_first_craft():
    world, pname = make_world()
    add_recipe(world, "Fried Eggs", {
        "inputs": [{"item": "egg", "count": 1, "consumed": True}],
        "conditions": [],
        "outputs": [{"item": "apple", "count": 1}],
        "learned_by": ["skill:Cooking"],
        "discoverable": True,
    })
    egg = add_world_item(world, "egg")
    player = world.player_manager.get_player(pname)
    # not learned by skill (Cooking not in defaults) → unknown
    with pytest.raises(ValueError, match="don't know how to craft"):
        world.craft_item("fried eggs")
    # teach the skill, then craft
    player.skills["Cooking"] = 1
    result = world.craft_item("fried eggs")
    assert "craft" in result.lower()
    assert "Fried Eggs" in (player.crafting_known or [])


def test_item_learned_recipe():
    world, pname = make_world()
    add_recipe(world, "Fried Eggs", {
        "inputs": [{"item": "egg", "count": 1, "consumed": True}],
        "conditions": [],
        "outputs": [{"item": "apple", "count": 1}],
        "learned_by": ["item:recipe_card_eggs"],
    })
    add_world_item(world, "egg")
    with pytest.raises(ValueError, match="don't know how to craft"):
        world.craft_item("fried eggs")
    card = add_world_item(world, "recipe_card_eggs")
    # take it into the inventory... take puts it in hand; carried_names check uses carrying+equipped
    world.take_item("recipe_card_eggs")
    result = world.craft_item("fried eggs")
    assert "craft" in result.lower()
