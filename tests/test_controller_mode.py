"""Verify the unified character controller mode and backward-compatible shims (task-437)."""

import pytest
from area import Area
from player import Player
from virtual_world_engine import VirtualWorld


def test_player_controller_modes_and_shims():
    """Verify that controller is the single authoritative source of truth on Player."""
    p = Player("TestActor")
    assert p.controller == "llm"
    assert p.control_mode == "llm"
    assert p.simple_npc is False
    assert p.autonomy is True

    # Human control
    p.controller = "human"
    assert p.controller == "human"
    assert p.simple_npc is False
    assert p.autonomy is False

    # Directed control
    p.controller = "directed"
    assert p.controller == "directed"
    assert p.simple_npc is False
    assert p.autonomy == "directed"

    # Scripted NPC
    p.controller = "npc"
    assert p.controller == "npc"
    assert p.simple_npc is True
    assert p.autonomy is True

    # Inert actor (e.g. test fixture isolation)
    p.controller = "inert"
    assert p.controller == "inert"
    assert p.simple_npc is True
    assert p.autonomy is False


def test_legacy_property_setters_update_controller():
    """Verify that assigning legacy simple_npc and autonomy fields maps to controller."""
    p = Player("TestActor")

    # autonomy = False makes it human
    p.autonomy = False
    assert p.controller == "human"

    # autonomy = "directed" makes it directed
    p.autonomy = "directed"
    assert p.controller == "directed"

    # simple_npc = True makes it npc
    p.simple_npc = True
    assert p.controller == "npc"
    assert p.autonomy is True

    # freezing an npc makes it inert
    p.autonomy = False
    assert p.controller == "inert"
    assert p.simple_npc is True
    assert p.autonomy is False

    # unfreezing an npc restores npc
    p.autonomy = True
    assert p.controller == "npc"
    assert p.simple_npc is True


def test_controller_mode_serialization_roundtrip():
    """Verify that controller survives world serialization and deserialization."""
    world = VirtualWorld()
    world.movement.add_area(Area("Town Square", "the town square.", []))

    # Add characters with distinct controllers
    chars = {
        "HumanHero": "human",
        "DirectedActor": "directed",
        "AutonomousBot": "llm",
        "TownGuard": "npc",
    }
    for name, mode in chars.items():
        p = Player(name)
        p.controller = mode
        world.add_player(p)
        world.set_player_area(name, "Town Square")

    payload = world.to_scenario_dict()

    for name, mode in chars.items():
        assert payload["players"][name]["controller"] == mode
        if mode == "human":
            assert payload["players"][name]["autonomy"] is False
            assert payload["players"][name]["simple_npc"] is False
        elif mode == "directed":
            assert payload["players"][name]["autonomy"] == "directed"
            assert payload["players"][name]["simple_npc"] is False
        elif mode == "llm":
            assert payload["players"][name]["autonomy"] is True
            assert payload["players"][name]["simple_npc"] is False
        elif mode == "npc":
            assert payload["players"][name]["autonomy"] is True
            assert payload["players"][name]["simple_npc"] is True

    reloaded = VirtualWorld()
    reloaded.load_from_dict(payload)

    for name, mode in chars.items():
        rp = reloaded.player_manager.get_player(name)
        assert rp.controller == mode, f"{name} expected controller {mode}, got {rp.controller}"


def test_legacy_payload_without_controller_derives_correctly():
    """Verify that loading an old scenario JSON lacking 'controller' derives the right mode."""
    legacy_payload = {
        "world": {"name": "LegacyWorld"},
        "areas": {"Square": {"name": "Square"}},
        "players": {
            "OldHuman": {"name": "OldHuman", "autonomy": False, "simple_npc": False},
            "OldDirected": {"name": "OldDirected", "autonomy": "directed", "simple_npc": False},
            "OldAgent": {"name": "OldAgent", "autonomy": True, "simple_npc": False},
            "OldNpc": {"name": "OldNpc", "autonomy": True, "simple_npc": True},
            "OldInert": {"name": "OldInert", "autonomy": False, "simple_npc": True},
        },
    }

    world = VirtualWorld()
    world.load_from_dict(legacy_payload)

    assert world.player_manager.get_player("OldHuman").controller == "human"
    assert world.player_manager.get_player("OldDirected").controller == "directed"
    assert world.player_manager.get_player("OldAgent").controller == "llm"
    assert world.player_manager.get_player("OldNpc").controller == "npc"
    assert world.player_manager.get_player("OldInert").controller == "inert"
