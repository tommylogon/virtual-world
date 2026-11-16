"""Unit tests for swimming, diving, and the bounded Air vital - task-594."""

import pytest

from area import Area
from graph import EDGE_CONNECTION, Edge, Node
from player import Player
from virtual_world_engine import VirtualWorld
from engine.traversal import WAY_VERBS, way_kind
from tools.way_properties import PROPERTIES


def _setup_water_world():
    w = VirtualWorld()

    # Shoreline (land)
    shore = Area("Shoreline", "A sandy riverbank next to calm water.", [])
    # Shallow water (swimmable)
    shallow = Area("Shallow River", "Waist-deep water moving slowly.", [])
    # Deep water (requires diving, submerged)
    deep = Area("Deep River Channel", "Dark, swirling deep water with strong undercurrents.", [])

    w.movement.add_area(shore)
    w.movement.add_area(shallow)
    w.movement.add_area(deep)

    shore_node = next(n for n in w.graph.nodes.values() if n.type == "area" and n.name == "Shoreline")
    shallow_node = next(n for n in w.graph.nodes.values() if n.type == "area" and n.name == "Shallow River")
    deep_node = next(n for n in w.graph.nodes.values() if n.type == "area" and n.name == "Deep River Channel")

    # Mark shallow water
    shallow_node.properties["surface"] = "shallow_water"
    shallow_node.properties["depth"] = "shallow"

    # Mark deep water
    deep_node.properties["surface"] = "deep_water"
    deep_node.properties["depth"] = "deep"
    deep_node.properties["tags"] = ["deep_water", "underwater"]

    # Way 1: shore -> shallow (requires: swim)
    w1 = Node(
        id="way_shore_shallow",
        type="way",
        name="river crossing",
        properties={
            "requires": "swim",
            "swim_dc": 10,
            "current_state": "open",
        },
    )
    w.graph.add_node(w1)
    w.graph.add_edge(Edge(source=shore_node.id, target=w1.id, type=EDGE_CONNECTION, properties={"direction": "north"}))
    w.graph.add_edge(Edge(source=w1.id, target=shallow_node.id, type=EDGE_CONNECTION, properties={"direction": "north"}))
    w.graph.add_edge(Edge(source=shallow_node.id, target=w1.id, type=EDGE_CONNECTION, properties={"direction": "south"}))
    w.graph.add_edge(Edge(source=w1.id, target=shore_node.id, type=EDGE_CONNECTION, properties={"direction": "south"}))

    # Way 2: shallow -> deep (requires: dive)
    w2 = Node(
        id="way_shallow_deep",
        type="way",
        name="submerged trench",
        properties={
            "requires": "dive",
            "dive_dc": 12,
            "current_state": "open",
        },
    )
    w.graph.add_node(w2)
    w.graph.add_edge(Edge(source=shallow_node.id, target=w2.id, type=EDGE_CONNECTION, properties={"direction": "north"}))
    w.graph.add_edge(Edge(source=w2.id, target=deep_node.id, type=EDGE_CONNECTION, properties={"direction": "north"}))
    w.graph.add_edge(Edge(source=deep_node.id, target=w2.id, type=EDGE_CONNECTION, properties={"direction": "south"}))
    w.graph.add_edge(Edge(source=w2.id, target=shallow_node.id, type=EDGE_CONNECTION, properties={"direction": "south"}))

    # Player
    swimmer = Player("Swimmer")
    swimmer.current_area = "Shoreline"
    swimmer.skills["Athletics"] = 25
    swimmer.vitals["Air"] = 100
    w.player_manager.players["Swimmer"] = swimmer
    w.player_manager.active_player = "Swimmer"
    w.name_matcher._set_player_area("Swimmer", "Shoreline")

    return w


def test_way_verbs_and_properties_include_swim_and_dive():
    assert "swim" in WAY_VERBS
    assert "dive" in WAY_VERBS

    req_prop = next(p for p in PROPERTIES if p.name == "requires")
    assert "swim" in req_prop.values
    assert "dive" in req_prop.values


def test_swimming_is_required_for_swim_ways():
    w = _setup_water_world()
    p = w.player_manager.players["Swimmer"]

    # Plain walk ("go") is refused because way requires swim
    try:
        w.movement.move_to_area("north", kind="go")
    except ValueError as exc:
        assert "need to swim" in str(exc).lower()
    else:
        raise AssertionError("Expected plain go to be refused on a swim-required way")

    # Successful swim moves player to shallow river
    res = w.movement.swim_to_area("north")
    assert p.current_area == "Shallow River"
    assert not p.is_submerged(w.graph)
    assert p.vitals.get("Air") == 100


def test_deep_water_requires_dive():
    w = _setup_water_world()
    p = w.player_manager.players["Swimmer"]

    # Swim to shallow first
    w.movement.swim_to_area("north")
    assert p.current_area == "Shallow River"

    # Trying to plain walk into deep water is refused
    try:
        w.movement.move_to_area("north", kind="go")
    except ValueError as exc:
        assert "need to dive" in str(exc).lower()
    else:
        raise AssertionError("Expected plain walk into deep water to be refused")

    # Trying to surface swim across deep water is refused
    try:
        w.movement.swim_to_area("north")
    except ValueError as exc:
        assert "need to dive" in str(exc).lower()
    else:
        raise AssertionError("Expected surface swim across deep water to be refused")

    # Successful dive moves player into deep river channel
    w.movement.dive_to_area("north")
    assert p.current_area == "Deep River Channel"
    assert p.is_submerged(w.graph)


def test_air_vital_depletes_underwater_and_triggers_suffocation():
    w = _setup_water_world()
    p = w.player_manager.players["Swimmer"]

    # Swim and dive into deep water
    w.movement.swim_to_area("north")
    w.movement.dive_to_area("north")
    assert p.is_submerged(w.graph)
    assert p.vitals["Air"] == 100

    # Advance ticks while submerged: air depletes
    w.tick_turn()
    assert p.vitals["Air"] == 80
    assert not p.has_condition("suffocating")

    w.tick_turn()
    assert p.vitals["Air"] == 60

    # Run air all the way down
    w.tick_turn()  # 40
    w.tick_turn()  # 20
    w.tick_turn()  # 0 -> suffocating applied
    assert p.vitals["Air"] == 0
    assert p.has_condition("suffocating")

    # Next tick: suffocating continues and drains HP
    hp_before = p.vitals["HP"]
    w.tick_turn()
    assert p.has_condition("suffocating")
    assert p.vitals["Air"] == 0


def test_surfacing_refills_air_and_cures_suffocation():
    w = _setup_water_world()
    p = w.player_manager.players["Swimmer"]

    # Put player in deep water with 0 air and suffocating
    p.current_area = "Deep River Channel"
    p.vitals["Air"] = 0
    p.add_condition("suffocating")
    assert p.is_submerged(w.graph)
    assert p.has_condition("suffocating")

    # Move back to surface (Shoreline)
    p.current_area = "Shoreline"
    assert not p.is_submerged(w.graph)

    # Tick at surface: air refills and suffocating is removed!
    w.tick_turn()
    assert p.vitals["Air"] == 50
    assert not p.has_condition("suffocating")

    # Full refill
    w.tick_turn()
    assert p.vitals["Air"] == 100
