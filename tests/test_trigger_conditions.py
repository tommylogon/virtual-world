"""Unit tests for TriggerSystem condition evaluation and save throws."""
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

    def test_random_chance_dual_path_consistency(self, trigger_system, sample_item):
        """Both evaluator paths return identical results for random_chance (seeded)."""
        import random
        for value in ("0", "50", "100"):
            for _ in range(20):
                seed = random.randint(0, 2**32)
                random.seed(seed)
                cond = {"type": "random_chance", "value": value}
                flat = trigger_system._evaluate_trigger_condition(cond, sample_item)
                random.seed(seed)
                tree = trigger_system._evaluate_conditions(cond, {"item_node": sample_item})
                assert flat is tree

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

        Value may be an array  -  any-of semantics  -  and works on non-player
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
        """Legacy string-valued trigger_type keeps working.

        The toggleable tag is required as well: `_get_available_actions`
        only offers Toggle when ToggleableItems.toggle_item_status would
        accept it, so a bare on_toggle_on trigger is no longer enough.
        """
        sample_item.properties["actions"] = ["examine"]
        sample_item.properties["tags"] = ["toggleable"]
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
