"""Timeskip action handler (task-464).

Runs a declared intent for an in-game span by advancing the world minute by
minute with the player's own character driven by a deterministic policy, and
returns a bounded summary. No LLM calls happen inside the span.
"""

import logging

from flask import jsonify, request

from engine import timeskip

logger = logging.getLogger(__name__)

#: A synchronous request must not hold a worker for a whole game week. Longer
#: spans need the soak-runner-style job (task-464 follow-up); the engine itself
#: supports up to timeskip.MAX_MINUTES.
MAX_REQUEST_MINUTES = 1440


def _requested_minutes(world, data):
    """Minutes from `minutes`, `hours` or `turns` (in that order)."""
    if data.get("minutes") is not None:
        return data.get("minutes")
    if data.get("hours") is not None:
        return float(data["hours"]) * 60.0
    if data.get("turns") is not None:
        per_tick = float(getattr(world, "time_per_tick_minutes", 1) or 1)
        return float(data["turns"]) * per_tick
    return None


def handle_timeskip(app):
    data = request.get_json(silent=True) or {}
    intent = str(data.get("intent", "idle")).lower()
    if intent not in timeskip.INTENTS:
        return jsonify({"error": f"Unknown intent '{intent}'",
                        "intents": list(timeskip.INTENTS)}), 400

    world = app.world
    minutes = _requested_minutes(world, data)

    target = data.get("target")
    player = world.get_active_player_obj()
    if player is None:
        return jsonify({"error": "No active character"}), 400

    # Travel to a known place can derive its own span from the route.
    if minutes is None and intent == "travel" and target:
        route = timeskip.travel_minutes(world, player.current_area, target)
        if route is None:
            return jsonify({"error": f"No route to '{target}'"}), 400
        minutes = route
    if minutes is None:
        return jsonify({"error": "Missing duration (minutes, hours or turns)"}), 400

    try:
        requested = float(minutes)
    except (TypeError, ValueError):
        return jsonify({"error": "Duration must be a number"}), 400
    if requested < timeskip.MIN_MINUTES:
        return jsonify({"error": "That is too short"}), 400
    if requested > MAX_REQUEST_MINUTES:
        return jsonify({"error": f"Too long for a request (max {MAX_REQUEST_MINUTES} min)",
                        "max_minutes": MAX_REQUEST_MINUTES}), 400

    watch_tags = data.get("watch_tags") or []
    if isinstance(watch_tags, str):
        watch_tags = [watch_tags]

    try:
        result = timeskip.advance(
            world, int(round(requested)), intent=intent, target=target,
            watch_tags=watch_tags, heading=data.get("heading"))
    except Exception as e:  # never 500 the world on a bad skip
        logger.exception("[timeskip] request failed")
        return jsonify({"error": str(e)}), 400

    payload = result.to_dict()
    if not result.ok:
        return jsonify(payload), 400
    return jsonify(payload)
