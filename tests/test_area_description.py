"""Tests for the area-description "People here" listing.

Verifies that intrinsic abilities (spells/talents) are never shown in the
holding list and that strangers appear by description (task-171 follow-up,
task-154).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import MagicMock

from graph import WorldGraph, Node, Edge, EDGE_IN, EDGE_CARRYING
from player import Player
from engine.player_manager import PlayerManager
from engine.area_description import AreaDescription, _is_intrinsic_ability


class PlayerManagerWithIds(PlayerManager):
    """PlayerManager plus the node-id helpers AreaDescription expects."""

    def player_node_id(self, name):
        return self.get_player_node_id(name)

    def area_node_id(self, name):
        return f"area_{name.lower()}".replace(' ', '_')

    def apply_action(self, action_name, player=None):
        return None


def _make_world():
    graph = WorldGraph()
    area = Node(
        id="area_Test",
        type="area",
        name="Test",
        properties={
            "description": "A small test room.",
            "environment": {
                "light": 80, "temperature": 21, "air": "fresh",
                "smell": "neutral", "noise": "quiet",
            },
        },
    )
    graph.add_node(area)

    pm = PlayerManagerWithIds(graph)
    hero = Player("Hero")
    hero.current_area = "Test"
    pm.add_player(hero)
    pm.set_active_player("Hero")

    lyrie = Player("Lyrie")
    lyrie.current_area = "Test"
    lyrie.description = "A tall woman with long auburn hair and a green cloak."
    pm.add_player(lyrie)
    pm.set_active_player("Hero")

    create_flame = Node(
        id="item_Create Flame",
        type="item",
        name="Create Flame",
        properties={"tags": ["fire", "spell", "magic"]},
    )
    graph.add_node(create_flame)
    graph.add_edge(Edge(source=create_flame.id, target=pm.get_player_node_id("Lyrie"), type=EDGE_CARRYING))

    waterskin = Node(
        id="item_waterskin",
        type="item",
        name="Waterskin",
        properties={"tags": ["container"]},
    )
    graph.add_node(waterskin)
    graph.add_edge(Edge(source=waterskin.id, target=pm.get_player_node_id("Lyrie"), type=EDGE_CARRYING))

    lighting = MagicMock()
    lighting.can_see_in_dark = MagicMock(return_value=True)
    lighting.get_ambient_light = MagicMock(return_value=80)
    lighting.light_to_level = MagicMock(return_value="bright")
    lighting.get_light_int = MagicMock(return_value=80)

    desc = AreaDescription(graph, lighting, pm, MagicMock())
    return graph, pm, desc


class TestHoldingFilter:
    def test_intrinsic_abilities_hidden_from_holding(self):
        """Create Flame (spell tag) never appears in the holding list."""
        _, _, desc = _make_world()
        output = desc.get_area_description()
        assert "Create Flame" not in output
        assert "Waterskin" in output
        assert "[holding: Waterskin]" in output

    def test_real_name_shown_after_meeting(self):
        """After LEARNING the name (task-339), the real name + full
        description appear. register_first_meeting alone is only
        recognition and keeps the label masked."""
        _, pm, desc = _make_world()
        pm.players["Hero"].register_first_meeting("Lyrie", tick=1)
        output = desc.get_area_description()
        assert "Lyrie" not in output  # recognition is not name knowledge
        pm.players["Hero"].learn_name("Lyrie", tick=2)
        output = desc.get_area_description()
        assert "Lyrie" in output
        assert "tall woman" in output

    def test_stranger_shown_by_description(self):
        """Before meeting, the character appears by appearance, not name."""
        _, _, desc = _make_world()
        output = desc.get_area_description()
        assert "Lyrie" not in output
        assert "tall woman" in output

    def test_name_never_revealed_by_sighting(self):
        """task-339: sighting registers recognition (masked label) but the
        name NEVER reveals by looking again — only hearing it spoken."""
        _, pm, desc = _make_world()
        first = desc.get_area_description()
        assert "Lyrie" not in first
        second = desc.get_area_description()
        assert "Lyrie" not in second
        pm.players["Hero"].learn_name("Lyrie", tick=2)
        third = desc.get_area_description()
        assert "Lyrie" in third

    def test_wearing_split_from_holding(self):
        """Equipped items render as [wearing: ...], carried items as
        [holding: ...], and an item on both edges only counts as worn."""
        graph, _, desc = _make_world()
        jumpsuit = Node(
            id="item_jumpsuit",
            type="item",
            name="Jumpsuit",
            properties={"tags": ["clothing"]},
        )
        graph.add_node(jumpsuit)
        graph.add_edge(Edge(
            source=jumpsuit.id,
            target="player_Lyrie",
            type="equipped",
            properties={"slot": "body"},
        ))
        # Waterskin is on EDGE_CARRYING from the fixture.
        output = desc.get_area_description()
        assert "[wearing: Jumpsuit]" in output
        assert "[holding: Waterskin]" in output
        assert "Jumpsuit" not in output.replace("[wearing: Jumpsuit]", "")

    def test_stranger_shows_first_sentence_description(self):
        """A stranger's first-sentence description is shown at a glance —
        '<label> — A tall woman...' — not just the bare appearance label."""
        _, _, desc = _make_world()
        output = desc.get_area_description()
        assert "tall woman with long auburn hair and a green cloak" in output
        # The first-sentence description appears twice: once as the label
        # itself, once as the glance suffix after the em-dash.
        assert "— A tall woman with long auburn hair and a green cloak." in output

    def test_is_intrinsic_ability_string_tags(self):
        """_is_intrinsic_ability handles both list and comma-string tags."""
        node = Node(id="x", type="item", name="X", properties={"tags": "fire, spell, magic"})
        assert _is_intrinsic_ability(node) is True
        node2 = Node(id="y", type="item", name="Y", properties={"tags": ["scroll", "magic"]})
        assert _is_intrinsic_ability(node2) is False
        assert _is_intrinsic_ability(None) is False
