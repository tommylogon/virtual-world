"""Armor wear-on-hit tests (task-161): uses decrement, natural-language
messages (never raw counts), break at 0 with on_break trigger."""

from area import Area
from graph import Node, Edge, EDGE_EQUIPPED, EDGE_CARRYING, EDGE_IN


def make_world():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.movement.add_area(Area("Room A", "First room.", []))
    pname = world.active_player
    world.name_matcher._set_player_area(pname, "Room A")
    return world, pname


def equip_armor(world, pname, name, uses=2, defense=3):
    n = Node(id=f"item_{name.replace(' ', '_')}", type="item", name=name, properties={
        "name": name, "weight": 2.0, "tags": ["armor"], "current_state": "normal",
        "actions": ["equip", "unequip"], "uses": uses, "max_uses": uses,
        "defense": defense,
    })
    world.graph.add_node(n)
    player_id = world._player_node_id(pname)
    world.graph.add_edge(Edge(source=n.id, target=player_id, type=EDGE_EQUIPPED, properties={"slot": "torso"}))
    player = world.player_manager.get_player(pname)
    player.equipped.setdefault("torso", []).append(n.id)
    return n


def test_single_hit_wears_naturally_message():
    world, pname = make_world()
    armor = equip_armor(world, pname, "leather vest", uses=4)
    player = world.player_manager.get_player(pname)
    msgs = world.equipment.decrement_armor_uses_on_hit(player)
    assert msgs
    assert armor.properties["uses"] == 3
    # natural language: no "3/4" or "uses:"-style numbers
    joined = " ".join(msgs)
    assert "takes the hit" in joined or "shows fresh wear" in joined
    assert "/4" not in joined


def test_wear_ratios_change_wording():
    world, pname = make_world()
    armor = equip_armor(world, pname, "plate", uses=10)
    player = world.player_manager.get_player(pname)
    msgs = []
    for _ in range(6):
        msgs.extend(world.equipment.decrement_armor_uses_on_hit(player))
    joined = " ".join(msgs)
    assert "battered" in joined


def test_break_removes_from_equipment_and_fires_on_break():
    world, pname = make_world()
    armor = equip_armor(world, pname, "cloth shirt", uses=2)
    # on_break trigger node
    trig = Node(id=f"trigger_break_{armor.id}", type="logic_trigger", name="break note", properties={
        "trigger_type": "on_break",
        "effects": [{"type": "message", "params": {"message": "The shirt unravels completely."}}],
    })
    world.graph.add_node(trig)
    world.graph.add_edge(Edge(source=armor.id, target=trig.id, type="triggers",
                              properties={"trigger_type": "on_break"}))

    player = world.player_manager.get_player(pname)
    # hit 1: wears
    msgs1 = world.equipment.decrement_armor_uses_on_hit(player)
    assert armor.properties["uses"] == 1
    # hit 2: breaks
    msgs2 = world.equipment.decrement_armor_uses_on_hit(player)
    joined = "\n".join(msgs1 + msgs2)
    assert "breaks" in joined.lower()
    assert "the shirt unravels completely" in joined.lower()
    player = world.player_manager.get_player(pname)
    assert not player.equipped.get("torso") or armor.id not in player.equipped["torso"]
    player_id = world._player_node_id(pname)
    assert armor.id not in [e.source for e in world.graph.get_edges_for_target(player_id, EDGE_EQUIPPED)]
    assert armor.id in [e.source for e in world.graph.get_edges_for_target(player_id, EDGE_CARRYING)]


def test_infinite_use_armor_unaffected():
    world, pname = make_world()
    armor = equip_armor(world, pname, "chainmail", uses=-1)
    player = world.player_manager.get_player(pname)
    msgs = world.equipment.decrement_armor_uses_on_hit(player)
    assert msgs == []
    assert armor.properties["uses"] == -1
