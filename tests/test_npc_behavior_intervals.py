"""Authored behaviour intervals are game minutes, not ticks (task-428).

`behaviors[].interval` and `npc_action_interval` were raw *tick* counts, so their
meaning depended on `world.time_per_tick_minutes`: at 15 min/tick an authored
"every 5" fired every 75 game minutes, and a legacy wanderer moved once every 45
minutes instead of every 3. Every other time-measuring thing in the engine is in
game units and scales with the tick; this was the last one that did not.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from engine.npc_behaviors import _interval_ticks


class _World:
    def __init__(self, minutes):
        self.time_per_tick_minutes = minutes


@pytest.mark.parametrize("tick_minutes,interval_minutes,expected_ticks", [
    # At the default tick length the meaning of an authored value is unchanged.
    (1, 1, 1), (1, 5, 5), (1, 30, 30),
    # A long tick makes the same authored interval fewer ticks.
    (15, 15, 1), (15, 30, 2), (15, 60, 4),
    (5, 5, 1), (5, 30, 6),
])
def test_an_interval_is_converted_from_game_minutes(tick_minutes, interval_minutes,
                                                    expected_ticks):
    assert _interval_ticks(_World(tick_minutes), interval_minutes) == expected_ticks


def test_the_same_authored_value_means_the_same_game_time_at_any_tick():
    """The whole point: 'every 30 minutes' is 30 minutes, whatever a tick is."""
    assert _interval_ticks(_World(1), 30) == 30
    assert _interval_ticks(_World(15), 30) == 2
    assert _interval_ticks(_World(30), 30) == 1


def test_an_interval_never_rounds_down_to_zero():
    """A tick is the smallest step the scheduler has, so a short interval cannot
    become 'never'."""
    assert _interval_ticks(_World(15), 1) == 1
    assert _interval_ticks(_World(60), 1) == 1
    assert _interval_ticks(_World(15), 0) == 1


def test_junk_falls_back_to_every_tick_instead_of_raising():
    assert _interval_ticks(_World(1), None) == 1
    assert _interval_ticks(_World(1), "soon") == 1
    assert _interval_ticks(_World(0), 5) == 5      # a bad tick length is 1
    assert _interval_ticks(_World(None), 5) == 5
