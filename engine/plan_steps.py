"""The short-term plan step vocabulary, declared once (task-701/702).

A pursuit template's ``steps`` are data, so the set of step *kinds* an author may
write is a declared contract rather than whatever an ``if`` chain happens to
answer to. This module is that single declaration: the template validator
(``engine/pursuit_templates.py``) and the executor (``engine/plan_executor.py``)
both read it, so a kind cannot be executable without being declarable, or
declarable without a primitive behind it.

Each entry states the fields the kind carries, which of them must be a
``$binding`` reference instead of a literal, and which literal values must
resolve in a library. A key that is not in ``fields`` is not part of the
vocabulary: the validator rejects the step rather than passing an unknown key
through to a primitive that would silently ignore it.

Two rules are load-bearing and are enforced here rather than in prose:

* **No literals where a binding belongs.** A field listed in ``bound`` must be a
  ``{"$binding": name}`` reference. A template that hardcodes ``"area": "Scrap
  Pile"`` is a character-specific script, not a reusable undertaking, and it is
  the failure mode task-701's "no character-specific proper names" criterion
  exists to catch.
* **Library references must resolve.** A field listed in ``library_refs`` names
  an entry in another library (an Activity definition), and an id nothing
  defines fails closed at load time.

@module plan_steps
@contributes the declared short-term plan step vocabulary shared by the template validator and the plan executor
@docs docs/virtualWorld/design/Character Pursuits.md
"""
from __future__ import annotations

from typing import Dict, Tuple

#: Every step kind the vocabulary declares, with its contract.
#:
#: ``fields``      - every key a step of this kind may carry.
#: ``bound``       - keys whose value MUST be a ``{"$binding": name}`` reference.
#: ``library_refs``- keys whose literal value must resolve in a library.
#: ``summary``     - what the primitive does, for the index report.
STEP_KINDS: Dict[str, dict] = {
    "travel": {
        "summary": "Walk toward a place: a named area, or any area carrying tags.",
        "fields": ("area", "tags", "to"),
        "required": (),
        "bound": ("area", "tags"),
        "library_refs": (),
    },
    "take": {
        "summary": "Pick up an item matching a spec from the current area.",
        "fields": ("spec",),
        "required": ("spec",),
        "bound": ("spec",),
        "library_refs": (),
    },
    "drop": {
        "summary": "Put down a carried item matching a spec, here.",
        "fields": ("spec",),
        "required": ("spec",),
        "bound": ("spec",),
        "library_refs": (),
    },
    "activity": {
        "summary": "Start or continue a persistent Activity from the activity library.",
        "fields": ("activity", "target_item", "recipe", "duration_minutes",
                   "duration_ticks", "catch_count_target"),
        "required": ("activity",),
        "bound": ("target_item",),
        "library_refs": ("activity",),
    },
    "wait": {
        "summary": "Let game time pass, as a visible waiting Activity.",
        "fields": ("activity", "duration_minutes", "duration_ticks"),
        "required": ("activity",),
        "bound": (),
        "library_refs": ("activity",),
    },
}

#: The count, stated so a reader never enumerates the set from one member.
STEP_KIND_COUNT = len(STEP_KINDS)

#: Kinds an author may write. Derived, never hand-listed.
ALLOWED_STEP_KINDS = frozenset(STEP_KINDS)

#: Fields every kind accepts, for the "unknown key" check.
KNOWN_STEP_FIELDS = frozenset(
    field for entry in STEP_KINDS.values() for field in entry["fields"]
)


def is_binding(value) -> bool:
    """Whether *value* is a ``{"$binding": name}`` reference."""
    return isinstance(value, dict) and set(value) == {"$binding"} and bool(value.get("$binding"))


def step_problem(step, index: int):
    """Why *step* is not a legal vocabulary step, or ``None`` when it is.

    Checks the kind, the field set, the binding rule and (via
    :func:`library_ref_problems`) the library references. Returns a human-readable
    reason; the caller records it and fails the whole template closed.
    """
    if not isinstance(step, dict):
        return f"step {index} must be an object"
    kind = step.get("kind")
    if kind not in STEP_KINDS:
        return f"step {index} has unsupported kind {kind!r}"
    entry = STEP_KINDS[kind]
    allowed = set(entry["fields"])
    for key in step:
        if key == "kind":
            continue
        if key not in allowed:
            return f"step {index} ({kind}) carries undeclared field {key!r}"
    missing = [key for key in entry["required"] if key not in step]
    if missing:
        return f"step {index} ({kind}) needs {', '.join(repr(key) for key in missing)}"
    if kind == "travel":
        has_area = "area" in step
        has_tags = "tags" in step
        if has_area == has_tags:
            return f"step {index} (travel) needs exactly one of 'area' or 'tags'"
        if has_tags and not isinstance(step["tags"], dict):
            return f"step {index} (travel) 'tags' must be a $binding reference"
        if "to" in step:
            target_label = step["to"]
            if not (isinstance(target_label, str) and target_label.strip()) and not is_binding(target_label):
                return (f"step {index} (travel) 'to' must be a non-empty label "
                        "or a $binding reference")
    for key in entry["bound"]:
        if key in step and not is_binding(step[key]):
            return (f"step {index} ({kind}) field {key!r} must be a "
                    f"$binding reference, not a literal")
    return None


def library_ref_problems(step, index: int, activities):
    """Why a step's library references do not resolve, or ``None``.

    *activities* is the activity catalog (``engine.activities_loader.load()``).
    An id nothing defines fails closed: a step that names a nonexistent Activity
    would otherwise start nothing and read as a low event rate.
    """
    kind = step.get("kind")
    entry = STEP_KINDS.get(kind)
    if not entry:
        return None
    for key in entry["library_refs"]:
        value = step.get(key)
        if value is None:
            if kind == "activity" and key == "activity":
                return f"step {index} ({kind}) needs an 'activity' id"
            continue
        if not isinstance(value, str) or not value.strip():
            return f"step {index} ({kind}) field {key!r} must be a non-empty id"
        if not isinstance(activities, dict):
            return f"step {index} ({kind}) cannot resolve Activity catalog"
        if value.strip() not in activities:
            return (f"step {index} ({kind}) references unknown activity "
                    f"{value.strip()!r}")
    recipe = step.get("recipe")
    if recipe is not None and (not isinstance(recipe, str) or not recipe.strip()):
        return f"step {index} ({kind}) field 'recipe' must be a non-empty id"
    return None
