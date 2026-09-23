"""Vital costs are absolute, and the clock has one owner (task-436).

``ACTION_COSTS`` used to carry a ``time`` field that did double duty: it
multiplied every vital cost *and* served as the "this action advanced the clock"
flag. So ``move {energy: 1, time: 1}`` cost 1 while ``fumble {energy: 3,
time: 2}`` cost 6 — the table read as totals while behaving as per-minute rates,
and *which* actions moved the clock was an accident of that table (``open`` did
not, ``look`` did).

These tests pin the split: the cost magnitudes are exactly what they were, and
clock advancement has one owner. Atomic actions take a minute, which the
per-action layer grants. A task that runs for its own duration — ``rest`` — marks
the clock as already advanced so that layer does not add a minute on top of the
hours it just spent.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player

AREA = "Blizzard Forest Clearing"


def _world_and_player():
    from app import create_app
    w = create_app({"TESTING": True}).world
    p = Player("CostProbe")
    w.add_player(p)
    p.current_area = AREA
    w.set_player_area(p.name, AREA)
    for k in p.vitals:
        p.vitals[k] = 80
    return w, p


def test_fumble_keeps_the_six_energy_it_always_cost():
    """3 x ``time: 2`` = 6, now written as an absolute 6."""
    w, p = _world_and_player()
    before = p.vitals["Energy"]
    w.apply_action("fumble", player=p)
    assert before - p.vitals["Energy"] == 6


def test_no_cost_entry_carries_a_time_multiplier():
    """A reintroduced ``time`` key would now be silently ignored, so it must
    fail here rather than quietly changing nothing in the vitals."""
    from app import create_app
    w = create_app({"TESTING": True}).world
    assert w.ACTION_COSTS, "cost table is empty?"
    for action, cost in w.ACTION_COSTS.items():
        assert "time" not in cost, f"{action} still carries `time`"
        assert all(
            isinstance(v, (int, float, bool)) for v in cost.values()
        ), f"{action} has a non-numeric cost: {cost}"


def test_apply_action_no_longer_claims_the_clock():
    """The per-action layer reports cost, not time. An action is one minute and
    the caller grants it, so applying a cost must not touch the guard."""
    w, p = _world_and_player()
    w._clock_advanced_by_task = False
    w.apply_action("move", player=p)
    assert w._clock_advanced_by_task is False


def test_rest_advances_the_clock_itself_and_is_marked_as_having_done_so():
    """The load-bearing invariant: ``rest`` advances exactly its own minutes.

    ``rest`` loops ``tick_turn`` once per minute, so it owns the clock for the
    duration it runs. If it did not mark that, the per-action layer would add a
    minute on top and a 60-minute rest would cost 61.
    """
    w, p = _world_and_player()
    w.time_per_tick_minutes = 1
    w._clock_advanced_by_task = False
    before = w.time_ticks

    w.tick_manager.rest(minutes=60)

    elapsed = (w.time_ticks - before) * w.time_per_tick_minutes
    assert elapsed == 60, f"rest advanced {elapsed} minutes, expected 60"
    assert w._clock_advanced_by_task is True, "rest must mark the clock advanced"
