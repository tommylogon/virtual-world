"""Tests for EDGE_KNOWN ability/spell knowledge system (task-392)."""
import json
import pytest

from graph import WorldGraph, Node, Edge, EDGE_KNOWN, EDGE_CARRYING, EDGE_EQUIPPED
from player import Player
from engine.player_manager import PlayerManager
from engine.equipment import INTRINSIC_ABILITY_TAGS


def _make_world():
    graph = WorldGraph()
    pm = PlayerManager(graph)
    player = Player("Lyrie")
    pm.add_player(player)
    pm.set_active_player("Lyrie")
    return graph, pm


def test_edge_known_constant_exists():
    assert EDGE_KNOWN == "known"


def test_find_item_node_resolves_known_ability():
    graph, pm = _make_world()
    flame = Node(id="item_create_flame", type="item", name="Create Flame", properties={
        "actions": ["examine", "use"],
        "tags": ["fire", "spell", "magic"],
    })
    graph.add_node(flame)
    graph.add_edge(Edge(source=flame.id, target=pm.get_player_node_id("Lyrie"), type=EDGE_KNOWN))

    found = pm.find_item_node("Create Flame")
    assert found is not None
    assert found.id == flame.id


def test_known_ability_does_not_appear_as_carrying_or_equipped():
    graph, pm = _make_world()
    flame = Node(id="item_create_flame", type="item", name="Create Flame", properties={
        "actions": ["examine", "use"],
        "tags": ["fire", "spell", "magic"],
    })
    graph.add_node(flame)
    graph.add_edge(Edge(source=flame.id, target=pm.get_player_node_id("Lyrie"), type=EDGE_KNOWN))

    carrying = graph.get_edges_for_target(pm.get_player_node_id("Lyrie"), EDGE_CARRYING)
    equipped = graph.get_edges_for_target(pm.get_player_node_id("Lyrie"), EDGE_EQUIPPED)
    known = graph.get_edges_for_target(pm.get_player_node_id("Lyrie"), EDGE_KNOWN)

    assert not any(e.source == flame.id for e in carrying)
    assert not any(e.source == flame.id for e in equipped)
    assert any(e.source == flame.id for e in known)


def test_known_ability_priority_behind_carrying():
    graph, pm = _make_world()
    flame = Node(id="item_create_flame", type="item", name="Create Flame", properties={
        "actions": ["examine", "use"],
        "tags": ["fire", "spell", "magic"],
    })
    graph.add_node(flame)
    # Physical copy carried
    graph.add_edge(Edge(source=flame.id, target=pm.get_player_node_id("Lyrie"), type=EDGE_CARRYING))
    # Knowledge copy
    knowledge = Node(id="item_create_flame_knowledge", type="item", name="Create Flame", properties={
        "actions": ["examine", "use"],
        "tags": ["fire", "spell", "magic"],
    })
    graph.add_node(knowledge)
    graph.add_edge(Edge(source=knowledge.id, target=pm.get_player_node_id("Lyrie"), type=EDGE_KNOWN))

    found = pm.find_item_node("Create Flame")
    assert found is not None
    assert found.id == flame.id


def test_scene_snapshot_includes_known_abilities():
    from engine.scene_snapshot import build_scene

    graph, pm = _make_world()
    flame = Node(id="item_create_flame", type="item", name="Create Flame", properties={
        "actions": ["examine", "use"],
        "tags": ["fire", "spell", "magic"],
    })
    graph.add_node(flame)
    graph.add_edge(Edge(source=flame.id, target=pm.get_player_node_id("Lyrie"), type=EDGE_KNOWN))

    area = Node(id="area_test", type="area", name="Test Room", properties={"description": "A room.", "environment": {}})
    graph.add_node(area)
    graph.add_edge(Edge(source=pm.get_player_node_id("Lyrie"), target=area.id, type="in"))
    pm.players["Lyrie"].current_area = "Test Room"

    class DummyWorld:
        pass
    dummy = DummyWorld()
    dummy.graph = graph
    dummy.player_manager = pm
    dummy.lighting = type("L", (), {"get_ambient_light": lambda *_: 80 })()
    dummy.area_description = type("AD", (), {"_render_node": lambda self, node: node.properties.get("description", "") if node else ""})()

    scene = build_scene(dummy, "Lyrie")
    assert "known_abilities" in scene["you"]
    assert "Create Flame" in scene["you"]["known_abilities"]


def test_examine_resolves_known_ability():
    graph, pm = _make_world()
    flame = Node(id="item_create_flame", type="item", name="Create Flame", properties={
        "actions": ["examine", "use"],
        "tags": ["fire", "spell", "magic"],
        "description": "A small flame.",
    })
    graph.add_node(flame)
    graph.add_edge(Edge(source=flame.id, target=pm.get_player_node_id("Lyrie"), type=EDGE_KNOWN))

    area = Node(id="area_test_room", type="area", name="Test Room", properties={"description": "A room.", "environment": {}})
    graph.add_node(area)
    graph.add_edge(Edge(source=pm.get_player_node_id("Lyrie"), target=area.id, type="in"))
    pm.players["Lyrie"].current_area = "Test Room"

    found = pm.find_item_node("Create Flame")
    assert found is not None
    assert found.id == flame.id


def test_autocomplete_includes_known_abilities():
    from engine.autocomplete import get_autocomplete_options

    graph, pm = _make_world()
    flame = Node(id="item_create_flame", type="item", name="Create Flame", properties={
        "actions": ["examine", "use"],
        "tags": ["fire", "spell", "magic"],
        "name": "Create Flame",
    })
    graph.add_node(flame)
    graph.add_edge(Edge(source=flame.id, target=pm.get_player_node_id("Lyrie"), type=EDGE_KNOWN))

    area = Node(id="area_test", type="area", name="Test Room", properties={"description": "A room.", "environment": {}})
    graph.add_node(area)
    graph.add_edge(Edge(source=pm.get_player_node_id("Lyrie"), target=area.id, type="in"))
    pm.players["Lyrie"].current_area = "Test Room"

    class DummyWorld:
        pass
    dummy = DummyWorld()
    dummy.graph = graph
    dummy.player_manager = pm
    dummy._get_area_id_for_player = lambda name: "area_test"

    opts = get_autocomplete_options(dummy, "use", "")
    assert "Create Flame" in opts or "item_create_flame" in opts

    opts = get_autocomplete_options(dummy, "examine", "")
    assert "Create Flame" in opts or "item_create_flame" in opts
