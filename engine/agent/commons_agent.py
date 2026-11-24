"""Python Commons Agent (Phase 4, task-1004).

Runs a character's conversational turn in the Commons chatroom using
``engine.agent.llm_client.LLMClient`` and ``response_parser``.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from engine.agent.json_schemas import AGENT_REACT
from engine.agent.llm_client import LLMClient
from engine.agent.response_parser import ParsedTurn, parse_turn_response


def build_commons_messages(
    world: Any,
    char_name: str,
    *,
    transcript: List[Dict[str, str]],
    topic: str = "",
) -> List[Dict[str, str]]:
    """Build [system, user] messages for a character speaking in the Commons."""
    player = world.players.get(char_name) if hasattr(world, "players") else None
    persona = getattr(player, "personality", "") if player else ""
    emo = player.emotions_description() if (player and hasattr(player, "emotions_description")) else ""
    somatic = player.somatic_description() if (player and hasattr(player, "somatic_description")) else ""

    system_msg = (
        f"You are {char_name} in a casual group conversation (The Commons).\n"
        + (f"Personality: {persona}\n" if persona else "")
        + "Stay in character. Respond ONLY with a single raw JSON object:\n"
        '{"inner_monologue":"...","speech":"...","volume":"say","tone":null,"emote":"...","learned_names":[]}'
    )

    lines: List[str] = []
    if topic:
        lines.append(f"Topic: {topic}")
    if emo:
        lines.append(f"Mood: {emo}")
    if somatic:
        lines.append(f"Body: {somatic}")
    if transcript:
        lines.append("=== RECENT CHAT ===")
        for entry in transcript[-12:]:
            speaker = entry.get("speaker") or "Someone"
            text = entry.get("text") or ""
            if text:
                lines.append(f"{speaker}: {text}")
    lines.append("\nWhat do you think, say, or emote next?")

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": "\n".join(lines)},
    ]


def run_commons_turn(
    world: Any,
    client: LLMClient,
    char_name: str,
    *,
    transcript: List[Dict[str, str]],
    topic: str = "",
) -> ParsedTurn:
    """Execute one Commons character turn via Python LLMClient."""
    msgs = build_commons_messages(world, char_name, transcript=transcript, topic=topic)
    raw = client.chat(msgs, response_format=AGENT_REACT)
    return parse_turn_response(raw, allow_action=False)
