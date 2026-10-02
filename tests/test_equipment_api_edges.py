"""task-654: `player.equipped` and the equipment edges are one fact, not two.

The bug: ``POST /api/players/<name>`` with an ``equipped`` payload returned 200,
showed the item in the inspector, and did nothing in combat — because the route
assigned ``player.equipped`` and nothing else, while **both** readers of
equipment read the graph:

    combat._best_weapon_node             -> EDGE_CARRYING + EDGE_EQUIPPED
    equipment_bonuses.get_equipment_nodes -> EDGE_EQUIPPED

The in-world verb ``take`` writes both, which is how the same character ended up
with ``hand: [item_spear]`` (API write, inert) beside ``hand_right:
[item_rusty_hatchet]`` (``take``, live).

These tests pin the invariant from the direction that actually matters: the two
readers must agree with the inspector.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import Edge, EDGE_CARRYING, EDGE_EQUIPPED, EDGE_IN, Node
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


def _weapon(world, name="Rusty Hatchet", lib_id="item_rusty_hatchet",
            equip=True):
    """A real weapon item node lying in the character's area, carried by nobody."""
    props = {
        "tags": ["weapon"],
        "damage": "1d6+2",
        "library_id": lib_id,
    }
    if equip:
        # `take` only offers itself when the item is worth having (contextual
        # actions) and declares the action, so both are set here.
        props["equip_slots"] = ["hand_right"]
        props["actions"] = ["examine", "take", "drop"]
    node = Node(id=lib_id, type="item", name=name, properties=props)
    world.graph.add_node(node)
    area_id = world._get_current_area_id()
    world.graph.add_edge(Edge(source=node.id, target=area_id, type=EDGE_IN))
    return node


def _pid(world, name):
    return world._player_node_id(name)


# ── the unit: the single writer puts both halves in step ─────────────────

def test_equipped_payload_creates_the_edges(world):
    p = _add(world, "Hero")
    node = _weapon(world)
    world.set_equipped_payload(p, {"hand_right": [node.id]})

    edges = world.graph.get_edges_for_target(_pid(world, "Hero"), EDGE_EQUIPPED)
    assert [(e.source, e.properties.get("slot")) for e in edges] == [
        (node.id, "hand_right")], edges
    assert p.equipped["hand_right"] == [node.id]


def test_equipping_removes_the_carrying_edge(world):
    """Worn means worn: the same edge swap `equip_item` performs."""
    p = _add(world, "Hero")
    node = _weapon(world)
    world.graph.add_edge(Edge(source=node.id, target=_pid(world, "Hero"),
                              type=EDGE_CARRYING))

    world.set_equipped_payload(p, {"hand_right": [node.id]})
    assert world.graph.get_edges_for_target(_pid(world, "Hero"), EDGE_CARRYING) == []


def test_payload_empties_a_slot_and_returns_the_item_to_carrying(world):
    """Dropping an item from a payload must not orphan it out of the graph."""
    p = _add(world, "Hero")
    node = _weapon(world)
    world.set_equipped_payload(p, {"hand_right": [node.id]})
    assert world.graph.get_edges_for_target(_pid(world, "Hero"), EDGE_EQUIPPED)

    world.set_equipped_payload(p, {})
    assert world.graph.get_edges_for_target(_pid(world, "Hero"), EDGE_EQUIPPED) == []
    assert [e.source for e in
            world.graph.get_edges_for_target(_pid(world, "Hero"),
                                             EDGE_CARRYING)] == [node.id]
    assert not p.equipped.get("hand_right")


def test_slot_markers_survive_and_never_become_edges(world):
    """`equip_item` writes `__multi_slot_<id>` for a two-handed item."""
    p = _add(world, "Hero")
    node = _weapon(world)
    marker = f"__multi_slot_{node.id}"
    world.set_equipped_payload(p, {"hand_right": [node.id], "hand_left": [marker]})

    sources = {e.source for e in
               world.graph.get_edges_for_target(_pid(world, "Hero"), EDGE_EQUIPPED)}
    assert sources == {node.id}, sources
    assert p.equipped["hand_left"] == [marker], p.equipped


def test_unresolvable_entry_is_reported_not_silently_dropped(world):
    p = _add(world, "Hero")
    result = world.set_equipped_payload(
        p, {"hand_right": ["item_that_does_not_exist"]})
    assert result["unresolved"] == ["item_that_does_not_exist"]
    assert not world.graph.get_edges_for_target(_pid(world, "Hero"), EDGE_EQUIPPED)


# ── the wiring: the two readers agree with the inspector ─────────────────

def test_an_api_equipped_weapon_is_the_weapon_combat_picks(world):
    """The regression: the item shows in the inspector and attacks with it."""
    p = _add(world, "Hero")
    node = _weapon(world)
    world.set_equipped_payload(p, {"hand_right": [node.id]})

    from engine.combat import CombatSystem
    combat = CombatSystem(world.graph, world.skills, world.ghost_system,
                          world.npc_behaviors)
    picked = combat._best_weapon_node("Hero")
    assert picked is not None, "equipped weapon invisible to weapon selection"
    assert picked.id == node.id


def test_an_api_equipped_armour_is_the_armour_bonuses_read(world):
    """Defense/insulation/resistances read EDGE_EQUIPPED only."""
    p = _add(world, "Hero")
    plate = Node(id="item_iron_plate", type="item", name="Iron Plate", properties={
        "tags": ["armor", "clothing"],
        "defense": 4,
        "insulation": 3,
        "equip_slots": ["torso"],
    })
    world.graph.add_node(plate)
    world.set_equipped_payload(p, {"torso": [plate.id]})

    from engine.equipment_bonuses import aggregate_bonuses
    bonuses = aggregate_bonuses(p, world.graph)
    assert bonuses["defense"] == 4, bonuses
    assert bonuses["insulation"] == 3, bonuses


def test_an_api_write_and_a_take_leave_the_same_shape(world):
    """The two writers must be indistinguishable to every reader."""
    api_player = _add(world, "ApiWriter")
    take_player = _add(world, "TakeWriter")
    api_node = _weapon(world, "Api Hatchet", "item_api_hatchet")
    take_node = _weapon(world, "Take Hatchet", "item_take_hatchet")

    world.set_equipped_payload(api_player, {"hand_right": [api_node.id]})
    world.player_manager.set_active_player("TakeWriter")
    world.take_item("Take Hatchet")

    def shape(player_name, own_item_id):
        """Everything the two readers can see, with the item id normalised so
        the two characters' *different* hatchets compare equal."""
        from engine.equipment_bonuses import aggregate_bonuses
        player = world.players[player_name]
        equipped = sorted(
            "THE_ITEM" if e.source == own_item_id else e.source
            for e in world.graph.get_edges_for_target(_pid(world, player_name),
                                                     EDGE_EQUIPPED))
        carried = sorted(
            "THE_ITEM" if e.source == own_item_id else e.source
            for e in world.graph.get_edges_for_target(_pid(world, player_name),
                                                     EDGE_CARRYING))
        bonuses = aggregate_bonuses(player, world.graph)
        dict_shape = {slot: ["THE_ITEM" if i == own_item_id else i for i in stack]
                      for slot, stack in player.equipped.items()}
        return equipped, carried, bonuses["damage_dice"], bonuses["damage"], \
            dict_shape

    assert shape("ApiWriter", api_node.id) == shape("TakeWriter", take_node.id)


# ── the route: POST /api/players/<name> ──────────────────────────────────

def test_update_player_route_writes_the_edges():
    from app import create_app
    app = create_app({"TESTING": True})
    world = app.world
    client = app.test_client()

    _add(world, "Hero")
    node = _weapon(world)

    response = client.post("/api/players/Hero",
                           json={"equipped": {"hand_right": [node.id]}})
    assert response.status_code == 200, response.get_data(as_text=True)

    edges = world.graph.get_edges_for_target(_pid(world, "Hero"), EDGE_EQUIPPED)
    assert [e.source for e in edges] == [node.id], (
        "POST /api/players still leaves the equipment edges untouched")


def test_update_player_route_clears_the_edges_when_a_slot_is_emptied():
    from app import create_app
    app = create_app({"TESTING": True})
    world = app.world
    client = app.test_client()

    _add(world, "Hero")
    node = _weapon(world)
    client.post("/api/players/Hero", json={"equipped": {"hand_right": [node.id]}})
    assert world.graph.get_edges_for_target(_pid(world, "Hero"), EDGE_EQUIPPED)

    client.post("/api/players/Hero", json={"equipped": {"hand_right": []}})
    assert world.graph.get_edges_for_target(_pid(world, "Hero"), EDGE_EQUIPPED) == []


# ── the other direction: deleting a node must not leave the dict lying ───

def test_deleting_an_equipped_item_node_prunes_the_equipped_dict():
    """The inverse divergence: the id used to outlive the node it named."""
    from app import create_app
    app = create_app({"TESTING": True})
    world = app.world
    client = app.test_client()

    p = _add(world, "Hero")
    node = _weapon(world)
    client.post("/api/players/Hero", json={"equipped": {"hand_right": [node.id]}})
    assert p.equipped["hand_right"] == [node.id]

    response = client.delete(f"/api/graph/node/{node.id}")
    assert response.status_code == 200, response.get_data(as_text=True)

    assert node.id not in p.equipped["hand_right"], (
        "equipped still names a node that no longer exists")


def test_prune_leaves_markers_and_live_items_alone(world):
    p = _add(world, "Hero")
    node = _weapon(world)
    marker = f"__multi_slot_{node.id}"
    world.set_equipped_payload(p, {"hand_right": [node.id], "hand_left": [marker]})
    world.graph.remove_node(node.id)

    pruned = world.equipment.prune_dangling_equipped(p)
    assert node.id in pruned
    assert p.equipped["hand_right"] == []
    assert p.equipped["hand_left"] == [marker]
