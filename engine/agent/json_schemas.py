"""Structured output JSON schemas for LLM calls (Phase 1 Python agent migration).

Single source of truth for provider-enforced ``response_format`` payloads
(``json_schema`` strict mode + ``json_object`` fallback). Mirrors and supersedes
``static/js/shared/json-schemas.ts``.
"""
from __future__ import annotations

from typing import Any, Dict

NULLABLE_STR: Dict[str, Any] = {"type": ["string", "null"]}


def _wrap_schema(name: str, schema: Dict[str, Any], strict: bool = True) -> Dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": strict,
            "schema": schema,
        },
    }


AGENT_ACTION: Dict[str, Any] = _wrap_schema(
    "agent_action",
    {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "inner_monologue": NULLABLE_STR,
            "action": NULLABLE_STR,
            "item": NULLABLE_STR,
            "target": NULLABLE_STR,
            "text": NULLABLE_STR,
            "speech": NULLABLE_STR,
            "volume": NULLABLE_STR,
            "tone": NULLABLE_STR,
            "emote": NULLABLE_STR,
            "learned_names": {"type": ["array", "null"], "items": {"type": "string"}},
        },
        "required": [
            "inner_monologue",
            "action",
            "item",
            "target",
            "text",
            "speech",
            "volume",
            "tone",
            "emote",
            "learned_names",
        ],
    },
)

AGENT_REACT: Dict[str, Any] = _wrap_schema(
    "agent_react",
    {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "inner_monologue": NULLABLE_STR,
            "speech": NULLABLE_STR,
            "volume": NULLABLE_STR,
            "tone": NULLABLE_STR,
            "emote": NULLABLE_STR,
            "learned_names": {"type": ["array", "null"], "items": {"type": "string"}},
        },
        "required": [
            "inner_monologue",
            "speech",
            "volume",
            "tone",
            "emote",
            "learned_names",
        ],
    },
)

_PLAN_STEP: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "action": {"type": "string"},
        "item": NULLABLE_STR,
        "target": NULLABLE_STR,
        "text": NULLABLE_STR,
        "note": NULLABLE_STR,
        "area": NULLABLE_STR,
        "until": NULLABLE_STR,
        "duration": {"type": ["number", "null"]},
    },
    "required": ["action", "item", "target", "text", "note", "area", "until", "duration"],
}

PLAN: Dict[str, Any] = _wrap_schema(
    "plan",
    {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "steps": {"type": "array", "items": _PLAN_STEP},
        },
        "required": ["steps"],
    },
)

_INSIGHT: Dict[str, Any] = {
    "type": ["object", "null"],
    "additionalProperties": False,
    "properties": {
        "belief": NULLABLE_STR,
        "about": {"type": ["array", "null"], "items": {"type": "string"}},
        "confidence": {"type": ["number", "null"]},
        "emotional": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "properties": {
                "label": NULLABLE_STR,
                "intensity": {"type": ["integer", "null"]},
            },
            "required": ["label", "intensity"],
        },
        "behavior": NULLABLE_STR,
        "relationship": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "properties": {
                "who": NULLABLE_STR,
                "dim": NULLABLE_STR,
                "delta": {"type": ["number", "null"]},
            },
            "required": ["who", "dim", "delta"],
        },
    },
    "required": ["belief", "about", "confidence", "emotional", "behavior", "relationship"],
}

INSIGHTS: Dict[str, Any] = _wrap_schema(
    "memory_insights",
    {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "insights": {"type": "array", "items": _INSIGHT},
        },
        "required": ["insights"],
    },
)

PERSONALITY: Dict[str, Any] = _wrap_schema(
    "personality",
    {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "personality": NULLABLE_STR,
            "description": NULLABLE_STR,
        },
        "required": ["personality", "description"],
    },
)

TAGS: Dict[str, Any] = _wrap_schema(
    "interest_tags",
    {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["tags"],
    },
)

JSON_OBJECT: Dict[str, Any] = {"type": "json_object"}

FORMATS: Dict[str, Dict[str, Any]] = {
    "agentAction": AGENT_ACTION,
    "agentReact": AGENT_REACT,
    "plan": PLAN,
    "insights": INSIGHTS,
    "personality": PERSONALITY,
    "tags": TAGS,
    "jsonObject": JSON_OBJECT,
}
