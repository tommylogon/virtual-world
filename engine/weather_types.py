"""
Weather-type registry (task-772)
================================
The weather vocabulary as **library data**, not a hardcoded list.

`data/library/weather/<id>.json` holds one record per weather type:

    id, name, kind ("normal" | "extreme"), order, icon,
    light_mult, time_dc, description, tags

so a world can add, edit or remove a type (acid rain, ion storm, a flash freeze)
through the library surface instead of a code change. This module is the engine
side of that registry: it loads the records and derives the tables the rest of
the engine and the UI read, so the state list, the guess-time DC, the light
multiplier and the sky prose cannot drift into parallel copies again (the
one-copy rule bug-54 established).

When the registry directory is missing or empty (a bare checkout, a unit test
that never wrote records) the built-in `FALLBACK_TYPES` reproduce the original
seven states exactly, so behaviour is unchanged.

Readers import from here (or, for compatibility, from `engine.weather_forecast`,
which re-exports these names):

    WEATHER_STATES        ordered list of ids
    WEATHER_TIME_DC       id -> survival DC for guessing the sky
    WEATHER_LIGHT_MULT    id -> ambient-light multiplier
    WEATHER_PROSE         id -> one sentence, "" to say nothing
    normalize_weather()   canonical id for any spelling, "" if unknown
    weather_light_mult()  light multiplier for a raw value, 1.0 if unknown

@module weather_types
@contributes the weather-type registry and the derived vocabulary tables
@powers weather states, guess-time DC, light multiplier and sky prose from library data
@relates engine/weather_forecast.py (re-exports these); data/library/weather/*.json
@docs docs/design/weather-world-integration.md
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent

#: One file per weather type: ``data/library/weather/<id>.json``.
REGISTRY_DIR = REPO_ROOT / "data" / "library" / "weather"

#: Survival DC for a type with no ``time_dc`` (and for an unknown value).
WEATHER_TIME_DC_DEFAULT = 15

#: Spellings seen in older and hand-authored worlds, mapped to a canonical id.
#: Read-time only: nothing rewrites a stored value. Kept in code (not data)
#: because it is *spelling* normalisation, not weather content.
WEATHER_ALIASES = {
    "sun": "clear",
    "sunny": "clear",
    "fair": "clear",
    "overcast": "cloudy",
    "rain": "rainy",
    "showers": "rainy",
    "drizzle": "rainy",
    "storm": "stormy",
    "downpour": "stormy",
    # "thunderstorm" and "blizzard" are no longer folded into stormy/snowy:
    # they are their own extreme types now (task-763), so a world's schedule can
    # name them and they resolve to the record instead of its milder cousin.
    "snow": "snowy",
    "sleet": "snowy",
    "wind": "windy",
    "fog": "foggy",
    "mist": "foggy",
}

#: The seven original states, used when the registry is absent. Values are
#: lifted verbatim from the tables this module replaced, so a bare checkout and
#: a populated library produce identical behaviour.
FALLBACK_TYPES: Dict[str, dict] = {
    "clear": {"id": "clear", "name": "Clear", "kind": "normal", "order": 1,
              "icon": "\u2600\ufe0f", "light_mult": 1.0, "time_dc": 10,
              "description": "", "tags": ["weather", "sky", "dry"]},
    "cloudy": {"id": "cloudy", "name": "Cloudy", "kind": "normal", "order": 2,
               "icon": "\u2601\ufe0f", "light_mult": 0.7, "time_dc": 15,
               "description": "A flat grey lid of cloud sits over the place.",
               "tags": ["weather", "sky"]},
    "windy": {"id": "windy", "name": "Windy", "kind": "normal", "order": 3,
              "icon": "\U0001f4a8", "light_mult": 0.8, "time_dc": 16,
              "description": "", "tags": ["weather", "sky"]},
    "rainy": {"id": "rainy", "name": "Rainy", "kind": "normal", "order": 4,
              "icon": "\U0001f327\ufe0f", "light_mult": 0.5, "time_dc": 18,
              "description": "Rain is falling, cold and steady.",
              "tags": ["weather", "sky", "wet"]},
    "stormy": {"id": "stormy", "name": "Stormy", "kind": "normal", "order": 5,
               "icon": "\u26c8\ufe0f", "light_mult": 0.3, "time_dc": 20,
               "description": "The storm is breaking overhead \u2014 rain lashes "
                              "sideways and the wind screams.",
               "tags": ["weather", "sky", "wet", "extreme"]},
    "foggy": {"id": "foggy", "name": "Foggy", "kind": "normal", "order": 6,
              "icon": "\U0001f32b\ufe0f", "light_mult": 0.4, "time_dc": 18,
              "description": "Fog has swallowed the place; shapes fade a short "
                             "way off.",
              "tags": ["weather", "sky"]},
    "snowy": {"id": "snowy", "name": "Snowy", "kind": "normal", "order": 7,
              "icon": "\U0001f328\ufe0f", "light_mult": 0.6, "time_dc": 18,
              "description": "Snow is falling, and it muffles every sound.",
              "tags": ["weather", "sky", "cold"]},
}

_TYPES: Dict[str, dict] | None = None
WEATHER_STATES: List[str] = []
WEATHER_TIME_DC: Dict[str, int] = {}
WEATHER_LIGHT_MULT: Dict[str, float] = {}
WEATHER_PROSE: Dict[str, str] = {}


def _ordered(reg: Dict[str, dict]) -> Dict[str, dict]:
    """Registry in canonical order: by ``order`` then id (stable, total)."""
    def key(item):
        rid, rec = item
        try:
            order = int(rec.get("order", 10_000))
        except (TypeError, ValueError):
            order = 10_000
        return (order, rid)
    return dict(sorted(reg.items(), key=key))


def _load() -> Dict[str, dict]:
    reg: Dict[str, dict] = {}
    try:
        paths = sorted(REGISTRY_DIR.glob("*.json")) if REGISTRY_DIR.is_dir() else []
    except OSError:
        paths = []
    for path in paths:
        try:
            rec = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if isinstance(rec, dict):
            rid = str(rec.get("id") or path.stem)
            rec.setdefault("id", rid)
            reg[rid] = rec
    if not reg:
        reg = {k: dict(v) for k, v in FALLBACK_TYPES.items()}
    return _ordered(reg)


def _refresh() -> None:
    """Rebuild the derived tables from the (cached) registry."""
    global _TYPES, WEATHER_STATES, WEATHER_TIME_DC, WEATHER_LIGHT_MULT, WEATHER_PROSE
    if _TYPES is None:
        _TYPES = _load()
    WEATHER_STATES = list(_TYPES.keys())
    WEATHER_TIME_DC = {
        rid: int(rec.get("time_dc", WEATHER_TIME_DC_DEFAULT))
        for rid, rec in _TYPES.items()
    }
    WEATHER_LIGHT_MULT = {
        rid: float(rec.get("light_mult", 1.0)) for rid, rec in _TYPES.items()
    }
    WEATHER_PROSE = {
        rid: str(rec.get("description", "")) for rid, rec in _TYPES.items()
    }


def weather_types() -> Dict[str, dict]:
    """The registry as ``id -> record`` (cached). Falls back to FALLBACK_TYPES."""
    if _TYPES is None:
        _refresh()
    return _TYPES  # type: ignore[return-value]


def reload() -> None:
    """Re-read the registry from disk and rebuild the derived tables."""
    global _TYPES
    _TYPES = None
    _refresh()


def normalize_weather(value: Any) -> str:
    """Canonical weather id for any input, ``""`` when it is not a type.

    Readers go through this so one alias table serves the light multiplier, the
    skill DC and the prose. Returns ``""`` rather than guessing, so an unknown
    value still falls through to each reader's default instead of silently
    becoming ``clear``.
    """
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = WEATHER_ALIASES.get(text, text)
    return text if text in weather_types() else ""


def weather_light_mult(weather: Any) -> float:
    """Ambient light multiplier for a weather value, ``1.0`` when unknown.

    Returns ``1.0`` for an unset or unrecognised value, so a world with no
    forecast is completely unaffected — only a world that actually authors
    weather sees its light change (bug-54).
    """
    rec = weather_types().get(normalize_weather(weather))
    return float(rec.get("light_mult", 1.0)) if rec else 1.0


#: Fields every weather record must carry.
REQUIRED_FIELDS = ("id", "name", "kind", "icon", "light_mult", "time_dc",
                   "description", "tags")

#: Allowed values of ``kind``.
KINDS = ("normal", "extreme")


def record_problems(entry_id: str, rec: Any) -> List[str]:
    """Validation problems for one weather record, ``[]`` when it is valid.

    The single validator: the library save route
    (``routes/library_ops._vocabulary_problems``) and
    ``tools/weather_library_check.py`` both call this, so a record that saves is
    a record the gate accepts and vice versa.
    """
    if not isinstance(rec, dict):
        return ["record must be an object"]
    problems: List[str] = []
    rid = rec.get("id")
    if isinstance(rid, str) and rid != entry_id:
        problems.append(f"id {rid!r} must match the entry id {entry_id!r}")
    for field in REQUIRED_FIELDS:
        if field not in rec:
            problems.append(f"missing required field {field!r}")
    if "kind" in rec and rec["kind"] not in KINDS:
        problems.append(f"kind {rec['kind']!r} must be one of {KINDS}")
    if "light_mult" in rec and not isinstance(rec["light_mult"], (int, float)):
        problems.append("light_mult must be a number")
    if "time_dc" in rec and not isinstance(rec["time_dc"], int):
        problems.append("time_dc must be an integer")
    if "tags" in rec and not (isinstance(rec["tags"], list)
                              and all(isinstance(t, str) for t in rec["tags"])):
        problems.append("tags must be a list of strings")
    if "description" in rec and not isinstance(rec["description"], str):
        problems.append("description must be a string")
    return problems


_refresh()
