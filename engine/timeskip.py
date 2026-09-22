"""Timeskip actions (task-464).

Declare an intent plus a span of game time; the world advances **minute by
minute** at maximum speed with the player's own decisions supplied by a
deterministic policy, and stops the moment something relevant happens to them
(:mod:`engine.interrupts`). No stasis, no protection: vitals decay and the
environment applies exactly as in normal play — the skip removes *decisions*,
not *consequences*.

A skip is the controller swap the Simulation Model describes: same Player, same
graph, same clock, same action flows; only who supplies the decision changes.
Every other character is already run by the soak tier through ``tick_turn``.
Zero LLM calls are made inside a skip.

The one deliberate deviation from the frame dial: a skip advances **1-minute
ticks regardless of ``time_per_tick_minutes``**, so interrupts land on a minute
boundary. Normal play keeps the scenario's turn length.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field

from engine.background_simulation import BackgroundSimulation, TASK_MINUTES
from engine import interrupts as interrupts_mod
from engine.trace import record, summarize_window

logger = logging.getLogger(__name__)

INTENTS = ("idle", "leisure", "search", "explore", "travel")
MIN_MINUTES = 1
MAX_MINUTES = 10080  # one in-game week
HEADING_WORDS = {
    "n": "north", "north": "north", "s": "south", "south": "south",
    "e": "east", "east": "east", "w": "west", "west": "west",
    "up": "up", "down": "down",
}

#: One active skip at a time (task-464 concurrency rule).
_ACTIVE = False


@dataclass
class TimeskipResult:
    ok: bool
    intent: str
    requested_minutes: int
    elapsed_minutes: int = 0
    ticks: int = 0
    interrupted: bool = False
    interrupt: dict = None
    reason: str = ""
    vitals_before: dict = field(default_factory=dict)
    vitals_after: dict = field(default_factory=dict)
    clock_after: str = ""
    lines: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "intent": self.intent,
            "requested_minutes": self.requested_minutes,
            "elapsed_minutes": self.elapsed_minutes,
            "ticks": self.ticks,
            "interrupted": self.interrupted,
            "interrupt": self.interrupt,
            "reason": self.reason,
            "vitals_before": self.vitals_before,
            "vitals_after": self.vitals_after,
            "clock_after": self.clock_after,
            "lines": self.lines,
        }


def is_running() -> bool:
    """True while a timeskip is advancing the world.

    Mutating requests (action / turn / llm) should refuse rather than
    interleave: a skip owns the clock for its span (task-464).
    """
    return _ACTIVE


def advance(gs, minutes, *, intent="idle", target=None, watch_tags=(),
            target_type=None, heading=None, player=None) -> TimeskipResult:
    """Run a timeskip for the active character.

    ``intent`` is one of :data:`INTENTS`. ``minutes`` is clamped to
    ``[MIN_MINUTES, MAX_MINUTES]``. ``target`` is an area name for travel or an
    item name for search; ``target_type`` is an item *tag* (items have no type
    taxonomy — the library identifies them by tags). ``watch_tags`` are interest
    tags that end the skip on discovery; Explore defaults them to the
    character's own ``interest_tags``. Returns a :class:`TimeskipResult`; the
    world is left at the exact minute the skip stopped on.
    """
    global _ACTIVE

    try:
        requested = int(minutes)
    except (TypeError, ValueError):
        return TimeskipResult(False, intent, 0, reason="A timeskip needs a duration.")

    if intent not in INTENTS:
        return TimeskipResult(False, intent, requested,
                              reason=f"Unknown timeskip intent '{intent}'.")
    if requested < MIN_MINUTES:
        return TimeskipResult(False, intent, requested, reason="That is too short.")
    requested = min(requested, MAX_MINUTES)

    who = player if player is not None else _resolve_active(gs)
    if who is None:
        return TimeskipResult(False, intent, requested, reason="No active character.")
    if getattr(who, "state", None) == "dead":
        return TimeskipResult(False, intent, requested,
                              reason="The dead do not wait.")

    if intent == "travel" and target:
        hops = route_hops(gs, getattr(who, "current_area", None), target)
        if hops is None:
            return TimeskipResult(False, intent, requested,
                                  reason=f"No route to '{target}'.")
        if hops == 0:
            return TimeskipResult(False, intent, requested,
                                  reason="You are already there.")

    if _ACTIVE:
        return TimeskipResult(False, intent, requested,
                              reason="A timeskip is already running.")

    _ACTIVE = True
    watch_tags = _default_watch_tags(who, intent, watch_tags)
    sim = BackgroundSimulation(gs)
    result = TimeskipResult(True, intent, requested)
    result.vitals_before = dict(getattr(who, "vitals", {}) or {})
    start_tick = getattr(gs, "time_ticks", 0)

    saved_per_tick = getattr(gs, "time_per_tick_minutes", 1)
    try:
        # Force minute resolution for the skip only.
        try:
            gs.time_per_tick_minutes = 1.0
        except Exception:
            pass

        before = interrupts_mod.snapshot(gs, who)
        for _ in range(requested):
            # 1. the standing-in policy spends this minute.
            if getattr(who, "state", None) != "dead" and not _busy(who):
                try:
                    found = _policy_step(gs, sim, who, intent, target,
                                         watch_tags, target_type, heading)
                except Exception as e:  # never let one step kill the skip
                    logger.warning("[timeskip] %s step: %s", intent, e)
                    found = None
                if found is not None:
                    result.interrupted = True
                    result.interrupt = {
                        "kind": "discovery", "why": "search:found",
                        "detail": f"You find {found.name}.", "salient": True,
                    }
                    break

            # 2. the world advances one minute (everyone else is soak).
            gs.tick_turn()
            result.elapsed_minutes += 1
            result.ticks += 1

            # 3. did anything relevant happen to us?
            after = interrupts_mod.snapshot(gs, who)
            events = interrupts_mod.events_since(gs, before)
            reasons = interrupts_mod.evaluate(
                before, after, events=events, watch_tags=watch_tags,
                target=target, intent=intent)
            before = after
            if reasons:
                result.interrupted = True
                result.interrupt = reasons[0].to_dict()
                break
            if getattr(who, "state", None) == "dead":
                result.interrupted = True
                result.interrupt = {"kind": "death", "why": "death",
                                    "detail": "You died.", "salient": True}
                break
    finally:
        try:
            gs.time_per_tick_minutes = saved_per_tick
        except Exception:
            pass
        _ACTIVE = False

    result.vitals_after = dict(getattr(who, "vitals", {}) or {})
    _stamp_trace(gs, who, result, intent, start_tick)
    try:
        result.clock_after = gs.tick_manager.get_current_time()
    except Exception:
        result.clock_after = ""
    result.lines = summarize_window(who, since_tick=start_tick, limit=40)
    result.lines += _notable_lines(gs, start_tick, getattr(who, "current_area", ""))
    _write_memory(gs, who, result, intent, target)
    return result


# ───────────────────────────── policy ─────────────────────────────────────

def _resolve_active(gs):
    """The active character as a Player object (``gs.active_player`` is a key,
    but some callers assign the object directly)."""
    who = getattr(gs, "active_player", None)
    if who is not None and not isinstance(who, str):
        return who
    getter = getattr(gs, "get_active_player_obj", None)
    if callable(getter):
        try:
            obj = getter()
            if obj is not None:
                return obj
        except Exception:
            pass
    if isinstance(who, str):
        return (getattr(gs, "players", None) or {}).get(who)
    return None


def _default_watch_tags(player, intent, watch_tags):
    """Explore watches the character's own interests when none are given."""
    if watch_tags:
        return tuple(watch_tags)
    if intent == "explore":
        return tuple(getattr(player, "interest_tags", []) or ())
    return ()


def _busy(player) -> bool:
    return bool(getattr(player, "activity", None)) or \
        getattr(player, "state", None) == "unconscious"


#: Named times for an "until X" span (hour of day, 24h).
UNTIL_HOURS = {
    "dawn": 6, "morning": 8, "noon": 12, "dusk": 18, "night": 22, "midnight": 0,
}


def minutes_until(gs, when):
    """Minutes from now until the next named time or hour, or None if unknown."""
    if isinstance(when, str):
        key = when.strip().lower()
        if key in UNTIL_HOURS:
            hour = UNTIL_HOURS[key]
        else:
            try:
                hour = int(key)
            except ValueError:
                return None
    else:
        try:
            hour = int(when)
        except (TypeError, ValueError):
            return None
    try:
        now = float(gs.total_game_minutes())
    except Exception:
        return None
    target = (hour % 24) * 60
    return int((target - (now % 1440)) % 1440)


def _policy_step(gs, sim, player, intent, target, watch_tags, target_type, heading):
    """One minute of the standing-in policy. Returns a found node or None."""
    if intent == "idle":
        return None  # do nothing, on purpose

    if intent == "leisure":
        sim.take_action(player, served=set(), remaining=1.0)
        return None

    if intent == "search":
        search_tags = tuple(watch_tags or ()) + ((target_type,) if target_type else ())
        found = sim.find_matching(player, tags=search_tags, name=target)
        if found is not None:
            return found
        # Nothing here: drift toward an area that might hold it, else keep up
        # the maintenance a mingle would.
        if search_tags and sim.step_toward_tags(player, search_tags, "search"):
            return None
        sim.take_action(player, served=set(), remaining=1.0)
        return None

    if intent == "explore":
        _explore_step(gs, player)
        return None

    if intent == "travel":
        if target:
            sim.step_toward_area(player, target, "timeskip")
        elif heading:
            _move_heading(gs, player, heading)
        return None

    return None


def _explore_step(gs, player):
    """Move through an exit, preferring one the character has not discovered."""
    area = getattr(player, "current_area", None)
    if not area:
        return False
    try:
        exits = gs.build_exits_for_area(area, include_hidden=True) or {}
    except Exception:
        return False
    if not exits:
        return False
    discovered = {str(x) for x in (getattr(player, "discovered_exits", []) or [])}
    labels = sorted(exits.keys())
    fresh = [lbl for lbl in labels if str(lbl) not in discovered]
    label = (fresh or labels)[0]
    return _move(gs, player, label)


def _move_heading(gs, player, heading):
    """Belief/direction travel: step through an exit matching the heading."""
    want = HEADING_WORDS.get(str(heading).strip().lower())
    if not want:
        return False
    area = getattr(player, "current_area", None)
    try:
        exits = gs.build_exits_for_area(area, include_hidden=True) or {}
    except Exception:
        return False
    for label in sorted(exits.keys()):
        if want in str(label).lower():
            return _move(gs, player, label)
    return False


# ───────────────────────────── route planning ─────────────────────────────

def per_hop_minutes() -> int:
    """How long one way-step takes, in game minutes (the travel task)."""
    return int(TASK_MINUTES.get("travel", 1))


def _canon_area(gs, area):
    if area is None:
        return None
    try:
        return str(gs.area_node_id(area) or area)
    except Exception:
        return str(area)


def _area_name(gs, area_id):
    node = gs.graph.get_node(area_id) if area_id else None
    return getattr(node, "name", None) or area_id


def route_hops(gs, from_area, to_area):
    """Fewest way-steps between two areas, or None if unreachable.

    Used to turn "travel to a known place" into a real duration instead of an
    arbitrary turn count: `route_hops * per_hop_minutes()` is the span a skip
    needs (task-467).
    """
    start = _canon_area(gs, from_area)
    goal = _canon_area(gs, to_area)
    if not start or not goal:
        return None
    if start == goal:
        return 0
    seen = {start}
    queue = deque([(start, 0)])
    while queue:
        current, depth = queue.popleft()
        name = _area_name(gs, current)
        try:
            exits = gs.build_exits_for_area(name, include_hidden=True) or {}
        except Exception:
            exits = {}
        for exit_data in exits.values():
            target = _canon_area(gs, exit_data.get("target"))
            if not target or target in seen:
                continue
            if target == goal:
                return depth + 1
            seen.add(target)
            queue.append((target, depth + 1))
    return None


def travel_minutes(gs, from_area, to_area):
    """Route duration in in-game minutes, or None when unreachable."""
    hops = route_hops(gs, from_area, to_area)
    if hops is None:
        return None
    return hops * per_hop_minutes()


def _move(gs, player, label):
    old_active = getattr(gs, "active_player", None)
    try:
        gs.active_player = player.name
        gs.movement.move_to_area(label)
    except Exception as e:
        logger.warning("[timeskip] move %s (%s): %s", player.name, label, e)
        return False
    finally:
        try:
            gs.active_player = old_active
        except Exception:
            pass
    return True


# ───────────────────────────── summary ────────────────────────────────────

#: Turn-event actions worth surfacing in a skip summary wherever they happen.
NOTABLE_ACTIONS = frozenset({
    "death", "kill", "attack", "steal", "arrive", "arrival", "take", "give",
})


def _notable_lines(gs, since_tick, area="", limit=20):
    """Readable world events during the skip: notable actions anywhere, plus
    anything that happened in the character's own area. Read-only; the summary
    should say who died or arrived, not just what the character did."""
    logger = getattr(gs, "game_logger", None)
    events = list(getattr(logger, "turn_events", []) or []) if logger else []
    lines, seen = [], set()
    for event in events:
        if not isinstance(event, dict):
            continue
        try:
            if int(event.get("tick", 0) or 0) < int(since_tick):
                continue
        except (TypeError, ValueError):
            continue
        action = str(event.get("action", "")).lower()
        if action not in NOTABLE_ACTIONS and (event.get("area") or "") != area:
            continue
        text = str(event.get("description", "") or "").strip()
        if text and text not in seen:
            seen.add(text)
            lines.append(text)
    return lines[-limit:]


def _stamp_trace(gs, player, result, intent, start_tick):
    why = f"timeskip:{intent}"
    what = f"waited {result.elapsed_minutes} min" if intent == "idle" \
        else f"{intent} for {result.elapsed_minutes} min"
    if result.interrupted and result.interrupt:
        what += f" (interrupted: {result.interrupt.get('why', '')})"
    try:
        record(player, getattr(gs, "time_ticks", 0), "plan", what, why=why,
               area=getattr(player, "current_area", ""), tags=["timeskip"],
               salient=result.interrupted)
    except Exception as e:
        logger.warning("[timeskip] trace: %s", e)


def _write_memory(gs, player, result, intent, target):
    """Exactly one bounded memory for the skip, so the next prompt knows what
    happened (and that vitals moved). Built from deterministic templates over
    recorded facts — no LLM (task-412 slice)."""
    if result.elapsed_minutes <= 0:
        return
    area = getattr(player, "current_area", "") or "somewhere"
    minutes = result.elapsed_minutes
    templates = {
        "idle": f"You waited {minutes} min in {area}.",
        "leisure": f"You spent {minutes} min mingling in {area}.",
        "search": f"You searched {area} for {target or 'something'} for {minutes} min.",
        "explore": f"You explored for {minutes} min and reached {area}.",
        "travel": f"You travelled for {minutes} min to {area}.",
    }
    text = templates.get(intent, f"You passed {minutes} min in {area}.")
    if result.interrupted and result.interrupt:
        detail = str(result.interrupt.get("detail", "")).strip()
        if detail:
            text = f"{text} {detail}"
    try:
        player.add_memory(text[:300], tick=getattr(gs, "time_ticks", 0),
                          importance=6 if result.interrupted else 3,
                          memory_type="observation", tags=["timeskip"],
                          source="timeskip", location=area)
    except Exception as e:
        logger.warning("[timeskip] memory: %s", e)
