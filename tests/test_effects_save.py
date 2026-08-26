"""Tests for the save-aware damage effect (task-159)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from graph import WorldGraph
from engine.effects import Effects
from engine.skills import SkillSystem
from engine.logging_events import GameLogger


class ConditionsStub:
    """Records apply_condition calls for the save-gate tests."""

    def __init__(self):
        self.applied = []

    def apply_condition(self, player_name, condition, **kwargs):
        self.applied.append((player_name, condition, kwargs))


class FakeGameState:
    """Minimal duck-typed game_state used by the damage handler."""

    def __init__(self, player, players=None):
        self.player = player
        self.players = players or {player.name: player}
        self.skills = SkillSystem(None, GameLogger())
        self.active_player = player.name
        self.conditions = ConditionsStub()

    def get_players_in_area(self, area_name=None, exclude_self=True):
        return [
            {"name": name}
            for name in self.players
            if name != self.player.name
        ]

    def saving_throw(self, player, stat, dc=12):
        return self.skills.saving_throw(player, stat, dc)


@pytest.fixture
def effects():
    """An Effects instance with no trigger wiring needed."""
    return Effects(WorldGraph(), GameLogger())


@pytest.fixture
def hero():
    from player import Player
    p = Player("Hero")
    p.vitals["HP"] = 50
    return p


class TestDamageSave:
    """handle_damage respects an optional save (halve/avoid)."""

    def test_damage_no_save(self, effects, hero):
        """Plain damage still works as before."""
        gs = FakeGameState(hero)
        out = effects.handle_damage({"amount": 10, "target": "self"}, {}, game_state=gs)
        assert hero.vitals["HP"] == 40
        assert any("takes 10 damage" in line for line in out)

    def test_damage_save_success_halves(self, effects, hero):
        """Successful save halves the damage by default."""
        hero.stats["DEX"] = 20  # mod +5, DC 5 always passes (min total 6)
        gs = FakeGameState(hero)
        out = effects.handle_damage(
            {"amount": 10, "target": "self", "save": {"stat": "DEX", "dc": 5}},
            {},
            game_state=gs,
        )
        assert hero.vitals["HP"] == 45  # 10 // 2 = 5
        assert any("[Save] DEX vs DC 5" in line for line in out)
        assert any("takes 5 damage (was 10)" in line for line in out)

    def test_damage_save_success_avoids(self, effects, hero):
        """on_success='none' avoids the damage entirely."""
        hero.stats["DEX"] = 20  # mod +5, DC 5 always passes
        gs = FakeGameState(hero)
        out = effects.handle_damage(
            {"amount": 10, "target": "self",
             "save": {"stat": "DEX", "dc": 5, "on_success": "none"}},
            {},
            game_state=gs,
        )
        assert hero.vitals["HP"] == 50
        assert any("avoids the damage entirely" in line for line in out)

    def test_damage_save_failure_full(self, effects, hero):
        """Failed save applies the full amount."""
        hero.stats["DEX"] = 3  # mod -3, max total 17 < DC 30
        gs = FakeGameState(hero)
        out = effects.handle_damage(
            {"amount": 10, "target": "self", "save": {"stat": "DEX", "dc": 30}},
            {},
            game_state=gs,
        )
        assert hero.vitals["HP"] == 40
        assert any("fails to resist" in line for line in out)

    def test_damage_save_skill_based(self, effects, hero):
        """The save can roll a skill (e.g. Acrobatics to dodge a trap)."""
        hero.skills["Acrobatics"] = 10
        gs = FakeGameState(hero)
        out = effects.handle_damage(
            {"amount": 8, "target": "self",
             "save": {"skill": "Acrobatics", "dc": 10}},
            {},
            game_state=gs,
        )
        assert hero.vitals["HP"] == 46  # 8 // 2 = 4
        assert any("[Save] Acrobatics vs DC 10" in line for line in out)

    def test_damage_named_target(self, effects, hero):
        """target can name an explicit character."""
        from player import Player
        guard = Player("Guard")
        guard.vitals["HP"] = 30
        gs = FakeGameState(hero, {"Hero": hero, "Guard": guard})
        out = effects.handle_damage({"amount": 6, "target": "Guard"}, {}, game_state=gs)
        assert guard.vitals["HP"] == 24
        assert any("Guard takes 6 damage" in line for line in out)

    def test_damage_no_resolvable_target(self, effects, hero):
        """Unknown target → no output, no crash."""
        gs = FakeGameState(hero)
        out = effects.handle_damage({"amount": 6, "target": "Ghost"}, {}, game_state=gs)
        assert out == []
        assert hero.vitals["HP"] == 50

    def test_damage_save_halves_odd_amounts(self, effects, hero):
        """Halving rounds down (floor division)."""
        hero.stats["DEX"] = 20  # always passes DC 5
        gs = FakeGameState(hero)
        out = effects.handle_damage(
            {"amount": 5, "target": "self", "save": {"stat": "DEX", "dc": 5}},
            {},
            game_state=gs,
        )
        assert hero.vitals["HP"] == 48  # 5 // 2 = 2

    def test_damage_save_halves_tiny_amount_to_zero(self, effects, hero):
        """amount 1 halved → 0 → reported as avoided."""
        hero.stats["DEX"] = 20
        gs = FakeGameState(hero)
        out = effects.handle_damage(
            {"amount": 1, "target": "self", "save": {"stat": "DEX", "dc": 5}},
            {},
            game_state=gs,
        )
        assert hero.vitals["HP"] == 50
        assert any("avoids the damage entirely" in line for line in out)

    def test_damage_save_unknown_on_success_treated_as_half(self, effects, hero):
        """A bogus on_success value falls back to halving."""
        hero.stats["DEX"] = 20
        gs = FakeGameState(hero)
        out = effects.handle_damage(
            {"amount": 10, "target": "self",
             "save": {"stat": "DEX", "dc": 5, "on_success": "absolutely"}},
            {},
            game_state=gs,
        )
        assert hero.vitals["HP"] == 45  # halved, not avoided

    def test_damage_other_with_character_name_and_save(self, effects, hero):
        """target='other' + character_name applies the save to that NPC."""
        from player import Player
        guard = Player("Guard")
        guard.vitals["HP"] = 30
        guard.stats["DEX"] = 20  # always passes DC 5
        gs = FakeGameState(hero, {"Hero": hero, "Guard": guard})
        out = effects.handle_damage(
            {"amount": 8, "target": "other", "character_name": "Guard",
             "save": {"stat": "DEX", "dc": 5}},
            {},
            game_state=gs,
        )
        assert guard.vitals["HP"] == 26  # 8 // 2 = 4
        assert any("[Save] DEX vs DC 5" in line for line in out)
        assert any("Guard takes 4 damage" in line for line in out)

    def test_damage_self_with_no_active_player(self, effects, hero):
        """game_state.player is None → no crash, no output."""
        gs = FakeGameState(hero)
        gs.player = None
        out = effects.handle_damage({"amount": 6, "target": "self"}, {}, game_state=gs)
        assert out == []


class TestSaveEffect:
    """handle_save — a generic save gate running sub-effects on fail/success."""

    def test_failed_save_runs_on_fail(self, effects, hero):
        hero.stats["WIS"] = 3  # mod -3, max total 17 < DC 30 → fail
        gs = FakeGameState(hero)
        out = effects.handle_save(
            {"stat": "WIS", "dc": 30, "on_fail": [
                {"type": "apply_condition", "params": {
                    "condition": "frightened", "duration": 4, "source_type": "way"}}
            ], "on_success": []},
            {}, item_node=None, game_state=gs,
        )
        assert any("[Save] WIS vs DC 30" in line for line in out)
        assert gs.conditions.applied
        _, cond, kw = gs.conditions.applied[0]
        assert cond == "frightened"
        assert kw["duration"] == 4
        assert kw["source_type"] == "way"

    def test_successful_save_runs_on_success(self, effects, hero):
        hero.stats["WIS"] = 20  # mod +5, DC 5 always passes
        gs = FakeGameState(hero)
        out = effects.handle_save(
            {"stat": "WIS", "dc": 5,
             "on_fail": [{"type": "apply_condition", "params": {"condition": "frightened"}}],
             "on_success": [{"type": "message", "params": {"message": "You steel yourself."}}]},
            {}, item_node=None, game_state=gs,
        )
        assert any("You steel yourself." in line for line in out)
        assert gs.conditions.applied == []

    def test_source_defaults_to_item_node_name(self, effects, hero):
        """apply_condition inside a save gate picks up the way/item name."""
        from graph import Node
        hero.stats["WIS"] = 3
        gs = FakeGameState(hero)
        orifice = Node(id="way_orifice", type="way", name="fleshy orifice", properties={})
        out = effects.handle_save(
            {"stat": "WIS", "dc": 30, "on_fail": [
                {"type": "apply_condition", "params": {
                    "condition": "frightened", "source_type": "way"}}],
             "on_success": []},
            {}, item_node=orifice, game_state=gs,
        )
        _, cond, kw = gs.conditions.applied[0]
        assert cond == "frightened"
        assert kw["source"] == "fleshy orifice"


class TestParameterEffects:
    """handle_set_parameter / handle_adjust_parameter mutate node parameters."""

    def _door(self, graph, node_id="way_door", name="Door"):
        from graph import Node
        node = Node(id=node_id, type="way", name=name, properties={})
        graph.add_node(node)
        return node

    def test_set_parameter_writes_parameters(self, effects):
        node = self._door(effects.graph)
        out = effects.handle_set_parameter(
            {"key": "light", "value": "green", "node_id": "way_door"}, {},
            item_node=None,
        )
        assert node.properties["parameters"]["light"] == "green"
        assert any("light" in line for line in out)

    def test_set_parameter_targets_self(self, effects):
        node = self._door(effects.graph, node_id="way_self", name="Self")
        effects.handle_set_parameter(
            {"key": "light", "value": "red", "node_id": "self"},
            {}, item_node=node,
        )
        assert node.properties["parameters"]["light"] == "red"

    def test_adjust_parameter_delta(self, effects):
        node = self._door(effects.graph)
        node.properties["parameters"] = {"charges": 3}
        effects.handle_adjust_parameter(
            {"key": "charges", "delta": -1, "node_id": "way_door"}, {},
            item_node=None,
        )
        assert node.properties["parameters"]["charges"] == 2

    def test_adjust_parameter_defaults_zero(self, effects):
        node = self._door(effects.graph, node_id="way_door2")
        effects.handle_adjust_parameter(
            {"key": "count", "delta": 5, "node_id": "way_door2"}, {},
            item_node=None,
        )
        assert node.properties["parameters"]["count"] == 5

    def test_set_parameter_targets_any_node_type(self, effects):
        """Works on areas/items too via _resolve_effect_target."""
        from graph import Node
        area = Node(id="area_kitchen", type="area", name="Kitchen", properties={})
        effects.graph.add_node(area)
        effects.handle_set_parameter(
            {"key": "flooded", "value": "true", "node_id": "area_kitchen"}, {},
            item_node=None,
        )
        assert area.properties["parameters"]["flooded"] == "true"
