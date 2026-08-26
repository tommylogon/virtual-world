"""Tests for the persistent activity system (task-131)."""
import pytest
from unittest.mock import MagicMock

from graph import WorldGraph, Node, Edge, EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED
from player import Player
from engine.activities import (
    ActivitySystem, activity_description, pile_node_id,
)


@pytest.fixture
def world():
    g = WorldGraph()
    g.add_node(Node(id="area_test", type="area", name="Test", properties={}))
    g.add_node(Node(id="player_Hero", type="character", name="Hero", properties={}))

    hero = Player("Hero")
    hero.current_area = "Test"
    hero.equipped = {
        "torso": [], "head": [], "legs": [], "arms": [],
        "hands": [], "feet": [], "back": [], "neck": [], "waist": [], "accessory": [],
        "hand_left": [], "hand_right": [],
    }

    pm = MagicMock()
    pm.players = {"Hero": hero}
    pm.active_player = "Hero"
    pm.current_area = MagicMock()
    pm.current_area.name = "Test"
    pm.get_player_node_id = lambda name: f"player_{name}"

    w = MagicMock()
    w.graph = g
    w.player_manager = pm
    w.game_logger = MagicMock()
    w.time_ticks = 0
    w.area_node_id = lambda name: "area_test"
    w.add_log_entry = MagicMock()
    w.skills = MagicMock()
    w.skills.saving_throw = MagicMock(return_value=(True, 15, "[Save] WIS vs DC 10: 15 => success"))
    w.equip_item = MagicMock(return_value="You equip the item.")
    w._execute_triggers = MagicMock(return_value=[])
    w.players = pm.players

    asys = ActivitySystem(w)
    w.activities = asys
    return w


def add_equipped(w, name, slot="torso"):
    g = w.graph
    item = Node(id=f"item_{name}", type="item", name=name, properties={
        "name": name, "tags": ["clothing"], "current_state": "normal",
        "actions": ["examine", "take", "use", "equip", "unequip"],
        "equip_slots": [slot],
    })
    g.add_node(item)
    g.add_edge(Edge(source=item.id, target="player_Hero", type=EDGE_EQUIPPED, properties={"slot": slot}))
    w.player_manager.players["Hero"].equipped[slot].append(item.id)
    return item


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ lifecycle â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_start_sleeping_sets_activity_and_state(world):
    out = world.activities.start_activity("Hero", "sleeping", "bed")
    assert "sleeping" in out
    hero = world.player_manager.players["Hero"]
    assert hero.activity["type"] == "sleeping"
    assert hero.activity["target_item"] == "bed"
    # sleep = an activity that applies unconsciousness
    assert hero.has_condition("unconscious")
    assert hero.state == "unconscious"
    world.game_logger.record_turn_event.assert_called()


def test_start_resting_sets_busy_state(world):
    world.activities.start_activity("Hero", "resting")
    assert world.player_manager.players["Hero"].state == "busy"


def test_start_sitting_sets_busy_state(world):
    world.activities.start_activity("Hero", "sitting")
    hero = world.player_manager.players["Hero"]
    assert hero.state == "busy"
    assert hero.activity["type"] == "sitting"


def test_start_rejects_when_already_active(world):
    world.activities.start_activity("Hero", "resting")
    with pytest.raises(ValueError):
        world.activities.start_activity("Hero", "sleeping")


def test_start_rejects_dead(world):
    world.player_manager.players["Hero"].state = "dead"
    with pytest.raises(ValueError):
        world.activities.start_activity("Hero", "resting")


def test_end_activity_resets_state(world):
    world.activities.start_activity("Hero", "sleeping")
    world.activities.end_activity("Hero")
    hero = world.player_manager.players["Hero"]
    assert hero.activity is None
    assert hero.state == "awake"


def test_interrupt_activity(world):
    world.activities.start_activity("Hero", "resting")
    out = world.activities.interrupt_activity("Hero")
    assert "stop" in out
    assert world.player_manager.players["Hero"].activity is None


def test_activity_description():
    # Open-ended activities now say so (task-339 feedback round)
    assert activity_description({"type": "sleeping", "target_item": "bed"}) == "sleeping in the bed (until woken)"
    assert activity_description({"type": "sitting"}) == "sitting (until woken)"
    assert activity_description(None) == ""


def test_activity_description_shows_remaining_or_open_end():
    # Timed activity: remaining ticks visible (task feedback â€” "when will
    # she stop resting?")
    assert activity_description(
        {"type": "resting", "duration_ticks": 10, "elapsed_ticks": 4}
    ) == "resting, 6 ticks left"
    assert activity_description(
        {"type": "resting", "duration_ticks": 10, "elapsed_ticks": 9}
    ) == "resting, 1 tick left"
    assert activity_description(
        {"type": "resting", "duration_ticks": 10, "elapsed_ticks": 40}
    ) == "resting, 0 ticks left"
    # Open-ended activity says so explicitly
    assert activity_description({"type": "resting"}) == "resting (until woken)"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ per-tick progress â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_sleeping_wakes_when_energy_full(world):
    hero = world.player_manager.players["Hero"]
    hero.vitals["Energy"] = 100
    world.activities.start_activity("Hero", "sleeping")
    world.activities.tick_activity("Hero")
    assert hero.activity is None
    assert hero.state == "awake"


def test_sleeping_duration_wakes(world):
    hero = world.player_manager.players["Hero"]
    hero.vitals["Energy"] = 50
    world.activities.start_activity("Hero", "sleeping", None, duration_ticks=2)
    world.activities.tick_activity("Hero")
    assert hero.activity is not None
    world.activities.tick_activity("Hero")
    assert hero.activity is None


def test_resting_regen_energy(world):
    hero = world.player_manager.players["Hero"]
    hero.vitals["Energy"] = 40
    world.activities.start_activity("Hero", "resting")
    world.activities.tick_activity("Hero")
    assert hero.vitals["Energy"] == 42


def test_meditating_regen_sanity(world):
    hero = world.player_manager.players["Hero"]
    hero.vitals["Sanity"] = 30
    world.activities.start_activity("Hero", "meditating")
    world.activities.tick_activity("Hero")
    assert hero.vitals["Sanity"] == 32


def test_tick_clears_activity_when_dead(world):
    hero = world.player_manager.players["Hero"]
    world.activities.start_activity("Hero", "resting")
    hero.state = "dead"
    world.activities.tick_activity("Hero")
    assert hero.activity is None


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ wake â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_wake_sleeper(world):
    world.activities.start_activity("Hero", "sleeping")
    out = world.activities.wake("Hero")
    assert "wake" in out
    assert world.player_manager.players["Hero"].activity is None
    assert world.player_manager.players["Hero"].state == "awake"


def test_wake_non_sleeper_raises(world):
    with pytest.raises(ValueError):
        world.activities.wake("Hero")


def test_wake_on_damage_sleeper(world):
    world.activities.start_activity("Hero", "sleeping")
    out = world.activities.wake_on_damage("Hero")
    assert "awake" in out
    assert world.player_manager.players["Hero"].activity is None


def test_wake_on_damage_interrupts_resting(world):
    world.activities.start_activity("Hero", "resting")
    world.activities.wake_on_damage("Hero")
    assert world.player_manager.players["Hero"].activity is None


def test_wake_on_noise_success(world):
    world.activities.start_activity("Hero", "sleeping")
    out = world.activities.wake_on_noise("Hero")
    assert out and "awake" in out
    assert world.player_manager.players["Hero"].activity is None


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ strip / dress / piles â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_strip_to_pile_creates_pile(world):
    add_equipped(world, "shirt", "torso")
    add_equipped(world, "pants", "legs")
    out = world.activities.strip_to_pile("Hero")
    assert "pile" in out
    g = world.graph
    pile = g.get_node(pile_node_id("Hero"))
    assert pile is not None
    assert "container" in pile.properties["tags"]
    assert "clothing_pile" in pile.properties["tags"]
    contents = {e.source for e in g.get_edges_for_target(pile.id, EDGE_IN)}
    assert "item_shirt" in contents and "item_pants" in contents
    # equipped edges gone, stacks cleared
    assert g.get_edges_for_target("player_Hero", EDGE_EQUIPPED) == []
    hero = world.player_manager.players["Hero"]
    assert all(stack == [] for stack in hero.equipped.values())


def test_strip_wearing_nothing_raises(world):
    with pytest.raises(ValueError):
        world.activities.strip_to_pile("Hero")


def test_dress_from_pile_re_equips(world):
    add_equipped(world, "shirt", "torso")
    world.activities.strip_to_pile("Hero")
    out = world.activities.dress_from_pile("Hero")
    assert "shirt" in out
    g = world.graph
    pile = g.get_node(pile_node_id("Hero"))
    assert pile is None  # pile removed when emptied
    carrying = {e.source for e in g.get_edges_for_target("player_Hero", EDGE_CARRYING)}
    assert "item_shirt" in carrying


def test_dress_no_pile_raises(world):
    with pytest.raises(ValueError):
        world.activities.dress_from_pile("Hero")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ bathe chain â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_bathe_strips_then_activity(world):
    add_equipped(world, "shirt", "torso")
    out = world.activities.bathe("Hero", "bath")
    assert "pile" in out and "bathing" in out
    hero = world.player_manager.players["Hero"]
    assert hero.activity["type"] == "bathing"
    assert hero.state == "busy"
    assert world.graph.get_node(pile_node_id("Hero")) is not None


def test_bathing_finishes_and_auto_dresses(world):
    hero = world.player_manager.players["Hero"]
    hero.vitals["Hygiene"] = 100
    world.activities.start_activity("Hero", "bathing", "bath")
    out = world.activities.tick_activity("Hero")
    assert hero.activity is None
    assert hero.state == "awake"
    assert "bathing" in (out or "")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ real-engine integration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_integration_rest_persists_across_ticks():
    """rest no longer fast-forwards: the activity persists and regens per tick."""
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    player = world.player_manager.get_player(world.active_player)
    player.vitals["Energy"] = 40

    out = world.rest(30)
    assert "resting" in out
    assert player.activity["type"] == "resting"
    assert player.state == "busy"
    assert world.time_ticks == 0  # clock NOT advanced by the command itself

    world.tick_turn()
    assert player.activity is not None  # still resting
    assert world.time_ticks == 1
    assert player.vitals["Energy"] == 41  # decay -1 + regen +2 = net +1


def test_integration_sleep_wakes_via_command():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    player = world.player_manager.get_player(world.active_player)
    player.vitals["Energy"] = 30

    world.sleep(None, "bed")
    assert player.activity["type"] == "sleeping"
    assert player.has_condition("unconscious")  # sleep = an unconscious instance
    assert player.state == "unconscious"
    # Only the activity's own state matters - clock is untouched by sleep itself
    assert world.time_ticks == 0

    world.tick_turn()
    assert player.activity is not None
    assert player.vitals["Energy"] == 32  # decay -1 + sleeping +3

    out = world.wake()
    assert player.activity is None
    assert player.state == "awake"
    assert "wake" in out


def test_integration_activity_survives_save_round_trip():
    """Activity persists through world serialization (to_dict/load)."""
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    player = world.player_manager.get_player(world.active_player)
    world.sleep(None, "bed")
    assert player.activity["type"] == "sleeping"

    data = world.to_dict()
    # players serialize via serializer; verify activity is present in the dump
    players = data.get("players") or {}
    assert players[world.active_player].get("activity", {}).get("type") == "sleeping"

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ wake covers all activities â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def test_wake_stops_resting_activity(world):
    """'wake' on a resting character stops the activity (task feedback:
    'miki doki isn't sleeping' while she was resting)."""
    world.activities.start_activity("Hero", "resting")
    result = world.activities.wake("Hero")
    assert "stop resting" in result
    assert world.activities.get_activity("Hero") is None


def test_wake_other_character_stops_their_activity(world):
    world.activities.start_activity("Hero", "waiting")
    result = world.activities.wake("Hero", waker_name="Someone Else")
    assert "stop waiting" in result
    assert world.activities.get_activity("Hero") is None


def test_wake_with_no_activity_raises():
    world = _bare_world()
    with pytest.raises(ValueError, match="isn't sleeping or busy"):
        world.activities.wake("Hero")


def test_rest_default_duration_survives_none_minutes():
    """A bare 'rest' command passes minutes=None explicitly — the 10-minute
    default must survive (miki rested with no set end)."""
    from virtual_world_engine import VirtualWorld

    world = _bare_world()
    world.time_per_tick_minutes = 5
    VirtualWorld.rest(world)  # unbound: route calls rest(None) today
    activity = world.activities.get_activity("Hero")
    assert activity is not None
    assert activity["duration_ticks"] == 2  # 10 min / 5 min per tick


def _bare_world():
    """Minimal harness: real ActivitySystem over mock player manager."""
    g = WorldGraph()
    g.add_node(Node(id="area_test", type="area", name="Test", properties={}))
    hero = Player("Hero")
    hero.current_area = "Test"
    pm = MagicMock()
    pm.players = {"Hero": hero}
    pm.active_player = "Hero"
    pm.current_area = MagicMock()
    pm.current_area.name = "Test"
    pm.get_player_node_id = lambda name: f"player_{name}"
    w = MagicMock()
    w.graph = g
    w.player_manager = pm
    w.active_player = "Hero"
    w.time_per_tick_minutes = 5
    w._activity_duration_ticks = lambda minutes: None if not minutes else max(1, minutes // 5)
    w.game_logger = MagicMock()
    w.time_ticks = 0
    w.area_node_id = lambda name: "area_test"
    w.add_log_entry = MagicMock()
    w.skills = MagicMock()
    w.activities = ActivitySystem(w)
    return w
