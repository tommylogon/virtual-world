"""Activity/pursuit durations: minutes and ticks must not be conflated (task-726)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import activities as activities_mod
from engine import background_plans as BP
from engine.activities import ActivitySystem


class _P:
    def __init__(self, activity):
        self.activity = activity
        self.current_area = "River"


def test_minutes_duration_compares_against_elapsed_minutes():
    # 30 game minutes elapsed, ticks still tiny. The pre-task-726 code compared
    # the minutes value against elapsed_ticks, so this never elapsed.
    p = _P({"type": "fishing", "elapsed_ticks": 2, "elapsed_minutes": 30})
    step = {"kind": "activity", "activity": "fishing", "duration_minutes": 30}
    assert BP._satisfied(object(), p, step) is True


def test_ticks_duration_still_compares_against_elapsed_ticks():
    p = _P({"type": "fishing", "elapsed_ticks": 120, "elapsed_minutes": 2})
    step = {"kind": "activity", "activity": "fishing", "duration_ticks": 120}
    assert BP._satisfied(object(), p, step) is True


def test_minutes_duration_is_not_satisfied_by_a_large_tick_count():
    p = _P({"type": "fishing", "elapsed_ticks": 500, "elapsed_minutes": 10})
    step = {"kind": "activity", "activity": "fishing", "duration_minutes": 30}
    assert BP._satisfied(object(), p, step) is not True


class _PM:
    def __init__(self, players):
        self.players = players


class _Player:
    def __init__(self):
        self.state = "alive"
        self.activity = None
        self.conditions = {}


def test_start_activity_stores_duration_minutes(monkeypatch):
    monkeypatch.setattr(activities_mod, "activity_description", lambda a, n: "fishing")
    a = object.__new__(ActivitySystem)
    p = _Player()
    a.player_manager = _PM({"A": p})
    a._definition = lambda t: {}
    a._current_tick = lambda: 0
    a._turn_event = lambda *args, **kw: None

    a.start_activity("A", "fishing", duration_minutes=120)
    assert p.activity["duration_minutes"] == 120
    assert p.activity["elapsed_minutes"] == 0.0
