"""Per-character soak orders (task-481).

A timeskip in a shared world is not a table-wide consensus and not a blocking
server jump — it is an **order attached to one character**, declared on that
player's turn ("go west for an hour"). While the order is active the character
is run by a deterministic policy on every turn of the normal game loop, exactly
like an agent or a distant NPC, so a turn with a thousand characters in soak
still finishes in seconds. Everyone else — attended humans, nearby high-fidelity
NPCs, agents — plays on unaffected.

The order ends when its span is spent, and it is **promoted back to the player**
early when something demands their attention: something they fear, a hostile
condition, a vital in its danger band, or a discovery matching the order's
watch tags. Promotion clears the order and writes one resume memory, so the
next prompt knows what the character did and that control is theirs again.

The blocking "advance the world N minutes" in engine/timeskip is the fast path
used only when nothing attended remains (solo play, or everyone soaking).
"""

from __future__ import annotations

import logging

from engine import fear as fear_mod
from engine import interrupts as interrupts_mod
from engine import timeskip
from engine.background_simulation import BackgroundSimulation

logger = logging.getLogger(__name__)


def declare(player, *, intent="idle", minutes, target=None, watch_tags=(),
            target_type=None, heading=None):
    """Attach a soak order to *player*. Replaces any existing order.

    Returns the order dict (also stored as ``player.soak_order``).
    """
    if intent not in timeskip.INTENTS:
        raise ValueError(f"Unknown timeskip intent '{intent}'")
    try:
        span = float(minutes)
    except (TypeError, ValueError):
        raise ValueError("A soak order needs a duration")
    if span < timeskip.MIN_MINUTES:
        raise ValueError("That is too short")

    order = {
        "intent": intent,
        "declared_minutes": min(span, float(timeskip.MAX_MINUTES)),
        "remaining_minutes": min(span, float(timeskip.MAX_MINUTES)),
        "target": target,
        "watch_tags": [str(t) for t in (watch_tags or [])],
        "target_type": target_type,
        "heading": heading,
        # Seeded on the first turn (we have no world yet here), so the area's
        # existing contents do not read as a fresh discovery.
        "seen": None,
    }
    # While the order runs the character is *genuinely* background: the soak tier
    # drives it, the agent/LLM loop does not ask it for decisions, and the turn
    # queue treats it as not-attended. Restored when the order ends.
    player._pre_soak_mode = getattr(player, "simulation_mode", "active")
    player.simulation_mode = "background"
    player.soak_order = order
    return order


def cancel(player) -> bool:
    """Drop *player*'s soak order. True when there was one."""
    had = getattr(player, "soak_order", None) is not None
    player.soak_order = None
    _restore_mode(player)
    return had


def _restore_mode(player) -> None:
    """Return the character to attended play after an order ends."""
    previous = getattr(player, "_pre_soak_mode", None)
    player.simulation_mode = previous if previous else "active"
    if hasattr(player, "_pre_soak_mode"):
        try:
            del player._pre_soak_mode
        except Exception:
            pass


def remaining(player):
    order = getattr(player, "soak_order", None)
    return None if not order else float(order.get("remaining_minutes", 0))


def apply_orders(gs) -> None:
    """Step every active soak order by one turn. Called from tick_turn."""
    players = list((getattr(gs, "players", None) or {}).values())
    if not any(getattr(p, "soak_order", None) for p in players):
        return
    sim = BackgroundSimulation(gs)
    for player in players:
        order = getattr(player, "soak_order", None)
        if not order:
            continue
        try:
            _step_one(gs, sim, player, order)
        except Exception as e:  # one bad order must not break the turn
            logger.warning("[soak] %s: %s", getattr(player, "name", "?"), e)


# ───────────────────────────── internals ──────────────────────────────────

def _step_one(gs, sim, player, order) -> None:
    if getattr(player, "state", "") == "dead":
        _finish(gs, player, order, ("death", "You died."))
        return

    per = timeskip.frame_minutes(gs)
    left = float(order.get("remaining_minutes", per))

    # 1. Anything already demanding attention at the start of the turn — a
    #    character waking beside something they fear should not walk on.
    reason = _promote_reason(gs, player, order)
    if reason:
        _promote(gs, player, order, reason)
        return

    # 2. Run the policy for this turn.
    found = None
    if not getattr(player, "activity", None) and \
            getattr(player, "state", "") != "unconscious":
        found = timeskip.run_policy_step(
            gs, sim, player, intent=order.get("intent", "idle"),
            target=order.get("target"), watch_tags=order.get("watch_tags") or (),
            target_type=order.get("target_type"), heading=order.get("heading"),
            remaining=min(per, left))

    # 3. Spend the time.
    order["remaining_minutes"] = left - per

    # 4. Anything that happened, arrived or was found this turn. A search that
    #    turned up its target is a discovery exactly like it is for a blocking
    #    skip, so hand control back rather than searching past it (the policy
    #    result used to be dropped here).
    if found is not None:
        _promote(gs, player, order,
                 ("discovery", f"You find {found.name}."))
        return
    reason = _promote_reason(gs, player, order)
    if reason:
        _promote(gs, player, order, reason)
        return
    if order["remaining_minutes"] <= 0:
        _finish(gs, player, order, None)


def _promote(gs, player, order, reason) -> None:
    """Hand a soaking character back to their player."""
    if reason[0] == "fear":
        sources = fear_mod.fear_sources(gs, player)
        fear_mod.apply_frightening(gs, player, sources)
    _finish(gs, player, order, reason)


def _promote_reason(gs, player, order):
    """Why a soaking character should be handed back, or None.

    Absolute checks rather than crossings: an order runs for many turns, so
    "am I in danger now" is the right question (unlike the one-turn skip where a
    crossing is the event).
    """
    if fear_mod.fear_sources(gs, player):
        return ("fear", "Something you fear is here.")

    present = set(getattr(player, "conditions", {}) or {})
    hostile = present & interrupts_mod.HOSTILE_CONDITIONS
    if hostile:
        cid = sorted(hostile)[0]
        return ("threat", f"You are {cid.replace('_', ' ')}.")

    vitals = getattr(player, "vitals", {}) or {}
    for stat, band in interrupts_mod.DRIVE_DANGER.items():
        if stat in vitals and vitals.get(stat, 0) >= band:
            return ("vital", f"Your {stat.lower()} is critical.")
    for stat, band in interrupts_mod.RESOURCE_DANGER.items():
        if stat in vitals and vitals.get(stat, 100) <= band:
            return ("vital", f"Your {stat.lower()} is dangerously low.")

    watch = {str(t).lower() for t in (order.get("watch_tags") or [])}
    target = str(order.get("target") or "").lower()
    try:
        visible = interrupts_mod.visible_here(gs, getattr(player, "current_area", None))
    except Exception:
        visible = set()
    if order.get("seen") is None:
        # First turn of the order: record the baseline, don't treat the area's
        # existing contents as a discovery.
        order["seen"] = set(visible)
        return None
    seen = set(order.get("seen") or ())
    order["seen"] = set(visible)
    for entry in sorted(visible - seen):
        _type, _id, name, tags = entry
        tagset = {str(t).lower() for t in tags}
        if (watch and (watch & tagset)) or (target and target in str(name).lower()):
            return ("discovery", f"You notice {name}.")
    return None


def _finish(gs, player, order, reason) -> None:
    """End an order: clear it, remember what happened, tell the stream."""
    declared = float(order.get("declared_minutes", 0) or 0)
    remaining = max(0.0, float(order.get("remaining_minutes", 0) or 0))
    elapsed = max(0, int(round(declared - remaining)))
    intent = order.get("intent", "idle")

    player.soak_order = None
    _restore_mode(player)

    if elapsed > 0 or reason:
        result = timeskip.TimeskipResult(
            ok=True, intent=intent, requested_minutes=int(declared),
            mode="soak", elapsed_minutes=elapsed,
            interrupted=bool(reason),
            interrupt=({"kind": reason[0], "why": f"soak:{reason[0]}",
                        "detail": reason[1], "salient": True} if reason else None),
        )
        try:
            timeskip.write_resume_memory(gs, player, result, intent,
                                         order.get("target"))
        except Exception as e:
            logger.warning("[soak] memory: %s", e)

    verb = "interrupted" if reason else "finished"
    detail = f": {reason[1]}" if reason else f" after {elapsed} min"
    try:
        gs.record_turn_event(player.name, "soak_end",
                             f"{player.name} {verb} their soak{detail}",
                             area_name=getattr(player, "current_area", None))
    except Exception:
        pass
