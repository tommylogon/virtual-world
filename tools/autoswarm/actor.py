"""tools/autoswarm/actor.py - Cognitive Playtest Swarm runner for ViWo AutoSwarm.

Deploys 2+ autonomous characters into an active scenario using fast local LLMs
(e.g. qwen3.5-2b via LM Studio).
Runs complete perception-action-decay cycles via app.test_client().
"""
from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.autoswarm.llm import call_tier


def clean_command(raw_text: str) -> str:
    """Extract a valid game action or dialogue from model output."""
    raw = raw_text.strip()
    if not raw:
        return "wait"

    # Filter out reasoning blocks if present
    if "<think>" in raw:
        parts = raw.split("</think>")
        raw = parts[-1].strip()

    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    if not lines:
        return "wait"
    first_line = lines[0]

    # Valid game action prefixes
    lower = first_line.lower()
    for verb in ("say ", "examine ", "take ", "drop ", "go ", "unlock ", "lock ", "open ", "close ", "use "):
        if lower.startswith(verb):
            return first_line

    if lower in ("wait", "look", "inventory"):
        return lower

    # If it's natural dialogue, wrap in say
    cleaned = first_line.strip('"').strip("'")
    return f"say {cleaned}"


def run_playtest_session(
    app: Any,
    character_names: List[str],
    cycles: int = 3,
) -> Dict[str, Any]:
    """Execute multi-cycle playtest soak directly against the engine in memory."""
    client = app.test_client()
    world = app.world

    transcript: List[Dict[str, Any]] = []

    for cycle_idx in range(cycles):
        cycle_record: Dict[str, Any] = {
            "cycle": cycle_idx + 1,
            "turns": [],
        }

        for char_name in character_names:
            player = world.players.get(char_name)
            if not player:
                # Try finding by lowercase or partial
                for p_name, p_obj in world.players.items():
                    if char_name.lower() in p_name.lower():
                        player = p_obj
                        char_name = p_name
                        break
            if not player:
                continue

            current_area_id = getattr(player, "current_area", "unknown")
            area_node = world.graph.nodes.get(current_area_id)
            area_name = area_node.name if area_node else current_area_id
            area_desc = area_node.properties.get("description", "") if area_node else ""

            # Detect visible items (source=item_id, target=current_area_id, type="location")
            visible_items = []
            for edge in world.graph.edges:
                if edge.target == current_area_id and edge.type in ("location", "in"):
                    item_node = world.graph.nodes.get(edge.source)
                    if item_node and item_node.type == "item":
                        visible_items.append(f"{item_node.name} (id: {item_node.id})")

            # Detect visible exits
            visible_exits = []
            for edge in world.graph.edges:
                if edge.source == current_area_id and edge.type == "connection":
                    way_node = world.graph.nodes.get(edge.target)
                    if way_node and way_node.type == "way":
                        wprops = way_node.properties
                        target_id = wprops.get("area_to") if wprops.get("area_from") == current_area_id else wprops.get("area_from")
                        target_node = world.graph.nodes.get(target_id)
                        tname = target_node.name if target_node else target_id
                        status = "locked" if wprops.get("locked") else "open"
                        direction = edge.properties.get("direction", "forward")
                        desc = f"go {direction} (to {tname} via {way_node.name} [{status}])"
                        if desc not in visible_exits:
                            visible_exits.append(desc)

            # Detect other characters present
            other_chars = []
            for p_name, p_obj in world.players.items():
                if p_name != char_name and getattr(p_obj, "current_area", None) == current_area_id:
                    other_chars.append(p_name)

            vitals = getattr(player, "vitals", {})
            emotion = getattr(player, "emotion", {})
            primary_emo = emotion.get("primary", "neutral") if isinstance(emotion, dict) else "neutral"

            # Build prompt for local fast LLM
            system_prompt = (
                f"You are {char_name}. You are in: {area_name}.\n"
                f"Room description: {area_desc}\n"
                f"Visible items: {', '.join(visible_items) if visible_items else 'none'}\n"
                f"Exits: {', '.join(visible_exits) if visible_exits else 'none'}\n"
                f"Others here: {', '.join(other_chars) if other_chars else 'none'}\n"
                f"Your emotional state: {primary_emo}. Vitals: {vitals}\n"
                "Choose ONE immediate action. Valid formats:\n"
                "- say <what you say to others in character>\n"
                "- examine <item or exit>\n"
                "- take <item name>\n"
                "- unlock <door> with <key>\n"
                "- go <exit name>\n"
                "- wait\n"
                "Output ONLY the command. Keep dialogue natural and grounded in the situation."
            )

            raw_choice = call_tier("dialogue", [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"What does {char_name} do next?"}
            ], max_tokens=150)

            cmd = clean_command(raw_choice)

            # Dispatch action to engine
            action_resp = client.post("/api/action", json={
                "action": cmd,
                "player": char_name,
            })
            action_data = action_resp.get_json() if action_resp.status_code == 200 else {}
            feedback = action_data.get("feedback") or action_data.get("message") or ""

            turn_log = {
                "character": char_name,
                "area": area_name,
                "action": cmd,
                "feedback": feedback,
                "emotion_primary": primary_emo,
            }
            cycle_record["turns"].append(turn_log)

        # Advance cycle (ticks & decay)
        turn_resp = client.post("/api/turn/apply", json={})
        cycle_record["cycle_result"] = turn_resp.get_json() if turn_resp.status_code == 200 else {}
        transcript.append(cycle_record)

    return {
        "cycles_completed": len(transcript),
        "transcript": transcript,
    }
