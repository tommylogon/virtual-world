"""Tests for single-roll hazard and current push effects (task-746).

A single-roll hazard effect:
- rolls the check once
- runs a fail branch or a success branch
- moves the actor along a direction/way via push_actor on failure
- sets a per-character sweep guard with an expiry tick to prevent cascades
- records traversal.note_refusal (AVOID_MINUTES) so soak routes around it
"""

import pytest
from app import create_app
from player import Player
from engine.effects import Effects
from engine import traversal


@pytest.fixture
def app_and_world():
    app = create_app({"TESTING": True})
    return app, app.world


def test_hazard_success_narrates_and_does_not_push(app_and_world):
    app, world = app_and_world
    effects = Effects(world.graph, None)

    p = world.get_player(world.active_player)
    p.stats["STR"] = 18
    p.skills["Athletics"] = 5
    start_area = p.current_area

    # Fixed high d20 roll guaranteed to pass DC 12
    res = effects.execute(
        "hazard",
        {
            "hazard_id": "river",
            "skill": "Athletics",
            "dc": 12,
            "direction": "south",
            "message_success": "You keep your footing and reach the far bank.",
        },
        {"roll_fn": lambda: 18},
        game_state=world,
    )

    assert any("keep your footing" in line for line in res)
    assert p.current_area == start_area
    assert "wet" not in getattr(p, "conditions", {})


def test_hazard_failure_pushes_actor_applies_consequences_and_notes_refusal(app_and_world):
    app, world = app_and_world
    effects = Effects(world.graph, None)

    p = world.get_player(world.active_player)
    start_area = p.current_area

    # Ensure there is an exit so push can succeed
    exits = world.build_exits_for_area(start_area, include_hidden=True)
    assert exits, "active area should have at least one exit"
    push_dir = next(iter(exits.keys()))
    expected_dest = exits[push_dir]["target"]

    # Fixed low d20 roll guaranteed to fail DC 15
    res = effects.execute(
        "hazard",
        {
            "hazard_id": "river",
            "skill": "Athletics",
            "dc": 15,
            "direction": push_dir,
            "message_fail": "The current drags you off your feet.",
        },
        {"roll_fn": lambda: 2},
        game_state=world,
    )

    assert any("The current drags you off your feet." in line for line in res)
    assert p.current_area == expected_dest
    # Conditions from hazards.json river on_fail: ["wet"]
    assert "wet" in getattr(p, "conditions", {})

    # Refusal recorded in traversal avoid (lowercased key pair)
    avoided = traversal.avoid(world, p)
    assert (start_area.lower(), push_dir.lower()) in avoided


def test_hazard_sweep_guard_prevents_cascades_within_expiry(app_and_world):
    app, world = app_and_world
    effects = Effects(world.graph, None)

    p = world.get_player(world.active_player)
    start_area = p.current_area
    exits = world.build_exits_for_area(start_area, include_hidden=True)
    push_dir = next(iter(exits.keys()))
    dest_area = exits[push_dir]["target"]

    # First roll fails and pushes
    res1 = effects.execute(
        "hazard",
        {
            "hazard_id": "river",
            "dc": 15,
            "direction": push_dir,
            "sweep_guard_minutes": 5.0,
        },
        {"roll_fn": lambda: 1},
        game_state=world,
    )
    assert p.current_area == dest_area

    # Immediate second trigger with same guard/hazard within 5 minutes is guarded (returns empty, no second roll or push)
    res2 = effects.execute(
        "hazard",
        {
            "hazard_id": "river",
            "dc": 15,
            "direction": push_dir,
            "sweep_guard_minutes": 5.0,
        },
        {"roll_fn": lambda: 1},
        game_state=world,
    )
    assert res2 == []

    # Advance game clock past the 5-minute guard
    world.advance_clock(10)

    # After guard expiry, hazard re-arms
    res3 = effects.execute(
        "hazard",
        {
            "hazard_id": "river",
            "dc": 15,
            "sweep_guard_minutes": 5.0,
        },
        {"roll_fn": lambda: 1},
        game_state=world,
    )
    assert res3 != []
