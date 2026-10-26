"""Timeskip and soak-order handlers (task-464/481).

A timeskip in a shared world is a **soak order on one character**: it is declared
on that player's turn, then run by the normal turn loop (like an agent or a
distant NPC) until the span is spent or the character is promoted back. When
nothing attended remains - solo play, or everyone already soaking - the blocking
`advance` fast path jumps the world in one request instead.

A request may also carry `world: true` to force the no-subject world advance
(`timeskip.advance_world`) while an active character exists: every character
soaks, nobody acts, and the clock runs. The Ctrl+K "Advance World" command uses
this, because world mode is otherwise reachable only with no active character.
"""

import logging

from flask import jsonify, request

from engine import soak, timeskip

logger = logging.getLogger(__name__)

#: A synchronous request runs a long span in chunks of this many minutes, so a
#: worker never holds one blocking `advance` for a whole game week at once. The
#: request ceiling is the engine's own `timeskip.MAX_MINUTES` (one in-game week).
MAX_REQUEST_MINUTES = 1440


def _merge_results(results):
    """Collapse chunked fast-path results into the last result's envelope."""
    if not results:
        return None
    if len(results) == 1:
        return results[0]
    first, last = results[0], results[-1]
    last.requested_minutes = sum(r.requested_minutes for r in results)
    last.elapsed_minutes = sum(r.elapsed_minutes for r in results)
    last.ticks = sum(r.ticks for r in results)
    last.ok = all(r.ok for r in results)
    last.interrupted = any(r.interrupted for r in results)
    if not last.vitals_before:
        last.vitals_before = first.vitals_before
    lines = []
    for r in results:
        lines.extend(r.lines or [])
    last.lines = lines[-50:]
    if not last.reason:
        last.reason = next((r.reason for r in results if r.reason), "")
    return last


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


def _publish_tick(frame):
    """Put one tick of a world advance on the live hub (task-861).

    A world advance owns the clock inside a single POST, so without this the GUI's
    only signal is the `world_changed` that fires *after* the response returns: an
    hour of game time measured at 30 s of dead air, then one 9 MB fetch. These
    frames are a projection of `turn_events`, not a second ledger, and `hub.publish`
    is non-blocking and drops for a subscriber whose queue is full - so a stalled
    browser cannot hold the world. The end-of-request `world_changed` is still what
    settles the clock and the graph from authoritative state.
    """
    from engine.world_events import hub
    hub.publish(dict(frame, type="world_tick"))


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
    heading = data.get("heading")

    # Travel to a known place can derive its own span from the route.
    # For a place known only by belief/hearsay (with a heading), fall back to a
    # single hop along the believed heading so `advance` can handle the belief path.
    if minutes is None and player is not None and intent == "travel" and target:
        route = timeskip.travel_minutes(world, player.current_area, target)
        if route is not None:
            minutes = route
        else:
            belief = timeskip.resolve_belief_destination(world, player, target)
            if belief and belief.get("heading"):
                minutes = timeskip.per_hop_minutes()
                if not heading:
                    heading = belief["heading"]
            else:
                return jsonify({"error": f"No route to '{target}'"}), 400
    elif player is not None and intent == "travel" and target and not heading:
        belief = timeskip.resolve_belief_destination(world, player, target)
        if belief and belief.get("heading"):
            heading = belief["heading"]
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
    if requested > timeskip.MAX_MINUTES:
        return jsonify({"error": f"Too long for a request (max {timeskip.MAX_MINUTES} min)",
                        "max_minutes": timeskip.MAX_MINUTES}), 400

    try:
        watch_tags = data.get("watch_tags") or []
        if isinstance(watch_tags, str):
            watch_tags = [watch_tags]
        total = int(round(requested))
        # `world: true` forces the no-subject world advance even when an active
        # character exists (the Ctrl+K "Advance World" command). Without it the
        # world path is reachable only with no active character at all.
        force_world = bool(data.get("world"))
        if player is not None and not force_world:
            if getattr(player, "state", None) == "dead" and not getattr(world, "ghost_mode", False):
                return jsonify({"ok": False, "error": "The dead do not wait.", "reason": "The dead do not wait."}), 400
        if player is None or force_world:
            # No human/active character (or a forced world advance): a timeskip is
            # a WORLD advance - intent, target and watch tags have no subject, so
            # everyone simply soaks. Long spans run in day-sized chunks (task-482)
            # so a synchronous request never holds one blocking advance for a whole
            # game week.
            results, remaining = [], total
            while remaining > 0:
                chunk = min(MAX_REQUEST_MINUTES, remaining)
                outcome = timeskip.advance_world(world, chunk, on_tick=_publish_tick)
                results.append(outcome)
                remaining -= chunk
                if not outcome.ok:
                    break
            result = _merge_results(results)
        elif _other_attended_humans(world, player):
            # Shared world: a blocking server jump would freeze the other players
            # (and lock them out while it runs). Attach a soak order to this
            # character instead and let the normal turn loop carry it - the loop
            # runs the span over many turns, so a week-long order is fine.
            order = soak.declare(
                player, intent=intent, minutes=total,
                target=target, watch_tags=watch_tags,
                target_type=data.get("target_type"), heading=heading)
            clean_order = {k: (list(v) if isinstance(v, set) else v) for k, v in order.items()}
            reason = soak.promote_reason(world, player, order)
            if reason:
                soak._promote(world, player, order, reason)
                return jsonify({
                    "ok": True,
                    "mode": "soak",
                    "order": {**clean_order, "ended": True, "reason": reason[1], "interrupted": True},
                    "ended": True,
                    "reason": reason[1],
                    "interrupted": True,
                })
            return jsonify({"ok": True, "mode": "soak", "order": clean_order})
        else:
            results, remaining = [], total
            while remaining > 0:
                chunk = min(MAX_REQUEST_MINUTES, remaining)
                outcome = timeskip.advance(
                    world, chunk, intent=intent, target=target,
                    watch_tags=watch_tags, target_type=data.get("target_type"),
                    heading=heading)
                results.append(outcome)
                remaining -= chunk
                # An interrupt hands control back to the player, so stop early.
                if not outcome.ok or outcome.interrupted:
                    break
            result = _merge_results(results)
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
            belief = timeskip.resolve_belief_destination(world, player, data.get("target"))
            if belief and belief.get("heading"):
                minutes = timeskip.per_hop_minutes()
            else:
                raise ValueError(f"No route to '{data.get('target')}'")
    if minutes is None:
        raise ValueError("Missing duration (minutes, hours or turns)")
    span = float(minutes)
    if span < timeskip.MIN_MINUTES:
        raise ValueError("That is too short")
    if span > timeskip.MAX_MINUTES:
        raise ValueError(f"Too long for an order (max {timeskip.MAX_MINUTES} min)")
    return int(round(span))


def handle_soak_declare(app):
    """POST /api/world/soak - attach a soak order to the active character."""
    data = request.get_json(silent=True) or {}
    intent = str(data.get("intent", "idle")).lower()
    if intent not in timeskip.INTENTS:
        return jsonify({"error": f"Unknown intent '{intent}'",
                        "intents": list(timeskip.INTENTS)}), 400
    world = app.world
    player = world.get_active_player_obj()
    if player is None:
        return jsonify({"error": "No active character"}), 400
    if getattr(player, "state", None) == "dead" and not getattr(world, "ghost_mode", False):
        return jsonify({"ok": False, "error": "The dead do not wait.", "reason": "The dead do not wait."}), 400
    try:
        minutes = _declared_span(world, player, data, intent)
        watch_tags = data.get("watch_tags") or []
        if isinstance(watch_tags, str):
            watch_tags = [watch_tags]
        heading = data.get("heading")
        if not heading and intent == "travel" and data.get("target"):
            belief = timeskip.resolve_belief_destination(world, player, data.get("target"))
            if belief and belief.get("heading"):
                heading = belief["heading"]
        order = soak.declare(
            player, intent=intent, minutes=minutes, target=data.get("target"),
            watch_tags=watch_tags, target_type=data.get("target_type"),
            heading=heading)
        clean_order = {k: (list(v) if isinstance(v, set) else v) for k, v in order.items()}
        reason = soak.promote_reason(world, player, order)
        if reason:
            soak._promote(world, player, order, reason)
            return jsonify({
                "ok": True,
                "mode": "soak",
                "order": {**clean_order, "ended": True, "reason": reason[1], "interrupted": True},
                "ended": True,
                "reason": reason[1],
                "interrupted": True,
            })
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"ok": True, "mode": "soak", "order": clean_order})


def handle_soak_cancel(app):
    """DELETE /api/world/soak[?character=Name] - drop a character's soak order.

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
