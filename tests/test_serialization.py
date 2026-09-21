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


def test_observation_memory_and_index_survive_save_load():
    """task-403: who/what/where/when and the subject index round-trip."""
    world = VirtualWorld()
    pname = world.active_player
    player = world.player_manager.get_player(pname)
    player.record_observation(
        "item_dried_meat", "You have seen Dried Meat in the Pantry.", 12,
        kind="item", tags=["food"], location="Pantry",
    )

    # A savegame, not a scenario: a scenario is authored content and strips
    # runtime perception (see test_a_scenario_save_carries_no_runtime_perception).
    data = world.to_dict()
    entry = data["players"][pname]["memory_index"]["item_dried_meat"]

    world2 = VirtualWorld()
    world2.load_from_dict(data)
    reloaded = world2.player_manager.get_player(pname)
    assert reloaded.memory_index["item_dried_meat"] == entry
    assert reloaded.has_seen("item_dried_meat")
    assert reloaded.observation_tick("item_dried_meat") == 12
    mem = reloaded.observation_memory("item_dried_meat")
    assert mem["entity_ids"] == ["item_dried_meat"]
    assert mem["location"] == "Pantry"
    assert mem["kind"] == "item"


def test_a_stale_index_entry_is_dropped_on_load():
    """A stored index must never point at a memory that is not there."""
    world = VirtualWorld()
    pname = world.active_player
    world.player_manager.get_player(pname).record_observation(
        "area_pantry", "You have been in the Pantry.", 3, kind="area")
    data = world.to_dict()
    data["players"][pname]["memory_index"]["area_ghost"] = "does_not_exist"

    world2 = VirtualWorld()
    world2.load_from_dict(data)
    reloaded = world2.player_manager.get_player(pname)
    assert "area_ghost" not in reloaded.memory_index
    assert reloaded.has_seen("area_pantry")


def test_a_superseded_observation_is_not_indexed_on_load():
    world = VirtualWorld()
    pname = world.active_player
    player = world.player_manager.get_player(pname)
    player.record_observation("item_bread", "You have seen Bread.", 1, kind="item")
    assert player.supersede_observation("item_bread", reason="eaten")

    data = world.to_dict()
    world2 = VirtualWorld()
    world2.load_from_dict(data)
    reloaded = world2.player_manager.get_player(pname)
    assert "item_bread" not in reloaded.memory_index
    assert not reloaded.has_seen("item_bread")


def test_index_is_rebuilt_for_a_save_written_before_the_index_existed():
    """Legacy saves carry observations with entity_ids but no memory_index."""
    world = VirtualWorld()
    pname = world.active_player
    player = world.player_manager.get_player(pname)
    player.record_observation("area_kitchen", "You have been in the Kitchen.", 2,
                              kind="area")
    data = world.to_dict()
    data["players"][pname].pop("memory_index", None)

    world2 = VirtualWorld()
    world2.load_from_dict(data)
    reloaded = world2.player_manager.get_player(pname)
    assert reloaded.has_seen("area_kitchen")
    assert reloaded.memory_index["area_kitchen"]


def test_the_starting_area_is_observed_at_load():
    """Nothing is observed without a move, so the starting area must be
    recorded at load — otherwise it is the one place a character can never
    remember, and novelty would pay for it again on the first re-entry."""
    from graph import Node

    world = VirtualWorld()
    pname = world.active_player
    world.graph.add_node(Node(id="area_pantry", type="area", name="Pantry"))
    world.player_manager.get_player(pname).current_area = "Pantry"

    data = world.to_scenario_dict()
    # Strip every memory: the only way the area can end up known is the load pass.
    for pdata in data["players"].values():
        pdata["memories"] = []
        pdata["memory_index"] = {}

    world2 = VirtualWorld()
    world2.load_from_dict(data)
    reloaded = world2.player_manager.get_player(pname)
    assert reloaded.current_area == "Pantry"
    assert reloaded.has_seen("area_pantry")
    assert reloaded.observation_tick("area_pantry") == data["time_ticks"]


def test_a_scenario_save_carries_no_runtime_perception():
    """Loading observes every character's starting area (task-403). Saving the
    scenario back must not bake that into the file: `_save_scenario` persists
    authorial content, and 23 characters' worth of "you have been in Blackmarsh"
    is runtime state the loader regenerates anyway (~60KB on the first save)."""
    from graph import Node

    world = VirtualWorld()
    pname = world.active_player
    world.graph.add_node(Node(id="area_pantry", type="area", name="Pantry"))
    player = world.player_manager.get_player(pname)
    player.current_area = "Pantry"
    player.add_memory("I was raised in the pantry.", 0, source="manual")
    player.record_observation("area_pantry", "You have been in the Pantry.", 0,
                              kind="area")

    scenario = world.to_scenario_dict()["players"][pname]
    assert [m["text"] for m in scenario["memories"]] == ["I was raised in the pantry."]
    assert "memory_index" not in scenario

    # A savegame is a complete snapshot, so it keeps both.
    savegame = world.to_dict()["players"][pname]
    assert len(savegame["memories"]) == 2
    assert savegame["memory_index"]["area_pantry"]
