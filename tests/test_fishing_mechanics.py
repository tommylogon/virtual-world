"""Tests for task-716 fishing mechanics:
  - start_activity effect dispatch
  - fishing activity tick + biome resource sampling
  - activity pursuit step
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import json
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from graph import WorldGraph, Node, Edge, EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED
from player import Player
from engine.effects import Effects
from engine.activities import ActivitySystem
from engine.activities_loader import get as get_activity_def
from engine.pursuit_templates import load as load_templates, ALLOWED_STEP_KINDS
from engine.background_plans import _satisfied as plan_satisfied, _run as plan_run, build_plan


# ──────────────────────────────────────────────────────────────────────────────
# start_activity effect dispatch
# ──────────────────────────────────────────────────────────────────────────────

class FakeConditions:
    def __init__(self):
        self.applied = []

    def apply_condition(self, player_name, condition, **kwargs):
        self.applied.append((player_name, condition, kwargs))

    def remove_condition(self, player_name, condition):
        pass


class FakeActivities:
    def __init__(self):
        self.started = []

    def start_activity(self, player_name, activity_type, target_item=None,
                       duration_ticks=None, **kwargs):
        self.started.append((player_name, activity_type, target_item, duration_ticks, kwargs))
        return f"You start {activity_type}."


class FakeGameState:
    def __init__(self, player):
        self.player = player
        self.players = {player.name: player}
        self.active_player = player.name
        self.conditions = FakeConditions()
        self.activities = FakeActivities()


def _make_world_with_effects():
    g = WorldGraph()
    g.add_node(Node(id="area_river", type="area", name="Raven River",
                    properties={"tags": ["river"]}))
    g.add_node(Node(id="player_Hero", type="character", name="Hero",
                    properties={}))
    g.add_edge(Edge(source="player_Hero", target="area_river", type=EDGE_IN))
    hero = Player("Hero")
    hero.current_area = "Raven River"
    hero.activity = None
    hero.state = "awake"
    gs = FakeGameState(hero)
    logger = MagicMock()
    effects = Effects(g, logger)
    return effects, gs, hero


def test_start_activity_effect_dispatches():
    effects, gs, hero = _make_world_with_effects()
    out = effects.handle_start_activity(
        {"activity_type": "fishing", "target_item": "river", "duration_ticks": 60},
        {},
        game_state=gs,
    )
    assert out == ["You start fishing."]
    assert len(gs.activities.started) == 1
    assert gs.activities.started[0][1] == "fishing"
    assert gs.activities.started[0][2] == "river"


def test_start_activity_effect_resolves_target_player():
    effects, gs, hero = _make_world_with_effects()
    out = effects.handle_start_activity(
        {"activity_type": "fishing", "target": "Hero"},
        {},
        game_state=gs,
    )
    assert out == ["You start fishing."]
    assert gs.activities.started[0][0] == "Hero"


def test_start_activity_effect_target_entrant_from_context():
    effects, gs, hero = _make_world_with_effects()
    out = effects.handle_start_activity(
        {"activity_type": "fishing", "target": "target"},
        {"target_name": "Hero"},
        game_state=gs,
    )
    assert out == ["You start fishing."]
    assert gs.activities.started[0][0] == "Hero"


# ──────────────────────────────────────────────────────────────────────────────
# Fishing activity tick + biome sampling
# ──────────────────────────────────────────────────────────────────────────────

_FISHING_ITEM = json.dumps({
    "id": "test_fish",
    "name": "Test Fish",
    "tags": ["fish", "creel_catch"],
    "description": "A test fish.",
    "actions": "examine,take",
    "uses": -1,
    "weight": 0.1,
    "current_state": "normal",
    "quantity": 1,
    "plural": "fish",
})


@pytest.fixture
def _make_world_with_fishing():
    g = WorldGraph()
    g.add_node(Node(id="area_river", type="area", name="Raven River",
                    properties={"tags": ["river"]}))
    g.add_node(Node(id="player_Hero", type="character", name="Hero",
                    properties={}))
    g.add_node(Node(id="creel_Hero", type="item", name="creel",
                    properties={"tags": ["container", "creel"]}))
    g.add_edge(Edge(source="player_Hero", target="area_river", type=EDGE_IN))
    g.add_edge(Edge(source="creel_Hero", target="player_Hero", type=EDGE_CARRYING))

    hero = Player("Hero")
    hero.current_area = "Raven River"
    hero.activity = None
    hero.state = "busy"
    hero.equipped = {
        "torso": [], "head": [], "legs": [], "arms": [],
        "hands": [], "feet": [], "back": [], "neck": [], "waist": [], "accessory": [],
        "hand_left": [], "hand_right": [],
    }

    lib_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "library", "items",
    )
    fish_path = os.path.join(lib_dir, "test_fish.json")
    if not os.path.exists(fish_path):
        with open(fish_path, "w", encoding="utf-8") as f:
            f.write(_FISHING_ITEM)

    w = MagicMock()
    w.graph = g
    w.player_manager = MagicMock()
    w.player_manager.players = {"Hero": hero}
    w.player_manager.active_player = "Hero"
    w.player_manager.current_area = MagicMock()
    w.player_manager.current_area.name = "Raven River"
    w.player_manager.get_player_node_id = lambda name: f"player_{name}"
    w.game_logger = MagicMock()
    w.time_ticks = 0
    w.area_node_id = lambda name: "area_river"
    w.add_log_entry = MagicMock()
    w.activities = ActivitySystem(w)
    w.skills = MagicMock()
    w.skills.saving_throw = MagicMock(return_value=(True, 15, ""))

    yield w, hero

    if os.path.exists(fish_path):
        os.remove(fish_path)


def test_fishing_ticks_and_catches(_make_world_with_fishing):
    world, hero = _make_world_with_fishing
    world.activities.start_activity("Hero", "fishing", duration_ticks=20)
    assert hero.activity["type"] == "fishing"
    assert hero.activity.get("catch_count", 0) == 0

    for _ in range(5):
        out = world.activities.tick_activity("Hero")
        assert hero.activity.get("type") == "fishing"


def test_fishing_activity_is_interruptible():
    definition = get_activity_def("fishing") or {}
    assert definition.get("interruptible") is True


def test_fishing_activity_blocks_turns():
    definition = get_activity_def("fishing") or {}
    assert definition.get("blocks_turns") is True


# ──────────────────────────────────────────────────────────────────────────────
# pursuit activity step
# ──────────────────────────────────────────────────────────────────────────────

def test_pursuit_template_allows_activity_step():
    assert "activity" in ALLOWED_STEP_KINDS


def _make_sim(world, player):
    sim = MagicMock()
    sim.gs = world
    sim._travel_to_area = MagicMock(return_value=True)
    sim._travel_toward = MagicMock(return_value=True)
    sim._carried_nodes = MagicMock(return_value=[])
    sim._spatial_items = MagicMock(return_value=[])
    sim._areas_with = MagicMock(return_value=[])
    sim._target_step = MagicMock(return_value=None)
    sim.gs.area_node_id = lambda name: name
    return sim


def test_pursuit_activity_step_starts_fishing(_make_world_with_fishing):
    world, hero = _make_world_with_fishing
    hero.activity = None
    world.activities = MagicMock()
    world.activities.start_activity = MagicMock(
        return_value="You start fishing."
    )
    world.area_node_id = lambda name: name

    plan = {
        "node_id": "pursuit_1",
        "pursuit_template": "fish-and-bring-home",
        "label": "fish_run",
        "steps": [
            {"kind": "activity", "activity": "fishing", "catch_count_target": 10},
        ],
        "index": 0,
    }
    step = plan["steps"][0]
    sim = _make_sim(world, hero)
    assert plan_satisfied(sim, hero, step) is False
    outcome = plan_run(sim, hero, plan, step)
    assert outcome is None
    world.activities.start_activity.assert_called_once_with(
        "Hero", "fishing", None, None, catch_count_target=10,
    )


def test_pursuit_activity_step_waits_while_running(_make_world_with_fishing):
    world, hero = _make_world_with_fishing
    hero.activity = {"type": "fishing", "catch_count": 0}
    plan = {
        "node_id": "pursuit_1",
        "pursuit_template": "fish-and-bring-home",
        "label": "fish_run",
        "steps": [
            {"kind": "activity", "activity": "fishing", "catch_count_target": 10},
        ],
        "index": 0,
    }
    step = plan["steps"][0]
    sim = _make_sim(world, hero)
    assert plan_satisfied(sim, hero, step) is False
    outcome = plan_run(sim, hero, plan, step)
    assert outcome is None


def test_pursuit_activity_step_satisfied_on_completion(_make_world_with_fishing):
    world, hero = _make_world_with_fishing
    hero.activity = {"type": "fishing", "catch_count": 10}
    plan = {
        "node_id": "pursuit_1",
        "pursuit_template": "fish-and-bring-home",
        "label": "fish_run",
        "steps": [
            {"kind": "activity", "activity": "fishing", "catch_count_target": 10},
        ],
        "index": 0,
    }
    step = plan["steps"][0]
    sim = _make_sim(world, hero)
    assert plan_satisfied(sim, hero, step) is True
