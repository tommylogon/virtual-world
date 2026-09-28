"""Tests for world save/load round-trips (serialization)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.character_spatial import (
    apply_positional_fidelity,
    check_spatial_invariants,
    pool_remaining,
    select_area_anchors,
    set_character_position,
    spawn_from_pool,
)
from area import Area
from graph import EDGE_AT, EDGE_IN, Edge, Node
from virtual_world_engine import VirtualWorld


def _world_with_an_area(area_name="Round Trip Room"):
    """A bare VirtualWorld has no areas at all, so nothing spatial can exist yet."""
    world = VirtualWorld()
    if area_name not in getattr(world, "areas", {}):
        world.movement.add_area(Area(area_name, "a room.", []))
    return world


def test_the_at_edge_survives_save_load_roundtrip():
    """Positional detail is the fidelity budget, so losing it on reload would
    silently demote an attended character back to 'somewhere in the area'."""
    world = _world_with_an_area()
    pname = world.active_player
    pid = world.player_manager.get_player_node_id(pname)
    world.set_player_area(pname, "Round Trip Room")
    world.graph.add_node(Node(id="round_trip_boulder", type="item",
                              name="boulder", properties={}))

    set_character_position(world.graph, pid, "round_trip_boulder")
    assert world.get_current_area_id(), "the area was set, so the test is not vacuous"

    reloaded = VirtualWorld()
    reloaded.load_from_dict(world.to_scenario_dict())
    reloaded_pid = reloaded.player_manager.get_player_node_id(pname)
    targets = [e.target for e in reloaded.graph.get_edges_for_source(reloaded_pid, EDGE_AT)]
    assert targets == ["round_trip_boulder"]


def test_a_pooled_anchor_survives_save_load_and_keeps_depleting():
    """The remaining count is world state, not scenery: a reloaded pool must
    not hand back gravel that was already taken."""
    world = _world_with_an_area()
    pname = world.active_player
    world.set_player_area(pname, "Round Trip Room")
    area = world.get_current_area_id()
    world.graph.add_node(Node(
        id="round_trip_gravel", type="item", name="gravel",
        properties={"anchor_kind": "pooled", "anchor": True,
                    "pool": {"remaining": 5, "max_spawn": 2, "unit": "handful",
                             "item": {"name": "pebble"}}}))
    world.graph.add_edge(Edge(source="round_trip_gravel", target=area, type=EDGE_IN))
    spawn_from_pool(world.graph, world.graph.get_node("round_trip_gravel"), area)
    assert pool_remaining(world.graph.get_node("round_trip_gravel")) == 3

    reloaded = VirtualWorld()
    reloaded.load_from_dict(world.to_scenario_dict())
    pool = reloaded.graph.get_node("round_trip_gravel")
    assert pool_remaining(pool) == 3, "the pool did not refill on load"

    spawned = spawn_from_pool(reloaded.graph, pool, reloaded.get_current_area_id())
    assert len(spawned) == 2
    assert pool_remaining(pool) == 1


def test_the_anchor_budget_is_the_same_after_a_reload():
    """A budget that changed on save would make an area read differently
    depending on how it was loaded."""
    world = VirtualWorld()
    area = world.get_current_area_id()
    for i in range(12):
        world.graph.add_node(Node(
            id=f"budget_rock_{i:02d}", type="item", name=f"rock {i}",
            properties={"anchor": True}))
        world.graph.add_edge(Edge(source=f"budget_rock_{i:02d}", target=area, type=EDGE_IN))
    before = select_area_anchors(world.graph, area)

    reloaded = VirtualWorld()
    reloaded.load_from_dict(world.to_scenario_dict())
    assert select_area_anchors(reloaded.graph, reloaded.get_current_area_id()) == before


def test_a_reloaded_world_still_satisfies_the_spatial_invariants():
    world = VirtualWorld()
    pname = world.active_player
    pid = world.player_manager.get_player_node_id(pname)
    world.graph.add_node(Node(id="reload_boulder", type="item",
                              name="boulder", properties={}))
    set_character_position(world.graph, pid, "reload_boulder")

    reloaded = VirtualWorld()
    reloaded.load_from_dict(world.to_scenario_dict())
    assert check_spatial_invariants(reloaded.graph) == []


def test_positional_fidelity_applies_to_a_saved_world():
    """Attending a character is expressible in a scenario and survives it."""
    world = VirtualWorld()
    pid = world.player_manager.get_player_node_id(world.active_player)
    world.graph.add_node(Node(id="fid_boulder", type="item",
                              name="boulder", properties={}))
    result = apply_positional_fidelity(
        world.graph, {world.active_player: pid}, [world.active_player],
        anchor_for={world.active_player: "fid_boulder"})
    assert result["at_edges"] == 1

    reloaded = VirtualWorld()
    reloaded.load_from_dict(world.to_scenario_dict())
    rpid = reloaded.player_manager.get_player_node_id(world.active_player)
    assert [e.target for e in reloaded.graph.get_edges_for_source(rpid, EDGE_AT)] \
        == ["fid_boulder"]


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
