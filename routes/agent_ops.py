"""Flask blueprint for server-side Python agent endpoints (Phase 2 & 3).

Exposes:
  - ``POST /api/agent/prompt``: build [system, user] messages + response_format
    directly from Python's authoritative VirtualWorld/Player/Graph state.
  - ``POST /api/agent/step``: run one non-streaming Python AgentRunner turn.
  - ``POST /api/agent/stream``: stream tokens over SSE and execute the parsed
    speech/action on VirtualWorld.
"""
from __future__ import annotations

import json
from typing import Any, Dict

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context

from engine.agent.json_schemas import AGENT_ACTION, AGENT_REACT
from engine.agent.llm_client import LLMClient, LLMConfig
from engine.agent.prompt_builder import (
    build_result_reaction_messages,
    build_think_decide_messages,
)
from engine.agent.response_parser import parse_turn_response
from engine.agent.runner import AgentRunner

agent_ops_bp = Blueprint("agent_ops", __name__)


def _get_world():
    return current_app.world


def _llm_config_from_payload(data: Dict[str, Any]) -> LLMConfig:
    cfg = data.get("llm") or {}
    return LLMConfig(
        base_url=str(cfg.get("base_url") or "http://127.0.0.1:1234/v1"),
        api_key=str(cfg.get("api_key") or ""),
        model=str(cfg.get("model") or ""),
        temperature=float(cfg.get("temperature", 0.7)),
        max_tokens=int(cfg.get("max_tokens", 1024)),
        timeout_s=float(cfg.get("timeout_s", 120.0)),
        suppress_local_thinking=bool(cfg.get("suppress_local_thinking", False)),
        reasoning_max_tokens=(
            int(cfg["reasoning_max_tokens"])
            if cfg.get("reasoning_max_tokens") is not None
            else None
        ),
    )


def _resolve_action_points(player: Any, data: Dict[str, Any]) -> Dict[str, int]:
    """Read authoritative remaining action points from Python Player.action_points."""
    from engine import action_tiers

    live = getattr(player, "action_points", None)
    if isinstance(live, dict) and live:
        return {k: int(v) for k, v in live.items() if k in ("major", "minor", "free")}
    override = data.get("action_points") or data.get("action_points")
    if isinstance(override, dict) and override:
        return {k: int(v) for k, v in override.items() if k in ("major", "minor", "free")}
    return dict(action_tiers.DEFAULT_BUDGET)


@agent_ops_bp.route("/api/agent/prompt", methods=["POST"])
def handle_agent_prompt():
    """Assemble prompt messages + strict response_format on the Python server."""
    data = request.get_json(silent=True) or {}
    world = _get_world()
    char_name = str(data.get("character") or getattr(world, "active_player", "") or "")
    if not char_name or char_name not in world.players:
        return jsonify({"error": f"Unknown character: {char_name}"}), 404

    phase = str(data.get("phase") or "think").strip().lower()
    action_points = _resolve_action_points(world.players[char_name], data)
    memory_thought = str(data.get("memory_thought") or "")

    if phase == "react":
        msgs = build_result_reaction_messages(
            world,
            char_name,
            what_happened=str(data.get("what_happened") or ""),
            memory_thought=memory_thought,
            action_points=action_points,
            said_this_turn=str(data.get("said_this_turn") or ""),
        )
        fmt = AGENT_REACT
    else:
        plan_steps = data.get("plan_steps") if isinstance(data.get("plan_steps"), list) else None
        recent_speech = data.get("recent_speech") if isinstance(data.get("recent_speech"), list) else None
        msgs = build_think_decide_messages(
            world,
            char_name,
            last_result=str(data.get("last_result") or ""),
            memory_thought=memory_thought,
            action_points=action_points,
            plan_steps=plan_steps,
            recent_speech=recent_speech,
        )
        fmt = AGENT_ACTION

    return jsonify({"character": char_name, "phase": phase, "messages": msgs, "response_format": fmt})


@agent_ops_bp.route("/api/agent/step", methods=["POST"])
def handle_agent_step():
    """Run one server-side Python AgentRunner step."""
    data = request.get_json(silent=True) or {}
    world = _get_world()
    char_name = str(data.get("character") or getattr(world, "active_player", "") or "")
    if not char_name or char_name not in world.players:
        return jsonify({"error": f"Unknown character: {char_name}"}), 404

    client = LLMClient(_llm_config_from_payload(data))
    runner = AgentRunner(world, client)
    outcome = runner.step_character(char_name, run_react=bool(data.get("run_react", False)))
    return jsonify(
        {
            "character": outcome.character,
            "parsed": outcome.parsed.__dict__,
            "action_result": outcome.action_result,
            "react_parsed": outcome.react_parsed.__dict__ if outcome.react_parsed else None,
        }
    )


@agent_ops_bp.route("/api/agent/stream", methods=["POST"])
def handle_agent_stream():
    """Stream LLM tokens via SSE for think-decide or result-reaction."""
    data = request.get_json(silent=True) or {}
    world = _get_world()
    char_name = str(data.get("character") or getattr(world, "active_player", "") or "")
    if not char_name or char_name not in world.players:
        return jsonify({"error": f"Unknown character: {char_name}"}), 404

    phase = str(data.get("phase") or "think").strip().lower()
    action_points = _resolve_action_points(world.players[char_name], data)
    memory_thought = str(data.get("memory_thought") or "")
    execute_side_effects = bool(data.get("execute_side_effects", False))

    if phase == "react":
        msgs = build_result_reaction_messages(
            world,
            char_name,
            what_happened=str(data.get("what_happened") or ""),
            memory_thought=memory_thought,
            action_points=action_points,
            said_this_turn=str(data.get("said_this_turn") or ""),
        )
        fmt = AGENT_REACT
        allow_action = False
    else:
        plan_steps = data.get("plan_steps") if isinstance(data.get("plan_steps"), list) else None
        recent_speech = data.get("recent_speech") if isinstance(data.get("recent_speech"), list) else None
        msgs = build_think_decide_messages(
            world,
            char_name,
            last_result=str(data.get("last_result") or ""),
            memory_thought=memory_thought,
            action_points=action_points,
            plan_steps=plan_steps,
            recent_speech=recent_speech,
        )
        fmt = AGENT_ACTION
        allow_action = True

    client = LLMClient(_llm_config_from_payload(data))

    def _generate():
        chunks = []
        try:
            for tok in client.stream_chat(msgs, response_format=fmt):
                chunks.append(tok)
                yield f"data: {json.dumps({'type': 'token', 'delta': tok})}\n\n"
            full_text = "".join(chunks)
            parsed = parse_turn_response(full_text, allow_action=allow_action)
            if execute_side_effects and parsed.speech and hasattr(world, "broadcast_speech"):
                world.broadcast_speech(
                    char_name,
                    parsed.speech,
                    speech_level=parsed.speech_volume or "normal",
                    whisper_target=parsed.speech_target,
                    tone=parsed.speech_tone,
                )
            yield f"data: {json.dumps({'type': 'done', 'raw': full_text, 'parsed': parsed.__dict__})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"

    return Response(stream_with_context(_generate()), mimetype="text/event-stream")


@agent_ops_bp.route("/api/agent/generate", methods=["POST"])
def handle_agent_generate():
    """Server-side AI generator (personality, tags, insights, description)."""
    from engine.agent.generators import (
        generate_description,
        generate_insights,
        generate_personality,
        generate_tags,
    )

    data = request.get_json(silent=True) or {}
    kind = str(data.get("kind") or "").strip().lower()
    client = LLMClient(_llm_config_from_payload(data))
    if kind == "personality":
        res = generate_personality(
            client,
            name=str(data.get("name") or ""),
            concept=str(data.get("concept") or ""),
            setting=str(data.get("setting") or ""),
        )
        return jsonify({"ok": True, "result": res})
    if kind == "tags":
        tags = generate_tags(
            client,
            name=str(data.get("name") or ""),
            description=str(data.get("description") or ""),
            entity_type=str(data.get("entity_type") or "item"),
        )
        return jsonify({"ok": True, "tags": tags})
    if kind == "insights":
        insights = generate_insights(
            client,
            char_name=str(data.get("character") or ""),
            memories=list(data.get("memories") or []),
        )
        return jsonify({"ok": True, "insights": insights})
    if kind == "description":
        res = generate_description(
            client,
            name=str(data.get("name") or ""),
            entity_type=str(data.get("entity_type") or "area"),
            hints=str(data.get("hints") or ""),
        )
        return jsonify({"ok": True, "result": res})
    return jsonify({"error": f"Unknown generate kind: {kind}"}), 400


@agent_ops_bp.route("/api/agent/commons/turn", methods=["POST"])
def handle_commons_turn():
    """Run one Commons group conversation turn in Python."""
    from engine.agent.commons_agent import run_commons_turn

    data = request.get_json(silent=True) or {}
    world = _get_world()
    char_name = str(data.get("character") or "").strip()
    if not char_name:
        return jsonify({"error": "character is required"}), 400
    client = LLMClient(_llm_config_from_payload(data))
    parsed = run_commons_turn(
        world,
        client,
        char_name,
        transcript=list(data.get("transcript") or []),
        topic=str(data.get("topic") or ""),
    )
    return jsonify({"ok": True, "character": char_name, "parsed": parsed.__dict__})


@agent_ops_bp.route("/api/agent/nl-edit", methods=["POST"])
def handle_nl_edit():
    """Execute a natural-language world edit via Python NL Editor."""
    from engine.agent.nl_editor import run_nl_edit

    data = request.get_json(silent=True) or {}
    instruction = str(data.get("instruction") or "").strip()
    if not instruction:
        return jsonify({"error": "instruction is required"}), 400
    world = _get_world()
    client = LLMClient(_llm_config_from_payload(data))
    result = run_nl_edit(world, client, instruction)
    return jsonify(result)


@agent_ops_bp.route("/api/agent/memory/synthesize", methods=["POST"])
def handle_memory_synthesize():
    """Synthesize recalled memory traces into a conscious thought in Python (Intermediator)."""
    from engine.agent.memory_manager import MemoryManager

    data = request.get_json(silent=True) or {}
    world = _get_world()
    char_name = str(data.get("character") or getattr(world, "active_player", "") or "")
    if not char_name or char_name not in world.players:
        return jsonify({"error": f"Unknown character: {char_name}"}), 404
    player = world.players[char_name]
    client = LLMClient(_llm_config_from_payload(data))
    mm = getattr(current_app, "_agent_memory_manager", None)
    if mm is None:
        mm = MemoryManager()
        current_app._agent_memory_manager = mm
    thought = mm.synthesize_thought(
        client,
        player,
        list(data.get("memories") or []),
        recent_heard=list(data.get("recent_heard") or []),
        area_name=str(data.get("area") or getattr(player, "current_area", "") or ""),
    )
    return jsonify({"ok": True, "character": char_name, "thought": thought})


@agent_ops_bp.route("/api/agent/plan/generate", methods=["POST"])
def handle_plan_generate():
    """Generate a 3-5 step grounded plan in Python via PlanManager."""
    from engine.agent.plan_manager import PlanManager

    data = request.get_json(silent=True) or {}
    world = _get_world()
    char_name = str(data.get("character") or getattr(world, "active_player", "") or "")
    if not char_name or char_name not in world.players:
        return jsonify({"error": f"Unknown character: {char_name}"}), 404
    client = LLMClient(_llm_config_from_payload(data))
    pm = getattr(current_app, "_agent_plan_manager", None)
    if pm is None:
        pm = PlanManager()
        current_app._agent_plan_manager = pm
    msgs = build_think_decide_messages(
        world,
        char_name,
        memory_thought=str(data.get("memory_thought") or ""),
    )
    context_prompt = msgs[1]["content"] if len(msgs) >= 2 else ""
    steps = pm.generate(
        client,
        char_name,
        context_prompt,
        intent=str(data.get("intent") or ""),
        turn_number=int(data.get("turn_number", 0) or 0),
    )
    return jsonify({"ok": True, "character": char_name, "steps": steps})
