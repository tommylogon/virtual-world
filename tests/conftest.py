"""Shared test fixtures and the fixture-world isolation helpers (task-586).

`world()` (the pytest fixture and `new_world()`) boots the declared regression
fixture at `tests/fixtures/world.json`, whose cast is inert: `autonomy` is False
on every character, so `process_simple_npcs` and the background simulation leave
them where a test puts them. That is what makes `solo()` an honest isolation
primitive — before task-586 a "moved everyone to Kitchen" helper was defeated by
the cast wandering back in, which is bug-55.

`solo(world, who, area=...)` is the real point: a test that cannot express
"one character, alone" without the world conspiring against it will keep minting
order-dependent failures. Tests that *want* NPC behaviour opt in by setting
`player.autonomy = True` (and restoring `npc_behavior`/behaviours as needed).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

AREA = "Blizzard Forest Clearing"
ELSEWHERE = "Kitchen"


def new_world():
    """A fresh TESTING world booted from the inert fixture."""
    from app import create_app

    return create_app({"TESTING": True}).world


def _place(world, name, area):
    if name in world.player_manager.players:
        player = world.player_manager.players[name]
    else:
        from player import Player

        player = Player(name)
        world.add_player(player)
    player.current_area = area
    world.set_player_area(name, area)
    return player


def solo(world, who, area=AREA):
    """Put ``who`` in ``area`` and move every other character out of it.

    The fixture is inert, so nobody wanders back in on a later tick.
    """
    player = _place(world, who, area)
    for other in world.player_manager.players.values():
        if other is not player and other.current_area == area:
            elsewhere = ELSEWHERE if area != ELSEWHERE else "Study"
            other.current_area = elsewhere
            world.set_player_area(other.name, elsewhere)
    return player


def company(world, a, b, area=AREA):
    """Put two characters together in ``area``; return both players."""
    return _place(world, a, area), _place(world, b, area)


@pytest.fixture
def world():
    """A fresh inert-fixture world for tests that do not need their own boot."""
    return new_world()
