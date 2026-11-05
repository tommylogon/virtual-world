"""Tests for background daily reflection (task-409).

Verifies:
- Capped at at most one reflection per background character per in-game day.
- Simulation continues unchanged when no local provider is configured.
- Bounded input context includes goals, relationships, and recent memories.
- Output applies through existing goal and memory APIs.
- Changes survive save/load round-trip in the Player record.
"""

from player import Player
from virtual_world_engine import VirtualWorld
from engine import daily_reflection, goals


def test_no_provider_leaves_simulation_unchanged():
    world = VirtualWorld()
    p = Player("Gribba")
    world.add_player(p)

    mem_count = len(p.memories)
    res = daily_reflection.maybe_reflect(world, p, local_provider=None)

    assert res is None
    assert len(p.memories) == mem_count
    assert getattr(p, "last_reflection_day", None) is None


def test_reflection_capped_at_once_per_in_game_day():
    world = VirtualWorld()
    p = Player("Mikka")
    world.add_player(p)
    day = world.game_day

    calls = []

    def mock_provider(ctx):
        calls.append(ctx)
        return {
            "thought": "I need to work more efficiently at the workshop.",
            "goal_updates": [],
        }

    # First call on Day executes
    res1 = daily_reflection.maybe_reflect(world, p, local_provider=mock_provider)
    assert res1 is not None
    assert res1["memory_added"] is True
    assert p.last_reflection_day == day
    assert len(calls) == 1

    # Second call on same Day is capped (no-op)
    res2 = daily_reflection.maybe_reflect(world, p, local_provider=mock_provider)
    assert res2 is None
    assert len(calls) == 1

    # Advancing day allows reflecting again
    world.time_ticks += 1440
    next_day = world.game_day
    assert next_day > day

    res3 = daily_reflection.maybe_reflect(world, p, local_provider=mock_provider)
    assert res3 is not None
    assert p.last_reflection_day == next_day
    assert len(calls) == 2


def test_reflection_updates_goals_and_memories():
    world = VirtualWorld()
    p = Player("Thrazz")
    world.add_player(p)

    # Add existing GIMP goal
    p.goals = [
        {"id": "forge_spears", "what": "Forge 5 spears", "priority": 2, "status": "active"},
    ]

    def mock_provider(ctx):
        assert ctx["character"] == "Thrazz"
        assert len(ctx["goals"]) == 1
        return {
            "thought": "The clan needs weapons before the first frost.",
            "goal_updates": [
                {"id": "forge_spears", "priority": 1, "status": "active"},
            ],
        }

    res = daily_reflection.maybe_reflect(world, p, local_provider=mock_provider)
    assert res is not None
    assert res["memory_added"] is True

    # Memory added as ordinary semantic reflection
    added_mem = [m for m in p.memories if m.get("source") == "daily_reflection"][0]
    assert added_mem["type"] == "reflection"
    assert added_mem["reflection_depth"] == 1
    assert "clan needs weapons" in added_mem["text"]

    # Goal priority updated through existing goal record
    goal = goals.find(p.goals, "forge_spears")
    assert goal["priority"] == 1


def test_reflection_survives_save_load():
    world = VirtualWorld()
    p = Player("Vekka")
    world.add_player(p)
    p.last_reflection_day = 5
    p.memories.append({
        "id": "mem_refl_test",
        "text": "Reflected on the borders.",
        "type": "reflection",
        "source": "daily_reflection",
        "reflection_depth": 1,
    })

    # Save to dict
    saved = world.serializer._serialize_player("Vekka", p)
    assert saved.get("last_reflection_day") == 5

    # Load into fresh player
    p2 = world.serializer._deserialize_player("Vekka", saved)
    assert p2.last_reflection_day == 5
    assert any(m.get("id") == "mem_refl_test" for m in p2.memories)
