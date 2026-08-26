"""Tests for the TriggerSystem: conditions, effects, and template rendering."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import MagicMock
from graph import Node, Edge, EDGE_TRIGGERS, EDGE_EQUIPPED, EDGE_CONNECTION
from engine.trigger_system import TriggerSystem
from engine.effects import Effects


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ Fixtures â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@pytest.fixture
def graph():
    """Create a bare WorldGraph."""
    from graph import WorldGraph
    return WorldGraph()


@pytest.fixture
def skills():
    """Create a SkillSystem with mock dependencies."""
    from engine.skills import SkillSystem
    from engine.player_manager import PlayerManager
    from engine.logging_events import GameLogger
    pm = PlayerManager(None)  # graph can be None for basic tests
    return SkillSystem(pm, GameLogger())


@pytest.fixture
def logging_events():
    """Create a GameLogger."""
    from engine.logging_events import GameLogger
    return GameLogger()


@pytest.fixture
def trigger_system(graph, skills, logging_events):
    """Create a TriggerSystem with all dependencies."""
    return TriggerSystem(graph, skills, logging_events)


@pytest.fixture
def sample_item(graph):
    """Create a basic item node in the graph."""
    item = Node(
        id="item_test_item",
        type="item",
        name="Test Item",
        properties={
            "description": "A test item.",
            "uses": 1,
            "current_state": "normal",
            "actions": ["examine", "take", "use"],
        }
    )
    graph.add_node(item)
    return item


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ TestConditions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestConditions:
    """Condition evaluation within triggers."""

    def test_uses_reached_triggers(self, graph, trigger_system, sample_item):
        """When item uses equals or is below the condition threshold, condition passes."""
        sample_item.properties["uses"] = 0
        condition = {"type": "uses_reached", "value": "0"}
        result = trigger_system._evaluate_trigger_condition(condition, sample_item)
        assert result is True

    def test_uses_reached_does_not_trigger(self, graph, trigger_system, sample_item):
        """When item uses is above the threshold, condition fails."""
        sample_item.properties["uses"] = 5
        condition = {"type": "uses_reached", "value": "0"}
        result = trigger_system._evaluate_trigger_condition(condition, sample_item)
        assert result is False

    def test_uses_reached_negative(self, graph, trigger_system, sample_item):
        """When uses is -1 and condition is 0: -1 <= 0 is True.
        Note: the engine treats -1 <= 0 as triggering, which may be
        a known limitation. A separate check for unlimited uses
        (uses == -1) would be needed to skip this condition."""
        sample_item.properties["uses"] = -1
        condition = {"type": "uses_reached", "value": "0"}
        result = trigger_system._evaluate_trigger_condition(condition, sample_item)
        # Current engine evaluates -1 <= 0 as True
        assert result is True

    def test_random_chance_always_true(self, trigger_system, sample_item):
        """random_chance with 100% always passes."""
        condition = {"type": "random_chance", "value": "100"}
        result = trigger_system._evaluate_trigger_condition(condition, sample_item)
        assert result is True

    def test_random_chance_always_false(self, trigger_system, sample_item):
        """random_chance with 0% always fails."""
        condition = {"type": "random_chance", "value": "0"}
        result = trigger_system._evaluate_trigger_condition(condition, sample_item)
        assert result is False

    def test_empty_condition_returns_true(self, trigger_system, sample_item):
        """When condition is empty/None, evaluation returns True."""
        assert trigger_system._evaluate_trigger_condition({}, sample_item) is True
        assert trigger_system._evaluate_trigger_condition(None, sample_item) is True

    def test_unknown_condition_type_returns_false(self, trigger_system, sample_item):
        """Unknown condition type returns False (fail-safe)."""
        condition = {"type": "unknown_condition", "value": "anything"}
        result = trigger_system._evaluate_trigger_condition(condition, sample_item)
        assert result is False

    def test_condition_tree_and_operator(self, trigger_system):
        """AND operator requires all sub-conditions to be true."""
        conditions = {
            "operator": "and",
            "conditions": [
                {"type": "eq", "target": "test_key", "value": "yes"},
                {"type": "eq", "target": "another_key", "value": "also_yes"},
            ]
        }
        context = {"test_key": "yes", "another_key": "also_yes"}
        assert trigger_system._evaluate_conditions(conditions, context) is True

    def test_condition_tree_and_fails(self, trigger_system):
        """AND operator fails if one sub-condition fails."""
        conditions = {
            "operator": "and",
            "conditions": [
                {"type": "eq", "target": "test_key", "value": "yes"},
                {"type": "eq", "target": "another_key", "value": "nope"},
            ]
        }
        context = {"test_key": "yes", "another_key": "also_yes"}
        assert trigger_system._evaluate_conditions(conditions, context) is False

    def test_condition_tree_or_operator(self, trigger_system):
        """OR operator succeeds if any sub-condition is true."""
        conditions = {
            "operator": "or",
            "conditions": [
                {"type": "eq", "target": "test_key", "value": "no"},
                {"type": "eq", "target": "another_key", "value": "yes"},
            ]
        }
        context = {"test_key": "maybe", "another_key": "yes"}
        assert trigger_system._evaluate_conditions(conditions, context) is True

    def test_condition_tree_not_operator(self, trigger_system):
        """NOT operator inverts a sub-condition."""
        conditions = {
            "operator": "not",
            "conditions": [
                {"type": "eq", "target": "test_key", "value": "nope"},
            ]
        }
        context = {"test_key": "yes"}
        # eq fails, not fails â†’ true
        assert trigger_system._evaluate_conditions(conditions, context) is True

    def test_condition_tree_empty_returns_true(self, trigger_system):
        """Empty or None conditions return True."""
        assert trigger_system._evaluate_conditions({}, {}) is True
        assert trigger_system._evaluate_conditions(None, {}) is True

    def test_has_item_condition_with_inventory(self, graph, trigger_system, sample_item):
        """has_item checks if an item is in a player's inventory through game_state."""
        from player import Player
        # Build a minimal game_state
        player = Player("TestPlayer")
        player_id = f"player_{player.name}"

        # Add player node and edge to graph
        player_node = Node(id=player_id, type="character", name="TestPlayer")
        graph.add_node(player_node)

        # Add item and connect to player
        graph.add_edge(
            Edge(source=sample_item.id, target=player_id, type="location")
        )

        class FakeGameState:
            active_player = "TestPlayer"
            def _player_node_id(self, name):
                return f"player_{name}"
            def _get_current_area_id(self):
                return None

        condition = {"type": "has_item", "value": "Test Item"}
        result = trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=FakeGameState()
        )
        assert result is True

    def test_has_item_condition_missing(self, graph, trigger_system, sample_item):
        """has_item returns False when item is not in inventory."""
        class FakeGameState:
            active_player = "EmptyPlayer"
            def _player_node_id(self, name):
                return f"player_{name}"
            def _get_current_area_id(self):
                return None

        condition = {"type": "has_item", "value": "Nonexistent Item"}
        result = trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=FakeGameState()
        )
        assert result is False

    def test_state_equals_direct(self, graph, trigger_system, sample_item):
        """state_equals checks the item's current_state property."""
        sample_item.properties["current_state"] = "open"
        condition = {"type": "state_equals", "value": "open"}
        result = trigger_system._evaluate_trigger_condition(condition, sample_item)
        assert result is True

    def test_state_equals_mismatch(self, graph, trigger_system, sample_item):
        """state_equals fails when state doesn't match."""
        sample_item.properties["current_state"] = "closed"
        condition = {"type": "state_equals", "value": "open"}
        result = trigger_system._evaluate_trigger_condition(condition, sample_item)
        assert result is False

    def test_has_trait_condition_active_player(self, graph, trigger_system, sample_item):
        """has_trait checks the active player's traits."""
        from player import Player
        player = Player("TestPlayer")
        player.traits["dark_vision"] = True
        game_state = type("FakeGameState", (), {})()
        game_state.players = {"TestPlayer": player}
        game_state.active_player = "TestPlayer"
        game_state.player = player

        condition = {"type": "has_trait", "value": "dark_vision"}
        assert trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=game_state
        ) is True

        condition = {"type": "has_trait", "value": "hardy"}
        assert trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=game_state
        ) is False

    def test_has_trait_condition_named_target(self, graph, trigger_system, sample_item):
        """has_trait resolves a named target from game_state.players."""
        from player import Player
        player = Player("TestPlayer")
        other = Player("Other")
        other.traits["hostile"] = True
        game_state = type("FakeGameState", (), {})()
        game_state.players = {"TestPlayer": player, "Other": other}
        game_state.active_player = "TestPlayer"
        game_state.player = player

        condition = {"type": "has_trait", "value": "hostile", "target": "Other"}
        assert trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=game_state
        ) is True
        # Case-insensitive name match
        condition = {"type": "has_trait", "value": "hostile", "target": "other"}
        assert trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=game_state
        ) is True

    def test_has_tag_condition_active_player(self, graph, trigger_system, sample_item):
        """has_tag checks the active player's tags."""
        from player import Player
        player = Player("TestPlayer")
        player.tags = ["vampire", "faction:guard"]
        game_state = type("FakeGameState", (), {})()
        game_state.players = {"TestPlayer": player}
        game_state.active_player = "TestPlayer"
        game_state.player = player

        condition = {"type": "has_tag", "value": "vampire"}
        assert trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=game_state
        ) is True

        condition = {"type": "has_tag", "value": "faction:guard"}
        assert trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=game_state
        ) is True

        condition = {"type": "has_tag", "value": "wolf"}
        assert trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=game_state
        ) is False

    def test_has_tag_condition_comma_string(self, graph, trigger_system, sample_item):
        """has_tag handles comma-separated string tags."""
        from player import Player
        player = Player("TestPlayer")
        player.tags = "vampire, noble"
        game_state = type("FakeGameState", (), {})()
        game_state.players = {"TestPlayer": player}
        game_state.active_player = "TestPlayer"
        game_state.player = player

        condition = {"type": "has_tag", "value": "noble"}
        assert trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=game_state
        ) is True

    def test_has_tag_condition_named_target(self, graph, trigger_system, sample_item):
        """has_tag resolves a named target from game_state.players."""
        from player import Player
        player = Player("TestPlayer")
        other = Player("Other")
        other.tags = ["hostile"]
        game_state = type("FakeGameState", (), {})()
        game_state.players = {"TestPlayer": player, "Other": other}
        game_state.active_player = "TestPlayer"
        game_state.player = player

        condition = {"type": "has_tag", "value": "hostile", "target": "Other"}
        assert trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=game_state
        ) is True
        # self resolves to the active player, not the tagged NPC
        condition = {"type": "has_tag", "value": "hostile", "target": "self"}
        assert trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=game_state
        ) is False

    def test_has_tag_target_uses_used_on_node(self, graph, trigger_system, sample_item):
        """has_tag with target='target' checks the used-on node (tree evaluator).

        Value may be an array — any-of semantics — and works on non-player
        nodes (ways/items), which is the keycard clearance use case.
        """
        from player import Player
        player = Player("TestPlayer")
        game_state = type("FakeGameState", (), {})()
        game_state.players = {"TestPlayer": player}
        game_state.active_player = "TestPlayer"
        game_state.player = player

        way = Node(id="way_vault", type="way", name="Vault Door",
                   properties={"tags": ["clearance-4", "reinforced"]})
        context = {"target_node": way, "item_node": sample_item}

        cond = {"type": "has_tag", "target": "target", "value": ["clearance-4", "clearance-3"]}
        assert trigger_system._evaluate_conditions(cond, context, game_state=game_state) is True
        cond = {"type": "has_tag", "target": "target", "value": ["clearance-3"]}
        assert trigger_system._evaluate_conditions(cond, context, game_state=game_state) is False
        cond = {"type": "has_tag", "target": "target", "value": "clearance-4"}
        assert trigger_system._evaluate_conditions(cond, context, game_state=game_state) is True
        # no target_node in context → fails safely
        assert trigger_system._evaluate_conditions(
            {"type": "has_tag", "target": "target", "value": "clearance-4"},
            {"item_node": sample_item}, game_state=game_state) is False

    def test_area_temp_comparator(self, graph, trigger_system, sample_item):
        """area_temp compares room temperature with a comparator operator."""
        area = Node(id="area_temp_test", type="area", name="Temp Room",
                    properties={"environment": {"temperature": 20}})
        graph.add_node(area)

        class FakeGameState:
            active_player = "TestPlayer"
            def _get_current_area_id(self):
                return "area_temp_test"

        gs = FakeGameState()
        assert trigger_system._evaluate_trigger_condition(
            {"type": "area_temp", "value": 25, "operator": "lt"}, sample_item, game_state=gs
        ) is True
        assert trigger_system._evaluate_trigger_condition(
            {"type": "area_temp", "value": 20, "operator": "eq"}, sample_item, game_state=gs
        ) is True
        assert trigger_system._evaluate_trigger_condition(
            {"type": "area_temp", "value": 20, "operator": "gt"}, sample_item, game_state=gs
        ) is False

    def test_vital_comparator(self, graph, trigger_system, sample_item):
        """vital compares a player's vital against a threshold."""
        from player import Player
        player = Player("TestPlayer")
        player.vitals["HP"] = 40
        game_state = type("FakeGameState", (), {})()
        game_state.players = {"TestPlayer": player}
        game_state.active_player = "TestPlayer"
        game_state.player = player

        assert trigger_system._evaluate_trigger_condition(
            {"type": "vital", "stat": "HP", "value": 50, "operator": "lt"}, sample_item, game_state=game_state
        ) is True
        assert trigger_system._evaluate_trigger_condition(
            {"type": "vital", "stat": "HP", "value": 40, "operator": "eq"}, sample_item, game_state=game_state
        ) is True
        assert trigger_system._evaluate_trigger_condition(
            {"type": "vital", "stat": "HP", "value": 40, "operator": "gt"}, sample_item, game_state=game_state
        ) is False

    def test_vital_comparator_named_target(self, graph, trigger_system, sample_item):
        """vital resolves a named target player."""
        from player import Player
        player = Player("TestPlayer")
        other = Player("Other")
        other.vitals["Energy"] = 10
        game_state = type("FakeGameState", (), {})()
        game_state.players = {"TestPlayer": player, "Other": other}
        game_state.active_player = "TestPlayer"
        game_state.player = player

        assert trigger_system._evaluate_trigger_condition(
            {"type": "vital", "stat": "Energy", "value": 20, "operator": "lt", "target": "Other"},
            sample_item, game_state=game_state,
        ) is True

    def test_vital_above_below_legacy(self, graph, trigger_system, sample_item):
        """vital_above / vital_below legacy aliases still work."""
        from player import Player
        player = Player("TestPlayer")
        player.vitals["HP"] = 40
        game_state = type("FakeGameState", (), {})()
        game_state.players = {"TestPlayer": player}
        game_state.active_player = "TestPlayer"
        game_state.player = player

        assert trigger_system._evaluate_trigger_condition(
            {"type": "vital_above", "stat": "HP", "value": 30}, sample_item, game_state=game_state
        ) is True
        assert trigger_system._evaluate_trigger_condition(
            {"type": "vital_below", "stat": "HP", "value": 30}, sample_item, game_state=game_state
        ) is False

    def test_is_equipped(self, graph, trigger_system, sample_item):
        """is_equipped checks a player's equipped edges."""
        from player import Player
        player = Player("TestPlayer")
        player_id = "player_TestPlayer"
        graph.add_node(Node(id=player_id, type="character", name="TestPlayer"))
        graph.add_node(sample_item)
        graph.add_edge(Edge(source=sample_item.id, target=player_id, type=EDGE_EQUIPPED))

        class FakeGameState:
            active_player = "TestPlayer"
            def __init__(self):
                self.player = player
                self.players = {"TestPlayer": player}
            def _player_node_id(self, name):
                return f"player_{name}"

        assert trigger_system._evaluate_trigger_condition(
            {"type": "is_equipped", "item": sample_item.name}, sample_item, game_state=FakeGameState()
        ) is True
        assert trigger_system._evaluate_trigger_condition(
            {"type": "is_equipped", "item": "nonexistent"}, sample_item, game_state=FakeGameState()
        ) is False

    def test_time_of_day(self, graph, trigger_system, sample_item):
        """time_of_day matches the current game clock (HH:MM)."""
        class FakeGameState:
            def get_current_time(self):
                return "14:30:00"

        assert trigger_system._evaluate_trigger_condition(
            {"type": "time_of_day", "value": "14:30"}, sample_item, game_state=FakeGameState()
        ) is True
        assert trigger_system._evaluate_trigger_condition(
            {"type": "time_of_day", "value": "09:00"}, sample_item, game_state=FakeGameState()
        ) is False

    def test_weather_condition(self, graph, trigger_system, sample_item):
        """weather matches the area environment's weather key."""
        area = Node(id="area_weather", type="area", name="Weather Room",
                    properties={"environment": {"weather": "rain", "temperature": 15}})
        graph.add_node(area)

        class FakeGameState:
            active_player = "TestPlayer"
            def _get_current_area_id(self):
                return "area_weather"

        assert trigger_system._evaluate_trigger_condition(
            {"type": "weather", "value": "rain"}, sample_item, game_state=FakeGameState()
        ) is True
        assert trigger_system._evaluate_trigger_condition(
            {"type": "weather", "value": "clear"}, sample_item, game_state=FakeGameState()
        ) is False


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ TestSaveThrowCondition â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestSaveThrowCondition:
    """save_throw condition (task-159): target rolls a stat/skill vs DC."""

    def _fake_gs(self, player):
        from player import Player

        class FakeGameState:
            def __init__(self, p):
                self.player = p
                self.players = {p.name: p}

        return FakeGameState(player)

    def test_save_throw_active_player_passes(self, graph, trigger_system, sample_item):
        """High DEX vs easy DC â†’ save succeeds â†’ condition passes."""
        from player import Player
        player = Player("Hero")
        player.stats["DEX"] = 20  # mod +5
        condition = {"type": "save_throw", "stat": "DEX", "dc": 5}
        result = trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=self._fake_gs(player)
        )
        assert result is True
        assert trigger_system._last_save_msg
        assert "[Save] DEX vs DC 5" in trigger_system._last_save_msg

    def test_save_throw_fails_at_high_dc(self, graph, trigger_system, sample_item):
        """Low DEX vs impossible DC â†’ save fails â†’ condition fails."""
        from player import Player
        player = Player("Hero")
        player.stats["DEX"] = 3  # mod -3, max total 17
        condition = {"type": "save_throw", "stat": "DEX", "dc": 30}
        result = trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=self._fake_gs(player)
        )
        assert result is False
        assert trigger_system._last_save_msg

    def test_save_throw_skill_check(self, graph, trigger_system, sample_item):
        """save_throw can roll a skill instead of a stat."""
        from player import Player
        player = Player("Hero")
        player.skills["Athletics"] = 8
        condition = {"type": "save_throw", "skill": "Athletics", "dc": 5}
        result = trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=self._fake_gs(player)
        )
        assert result is True
        assert "[Save] Athletics vs DC 5" in trigger_system._last_save_msg

    def test_save_throw_named_target(self, graph, trigger_system, sample_item):
        """target=<name> resolves an NPC from game_state.players."""
        from player import Player
        hero = Player("Hero")
        hero.stats["STR"] = 3
        guard = Player("Guard")
        guard.stats["STR"] = 20  # mod +5, DC 5 always passes
        gs = self._fake_gs(hero)
        gs.players["Guard"] = guard
        condition = {"type": "save_throw", "stat": "STR", "dc": 5, "target": "Guard"}
        result = trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=gs
        )
        assert result is True

    def test_save_throw_no_resolvable_target_fails(self, graph, trigger_system, sample_item):
        """No active player / unknown target â†’ condition fails safely."""
        condition = {"type": "save_throw", "stat": "DEX", "dc": 5}
        result = trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=None
        )
        assert result is False

    def test_save_throw_tree_eval(self, trigger_system):
        """save_throw works inside the AND/OR condition tree (NPC behaviors)."""
        from player import Player
        player = Player("Hero")
        player.stats["DEX"] = 20
        gs = self._fake_gs(player)
        tree = {
            "operator": "and",
            "conditions": [{"type": "save_throw", "stat": "DEX", "dc": 5}],
        }
        result = trigger_system._evaluate_conditions(tree, {"game_state": gs})
        assert result is True

    def test_save_throw_defaults_stat_and_dc(self, graph, trigger_system, sample_item, monkeypatch):
        """Missing stat/dc default to DEX/12 (exact-boundary via patched roll)."""
        from player import Player
        player = Player("Hero")  # DEX 10 â†’ mod 0
        gs = self._fake_gs(player)
        condition = {"type": "save_throw"}

        monkeypatch.setattr(trigger_system.skills, "roll_dice", lambda *a, **k: 11)  # total 11 < 12
        assert trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=gs
        ) is False
        assert "[Save] DEX vs DC 12" in trigger_system._last_save_msg

        monkeypatch.setattr(trigger_system.skills, "roll_dice", lambda *a, **k: 12)  # total 12 == 12
        assert trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=gs
        ) is True

    def test_save_throw_target_explicit_self(self, graph, trigger_system, sample_item):
        """target='self' resolves to the active player like the default."""
        from player import Player
        player = Player("Hero")
        player.stats["DEX"] = 20
        condition = {"type": "save_throw", "stat": "DEX", "dc": 5, "target": "self"}
        result = trigger_system._evaluate_trigger_condition(
            condition, sample_item, game_state=self._fake_gs(player)
        )
        assert result is True

    def test_save_throw_not_operator_tree(self, trigger_system):
        """NOT(save fails) is True â€” tree operator support."""
        from player import Player
        player = Player("Hero")
        player.stats["DEX"] = 3  # mod -3 â†’ never passes DC 30
        gs = self._fake_gs(player)
        tree = {
            "operator": "not",
            "conditions": [{"type": "save_throw", "stat": "DEX", "dc": 30}],
        }
        result = trigger_system._evaluate_conditions(tree, {"game_state": gs})
        assert result is True


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ TestSaveThrowIntegration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestSaveThrowIntegration:
    """End-to-end: save_throw gating + damage save through _execute_triggers."""

    @staticmethod
    def _fake_gs(player, skills):
        gs = type("FakeGS", (), {})()
        gs.player = player
        gs.players = {player.name: player}
        gs.active_player = player.name
        gs.time_ticks = 0
        gs.turn_number = 1
        gs.current_area = None
        gs.get_current_time = lambda: "12:00"
        gs.get_players_in_area = lambda area_name=None, exclude_self=True: []
        gs.saving_throw = lambda p, s, dc=12: skills.saving_throw(p, s, dc)
        return gs

    def _wire_trap(self, graph, item, conditions, effects):
        props = {
            "trigger_type": "on_take",
            "conditions": conditions,
            "effects": effects,
        }
        tnode = Node(id=f"trigger_trap_{item.id}", type="logic_trigger", name="trap", properties=props)
        graph.add_node(tnode)
        graph.add_edge(Edge(source=item.id, target=tnode.id, type=EDGE_TRIGGERS, properties=props))
        return props

    def test_save_success_fires_effect(self, graph, skills, logging_events, sample_item):
        """Save succeeds â†’ condition passes â†’ the dodge effect fires, HP intact."""
        from player import Player
        hero = Player("Hero")
        hero.vitals["HP"] = 50
        hero.stats["DEX"] = 20  # mod +5 â†’ always passes DC 5
        gs = self._fake_gs(hero, skills)
        trigger_system = TriggerSystem(graph, skills, logging_events)
        self._wire_trap(
            graph, sample_item,
            [{"type": "save_throw", "stat": "DEX", "dc": 5}],
            [{"type": "message", "params": {"message": "You dive out of the way!"}}],
        )
        outputs = trigger_system._execute_triggers(sample_item, "on_take", game_state=gs)
        assert hero.vitals["HP"] == 50
        assert any("[Save] DEX vs DC 5" in o for o in outputs)
        assert any("dive out of the way" in o for o in outputs)

    def test_save_failure_skips_effect_and_shows_fail_message(self, graph, skills, logging_events, sample_item):
        """Save fails â†’ effects skipped, the effect's fail_message is emitted."""
        from player import Player
        hero = Player("Hero")
        hero.vitals["HP"] = 50
        hero.stats["DEX"] = 3  # mod -3 â†’ never passes DC 30
        gs = self._fake_gs(hero, skills)
        trigger_system = TriggerSystem(graph, skills, logging_events)
        self._wire_trap(
            graph, sample_item,
            [{"type": "save_throw", "stat": "DEX", "dc": 30}],
            [{"type": "message",
              "params": {"message": "You dodge cleanly!",
                         "fail_message": "The dart sinks into your shoulder."}}],
        )
        outputs = trigger_system._execute_triggers(sample_item, "on_take", game_state=gs)
        assert hero.vitals["HP"] == 50
        assert any("[Save] DEX vs DC 30" in o for o in outputs)
        assert not any("dodge cleanly" in o for o in outputs)
        assert any("sinks into your shoulder" in o for o in outputs)

    def test_damage_save_param_through_full_pipeline(self, graph, skills, logging_events, sample_item):
        """A damage effect's save param halves damage inside _execute_triggers."""
        from player import Player
        hero = Player("Hero")
        hero.vitals["HP"] = 50
        hero.stats["DEX"] = 20  # mod +5 â†’ always passes DC 5
        gs = self._fake_gs(hero, skills)
        trigger_system = TriggerSystem(graph, skills, logging_events)
        self._wire_trap(
            graph, sample_item,
            [],
            [{"type": "damage",
              "params": {"amount": 10, "target": "self",
                         "save": {"stat": "DEX", "dc": 5}}}],
        )
        outputs = trigger_system._execute_triggers(sample_item, "on_take", game_state=gs)
        assert hero.vitals["HP"] == 45  # 10 // 2 = 5
        assert any("[Save] DEX vs DC 5" in o for o in outputs)
        assert any("takes 5 damage" in o for o in outputs)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ TestEffects â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestAvailableActions:
    """_get_available_actions must tolerate list-valued trigger_type (multi-select editor)."""

    def _wire_trigger(self, graph, item, trigger_type):
        """Attach a logic_trigger node + triggers edge with the given trigger_type value."""
        props = {
            "trigger_type": trigger_type,
            "conditions": [],
            "effects": [{"type": "message", "params": {"message": "hi"}}],
            "success_message": "",
            "fail_message": "",
        }
        tnode = Node(id=f"trigger_{item.id}", type="logic_trigger", name="t", properties=props)
        graph.add_node(tnode)
        graph.add_edge(Edge(source=item.id, target=tnode.id, type=EDGE_TRIGGERS, properties=props))

    def test_list_trigger_type_does_not_crash(self, graph, trigger_system, sample_item):
        """A trigger_type stored as a list must not crash _get_available_actions."""
        self._wire_trigger(graph, sample_item, ["on_examine"])
        available = trigger_system._get_available_actions(sample_item)
        assert any(a["action"] == "examine" for a in available)

    def test_list_trigger_type_use(self, graph, trigger_system, sample_item):
        """on_use inside a list-valued trigger_type enables the Use action."""
        sample_item.properties["actions"] = ["examine"]
        self._wire_trigger(graph, sample_item, ["on_use"])
        available = trigger_system._get_available_actions(sample_item)
        assert any(a["action"] == "use" for a in available)

    def test_string_trigger_type_still_works(self, graph, trigger_system, sample_item):
        """Legacy string-valued trigger_type keeps working."""
        sample_item.properties["actions"] = ["examine"]
        self._wire_trigger(graph, sample_item, "on_toggle_on")
        available = trigger_system._get_available_actions(sample_item)
        assert any(a["action"] == "toggle" for a in available)

    def test_on_use_on_label_with_list(self, graph, trigger_system, sample_item):
        """'Use on <target>' label resolves when on_use_on is in a list."""
        sample_item.properties["actions"] = ["examine"]
        self._wire_trigger(graph, sample_item, ["on_use_on"])
        graph.get_node(f"trigger_{sample_item.id}").properties["target_name"] = "door_south"
        available = trigger_system._get_available_actions(sample_item)
        use_action = next(a for a in available if a["action"] == "use")
        assert use_action["label"] == "Use on door_south"


class TestEffects:
    """Effect execution through the Effects class."""

    def test_message_effect(self, graph, logging_events):
        """message effect returns the configured message."""
        effects = Effects(graph, logging_events)
        result = effects.execute("message", {"message": "Hello world!"}, {})
        assert result == ["Hello world!"]

    def test_message_effect_empty_message_returns_nothing(self, graph, logging_events):
        """message effect with no message produces no output (no "Something happens.")."""
        effects = Effects(graph, logging_events)
        result = effects.execute("message", {}, {})
        assert result == []

    @staticmethod
    def _make_game_state(player, extra_players=None):
        """Build a minimal duck-typed game_state for testing effect handlers."""
        game_state = type("FakeGameState", (), {})()
        game_state.player = player
        game_state.players = extra_players or {player.name: player}
        game_state.get_players_in_area = lambda area_name=None, exclude_self=True: []
        return game_state

    def test_damage_effect_self(self, graph, logging_events):
        """damage effect reduces the player's HP."""
        effects = Effects(graph, logging_events)
        from player import Player
        test_player = Player("TestPlayer")
        test_player.vitals["HP"] = 100
        game_state = self._make_game_state(test_player)

        result = effects.execute("damage", {"amount": 15}, {},
                                 game_state=game_state)
        assert test_player.vitals["HP"] == 85
        assert any("15 damage" in msg for msg in result)

    def test_heal_effect(self, graph, logging_events):
        """heal effect restores HP."""
        effects = Effects(graph, logging_events)
        from player import Player
        test_player = Player("TestPlayer")
        test_player.vitals["HP"] = 50
        game_state = self._make_game_state(test_player)

        result = effects.execute("heal", {"amount": 30, "stat": "HP"}, {},
                                 game_state=game_state)
        assert test_player.vitals["HP"] == 80
        assert any("restore 30 HP" in msg for msg in result)

    def test_damage_does_not_below_zero(self, graph, logging_events):
        """damage effect clamps HP to 0."""
        effects = Effects(graph, logging_events)
        from player import Player
        test_player = Player("TestPlayer")
        test_player.vitals["HP"] = 10
        game_state = self._make_game_state(test_player)

        effects.execute("damage", {"amount": 100}, {},
                        game_state=game_state)
        assert test_player.vitals["HP"] == 0

    def test_heal_does_not_exceed_100(self, graph, logging_events):
        """heal effect clamps HP to 100."""
        effects = Effects(graph, logging_events)
        from player import Player
        test_player = Player("TestPlayer")
        test_player.vitals["HP"] = 90
        game_state = self._make_game_state(test_player)

        effects.execute("heal", {"amount": 50, "stat": "HP"}, {},
                        game_state=game_state)
        assert test_player.vitals["HP"] == 100

    def test_adjust_vital(self, graph, logging_events):
        """adjust_vital modifies a vital stat."""
        effects = Effects(graph, logging_events)
        from player import Player
        test_player = Player("TestPlayer")
        test_player.vitals["Energy"] = 50
        game_state = self._make_game_state(test_player)

        result = effects.execute("adjust_vital",
                                 {"stat": "Energy", "amount": 20}, {},
                                 game_state=game_state)
        assert test_player.vitals["Energy"] == 70

    def test_adjust_vital_clamped(self, graph, logging_events):
        """adjust_vital clamps between 0 and 100."""
        effects = Effects(graph, logging_events)
        from player import Player
        test_player = Player("TestPlayer")
        test_player.vitals["Energy"] = 90
        game_state = self._make_game_state(test_player)

        effects.execute("adjust_vital",
                        {"stat": "Energy", "amount": 50}, {},
                        game_state=game_state)
        assert test_player.vitals["Energy"] == 100

    def test_adjust_vital_negative(self, graph, logging_events):
        """adjust_vital can reduce a vital stat."""
        effects = Effects(graph, logging_events)
        from player import Player
        test_player = Player("TestPlayer")
        test_player.vitals["Sanity"] = 80
        game_state = self._make_game_state(test_player)

        effects.execute("adjust_vital",
                        {"stat": "Sanity", "amount": -25}, {},
                        game_state=game_state)
        assert test_player.vitals["Sanity"] == 55

    def test_spawn_item(self, graph, logging_events):
        """spawn_item creates an item node in the current area."""
        effects = Effects(graph, logging_events)

        class FakeGameState:
            def get_current_area_id(self):
                return "area_Test_Room"

        from graph import Node
        area_node = Node(id="area_Test_Room", type="area", name="Test Area")
        graph.add_node(area_node)

        result = effects.execute("spawn_item",
                                 {"item_id": "item_new_sword",
                                  "name": "New Sword",
                                  "description": "A shiny new sword."}, {},
                                 game_state=FakeGameState())
        assert "New Sword" in result[0]
        spawned = graph.get_node("item_new_sword")
        assert spawned is not None
        assert spawned.name == "New Sword"

    def test_spawn_item_into_container(self, graph, logging_events):
        """spawn_item with into=container places a fresh item copy inside."""
        from graph import Node, EDGE_IN

        effects = Effects(graph, logging_events)
        container = Node(
            id="item_crate",
            type="item",
            name="crate",
            properties={"tags": ["container"], "max_weight_capacity": 2},
        )
        graph.add_node(container)

        result = effects.execute(
            "spawn_item",
            {"item_id": "item_key", "into": "container"},
            {},
            item_node=container,
            game_state=type("GS", (), {"get_current_area_id": lambda self: None})(),
        )
        assert "key" in result[0].lower()
        edges = graph.get_edges_for_target("item_crate", EDGE_IN)
        assert len(edges) == 1
        assert edges[0].source.startswith("item_key")

    def test_spawn_item_into_container_rejects_over_capacity(self, graph, logging_events):
        from graph import Node, EDGE_IN

        effects = Effects(graph, logging_events)
        container = Node(
            id="item_crate",
            type="item",
            name="crate",
            properties={"tags": ["container"], "max_weight_capacity": 2},
        )
        graph.add_node(container)

        result = effects.execute(
            "spawn_item",
            {"item_id": "item_anvil", "weight": 5, "into": "container"},
            {},
            item_node=container,
            game_state=type("GS", (), {"get_current_area_id": lambda self: None})(),
        )
        assert "can't hold" in result[0].lower()
        assert not graph.get_edges_for_target("item_crate", EDGE_IN)

    def test_give_item_rejects_when_over_capacity(self, graph, logging_events):
        """give_item respects player carry capacity (task-103 Phase 3)."""
        from graph import Node, Edge, EDGE_CARRYING
        from player import Player

        effects = Effects(graph, logging_events)
        graph.add_node(Node(id="player_Hero", type="player", name="Hero", properties={}))
        for item_id, weight in (("item_a", 60), ("item_b", 35)):
            graph.add_node(Node(id=item_id, type="item", name=item_id, properties={"weight": weight}))
            graph.add_edge(Edge(source=item_id, target="player_Hero", type=EDGE_CARRYING))
        graph.add_node(Node(id="item_heavy", type="item", name="heavy", properties={"weight": 10}))

        gs = type("GS", (), {"players": {}, "active_player": "Hero"})()

        result = effects.execute(
            "give_item",
            {"item_id": "item_heavy", "target": "self", "weight": 10},
            {},
            game_state=gs,
        )
        assert any("can't carry" in msg.lower() for msg in result)
        assert not any(
            e.source == "item_heavy"
            for e in graph.get_edges_for_target("player_Hero", EDGE_CARRYING)
        )

    def test_spawn_item_copies_heat_props_from_library(self, graph, logging_events):
        """spawn_item hydrates heat/light/contents props from the library file."""
        import json as _json
        import os as _os
        effects = Effects(graph, logging_events)

        class FakeGameState:
            def get_current_area_id(self):
                return "area_Test_Room"

        area_node = Node(id="area_Test_Room", type="area", name="Test Area")
        graph.add_node(area_node)

        result = effects.execute("spawn_item",
                                 {"item_id": "everflame_ember"}, {},
                                 game_state=FakeGameState())
        # Expectations come FROM the library entry, so retuning the data
        # doesn't stale the test — the contract is "spawn copies the library".
        lib_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                 '..', 'data', 'library', 'items', 'everflame_ember.json')
        with open(lib_path, encoding='utf-8') as f:
            lib = _json.load(f)
        assert lib["name"] in result[0]
        ember = graph.get_node("everflame_ember")
        assert ember is not None
        assert ember.properties["uses"] == lib.get("uses")
        assert ember.properties["current_state"] == lib.get("current_state")
        assert ember.properties["light_level"] == lib.get("light_level")
        assert ember.properties.get("target_temperature") == lib.get("target_temperature")
        assert ember.properties.get("heating_rate") == lib.get("heating_rate")
        assert ember.properties["contents"] == lib.get("contents", [])

    def test_spawn_item_materializes_triggers(self, graph, trigger_system, logging_events):
        """spawned library items get trigger nodes/edges so on_tick burns them down."""
        effects = Effects(graph, logging_events)

        game_state = type("FakeGameState", (), {})()
        game_state.get_current_area_id = lambda: "area_Test_Room"
        game_state.get_current_time = lambda: "10:00"
        game_state.time_ticks = 1
        game_state.turn_number = 1
        game_state.active_player = "TestPlayer"
        game_state.player = None
        game_state.current_area = None

        area_node = Node(id="area_Test_Room", type="area", name="Test Area")
        graph.add_node(area_node)

        effects.execute("spawn_item", {"item_id": "everflame_ember"}, {},
                        game_state=game_state)
        ember = graph.get_node("everflame_ember")

        trigger_edges = graph.get_edges_for_source("everflame_ember", EDGE_TRIGGERS)
        assert len(trigger_edges) == 2
        trigger_types = {e.properties["trigger_type"] for e in trigger_edges}
        assert trigger_types == {"on_tick", "on_depleted"}
        for edge in trigger_edges:
            trigger_node = graph.get_node(edge.target)
            assert trigger_node is not None
            assert trigger_node.type == "logic_trigger"
            assert "effects" in trigger_node.properties

        # Seed a known uses count — the library entry is user-tuned data and
        # may legitimately hold any value; this test verifies the burn-down.
        ember.properties["uses"] = 3
        trigger_system._execute_triggers(ember, "on_tick", game_state=game_state)
        assert ember.properties["uses"] == 2

    def test_spawn_character_from_library(self, graph, logging_events):
        """spawn_character hydrates a Player from the library and places them."""
        effects = Effects(graph, logging_events)

        class FakeGameState:
            def __init__(self, graph):
                self.graph = graph
                self.players = {}
                self.active_player = "TestPlayer"

            def get_current_area_id(self):
                return "area_Test_Room"

            def get_player(self, name):
                return self.players.get(name)

            def add_player(self, player_obj):
                self.players[player_obj.name] = player_obj
                self.active_player = player_obj.name
                from graph import Node
                player_node_id = f"player_{player_obj.name}".replace(' ', '_')
                if not self.graph.get_node(player_node_id):
                    self.graph.add_node(Node(id=player_node_id, type="character", name=player_obj.name))

            def set_player_area(self, name, area_name):
                from graph import Edge, EDGE_IN
                player_node_id = f"player_{name}".replace(' ', '_')
                area_id = f"area_{area_name.lower()}".replace(' ', '_')
                for edge in list(self.graph.get_edges_for_source(player_node_id, EDGE_IN)):
                    self.graph.remove_edge(edge.source, edge.target, edge.type)
                self.graph.add_edge(Edge(source=player_node_id, target=area_id, type=EDGE_IN))

        game_state = FakeGameState(graph)
        area_node = Node(id="area_Test_Room", type="area", name="Test Area")
        graph.add_node(area_node)

        result = effects.execute("spawn_character",
                                 {"character_id": "jake"}, {},
                                 game_state=game_state)
        # The library entry is the source of truth for display name + node id
        # casing (it was lowercased at some point; derive, don't hardcode).
        import json as _json
        import os as _os
        lib_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                 '..', 'data', 'library', 'characters', 'jake.json')
        with open(lib_path, encoding='utf-8') as f:
            lib_name = _json.load(f)["name"]
        assert lib_name in result[0]
        player_node_id = f"player_{lib_name}".replace(' ', '_')
        player_node = graph.get_node(player_node_id)
        assert player_node is not None
        assert player_node.type == "character"
        area_edge = next(
            (e for e in graph.edges
             if e.source == player_node_id and e.type == "in"),
            None,
        )
        assert area_edge is not None
        assert area_edge.target == "area_test_area"

    def test_spawn_character_unknown_id(self, graph, logging_events):
        """spawn_character with unknown id returns empty (no-op)."""
        effects = Effects(graph, logging_events)
        result = effects.execute("spawn_character",
                                 {"character_id": "nonexistent_hero"}, {},
                                 game_state=type("GS", (), {"get_current_area_id": lambda: None})())
        assert result == []

    def test_destroy_self(self, graph, logging_events):
        """destroy_self removes the triggering item from the graph."""
        effects = Effects(graph, logging_events)
        item = Node(id="item_disposable", type="item", name="Disposable",
                    properties={})
        graph.add_node(item)

        effects.execute("destroy_self", {"message": "It crumbles!"}, {},
                        item_node=item)
        assert graph.get_node("item_disposable") is None

    def test_set_state(self, graph, logging_events):
        """set_state changes the current_state property on a node."""
        effects = Effects(graph, logging_events)
        chest = Node(id="item_chest", type="item", name="Chest",
                     properties={"current_state": "closed"})
        graph.add_node(chest)

        result = effects.execute("set_state",
                                 {"node_id": "item_chest", "state": "open"}, {})
        assert chest.properties["current_state"] == "open"
        assert "now open" in result[0]

    def test_set_state_self_resolves_to_host_node(self, graph, logging_events):
        """set_state with node_id 'self' targets the triggering node (door-lock pattern).

        The trigger editor authors node_id 'self' for the host node; the
        handler must resolve it to the way/item that fired the trigger.
        """
        effects = Effects(graph, logging_events)
        door = Node(id="way_test_door", type="way", name="Test Door",
                    properties={"current_state": "closed"})
        graph.add_node(door)

        result = effects.execute(
            "set_state",
            {"node_id": "self", "state": "locked",
             "message": "the door locks behind you"},
            {}, item_node=door)
        assert door.properties["current_state"] == "locked"
        assert "locks behind you" in result[0]

    def test_set_hidden_self_resolves_to_host_node(self, graph, logging_events):
        """set_hidden with node_id 'self' targets the triggering node."""
        effects = Effects(graph, logging_events)
        item = Node(id="item_trapdoor", type="item", name="Trapdoor",
                    properties={"current_state": "normal"})
        graph.add_node(item)

        effects.execute("set_hidden", {"node_id": "self", "hidden": True}, {},
                        item_node=item)
        assert item.properties["current_state"] == "hidden"

    def test_unlock_way(self, graph, logging_events):
        """unlock_way unlocks a way node to closed state."""
        effects = Effects(graph, logging_events)
        door = Node(id="way_test", type="way", name="Test Way",
                    properties={"current_state": "locked"})
        graph.add_node(door)

        effects.execute("unlock_way",
                        {"way_id": "way_test",
                         "message": "A lock clicks open!"}, {})
        assert door.properties["current_state"] == "closed"

    def test_unlock_way_target_fallback(self, graph, logging_events):
        """unlock_way with way_id 'target'/blank unlocks the on_use_on target."""
        effects = Effects(graph, logging_events)
        door = Node(id="way_vault", type="way", name="Vault Door",
                    properties={"current_state": "locked"})
        graph.add_node(door)

        result = effects.execute(
            "unlock_way",
            {"way_id": "target", "message": "The vault unlocks!"},
            {}, item_node=None, target_item_node=door)
        assert door.properties["current_state"] == "closed"
        assert "unlocks" in result[0]

        door2 = Node(id="way_office", type="way", name="Office Door",
                     properties={"current_state": "locked"})
        graph.add_node(door2)
        effects.execute("unlock_way", {}, {}, target_item_node=door2)
        assert door2.properties["current_state"] == "closed"

    def test_unlock_way_target_fallback_ignores_non_way(self, graph, logging_events):
        """unlock_way 'target' against a non-way target is a no-op."""
        effects = Effects(graph, logging_events)
        chest = Node(id="item_chest", type="item", name="Chest",
                     properties={"current_state": "closed"})
        graph.add_node(chest)

        result = effects.execute("unlock_way", {"way_id": "target"}, {},
                                 target_item_node=chest)
        assert result == []
        assert chest.properties["current_state"] == "closed"

    def test_adjust_uses(self, graph, logging_events):
        """adjust_uses changes the uses count on a node."""
        effects = Effects(graph, logging_events)
        item = Node(id="item_battery", type="item", name="Battery",
                    properties={"uses": 5})
        graph.add_node(item)

        effects.execute("adjust_uses",
                        {"node_id": "item_battery", "delta": -1}, {})
        assert item.properties["uses"] == 4

    def test_unknown_effect_type(self, graph, logging_events):
        """Unknown effect type returns an error message."""
        effects = Effects(graph, logging_events)
        result = effects.execute("teleport_to_moon", {}, {})
        assert len(result) == 1
        assert "Unknown effect" in result[0]

    def test_rename_defaults_to_triggering_item(self, graph, logging_events):
        """rename without node_id targets the triggering item node."""
        effects = Effects(graph, logging_events)
        photo = Node(id="item_photo", type="item", name="photo",
                     properties={})
        graph.add_node(photo)

        result = effects.execute("rename", {"name": "photo of james"}, {},
                                 item_node=photo)
        assert photo.name == "photo of james"
        assert photo.properties["name"] == "photo of james"
        assert "photo of james" in result[0]

    def test_rename_with_node_id(self, graph, logging_events):
        """rename with an explicit node_id targets that node, not the trigger."""
        effects = Effects(graph, logging_events)
        trigger = Node(id="item_locket", type="item", name="Locket",
                       properties={})
        other = Node(id="item_painting", type="item", name="painting",
                     properties={})
        graph.add_node(trigger)
        graph.add_node(other)

        effects.execute("rename", {"node_id": "item_painting",
                                   "name": "painting of the valerius estate"}, {},
                        item_node=trigger)
        assert trigger.name == "Locket"
        assert other.name == "painting of the valerius estate"

    def test_rename_self_targets_triggering_item(self, graph, logging_events):
        """rename with node_id='self' targets the triggering item."""
        effects = Effects(graph, logging_events)
        vial = Node(id="item_vial", type="item", name="vial",
                    properties={})
        graph.add_node(vial)

        effects.execute("rename", {"node_id": "self", "name": "Vial of Antidote"}, {},
                        item_node=vial)
        assert vial.name == "Vial of Antidote"

    def test_rename_missing_name_returns_empty(self, graph, logging_events):
        """rename with no name is a no-op (no output, no change)."""
        effects = Effects(graph, logging_events)
        item = Node(id="item_test", type="item", name="Test",
                    properties={})
        graph.add_node(item)

        result = effects.execute("rename", {}, {}, item_node=item)
        assert result == []
        assert item.name == "Test"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ TestTemplateRendering â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestTemplateRendering:
    """Template variable substitution in trigger messages."""

    def test_render_template_player_name(self, trigger_system):
        """{player_name} is replaced with the player's name."""
        result = trigger_system._render_template(
            "Hello {player_name}!",
            {"player_name": "Traveler"}
        )
        assert result == "Hello Traveler!"

    def test_render_template_area_name(self, trigger_system):
        """{area_name} is replaced with the area name."""
        result = trigger_system._render_template(
            "You are in {area_name}.",
            {"area_name": "Dungeon"}
        )
        assert result == "You are in Dungeon."

    def test_render_template_item_name(self, trigger_system):
        """{item_name} is replaced with the item name."""
        result = trigger_system._render_template(
            "The {item_name} glows.",
            {"item_name": "Magic Sword"}
        )
        assert result == "The Magic Sword glows."

    def test_render_template_unknown_variable(self, trigger_system):
        """Unknown variables are left as-is."""
        result = trigger_system._render_template(
            "The {unknown_var} is here.",
            {"player_name": "Traveler"}
        )
        assert result == "The {unknown_var} is here."

    def test_render_template_multiple_variables(self, trigger_system):
        """Multiple variables are all replaced."""
        result = trigger_system._render_template(
            "{player_name} uses the {item_name} in {area_name}.",
            {"player_name": "Hero", "item_name": "Key", "area_name": "Hall"}
        )
        assert result == "Hero uses the Key in Hall."

    def test_render_template_no_variables(self, trigger_system):
        """Plain text without variables is returned unchanged."""
        result = trigger_system._render_template(
            "Nothing happens.",
            {"player_name": "Traveler"}
        )
        assert result == "Nothing happens."

    def test_render_template_item_properties(self, trigger_system):
        """{prop:key} resolves to item property values."""
        result = trigger_system._render_template(
            "The item has {prop:current_state} state.",
            {"item_properties": {"current_state": "open"}}
        )
        assert result == "The item has open state."

    def test_render_template_item_params(self, trigger_system):
        """{param:key} resolves to item parameter values."""
        result = trigger_system._render_template(
            "Parameter value: {param:dose}",
            {"item_params": {"dose": "5mg"}}
        )
        assert result == "Parameter value: 5mg"

    def test_render_template_strips_unknown_prop(self, trigger_system):
        """{prop:unknown} is left as-is when the key doesn't exist."""
        result = trigger_system._render_template(
            "Value: {prop:missing}",
            {"item_properties": {"exists": "yes"}}
        )
        assert result == "Value: {prop:missing}"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ TestIntegration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestTriggerIntegration:
    """End-to-end trigger execution pipeline."""

    def test_message_trigger_on_take(self, graph, logging_events, skills, sample_item):
        """An on_take trigger with message effect returns the message."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        # Create trigger node
        trigger_node = Node(
            id="trigger_test_message",
            type="logic_trigger",
            name="on_take â†’ message",
            properties={
                "trigger_type": "on_take",
                "effect_type": "message",
                "effect_params": {"message": "The item vibrates as you pick it up!"}
            }
        )
        graph.add_node(trigger_node)

        # Link item to trigger
        graph.add_edge(Edge(
            source=sample_item.id,
            target=trigger_node.id,
            type=EDGE_TRIGGERS,
            properties={"trigger_type": "on_take",
                        "effects": [{"type": "message", "params": {"message": "The item vibrates as you pick it up!"}}]}
        ))

        outputs = trigger_system._execute_triggers(
            sample_item, "on_take",
            game_state=None
        )
        assert len(outputs) > 0
        assert "vibrates" in outputs[0]

    def test_on_enter_set_state_self_locks_door(self, graph, skills, logging_events):
        """Door-lock pattern: on_enter on a way + set_state node_id 'self' locks it.

        Mirrors the UI-authored trigger (node_id 'self' = the host door) and
        the movement call site firing on_enter on the way node.
        """
        trigger_system = TriggerSystem(graph, skills, logging_events)

        door = Node(id="way_test_door", type="way", name="Test Door",
                    properties={"current_state": "open"})
        graph.add_node(door)

        trigger_node = Node(
            id="trigger_test_door_lock",
            type="logic_trigger",
            name="on_enter â†’ set_state",
            properties={
                "trigger_type": "on_enter",
                "effects": [
                    {"type": "set_state",
                     "params": {"node_id": "self", "state": "locked",
                                "message": "the door locks behind you"}}
                ],
            },
        )
        graph.add_node(trigger_node)
        graph.add_edge(Edge(
            source=door.id,
            target=trigger_node.id,
            type=EDGE_TRIGGERS,
            properties={"trigger_type": "on_enter",
                        "effects": trigger_node.properties["effects"]},
        ))

        outputs = trigger_system._execute_triggers(door, "on_enter", game_state=None)
        assert any("locks behind you" in o for o in outputs)
        assert door.properties["current_state"] == "locked"

    def test_keycard_on_use_on_clearance_unlocks_way(self, graph, skills, logging_events):
        """Keycard pattern: on_use_on + has_tag (target) + unlock_way target.

        Using the card on a door tagged clearance-4 unlocks THAT door; the
        way_id 'target' resolves to the used-on way via exit-direction matching.
        """
        trigger_system = TriggerSystem(graph, skills, logging_events)

        area = Node(id="area_secure", type="area", name="Secure Wing")
        graph.add_node(area)
        door = Node(id="way_vault", type="way", name="Vault Door",
                    properties={"current_state": "locked", "tags": ["clearance-4"]})
        graph.add_node(door)
        graph.add_edge(Edge(source=area.id, target=door.id, type=EDGE_CONNECTION,
                            properties={"direction": "north"}))
        card = Node(id="item_keycard", type="item", name="Keycard",
                    properties={"actions": ["use"], "tags": ["clearance-4"]})
        graph.add_node(card)

        trigger_node = Node(
            id="trigger_keycard_clearance",
            type="logic_trigger",
            name="on_use_on â†’ unlock_way",
            properties={
                "trigger_type": "on_use_on",
                "conditions": [{"type": "has_tag", "target": "target", "value": ["clearance-4"]}],
                "effects": [
                    {"type": "message",
                     "params": {"success_message": "Access granted.",
                                "fail_message": "Access denied â€” insufficient clearance."}},
                    {"type": "unlock_way",
                     "params": {"way_id": "target"}},
                ],
            },
        )
        graph.add_node(trigger_node)
        graph.add_edge(Edge(source=card.id, target=trigger_node.id, type=EDGE_TRIGGERS,
                            properties={"trigger_type": "on_use_on",
                                        "conditions": [{"type": "has_tag", "target": "target", "value": ["clearance-4"]}],
                                        "effects": trigger_node.properties["effects"]}))

        gs = type("FakeGS", (), {})()
        gs.get_current_time = lambda: "10:00"
        gs.time_ticks = 1
        gs.turn_number = 1
        gs.active_player = "TestPlayer"
        gs.player = None
        gs.current_area = None
        gs.get_current_area_id = lambda: "area_secure"
        gs._match_exit_direction = lambda area_id, name: "north"

        outputs = trigger_system._execute_triggers(
            card, "on_use_on", target_name="the vault door", game_state=gs
        )
        assert any("Access granted" in o for o in outputs)
        assert not any("denied" in o for o in outputs)
        assert door.properties["current_state"] == "closed"

    def test_keycard_clearance_mismatch_fails_with_message(self, graph, skills, logging_events):
        """Wrong clearance tag â†’ condition fails, door stays locked, fail message shown."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        area = Node(id="area_secure", type="area", name="Secure Wing")
        graph.add_node(area)
        door = Node(id="way_lab", type="way", name="Lab Door",
                    properties={"current_state": "locked", "tags": ["clearance-2"]})
        graph.add_node(door)
        graph.add_edge(Edge(source=area.id, target=door.id, type=EDGE_CONNECTION,
                            properties={"direction": "west"}))
        card = Node(id="item_keycard", type="item", name="Keycard",
                    properties={"actions": ["use"], "tags": ["clearance-4"]})
        graph.add_node(card)

        trigger_node = Node(
            id="trigger_keycard_lab",
            type="logic_trigger",
            name="on_use_on â†’ unlock_way",
            properties={
                "trigger_type": "on_use_on",
                "conditions": [{"type": "has_tag", "target": "target", "value": ["clearance-4"]}],
                "effects": [
                    {"type": "message",
                     "params": {"success_message": "Access granted.",
                                "fail_message": "Access denied â€” insufficient clearance."}},
                    {"type": "unlock_way", "params": {"way_id": "target"}},
                ],
            },
        )
        graph.add_node(trigger_node)
        graph.add_edge(Edge(source=card.id, target=trigger_node.id, type=EDGE_TRIGGERS,
                            properties={"trigger_type": "on_use_on",
                                        "conditions": [{"type": "has_tag", "target": "target", "value": ["clearance-4"]}],
                                        "effects": trigger_node.properties["effects"]}))

        gs = type("FakeGS", (), {})()
        gs.get_current_time = lambda: "10:00"
        gs.time_ticks = 1
        gs.turn_number = 1
        gs.active_player = "TestPlayer"
        gs.player = None
        gs.current_area = None
        gs.get_current_area_id = lambda: "area_secure"
        gs._match_exit_direction = lambda area_id, name: "west"

        outputs = trigger_system._execute_triggers(
            card, "on_use_on", target_name="the lab door", game_state=gs
        )
        assert any("Access denied" in o for o in outputs)
        assert not any("Access granted" in o for o in outputs)
        assert door.properties["current_state"] == "locked"

    def test_trigger_array_fires_for_each_type(self, graph, skills, logging_events, sample_item):
        """A trigger with trigger_type array fires for any of the listed types."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        trigger_node = Node(
            id="trigger_multi",
            type="logic_trigger",
            name="multi â†’ message",
            properties={
                "trigger_type": ["on_use", "on_examine"],
                "effect_type": "message",
                "effect_params": {"message": "The drawer rattles."}
            }
        )
        graph.add_node(trigger_node)

        graph.add_edge(Edge(
            source=sample_item.id,
            target=trigger_node.id,
            type=EDGE_TRIGGERS,
            properties={"trigger_type": ["on_use", "on_examine"],
                        "effects": [{"type": "message", "params": {"message": "The drawer rattles."}}]}
        ))

        outputs = trigger_system._execute_triggers(sample_item, "on_use", game_state=None)
        assert len(outputs) > 0
        assert "rattles" in outputs[0]

        outputs = trigger_system._execute_triggers(sample_item, "on_examine", game_state=None)
        assert len(outputs) > 0
        assert "rattles" in outputs[0]

    def test_trigger_array_does_not_fire_for_unlisted_type(self, graph, skills, logging_events, sample_item):
        """A trigger with trigger_type array is skipped for types not in the list."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        trigger_node = Node(
            id="trigger_multi_skip",
            type="logic_trigger",
            name="multi â†’ message",
            properties={
                "trigger_type": ["on_use", "on_examine"],
                "effect_type": "message",
                "effect_params": {"message": "The drawer rattles."}
            }
        )
        graph.add_node(trigger_node)

        graph.add_edge(Edge(
            source=sample_item.id,
            target=trigger_node.id,
            type=EDGE_TRIGGERS,
            properties={"trigger_type": ["on_use", "on_examine"],
                        "effects": [{"type": "message", "params": {"message": "The drawer rattles."}}]}
        ))

        outputs = trigger_system._execute_triggers(sample_item, "on_take", game_state=None)
        assert outputs == []

    def test_speech_matches_condition_contains(self, graph, skills, logging_events, sample_item):
        """speech_matches with contains mode fires when phrase is in the speech."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        trigger_node = Node(
            id="trigger_speech",
            type="logic_trigger",
            name="open sesame â†’ message",
            properties={
                "trigger_type": "on_speech",
                "effect_type": "message",
                "effect_params": {"message": "The wall grinds open!"},
                "conditions": [{"type": "speech_matches", "phrase": "open sesame", "mode": "contains"}]
            }
        )
        graph.add_node(trigger_node)

        graph.add_edge(Edge(
            source=sample_item.id,
            target=trigger_node.id,
            type=EDGE_TRIGGERS,
            properties={
                "trigger_type": "on_speech",
                "conditions": [{"type": "speech_matches", "phrase": "open sesame", "mode": "contains"}],
                "effects": [{"type": "message", "params": {"message": "The wall grinds open!"}}]
            }
        ))

        outputs = trigger_system._execute_triggers(
            sample_item, "on_speech",
            context={"speech": "please say open sesame now", "speaker": "Miki"},
            game_state=None)
        assert len(outputs) > 0
        assert "grinds open" in outputs[0]

    def test_speech_matches_condition_exact_no_fire(self, graph, skills, logging_events, sample_item):
        """speech_matches with exact mode requires the whole phrase, not a substring."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        trigger_node = Node(
            id="trigger_speech_exact",
            type="logic_trigger",
            name="exact â†’ message",
            properties={
                "trigger_type": "on_speech",
                "effect_type": "message",
                "effect_params": {"message": "It worked!"},
                "conditions": [{"type": "speech_matches", "phrase": "open sesame", "mode": "exact"}]
            }
        )
        graph.add_node(trigger_node)

        graph.add_edge(Edge(
            source=sample_item.id,
            target=trigger_node.id,
            type=EDGE_TRIGGERS,
            properties={
                "trigger_type": "on_speech",
                "conditions": [{"type": "speech_matches", "phrase": "open sesame", "mode": "exact"}],
                "effects": [{"type": "message", "params": {"message": "It worked!"}}]
            }
        ))

        outputs = trigger_system._execute_triggers(
            sample_item, "on_speech",
            context={"speech": "please open sesame", "speaker": "Miki"},
            game_state=None)
        assert outputs == []

        outputs = trigger_system._execute_triggers(
            sample_item, "on_speech",
            context={"speech": "open sesame", "speaker": "Miki"},
            game_state=None)
        assert len(outputs) > 0
        assert "It worked" in outputs[0]

    def test_speech_matches_condition_absent_speech_no_fire(self, graph, skills, logging_events, sample_item):
        """speech_matches with no speech in context never fires."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        trigger_node = Node(
            id="trigger_speech_nospeech",
            type="logic_trigger",
            name="no speech â†’ message",
            properties={
                "trigger_type": "on_speech",
                "effect_type": "message",
                "effect_params": {"message": "Should not fire"},
                "conditions": [{"type": "speech_matches", "phrase": "open sesame", "mode": "contains"}]
            }
        )
        graph.add_node(trigger_node)

        graph.add_edge(Edge(
            source=sample_item.id,
            target=trigger_node.id,
            type=EDGE_TRIGGERS,
            properties={
                "trigger_type": "on_speech",
                "conditions": [{"type": "speech_matches", "phrase": "open sesame", "mode": "contains"}],
                "effects": [{"type": "message", "params": {"message": "Should not fire"}}]
            }
        ))

        outputs = trigger_system._execute_triggers(sample_item, "on_speech", game_state=None)
        assert outputs == []

    def test_trigger_with_condition(self, graph, skills, logging_events, sample_item):
        """Trigger with condition only fires when condition is met."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        sample_item.properties["uses"] = 0

        trigger_node = Node(
            id="trigger_conditional",
            type="logic_trigger",
            name="uses exhausted â†’ message",
            properties={
                "trigger_type": "on_use",
                "effect_type": "message",
                "effect_params": {"message": "The item is depleted!"},
                "conditions": [{"type": "uses_reached", "value": "0"}]
            }
        )
        graph.add_node(trigger_node)

        graph.add_edge(Edge(
            source=sample_item.id,
            target=trigger_node.id,
            type=EDGE_TRIGGERS,
            properties={
                "trigger_type": "on_use",
                "conditions": [{"type": "uses_reached", "value": "0"}],
                "effects": [{"type": "message", "params": {"message": "The item is depleted!"}}]
            }
        ))

        outputs = trigger_system._execute_triggers(sample_item, "on_use")
        assert len(outputs) > 0
        assert "depleted" in outputs[0]

    def test_trigger_condition_not_met(self, graph, skills, logging_events, sample_item):
        """Trigger with unmet condition does not fire."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        sample_item.properties["uses"] = 5  # not <= 0

        trigger_node = Node(
            id="trigger_no_fire",
            type="logic_trigger",
            name="wont fire",
            properties={
                "trigger_type": "on_use",
                "effect_type": "message",
                "effect_params": {"message": "Should not fire."},
                "conditions": [{"type": "uses_reached", "value": "0"}]
            }
        )
        graph.add_node(trigger_node)

        graph.add_edge(Edge(
            source=sample_item.id,
            target=trigger_node.id,
            type=EDGE_TRIGGERS,
            properties={
                "trigger_type": "on_use",
                "conditions": [{"type": "uses_reached", "value": "0"}],
                "effects": [{"type": "message", "params": {"message": "Should not fire."}}]
            }
        ))

        outputs = trigger_system._execute_triggers(sample_item, "on_use")
        assert len(outputs) == 0

    def test_available_actions_includes_use(self, graph, skills, logging_events, sample_item):
        """Items with 'use' action have use in available actions."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        actions = trigger_system._get_available_actions(sample_item)
        action_labels = [a["action"] for a in actions]
        assert "use" in action_labels

    def test_available_actions_includes_take(self, graph, skills, logging_events, sample_item):
        """Items with 'take' action have take in available actions."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        actions = trigger_system._get_available_actions(sample_item)
        action_labels = [a["label"] for a in actions]
        assert "Pick up" in action_labels

    def test_contextual_failure_message(self, graph, skills, logging_events):
        """_contextual_failure returns a descriptive failure message."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        msg = trigger_system._contextual_failure(
            "eat", "Rock",
            [{"action": "examine", "label": "Examine", "enabled": True}]
        )
        assert "not food" in msg.lower()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ TestAddRemoveTagEffect â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestWayTriggerFiring:
    """Ways fire on_examine (via the door examine path) and on_use_on
    (when an item is used on them and the item's own trigger is silent)."""

    @staticmethod
    def _make_way_area(graph, door_name="Vault Door", door_state="locked", see_through=False, view=""):
        area = Node(id="area_secure", type="area", name="Secure Wing",
                    properties={"environment": {"light": 80}})
        graph.add_node(area)
        props = {"current_state": door_state}
        if see_through:
            props["see_through"] = True
        door = Node(id="way_vault", type="way", name=door_name, properties=props)
        graph.add_node(door)
        graph.add_edge(Edge(source=area.id, target=door.id, type=EDGE_CONNECTION,
                            properties={"direction": "north", "visible_in_direction": view}))
        return area, door

    @staticmethod
    def _wire_message_trigger(graph, node, trigger_type, message):
        trigger_node = Node(
            id=f"trigger_{node.id}_{trigger_type}",
            type="logic_trigger",
            name=f"{trigger_type} → message",
            properties={
                "trigger_type": trigger_type,
                "effects": [{"type": "message", "params": {"message": message}}],
                "success_message": "",
                "fail_message": "",
            },
        )
        graph.add_node(trigger_node)
        graph.add_edge(Edge(
            source=node.id, target=trigger_node.id, type=EDGE_TRIGGERS,
            properties={"trigger_type": trigger_type,
                        "effects": trigger_node.properties["effects"]},
        ))

    @staticmethod
    def _make_item_actions(graph, skills, logging_events):
        from engine.item_actions import ItemActions
        from engine.matching import NameMatching
        from unittest.mock import MagicMock
        trigger_system = TriggerSystem(graph, skills, logging_events)
        ia = ItemActions.__new__(ItemActions)
        ia.graph = graph
        real_matcher = NameMatching(graph, None)
        ia.matching = MagicMock()
        ia.matching._match_item_name = MagicMock(return_value=None)
        ia.matching._match_exit_direction = MagicMock(side_effect=real_matcher._match_exit_direction)
        ia.matching._match_character_name = MagicMock(return_value=(None, []))
        ia.matching.way_handle = MagicMock(side_effect=real_matcher.way_handle)
        ia.matching.resolve_exit = MagicMock(side_effect=real_matcher.resolve_exit)
        ia.trigger_system = trigger_system
        ia.equipment = MagicMock()
        ia.ghost_system = MagicMock()
        ia.ghost_system.check_ghost_action = MagicMock(return_value=None)
        ia.world = None
        return ia

    @staticmethod
    def _make_player_manager():
        from unittest.mock import MagicMock
        pm = MagicMock()
        pm.active_player = "Hero"
        pm.current_area = MagicMock()
        pm.current_area.name = "Secure Wing"
        pm.ghost_mode = False
        pm.lighting = MagicMock()
        pm.lighting.can_see_in_dark = MagicMock(return_value=True)
        pm.lighting.get_ambient_light = MagicMock(return_value=80)
        pm._get_current_area_id = MagicMock(return_value="area_secure")
        pm._player_node_id = MagicMock(side_effect=lambda n: f"player_{n}")
        pm.players = {}
        return pm

    def test_way_on_examine_fires(self, graph, skills, logging_events):
        """Examining a door fires its on_examine triggers."""
        _, door = self._make_way_area(graph)
        self._wire_message_trigger(graph, door, "on_examine", "A faint hum comes from the lock.")
        ia = self._make_item_actions(graph, skills, logging_events)
        pm = self._make_player_manager()

        desc = ia.get_item_desc(pm, "north")
        assert "faint hum" in desc

    def test_way_on_examine_peephole(self, graph, skills, logging_events):
        """A closed see_through door with a view reveals the room on examine."""
        _, door = self._make_way_area(graph, see_through=True,
                                      view="the lab bench glows faintly beyond")
        ia = self._make_item_actions(graph, skills, logging_events)
        pm = self._make_player_manager()

        desc = ia.get_item_desc(pm, "north")
        assert "lab bench glows" in desc
        assert "currently locked" in desc

    def test_way_on_use_fires_when_item_silent(self, graph, skills, logging_events):
        """Using a passive item on a door fires the door's on_use trigger
        (target side), matching the item-target fallback semantics."""
        area, door = self._make_way_area(graph)
        self._wire_message_trigger(graph, door, "on_use",
                                   "The lock rejects the item with a dull thunk.")
        card = Node(id="item_rock", type="item", name="Rock",
                    properties={"actions": ["use"]})
        graph.add_node(card)
        graph.add_edge(Edge(source=card.id, target=area.id, type="in"))
        ia = self._make_item_actions(graph, skills, logging_events)
        pm = self._make_player_manager()

        def _find_item_node(name):
            return graph.get_node(f"item_{name}")
        pm.find_item_node = _find_item_node

        result = ia.use_item_on(pm, "Rock", target_name="north")
        assert "dull thunk" in result

    def test_way_on_use_not_fired_when_item_has_on_use_on(self, graph, skills, logging_events):
        """A source item with a working on_use_on wins — the way's on_use
        does not also fire."""
        area, door = self._make_way_area(graph)
        self._wire_message_trigger(graph, door, "on_use",
                                   "The lock rejects the item with a dull thunk.")
        card = Node(id="item_keycard", type="item", name="Keycard",
                    properties={"actions": ["use"]})
        graph.add_node(card)
        graph.add_edge(Edge(source=card.id, target=area.id, type="in"))

        trigger_node = Node(
            id="trigger_keycard_use_on",
            type="logic_trigger",
            name="on_use_on → message",
            properties={
                "trigger_type": "on_use_on",
                "effects": [{"type": "message",
                             "params": {"message": "The keycard slot beeps."}}],
                "success_message": "",
                "fail_message": "",
            },
        )
        graph.add_node(trigger_node)
        graph.add_edge(Edge(
            source=card.id, target=trigger_node.id, type=EDGE_TRIGGERS,
            properties={"trigger_type": "on_use_on",
                        "effects": trigger_node.properties["effects"]},
        ))
        ia = self._make_item_actions(graph, skills, logging_events)
        pm = self._make_player_manager()

        def _find_item_node(name):
            return graph.get_node(f"item_{name}")
        pm.find_item_node = _find_item_node

        result = ia.use_item_on(pm, "Keycard", target_name="north")
        assert "slot beeps" in result
        assert "dull thunk" not in result


    def test_area_on_examine_fires(self, graph, skills, logging_events):
        """Examining the current area fires its on_examine triggers."""
        area = Node(id="area_secure", type="area", name="Secure Wing",
                    properties={"environment": {"light": 80},
                                "description": "White tile, humming lights."})
        graph.add_node(area)
        self._wire_message_trigger(graph, area, "on_examine",
                                   "A voice announces: 'Bay 7 clearance required.'")
        ia = self._make_item_actions(graph, skills, logging_events)
        pm = self._make_player_manager()

        desc = ia.get_item_desc(pm, "the room")
        assert "White tile" in desc
        assert "Bay 7" in desc

    def test_area_on_enter_fires(self, graph, skills, logging_events, trigger_system):
        """Moving into an area fires its on_enter triggers."""
        from engine.movement import MovementSystem
        area_a = Node(id="area_hall", type="area", name="Hall",
                      properties={"environment": {"light": 80}})
        area_b = Node(id="area_secure", type="area", name="Secure Wing",
                      properties={"environment": {"light": 80}})
        graph.add_node(area_a)
        graph.add_node(area_b)
        door = Node(id="way_door", type="way", name="Door",
                    properties={"current_state": "open"})
        graph.add_node(door)
        graph.add_edge(Edge(source=area_a.id, target=door.id, type=EDGE_CONNECTION,
                            properties={"direction": "north"}))
        graph.add_edge(Edge(source=door.id, target=area_b.id, type=EDGE_CONNECTION,
                            properties={"direction": "south"}))
        graph.add_edge(Edge(source=area_b.id, target=door.id, type=EDGE_CONNECTION,
                            properties={"direction": "south"}))
        graph.add_edge(Edge(source=door.id, target=area_a.id, type=EDGE_CONNECTION,
                            properties={"direction": "north"}))
        self._wire_message_trigger(graph, area_b, "on_enter",
                                   "The room lights snap on as you enter.")

        gs = type("FakeGS", (), {})()
        gs.player = MagicMock()
        gs.player.state = "awake"
        gs.player.has_condition = MagicMock(return_value=False)
        gs.player.vitals = {"Entertainment": 50}
        gs.player.visited_areas = set()
        gs.players = {}
        gs.active_player = "Hero"
        gs.current_area = MagicMock()
        gs.current_area.name = "Hall"
        gs.current_area.environment = {"light": 80}
        gs.time_ticks = 1
        gs.turn_number = 1
        gs.get_current_time = lambda: "10:00"
        gs.get_current_area_id = lambda: area_a.id
        gs._get_current_area_id = gs.get_current_area_id
        gs.apply_action = lambda *a, **k: None
        log_entries = []
        gs.add_log_entry = lambda *a, **k: log_entries.append(a[0])
        gs.record_turn_event = lambda *a, **k: None
        gs.speech_log = []
        gs.area_node_id = lambda name: f"area_{name.lower().replace(' ', '_')}"
        gs.player_node_id = lambda name: f"player_{name}"
        gs._player_node_id = gs.player_node_id
        gs._area_node_id = gs.area_node_id
        gs._set_player_area = lambda *a, **k: None
        gs._match_exit_direction = lambda area_id, name: "north" if "north" in name.lower() else None
        gs.name_matcher = MagicMock()
        gs.name_matcher._match_exit_direction = MagicMock(return_value="north")
        name_matcher = MagicMock()
        name_matcher._match_exit_direction = MagicMock(return_value="north")
        name_matcher.resolve_exit = MagicMock(
            side_effect=lambda area_id, name: (
                graph.get_edges_for_source(area_id, EDGE_CONNECTION)[0],
                graph.get_node("way_door"),
                "north",
            ) if "north" in name.lower() else (None, None, "")
        )
        gs.npc_behaviors = MagicMock()
        gs.npc_behaviors.process_simple_npcs = MagicMock()
        gs.player.visited_areas = gs.player.visited_areas

        movement = MovementSystem(
            graph, gs, trigger_system,
            toggleable_items=MagicMock(),
            name_matcher=name_matcher,
            game_state=gs,
        )
        result = movement.move_to_area("north")
        assert "Secure Wing" in result
        assert any("lights snap on" in entry for entry in log_entries)


class TestAddRemoveTagEffect:
    """add_tag / remove_tag trigger effects (task-169)."""

    def _make_item(self, graph, tags=None):
        item = Node(
            id="item_tagged",
            type="item",
            name="Tagged Item",
            properties={"description": "An item.", "tags": tags or []},
        )
        graph.add_node(item)
        return item

    def test_add_tag_adds_to_properties(self, graph, logging_events):
        effects = Effects(graph, logging_events)
        item = self._make_item(graph)
        result = effects.execute("add_tag", {"tag": "flammable", "node_id": item.id}, {}, item_node=item)
        assert "flammable" in item.properties["tags"]
        assert any("flammable" in msg for msg in result)

    def test_remove_tag_removes(self, graph, logging_events):
        effects = Effects(graph, logging_events)
        item = self._make_item(graph, tags=["flammable", "tool"])
        result = effects.execute("remove_tag", {"tag": "flammable", "node_id": item.id}, {}, item_node=item)
        assert "tool" in item.properties["tags"]
        assert "flammable" not in item.properties["tags"]
        assert any("Removed tag" in msg for msg in result)

    def test_works_with_comma_string_tags(self, graph, logging_events):
        effects = Effects(graph, logging_events)
        item = self._make_item(graph, tags="flammable,tool")
        effects.execute("add_tag", {"tag": "magic", "node_id": item.id}, {}, item_node=item)
        assert isinstance(item.properties["tags"], list)
        assert "magic" in item.properties["tags"]
        assert "flammable" in item.properties["tags"]

    def test_tag_based_targeting_sees_new_tag(self, graph, skills, logging_events):
        """After add_tag, tag-based targeting in the same trigger finds the item."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        area = Node(id="area_test", type="area", name="Test",
                    properties={"environment": {}})
        graph.add_node(area)
        item = self._make_item(graph)
        from graph import EDGE_IN
        graph.add_edge(Edge(source=item.id, target=area.id, type=EDGE_IN))

        # Trigger that tags the item with light_source on use
        graph.add_edge(Edge(
            source=item.id,
            target="trigger_tag",  # stub target â€” effects live on the edge
            type=EDGE_TRIGGERS,
            properties={
                "trigger_type": "on_use",
                "effects": [{"type": "add_tag", "params": {"tag": "light_source", "node_id": "self"}}]
            }
        ))

        trigger_system._execute_triggers(item, "on_use")
        assert "light_source" in item.properties["tags"]

        # Tag-based targeting must now see the item
        matches = trigger_system._get_items_by_tag_in_area("light_source", None, "area_test")
        assert any(m.id == item.id for m in matches)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ TestApplyRemoveTraitEffect â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestApplyRemoveTraitEffect:
    """apply_trait / remove_trait trigger effects."""

    @staticmethod
    def _make_game_state(player, extra_players=None):
        game_state = type("FakeGameState", (), {})()
        game_state.player = player
        game_state.players = extra_players or {player.name: player}
        game_state.active_player = player.name
        game_state.get_players_in_area = lambda area_name=None, exclude_self=True: []
        game_state.log_entries = []
        game_state.add_log_entry = lambda text: game_state.log_entries.append(text)
        return game_state

    def test_apply_trait_self(self, graph, logging_events):
        from player import Player
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        game_state = self._make_game_state(test_player)

        result = effects.execute(
            "apply_trait", {"trait": "dark_vision", "target": "self", "param": True},
            {}, game_state=game_state,
        )
        assert test_player.traits.get("dark_vision") is True
        # Silent by default â€” no message unless the author specifies one.
        assert result == []

    def test_apply_trait_self_with_message(self, graph, logging_events):
        from player import Player
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        game_state = self._make_game_state(test_player)

        result = effects.execute(
            "apply_trait", {"trait": "dark_vision", "target": "self", "param": True,
                            "message": "Your eyes adjust to the dark."},
            {}, game_state=game_state,
        )
        assert test_player.traits.get("dark_vision") is True
        assert "Your eyes adjust to the dark." in result

    def test_apply_trait_with_param(self, graph, logging_events):
        from player import Player
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        game_state = self._make_game_state(test_player)

        effects.execute(
            "apply_trait", {"trait": "allergic", "target": "self", "param": "pollen"},
            {}, game_state=game_state,
        )
        assert test_player.traits.get("allergic") == "pollen"

    def test_apply_trait_to_named_target(self, graph, logging_events):
        from player import Player
        effects = Effects(graph, logging_events)
        actor = Player("Actor")
        other = Player("Other")
        game_state = self._make_game_state(actor, {"Actor": actor, "Other": other})

        effects.execute(
            "apply_trait", {"trait": "hardy", "target": "Other", "param": True},
            {}, game_state=game_state,
        )
        assert other.traits.get("hardy") is True
        assert actor.traits.get("hardy") is None

    def test_apply_trait_to_named_target_is_silent_for_actor(self, graph, logging_events):
        """A trait granted to someone else must not be announced in the ACTOR's
        output â€” otherwise pressing a button reads back as 'I gained Hostile'."""
        from player import Player
        effects = Effects(graph, logging_events)
        actor = Player("Actor")
        other = Player("Other")
        game_state = self._make_game_state(actor, {"Actor": actor, "Other": other})

        result = effects.execute(
            "apply_trait", {"trait": "hostile", "target": "Other", "param": True},
            {}, game_state=game_state,
        )
        assert other.traits.get("hostile") is True
        assert actor.traits.get("hostile") is None
        assert result == []

    def test_remove_trait_from_named_target_is_silent_for_actor(self, graph, logging_events):
        """Same for remove_trait: only the affected player hears about it."""
        from player import Player
        effects = Effects(graph, logging_events)
        actor = Player("Actor")
        other = Player("Other")
        other.traits["hostile"] = True
        game_state = self._make_game_state(actor, {"Actor": actor, "Other": other})

        result = effects.execute(
            "remove_trait", {"trait": "hostile", "target": "Other"},
            {}, game_state=game_state,
        )
        assert "hostile" not in other.traits
        assert result == []

    def test_remove_trait_self(self, graph, logging_events):
        from player import Player
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        test_player.traits["dark_vision"] = True
        game_state = self._make_game_state(test_player)

        result = effects.execute(
            "remove_trait", {"trait": "dark_vision", "target": "self"},
            {}, game_state=game_state,
        )
        assert "dark_vision" not in test_player.traits
        # Silent by default â€” no message unless the author specifies one.
        assert result == []

    def test_remove_trait_self_with_message(self, graph, logging_events):
        from player import Player
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        test_player.traits["dark_vision"] = True
        game_state = self._make_game_state(test_player)

        result = effects.execute(
            "remove_trait", {"trait": "dark_vision", "target": "self",
                             "message": "Your dark vision fades."},
            {}, game_state=game_state,
        )
        assert "dark_vision" not in test_player.traits
        assert "Your dark vision fades." in result

    def test_remove_trait_missing_is_noop(self, graph, logging_events):
        from player import Player
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        game_state = self._make_game_state(test_player)

        result = effects.execute(
            "remove_trait", {"trait": "hardy", "target": "self"},
            {}, game_state=game_state,
        )
        assert result == []  # silent no-op â€” no message specified
        assert test_player.traits == {}

    def test_apply_trait_no_id_returns_nothing(self, graph, logging_events):
        from player import Player
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        game_state = self._make_game_state(test_player)

        result = effects.execute(
            "apply_trait", {"target": "self"}, {}, game_state=game_state,
        )
        assert result == []

    def test_apply_condition_no_id_returns_nothing(self, graph, logging_events):
        from player import Player
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        game_state = self._make_game_state(test_player)
        game_state.conditions = type("C", (), {
            "apply_condition": lambda *a, **k: None,
            "remove_condition": lambda *a, **k: None,
        })()

        result = effects.execute(
            "apply_condition", {"target": "self"}, {}, game_state=game_state,
        )
        assert result == []

    def test_apply_condition_with_symptoms_and_extras(self, graph, logging_events):
        """apply_condition carries per-instance symptoms + extra conditions."""
        from player import Player
        from unittest.mock import MagicMock
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        game_state = self._make_game_state(test_player)

        captured = {}
        game_state.conditions = MagicMock()
        game_state.conditions.apply_condition = lambda *a, **k: captured.update(k)

        effects.execute(
            "apply_condition", {
                "condition": "poisoned", "target": "self", "duration": 10,
                "source": "poisoned wine", "periodic": {"HP": -8},
                "symptoms": {"8": "queasy", "1": "spinning"},
                "extra_conditions": [{"condition": "blind", "duration": 3}],
            },
            {}, game_state=game_state,
        )
        assert captured["duration"] == 10
        assert captured["periodic"] == {"HP": -8}
        assert captured["symptoms"] == {"8": "queasy", "1": "spinning"}
        assert captured["extra_conditions"] == [{"condition": "blind", "duration": 3}]

    def test_apply_trait_conflict_is_system_message_not_agent_output(self, graph, logging_events):
        """A conflicting trait grant surfaces in the SYSTEM log (event stream /
        UI) but never in the agent's action result."""
        from player import Player
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        test_player.traits["night_owl"] = True
        game_state = self._make_game_state(test_player)

        result = effects.execute(
            "apply_trait", {"trait": "morning_person", "target": "self", "param": True},
            {}, game_state=game_state,
        )
        # Agent sees nothing...
        assert result == []
        # ...but the system log records the conflict.
        assert any("conflict" in e for e in game_state.log_entries)
        assert test_player.traits.get("morning_person") is None


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ TestTriggerTestHelper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestTriggerTestHelper:
    """The editor's trigger test endpoint (TriggerSystem.test_trigger)."""

    def test_dry_run_reports_conditions_and_outputs(self, graph, skills, logging_events, sample_item):
        """Dry run reports per-condition pass/fail and dry-run outputs, no side effects."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        trigger_def = {
            "trigger_type": "on_use",
            "conditions": [{"type": "uses_reached", "value": "0"}],
            "effects": [{"type": "message", "params": {"message": "The item is depleted!"}}],
        }

        sample_item.properties["uses"] = 0
        result = trigger_system.test_trigger(trigger_def, item_node=sample_item, dry_run=True)

        assert result["conditions_pass"] is True
        assert all(c["passed"] for c in result["conditions"])
        assert result["fireable"] is True
        assert len(result["outputs"]) == 1
        assert "dry-run" in result["outputs"][0]
        assert "depleted" in result["outputs"][0]
        assert result["side_effects"] == []

    def test_dry_run_flags_failed_condition(self, graph, skills, logging_events, sample_item):
        """A failed condition is reported as failed and blocks the dry-run output list."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        trigger_def = {
            "trigger_type": "on_use",
            "conditions": [{"type": "uses_reached", "value": "0"}],
            "effects": [{"type": "message", "params": {"message": "Should not fire."}}],
        }

        sample_item.properties["uses"] = 5
        result = trigger_system.test_trigger(trigger_def, item_node=sample_item, dry_run=True)

        assert result["conditions_pass"] is False
        assert result["conditions"][0]["passed"] is False
        assert result["fireable"] is True

    def test_live_run_executes_message_effect(self, graph, skills, logging_events, sample_item):
        """Live run executes effects and returns real output messages."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        trigger_def = {
            "trigger_type": "on_use",
            "conditions": [],
            "effects": [{"type": "message", "params": {"message": "It crackles and lights up!"}}],
        }

        result = trigger_system.test_trigger(trigger_def, item_node=sample_item, dry_run=False)

        assert result["conditions_pass"] is True
        assert len(result["outputs"]) == 1
        assert "crackles" in result["outputs"][0]
        assert "dry-run" not in result["outputs"][0]

    def test_fireable_false_when_item_required_but_missing(self, graph, skills, logging_events):
        """Trigger types that need an item report fireable=false when no item is provided."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        trigger_def = {
            "trigger_type": "on_examine",
            "conditions": [],
            "effects": [{"type": "message", "params": {"message": "Hi."}}],
        }

        result = trigger_system.test_trigger(trigger_def, item_node=None, dry_run=True)
        assert result["fireable"] is False

    def test_undefined_trigger_type_reports_clear_reason(self, graph, skills, logging_events):
        """No trigger type selected is reported distinctly from missing item context."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        trigger_def = {
            "trigger_type": "",
            "conditions": [],
            "effects": [{"type": "message", "params": {"message": "Hi."}}],
        }

        result = trigger_system.test_trigger(trigger_def, item_node=None, dry_run=True)
        assert result["fireable"] is False
        assert "no trigger type selected" in result["fireable_reason"]

    def test_dry_run_apply_trait_reports_character_target(self, graph, skills, logging_events, sample_item):
        """apply_trait dry-run describes the character target, not 'modify node'."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        trigger_def = {
            "trigger_type": "on_use",
            "conditions": [],
            "effects": [{"type": "apply_trait", "params": {"trait": "hostile", "target": "Bob", "param": True}}],
        }

        result = trigger_system.test_trigger(trigger_def, item_node=sample_item, dry_run=True)
        assert result["side_effects"]
        msg = result["side_effects"][0]
        assert "would apply trait" in msg
        assert "hostile" in msg
        assert "Bob" in msg
        assert "modify node" not in msg

    def test_array_trigger_type_normalized(self, graph, skills, logging_events, sample_item):
        """The editor stores trigger_type as an array â€” test_trigger must accept it."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        trigger_def = {
            "trigger_type": ["on_use"],
            "conditions": {},
            "effects": [{"type": "apply_trait", "params": {"trait": "hostile", "target": "Bob", "param": True}}],
        }

        result = trigger_system.test_trigger(trigger_def, item_node=sample_item, dry_run=True)
        assert result["trigger_type"] == "on_use"
        assert result["fireable"] is True
        assert result["conditions_pass"] is True
        assert "would apply trait" in result["side_effects"][0]

    def test_item_trigger_without_context_not_fireable(self, graph, skills, logging_events):
        """An itemful trigger with no item context reports fireable=false."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        trigger_def = {
            "trigger_type": ["on_use"],
            "conditions": {},
            "effects": [{"type": "message", "params": {"message": "Hi."}}],
        }

        result = trigger_system.test_trigger(trigger_def, item_node=None, dry_run=True)
        assert result["fireable"] is False
        assert "needs an item/way context" in result["fireable_reason"]

    def test_speech_context_reaches_condition(self, graph, skills, logging_events, sample_item):
        """test_trigger passes context (speech) through to condition evaluation."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        trigger_def = {
            "trigger_type": "on_speech",
            "conditions": [{"type": "speech_matches", "phrase": "open sesame", "mode": "contains"}],
            "effects": [{"type": "message", "params": {"message": "The wall grinds open!"}}],
        }

        result = trigger_system.test_trigger(
            trigger_def, item_node=sample_item, dry_run=True,
            context={"speech": "please open sesame now", "speaker": "Miki"},
        )
        assert result["conditions_pass"] is True
        assert result["conditions"][0]["passed"] is True


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ TestUnifiedEffectTargeting â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestUnifiedEffectTargeting:
    """target_by name/tag/trait/type/all_in_area fan-out for trigger effects."""

    @staticmethod
    def _world():
        from app import create_app
        app = create_app({'TESTING': True})
        return app.world, app.test_client()

    def _add_players(self, world, names):
        from player import Player
        world.set_active_player(names[0])
        for name in names:
            world.add_player(Player(name))
            world.set_player_area(name, 'Blizzard Forest Clearing')
            world.player_manager.players[name].current_area = 'Blizzard Forest Clearing'

    def _run_condition(self, world, params):
        from graph import Node, Edge, EDGE_TRIGGERS
        cloud = Node(id=f'item_t_{abs(hash(str(params)))%100000}', type='item', name='cloud', properties={})
        world.graph.add_node(cloud)
        world.graph.add_edge(Edge(source=cloud.id, target='trig_t', type='triggers', properties={
            'trigger_type': ['on_tick'],
            'effects': [{'type': 'apply_condition', 'params': dict(params)}],
        }))
        for p in world.player_manager.players.values():
            p.conditions.pop('sick', None)
        world.triggers._execute_triggers(cloud, 'on_tick', game_state=world)
        return sorted(n for n, p in world.player_manager.players.items() if p.conditions.get('sick'))

    def test_by_name(self):
        world, _ = self._world()
        self._add_players(world, ['Kaelen Voss', 'Other'])
        got = self._run_condition(world, {'condition': 'sick', 'target_by': 'name', 'target_value': 'Other', 'duration': 5})
        assert got == ['Other']

    def test_by_trait(self):
        world, _ = self._world()
        self._add_players(world, ['Kaelen Voss', 'Other'])
        world.player_manager.players['Kaelen Voss'].traits['hostile'] = True
        got = self._run_condition(world, {'condition': 'sick', 'target_by': 'trait', 'target_value': 'hostile', 'duration': 5})
        assert got == ['Kaelen Voss']

    def test_by_tag(self):
        world, _ = self._world()
        self._add_players(world, ['Kaelen Voss', 'Other'])
        world.player_manager.players['Other'].tags = ['wolf']
        got = self._run_condition(world, {'condition': 'sick', 'target_by': 'tag', 'target_value': 'wolf', 'duration': 5})
        assert got == ['Other']

    def test_by_type_character_area(self):
        world, _ = self._world()
        self._add_players(world, ['Kaelen Voss', 'Other'])
        got = self._run_condition(world, {'condition': 'sick', 'target_by': 'type', 'target_value': 'character', 'target_scope': 'area', 'duration': 5})
        assert 'Kaelen Voss' in got and 'Other' in got

    def test_all_in_area(self):
        world, _ = self._world()
        self._add_players(world, ['Kaelen Voss', 'Other'])
        got = self._run_condition(world, {'condition': 'sick', 'target_by': 'all_in_area', 'duration': 5})
        assert 'Kaelen Voss' in got and 'Other' in got

    def test_legacy_target_tag_still_works(self):
        from graph import Node, Edge, EDGE_TRIGGERS
        world, _ = self._world()
        world.set_active_player('Kaelen Voss')
        area = 'Blizzard Forest Clearing'
        torch = Node(id='item_torch', type='item', name='torch', properties={'tags': ['flammable']})
        world.graph.add_node(torch)
        world.graph.add_edge(Edge(source=torch.id, target='area_blizzard_forest_clearing', type='in'))
        cloud = Node(id='item_t_legacy', type='item', name='cloud', properties={})
        world.graph.add_node(cloud)
        world.graph.add_edge(Edge(source=cloud.id, target='trig_t', type='triggers', properties={
            'trigger_type': ['on_tick'],
            'effects': [{'type': 'set_state', 'params': {'target_tag': 'flammable', 'state': 'extinguished'}}],
        }))
        world.triggers._execute_triggers(cloud, 'on_tick', game_state=world)
        assert torch.properties.get('current_state') == 'extinguished'


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ TestGiveItemEffect â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestGiveItemEffect:
    """give_item places a library item directly into a character's inventory."""

    @staticmethod
    def _world():
        from app import create_app
        app = create_app({'TESTING': True})
        return app.world, app.test_client()

    def _fire(self, world, params, trigger_type="on_use", item_name="giver"):
        from graph import Node, Edge
        src = Node(id=f'item_{item_name}_{abs(hash(str(params)))%100000}', type='item', name=item_name, properties={})
        world.graph.add_node(src)
        world.graph.add_edge(Edge(source=src.id, target='trig_g', type='triggers', properties={
            'trigger_type': [trigger_type],
            'effects': [{'type': 'give_item', 'params': dict(params)}],
        }))
        return world.triggers._execute_triggers(src, trigger_type, game_state=world)

    def _carried(self, world, player_name):
        player_id = f"player_{player_name}".replace(' ', '_')
        ids = [e.source for e in world.graph.edges if e.type == 'carrying' and e.target == player_id]
        return [world.graph.get_node(i).name for i in ids if world.graph.get_node(i)]

    def _carried_matches(self, world, player_name, needle):
        return any(needle.lower() in name.lower() for name in self._carried(world, player_name))

    def test_give_to_self(self):
        world, _ = self._world()
        world.set_active_player('Kaelen Voss')
        outs = self._fire(world, {'item_id': 'rotten_meat', 'target': 'self'})
        assert self._carried_matches(world, 'Kaelen Voss', 'Rotten Meat')
        # triggers from the library were materialized onto the given item
        carried_id = next(e.source for e in world.graph.edges
                          if e.type == 'carrying' and e.target == 'player_Kaelen_Voss')
        assert len(world.graph.get_edges_for_source(carried_id, 'triggers')) >= 1

    def test_give_to_named_character(self):
        from player import Player
        world, _ = self._world()
        world.set_active_player('Kaelen Voss')
        world.add_player(Player('Other'))
        world.set_player_area('Other', 'Blizzard Forest Clearing')
        self._fire(world, {'item_id': 'bandages', 'target': 'Other'})
        assert self._carried_matches(world, 'Other', 'bandages')

    def test_give_to_on_use_on_target(self):
        world, _ = self._world()
        world.set_active_player('Kaelen Voss')
        outs = self._fire(world, {'item_id': 'bandages', 'target': 'target'}, trigger_type='on_use_on')
        assert self._carried_matches(world, 'Kaelen Voss', 'bandages')

    def test_give_unknown_id_creates_blank_item(self):
        world, _ = self._world()
        world.set_active_player('Kaelen Voss')
        # Consistent with spawn_item: unknown ids still materialize a blank node.
        self._fire(world, {'item_id': 'brand_new_gadget', 'target': 'self'})
        assert self._carried_matches(world, 'Kaelen Voss', 'brand_new_gadget')

    def test_carried_item_fires_on_tick(self):
        """A hidden carried item's on_tick trigger fires on tick_turn â€”
        the contagion/sneeze-cloud pattern (carriers aren't 'lit')."""
        from graph import Node, Edge
        world, _ = self._world()
        world.set_active_player('Kaelen Voss')
        player_id = 'player_Kaelen_Voss'
        carrier = Node(id='item_carrier', type='item', name='carrier', properties={
            'current_state': 'hidden', 'uses': -1, 'actions': 'examine,take,use'})
        world.graph.add_node(carrier)
        world.graph.add_edge(Edge(source='item_carrier', target=player_id, type='carrying'))
        world.graph.add_edge(Edge(source='item_carrier', target='trig_c', type='triggers', properties={
            'trigger_type': ['on_tick'],
            'effects': [{'type': 'apply_condition', 'params': {
                'condition': 'sick', 'target_by': 'all_in_area', 'duration': 8, 'source': 'miasma'}}],
            'conditions': {'operator': 'and', 'conditions': [
                {'type': 'random_chance', 'value': 100}]},
        }))
        player = world.player_manager.players['Kaelen Voss']
        player.conditions.pop('sick', None)
        world.tick_turn()
        assert player.has_condition('sick')


class TestLegacyTriggerEffects:
    """Legacy effect_type/effect_params shim (pre-migration scenario triggers)."""

    def _wire_legacy_trigger(self, graph, item, trigger_type, effect_type, effect_params):
        props = {
            "trigger_type": trigger_type,
            "effect_type": effect_type,
            "effect_params": effect_params,
            "target_name": "",
        }
        trigger_id = f"trigger_{item.id}_{trigger_type}"
        tnode = Node(id=trigger_id, type="logic_trigger", name="legacy", properties=props)
        graph.add_node(tnode)
        graph.add_edge(Edge(source=item.id, target=trigger_id, type=EDGE_TRIGGERS, properties=props))

    def test_legacy_message_on_examine(self, graph, trigger_system, sample_item):
        self._wire_legacy_trigger(
            graph,
            sample_item,
            "on_examine",
            "message",
            {"message": "You notice a scratch on the tile."},
        )
        outputs = trigger_system._execute_triggers(sample_item, "on_examine", game_state=None)
        assert outputs == ["You notice a scratch on the tile."]

    def test_legacy_damage_splits_narrative(self, graph, trigger_system, sample_item):
        hero = MagicMock()
        hero.vitals = {"HP": 100}
        hero.name = "Hero"
        game_state = MagicMock()
        game_state.player = hero
        game_state.players = {"Hero": hero}
        game_state.activities = MagicMock()
        game_state.activities.wake_on_damage.return_value = None

        self._wire_legacy_trigger(
            graph,
            sample_item,
            "on_take",
            "damage",
            {
                "amount": 8,
                "target": "self",
                "message": "A searing cold shoots up your arm.",
            },
        )
        outputs = trigger_system._execute_triggers(sample_item, "on_take", game_state=game_state)
        assert hero.vitals["HP"] == 92
        assert any("takes 8 damage" in line for line in outputs)
        assert "A searing cold shoots up your arm." in outputs

    def test_modern_effects_take_precedence_over_legacy(self, graph, trigger_system, sample_item):
        props = {
            "trigger_type": ["on_examine"],
            "effect_type": "message",
            "effect_params": {"message": "legacy text"},
            "effects": [{"type": "message", "params": {"message": "modern text"}}],
        }
        trigger_id = "trigger_hybrid"
        graph.add_node(Node(id=trigger_id, type="logic_trigger", name="hybrid", properties=props))
        graph.add_edge(Edge(source=sample_item.id, target=trigger_id, type=EDGE_TRIGGERS, properties=props))
        outputs = trigger_system._execute_triggers(sample_item, "on_examine", game_state=None)
        assert outputs == ["modern text"]

