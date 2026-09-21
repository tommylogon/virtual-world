"""Vital costs are absolute; `consumes_time` says whether an action takes a
minute (task-436).

`ACTION_COSTS` used to carry a `time` field that did double duty: it multiplied
every vital cost *and* served as the "this action advanced the clock" flag. That
made the table's numbers read as totals while behaving as per-minute rates —
`move {energy: 1, time: 1}` cost 1, but `fumble {energy: 3, time: 2}` cost 6.

These tests pin the split. The magnitudes are unchanged (verified end-to-end
against the pre-change code: `fumble` 6, `open` 1 with no clock advance, `take`
and `look` advancing), and the clock question is now an explicit field.

The flag is read from the world (``tools/game_tools.py`` reads
``world._action_time_consumed``), not from ``PlayerManager``.
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
    """3 x `time: 2` = 6, now written as an absolute 6."""
    w, p = _world_and_player()
    before = p.vitals["Energy"]
    w.apply_action("fumble", player=p)
    assert before - p.vitals["Energy"] == 6


def test_consumes_time_flag_follows_the_action():
    """`move` takes a minute; `open` deliberately does not."""
    w, p = _world_and_player()
    w.apply_action("move", player=p)
    assert w._action_time_consumed is True
    w.apply_action("open", player=p)
    assert w._action_time_consumed is False


def test_an_override_can_suppress_the_clock_advance():
    """The old `{"time": 0}` idiom, now spelled `consumes_time`.

    `engine/movement.py` charges extra energy for encumbrance and dash without
    that charge being an action of its own.
    """
    w, p = _world_and_player()
    w.apply_action("move", player=p)
    assert w._action_time_consumed is True
    w.apply_action("move", {"energy": 4, "consumes_time": False}, player=p)
    assert w._action_time_consumed is False


def test_no_cost_entry_carries_a_time_multiplier():
    """The overload is gone; a stray `time` key would now be silently ignored,
    so a reintroduced one must fail here rather than in the vitals."""
    from app import create_app
    w = create_app({"TESTING": True}).world
    assert w.ACTION_COSTS, "cost table is empty?"
    for action, cost in w.ACTION_COSTS.items():
        assert "time" not in cost, f"{action} still carries `time`"
        assert all(
            isinstance(v, (int, float, bool)) for v in cost.values()
        ), f"{action} has a non-numeric cost: {cost}"
