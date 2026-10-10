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

# The weather vocabulary is **library data** now (task-772): the state list, the
# guess-time DC, the light multiplier and the sky prose are loaded from
# ``data/library/weather/*.json`` by :mod:`engine.weather_types`. They are
# re-exported here so existing imports (``from engine.weather_forecast import
# WEATHER_STATES`` and friends) keep working — this module is the forecast
# *engine*; the vocabulary's home is the library.
from engine.weather_types import (  # noqa: F401  (re-export)
    WEATHER_ALIASES, WEATHER_LIGHT_MULT, WEATHER_PROSE, WEATHER_STATES,
    WEATHER_TIME_DC, WEATHER_TIME_DC_DEFAULT, normalize_weather,
    weather_light_mult, weather_types,
)


#: Wind states (task-231).
WIND_STATES = ["none", "breeze", "wind", "gale", "storm", "hurricane"]

#: Humidity states (task-232).
HUMIDITY_STATES = ["dry", "humid", "wet", "flooding"]

#: Wind directions (task-555): 8 points, **the same words** as the compiler's
#: ``engine.world_compile._COMPASS_BY_SIGN`` so the project keeps one compass
#: vocabulary, not two. Stored **alongside** the magnitude, not fused into it —
#: ``wind`` is how hard, ``wind_direction`` is **where the wind blows FROM**
#: (the meteorological convention: a "north wind" is a cold wind out of the
#: north). Nothing reads it for an effect yet; it is the additive hook the
#: rain-shadow / terrain-deflection work needs, so a world that authors nothing
#: keeps behaving exactly as before.
WIND_DIRECTIONS = ["north", "northeast", "east", "southeast",
                   "south", "southwest", "west", "northwest"]

#: Spellings → canonical direction word. Read-time only, like WEATHER_ALIASES.
WIND_DIRECTION_ALIASES = {
    "n": "north", "ne": "northeast", "e": "east", "se": "southeast",
    "s": "south", "sw": "southwest", "w": "west", "nw": "northwest",
    "northerly": "north", "northward": "north",
    "northeasterly": "northeast", "easterly": "east", "eastward": "east",
    "southeasterly": "southeast", "southerly": "south", "southward": "south",
    "southwesterly": "southwest", "westerly": "west", "westward": "west",
    "northwesterly": "northwest",
}


def normalize_wind_direction(value: Any) -> str:
    """Canonical compass word (``north``/``northeast``/…) for any input, ``""`` if unknown."""
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = WIND_DIRECTION_ALIASES.get(text, text)
    return text if text in WIND_DIRECTIONS else ""


#: Wind multiplier on heat propagation (task-231; stronger wind of a pair wins).
WIND_HEAT_MULT = {"none": 1.0, "breeze": 1.2, "wind": 1.5, "gale": 2.0, "storm": 2.5, "hurricane": 3.0}

#: Wind chill (°C) applied by effective_temperature before wind_resistance.
WIND_CHILL = {"none": 0, "breeze": -1, "wind": -3, "gale": -6, "storm": -10, "hurricane": -15}

#: Humidity modifier on effective temperature: (hot >20°C, cold ≤20°C).
HUMIDITY_TEMP_MOD = {"dry": (0, 0), "humid": (2, -1), "wet": (3, -2), "flooding": (4, -3)}

#: Which weather obscures the sky (moon bonus rules, task-229).
OBSCURING_WEATHER = {"stormy", "foggy"}


# ── Surface snow (task-556) ───────────────────────────────────────────────
# Snowy weather used to be a label that only dimmed the light. It now settles a
# **depth** on an *exterior* area, and the depth - not the word "snowy" - is what
# movement and forage read. That is the whole point: depth lives on the area, so
# snow lingers after the sky clears and thaws gradually instead of vanishing the
# instant the forecast entry that made it changes.
#
# Everything below is centimetres of settled snow. The depth is written by
# ``VirtualWorld._apply_forecast_env`` under ``environment.snow_depth`` on the
# area node - the same block that already carries ``temperature`` and
# ``weather`` - so it survives a save with no new serialization path, and only
# when it is above zero: a world that never snows never gains the key and is
# bit-for-bit unchanged.

#: Settled snow added per hour of ``snowy`` weather (a steady fall).
SNOW_ACCUM_CM_PER_HOUR = 3.0
#: Snow lost per hour of anything else - clear, fog, even rain. Slow on purpose:
#: a thaw takes hours, which is why depth is kept on the area, not the state.
SNOW_MELT_CM_PER_HOUR = 1.5
#: Depth ceiling, so a long winter cannot bury a world without end.
SNOW_MAX_CM = 60.0
#: Centimetres of settled snow per millimetre of water-equivalent precipitation.
SNOW_CM_PER_MM = 0.8

#: Depth at which snow starts to matter; below this it is cosmetic.
SNOW_LIGHT_CM = 2.0
#: Depth at which going is heavy.
SNOW_DEEP_CM = 15.0
#: Depth at which travel is a slog and forage is all but covered.
SNOW_BURIED_CM = 35.0


def weather_produces_snow(state: Any) -> bool:
    """True when a weather state settles snow (task-763).

    `snowy` always does; any registry type the author tagged `snow` does too, so
    the generated extremes (`blizzard`) accumulate snow without this module
    knowing their names. Data-driven, so a world's own snowstorm works.
    """
    cid = normalize_weather(state)
    if not cid:
        return False
    if cid == "snowy":
        return True
    rec = weather_types().get(cid) or {}
    return "snow" in [str(t).lower() for t in (rec.get("tags") or [])]


def advance_snow_depth(depth_cm: Any, weather: Any, minutes: Any,
                       precipitation: Any = None) -> float:
    """The settled-snow depth after *minutes* of *weather*, in cm (task-556/763).

    Snow-producing weather (see :func:`weather_produces_snow`) builds depth;
    anything else melts it at :data:`SNOW_MELT_CM_PER_HOUR`. When the state's
    precipitation is supplied, the accumulation rate scales with it
    (:data:`SNOW_CM_PER_MM`), so heavy snow settles faster than light snow;
    without it, a flat :data:`SNOW_ACCUM_CM_PER_HOUR`. Never negative, never
    above :data:`SNOW_MAX_CM`. Pure: the caller owns where the value is stored.
    """
    try:
        depth = max(0.0, float(depth_cm or 0.0))
    except (TypeError, ValueError):
        depth = 0.0
    try:
        hours = max(0.0, float(minutes or 0.0)) / 60.0
    except (TypeError, ValueError):
        hours = 0.0
    if weather_produces_snow(weather):
        if precipitation is None:
            rate = SNOW_ACCUM_CM_PER_HOUR
        else:
            try:
                rate = max(0.0, float(precipitation)) * SNOW_CM_PER_MM
            except (TypeError, ValueError):
                rate = SNOW_ACCUM_CM_PER_HOUR
        depth = min(SNOW_MAX_CM, depth + rate * hours)
    else:
        depth = max(0.0, depth - SNOW_MELT_CM_PER_HOUR * hours)
    return round(depth, 2)


def snow_movement_energy(depth_cm: Any) -> int:
    """Extra move **energy** for crossing ground under *depth_cm* of snow (task-556)."""
    try:
        depth = max(0.0, float(depth_cm or 0.0))
    except (TypeError, ValueError):
        return 0
    if depth >= SNOW_BURIED_CM:
        return 6
    if depth >= SNOW_DEEP_CM:
        return 3
    if depth >= SNOW_LIGHT_CM:
        return 1
    return 0


def snow_forage_dc_penalty(depth_cm: Any) -> int:
    """Extra search DC when *depth_cm* of snow covers the ground (task-556)."""
    try:
        depth = max(0.0, float(depth_cm or 0.0))
    except (TypeError, ValueError):
        return 0
    if depth >= SNOW_BURIED_CM:
        return 6
    if depth >= SNOW_DEEP_CM:
        return 4
    if depth >= SNOW_LIGHT_CM:
        return 2
    return 0


def snow_depth_prose(depth_cm: Any) -> str:
    """A sentence for settled snow, ``""`` when there is too little to say (task-556)."""
    try:
        depth = float(depth_cm or 0.0)
    except (TypeError, ValueError):
        return ""
    if depth >= SNOW_BURIED_CM:
        return "Snow lies deep - knee-high and drifted."
    if depth >= SNOW_DEEP_CM:
        return "Snow lies a good few inches deep underfoot."
    if depth >= SNOW_LIGHT_CM:
        return "A thin crust of snow covers the ground."
    return ""


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

# ── Weather generation (task-763) ─────────────────────────────────────────
# The forecast was authored, or a *single* global state machine. This adds a
# seeded, per-area generator on top: the same first-order Markov chain
# (DEFAULT_TRANSITION_TABLE), but its weights are conditioned on the season and
# on each area's terrain, rolled once per game day, with neighbours coupled so a
# front spreads across the map instead of reading as checkerboard noise.
#
# Two rules decide the shape, both learned from the standalone preview:
#
#  * The roll is over the FULL weighted distribution, never a top-N. The rare
#    states *are* the extreme weather; truncating the tail deletes it.
#  * Season and terrain may ADD a transition the base table lacks. `snowy` is the
#    proof: no row of DEFAULT_TRANSITION_TABLE transitions INTO it, so a
#    multiplier on a weight of zero is still zero. Only an additive edge works.

#: Season -> additive weight bias by weather state. Additive on purpose, so a
#: state the table never rolls into can be *added* (winter can add snow).
SEASON_WEATHER_BIAS = {
    # Extreme-kind ids appear here too: a season both raises its own extremes and
    # *suppresses* the ones that make no sense in it (a negative bias can push an
    # extreme's weight to zero, so there is no summer blizzard).
    "winter": {"snowy": 5, "cloudy": 3, "windy": 1, "clear": -3,
               "blizzard": 3, "cold_snap": 3, "heatwave": -2},
    "spring": {"rainy": 3, "cloudy": 1, "clear": 1,
               "thunderstorm": 1, "heatwave": -1},
    "summer": {"clear": 5, "stormy": 2, "snowy": -6, "cloudy": -1,
               "heatwave": 3, "thunderstorm": 1, "blizzard": -4, "cold_snap": -4},
    "autumn": {"foggy": 2, "windy": 2, "rainy": 1, "clear": -1,
               "thunderstorm": 1, "blizzard": 1, "cold_snap": 1},
}

#: Area tag -> additive weight bias by weather state. Terrain reads the tags the
#: compiler already writes (world_compile.py) and the climate paint layer
#: (task-557) turns into `base_temperature`; this is the same fact read for
#: weather. Mountains snowier, coasts foggier/wetter, forest humid, desert dry.
TERRAIN_WEATHER_BIAS = {
    # High, cold ground. Also raises the cold extremes and suppresses the hot one.
    "mountain": {"snowy": 3, "cloudy": 1, "blizzard": 2, "cold_snap": 1, "heatwave": -2},
    "mountains": {"snowy": 3, "cloudy": 1, "blizzard": 2, "cold_snap": 1, "heatwave": -2},
    "peak": {"snowy": 3, "blizzard": 2}, "peaks": {"snowy": 3, "blizzard": 2},
    "alpine": {"snowy": 4, "windy": 1, "blizzard": 3, "cold_snap": 2, "heatwave": -3},
    "summit": {"snowy": 3, "windy": 1, "blizzard": 2, "cold_snap": 1},
    "highland": {"snowy": 2, "windy": 1, "blizzard": 1, "cold_snap": 1},
    "highlands": {"snowy": 2, "windy": 1, "blizzard": 1, "cold_snap": 1},
    "glacier": {"snowy": 4, "blizzard": 3, "cold_snap": 2},
    "tundra": {"snowy": 3, "windy": 1, "blizzard": 2, "cold_snap": 2},
    "frozen": {"snowy": 3, "blizzard": 2, "cold_snap": 2},
    "ice": {"snowy": 2, "cold_snap": 2},
    # Wet ground: coasts, lakes, rivers, wetlands. Coasts brew thunderstorms.
    "coast": {"foggy": 3, "rainy": 2, "cloudy": 1, "thunderstorm": 1},
    "coastal": {"foggy": 3, "rainy": 2, "thunderstorm": 1},
    "beach": {"foggy": 3, "rainy": 1, "thunderstorm": 1},
    "shore": {"foggy": 3, "rainy": 2, "thunderstorm": 1},
    "shoreline": {"foggy": 3, "rainy": 2, "thunderstorm": 1},
    "ocean": {"foggy": 3, "rainy": 2, "windy": 1, "thunderstorm": 1},
    "sea": {"foggy": 3, "rainy": 2, "thunderstorm": 1},
    "lake": {"foggy": 2, "rainy": 1, "thunderstorm": 1},
    "river": {"foggy": 2, "rainy": 1}, "stream": {"foggy": 2, "rainy": 1},
    "spring": {"foggy": 1, "rainy": 1},
    "marsh": {"foggy": 2, "rainy": 1}, "swamp": {"foggy": 2, "rainy": 1},
    "bog": {"foggy": 2, "rainy": 1}, "wetland": {"foggy": 2, "rainy": 1},
    "fjord": {"foggy": 3, "rainy": 2},
    # Vegetated, humid ground.
    "forest": {"rainy": 1, "foggy": 1}, "forests": {"rainy": 1, "foggy": 1},
    "woods": {"rainy": 1, "foggy": 1}, "woodland": {"rainy": 1, "foggy": 1},
    "jungle": {"rainy": 2, "foggy": 1}, "rainforest": {"rainy": 3, "foggy": 1},
    "grove": {"rainy": 1, "foggy": 1},
    # Dry, hot, open ground: heatwaves happen, blizzards do not.
    "desert": {"clear": 3, "rainy": -2, "foggy": -1, "heatwave": 3, "blizzard": -4, "cold_snap": -3},
    "deserts": {"clear": 3, "rainy": -2, "foggy": -1, "heatwave": 3, "blizzard": -4, "cold_snap": -3},
    "arid": {"clear": 3, "rainy": -1, "heatwave": 3, "blizzard": -3, "cold_snap": -3},
    "dune": {"clear": 2, "rainy": -1, "heatwave": 3, "blizzard": -4, "cold_snap": -3},
    "dunes": {"clear": 2, "rainy": -1, "heatwave": 3, "blizzard": -4, "cold_snap": -3},
    "badlands": {"clear": 2, "rainy": -1, "heatwave": 2},
    "sand": {"clear": 2, "rainy": -1, "heatwave": 2, "blizzard": -4},
    "savanna": {"clear": 2, "rainy": -1, "heatwave": 2, "blizzard": -3},
    "savannah": {"clear": 2, "rainy": -1, "heatwave": 2, "blizzard": -3},
    "steppe": {"clear": 2, "rainy": -1, "heatwave": 2, "blizzard": -2, "cold_snap": -2},
}

#: Painted **climate** (task-557) -> additive weather bias. The compiler writes a
#: coarse `climate` enum (`arctic`/`alpine`/`temperate`/`arid`/`tropical`) onto an
#: area and its `base_temperature`; the generator reads that the way it reads a
#: biome tag, one band coarser, so a painted arctic area produces snow where an
#: adjacent temperate one does not — the same fact, read for weather.
CLIMATE_WEATHER_BIAS = {
    "arctic": {"snowy": 3, "cold_snap": 3, "blizzard": 2, "heatwave": -4, "clear": 1},
    "alpine": {"snowy": 3, "blizzard": 2, "cold_snap": 2, "cloudy": 1, "heatwave": -3},
    "temperate": {},          # the default: no bias
    "arid": {"clear": 3, "heatwave": 3, "blizzard": -4, "rainy": -1},
    "tropical": {"rainy": 2, "thunderstorm": 2, "foggy": 1, "cloudy": 1, "snowy": -6},
}

#: The tail tier. Every state the library marks ``kind: extreme`` is always a
#: candidate with at least this weight, so the tails stay reachable; season and
#: terrain can raise it, but never past :data:`EXTREME_CAP`, so the extraordinary
#: stays extraordinary. The *set* of extremes is library data (task-772), not a
#: list here — a world adds a blizzard or an acid rain and it becomes reachable.
EXTREME_BASE_WEIGHT = 1.0
EXTREME_CAP = 6.0

#: The state a chain with no history starts from.
DEFAULT_CURRENT_STATE = "clear"


def weather_state_kind(state: Any) -> str:
    """``"normal"`` or ``"extreme"`` for a weather id (``"normal"`` if unknown)."""
    rec = weather_types().get(normalize_weather(state))
    return str(rec.get("kind", "normal")) if rec else "normal"


def is_extreme_weather(state: Any) -> bool:
    """True when the vocabulary marks *state* as an extreme weather type."""
    return weather_state_kind(state) == "extreme"


def terrain_weather_bias(tags: Any, climate: Any = None) -> dict:
    """Additive weather-weight bias for an area's tags and painted climate (task-763).

    Sums every recognised tag, so a coastal forest is both wet and humid, then
    folds in the compiled `climate` (task-557). Unrecognised tags contribute
    nothing; an unpainted climate contributes nothing.
    """
    out: dict = {}
    if tags:
        if isinstance(tags, str):
            tags = tags.split(",")
        for tag in tags:
            for state, weight in TERRAIN_WEATHER_BIAS.get(str(tag).strip().lower(), {}).items():
                out[state] = out.get(state, 0) + weight
    for state, weight in CLIMATE_WEATHER_BIAS.get(str(climate or "").strip().lower(), {}).items():
        out[state] = out.get(state, 0) + weight
    return out


def conditioned_weights(current: Any, table: Any = None, season: Any = None,
                        terrain: Any = None, coupling: Any = None) -> dict:
    """Transition weights from *current*, conditioned on season/terrain/coupling.

    Starts from the table row and **adds** the season bias, the terrain bias and
    any neighbour coupling; every extreme-kind state is folded in as the tail
    tier (clamped to :data:`EXTREME_CAP`). Weights are floored at zero, so a
    negative season bias (summer against snow) can suppress but not invert a
    weight, and it can never resurrect one that the base and bonus both leave at
    zero.
    """
    table = table if table is not None else DEFAULT_TRANSITION_TABLE
    row = dict((table or {}).get(current) or {})
    season_bias = SEASON_WEATHER_BIAS.get(str(season or "").strip().lower(), {})
    terrain = terrain or {}
    coupling = coupling or {}
    known = set(weather_types())
    keys = (set(row) | set(season_bias) | set(terrain) | set(coupling)) & known
    keys |= {s for s in known if weather_state_kind(s) == "extreme"}
    weights: dict = {}
    for state in keys:
        weight = (float(row.get(state, 0)) + float(season_bias.get(state, 0))
                  + float(terrain.get(state, 0)) + float(coupling.get(state, 0)))
        if weather_state_kind(state) == "extreme":
            # Tail tier: a small base on top of the biases, capped. A *negative*
            # season/terrain bias can push it back to zero, so a summer blizzard
            # or a desert thunderstorm simply never rolls — the cap keeps the
            # extraordinary extraordinary, and the sign keeps it sensible.
            weights[state] = min(EXTREME_CAP, max(0.0, EXTREME_BASE_WEIGHT + weight))
        else:
            weights[state] = max(0.0, weight)
    return weights


def roll_from_weights(rng: random.Random, weights: dict, current: Any) -> str:
    """Weighted pick over the **full** distribution; *current* if all zero."""
    states = list(weights.keys())
    counts = [max(0.0, float(weights[s])) for s in states]
    total = sum(counts)
    if total <= 0 or not states:
        return str(current)
    pick = rng.uniform(0, total)
    acc = 0.0
    for state, count in zip(states, counts):
        acc += count
        if pick <= acc:
            return state
    return states[-1]


def generate_weather_field(prev: Any, areas: Any, neighbours: Any, *,
                           table: Any = None, season: Any = None,
                           seed: Any = None, day: int = 0,
                           coupling_bonus: float = 2.0,
                           climates: Any = None) -> dict:
    """One day's per-area weather, seeded and reproducible (task-763).

    ``areas`` maps ``area_id -> tags`` (only open-sky areas are passed).
    ``neighbours`` maps ``area_id -> iterable of adjacent area_ids`` and couples
    the roll: a state its neighbours are already in gets a bonus, so a front
    spreads to adjacent open ground instead of each area rolling in isolation.

    The RNG is seeded from ``(seed, day)`` and areas are rolled in sorted id
    order, so the same world and day always produce the same field, and a later
    day differs because the seed string differs.
    """
    rng = random.Random(f"{seed}|{day}")
    prev = prev or {}
    climates = climates or {}
    out: dict = {}
    for area_id in sorted(areas):
        current = prev.get(area_id) or DEFAULT_CURRENT_STATE
        coupling: dict = {}
        for nb in (neighbours.get(area_id) or ()):
            if nb not in areas:
                continue
            nb_state = prev.get(nb)
            if nb_state:
                coupling[nb_state] = coupling.get(nb_state, 0.0) + float(coupling_bonus)
        terrain = terrain_weather_bias(areas.get(area_id), climates.get(area_id))
        weights = conditioned_weights(current, table, season, terrain, coupling)
        out[area_id] = roll_from_weights(rng, weights, current)
    return out


def apply_field_overrides(field: Any, area_overrides: Any = None,
                          date_overrides: Any = None, day: Any = None) -> dict:
    """Patch a generated field with ordered overrides (task-763).

    One precedence chain, lowest to highest: generated heuristic < **date
    override** < **area override**. A date override replaces every area's state
    for that day; an area override then pins a single area over it, so a front
    can sweep the map while one valley stays stubbornly clear (or snowed in).
    """
    out = dict(field or {})
    date_overrides = date_overrides or {}
    picked = date_overrides.get(str(day), date_overrides.get(day))
    if picked:
        out = {area_id: picked for area_id in out}
    for area_id, state in (area_overrides or {}).items():
        if area_id in out:
            out[area_id] = state
    return out


#: What a weather state *implies* about the rest of the environment (task-763).
#: ``current_environment`` promises "the weather layer rides on a small per-state
#: tuning table" and never had one: the machine set the weather word and left
#: wind, humidity and temperature to whatever the authored entry said. A state
#: now carries its own tendency - a storm is not only a word, it is a strong wind
#: and a drop in temperature.
WEATHER_TUNING = {
    # `precipitation` is millimetres per hour (water-equivalent); 0 for states
    # that drop nothing. It is the state's precipitation amount (task-763) and
    # is what the snow rule reads, so heavy snow settles faster than light snow.
    "clear": {"wind": "none", "humidity": "dry", "temperature_mod": 1.0, "precipitation": 0.0},
    "cloudy": {"wind": "breeze", "humidity": "dry", "temperature_mod": 0.0, "precipitation": 0.0},
    "windy": {"wind": "wind", "humidity": "dry", "temperature_mod": 0.0, "precipitation": 0.0},
    "rainy": {"wind": "breeze", "humidity": "wet", "temperature_mod": -1.0, "precipitation": 3.0},
    "stormy": {"wind": "storm", "humidity": "flooding", "temperature_mod": -2.0, "precipitation": 8.0},
    "foggy": {"wind": "none", "humidity": "humid", "temperature_mod": -1.0, "precipitation": 0.0},
    "snowy": {"wind": "breeze", "humidity": "dry", "temperature_mod": -3.0, "precipitation": 4.0},
    # Extremes (task-763 content): same shape, pushed further.
    "blizzard": {"wind": "hurricane", "humidity": "dry", "temperature_mod": -6.0, "precipitation": 5.0},
    "thunderstorm": {"wind": "storm", "humidity": "flooding", "temperature_mod": -2.0, "precipitation": 12.0},
    "heatwave": {"wind": "none", "humidity": "dry", "temperature_mod": 8.0, "precipitation": 0.0},
    "cold_snap": {"wind": "breeze", "humidity": "dry", "temperature_mod": -8.0, "precipitation": 0.0},
}


def weather_tuning(state: Any) -> dict:
    """The wind/humidity/temperature a weather state implies (task-763).

    Empty for an unknown or custom state, so a world's own extreme type does not
    silently invent a wind it never declared.
    """
    return dict(WEATHER_TUNING.get(normalize_weather(state), {}))


#: Modes where the machine (not an authored entry) is the source of the weather,
#: so its per-state tuning applies.
STATE_MACHINE_MODES = ("deterministic", "random", "hybrid", "generated")


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
        if self.mode not in ("authored", "deterministic", "random", "hybrid",
                             "generated"):
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
        # `deterministic` must be reproducible *and* able to change state: with
        # no authored seed it uses 0, so the same world always rolls the same
        # sequence. (The old `deterministic` picked the first non-zero weight,
        # which froze every world at `clear` — bug-537.)
        seed = self.seed
        if seed is None and self.mode == "deterministic":
            seed = 0
        self._rng = random.Random(seed) if seed is not None else random.Random()
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
        # deterministic and random share the weighted pick; the difference is the
        # seed — `deterministic` is always seeded (see __init__), so its sequence
        # is reproducible, while `random` with no seed is not.
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

        State-machine modes synthesize the weather word from ``current_state``.
        The per-state wind/humidity/temperature a state implies (:data:`WEATHER_TUNING`)
        is applied at the *write* point instead — ``VirtualWorld._apply_forecast_env``
        — because the generated field (task-763) varies weather per area, so the
        tuning has to be per area too, and a single global table here would
        override it.
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
            for key in ("weather", "wind", "wind_direction", "humidity",
                        "temperature_mod", "light_mod", "air", "blood_moon"):
                if key in override and override[key] is not None:
                    env[key] = override[key]
        return env
