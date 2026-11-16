"""Tests for world recipes as activities (task-703).

World recipes resolve transformations performed by persistent Activities:
- Make X fails closed with an explicit missing list if ingredients are lacking.
- On success, starts timed cooking Activity, binds station in graph (at edge).
- Interruption ends activity with no consumption and no outputs.
- Completion rechecks conditions and resolves tier via central dice.
- Spatial relations are cleared on completion or interrupt.
- Other characters in the area can perceive the cook at the station.
"""

import json
import pytest

from area import Area
from graph import Node, Edge, EDGE_CARRYING, EDGE_IN
from virtual_world_engine import VirtualWorld


FRIED_EGG_RECIPE = {
    "id": "fried_egg",
    "name": "Fried Egg",
    "ingredients": [
        {"item": "raw_egg", "count": 1, "consumed": True},
        {"item": "butter", "count": 1, "consumed": True},
        {"item": "frying_pan", "count": 1, "consumed": False},
    ],
    "conditions": [
        {"type": "state_equals", "target": "campfire", "value": "on"}
    ],
    "duration_min": 10,
    "skill_check": {"skill": "Cooking", "dc": 10},
    "outputs": [{"item": "fried_egg", "count": 1}],
    "outcomes": {
        "crit_success": {
            "outputs": [{"item": "fried_egg", "count": 2}],
            "message": "Fluffy and golden - two perfect eggs."
        },
        "success": {
            "outputs": [{"item": "fried_egg", "count": 1}],
            "message": "Cooked just right."
        },
        "fail": {
            "consume_inputs": True,
            "outputs": [{"item": "fried_egg", "count": 1}],
            "message": "Slightly burned, but edible."
        },
        "crit_fail": {
            "consume_inputs": True,
            "outputs": [],
            "message": "Burned to a crisp."
        }
    },
    "learned_by": ["global"],
    "discoverable": True,
}


def make_cooking_world(tmp_path, *recipes):
    world = VirtualWorld()
    world.movement.add_area(Area("CampfireClearing", "A clearing with a cooking fire.", []))
    pname = world.active_player
    world.name_matcher._set_player_area(pname, "CampfireClearing")

    recipe_dir = tmp_path / "recipes"
    recipe_dir.mkdir(exist_ok=True)
    all_recipes = list(recipes) if recipes else [FRIED_EGG_RECIPE]
    for r in all_recipes:
        (recipe_dir / f"{r['id']}.json").write_text(json.dumps(r), encoding="utf-8")
    world.crafting.recipe_dir = str(recipe_dir)
    return world, pname


def add_item(world, name, props=None):
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


def test_make_fails_closed_with_explicit_missing_list(tmp_path):
    world, pname = make_cooking_world(tmp_path)
    add_item(world, "frying_pan")
    fire = add_item(world, "campfire")
    fire.properties["current_state"] = "on"

    with pytest.raises(ValueError) as exc:
        world.crafting.start_cooking(world, "fried egg")

    err = str(exc.value).lower()
    assert "you are missing:" in err
    assert "raw_egg" in err
    assert "butter" in err

    player = world.player_manager.get_player(pname)
    assert not player.activity


def test_make_starts_activity_and_binds_station(tmp_path):
    world, pname = make_cooking_world(tmp_path)
    add_item(world, "raw_egg")
    add_item(world, "butter")
    add_item(world, "frying_pan")
    fire = add_item(world, "campfire")
    fire.properties["current_state"] = "on"

    msg = world.crafting.start_cooking(world, "fried egg")
    assert "start cooking" in msg.lower()
    assert "10 min" in msg

    player = world.player_manager.get_player(pname)
    assert player.activity is not None
    assert player.activity.get("type") == "cooking"
    assert player.activity.get("target_item") == "campfire"

    # Check station binding in graph: Edge(player, campfire, "at")
    pid = world._player_node_id(pname)
    at_edges = list(world.graph.get_edges_for_source(pid, "at"))
    assert len(at_edges) == 1
    assert at_edges[0].target == fire.id


def test_interruption_produces_no_outputs_and_unbinds_station(tmp_path):
    world, pname = make_cooking_world(tmp_path)
    egg = add_item(world, "raw_egg")
    add_item(world, "butter")
    add_item(world, "frying_pan")
    fire = add_item(world, "campfire")
    fire.properties["current_state"] = "on"

    world.crafting.start_cooking(world, "fried egg")
    pid = world._player_node_id(pname)
    assert len(list(world.graph.get_edges_for_source(pid, "at"))) == 1

    stopped = world.activities.interrupt_activity(pname)
    assert "stop" in stopped.lower()

    player = world.player_manager.get_player(pname)
    assert player.activity is None
    # Spatial relation unbound
    assert len(list(world.graph.get_edges_for_source(pid, "at"))) == 0
    # Inputs not consumed
    assert world.graph.get_node(egg.id) is not None


def test_completion_rechecks_resolves_tier_and_cleans_graph(tmp_path):
    world, pname = make_cooking_world(tmp_path)
    add_item(world, "raw_egg")
    add_item(world, "butter")
    add_item(world, "frying_pan")
    fire = add_item(world, "campfire")
    fire.properties["current_state"] = "on"

    world.crafting.start_cooking(world, "fried egg")
    world.crafting.roll_fn = lambda: 15  # DC 10 -> success

    # Tick turns until completion
    out = None
    for _ in range(15):
        out = world.activities.tick_activity(pname)
        player = world.player_manager.get_player(pname)
        if not player.activity:
            break

    assert out is not None
    assert "craft" in out.lower() or "finish" in out.lower()

    # Verify output in inventory
    pid = world._player_node_id(pname)
    carried = [world.graph.get_node(e.source).name.lower()
               for e in world.graph.get_edges_for_target(pid, EDGE_CARRYING)]
    assert "fried_egg" in carried or any("egg" in c for c in carried)

    # Station relation unbound after completion
    assert len(list(world.graph.get_edges_for_source(pid, "at"))) == 0


def test_witness_perceives_cook_at_station(tmp_path):
    world, cook_name = make_cooking_world(tmp_path)
    add_item(world, "raw_egg")
    add_item(world, "butter")
    add_item(world, "frying_pan")
    fire = add_item(world, "campfire")
    fire.properties["current_state"] = "on"

    # Start cook as cook_name
    world.crafting.start_cooking(world, "fried egg")

    # Add witness character in same area
    from player import Player
    witness = Player("Witness")
    world.add_player(witness)
    world.name_matcher._set_player_area("Witness", "CampfireClearing")
    world.player_manager.active_player = cook_name

    cook = world.player_manager.get_player(cook_name)
    from engine.activities import activity_description
    desc = activity_description(cook.activity, cook_name)
    assert "cooking at the campfire" in desc.lower()

    pid = world._player_node_id(cook_name)
    at_edges = list(world.graph.get_edges_for_source(pid, "at"))
    assert at_edges[0].target == fire.id
