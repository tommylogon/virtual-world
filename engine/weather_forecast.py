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
#: This list is the single weather vocabulary: the light multiplier, the
#: guess-time skill DC and the description prose are all keyed by these values.
#: Nothing validates the ``weather`` field on save, so a hand-authored world may
#: carry a spelling that is not here — readers normalise with
#: :func:`normalize_weather` rather than each keeping a private alias list
#: (task-559; the guess-time table had already drifted into a second list that
#: also knew ``sunny`` and ``overcast``).
WEATHER_STATES = ["clear", "cloudy", "windy", "rainy", "stormy", "foggy", "snowy"]

#: Spellings seen in older and hand-authored worlds, mapped to a canonical
#: state. Read-time only: nothing rewrites a stored value, so a world that says
#: ``overcast`` keeps saying it and still behaves like ``cloudy`` everywhere.
WEATHER_ALIASES = {
    "sunny": "clear",
    "fair": "clear",
    "overcast": "cloudy",
    "drizzle": "rainy",
    "downpour": "stormy",
    "thunderstorm": "stormy",
    "sleet": "snowy",
    "mist": "foggy",
}


def normalize_weather(value: Any) -> str:
    """Canonical weather state for any input, ``""`` when it is not a state.

    Readers go through this so one alias table serves the light multiplier, the
    skill DC and the prose. Returns ``""`` rather than guessing, so an unknown
    value still falls through to each reader's default instead of silently
    becoming ``clear``.
    """
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = WEATHER_ALIASES.get(text, text)
    return text if text in WEATHER_STATES else ""


#: Survival DC for reading the sky out of a forecast, per canonical weather
#: state (task-559). Moved here from the action handler so the DC table and
#: :data:`WEATHER_STATES` cannot drift apart again.
WEATHER_TIME_DC = {
    "clear": 10,
    "cloudy": 15,
    "windy": 16,
    "rainy": 18,
    "foggy": 18,
    "snowy": 18,
    "stormy": 20,
}

#: DC used for a state with no entry (including an unrecognised value).
WEATHER_TIME_DC_DEFAULT = 15

#: Wind states (task-231).
WIND_STATES = ["none", "breeze", "wind", "gale", "storm", "hurricane"]

#: Humidity states (task-232).
HUMIDITY_STATES = ["dry", "humid", "wet", "flooding"]


#: Wind multiplier on heat propagation (task-231; stronger wind of a pair wins).
WIND_HEAT_MULT = {"none": 1.0, "breeze": 1.2, "wind": 1.5, "gale": 2.0, "storm": 2.5, "hurricane": 3.0}

#: Wind chill (°C) applied by effective_temperature before wind_resistance.
WIND_CHILL = {"none": 0, "breeze": -1, "wind": -3, "gale": -6, "storm": -10, "hurricane": -15}

#: Humidity modifier on effective temperature: (hot >20°C, cold ≤20°C).
HUMIDITY_TEMP_MOD = {"dry": (0, 0), "humid": (2, -1), "wet": (3, -2), "flooding": (4, -3)}

#: Weather → ambient light multiplier (Time & Weather.md: "Weather Modifier").
#: This table had **no readers** — it was defined, documented and never applied,
#: so a midday thunderstorm was exactly as bright as a clear midday
#: (bug-54). :func:`weather_light_mult` is the reader; ``LightingSystem``
#: scales the time-of-day curve by it.
WEATHER_LIGHT_MULT = {
    "clear": 1.0, "cloudy": 0.7, "rainy": 0.5, "stormy": 0.3,
    "foggy": 0.4, "windy": 0.8, "snowy": 0.6,
}


def weather_light_mult(weather: Any) -> float:
    """Ambient light multiplier for a weather state.

    Returns ``1.0`` for an unset, unknown or unrecognised value, so a world
    with no forecast is completely unaffected — only a world that actually
    authors weather sees its light change.
    """
    return WEATHER_LIGHT_MULT.get(normalize_weather(weather), 1.0)

#: Which weather obscures the sky (moon bonus rules, task-229).
OBSCURING_WEATHER = {"stormy", "foggy"}

#: The outdoor base every world has always had, in °C (task-553). It is the default
#: for ``env.base_temperature`` and the reason a world with no climate authored
#: anywhere reproduces its old numbers exactly: the curve is added *to* this, and
#: an unseasoned, unmodified world at 21.0 reads 21.0 as it did before.
OUTDOOR_BASE_C = 21.0

#: Outdoor temperature across the day, as **deltas from the base** in °C
#: (task-553). Same shape as ``lighting._OUTDOOR_ANCHORS`` — ``(hour, delta)``
#: pairs, linearly interpolated — so the two curves are read the same way and a
#: new hour is added in one place.
#:
#: Deltas rather than absolute values on purpose: the *shape* of a day is the same
#: whether the base is 21 °C or 5 °C, and a table of absolutes would have to be
#: rewritten per climate. The numbers are deliberately shallow — a night a few
#: degrees under, an afternoon a few over. A real curve belongs to the forecast
#: (``temperature_mod``) and to the season, both of which are authored.
TEMP_CURVE_ANCHORS = [
    (0, -4.0), (4, -5.0), (7, -3.0), (9, 0.0), (13, 3.5), (16, 2.5), (19, -0.5),
    (22, -3.0), (24, -4.0),
]

#: Season → the °C the season pulls the daily curve by (task-554). Signed, and
#: deliberately not a "temperature" — the season is a *bias on the shape*, so a
#: tropical base with a winter bias is still warm and a temperate base in winter
#: is properly cold. Keyed by the canonical season names the engine resolves.
SEASON_TEMP_BIAS = {
    "spring": 1.0,
    "summer": 4.0,
    "autumn": -1.0,
    "winter": -7.0,
}

#: The canonical seasons, in the order the year runs (task-554).
SEASONS = ("spring", "summer", "autumn", "winter")

#: Month → season, 1-12 (task-554).
#:
#: **This table used to exist twice in the frontend and nowhere in the engine.**
#: `static/js/sky-scape.js` had two copies of it — one in `SEASON_BY_MONTH` and
#: one inline in the iframe `postMessage` — and the backend read a season nowhere,
#: so `"season": "winter"` in a save was a value no code path ever looked at. The
#: engine is the only place a month can be read now, and the frontend asks it,
#: because two copies of a calendar boundary can disagree and there is nothing to
#: arbitrate between them.
#:
#: The boundaries are the northern-hemisphere ones the old table used (Dec-Feb
#: winter, Mar-May spring, Jun-Aug summer, Sep-Nov autumn), kept deliberately:
#: changing them would change what "winter" means in every existing world.
SEASON_BY_MONTH = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "autumn", 10: "autumn", 11: "autumn",
}

#: The season a world with no clock and no override is in. ``summer`` is what the
#: old frontend fell back to, and the scenarios that ship say ``"summer"``, so
#: this keeps their temperature behaviour unchanged.
DEFAULT_SEASON = "summer"


def season_for_month(month: Any) -> str:
    """The season for a game month 1-12 (task-554).

    Mirrors the boundaries ``sky-scape.js`` used, which are the northern
    hemisphere's. A month outside 1-12 clamps rather than raising, because the
    same clock that hands this function a month also renders it, and a sky widget
    that crashes on day 0 is worse than one that says summer.
    """
    try:
        m = max(1, min(12, int(month)))
    except (TypeError, ValueError):
        return DEFAULT_SEASON
    return SEASON_BY_MONTH[m]


def resolve_season(world_state: Any) -> str:
    """The season the engine is in, from the clock or an explicit override (task-554).

    Order, and the reason for it: an **authored** ``world_state.season`` wins over
    the clock, because a scenario that says ``"season": "winter"`` is making a
    statement about its world and should not have it silently overruled by whatever
    month the clock happens to be on. With no authored season, the clock decides,
    so a world that plays across a season boundary **changes season without a
    save or a reload** — the whole point of moving this out of the sky widget.

    A recognised season name is returned as-is (case-insensitively); an
    unrecognised one falls through to the clock rather than becoming a state the
    temperature model has no bias for.
    """
    state = world_state or {}
    authored = str(state.get("season") or "").strip().lower()
    if authored in SEASON_TEMP_BIAS:
        return authored
    month = state.get("game_month")
    if month not in (None, ""):
        return season_for_month(month)
    return authored if authored in SEASONS else DEFAULT_SEASON


def temp_curve_for_hour(hour: Any, season: Any = None) -> float:
    """The outdoor temperature **delta** for an hour, in °C (task-553).

    The diurnal curve, plus a season bias, as a delta on
    :data:`OUTDOOR_BASE_C`. An hour outside 0-23 is clamped rather than rejected,
    matching :func:`engine.lighting.outdoor_light_for_hour` so the two curves
    cannot disagree about a silly hour.

    An unknown or missing season contributes nothing: a world that never set one
    gets a plain diurnal day, which is the shape it had before this existed (flat,
    but at least honest about the time of day).
    """
    hour = max(0, min(23, int(hour)))
    delta = OUTDOOR_BASE_C  # only used as the "below every anchor" fallback
    for (h0, v0), (h1, v1) in zip(TEMP_CURVE_ANCHORS, TEMP_CURVE_ANCHORS[1:]):
        if h0 <= hour <= h1:
            if h1 == h0:
                delta = v0
                break
            frac = (hour - h0) / (h1 - h0)
            delta = v0 + (v1 - v0) * frac
            break
    else:
        delta = TEMP_CURVE_ANCHORS[-1][1]
    bias = SEASON_TEMP_BIAS.get(str(season or "").strip().lower())
    return delta + (bias if bias is not None else 0.0)

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
