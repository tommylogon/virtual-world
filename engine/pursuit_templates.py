"""Reusable character-pursuit templates for the background runner.

Templates are game-content definitions: they describe a reusable undertaking,
its purpose, the values a pursuit must supply, and the typed steps used by its
current short-term plan. They do not define ongoing activities or world-recipe
transformations.

A template is character-agnostic. Everything an instance fills in - the actor,
the places, the items, the times - arrives as a **binding**, and a step field
that names a place or an item must be a ``{"$binding": name}`` reference rather
than a literal (see :mod:`engine.plan_steps`). A template that hardcodes
``"area": "Scrap Pile"`` is a character-specific script wearing a template's
clothes, and the validator rejects it.

The schema carries the whole undertaking, not only its steps:

``purpose``        what the undertaking is for, in prose an author can read.
``parameters``     the values an instance must bind (area / tag_list / item_spec /
                   item_id).
``requirements``   condition leaves that must hold, in the shared trigger-leaf
                   vocabulary (:data:`engine.trigger_validator.CONDITION_TYPES`).
``supplies``       item specs the character is expected to be carrying.
``timing``         when the undertaking is timely, read from the world's existing
                   clock, season, weather and moon - no second calendar.
``steps``          the typed short-term plan, in the declared step vocabulary.
``progress``       named checks that say what "further along" means.
``stop_conditions``leaves that end the undertaking early.
``recipe``         an optional world-recipe reference (task-703 owns the store).

Unknown condition leaves and unknown step kinds fail closed: an unusable file is
reported through :func:`problems` and never silently half-loaded.

@module pursuit_templates
@contributes reusable pursuit templates for the background simulation
@docs docs/virtualWorld/design/Character Pursuits.md
"""
from __future__ import annotations

import json
import logging
import os
from copy import deepcopy
from typing import Dict, List, Optional, Tuple

from engine.plan_steps import (
    ALLOWED_STEP_KINDS,
    STEP_KINDS,
    STEP_KIND_COUNT,
    is_binding,
    library_ref_problems,
    step_problem,
)

logger = logging.getLogger(__name__)

ALLOWED_PARAMETER_TYPES = frozenset({"area", "tag_list", "item_spec", "item_id"})

#: Keys a ``timing`` block may declare. Each is read from existing world state by
#: :func:`timing_matches`; a key nothing reads would be authored dead data.
TIMING_KEYS = ("date", "hours", "season", "weather", "moon_phase", "sun", "daylight")

#: The daylight band, matching the engine's own ``on_day`` time trigger
#: (``virtual_world_engine.py:_fire_time_triggers``) rather than inventing one.
DAYLIGHT_HOURS = (6, 18)
SUN_UP_HOURS = (6, 18)

_cache: Dict[str, Dict[str, dict]] = {}
_problems: Dict[str, List[Tuple[str, str]]] = {}


def library_dir(data_dir: Optional[str] = None) -> str:
    """Directory used by the generic pursuit_templates library registry."""
    base = data_dir or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    return os.path.join(base, "library", "pursuit_templates")


def _binding_names(value):
    if isinstance(value, dict):
        if set(value) == {"$binding"}:
            name = value.get("$binding")
            return {str(name)} if name else {""}
        found = set()
        for child in value.values():
            found.update(_binding_names(child))
        return found
    if isinstance(value, list):
        found = set()
        for child in value:
            found.update(_binding_names(child))
        return found
    return set()


def _condition_types():
    """The shared condition-leaf vocabulary, imported lazily.

    ``engine/trigger_validator.py`` declares the leaf types the engine actually
    evaluates; importing it lazily keeps this module importable on its own (the
    validator pulls in the trigger system).
    """
    try:
        from engine.trigger_validator import CONDITION_TYPES
        return CONDITION_TYPES
    except Exception:  # pragma: no cover - validator always importable in-repo
        return frozenset()


def _leaf_problem(leaf, where: str) -> Optional[str]:
    """Why *leaf* is not a legal condition leaf, or ``None``.

    The check is against the shared vocabulary, not a private one: an unknown
    type is a leaf the engine cannot evaluate, so it fails closed here rather
    than resolving to False at runtime and reading as "the condition never held".
    """
    if not isinstance(leaf, dict):
        return f"{where} must be an object"
    ctype = leaf.get("type")
    if not isinstance(ctype, str) or not ctype.strip():
        return f"{where} needs a 'type'"
    known = _condition_types()
    if not known:
        return f"{where} cannot resolve the shared condition vocabulary"
    if ctype not in known:
        return f"{where} uses unknown condition type {ctype!r}"
    return None


def _item_spec_problem(spec, where: str) -> Optional[str]:
    if not isinstance(spec, dict):
        return f"{where} must be an object"
    tags = spec.get("tags", [])
    name = spec.get("name")
    if not isinstance(tags, list) or not all(isinstance(t, str) and t.strip() for t in tags):
        return f"{where} tags must be a list of strings"
    if name is not None and (not isinstance(name, str) or not name.strip()):
        return f"{where} name must be a non-empty string"
    if not tags and not name:
        return f"{where} needs at least one tag or a name"
    return None


def _parse_hhmm(value) -> Optional[int]:
    """``"HH:MM"`` -> minutes since midnight, or ``None`` when unparseable."""
    if not isinstance(value, str):
        return None
    parts = value.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour * 60 + minute


def _timing_problem(timing) -> Optional[str]:
    if not isinstance(timing, dict):
        return "timing must be an object"
    for key in timing:
        if key not in TIMING_KEYS:
            return f"timing declares unread key {key!r}"
    hours = timing.get("hours")
    if hours is not None:
        if not isinstance(hours, dict):
            return "timing.hours must be an object"
        for bound in ("after", "before"):
            if bound in hours and _parse_hhmm(hours[bound]) is None:
                return f"timing.hours.{bound} must be HH:MM"
    date = timing.get("date")
    if date is not None:
        if not isinstance(date, dict) or not date:
            return "timing.date must be a non-empty object"
        for part, value in date.items():
            if part not in ("day", "month", "year"):
                return f"timing.date declares unknown part {part!r}"
            values = value if isinstance(value, list) else [value]
            if (not values or any(isinstance(item, bool)
                                  or not isinstance(item, int) or item < 1
                                  for item in values)):
                return f"timing.date.{part} must be a positive integer or list"
    for key in ("season", "weather", "moon_phase"):
        value = timing.get(key)
        if value is None:
            continue
        if (not isinstance(value, list) or not value
                or not all(isinstance(item, str) and item.strip() for item in value)):
            return f"timing.{key} must be a non-empty list of strings"
    sun = timing.get("sun")
    if sun is not None:
        values = sun if isinstance(sun, list) else [sun]
        if not values or any(value not in ("up", "down") for value in values):
            return "timing.sun must be 'up', 'down', or a list of those values"
    if "daylight" in timing and not isinstance(timing["daylight"], bool):
        return "timing.daylight must be a boolean"
    return None


def _validate(entry_id: str, entry: dict) -> Optional[str]:
    if str(entry.get("id") or "") != entry_id:
        return "entry id must match its filename"
    if not isinstance(entry.get("version"), int) or entry["version"] < 1:
        return "version must be a positive integer"
    if not isinstance(entry.get("purpose"), str) or not entry["purpose"].strip():
        return "purpose must be a non-empty string"
    parameters = entry.get("parameters")
    if not isinstance(parameters, dict):
        return "parameters must be an object"
    for name, definition in parameters.items():
        if not isinstance(definition, dict):
            return f"parameter {name!r} must be an object"
        if definition.get("type") not in ALLOWED_PARAMETER_TYPES:
            return f"parameter {name!r} has an unsupported type"

    # Requirements, supplies, progress checks and stop conditions all speak the
    # shared condition/item vocabulary. One vocabulary, no parallel system.
    requirements = entry.get("requirements")
    if requirements is not None:
        if not isinstance(requirements, list):
            return "requirements must be a list"
        for index, leaf in enumerate(requirements):
            problem = _leaf_problem(leaf, f"requirements[{index}]")
            if problem:
                return problem

    supplies = entry.get("supplies")
    if supplies is not None:
        if not isinstance(supplies, list):
            return "supplies must be a list"
        for index, spec in enumerate(supplies):
            problem = _item_spec_problem(spec, f"supplies[{index}]")
            if problem:
                return problem

    progress = entry.get("progress")
    if progress is not None:
        if not isinstance(progress, list):
            return "progress must be a list"
        seen_ids = set()
        for index, item in enumerate(progress):
            if not isinstance(item, dict):
                return f"progress[{index}] must be an object"
            pid = item.get("id")
            if not isinstance(pid, str) or not pid.strip():
                return f"progress[{index}] needs a non-empty id"
            if pid in seen_ids:
                return f"progress id {pid!r} is declared twice"
            seen_ids.add(pid)
            if "check" in item:
                problem = _leaf_problem(item["check"], f"progress[{index}].check")
                if problem:
                    return problem

    stop_conditions = entry.get("stop_conditions")
    if stop_conditions is not None:
        if not isinstance(stop_conditions, list):
            return "stop_conditions must be a list"
        for index, leaf in enumerate(stop_conditions):
            problem = _leaf_problem(leaf, f"stop_conditions[{index}]")
            if problem:
                return problem

    recipe = entry.get("recipe")
    if recipe is not None:
        if not isinstance(recipe, dict):
            return "recipe must be an object"
        rid = recipe.get("id")
        if not isinstance(rid, str) or not rid.strip():
            return "recipe.id must be a non-empty string"

    duration = entry.get("duration")
    if duration is not None:
        if not isinstance(duration, dict) or set(duration) - {"minutes", "ticks"}:
            return "duration must contain only minutes and/or ticks"
        if len(duration) != 1:
            return "duration must declare exactly one of minutes or ticks"
        value = next(iter(duration.values()))
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            return "duration value must be a positive number"

    timing = entry.get("timing")
    if timing is not None:
        problem = _timing_problem(timing)
        if problem:
            return problem

    steps = entry.get("steps")
    if not isinstance(steps, list) or not steps:
        return "steps must be a non-empty list"
    for index, step in enumerate(steps):
        problem = step_problem(step, index)
        if problem:
            return problem
    binding_fields = ("requirements", "supplies", "timing", "progress",
                      "stop_conditions", "duration", "recipe", "steps")
    referenced = set().union(*(_binding_names(entry.get(field)) for field in binding_fields))
    unknown = referenced - set(parameters)
    if unknown:
        return f"template references undeclared bindings: {', '.join(sorted(unknown))}"
    return None


def _read_library(data_dir: Optional[str]):
    directory = library_dir(data_dir)
    catalog: Dict[str, dict] = {}
    problems: List[Tuple[str, str]] = []
    if not os.path.isdir(directory):
        return catalog, problems
    try:
        from engine.activities_loader import load as load_activity_defs
        activities = load_activity_defs()
    except Exception:
        activities = None
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".json"):
            continue
        entry_id = filename[:-5]
        try:
            with open(os.path.join(directory, filename), "r", encoding="utf-8-sig") as handle:
                entry = json.load(handle)
        except Exception as exc:
            problems.append((filename, f"unreadable: {exc}"))
            continue
        if not isinstance(entry, dict):
            problems.append((filename, "not a JSON object"))
            continue
        problem = _validate(entry_id, entry)
        if problem:
            problems.append((filename, problem))
            continue
        for index, step in enumerate(entry["steps"]):
            problem = library_ref_problems(step, index, activities)
            if problem:
                problems.append((filename, problem))
                break
        else:
            catalog[entry_id] = entry
    return catalog, problems


def load(data_dir: Optional[str] = None, *, fresh: bool = False) -> Dict[str, dict]:
    """Load the reusable pursuit-template catalog, reporting unusable files."""
    key = os.path.abspath(library_dir(data_dir))
    if fresh or key not in _cache:
        catalog, problems = _read_library(data_dir)
        _cache[key] = catalog
        _problems[key] = problems
        for filename, reason in problems:
            logger.warning("Pursuit template %s is unusable: %s", filename, reason)
    return _cache[key]


def reload(data_dir: Optional[str] = None) -> Dict[str, dict]:
    """Refresh after a library edit."""
    return load(data_dir, fresh=True)


def problems(data_dir: Optional[str] = None) -> List[Tuple[str, str]]:
    load(data_dir)
    return list(_problems.get(os.path.abspath(library_dir(data_dir)), []))


def _item_spec(properties: dict, name: Optional[str] = None) -> Optional[dict]:
    """Read an item spec off an assignment.

    The spec is read under the parameter's own name first, so a template that
    declares ``"bed_spec"`` binds ``{"bed_spec": ...}`` rather than having to
    guess the key. The legacy ``item``/``item_name`` keys are still read, which
    is what the existing haul/gather assignments carry.
    """
    if name is not None:
        direct = properties.get(name)
        if isinstance(direct, dict):
            return direct
        if isinstance(direct, str) and direct.strip():
            return {"tags": [direct.strip()], "name": None}
    tag = properties.get("item")
    name_key = properties.get("item_name")
    if tag is not None and not isinstance(tag, str):
        return None
    if name_key is not None and not isinstance(name_key, str):
        return None
    spec = {"tags": [str(tag)] if tag else [], "name": str(name_key) if name_key else None}
    return spec if spec["tags"] or spec["name"] else None


def _parameter_value(name: str, definition: dict, properties: dict):
    kind = definition.get("type")
    if kind == "item_id":
        value = properties.get(name)
        return value.strip() if isinstance(value, str) and value.strip() else None
    if kind == "item_spec":
        return _item_spec(properties, name)
    value = properties.get(name)
    if kind == "tag_list":
        if (not isinstance(value, list)
                or not all(isinstance(item, str) and item.strip() for item in value)):
            return None
        cleaned = [item.strip() for item in value]
        return cleaned or None
    if kind == "area":
        return value.strip() if isinstance(value, str) and value.strip() else None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _expand(value, bindings):
    if isinstance(value, dict):
        if set(value) == {"$binding"}:
            name = value["$binding"]
            return deepcopy(bindings[name])
        return {key: _expand(child, bindings) for key, child in value.items()}
    if isinstance(value, list):
        return [_expand(child, bindings) for child in value]
    return value


def _valid_bound_value(kind, value):
    if kind == "item_id":
        return isinstance(value, str) and bool(value.strip())
    if kind == "area":
        return isinstance(value, str) and bool(value.strip())
    if kind == "tag_list":
        return isinstance(value, list) and bool(value) and all(
            isinstance(item, str) and item.strip() for item in value)
    if kind == "item_spec":
        if not isinstance(value, dict):
            return False
        tags = value.get("tags", [])
        name = value.get("name")
        return (isinstance(tags, list)
                and all(isinstance(tag, str) and tag.strip() for tag in tags)
                and (name is None or (isinstance(name, str) and bool(name.strip())))
                and (bool(tags) or bool(name)))
    return False


def instantiate(template_id: str, bindings: dict, *, data_dir: Optional[str] = None):
    """Build an instance from already-resolved bindings, failing closed."""
    entry = load(data_dir).get(str(template_id or "").strip())
    if entry is None:
        return None
    if not isinstance(bindings, dict):
        return None
    resolved = {}
    for name, definition in entry["parameters"].items():
        value = bindings.get(name)
        if value is None:
            if definition.get("required", True):
                return None
            continue
        if not _valid_bound_value(definition.get("type"), value):
            return None
        resolved[name] = deepcopy(value)
    try:
        steps = _expand(entry["steps"], resolved)
        structured = {
            key: _expand(entry[key], resolved)
            for key in ("requirements", "supplies", "timing", "progress",
                        "stop_conditions", "duration", "recipe")
            if key in entry
        }
    except (KeyError, TypeError):
        return None
    instance = {
        "template_id": entry["id"],
        "template_version": entry["version"],
        "name": entry.get("name"),
        "purpose": entry["purpose"],
        "bindings": resolved,
        "steps": steps,
    }
    instance.update(structured)
    return instance


def bind(template_id: str, properties: dict, *, data_dir: Optional[str] = None):
    """Resolve a character-agnostic template against one authored assignment.

    Returns an executable instance description, or ``None`` when a required
    binding is absent or malformed. Unknown template ids fail closed.
    """
    entry = load(data_dir).get(str(template_id or "").strip())
    if entry is None:
        return None
    properties = properties if isinstance(properties, dict) else {}
    bindings = {}
    for name, definition in entry["parameters"].items():
        value = _parameter_value(name, definition, properties)
        if value is None:
            if definition.get("required", True):
                return None
            continue
        bindings[name] = value
    return instantiate(template_id, bindings, data_dir=data_dir)


# ───────────────────────────── timing ────────────────────────────────────────

def _world_call(world, name, default=None):
    """Read one accessor off the world, tolerating a stand-in object.

    The world exposes its clock as properties (``current_game_hour`` etc.), so a
    plain attribute read is the only case that can reach a real value. A callable
    is called for the rare test double that models the clock as a method; anything
    else is the stand-in and the default comes back.
    """
    if world is None:
        return default
    getter = getattr(world, name, None)
    if callable(getter):
        try:
            return getter()
        except Exception:
            return default
    return getter if getter is not None else default


def _current_weather(world) -> str:
    schedule = getattr(world, "forecast_schedule", None) or {}
    if not isinstance(schedule, dict):
        return ""
    return str(schedule.get("current_state") or "").strip().lower()


def timing_matches(entry: dict, world) -> bool:
    """Whether *entry*'s timing block is satisfied by the world's own clock.

    Reads the existing world state and nothing else: ``game_day`` / month / year
    for the date, ``current_game_hour`` for time and the existing ``on_day`` sun
    band, ``current_season``, ``forecast_schedule.current_state`` for weather,
    and ``current_moon_phase`` for the moon. The engine has no separate global
    sun-position source; ``sun: up/down`` uses the same daylight interval as its
    ``on_day`` trigger. A template with no ``timing`` block is always timely.

    This is a *prompt* input for selection (task-704), not a gate the executor
    enforces: a character already mid-pursuit is not stopped by dusk.
    """
    timing = entry.get("timing") if isinstance(entry, dict) else None
    if not isinstance(timing, dict) or not timing:
        return True

    date = timing.get("date") or {}
    if date:
        game_day = _world_call(world, "game_day", None)
        if game_day is None:
            return False
        calendar = getattr(world, "calendar_config", None) or {}
        try:
            days_per_month = max(1, int(calendar.get("days_per_month", 30)))
            current_date = {
                "day": ((int(game_day) - 1) % days_per_month) + 1,
                "month": int(_world_call(world, "game_month", 0)),
                "year": int(_world_call(world, "game_year", 0)),
            }
        except (TypeError, ValueError):
            return False
        for part, allowed in date.items():
            values = allowed if isinstance(allowed, list) else [allowed]
            if current_date.get(part) not in values:
                return False

    hours = timing.get("hours") or {}
    if isinstance(hours, dict) and hours:
        hour = _world_call(world, "current_game_hour", None)
        if hour is None:
            return False
        after = _parse_hhmm(hours.get("after"))
        before = _parse_hhmm(hours.get("before"))
        if after is not None and int(hour) * 60 < after:
            return False
        if before is not None and int(hour) * 60 >= before:
            return False

    season = timing.get("season")
    if season:
        current = str(_world_call(world, "current_season", "") or "").lower()
        if current not in {str(s).lower() for s in season}:
            return False

    weather = timing.get("weather")
    if weather:
        if _current_weather(world) not in {str(s).lower() for s in weather}:
            return False

    moon = timing.get("moon_phase")
    if moon:
        phase = _world_call(world, "current_moon_phase", {}) or {}
        name = str(phase.get("name") or "").lower() if isinstance(phase, dict) else ""
        if name not in {str(s).lower() for s in moon}:
            return False

    if timing.get("daylight") is True:
        hour = _world_call(world, "current_game_hour", None)
        if hour is None:
            return False
        if not (DAYLIGHT_HOURS[0] <= int(hour) <= DAYLIGHT_HOURS[1]):
            return False

    sun = timing.get("sun")
    if sun is not None:
        hour = _world_call(world, "current_game_hour", None)
        if hour is None:
            return False
        sun_state = "up" if SUN_UP_HOURS[0] <= int(hour) <= SUN_UP_HOURS[1] else "down"
        allowed = sun if isinstance(sun, list) else [sun]
        if sun_state not in allowed:
            return False

    return True
