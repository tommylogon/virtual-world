"""Unit tests for scene chips display name resolution and item state formatting (task-682)."""

from unittest.mock import MagicMock

from graph import WorldGraph, Node, Edge, EDGE_IN, EDGE_CARRYING
from player import Player
from engine.scene_snapshot import build_scene
from engine.room_perception import resolve_item_name, describe_item_quantity


def test_resolve_item_name_normalizes_snake_case():
    """Items whose name is a snake_case id are normalized to readable spaces."""
    assert resolve_item_name(Node(id="item_coat_rack", type="item", name="coat_rack")) == "coat rack"
    assert resolve_item_name(Node(id="item_calling_cards", type="item", name="calling_cards")) == "calling cards"
    assert resolve_item_name(Node(id="item_protein_bar", type="item", name="protein_bar")) == "protein bar"
    assert resolve_item_name(Node(id="item_vase", type="item", name="vase")) == "vase"


def test_resolve_item_name_prefers_authored_display_name_or_label():
    """Authored display_name or label property takes precedence over raw node name."""
    node_with_display = Node(
        id="item_energy_drink",
        type="item",
        name="energy_drink",
        properties={"display_name": "Mega Energy Drink"}
    )
    assert resolve_item_name(node_with_display) == "Mega Energy Drink"

    node_with_label = Node(
        id="item_cutoffs",
        type="item",
        name="denim_cutoffs",
        properties={"label": "denim cut-offs"}
    )
    assert resolve_item_name(node_with_label) == "denim cut-offs"


def test_describe_item_quantity_uses_resolved_display_name():
    """describe_item_quantity reflects resolved display names and pluralization."""
    single = Node(id="i1", type="item", name="protein_bar")
    assert describe_item_quantity(single) == "protein bar"

    pooled = Node(
        id="i2",
        type="item",
        name="wild_berries",
        properties={"quantity": 5}
    )
    assert describe_item_quantity(pooled) == "5 wild berries"


def test_scene_snapshot_emits_resolved_names_and_display_name_property():
    """build_scene emits human-readable name and display_name on area items and carried items."""
    g = WorldGraph()
    area = Node(id="area_lobby", type="area", name="Lobby", properties={"environment": {"light": 90}})
    g.add_node(area)

    coat_rack = Node(id="item_coat_rack", type="item", name="coat_rack")
    g.add_node(coat_rack)
    g.add_edge(Edge(source="item_coat_rack", target="area_lobby", type=EDGE_IN))

    energy_drink = Node(
        id="item_energy_drink",
        type="item",
        name="energy_drink",
        properties={"current_state": "broken"}
    )
    g.add_node(energy_drink)

    player_node = Node(id="player_tester", type="character", name="Tester")
    g.add_node(player_node)
    g.add_edge(Edge(source="player_tester", target="area_lobby", type=EDGE_IN))
    g.add_edge(Edge(source="item_energy_drink", target="player_tester", type=EDGE_CARRYING))

    player = Player(name="Tester")
    player.current_area = "Lobby"

    class WorldStub:
        def __init__(self, graph, p):
            self.graph = graph
            self.player_manager = MagicMock()
            self.player_manager.players = {"Tester": p}
            self.player_manager.is_slasher.return_value = False
            self.player_manager._player_node_id = lambda name: "player_tester"
            self.area_node_id = lambda name: "area_lobby"
            self.area_description = None
        def _get_available_actions(self, node, carrying=False):
            return ["examine", "take"]

    scene = build_scene(WorldStub(g, player), "Tester")

    # Check area items
    items = scene.get("items", [])
    assert len(items) == 1
    assert items[0]["name"] == "coat rack"
    assert items[0]["display_name"] == "coat rack"

    # Check carried items in you strip
    you = scene.get("you", {})
    carried = you.get("carrying", [])
    assert len(carried) == 1
    assert carried[0]["name"] == "energy drink"
    assert carried[0]["display_name"] == "energy drink"
    assert carried[0]["current_state"] == "broken"
