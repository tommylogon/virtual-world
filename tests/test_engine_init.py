"""Tests that the VirtualWorld engine can be instantiated with default state."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from collections import deque
from virtual_world_engine import VirtualWorld
from player import Player


def test_virtual_world_creates():
    """A bare VirtualWorld can be instantiated."""
    world = VirtualWorld()
    assert world is not None
    assert hasattr(world, 'graph')


def test_default_player_exists():
    """VirtualWorld creates a default player in the player_manager."""
    world = VirtualWorld()
    assert world.active_player is not None
    # Players live in player_manager.players, not world.players
    assert world.active_player in world.player_manager.players


def test_default_player_is_awake():
    """Default player starts awake and with full vitals."""
    world = VirtualWorld()
    player = world.player_manager.get_player(world.active_player)
    assert player is not None
    assert player.state == "awake"
    assert player.vitals["HP"] == 100
    assert player.vitals["Energy"] == 100
    assert player.vitals["Hunger"] == 0  # drive (task-337): spawn satisfied
    assert player.vitals["Sanity"] == 100


def test_engine_has_all_subsystems():
    """VirtualWorld initialises every expected subsystem."""
    world = VirtualWorld()
    assert hasattr(world, 'triggers')
    assert hasattr(world, 'equipment')
    assert hasattr(world, 'combat')
    assert hasattr(world, 'movement')
    assert hasattr(world, 'item_actions')
    assert hasattr(world, 'player_manager')
    assert hasattr(world, 'narration')
    assert hasattr(world, 'tick_manager')
    assert hasattr(world, 'serializer')
    assert hasattr(world, 'game_logger')
    assert hasattr(world, 'lighting')
    assert hasattr(world, 'skills')
    assert hasattr(world, 'name_matcher')
    assert hasattr(world, 'npc_behaviors')
    assert hasattr(world, 'ghost_system')
    assert hasattr(world, 'toggleable_items')


def test_game_log_starts_with_welcome():
    """Initial game log contains welcome messages."""
    world = VirtualWorld()
    assert len(world.game_log) > 0
    welcome = any("Welcome" in entry for entry in world.game_log)
    assert welcome, "Expected welcome message in game log"


def test_player_serialization_includes_region_exposure():
    """Serialized players carry a computed per-region exposure map so the
    frontend never re-implements coverage logic (single source of truth)."""
    from engine.body_parts import is_exposed
    world = VirtualWorld()
    data = world.serializer.to_dict()
    player_name = world.active_player
    player = world.player_manager.get_player(player_name)
    payload = data["players"][player_name]
    assert "region_exposed" in payload
    assert set(payload["region_exposed"].keys()) == set(payload["body_region_names"].keys())
    for region_id, expected in payload["region_exposed"].items():
        assert payload["region_exposed"][region_id] == is_exposed(player, region_id, world.graph)


def test_engine_properties_forwarded():
    """Property forwarders for log_revision, turn_number, etc. work."""
    world = VirtualWorld()
    assert world.log_revision >= 0
    assert world.turn_number == 0
    assert isinstance(world.turn_events, list)
    assert isinstance(world.speech_log, deque)
    assert isinstance(world.game_log, list)


def test_add_player_creates_new_player():
    """Adding a player registers them and creates a graph node."""
    world = VirtualWorld()
    new_player = Player("TestHero")
    world.add_player(new_player)
    assert "TestHero" in world.player_manager.players
    player_node_id = "player_TestHero"
    player_node = world.graph.get_node(player_node_id)
    assert player_node is not None
    assert player_node.type == "character"


def test_engine_tick_advances_clock():
    """Calling tick() advances time_ticks."""
    world = VirtualWorld()
    initial_ticks = world.time_ticks
    world.tick(ticks=1)
    assert world.time_ticks == initial_ticks + 1


def test_engine_has_default_clock_time():
    """Engine starts at 08:00 by default."""
    world = VirtualWorld()
    time_string = world.get_current_time()
    assert ":" in time_string


def test_subgraph_add_area():
    """Adding a area creates the graph node and legacy compat area."""
    from area import Area
    world = VirtualWorld()
    area = Area("Test Chamber", "A sterile test chamber.", items=[])
    world.add_area(area)
    # NodeIDHelper normalises area names to lowercase
    area_node = world.graph.get_node("area_test_chamber")
    assert area_node is not None
    assert area_node.type == "area"
    assert "Test Chamber" in world.areas


def test_subgraph_connect_areas():
    """Connecting two areas creates door nodes with edges."""
    from area import Area
    world = VirtualWorld()
    world.add_area(Area("Alpha", "First area.", items=[]))
    world.add_area(Area("Beta", "Second area.", items=[]))
    world.connect_areas("Alpha", "Beta", "north", "south",
                        state="open", desc="A plain door.")

    way_id = "way_Alpha_north"
    way_node = world.graph.get_node(way_id)
    assert way_node is not None
    assert way_node.type == "way"
    assert way_node.properties.get("current_state") == "open"


def test_get_current_time_returns_formatted():
    """get_current_time() returns HH:MM format."""
    world = VirtualWorld()
    time_string = world.get_current_time()
    # The time includes seconds (HH:MM:SS), split on last separator
    assert ":" in time_string
    parts = time_string.split(":")
    assert len(parts) >= 2
    hour = int(parts[0])
    minute = int(parts[1])
    assert 0 <= hour <= 23
    assert 0 <= minute <= 59


def test_get_current_time_with_float_tick_minutes():
    """Fractional time_per_tick_minutes must not crash the clock formatter."""
    world = VirtualWorld()
    world.time_per_tick_minutes = 2.5
    world.tick(ticks=97)  # 242.5 minutes elapsed
    time_string = world.get_current_time()
    parts = time_string.split(":")
    assert len(parts) == 3
    hour, minute, second = int(parts[0]), int(parts[1]), int(parts[2])
    assert 0 <= hour <= 23
    assert 0 <= minute <= 59
    assert 0 <= second <= 59
    # 08:00 + 4h02m30s == 12:02:30
    assert time_string == "12:02:30"


def test_engine_can_advance_turn_number():
    """Adding entries to the game log works without crashing."""
    world = VirtualWorld()
    # turn_number starts at 0, clear_turn_events increments it
    world.clear_turn_events()
    assert world.turn_number == 1


def test_broadcast_speech_fires_on_speech_area_trigger():
    """Speaking in an area fires an on_speech trigger placed on that area.

    Password-door flow: a player in the room says the magic phrase, the
    area's on_speech trigger matches it and emits the result message.
    """
    from area import Area
    from graph import Node, Edge, EDGE_TRIGGERS
    world = VirtualWorld()
    world.add_area(Area("Throne Room", "A grand hall.", items=[]))

    player = world.player_manager.get_player(world.active_player)
    player.current_area = "Throne Room"

    area_node = world.graph.get_node("area_throne_room")

    trigger_node = Node(
        id="trigger_secret_word",
        type="logic_trigger",
        name="secret word → message",
        properties={
            "trigger_type": "on_speech",
            "effect_type": "message",
            "effect_params": {"message": "The wall grinds open!"},
            "conditions": [{"type": "speech_matches", "phrase": "open sesame", "mode": "contains"}],
        },
    )
    world.graph.add_node(trigger_node)
    world.graph.add_edge(Edge(
        source=area_node.id,
        target=trigger_node.id,
        type=EDGE_TRIGGERS,
        properties={
            "trigger_type": "on_speech",
            "conditions": [{"type": "speech_matches", "phrase": "open sesame", "mode": "contains"}],
            "effects": [{"type": "message", "params": {"message": "The wall grinds open!"}}],
        },
    ))

    world.broadcast_speech(world.active_player, "please open sesame for me")

    # The trigger output lands in the game log / turn events
    log_text = " ".join(world.game_log)
    assert "grinds open" in log_text


def test_broadcast_speech_ignores_wrong_phrase():
    """An on_speech trigger does not fire when the phrase does not match."""
    from area import Area
    from graph import Node, Edge, EDGE_TRIGGERS
    world = VirtualWorld()
    world.add_area(Area("Throne Room", "A grand hall.", items=[]))

    player = world.player_manager.get_player(world.active_player)
    player.current_area = "Throne Room"

    area_node = world.graph.get_node("area_throne_room")

    trigger_node = Node(
        id="trigger_secret_word2",
        type="logic_trigger",
        name="secret word → message",
        properties={
            "trigger_type": "on_speech",
            "effect_type": "message",
            "effect_params": {"message": "The wall grinds open!"},
            "conditions": [{"type": "speech_matches", "phrase": "open sesame", "mode": "contains"}],
        },
    )
    world.graph.add_node(trigger_node)
    world.graph.add_edge(Edge(
        source=area_node.id,
        target=trigger_node.id,
        type=EDGE_TRIGGERS,
        properties={
            "trigger_type": "on_speech",
            "conditions": [{"type": "speech_matches", "phrase": "open sesame", "mode": "contains"}],
            "effects": [{"type": "message", "params": {"message": "The wall grinds open!"}}],
        },
    ))

    world.broadcast_speech(world.active_player, "hello there")

    log_text = " ".join(world.game_log)
    assert "grinds open" not in log_text
