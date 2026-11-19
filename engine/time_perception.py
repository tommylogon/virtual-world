"""Subjective time perception, timepiece readings, and sky-based guess_time.

Single source of truth for how a character tells time in the simulation:
- Working timepieces (clocks, watches, phones, sundials) give direct readings
  when examined or when checking time, gated by device state, viewer literacy
  (animals cannot read a digital clock), and sunlight (sundials).
- Sky reading (``guess time``) is gated on open sky (``engine.area_tags.is_open_sky``)
  or a window looking outside; windowless indoor areas cannot read the sun or stars.
- Non-clock-literate characters (animals, wild/feral creatures, goblins, or
  ``traits.no_clock_time``) perceive natural sky bands rather than ``HH:MM``.

@module time_perception
@contributes natural_time_band, is_non_clock_character, is_timepiece_node,
             is_sundial_node, find_accessible_timepiece,
             describe_timepiece_reading, resolve_guess_time
@docs docs/virtualWorld/Environment/Time & Weather.md
"""

from __future__ import annotations

import re
from typing import Any, List, Optional

from engine.area_tags import is_open_sky
from graph import EDGE_CARRYING, EDGE_CONNECTION, EDGE_EQUIPPED, EDGE_IN
from engine.weather_forecast import (
    WEATHER_TIME_DC,
    WEATHER_TIME_DC_DEFAULT,
    normalize_weather,
)

TIMEPIECE_TAGS = frozenset({
    "timepiece",
    "clock",
    "watch",
    "wristwatch",
    "pocket_watch",
    "phone",
    "smartphone",
    "cellphone",
    "sundial",
    "horologium",
})

SUNDIAL_TAGS = frozenset({"sundial", "horologium"})

BROKEN_TIMEPIECE_STATES = frozenset({
    "broken",
    "dead",
    "off",
    "unpowered",
    "shattered",
    "destroyed",
    "stopped",
})

NON_CLOCK_CHARACTER_TAGS = frozenset({
    "animal",
    "beast",
    "cat",
    "dog",
    "wolf",
    "bird",
    "monster",
    "feral",
    "wild",
    "goblin",
    "primitive",
})

OBSCURING_SUNDIAL_WEATHER = frozenset({
    "cloudy",
    "foggy",
    "rainy",
    "stormy",
    "snowy",
    "blizzard",
})

_TIMEPIECE_NAME_RE = re.compile(
    r"\b(wall clock|grandfather clock|alarm clock|clock|pocket watch|wristwatch|watch|timepiece|smartphone|cellphone|phone|sundial|horologium)\b",
    re.IGNORECASE,
)

_SUNDIAL_NAME_RE = re.compile(r"\b(sundial|horologium)\b", re.IGNORECASE)

_MOON_LABELS = {
    "new_moon": "new moon",
    "crescent": "waxing crescent",
    "quarter": "first quarter",
    "gibbous": "waxing gibbous",
    "full_moon": "full moon",
    "waning": "waning",
    "blood_moon": "blood moon",
}


def _norm_tags(raw: Any) -> set[str]:
    if not raw:
        return set()
    if isinstance(raw, str):
        raw = raw.split(",")
    if not isinstance(raw, (list, tuple, set, frozenset)):
        return set()
    return {str(t).strip().lower() for t in raw if str(t).strip()}


def natural_time_band(hour: int) -> str:
    """Return a natural, clock-free time-of-day band for ``hour`` (0..23)."""
    h = int(hour) % 24
    if h <= 3:
        return "deep night"
    if h == 4:
        return "the small hours before dawn"
    if h <= 6:
        return "dawn"
    if h <= 9:
        return "early morning"
    if h <= 11:
        return "late morning"
    if h == 12:
        return "midday"
    if h <= 15:
        return "early afternoon"
    if h <= 17:
        return "late afternoon"
    if h == 18:
        return "dusk"
    if h <= 21:
        return "evening"
    return "late night"


def is_non_clock_character(player: Any) -> bool:
    """True when *player* thinks in natural sky bands rather than HH:MM clock time."""
    if player is None:
        return False
    traits = getattr(player, "traits", None)
    if isinstance(traits, dict):
        if traits.get("no_clock_time") is True or traits.get("animal") is True:
            return True
        if str(traits.get("time_sense", "")).strip().lower() == "natural":
            return True
    tags = _norm_tags(getattr(player, "tags", None))
    if tags & NON_CLOCK_CHARACTER_TAGS:
        return True
    species = str(getattr(player, "species", "") or "").strip().lower()
    if species and species in NON_CLOCK_CHARACTER_TAGS:
        return True
    return False


def is_sundial_node(node: Any) -> bool:
    """True when an item node is a sun-dependent timepiece (sundial / horologium)."""
    if node is None:
        return False
    props = getattr(node, "properties", None) or {}
    if _norm_tags(props.get("tags")) & SUNDIAL_TAGS:
        return True
    name = str(getattr(node, "name", "") or "")
    return bool(_SUNDIAL_NAME_RE.search(name))


def is_timepiece_node(node: Any) -> bool:
    """True when an item node represents a clock, watch, phone, or sundial."""
    if node is None:
        return False
    if getattr(node, "type", "item") != "item":
        return False
    props = getattr(node, "properties", None) or {}
    if props.get("is_timepiece") is True:
        return True
    if props.get("is_timepiece") is False:
        return False
    if _norm_tags(props.get("tags")) & TIMEPIECE_TAGS:
        return True
    name = str(getattr(node, "name", "") or "")
    return bool(_TIMEPIECE_NAME_RE.search(name))


def _is_broken_timepiece(node: Any) -> bool:
    props = getattr(node, "properties", None) or {}
    state = str(props.get("current_state", "") or "").strip().lower()
    if state in BROKEN_TIMEPIECE_STATES:
        return True
    if props.get("powered") is False or props.get("working") is False:
        return True
    return False


def _world_hour_minute(world: Any) -> Optional[tuple[int, int]]:
    if world is None:
        return None
    hour_fn = getattr(world, "current_game_hour", None)
    mins_fn = getattr(world, "total_game_minutes", None)
    if not callable(hour_fn) or not callable(mins_fn):
        return None
    try:
        hour = int(hour_fn()) % 24
        minute = int(mins_fn() % 60)
        return hour, minute
    except Exception:
        return None


def area_has_window_to_sky(graph: Any, area_node: Any) -> bool:
    """True when an indoor area has a window tag or a see-through way to an open-sky area."""
    if area_node is None:
        return False
    props = getattr(area_node, "properties", None) or {}
    tags = _norm_tags(props.get("tags"))
    if "window" in tags or "windows" in tags or "skylight" in tags or props.get("has_window") is True:
        return True
    if graph is None:
        return False
    area_id = getattr(area_node, "id", None)
    if not area_id:
        return False
    try:
        edges = list(graph.get_edges_for_source(area_id)) + list(graph.get_edges_for_target(area_id))
    except Exception:
        return False
    for edge in edges:
        if getattr(edge, "type", None) not in ("way", EDGE_CONNECTION):
            continue
        other_id = edge.target if edge.source == area_id else edge.source
        way_node = graph.get_node(other_id)
        if way_node is None or getattr(way_node, "type", None) != "way":
            continue
        wprops = getattr(way_node, "properties", None) or {}
        wtags = _norm_tags(wprops.get("tags"))
        wname = str(getattr(way_node, "name", "") or "").lower()
        is_see_through = bool(wprops.get("see_through")) or "window" in wtags or "window" in wname
        if not is_see_through:
            continue
        try:
            way_edges = list(graph.get_edges_for_source(way_node.id)) + list(graph.get_edges_for_target(way_node.id))
        except Exception:
            continue
        for we in way_edges:
            if getattr(we, "type", None) not in ("way", EDGE_CONNECTION):
                continue
            dest_id = we.target if we.source == way_node.id else we.source
            if dest_id == area_id:
                continue
            dest_node = graph.get_node(dest_id)
            if dest_node is not None and getattr(dest_node, "type", None) == "area":
                dtags = (getattr(dest_node, "properties", None) or {}).get("tags")
                if is_open_sky(dtags):
                    return True
    return False


def describe_timepiece_reading(
    world: Any,
    item_node: Any,
    area_node: Any = None,
    viewer: Any = None,
) -> str:
    """Return a live time reading line for *item_node* if it is a timepiece, else ''."""
    if not is_timepiece_node(item_node):
        return ""
    hm = _world_hour_minute(world)
    if hm is None:
        return ""
    hour, minute = hm
    exact_time = f"{hour:02d}:{minute:02d}"
    band = natural_time_band(hour)

    if _is_broken_timepiece(item_node):
        return f"The {item_node.name} is not running and shows no reliable time."

    if viewer is None and hasattr(world, "players") and hasattr(world, "active_player"):
        viewer = world.players.get(world.active_player)

    if is_sundial_node(item_node):
        area_tags = (getattr(area_node, "properties", None) or {}).get("tags") if area_node else None
        if not is_open_sky(area_tags):
            return f"Indoors, the {item_node.name} casts no shadow."
        if hour < 5 or hour >= 19:
            return f"Without the sun, the {item_node.name} is unreadable."
        env = (getattr(area_node, "properties", None) or {}).get("environment", {}) if area_node else {}
        weather = normalize_weather(env.get("weather", "clear"))
        if weather in OBSCURING_SUNDIAL_WEATHER:
            return f"Under {weather} skies, the {item_node.name} casts only a faint blur - roughly {band}."
        rounded_min = int(round(minute / 15.0) * 15)
        disp_h, disp_m = hour, rounded_min
        if disp_m >= 60:
            disp_h = (disp_h + 1) % 24
            disp_m = 0
        if is_non_clock_character(viewer):
            return f"The shadow on the {item_node.name} marks {band}."
        return f"The shadow on the {item_node.name} falls near {disp_h:02d}:{disp_m:02d} ({band})."

    if is_non_clock_character(viewer):
        return f"The markings on the {item_node.name} mean nothing to you."

    return f"It reads {exact_time}."


def find_accessible_timepiece(world: Any, area_id: str) -> Optional[Any]:
    """Find a working timepiece carried/worn by the active player or visible in *area_id*."""
    graph = getattr(world, "graph", None)
    if graph is None:
        return None

    area_node = graph.get_node(area_id) if area_id else None
    area_tags = (getattr(area_node, "properties", None) or {}).get("tags") if area_node else None
    env = (getattr(area_node, "properties", None) or {}).get("environment", {}) if area_node else {}
    weather = normalize_weather(env.get("weather", "clear"))
    hm = _world_hour_minute(world)
    hour = hm[0] if hm else 12

    def _usable(node: Any) -> bool:
        if not is_timepiece_node(node) or _is_broken_timepiece(node):
            return False
        props = getattr(node, "properties", None) or {}
        if str(props.get("current_state", "") or "").strip().lower() == "hidden":
            return False
        if is_sundial_node(node):
            if not is_open_sky(area_tags):
                return False
            if hour < 5 or hour >= 19:
                return False
            if weather in OBSCURING_SUNDIAL_WEATHER:
                return False
        return True

    # 1. Carried or equipped by active player
    player_node_id = None
    getter = getattr(world, "_player_node_id", None)
    if callable(getter):
        try:
            player_node_id = getter(getattr(world, "active_player", None))
        except Exception:
            player_node_id = None
    if player_node_id:
        for edge_type in (EDGE_EQUIPPED, EDGE_CARRYING):
            for edge in graph.get_edges_for_target(player_node_id, edge_type):
                node = graph.get_node(edge.source)
                if _usable(node):
                    return node

    # 2. Visible in current area
    if area_id:
        for edge in graph.get_edges_for_target(area_id, EDGE_IN):
            node = graph.get_node(edge.source)
            if _usable(node):
                return node

    return None


def _moon_line(world: Any) -> Optional[str]:
    try:
        moon = world.current_moon_phase()
        moon_name = moon.get("name", "")
        moon_icon = moon.get("icon", "")
        if moon_name and moon_icon:
            return f"The moon is {_MOON_LABELS.get(moon_name, moon_name)} tonight. {moon_icon}"
    except Exception:
        pass
    return None


def resolve_guess_time(world: Any) -> List[str]:
    """Execute ``guess time`` for the active player, respecting timepieces, sky access, and lens."""
    area_id = world._get_current_area_id()
    if not area_id:
        return ["You can't guess the time in an empty void."]

    area_node = world.graph.get_node(area_id)
    area_props = (getattr(area_node, "properties", None) or {}) if area_node else {}
    area_tags = area_props.get("tags")
    env = area_props.get("environment", {}) if isinstance(area_props.get("environment"), dict) else {}

    viewer = None
    if hasattr(world, "players") and hasattr(world, "active_player"):
        viewer = world.players.get(world.active_player)
    natural_only = is_non_clock_character(viewer)

    hour = int(world.current_game_hour()) % 24
    minute = int(world.total_game_minutes() % 60)
    exact_time = f"{hour:02d}:{minute:02d}"
    band = natural_time_band(hour)

    # 1. Working timepiece (clock, watch, phone, or sunlit sundial)
    timepiece = find_accessible_timepiece(world, area_id)
    if timepiece is not None and not natural_only:
        reading = describe_timepiece_reading(world, timepiece, area_node=area_node, viewer=viewer)
        if reading:
            return [f"You glance at the {timepiece.name}. {reading}"]

    # 2. Open sky vs. indoor window vs. sealed indoors
    open_sky = is_open_sky(area_tags)
    has_window = False if open_sky else area_has_window_to_sky(world.graph, area_node)

    if not open_sky and not has_window:
        try:
            success, _total, _message = world.skills.skill_check("Survival", 18)
        except Exception:
            success = False
        if success:
            return [
                f"You're indoors with no view of the sky or a clock, though your internal sense puts it around {band}."
            ]
        return [
            "You're indoors with no view of the sky and no clock in sight - you have no reliable way to tell the time."
        ]

    # 3. Sky-reading Survival check (outdoors, or through a window with +3 DC)
    weather = normalize_weather(env.get("weather", "clear"))
    weather_dc = WEATHER_TIME_DC.get(weather, WEATHER_TIME_DC_DEFAULT)
    if has_window:
        weather_dc += 3

    try:
        success, total, _message = world.skills.skill_check("Survival", weather_dc)
    except Exception:
        success, total = False, 0

    window_prefix = "Through the window, " if has_window else ""
    out: List[str] = []

    if total >= weather_dc + 10:
        if natural_only:
            if 5 <= hour < 19:
                out.append(f"{window_prefix}the sun's height is unmistakable - it's {band}." if has_window
                           else f"The sun's height is unmistakable - it's {band}.")
            else:
                out.append(f"{window_prefix}the stars and moon tell you plainly: it's {band}." if has_window
                           else f"The stars and moon tell you plainly: it's {band}.")
        else:
            if 5 <= hour < 19:
                out.append(f"{window_prefix}the sun's position is clear to you. It's {exact_time}." if has_window
                           else f"The sun's position is clear to you. It's {exact_time}.")
            else:
                out.append(f"{window_prefix}the stars and moon give it away. It's {exact_time}." if has_window
                           else f"The stars and moon give it away. It's {exact_time}.")
    elif success:
        if natural_only:
            out.append(f"{window_prefix}by the sky, it feels like {band}." if has_window
                       else f"By the sky, it feels like {band}.")
        else:
            if minute < 15:
                out.append(f"{window_prefix}it's just after {hour:02d}:00." if has_window
                           else f"It's just after {hour:02d}:00.")
            elif minute < 45:
                out.append(f"{window_prefix}it's around {hour:02d}:30." if has_window
                           else f"It's around {hour:02d}:30.")
            else:
                next_hour = (hour + 1) % 24
                out.append(f"{window_prefix}it's almost {next_hour:02d}:00." if has_window
                           else f"It's almost {next_hour:02d}:00.")
        if hour >= 19 or hour < 5:
            ml = _moon_line(world)
            if ml:
                out.append(ml)
    elif total >= max(1, weather_dc - 5):
        approx_hour = (hour + (1 if minute >= 30 else 0)) % 24
        if natural_only:
            out.append(f"You squint at the sky - {band}, maybe, though you're not certain.")
        elif 5 <= hour < 19:
            out.append(
                f"You squint at the sky and guess it's {band} - sometime around {approx_hour:02d}:00, give or take an hour, though you're not certain."
            )
        else:
            out.append(
                f"You try to read the stars but the darkness confuses you - {band}, maybe around {approx_hour:02d}:00, give or take an hour."
            )
    else:
        if 5 <= hour < 19:
            out.append("It's daytime, you think. Probably around the middle of the day, but you can't be more specific than that.")
        else:
            out.append("It's night. Somewhere around the middle of the night, probably. You have no better idea.")

    return out
