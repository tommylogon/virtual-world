"""Timeskip and soak-order handlers (task-464/481).

A timeskip in a shared world is a **soak order on one character**: it is declared
on that player's turn, then run by the normal turn loop (like an agent or a
distant NPC) until the span is spent or the character is promoted back. When
nothing attended remains — solo play, or everyone already soaking — the blocking
`advance` fast path jumps the world in one request instead.
"""

import logging

from flask import jsonify, request

from engine import soak, timeskip

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

    # Travel to a known place can derive its own span from the route.
    if minutes is None and player is not None and intent == "travel" and target:
        route = timeskip.travel_minutes(world, player.current_area, target)
        if route is None:
            return jsonify({"error": f"No route to '{target}'"}), 400
        minutes = route
    # "Until dawn/dusk/noon" derives the span from the world clock.
    if minutes is None and data.get("until") is not None:
        minutes = timeskip.minutes_until(world, data.get("until"))
        if minutes is None:
            return jsonify({"error": f"Unknown 'until' value '{data.get('until')}'"}), 400
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

    try:
        watch_tags = data.get("watch_tags") or []
        if isinstance(watch_tags, str):
            watch_tags = [watch_tags]
        if player is None:
            # No human/active character: a timeskip is a WORLD advance — intent,
            # target and watch tags have no subject, so everyone simply soaks.
            result = timeskip.advance_world(world, int(round(requested)))
        elif _other_attended_humans(world, player):
            # Shared world: a blocking server jump would freeze the other players
            # (and lock them out while it runs). Attach a soak order to this
            # character instead and let the normal turn loop carry it.
            order = soak.declare(
                player, intent=intent, minutes=int(round(requested)),
                target=target, watch_tags=watch_tags,
                target_type=data.get("target_type"), heading=data.get("heading"))
            return jsonify({"ok": True, "mode": "soak", "order": order})
        else:
            result = timeskip.advance(
                world, int(round(requested)), intent=intent, target=target,
                watch_tags=watch_tags, target_type=data.get("target_type"),
                heading=data.get("heading"))
    except Exception as e:  # never 500 the world on a bad skip
        logger.exception("[timeskip] request failed")
        return jsonify({"error": str(e)}), 400

    payload = result.to_dict()
    if not result.ok:
        return jsonify(payload), 400
    return jsonify(payload)


def _other_attended_humans(world, player) -> bool:
    """True when another human-driven character is neither soaking nor dead."""
    for other in (getattr(world, "players", None) or {}).values():
        if other is player:
            continue
        if getattr(other, "autonomy", True) is not False:
            continue                       # not human-driven
        if getattr(other, "soak_order", None):
            continue                       # already soaking
        if getattr(other, "state", "") == "dead":
            continue
        return True
    return False


def _declared_span(world, player, data, intent):
    """Minutes for a soak order: explicit span, `until`, or a travel route."""
    minutes = _requested_minutes(world, data)
    if minutes is None and data.get("until") is not None:
        minutes = timeskip.minutes_until(world, data.get("until"))
        if minutes is None:
            raise ValueError(f"Unknown 'until' value '{data.get('until')}'")
    if minutes is None and intent == "travel" and data.get("target"):
        minutes = timeskip.travel_minutes(world, player.current_area,
                                          data.get("target"))
        if minutes is None:
            raise ValueError(f"No route to '{data.get('target')}'")
    if minutes is None:
        raise ValueError("Missing duration (minutes, hours or turns)")
    span = float(minutes)
    if span < timeskip.MIN_MINUTES:
        raise ValueError("That is too short")
    if span > MAX_REQUEST_MINUTES:
        raise ValueError(f"Too long for a request (max {MAX_REQUEST_MINUTES} min)")
    return int(round(span))


def handle_soak_declare(app):
    """POST /api/world/soak — attach a soak order to the active character."""
    data = request.get_json(silent=True) or {}
    intent = str(data.get("intent", "idle")).lower()
    if intent not in timeskip.INTENTS:
        return jsonify({"error": f"Unknown intent '{intent}'",
                        "intents": list(timeskip.INTENTS)}), 400
    world = app.world
    player = world.get_active_player_obj()
    if player is None:
        return jsonify({"error": "No active character"}), 400
    try:
        minutes = _declared_span(world, player, data, intent)
        watch_tags = data.get("watch_tags") or []
        if isinstance(watch_tags, str):
            watch_tags = [watch_tags]
        order = soak.declare(
            player, intent=intent, minutes=minutes, target=data.get("target"),
            watch_tags=watch_tags, target_type=data.get("target_type"),
            heading=data.get("heading"))
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"ok": True, "mode": "soak", "order": order})


def handle_soak_cancel(app):
    """DELETE /api/world/soak[?character=Name] — drop a character's soak order.

    Defaults to the active character; the roster's cancel button names the row's
    character explicitly.
    """
    world = app.world
    name = request.args.get("character")
    if name:
        player = (getattr(world, "players", None) or {}).get(name)
        if player is None:
            return jsonify({"error": f"No such character: {name}"}), 404
    else:
        player = world.get_active_player_obj()
    if player is None:
        return jsonify({"error": "No active character"}), 400
    return jsonify({"ok": soak.cancel(player)})
