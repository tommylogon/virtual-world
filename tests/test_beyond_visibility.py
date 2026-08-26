"""Tests for beyond-way visibility (task-201)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import MagicMock

from graph import WorldGraph, Node, Edge, EDGE_IN, EDGE_CONNECTION
from player import Player
from engine.player_manager import PlayerManager
from engine.area_description import AreaDescription
from engine.beyond_visibility import collect_items_in_area, normalize_visible_items, build_beyond_suffix


class PlayerManagerWithIds(PlayerManager):
    def player_node_id(self, name):
        return self.get_player_node_id(name)

    def area_node_id(self, name):
        return f"area_{name.lower()}".replace(' ', '_')

    def apply_action(self, action_name, player=None):
        return None


def _make_two_room_world(way_state="open", see_through=False):
    graph = WorldGraph()
    kitchen = Node(
        id="area_Kitchen",
        type="area",
        name="Kitchen",
        properties={"description": "A kitchen.", "environment": {"light": 80, "temperature": 21}},
    )
    hall = Node(
        id="area_Hall",
        type="area",
        name="Hall",
        properties={"description": "A hall.", "environment": {"light": 40, "temperature": 20, "noise": "quiet"}},
    )
    way = Node(
        id="way_kitchen_door",
        type="way",
        name="Kitchen - door",
        properties={
            "current_state": way_state,
            "description": "A doorway.",
            "see_through": see_through,
        },
    )
    clock = Node(
        id="item_clock",
        type="item",
        name="Grandfather Clock",
        properties={"description": "A tall clock.", "current_state": "normal"},
    )
    rug = Node(
        id="item_rug",
        type="item",
        name="Rug",
        properties={"description": "A rug.", "current_state": "normal"},
    )
    for node in (kitchen, hall, way, clock, rug):
        graph.add_node(node)
    graph.add_edge(Edge(source="player_Hero", target="area_Kitchen", type=EDGE_IN))
    graph.add_edge(Edge(source=clock.id, target=hall.id, type=EDGE_IN))
    graph.add_edge(Edge(source=rug.id, target=hall.id, type=EDGE_IN))
    graph.add_edge(Edge(
        source="area_Kitchen",
        target=way.id,
        type=EDGE_CONNECTION,
        properties={
            "direction": "door",
            "allow_see_characters": True,
            "visible_items": ["Grandfather Clock"],
        },
    ))
    graph.add_edge(Edge(source=way.id, target="area_Hall", type=EDGE_CONNECTION, properties={"direction": "enter"}))
    graph.add_edge(Edge(source=way.id, target="area_Kitchen", type=EDGE_CONNECTION, properties={"direction": "door"}))

    pm = PlayerManagerWithIds(graph)
    hero = Player("Hero")
    hero.current_area = "Kitchen"
    pm.add_player(hero)
    pm.set_active_player("Hero")

    lyrie = Player("Lyrie")
    lyrie.current_area = "Hall"
    lyrie.description = "A tall woman in a green cloak."
    pm.add_player(lyrie)
    pm.set_active_player("Hero")

    lighting = MagicMock()
    lighting.can_see_in_dark = MagicMock(return_value=True)
    lighting.get_ambient_light = MagicMock(side_effect=lambda area_id, env: int(env.get("light", 80)))
    lighting.light_to_level = MagicMock(return_value="normal")
    lighting.get_light_int = MagicMock(return_value=80)

    desc = AreaDescription(graph, lighting, pm, MagicMock())
    return graph, pm, desc, hero


class TestBeyondVisibilityHelpers:
    def test_normalize_visible_items(self):
        assert normalize_visible_items(None) == []
        assert normalize_visible_items([" Clock ", ""]) == ["Clock"]
        assert normalize_visible_items("Lantern") == ["Lantern"]

    def test_collect_items_filters_by_name(self):
        graph, _, _, _ = _make_two_room_world()
        all_items = collect_items_in_area(graph, "area_Hall", None)
        assert set(all_items) == {"Grandfather Clock", "Rug"}
        filtered = collect_items_in_area(graph, "area_Hall", ["Grandfather Clock"])
        assert filtered == ["Grandfather Clock"]

    def test_build_beyond_suffix_lists_people_and_items(self):
        graph, pm, _, hero = _make_two_room_world()
        edge_props = {"allow_see_characters": True, "visible_items": ["Grandfather Clock"]}
        suffix = build_beyond_suffix(graph, pm, "area_Hall", "Hall", edge_props, hero)
        assert "Beyond you can see:" in suffix
        assert "Grandfather Clock" in suffix
        assert "Lyrie" not in suffix  # stranger label before meeting
        assert "woman" in suffix or "tall" in suffix


class TestAreaDescriptionBeyond:
    def test_open_way_shows_beyond_people_and_selected_items(self):
        _, pm, desc, _ = _make_two_room_world(way_state="open")
        pm.players["Hero"].register_first_meeting("Lyrie", tick=1)
        output = desc.get_area_description()
        assert "visible beyond" in output
        assert "Lyrie" in output
        assert "Grandfather Clock" in output
        assert "Rug" not in output

    def test_closed_opaque_way_hides_beyond(self):
        _, _, desc, _ = _make_two_room_world(way_state="closed", see_through=False)
        output = desc.get_area_description()
        assert "Beyond you can see" not in output

    def test_see_through_closed_way_shows_beyond(self):
        _, pm, desc, _ = _make_two_room_world(way_state="closed", see_through=True)
        graph = desc.graph
        for edge in graph.get_edges_for_source("area_Kitchen", EDGE_CONNECTION):
            if edge.target == "way_kitchen_door":
                edge.properties["visible_in_direction"] = "the hall beyond"
        pm.players["Hero"].register_first_meeting("Lyrie", tick=1)
        output = desc.get_area_description()
        assert "through it you can see the hall beyond" in output
        assert "Lyrie" in output
        assert "Grandfather Clock" in output

    def test_build_exits_for_area_exports_visibility_fields(self):
        _, _, desc, _ = _make_two_room_world(way_state="open")
        exits = desc.build_exits_for_area("Kitchen")
        assert exits
        exit_data = next(iter(exits.values()))
        assert exit_data["allow_see_characters"] is True
        assert exit_data["visible_items"] == ["Grandfather Clock"]
