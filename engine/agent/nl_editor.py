"""Python Natural-Language World Editor loop (Phase 4, task-1004).

Translates natural-language world editing requests into validated tool calls
and executes them against ``VirtualWorld`` (areas, items, characters, notes).
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from engine.agent.json_schemas import JSON_OBJECT
from engine.agent.llm_client import LLMClient
from engine.agent.response_parser import repair_json


_NL_EDITOR_SYSTEM = (
    "You are the VirtualWorld NL Editor. Convert the user's editing request into a JSON list of tool calls.\n"
    "Supported tools:\n"
    '- {"tool": "set_area_description", "area": "<name>", "description": "<text>"}\n'
    '- {"tool": "set_character_personality", "character": "<name>", "personality": "<text>"}\n'
    '- {"tool": "rename_node", "node_id": "<id>", "name": "<new_name>"}\n'
    '- {"tool": "reply", "message": "<summary>"}\n'
    'Return ONLY valid JSON: {"calls": [...], "summary": "..."}'
)


def _execute_tool_call(world: Any, call: Dict[str, Any]) -> Dict[str, Any]:
    tool = str(call.get("tool") or "").strip()
    if tool == "set_area_description":
        area_name = str(call.get("area") or "").strip()
        desc = str(call.get("description") or "").strip()
        graph = getattr(world, "graph", None)
        node = graph.nodes.get(area_name) if (graph and hasattr(graph, "nodes")) else None
        if node is None:
            return {"tool": tool, "ok": False, "error": f"Unknown area: {area_name}"}
        node.description = desc
        return {"tool": tool, "ok": True, "area": area_name}

    if tool == "set_character_personality":
        char_name = str(call.get("character") or "").strip()
        personality = str(call.get("personality") or "").strip()
        player = world.players.get(char_name) if hasattr(world, "players") else None
        if player is None:
            return {"tool": tool, "ok": False, "error": f"Unknown character: {char_name}"}
        player.personality = personality
        return {"tool": tool, "ok": True, "character": char_name}

    if tool == "rename_node":
        node_id = str(call.get("node_id") or "").strip()
        new_name = str(call.get("name") or "").strip()
        graph = getattr(world, "graph", None)
        node = graph.nodes.get(node_id) if (graph and hasattr(graph, "nodes")) else None
        if node is None or not new_name:
            return {"tool": tool, "ok": False, "error": f"Cannot rename node: {node_id}"}
        node.name = new_name
        return {"tool": tool, "ok": True, "node_id": node_id, "name": new_name}

    if tool == "reply":
        return {"tool": tool, "ok": True, "message": str(call.get("message") or "")}

    return {"tool": tool, "ok": False, "error": f"Unsupported tool: {tool}"}


def run_nl_edit(world: Any, client: LLMClient, instruction: str) -> Dict[str, Any]:
    """Plan and execute a natural-language edit against ``world``."""
    areas = list(getattr(getattr(world, "graph", None), "nodes", {}).keys())[:40]
    players = list(getattr(world, "players", {}).keys())[:20]
    user_msg = (
        f"Known nodes: {', '.join(areas) or '(none)'}\n"
        f"Known characters: {', '.join(players) or '(none)'}\n\n"
        f"Request: {instruction}"
    )
    raw = client.chat(
        [
            {"role": "system", "content": _NL_EDITOR_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        response_format=JSON_OBJECT,
    )
    parsed, _ = repair_json(raw or "")
    if not isinstance(parsed, dict):
        parsed = {}
    calls = parsed.get("calls") if isinstance(parsed, dict) and isinstance(parsed.get("calls"), list) else []
    results = [_execute_tool_call(world, c) for c in calls if isinstance(c, dict)]
    return {
        "ok": True,
        "summary": str(parsed.get("summary") or "") if isinstance(parsed, dict) else "",
        "results": results,
    }
