"""Tests for world save/load round-trips (serialization)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from virtual_world_engine import VirtualWorld


def test_player_tags_survive_save_load_roundtrip():
    """Player tags must survive a to_scenario_dict → load_from_dict cycle.
    Regression: load_from_dict never restored tags, so any world reload
    (restart, scenario load, reset) silently wiped character tags."""
    world = VirtualWorld()
    pname = world.active_player
    world.player_manager.get_player(pname).tags = ['female', 'magic']

    data = world.to_scenario_dict()
    assert data["players"][pname]["tags"] == ["female", "magic"]

    world2 = VirtualWorld()
    world2.load_from_dict(data)
    reloaded = world2.player_manager.get_player(pname)
    assert reloaded.tags == ["female", "magic"]


def test_player_tags_roundtrip_without_tags_field():
    """Characters with no tags field in the source data load with empty tags."""
    world = VirtualWorld()
    pname = world.active_player
    data = world.to_scenario_dict()
    data["players"][pname].pop("tags", None)

    world2 = VirtualWorld()
    world2.load_from_dict(data)
    assert world2.player_manager.get_player(pname).tags == []


def test_player_interest_tags_survive_save_load_roundtrip():
    """interest_tags must survive a to_scenario_dict → load_from_dict cycle."""
    world = VirtualWorld()
    pname = world.active_player
    world.player_manager.get_player(pname).interest_tags = ['magic', 'documents']

    data = world.to_scenario_dict()
    assert data["players"][pname]["interest_tags"] == ["magic", "documents"]

    world2 = VirtualWorld()
    world2.load_from_dict(data)
    assert world2.player_manager.get_player(pname).interest_tags == ["magic", "documents"]


def test_condition_instances_survive_save_load_roundtrip():
    """Per-condition instances (durations/sources/overrides) survive a
    save/load cycle — including MULTIPLE stacked instances per condition."""
    world = VirtualWorld()
    pname = world.active_player
    player = world.player_manager.get_player(pname)
    player.add_condition("poisoned", duration=7, source="viper", periodic={"HP": -5})
    player.add_condition("poisoned", duration=4, source="rat")
    player.add_condition("mute")

    data = world.to_scenario_dict()
    saved = data["players"][pname]["conditions"]["poisoned"]
    assert isinstance(saved, list) and len(saved) == 2
    assert saved[0]["duration"] == 7
    assert saved[0]["source"] == "viper"
    assert saved[0]["periodic"] == {"HP": -5}
    assert "mute" in data["players"][pname]["conditions"]

    world2 = VirtualWorld()
    world2.load_from_dict(data)
    reloaded = world2.player_manager.get_player(pname)
    assert reloaded.has_condition("poisoned")
    assert len(reloaded.conditions["poisoned"]) == 2
    assert reloaded.conditions["poisoned"][0]["duration"] == 7
    assert reloaded.conditions["poisoned"][0]["source"] == "viper"
    assert reloaded.conditions["poisoned"][0]["periodic"] == {"HP": -5}
    assert reloaded.has_condition("mute")


def test_legacy_list_conditions_load():
    """Old saves with a list-of-strings conditions field still load."""
    world = VirtualWorld()
    pname = world.active_player
    data = world.to_scenario_dict()
    data["players"][pname]["conditions"] = ["awake", "poisoned", "blind"]

    world2 = VirtualWorld()
    world2.load_from_dict(data)
    reloaded = world2.player_manager.get_player(pname)
    assert set(reloaded.conditions) == {"awake", "poisoned", "blind"}
    assert reloaded.conditions["poisoned"][0]["duration"] == 10
