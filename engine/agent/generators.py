"""Python AI Generators (Phase 4, task-1004).

Replaces browser-side ``ai-generator.ts`` calls with server-side structured
generation via ``engine.agent.llm_client.LLMClient`` and ``json_schemas``.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from engine.agent.json_schemas import INSIGHTS, JSON_OBJECT, PERSONALITY, TAGS
from engine.agent.llm_client import LLMClient
from engine.agent.response_parser import repair_json


def _parse_json_obj(raw: str) -> Dict[str, Any]:
    parsed, _ = repair_json(raw or "")
    return parsed if isinstance(parsed, dict) else {}


def generate_personality(client: LLMClient, *, name: str, concept: str = "", setting: str = "") -> Dict[str, Any]:
    """Generate a character personality + appearance profile."""
    prompt = (
        f"Create a grounded character profile for '{name}'.\n"
        + (f"Concept: {concept}\n" if concept else "")
        + (f"Setting: {setting}\n" if setting else "")
        + 'Return ONLY JSON: {"personality": "...", "appearance": "...", "speech_style": "..."}'
    )
    raw = client.chat([{"role": "user", "content": prompt}], response_format=PERSONALITY)
    return _parse_json_obj(raw)


def generate_tags(client: LLMClient, *, name: str, description: str, entity_type: str = "item") -> List[str]:
    """Generate concise lowercase tags for an area, item, or character."""
    prompt = (
        f"Generate 3-6 concise lowercase tags for this {entity_type}.\n"
        f"Name: {name}\nDescription: {description}\n"
        'Return ONLY JSON: {"tags": ["tag1", "tag2"]}'
    )
    raw = client.chat([{"role": "user", "content": prompt}], response_format=TAGS)
    data = _parse_json_obj(raw)
    tags = data.get("tags")
    return [str(t).strip().lower() for t in tags if str(t).strip()] if isinstance(tags, list) else []


def generate_insights(client: LLMClient, *, char_name: str, memories: List[str]) -> List[Dict[str, Any]]:
    """Synthesize higher-level reflections/insights from recent memories."""
    mem_lines = "\n".join(f"- {m}" for m in memories[:12] if m)
    prompt = (
        f"Character: {char_name}\nRecent memories:\n{mem_lines}\n\n"
        'Synthesize 1-3 concise first-person insights. Return ONLY JSON: {"insights": [{"text": "...", "importance": 1-10}]}'
    )
    raw = client.chat([{"role": "user", "content": prompt}], response_format=INSIGHTS)
    data = _parse_json_obj(raw)
    items = data.get("insights")
    return items if isinstance(items, list) else []


def generate_description(client: LLMClient, *, name: str, entity_type: str = "area", hints: str = "") -> Dict[str, Any]:
    """Generate a vivid, grounded description for an area or item."""
    prompt = (
        f"Write a concise, grounded 2-4 sentence description for this {entity_type}.\n"
        f"Name: {name}\n"
        + (f"Hints: {hints}\n" if hints else "")
        + 'Return ONLY JSON: {"description": "..."}'
    )
    raw = client.chat([{"role": "user", "content": prompt}], response_format=JSON_OBJECT)
    return _parse_json_obj(raw)
