"""Trigger effect resolution helpers.

Moved from engine/trigger_system.py.

Also owns the shape normalisers for ``properties['triggers']``. An item-library
round trip once wrote a trigger definition wrapped under its own key
(``{"item": {...}}``, and the same wrapper around ``effects``), so the store on
disk holds definitions, wrapper objects and wrapper lists in the same field.
Normalise on the way in (bug-566) instead of teaching every reader the shapes.
"""

from typing import List, Optional


# Keys a real trigger definition carries. A single-key dict whose key is not in
# this set is treated as a wrapper around its value, not as a definition.
_TRIGGER_FIELDS = frozenset({
    "id", "name", "trigger_type", "effects", "effect_type", "effect_params",
    "condition", "conditions", "conditions_logic", "target_name", "target_tag",
    "target_state", "success_message", "fail_message", "once", "fired",
    "cooldown",
})


def _looks_like_trigger(value) -> bool:
    return isinstance(value, dict) and bool(_TRIGGER_FIELDS & set(value))


def _unwrap_single_key(value, *, scalar: bool = False):
    """Unwrap ``{key: inner}`` wrappers, repeatedly.

    Only a dict with one key outside the trigger vocabulary is a wrapper. A
    definition, a condition leaf and an effect all carry at least one known key,
    so they are returned untouched. ``scalar`` allows unwrapping a wrapped
    scalar (``{"item": "on_use"}``), which only makes sense for a field value.
    """
    for _ in range(8):
        if not isinstance(value, dict) or len(value) != 1 or _looks_like_trigger(value):
            return value
        inner = next(iter(value.values()))
        if not scalar and not isinstance(inner, (dict, list)):
            return value
        value = inner
    return value


def normalize_trigger_entry(entry):
    """Return one trigger definition as a dict, or ``None`` when unusable.

    Accepts a definition, a single-key wrapper around one, or a definition whose
    ``effects`` / ``trigger_type`` / ``conditions`` values are themselves
    wrapped. Effects without a ``type`` are dropped rather than passed to the
    engine.
    """
    entry = _unwrap_single_key(entry)
    if not isinstance(entry, dict) or not entry:
        return None
    entry = dict(entry)

    for key in ("trigger_type", "effects", "conditions", "condition"):
        if isinstance(entry.get(key), dict):
            entry[key] = _unwrap_single_key(entry[key], scalar=True)

    effects = entry.get("effects")
    if isinstance(effects, dict):
        effects = [effects]
    if isinstance(effects, list):
        fixed = []
        for effect in effects:
            effect = _unwrap_single_key(effect)
            if isinstance(effect, dict) and effect.get("type"):
                fixed.append(dict(effect))
        if fixed:
            entry["effects"] = fixed
        else:
            entry.pop("effects", None)

    if entry.get("conditions") in ("", None):
        entry.pop("conditions", None)
    return entry


def normalize_trigger_list(value) -> List[dict]:
    """Return ``properties['triggers']`` as a list of definitions.

    A bare definition, a wrapper around a definition, a wrapper around a list
    and a plain list all normalise to the same list. Non-dict entries are
    dropped. The input is never mutated.
    """
    if value is None:
        return []
    unwrapped = _unwrap_single_key(value)
    if isinstance(unwrapped, list):
        raw = unwrapped
    elif isinstance(value, list):
        raw = value
    else:
        raw = [unwrapped]
    out: List[dict] = []
    for item in raw:
        entry = normalize_trigger_entry(item)
        if entry is not None:
            out.append(entry)
    return out


def _legacy_effects_from_properties(props: dict) -> Optional[List[dict]]:
    """Synthesize ``effects[]`` from pre-migration ``effect_type`` + ``effect_params``."""
    effect_type = props.get("effect_type")
    if isinstance(effect_type, list):
        effect_type = effect_type[0] if effect_type else None
    if not effect_type:
        return None
    effect_type = str(effect_type)

    raw_params = props.get("effect_params")
    params = dict(raw_params) if isinstance(raw_params, dict) else {}

    if effect_type == "message":
        message_params = dict(params)
        if not message_params.get("message"):
            message_params["message"] = props.get("success_message") or ""
        if props.get("fail_message") and not message_params.get("fail_message"):
            message_params["fail_message"] = props.get("fail_message")
        return [{"type": "message", "params": message_params}]

    if effect_type == "damage":
        narrative = params.pop("message", None)
        effects = [{"type": "damage", "params": params}]
        if narrative and str(narrative).strip():
            effects.append({"type": "message", "params": {"message": narrative}})
        return effects

    return [{"type": effect_type, "params": params}]


def _effects_list_from_properties(props: Optional[dict]) -> Optional[List[dict]]:
    """Return ``effects[]`` from props, falling back to legacy flat fields."""
    if not props:
        return None

    effects = props.get("effects")
    if isinstance(effects, list) and effects:
        typed = [effect for effect in effects if isinstance(effect, dict) and effect.get("type")]
        if typed:
            return typed

    return _legacy_effects_from_properties(props)


def _resolve_trigger_effects(trigger_edge, graph) -> List[dict]:
    """Resolve trigger effects from property dict, edge props, or linked trigger node."""
    if isinstance(trigger_edge, dict):
        sources = [trigger_edge]
    elif hasattr(trigger_edge, "properties"):
        sources = [trigger_edge.properties]
    else:
        sources = []

    target = getattr(trigger_edge, "target", None)
    if target and graph is not None:
        target_node = graph.get_node(target)
        if target_node:
            sources.append(target_node.properties)

    for props in sources:
        resolved = _effects_list_from_properties(props)
        if resolved:
            return resolved

    return [{"type": "message", "params": {}}]
