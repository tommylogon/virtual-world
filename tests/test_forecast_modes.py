"""Forecast state-machine modes (bug-537).

`deterministic` used to pick the *first non-zero* weight, and every row of
DEFAULT_TRANSITION_TABLE lists `clear` first, so the weather was frozen at
`clear` forever. It is now a seeded weighted pick — reproducible, and able to
move.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.weather_forecast import ForecastSchedule  # noqa: E402


def test_deterministic_is_reproducible_and_not_frozen():
    a = ForecastSchedule({"mode": "deterministic", "current_state": "clear"})
    seq_a = [a.roll_state() for _ in range(40)]
    b = ForecastSchedule({"mode": "deterministic", "current_state": "clear"})
    seq_b = [b.roll_state() for _ in range(40)]
    assert seq_a == seq_b, "same (default) seed must give the same sequence"
    assert len(set(seq_a)) > 1, "deterministic weather is frozen (bug-537)"


def test_random_with_a_seed_is_reproducible():
    a = ForecastSchedule({"mode": "random", "seed": 7, "current_state": "clear"})
    b = ForecastSchedule({"mode": "random", "seed": 7, "current_state": "clear"})
    assert [a.roll_state() for _ in range(20)] == [b.roll_state() for _ in range(20)]
