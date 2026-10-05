"""Reusable character-pursuit templates for the background runner.

Templates are game-content definitions: they describe a reusable undertaking,
its purpose, the values a pursuit must supply, and the typed steps used by its
current short-term plan. They do not define ongoing activities or world-recipe
transformations.

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

logger = logging.getLogger(__name__)

ALLOWED_STEP_KINDS = frozenset({"travel", "take", "drop"})
ALLOWED_PARAMETER_TYPES = frozenset({"area", "tag_list", "item_spec"})
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
    steps = entry.get("steps")
    if not isinstance(steps, list) or not steps:
        return "steps must be a non-empty list"
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            return f"step {index} must be an object"
        if step.get("kind") not in ALLOWED_STEP_KINDS:
            return f"step {index} has unsupported kind {step.get('kind')!r}"
    unknown = set().union(*(_binding_names(step) for step in steps)) - set(parameters)
    if unknown:
        return f"steps reference undeclared bindings: {', '.join(sorted(unknown))}"
    return None


def _read_library(data_dir: Optional[str]):
    directory = library_dir(data_dir)
    catalog: Dict[str, dict] = {}
    problems: List[Tuple[str, str]] = []
    if not os.path.isdir(directory):
        return catalog, problems
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


def _item_spec(properties: dict) -> Optional[dict]:
    tag = properties.get("item")
    name = properties.get("item_name")
    if tag is not None and not isinstance(tag, str):
        return None
    if name is not None and not isinstance(name, str):
        return None
    spec = {"tags": [str(tag)] if tag else [], "name": str(name) if name else None}
    return spec if spec["tags"] or spec["name"] else None


def _parameter_value(name: str, definition: dict, properties: dict):
    kind = definition.get("type")
    if kind == "item_spec":
        return _item_spec(properties)
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
    except (KeyError, TypeError):
        return None
    return {
        "template_id": entry["id"],
        "template_version": entry["version"],
        "purpose": entry["purpose"],
        "bindings": resolved,
        "steps": steps,
    }


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

