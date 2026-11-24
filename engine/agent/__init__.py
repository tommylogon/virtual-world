"""Server-side Python agent package (Phase 1 foundation).

Consolidates structured LLM JSON schemas, response parsing/repair, and the
OpenAI-compatible ``LLMClient`` on the Python side so agent logic and prompt
pipelines can be tested directly with ``pytest``.
"""
from __future__ import annotations

from engine.agent.json_schemas import (
    AGENT_ACTION,
    AGENT_REACT,
    FORMATS,
    INSIGHTS,
    JSON_OBJECT,
    PERSONALITY,
    PLAN,
    TAGS,
)
from engine.agent.llm_client import LLMClient, LLMConfig, LLMResult
from engine.agent.response_parser import ParsedTurn, parse_turn_response, repair_json

__all__ = [
    "AGENT_ACTION",
    "AGENT_REACT",
    "FORMATS",
    "INSIGHTS",
    "JSON_OBJECT",
    "LLMClient",
    "LLMConfig",
    "LLMResult",
    "PERSONALITY",
    "PLAN",
    "ParsedTurn",
    "TAGS",
    "parse_turn_response",
    "repair_json",
]
