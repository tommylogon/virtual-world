"""MOSIAC: the per-character decision context for one turn (task-812).

MOSIAC is the runtime state machine that feeds an actor. Its letters are:

- **M** Motivation - the standing drive.
- **O** Obligations - what the character owes.
- **S** Schedule - what the day says they should be doing.
- **I** Intention - why this, now.
- **A** Attention - what is salient at this moment.
- **C** Choices - the actions available to them.

Every letter is read from real state - the character's own mind (`Player.goals`,
`obligations`, `schedule`) plus the moment (vitals, the clock, the turn-slot
budget). Nothing is invented to fill a blank: a letter with no source is reported
empty. This is the one object a soak policy or an LLM reads; they resolve it
differently in quality, never in capability.

@module mosiac
@contributes assemble, salient_needs, motivation, intention, choices, DRIVE_VITALS
@docs docs/virtualWorld/design/Character Pursuits.md
"""
from __future__ import annotations

from engine import action_tiers, goals as _goals, schedule as _schedule

#: Drives fill toward 100, so a *high* value is the concern.
DRIVE_VITALS = ("Hunger", "Thirst", "Bladder")

#: Meters that deplete toward 0, so a *low* value is the concern.
DEPLETING_VITALS = ("Energy", "Social", "Sanity", "Hygiene", "Entertainment")

#: A drive at or above this is salient.
CONCERN_DRIVE = 70
#: A depleting meter at or below this is salient.
CONCERN_DEPLETION = 30


def attention_of(player, *, drive=CONCERN_DRIVE, depletion=CONCERN_DEPLETION):
    """The vitals that are currently salient, worst first.

    Each entry is ``{need, value, why}`` where ``why`` is ``drive`` (too full) or
    ``depleted`` (too empty). A character with nothing pressing gets ``[]`` - a
    calm moment is a real answer, not a blank to fill.
    """
    vitals = getattr(player, "vitals", {}) or {}
    out = []
    for name in DRIVE_VITALS:
        value = vitals.get(name)
        if isinstance(value, (int, float)) and value >= drive:
            out.append({"need": name.lower(), "value": round(float(value), 1),
                        "why": "drive", "urgency": round(float(value), 1)})
    for name in DEPLETING_VITALS:
        value = vitals.get(name)
        if isinstance(value, (int, float)) and value <= depletion:
            out.append({"need": name.lower(), "value": round(float(value), 1),
                        "why": "depleted", "urgency": round(100.0 - float(value), 1)})
    out.sort(key=lambda n: n["urgency"], reverse=True)
    for entry in out:
        entry.pop("urgency", None)
    return out


def motivation(goal, attention):
    """The standing drive: the active goal's own motivation, else the top need."""
    if goal and goal.get("motivation"):
        return goal["motivation"]
    if attention:
        return f"the need to satisfy {attention[0]['need']}"
    return ""


def intention(goal, step):
    """Why this, now: the active goal's intention, else what the schedule says."""
    if goal:
        return goal.get("intention") or goal.get("what", "")
    if step:
        where = f" at {step['area']}" if step.get("area") else ""
        return f"the schedule says {step['activity']}{where}"
    return ""


def choices(player):
    """The actions available this turn, grouped by tier.

    Reads the same tier table the engine enforces against (`engine.action_tiers`)
    and the character's remaining budget (`Player.turn_slots`), so a spent major
    slot drops the major verbs from the set. `free` is always offered - the
    always-available commands are the documented override.
    """
    slots = dict(getattr(player, "turn_slots", {}) or {}) or dict(action_tiers.DEFAULT_BUDGET)
    by_tier = {}
    for verb in action_tiers.all_verbs():
        tier = action_tiers.tier_of(verb)
        if tier == action_tiers.FREE or slots.get(tier, 0) > 0:
            by_tier.setdefault(tier, []).append(verb)
    for verbs in by_tier.values():
        verbs.sort()
    return by_tier


def assemble(gs, player):
    """The six letters for one character, for one turn.

    *gs* is the world (for the clock); *player* is the character. The result is a
    plain dict so it can be serialized, rendered in the Mind panel, and dropped
    into an LLM prompt unchanged.
    """
    normalized = _goals.normalize(getattr(player, "goals", []) or [])
    active = [g for g in normalized if g["status"] == "active"]
    obligations = _goals.normalize_obligations(getattr(player, "obligations", []) or [])
    open_obligations = [o for o in obligations if o["status"] in ("offered", "accepted")]

    schedule = _schedule.normalize(getattr(player, "schedule", []) or [])
    now = _schedule.minutes_of_day(gs)
    step = _schedule.current_step(schedule, now)

    goal = active[0] if active else None
    attention = attention_of(player)

    return {
        "character": getattr(player, "name", ""),
        "tick": int(getattr(gs, "time_ticks", 0) or 0),
        "M": motivation(goal, attention),
        "O": open_obligations,
        "S": {"now": now, "step": step, "day": _schedule.describe(schedule)},
        "I": intention(goal, step),
        "A": attention,
        "C": choices(player),
        "goals": active,
    }
