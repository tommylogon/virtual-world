"""Tests for the descriptive-target fallback (flavor text interactions).

Verifies that examining or using items on objects that only exist in
descriptive text produces a contextual narrative response instead of a
plain "not found" error.

Uses a self-contained foyer graph (not live autosave.json) so the tests
don't depend on whichever scenario happens to be loaded.
"""
import pytest
from unittest.mock import MagicMock

from graph import WorldGraph, Node, Edge, EDGE_IN, EDGE_CONNECTION
from engine.item_actions import ItemActions


@pytest.fixture
def graph():
    """Build a mansion-style foyer graph with flavor objects in descriptions."""
    g = WorldGraph()

    foyer = Node(
        id="area_foyer",
        type="area",
        name="Foyer",
        properties={
            "description": (
                "A grand foyer with a sweeping marble floor. A crystal "
                "chandelier hangs from the ceiling, and a heavy oak door "
                "stands to the north. Near the wall stands an old iron "
                "stove, cold and unlit."
            )
        },
    )
    g.add_node(foyer)

    # A real item in the room (so real-item matching still works)
    coat = Node(
        id="item_coat",
        type="item",
        name="Winter Coat",
        properties={"description": "A heavy wool coat."},
    )
    g.add_node(coat)
    g.add_edge(Edge(source=coat.id, target=foyer.id, type=EDGE_IN))

    # A real item that shares a word with a flavor object: the classic
    # "stove" vs "stovepipe boots" collision (word-boundary matching).
    boots = Node(
        id="item_stovepipe_boots",
        type="item",
        name="Stovepipe Leather Boots (Pair)",
        properties={"description": "Tall leather boots."},
    )
    g.add_node(boots)
    g.add_edge(Edge(source=boots.id, target=foyer.id, type=EDGE_IN))

    # An open door with a description (scanning way descriptions)
    door = Node(
        id="way_foyer_north",
        type="way",
        name="oak door",
        properties={"description": "A heavy oak door leading north."},
    )
    g.add_node(door)
    g.add_edge(Edge(
        source=foyer.id, target=door.id, type=EDGE_CONNECTION,
        properties={"direction": "north"}
    ))

    return g


@pytest.fixture
def player_manager(graph):
    """Build a minimal player_manager mock backed by the real graph."""
    pm = MagicMock()
    pm.graph = graph
    pm.active_player = "Jake Halloway"
    pm.players = {"Jake Halloway": MagicMock(state="awake")}
    pm.current_area = MagicMock()
    pm.current_area.name = "Foyer"
    pm.record_turn_event = MagicMock()

    def _get_current_area_id():
        return "area_foyer"

    def _player_node_id(name):
        return "player_jake_halloway"

    def _area_node_id(name):
        return "area_foyer"

    pm._get_current_area_id = _get_current_area_id
    pm._player_node_id = _player_node_id
    pm._area_node_id = _area_node_id
    pm.lighting = MagicMock()
    pm.lighting.can_see_in_dark = MagicMock(return_value=True)
    pm.ghost_mode = False
    pm.player = pm.players["Jake Halloway"]
    return pm


@pytest.fixture
def item_actions(graph, player_manager):
    ia = ItemActions.__new__(ItemActions)
    ia.graph = graph
    ia.matching = None
    ia.trigger_system = MagicMock()
    ia.trigger_system._get_available_actions = MagicMock(return_value=[])
    ia.trigger_system._contextual_failure = MagicMock(return_value="")
    ia.trigger_system._execute_triggers = MagicMock(return_value=[])
    ia.equipment = MagicMock()
    ia.ghost_system = MagicMock()
    ia.ghost_system.check_ghost_action = MagicMock(return_value=None)
    ia.world = MagicMock()
    return ia


class TestDescribeFlavorTarget:
    def test_flavor_match_returns_sentence(self, item_actions, player_manager, graph):
        """An object mentioned only in the area description returns a narrative."""
        result = item_actions._describe_flavor_target(player_manager, "chandelier", "area_foyer")
        assert result is not None
        assert "chandelier" in result.lower() or "crystal" in result.lower()

    def test_flavor_match_marble(self, item_actions, player_manager, graph):
        result = item_actions._describe_flavor_target(player_manager, "marble floor", "area_foyer")
        assert result is not None
        assert "marble" in result.lower()

    def test_no_match_returns_none(self, item_actions, player_manager, graph):
        result = item_actions._describe_flavor_target(player_manager, "quantum flux capacitor", "area_foyer")
        assert result is None

    def test_empty_target_returns_none(self, item_actions, player_manager, graph):
        assert item_actions._describe_flavor_target(player_manager, "", "area_foyer") is None

    def test_examine_stove_uses_flavor_not_boots(self, item_actions, player_manager, graph):
        """'examine stove' returns the area-description flavor text with the
        no-use note — never the Stovepipe Leather Boots item (F4/F8)."""
        from engine.matching import NameMatching
        item_actions.matching = NameMatching(graph, player_manager)

        result = item_actions.get_item_desc(player_manager, "stove")

        assert result is not None
        assert "stove" in result.lower()
        assert "of any use" in result.lower()
        assert "Stovepipe" not in result


class TestDescriptiveTargetFailure:
    # task-340 follow-up: descriptive failures now RAISE ValueError (so
    # /api/action reports success=false) instead of returning the message.
    def test_use_on_flavor_target_gives_narrative(self, item_actions, player_manager, graph):
        """Using an item on a flavor object raises an in-character failure."""
        item_actions.matching = MagicMock()
        item_actions.matching._match_item_name = MagicMock(return_value=None)
        item_actions.matching._match_exit_direction = MagicMock(return_value=None)
        item_actions.use_item_on = item_actions.use_item_on.__get__(item_actions)

        with pytest.raises(ValueError) as excinfo:
            item_actions._descriptive_target_failure(player_manager, "multitool", "chandelier", "area_foyer")
        assert "chandelier" in str(excinfo.value)
        # It should have logged a turn event so others can witness the attempt
        player_manager.record_turn_event.assert_called_once()

    def test_use_on_unknown_target_returns_none(self, item_actions, player_manager, graph):
        result = item_actions._descriptive_target_failure(player_manager, "multitool", "spaceship", "area_foyer")
        assert result is None

    def test_use_on_flavor_via_real_matching(self, item_actions, player_manager, graph):
        """'use kindling on stove' should fall through to the descriptive
        failure — never match 'Stovepipe Leather Boots (Pair)' (F4/F8)."""
        from engine.matching import NameMatching
        item_actions.matching = NameMatching(graph, player_manager)
        with pytest.raises(ValueError) as excinfo:
            item_actions._descriptive_target_failure(player_manager, "kindling", "stove", "area_foyer")
        assert "stove" in str(excinfo.value).lower()
        assert "stovepipe" not in str(excinfo.value).lower()

    def test_fire_item_gets_fire_failure_text(self, item_actions, player_manager, graph):
        """Using a fire-tagged item on scenery gives fire-appropriate text."""
        fire_item = Node(
            id="item_create_flame",
            type="item",
            name="Create Flame",
            properties={"tags": ["fire", "spell", "magic"]},
        )
        with pytest.raises(ValueError) as excinfo:
            item_actions._descriptive_target_failure(
                player_manager, "create flame", "stove", "area_foyer", item_node=fire_item
            )
        result = str(excinfo.value)
        assert any(word in result.lower() for word in ("catch", "ignite", "smolder", "burn"))
        assert "movable" not in result.lower()

    def test_heat_source_item_gets_fire_failure_text(self, item_actions, player_manager, graph):
        """heat_source tag triggers fire-appropriate text too."""
        torch = Node(
            id="item_torch",
            type="item",
            name="Torch",
            properties={"tags": ["light_source", "heat_source"]},
        )
        with pytest.raises(ValueError) as excinfo:
            item_actions._descriptive_target_failure(
                player_manager, "torch", "stove", "area_foyer", item_node=torch
            )
        result = str(excinfo.value)
        assert any(word in result.lower() for word in ("catch", "ignite", "smolder", "burn"))

    def test_non_fire_item_keeps_scenery_reasons(self, item_actions, player_manager, graph):
        """Non-fire items still get the generic scenery failure text."""
        key = Node(
            id="item_key",
            type="item",
            name="Rusty Key",
            properties={"tags": ["metal"]},
        )
        with pytest.raises(ValueError) as excinfo:
            item_actions._descriptive_target_failure(
                player_manager, "rusty key", "stove", "area_foyer", item_node=key
            )
        result = str(excinfo.value)
        assert not any(word in result.lower() for word in ("catch", "ignite", "smolder", "burn"))

    def test_fire_item_without_node_uses_generic(self, item_actions, player_manager, graph):
        """No item node passed (unknown source) falls back to generic text."""
        with pytest.raises(ValueError) as excinfo:
            item_actions._descriptive_target_failure(
                player_manager, "create flame", "stove", "area_foyer"
            )
        result = str(excinfo.value)
        assert not any(word in result.lower() for word in ("catch", "ignite", "smolder", "burn"))
