"""Weather forecast schedule + moon phases (task-227, task-229, task-234).

The forecast is a *time-aware environment overlay*, not a weather
simulation: an authored (or state-machine) schedule that `tick_turn()`
applies each turn as the environmental baseline for exterior areas.
Forecast modes:

  authored       — explicit entries at offsets in a repeating period
                   (hourly = 1 day, weekly = 7 days, yearly = 365 days)
  deterministic  — weighted transition table, no randomness
  random         — same table, seeded `random`
  hybrid         — authored base temps/light + state-machine weather on top

A GM/trigger `forecast_override` supersedes the schedule and auto-reverts
after `duration_ticks`. Moon phases follow a deterministic 30-day cycle
from `game_day` (see `get_moon_phase`), driving the outdoor night-light
bonus (task-229) and the `moon_phase_equals` trigger condition (task-234).
"""

from __future__ import annotations

import random
from typing import Any, Optional

#: Weather states (canonical order — also used by adjust_weather cycling).
WEATHER_STATES = ["clear", "cloudy", "windy", "rainy", "stormy", "foggy", "snowy"]

#: Wind states (task-231).
WIND_STATES = ["none", "breeze", "wind", "gale", "storm", "hurricane"]

#: Humidity states (task-232).
HUMIDITY_STATES = ["dry", "humid", "wet", "flooding"]

#: Numeric wind scale.
WIND_SCALE = {"none": 0, "breeze": 1, "wind": 2, "gale": 3, "storm": 4, "hurricane": 5}

#: Wind multiplier on heat propagation (task-231; stronger wind of a pair wins).
WIND_HEAT_MULT = {"none": 1.0, "breeze": 1.2, "wind": 1.5, "gale": 2.0, "storm": 2.5, "hurricane": 3.0}

#: Wind chill (°C) applied by effective_temperature before wind_resistance.
WIND_CHILL = {"none": 0, "breeze": -1, "wind": -3, "gale": -6, "storm": -10, "hurricane": -15}

#: Humidity modifier on effective temperature: (hot >20°C, cold ≤20°C).
HUMIDITY_TEMP_MOD = {"dry": (0, 0), "humid": (2, -1), "wet": (3, -2), "flooding": (4, -3)}

#: Weather → ambient light multiplier (Time & Weather.md: "Weather Modifier").
WEATHER_LIGHT_MULT = {
    "clear": 1.0, "cloudy": 0.7, "rainy": 0.5, "stormy": 0.3,
    "foggy": 0.4, "windy": 0.8, "snowy": 0.6,
}

#: Which weather obscures the sky (moon bonus rules, task-229).
OBSCURING_WEATHER = {"stormy", "foggy"}

#: Default transition table for deterministic/random modes when the scenario
#: doesn't author one (mirrors Time & Weather.md / task-227 example).
DEFAULT_TRANSITION_TABLE = {
    "clear": {"clear": 7, "cloudy": 2, "windy": 1},
    "cloudy": {"clear": 2, "cloudy": 4, "rainy": 2, "foggy": 1, "windy": 1},
    "rainy": {"clear": 1, "cloudy": 2, "rainy": 3, "stormy": 2, "foggy": 2},
    "stormy": {"rainy": 3, "cloudy": 2, "clear": 1},
    "foggy": {"clear": 2, "foggy": 3, "cloudy": 2, "rainy": 1},
    "windy": {"clear": 3, "cloudy": 2, "windy": 2, "stormy": 1},
}

PERIOD_MINUTES = {"hourly": 1440, "weekly": 10080, "yearly": 525600}


def get_moon_phase(game_day: int) -> dict:
    """Deterministic 30-day moon cycle (task-229).

    Returns ``{"name", "icon", "light_bonus", "cycle_day"}``. The bonus is
    the extra ambient light a full moon adds to *outdoor night* areas.
    """
    cycle_day = int(game_day) % 30
    if cycle_day < 5:
        phase = {"name": "new_moon", "icon": "🌑", "light_bonus": 0}
    elif cycle_day < 10:
        phase = {"name": "crescent", "icon": "🌒", "light_bonus": 5}
    elif cycle_day < 15:
        phase = {"name": "quarter", "icon": "🌓", "light_bonus": 10}
    elif cycle_day < 20:
        phase = {"name": "gibbous", "icon": "🌔", "light_bonus": 15}
    elif cycle_day < 25:
        phase = {"name": "full_moon", "icon": "🌕", "light_bonus": 25}
    else:
        phase = {"name": "waning", "icon": "🌖", "light_bonus": 10}
    phase["cycle_day"] = cycle_day
    return phase


class ForecastSchedule:
    """The scenario's authored / state-machine forecast."""

    def __init__(self, schedule: Optional[dict] = None):
        schedule = schedule or {}
        self.mode = schedule.get("mode", "authored")
        if self.mode not in ("authored", "deterministic", "random", "hybrid"):
            self.mode = "authored"
        self.seed = schedule.get("seed")
        self.granularity = schedule.get("granularity", "hourly")
        if self.granularity not in PERIOD_MINUTES:
            self.granularity = "hourly"
        self.period = PERIOD_MINUTES[self.granularity]
        entries = schedule.get("entries") or []
        self.entries = sorted(entries, key=lambda e: int(e.get("offset", 0) or 0))
        # State-machine fields (deterministic / random / hybrid weather layer).
        self.current_state = schedule.get("current_state", "clear")
        self.transition_interval = int(schedule.get("transition_interval", 1) or 1)
        self.transition_table = schedule.get("transition_table") or DEFAULT_TRANSITION_TABLE
        self._rng = random.Random(self.seed) if self.seed is not None else random.Random()
        self._last_entry_key = None  # (offset key) of the previously returned entry

    # ── authored/hybrid lookup ───────────────────────────────────────────

    def _entry_for_offset(self, offset: int) -> dict:
        if not self.entries:
            return {}
        offset = offset % self.period
        for i, entry in enumerate(self.entries):
            start = int(entry.get("offset", 0) or 0)
            if i + 1 < len(self.entries):
                end = int(self.entries[i + 1].get("offset", 0) or 0)
            else:
                end = self.period
            if start <= offset < end:
                return entry
        return self.entries[0]

    # ── state machine rolls ──────────────────────────────────────────────

    def roll_state(self) -> str:
        """Advance the weather state machine by one transition interval."""
        table = self.transition_table or {}
        weights = table.get(self.current_state)
        if not weights or not isinstance(weights, dict):
            return self.current_state
        if self.mode == "deterministic":
            # Deterministic: pick the first non-zero weight (no randomness).
            for state, w in weights.items():
                if int(w) > 0:
                    self.current_state = state
                    return state
            return self.current_state
        # random: seeded rng weighted pick
        states = list(weights.keys())
        counts = [max(0, int(weights[s])) for s in states]
        total = sum(counts)
        if total <= 0:
            return self.current_state
        pick = self._rng.uniform(0, total)
        acc = 0
        for state, count in zip(states, counts):
            acc += count
            if pick <= acc:
                self.current_state = state
                return state
        return self.current_state

    # ── public lookup ────────────────────────────────────────────────────

    def get_entry_for_time(self, total_minutes: int, game_day: int = 1) -> dict:
        """Return the authored entry active at ``total_minutes``.

        For weekly/yearly granularity, ``game_day`` shifts the period origin
        (day 1 = 0; day counts as a full day of minutes).
        """
        if not self.entries:
            return {}
        offset = int(total_minutes)
        if self.granularity in ("weekly", "yearly"):
            offset += max(0, int(game_day) - 1) * 1440
        return self._entry_for_offset(offset)

    def current_environment(self, time_ticks: int, time_per_tick_minutes: float,
                            game_day: int = 1) -> dict:
        """Effective weather/environment from the schedule (no override).

        State-machine modes synthesize an entry from ``current_state``; the
        weather layer rides on a small per-state tuning table.
        """
        if self.mode in ("authored",):
            return dict(self.get_entry_for_time(
                int(time_ticks * time_per_tick_minutes), game_day))
        base = dict(self.get_entry_for_time(
            int(time_ticks * time_per_tick_minutes), game_day)) if self.mode == "hybrid" else {}
        base.setdefault("weather", self.current_state)
        return base

    @staticmethod
    def is_override_active(override: Optional[dict]) -> bool:
        return isinstance(override, dict) and bool(override.get("weather") or override.get("wind")
                                                   or override.get("humidity")
                                                   or override.get("temperature_mod")
                                                   or override.get("light_mod")
                                                   or override.get("air")
                                                   or override.get("blood_moon"))

    def resolve(self, schedule_env: dict, override: Optional[dict]) -> dict:
        """Merge schedule values with an active GM/trigger override."""
        env = dict(schedule_env or {})
        if override:
            for key in ("weather", "wind", "humidity", "temperature_mod",
                        "light_mod", "air", "blood_moon"):
                if key in override and override[key] is not None:
                    env[key] = override[key]
        return env
