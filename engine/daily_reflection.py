"""Daily character reflection for background characters (task-409).

Capped at at most one reflection per background character per in-game day.
Uses only the configured local provider. With no local provider configured,
the simulation continues completely unchanged.

A reflection can update an existing GIMP goal through the existing goal mutation
path (engine.goals.set_status) and may write an ordinary semantic reflection
memory through Player.memories. It never directly chooses or executes an action,
and never writes a duplicate mind store.

@module daily_reflection
@contributes build_reflection_context, apply_reflection_result, maybe_reflect
@docs docs/virtualWorld/AI & Narration/Memory System.md
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from engine import goals


def build_reflection_context(world, player) -> Dict[str, Any]:
    """Assemble a bounded, read-only summary of the character's day for reflection."""
    pname = getattr(player, "name", "Character")
    current_day = getattr(world, "game_day", 1)
    current_area = getattr(player, "current_area", "Camp")

    # 1. Existing GIMP goals
    active_goals = [
        {"id": g.get("id"), "what": g.get("what"), "priority": g.get("priority", 1),
         "why": g.get("why", ""), "status": g.get("status")}
        for g in (getattr(player, "goals", []) or [])
        if isinstance(g, dict) and g.get("status") in ("active", "dormant", "proposed")
    ]

    # 2. Close relationships
    relations = {}
    if hasattr(player, "relationships") and isinstance(player.relationships, dict):
        for other, rel in player.relationships.items():
            if isinstance(rel, dict) and (rel.get("closeness", 0) or rel.get("trust", 0)):
                relations[other] = {
                    "closeness": rel.get("closeness", 0),
                    "trust": rel.get("trust", 0),
                    "sentiment": rel.get("sentiment", "neutral"),
                }

    # 3. Recent episodic memories (last 5)
    memories = [
        m.get("text", "") for m in (getattr(player, "memories", []) or [])[-5:]
        if isinstance(m, dict) and m.get("text")
    ]

    # 4. Traits and vitals
    vitals = {k: v for k, v in (getattr(player, "vitals", {}) or {}).items() if k in ("Hunger", "Energy", "Social", "Sanity")}
    traits = list((getattr(player, "traits", {}) or {}).keys())

    return {
        "character": pname,
        "day": current_day,
        "area": current_area,
        "vitals": vitals,
        "traits": traits,
        "goals": active_goals,
        "relationships": relations,
        "recent_memories": memories,
    }


def apply_reflection_result(world, player, result: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and apply reflection output through existing goal and memory APIs."""
    applied: Dict[str, Any] = {"memory_added": False, "goals_updated": []}
    if not isinstance(result, dict):
        return applied

    current_day = getattr(world, "game_day", 1)
    current_tick = getattr(world, "time_ticks", 0) or 0

    # 1. Add ordinary reflection memory
    reflection_text = str(result.get("reflection") or result.get("thought") or "").strip()
    if reflection_text:
        mem_id = f"mem_refl_{current_day}_{int(time.time() * 1000) % 100000}"
        t_min = world.total_game_minutes() if callable(getattr(world, "total_game_minutes", None)) else getattr(world, "total_game_minutes", 0.0)
        memory = {
            "id": mem_id,
            "text": reflection_text,
            "tick": current_tick,
            "timestamp": float(t_min or 0.0),
            "type": "reflection",
            "category": "semantic",
            "importance": 3,
            "source": "daily_reflection",
            "reflection_depth": 1,
            "entity_ids": [],
            "tags": ["reflection", "daily"],
        }
        if not hasattr(player, "memories") or player.memories is None:
            player.memories = []
        player.memories.append(memory)
        applied["memory_added"] = True
        applied["memory_id"] = mem_id

    # 2. Update existing GIMP goals
    goal_updates = result.get("goal_updates") or []
    if isinstance(goal_updates, dict):
        goal_updates = [goal_updates]

    for update in goal_updates:
        if not isinstance(update, dict):
            continue
        g_id = update.get("id") or update.get("goal_id")
        if not g_id:
            continue
        existing = goals.find(player.goals, g_id)
        if not existing:
            continue

        new_status = update.get("status")
        if new_status and new_status in goals.GOAL_STATUSES:
            player.goals, _ = goals.set_status(player.goals, g_id, new_status, tick=current_tick)
            applied["goals_updated"].append({"id": g_id, "status": new_status})

        if "priority" in update:
            for g in (player.goals or []):
                if isinstance(g, dict) and (g.get("id") == g_id or str(g.get("what", "")).lower() == str(g_id).lower()):
                    try:
                        g["priority"] = max(1, int(update["priority"]))
                    except (TypeError, ValueError):
                        pass

    return applied


def maybe_reflect(
    world,
    player,
    local_provider: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Perform capped daily reflection for *player*.

    Leaves simulation unchanged when no local provider is configured.
    """
    if getattr(player, "state", "") in ("dead", "unconscious"):
        return None

    try:
        current_day = int(getattr(world, "game_day", 1) or 1)
    except (TypeError, ValueError):
        current_day = 1

    last_day = getattr(player, "last_reflection_day", None)
    if last_day is not None and int(last_day) >= current_day:
        return None  # Capped at at most one reflection per character per in-game day

    provider = local_provider or getattr(world, "local_provider", None)
    if provider is None or not callable(provider):
        return None  # No local provider configured: leave simulation unchanged

    ctx = build_reflection_context(world, player)
    try:
        result = provider(ctx)
    except Exception:
        return None

    if not result or not isinstance(result, dict):
        return None

    record = apply_reflection_result(world, player, result)
    player.last_reflection_day = current_day
    return record
