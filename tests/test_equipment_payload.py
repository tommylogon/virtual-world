"""The equipped map has to reach the client, and a worn item has to read as carried.

One report, two bugs:

1. ``GET /api/state`` stopped publishing ``player.equipped``. The lite-mode
   refactor (ddf032ff) rebuilt ``_serialize_player`` and dropped the key along
   with ``skills``. Every front-end reader of the map - the paperdoll, the
   inventory list, the equip picker, the equipment narrative - then saw an
   empty map: all 13 slots rendered "-" and the 14 worn items were counted as
   "19 carried".

2. ``EquipmentSystem.equip_item`` asked only the ``carrying`` edges "do you
   have this?". A worn item is not carried, so equipping what the character
   was already wearing answered "You aren't carrying 'X'." and the "You're
   already wearing the X." check below it never ran.

The worn record itself is fine: the graph holds the ``equipped`` edges and
``_sync_equipped_from_graph`` rebuilds the map from them. The map simply
stopped being published.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import EDGE_CARRYING, EDGE_EQUIPPED, EDGE_IN, Edge, Node
from player import Player

AREA = "Blizzard Forest Clearing"


@pytest.fixture()
def world():
    from app import create_app
    return create_app({"TESTING": True}).world


def _add(world, name):
    p = Player(name)
    world.add_player(p)
    p.current_area = AREA
    world.set_player_area(p.name, AREA)
    return p


def _item(world, name, lib_id, slot="hand_right", tags=None):
    node = Node(id=lib_id, type="item", name=name, properties={
        "equip_slots": [slot],
        "tags": tags or ["clothing"],
        "actions": ["examine", "take", "drop"],
    })
    world.graph.add_node(node)
    return node


def _pid(world, name):
    return world._player_node_id(name)


# ── the payload publishes the map ─────────────────────────────────────────

def test_state_payload_publishes_the_equipped_map(world):
    """The paperdoll, the inventory list and the equip picker all read
    `player.equipped`; without the key they render an empty body."""
    p = _add(world, "Hero")
    node = _item(world, "Hatchet", "item_hatchet")
    world.set_equipped_payload(p, {"hand_right": [node.id]})

    payload = world.to_dict()
    equipped = payload["players"]["Hero"].get("equipped")
    assert equipped is not None, "/api/state publishes no equipped map"
    assert equipped["hand_right"] == [node.id], equipped


def test_published_map_is_the_projection_of_the_equipped_edges(world):
    """The edges are the store (task-654); the published map is their read
    projection, so the two must not drift."""
    p = _add(world, "Hero")
    node = _item(world, "Hatchet", "item_hatchet")
    world.set_equipped_payload(p, {"hand_right": [node.id]})

    edges = world.graph.get_edges_for_target(_pid(world, "Hero"), EDGE_EQUIPPED)
    published = world.to_dict()["players"]["Hero"]["equipped"]

    by_slot = {}
    for edge in edges:
        by_slot.setdefault(edge.properties.get("slot"), []).append(edge.source)
    for slot, sources in by_slot.items():
        assert published.get(slot) == sources, (slot, published.get(slot), sources)


def test_state_payload_publishes_skills(world):
    """The same commit dropped `skills`; the inspector's skill editor and the
    world export both read it."""
    p = _add(world, "Hero")
    p.skills = {"perception": 3}
    payload = world.to_dict()
    assert payload["players"]["Hero"].get("skills") == {"perception": 3}, payload["players"]["Hero"]


def test_published_map_is_not_a_second_record_in_a_saved_file(world):
    """A saved world is graph-only: the equipped edges carry the slot, so the
    players block must not carry a second copy of the same fact."""
    p = _add(world, "Hero")
    node = _item(world, "Hatchet", "item_hatchet")
    world.set_equipped_payload(p, {"hand_right": [node.id]})

    saved = world.to_scenario_dict()
    assert "equipped" not in saved["players"]["Hero"], saved["players"]["Hero"]
    equipped_edges = [e for e in saved["graph"]["edges"]
                      if e.get("type") == EDGE_EQUIPPED
                      and e.get("target") == _pid(world, "Hero")]
    assert [e["source"] for e in equipped_edges] == [node.id], equipped_edges


# ── a worn item is carried ───────────────────────────────────────────────

def test_equipping_a_worn_item_says_already_wearing(world):
    """The regression: "You aren't carrying 'X'." for something the character
    is wearing."""
    p = _add(world, "Hero")
    node = _item(world, "Hatchet", "item_hatchet")
    world.set_equipped_payload(p, {"hand_right": [node.id]})
    world.player_manager.set_active_player("Hero")

    with pytest.raises(ValueError) as excinfo:
        world.equipment.equip_item("Hatchet")
    message = str(excinfo.value)
    assert "already wearing" in message, message
    assert "aren't carrying" not in message, message


def test_a_carried_item_still_equips(world):
    """The control: a packed item equips, and says so."""
    p = _add(world, "Hero")
    node = _item(world, "Hatchet", "item_hatchet")
    world.graph.add_edge(Edge(source=node.id, target=_pid(world, "Hero"),
                              type=EDGE_CARRYING))
    world.player_manager.set_active_player("Hero")

    message = world.equipment.equip_item("Hatchet")
    assert "equip" in message.lower(), message
    edges = world.graph.get_edges_for_target(_pid(world, "Hero"), EDGE_EQUIPPED)
    assert [e.source for e in edges] == [node.id], edges


# ── the loader writes the edge type the readers look for ─────────────────

def _legacy_payload():
    """A file whose players block carries `equipped` and whose graph has no
    equipped edges: the shape an older savegame had."""
    return {
        "graph": {
            "nodes": {
                "item_hatchet": {
                    "id": "item_hatchet",
                    "type": "item",
                    "name": "Hatchet",
                    "properties": {"equip_slots": ["hand_right"]},
                },
            },
            "edges": [],
        },
        "players": {
            "Hero": {"name": "Hero", "equipped": {"hand_right": ["item_hatchet"]}},
        },
    }


def test_loading_an_equipped_block_makes_equipped_edges_not_ways(world):
    """The loader wrote a `connection` edge (a way between two areas) for worn
    gear, so the equipment readers never saw it and the graph grew a
    item->character way for every worn item."""
    world.load_from_dict(_legacy_payload())

    equipped = world.graph.get_edges_for_target(_pid(world, "Hero"), EDGE_EQUIPPED)
    assert [e.source for e in equipped] == ["item_hatchet"], equipped
    assert equipped[0].properties.get("slot") == "hand_right", equipped[0].properties

    ways = [e for e in world.graph.edges
            if e.source == "item_hatchet" and e.target == _pid(world, "Hero")
            and e.type not in (EDGE_EQUIPPED, EDGE_CARRYING)]
    assert ways == [], ways


def test_loading_an_equipped_block_leaves_the_map_in_step(world):
    world.load_from_dict(_legacy_payload())
    published = world.to_dict()["players"]["Hero"]["equipped"]
    assert published["hand_right"] == ["item_hatchet"], published


def test_a_worn_item_is_not_also_carried_after_a_load(world):
    """task-450: an item holds at most one of carrying/equipped."""
    payload = _legacy_payload()
    payload["graph"]["edges"] = [
        {"source": "item_hatchet", "target": "player_Hero", "type": EDGE_CARRYING,
         "properties": {}},
    ]
    world.load_from_dict(payload)

    pid = _pid(world, "Hero")
    carrying = [e.source for e in world.graph.get_edges_for_target(pid, EDGE_CARRYING)]
    assert "item_hatchet" not in carrying, carrying


def test_a_scenario_with_equipped_edges_loads_them_into_the_map(world):
    """The mansion case: the graph holds the equipped edges, so the map must
    come back populated."""
    payload = _legacy_payload()
    payload["players"]["Hero"].pop("equipped")
    payload["graph"]["edges"] = [
        {"source": "item_hatchet", "target": "player_Hero", "type": EDGE_EQUIPPED,
         "properties": {"slot": "hand_right"}},
    ]
    world.load_from_dict(payload)

    published = world.to_dict()["players"]["Hero"]["equipped"]
    assert published["hand_right"] == ["item_hatchet"], published
