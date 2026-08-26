"""Tests for the human turn panel scene snapshot (task-333 Phase 1).

Covers:
- build_scene: people stranger-masking, hidden-item exclusion, item
  available_actions passthrough, per-player way state discovery
- Player.learn_way_aspect / knows_way_aspect round-trip
- movement/examine discovery wiring (locked go-fail and examine mark the
  aspect on the acting player)
"""
import pytest
from unittest.mock import MagicMock

from graph import WorldGraph, Node, Edge, EDGE_IN, EDGE_CARRYING, EDGE_CONNECTION
from player import Player
from engine.scene_snapshot import build_scene


def add_area(g, area_id, name, light=80):
    node = Node(id=area_id, type="area", name=name, properties={
        "environment": {"light": light},
    })
    g.add_node(node)
    return node


def connect_way(g, area_id, way_id, name, direction, to_area_id, props=None):
    """Area -> way -> target area via CONNECTION edges (engine layout)."""
    way = Node(id=way_id, type="way", name=name, properties=dict({
        "current_state": "closed",
        "direction": direction,
    }, **(props or {})))
    g.add_node(way)
    g.add_edge(Edge(source=area_id, target=way_id, type=EDGE_CONNECTION,
                    properties={"direction": direction}))
    g.add_edge(Edge(source=way_id, target=to_area_id, type=EDGE_CONNECTION))
    return way


@pytest.fixture
def world():
    """Minimal duck-typed VirtualWorld: graph + real Player + mock systems."""
    g = WorldGraph()
    add_area(g, "area_kitchen", "Kitchen", light=90)
    add_area(g, "area_hall", "Hall")

    # locked door north, plain arch east, see-through window
    connect_way(g, "area_kitchen", "way_mens", "Men's Room Door", "north",
                "area_hall", props={"current_state": "locked"})
    connect_way(g, "area_kitchen", "way_arch", "Dining Archway", "east",
                "area_hall", props={"current_state": "open"})
    connect_way(g, "area_kitchen", "way_window", "Serving Window", "northeast",
                "area_hall", props={
                    "current_state": "closed", "see_through": True,
                    "needs_open": {"enabled": True, "skill": "Athletics", "dc": 12},
                })

    # a met character, an unmet stranger, a visible item, a hidden item
    friend_node = Node(id="player_miki", type="character", name="miki",
                       properties={"description": "Anxious. Chews her thumbnail.",
                                   "tags": ["female"]})
    g.add_node(friend_node)
    g.add_edge(Edge(source="player_miki", target="area_kitchen", type=EDGE_IN))

    stranger_node = Node(id="player_clerk", type="character", name="rosa",
                         properties={"description": "Visor fringe, pen behind one ear.",
                                     "tags": ["female"]})
    g.add_node(stranger_node)
    g.add_edge(Edge(source="player_clerk", target="area_kitchen", type=EDGE_IN))

    cup = Node(id="item_cup", type="item", name="Baja Blast Cup", properties={
        "description": "Neon-teal and sweating.", "current_state": "normal",
        "actions": ["examine", "take", "drink"],
    })
    g.add_node(cup)
    g.add_edge(Edge(source="item_cup", target="area_kitchen", type=EDGE_IN))

    earring = Node(id="item_earring", type="item", name="Blue Butterfly Earring",
                   properties={"description": "Tiny blue wings.",
                               "current_state": "hidden"})
    g.add_node(earring)
    g.add_edge(Edge(source="item_earring", target="area_kitchen", type=EDGE_IN))

    jake = Player("jake halloway")
    jake.current_area = "Kitchen"
    # jake has met miki, not rosa
    jake.relationships["miki"] = {"closeness": 10, "interaction_count": 3}

    pm = MagicMock()
    pm.players = {"jake halloway": jake, "miki": MagicMock(), "rosa": MagicMock()}
    pm.current_area = MagicMock()
    pm.current_area.name = "Kitchen"
    pm._player_node_id = lambda name: f"player_{name.replace(' ', '_')}"
    pm.is_slasher = MagicMock(return_value=False)

    w = MagicMock()
    w.graph = g
    w.player_manager = pm
    # production resolves area ids on the WORLD facade (NodeIDHelper format)
    w.area_node_id = lambda name: f"area_{name.lower().replace(' ', '_')}"
    w.lighting.get_ambient_light = MagicMock(return_value=90)
    ad = MagicMock()
    ad._render_node = MagicMock(side_effect=lambda n: n.properties.get("description", ""))
    w.area_description = ad
    w._get_available_actions = MagicMock(return_value=[
        {"action": "examine", "label": "Examine the object", "enabled": True},
        {"action": "take", "label": "Pick up", "enabled": True},
    ])
    w.name_matcher.way_handle = MagicMock(
        side_effect=lambda way, d, area: d or way.name)
    return w


def test_people_are_stranger_masked(world):
    scene = build_scene(world, "jake halloway")
    by_name = {p["id"]: p for p in scene["people"]}
    assert by_name["player_miki"]["met"] is True
    assert by_name["player_miki"]["name"] == "miki"
    assert by_name["player_clerk"]["met"] is False
    assert by_name["player_clerk"]["name"] is None
    assert by_name["player_clerk"]["display_name"] != "rosa"


def test_hidden_items_stay_out_visible_items_have_actions(world):
    scene = build_scene(world, "jake halloway")
    names = [i["name"] for i in scene["items"]]
    assert "Baja Blast Cup" in names
    assert "Blue Butterfly Earring" not in names
    cup = next(i for i in scene["items"] if i["name"] == "Baja Blast Cup")
    actions = [a["action"] for a in cup["available_actions"]]
    assert "examine" in actions and "take" in actions


def test_locked_way_reads_closed_until_discovered(world):
    player = world.player_manager.players["jake halloway"]
    scene = build_scene(world, "jake halloway")
    mens = next(wy for wy in scene["ways"] if wy["direction"] == "north")
    assert mens["state"] == "closed"
    assert mens["known_locked"] is False

    player.learn_way_aspect("Kitchen", "north", "locked")
    scene = build_scene(world, "jake halloway")
    mens = next(wy for wy in scene["ways"] if wy["direction"] == "north")
    assert mens["state"] == "locked"
    assert mens["known_locked"] is True


def test_open_way_reports_open_without_knowledge(world):
    scene = build_scene(world, "jake halloway")
    arch = next(wy for wy in scene["ways"] if wy["direction"] == "east")
    assert arch["state"] == "open"
    assert arch["to"] == "Hall"


def test_you_strip_reports_vitals_conditions_carrying(world):
    player = world.player_manager.players["jake halloway"]
    player.vitals = {"HP": 100, "Energy": 59}
    player.conditions = {"poisoned": [{"duration": 5, "source": "vial"}]}
    carried = Node(id="item_phone", type="item", name="Miki's Phone",
                   properties={"name": "Miki's Phone"})
    world.graph.add_node(carried)
    world.graph.add_edge(Edge(source="item_phone", target="player_jake_halloway",
                              type=EDGE_CARRYING))
    scene = build_scene(world, "jake halloway")
    you = scene["you"]
    assert you["vitals"]["Energy"] == 59
    assert "poisoned" in you["conditions"]
    assert any(c["name"] == "Miki's Phone" for c in you["carrying"])


def test_darkness_flag_follows_light_level(world):
    world.lighting.get_ambient_light = MagicMock(return_value=15)
    scene = build_scene(world, "jake halloway")
    assert scene["area"]["dark"] is True
    assert scene["area"]["light_level"] == 15


def test_movement_learn_way_aspect_records_on_active_player():
    from engine.movement import MovementSystem
    player = Player("jake halloway")
    pm = MagicMock()
    pm.get_active_player_obj = MagicMock(return_value=player)
    pm.current_area = MagicMock()
    pm.current_area.name = "Kitchen"
    ms = MovementSystem.__new__(MovementSystem)
    ms.player_manager = pm
    way_node = Node(id="way_mens", type="way", name="Men's Room Door",
                    properties={})
    ms._learn_way_aspect(way_node, "north", "locked")
    assert player.knows_way_aspect("Kitchen", "north", "locked") is True
    assert player.knows_way_aspect("Kitchen", "north", "blocked") is False


def test_examine_way_marks_discovery(monkeypatch):
    """Examining a locked way records 'locked' via learn_way_aspect."""
    from engine.items.examine_actions import ExamineActionsMixin
    g = WorldGraph()
    add_area(g, "area_kitchen", "Kitchen")
    connect_way(g, "area_kitchen", "way_mens", "Men's Room Door", "north",
                "area_hall_placeholder", props={"current_state": "locked"})
    # target area node must exist for the CONNECTION walk
    hall = Node(id="area_hall_placeholder", type="area", name="Hall",
                properties={})
    g.add_node(hall)

    player = Player("jake halloway")
    player.current_area = "Kitchen"
    pm = MagicMock()
    pm.players = {"jake halloway": player}
    pm.active_player = "jake halloway"
    pm.get_active_player_obj = MagicMock(return_value=player)
    pm._player_node_id = lambda name: f"player_{name.replace(' ', '_')}"
    pm.current_area = MagicMock()
    pm.current_area.name = "Kitchen"

    mixin = ExamineActionsMixin.__new__(ExamineActionsMixin)
    mixin.graph = g
    mixin.matching = MagicMock()
    edge = next(e for e in g.get_edges_for_source("area_kitchen", EDGE_CONNECTION)
                if e.target == "way_mens")
    mixin.matching.resolve_exit = MagicMock(
        return_value=(edge, g.get_node("way_mens"), "north"))
    mixin.matching.way_handle = MagicMock(return_value="north")
    mixin.matching._match_item_name = MagicMock(return_value=None)
    mixin.matching._match_character_name = MagicMock(return_value=(None, []))
    mixin.trigger_system = MagicMock()
    mixin.trigger_system._execute_triggers = MagicMock(return_value=[])
    mixin._exec_triggers = MagicMock(return_value=[])

    pm.lighting = MagicMock()
    pm.lighting.can_see_in_dark = MagicMock(return_value=True)
    pm.lighting.get_ambient_light = MagicMock(return_value=80)
    pm._get_current_area_id = lambda: "area_kitchen"

    desc = ExamineActionsMixin.get_item_desc(mixin, pm, "north door")
    assert "locked" in desc.lower()
    assert player.knows_way_aspect("Kitchen", "north", "locked") is True


def test_hidden_ways_stay_out_of_scene(world):
    """bug: scene_snapshot leaked hidden (undiscovered) ways to the human
    turn panel — look filters them, the panel must too."""
    connect_way(world.graph, "area_kitchen", "way_sewer", "Sewer Passage",
                "down", "area_hall", props={"current_state": "hidden"})

    scene = build_scene(world, "jake halloway")

    directions = [w["direction"] for w in scene["ways"]]
    assert "down" not in directions
    assert "Sewer Passage" not in [w["name"] for w in scene["ways"]]


def test_discovered_hidden_way_shows_in_scene(world):
    connect_way(world.graph, "area_kitchen", "way_sewer", "Sewer Passage",
                "down", "area_hall", props={"current_state": "hidden"})
    jake = world.player_manager.players["jake halloway"]
    jake.discovered_exits.add(("Kitchen", "down"))

    scene = build_scene(world, "jake halloway")

    assert "down" in [w["direction"] for w in scene["ways"]]


def test_slasher_sees_hidden_ways_in_scene(world):
    connect_way(world.graph, "area_kitchen", "way_sewer", "Sewer Passage",
                "down", "area_hall", props={"current_state": "hidden"})
    world.player_manager.is_slasher = MagicMock(return_value=True)

    scene = build_scene(world, "jake halloway")

    assert "down" in [w["direction"] for w in scene["ways"]]


def test_requires_none_is_not_a_gate(world):
    """Legacy data stores requires:'none' for walk-through ways; movement.py
    special-cases it, so the panel payload must normalize it to '' — a
    truthy 'requires none' disabled Go and hid Open in the way menu."""
    connect_way(world.graph, "area_kitchen", "way_mens2", "Men's Restroom Door",
                "west", "area_hall", props={"requires": "none"})

    scene = build_scene(world, "jake halloway")

    west = next(w for w in scene["ways"] if w["direction"] == "west")
    assert west["requires"] == ""


def test_noncanonical_area_id_resolves_by_name(world):
    """bug-26: hand-authored ids strip punctuation — "Taco Bell Men's
    Restroom" lives at area_tacobell_mens_room, so the canonical id
    construction missed it and the panel rendered nobody/nothing/no ways
    out. The name-based fallback must win."""
    g = world.graph
    g.add_node(Node(id="area_tacobell_mens_room", type="area",
                    name="Taco Bell Men's Restroom",
                    properties={"environment": {"light": 90},
                                "description": "one toilet, one sink, one mirror."}))
    toilet = Node(id="item_toilet_x", type="item", name="Toilet",
                  properties={"description": "porcelain",
                              "current_state": "normal"})
    g.add_node(toilet)
    g.add_edge(Edge(source="item_toilet_x", target="area_tacobell_mens_room",
                    type=EDGE_IN))
    connect_way(g, "area_tacobell_mens_room", "way_out_x", "Door", "out",
                "area_hall")
    jake = world.player_manager.players["jake halloway"]
    jake.current_area = "Taco Bell Men's Restroom"

    scene = build_scene(world, "jake halloway")

    assert scene["area"]["id"] == "area_tacobell_mens_room"
    assert scene["area"]["desc"]  # area node found → description renders
    assert [i["name"] for i in scene["items"]] == ["Toilet"]
    assert len(scene["ways"]) == 1


def test_you_strip_carries_character_name(world):
    """task-342: the composer's you-strip opens the shared vital detail
    modal, which needs the character name in the payload."""
    scene = build_scene(world, "jake halloway")

    assert scene["you"]["name"] == "jake halloway"
    assert "HP" in scene["you"]["vitals"]
