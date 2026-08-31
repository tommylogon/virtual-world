"""Batch tests: scry (320), teach (197), sing (247), use-on quantity (196),
encumbrance size bump (202)."""

import pytest

from area import Area
from graph import Node, Edge, EDGE_CARRYING, EDGE_IN


def make_world():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.movement.add_area(Area("Kitchen", "A test kitchen.", []))
    world.movement.add_area(Area("Cellar", "A dark cellar.", []))
    pname = world.active_player
    world.name_matcher._set_player_area(pname, "Kitchen")
    return world, pname


def area_id(world, name):
    for n in world.graph.nodes.values():
        if n.type == "area" and n.name == name:
            return n.id
    return None


# ── 320 scry ────────────────────────────────────────────────────────────────

def test_scry_view_renders_distant_area():
    from engine.scry import scry_view
    world, pname = make_world()
    cell = world.graph.get_node(area_id(world, "Cellar"))
    cell.properties["description"] = "Dust-covered crates line the walls."
    view = scry_view(world, "Cellar")
    assert "Cellar" in view
    assert "Dust-covered crates" in view


def test_scry_effect_handler_output():
    world, pname = make_world()
    out = world.effects.execute(
        "scry",
        {"target": "Kitchen", "message": "Your eye blinks open elsewhere."},
        {},
        game_state=world,
    )
    assert out and "Your eye blinks open elsewhere." in out[0]
    # unknown target → fail message
    out2 = world.effects.execute("scry", {"target": "Nowhere", "fail_message": "Nothing there."}, {}, game_state=world)
    assert "Nothing there." in out2[0]


# ── 197 teach ──────────────────────────────────────────────────────────────

def test_teach_recipe_transfers_knowledge():
    from player import Player
    world, pname = make_world()
    recipe = Node(id="recipe_fried_eggs", type="recipe", name="Fried Eggs", properties={
        "inputs": [{"item": "egg", "count": 1, "consumed": True}],
        "conditions": [],
        "outputs": [{"item": "apple", "count": 1}],
        "learned_by": ["global"],
    })
    world.graph.add_node(recipe)
    student = Player()
    student.name = "Student"
    student.current_area = "Kitchen"
    world.player_manager.players["Student"] = student

    # teacher knows it (global recipe) → teach
    msg = world.teach_item("Fried Eggs", "Student")
    assert "know how to make" in msg
    assert "Fried Eggs" in (student.crafting_known or [])


def test_teach_unknown_subject_fails():
    from player import Player
    world, pname = make_world()
    student = Player()
    student.name = "Student"
    student.current_area = "Kitchen"
    world.player_manager.players["Student"] = student
    with pytest.raises(ValueError, match="recipe called"):
        world.teach_item("Warp Drives", "Student")


# ── 247 sing ───────────────────────────────────────────────────────────────

def test_sing_is_a_speech_level():
    from engine.sound import _speech_levels
    levels = _speech_levels()
    assert "sing" in levels
    assert levels["sing"] >= 1


# ── 196 use N on target ────────────────────────────────────────────────────

def test_use_on_amount_consumes_extra_uses():
    world, pname = make_world()
    log = Node(id="item_kindling", type="item", name="kindling", properties={
        "name": "kindling", "weight": 0.5, "tags": [], "current_state": "normal",
        "actions": "examine,take,use", "uses": 5, "max_uses": 5,
    })
    fireplace = Node(id="item_fireplace", type="item", name="fireplace", properties={
        "name": "fireplace", "weight": 20, "tags": [], "actions": "examine,use",
    })
    world.graph.add_node(log)
    world.graph.add_node(fireplace)
    aid = area_id(world, "Kitchen")
    world.graph.add_edge(Edge(source=log.id, target=aid, type=EDGE_IN))
    world.graph.add_edge(Edge(source=fireplace.id, target=aid, type=EDGE_IN))
    world.use_item_on("kindling", "fireplace", amount=2)
    assert log.properties["uses"] == 3


def test_use_on_amount_validates_against_available():
    world, pname = make_world()
    log = Node(id="item_kindling", type="item", name="kindling", properties={
        "name": "kindling", "weight": 0.5, "actions": "use", "uses": 1,
    })
    fireplace = Node(id="item_fireplace2", type="item", name="fireplace2", properties={
        "name": "fireplace2", "actions": "use",
    })
    world.graph.add_node(log)
    world.graph.add_node(fireplace)
    aid = area_id(world, "Kitchen")
    world.graph.add_edge(Edge(source=log.id, target=aid, type=EDGE_IN))
    world.graph.add_edge(Edge(source=fireplace.id, target=aid, type=EDGE_IN))
    with pytest.raises(ValueError, match="only have 1 use"):
        world.use_item_on("kindling", "fireplace2", amount=3)


# ── 202 encumbrance size bump ──────────────────────────────────────────────

def test_overencumbrance_blocks_small_ways():
    world, pname = make_world()
    way = Node(id="way_tinygap", type="way", name="tiny gap", properties={
        "current_state": "open", "max_size": "small",
    })
    world.graph.add_node(way)
    world.graph.add_edge(Edge(source=area_id(world, "Kitchen"), target=way.id, type="connection",
                              properties={"direction": "down"}))
    world.graph.add_edge(Edge(source=way.id, target=area_id(world, "Cellar"), type="connection",
                              properties={"direction": "down"}))
    world.graph.add_edge(Edge(source=area_id(world, "Cellar"), target=way.id, type="connection",
                              properties={"direction": "up"}))
    world.graph.add_edge(Edge(source=way.id, target=area_id(world, "Kitchen"), type="connection",
                              properties={"direction": "up"}))

    # normal size, light load → passes (tight fit auto-crawls)
    result = world.move_to_area("down")
    assert isinstance(result, str)

    # heavy load (>50%) → effective size bumps by one → doesn't fit
    boulder = Node(id="item_boulder2", type="item", name="boulder2", properties={
        "name": "boulder2", "weight": 60.0, "actions": "take",
    })
    world.graph.add_node(boulder)
    pid = world._player_node_id(pname)
    world.graph.add_edge(Edge(source=boulder.id, target=pid, type=EDGE_CARRYING))
    # reset player to Kitchen (the move above succeeded)
    world.name_matcher._set_player_area(pname, "Kitchen")
    with pytest.raises(ValueError, match="don't fit"):
        world.move_to_area("down")
