"""Tests for simple NPC behavior processing."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from area import Area
from player import Player
from virtual_world_engine import VirtualWorld


def _make_rat_world():
    world = VirtualWorld()
    rat = Player("rat")
    rat.simple_npc = True
    rat.current_area = "Kitchen"
    rat.npc_state = "idle"
    rat.behaviors = [
        {
            "trigger": "on_tick",
            "priority": 5,
            "interval": 1,
            "conditions": {},
            "actions": [
                {"type": "set_npc_state", "state": "foraging"},
                {"type": "message", "text": "sniff"},
            ],
        }
    ]
    world.players["rat"] = rat
    world.time_ticks = 1
    return world, rat


@pytest.fixture
def patrol_world():
    """Two-room world with a simple NPC for movement tests."""
    world = VirtualWorld()
    world.movement.add_area(Area("Kitchen", "Kitchen.", []))
    world.movement.add_area(Area("Cellar", "Cellar.", []))
    world.movement.connect_areas("Kitchen", "Cellar", "trapdoor", "ladder", state="open")

    rat = Player("rat")
    rat.simple_npc = True
    rat.current_area = "Kitchen"
    world.players["rat"] = rat
    world.time_ticks = 1
    return world, rat


def test_behavior_actions_require_game_state():
    """Regression: behavior actions must receive game_state or they no-op."""
    world, rat = _make_rat_world()
    world.npc_behaviors.process_simple_npcs("on_tick")
    assert rat.npc_state == "foraging"


def test_random_chance_accepts_fractional_chance_field():
    """NPC behaviors use chance 0.0–1.0, not 0–100."""
    from engine.trigger_system import TriggerSystem
    from unittest.mock import MagicMock

    triggers = TriggerSystem(MagicMock(), MagicMock(), MagicMock())
    condition = {"type": "random_chance", "chance": 0.35}
    hits = sum(
        1
        for _ in range(200)
        if triggers._evaluate_conditions(condition, {})
    )
    assert hits > 20, f"expected ~35% hit rate, got {hits}/200"


def test_rat_template_behaviors_parse():
    """world_template rat has a non-empty scripted behavior tree."""
    import json

    template_path = Path(__file__).resolve().parent.parent / "world_template.json"
    data = json.loads(template_path.read_text(encoding="utf-8"))
    rat = data["players"]["rat"]
    assert rat["simple_npc"] is True
    assert len(rat["behaviors"]) >= 8
    assert rat["npc_behavior"] == "stationary"


def test_go_goto_moves_one_step_via_way(patrol_world):
    world, rat = patrol_world
    msg = world.npc_behaviors.execute_go_action(
        "rat", {"mode": "goto", "area": "Cellar"}
    )
    assert rat.current_area == "Cellar"
    assert "trapdoor" in msg or "→" in msg


def test_go_random_picks_open_exit(patrol_world):
    world, rat = patrol_world
    msg = world.npc_behaviors.execute_go_action("rat", {"mode": "random"})
    assert rat.current_area == "Cellar"
    assert "wanders" in msg


def test_go_patrol_cycles_route(patrol_world):
    world, rat = patrol_world
    action = {"mode": "patrol", "areas": "Kitchen, Cellar"}
    msg1 = world.npc_behaviors.execute_go_action("rat", action)
    assert rat.current_area == "Kitchen"
    assert rat.patrol_index == 1
    assert "patrol point" in msg1
    world.npc_behaviors.execute_go_action("rat", action)
    assert rat.current_area == "Cellar"
    assert rat.patrol_index == 0


def test_go_goto_blocked_by_locked_door():
    world = VirtualWorld()
    world.movement.add_area(Area("Kitchen", "Kitchen.", []))
    world.movement.add_area(Area("Cellar", "Cellar.", []))
    world.movement.connect_areas(
        "Kitchen", "Cellar", "trapdoor", "ladder", state="locked"
    )
    rat = Player("rat")
    rat.simple_npc = True
    rat.current_area = "Kitchen"
    world.players["rat"] = rat

    msg = world.npc_behaviors.execute_go_action(
        "rat", {"mode": "goto", "area": "Cellar"}
    )
    assert rat.current_area == "Kitchen"
    assert "cannot" in msg.lower()
