"""Background preparation: carry supplies so a need is not a round trip (task-426).

The world models natural water as an area tag you drink from standing in it and
food as items. Before this, a character could never fill a skin or pocket a
ration, so every need was a fresh journey. These tests pin the primitive that a
trip into the wild depends on.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.background_simulation import CARRIED_WATER_FILL
from graph import Edge, Node, EDGE_CARRYING, EDGE_IN
from player import Player

AREA = "Blizzard Forest Clearing"


def _world():
    from app import create_app
    return create_app({"TESTING": True}).world


def _bg_player(world, name="BgGoblin", area=AREA, **vitals):
    p = Player(name)
    world.add_player(p)
    p.current_area = area
    world.set_player_area(name, area)
    p.simulation_mode = "background"
    p.next_due_tick = 0
    for stat, value in {
        "Hunger": 10, "Thirst": 10, "Energy": 90, "Bladder": 0,
        "Hygiene": 100, "Sanity": 100, "Entertainment": 100, "Social": 100,
    }.items():
        p.vitals[stat] = value
    for stat, value in vitals.items():
        p.vitals[stat] = value
    return p


def _add_item(world, area, name, tags, actions, uses=-1, item_id=None):
    area_id = world.area_node_id(area)
    node = Node(
        id=item_id or f"item_{name.lower().replace(' ', '_')}", type="item", name=name,
        properties={"name": name, "tags": list(tags), "actions": list(actions),
                    "weight": 1.0, "uses": uses})
    world.graph.add_node(node)
    world.graph.add_edge(Edge(source=node.id, target=area_id, type=EDGE_IN))
    return node


def _carried_ids(world, player_name):
    pid = world._player_node_id(player_name)
    return {e.source for e in world.graph.get_edges_for_target(pid, EDGE_CARRYING)}


def test_takes_food_to_carry_when_at_a_food_area():
    w = _world()
    _bg_player(w, "Gob", Hunger=10)
    food = _add_item(w, AREA, "dried meat", ["food"], ["eat"])
    w.tick_turn()
    assert food.id in _carried_ids(w, "Gob"), "did not pocket a ration"
    assert any(e.get("why") == "prepare:stock" for e in w.players["Gob"].lived_log)


def test_fills_a_waterskin_at_a_water_area():
    w = _world()
    area_node = w.graph.get_node(w.area_node_id(AREA))
    area_node.properties.setdefault("tags", []).append("water")
    p = _bg_player(w, "Gob")
    skin = _add_item(w, AREA, "empty skin", ["water", "container", "drink"],
                     ["drink"], uses=0)
    w.graph.add_edge(Edge(source=skin.id, target=w._player_node_id("Gob"),
                          type=EDGE_CARRYING))
    w.tick_turn()
    assert skin.properties["uses"] == CARRIED_WATER_FILL, "waterskin not refilled"


def test_eats_carried_food_away_from_a_food_area():
    w = _world()
    p = _bg_player(w, "Gob", Hunger=80, Thirst=10)
    ration = _add_item(w, AREA, "ration", ["food"], ["eat"], uses=1)
    # not in the area: it is in the character's hands
    w.graph.remove_edge(ration.id, w.area_node_id(AREA), EDGE_IN)
    w.graph.add_edge(Edge(source=ration.id, target=w._player_node_id("Gob"),
                          type=EDGE_CARRYING))
    w.tick_turn()
    assert p.vitals["Hunger"] < 80, "did not eat from the pack"
    assert ration.id not in _carried_ids(w, "Gob"), "ration not consumed"
