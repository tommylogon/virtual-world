"""Trigger effect resolution helpers.

Moved from engine/trigger_system.py.
"""

from typing import List, Optional


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
    """Resolve trigger effects from edge props, then linked trigger node, then legacy fields."""
    sources = [trigger_edge.properties]
    target_node = graph.get_node(trigger_edge.target)
    if target_node:
        sources.append(target_node.properties)

    for props in sources:
        resolved = _effects_list_from_properties(props)
        if resolved:
            return resolved

    return [{"type": "message", "params": {}}]
