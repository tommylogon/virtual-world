"""Authored daily schedules for characters (task-409).

A schedule is a list of steps, ordered by time of day and wrapping at midnight:

    {"start": "07:00", "activity": "work", "area": "Workshop", "fallback": "wait"}

It is what turns a survival loop into a *day*. Before this, every background
character did the same thing: eat, drink, sleep, wash and talk wherever it
happened to be standing, and moved only when a need drove it somewhere. With a
schedule, Mikka walks to the Workshop and works, Gribba cooks, Vekka scouts, and
they come back to eat, socialise and sleep at roughly human hours.

Deliberately deterministic and LLM-free: choosing the step is arithmetic on the
clock, and travelling there reuses the engine's own exits. The optional daily
reflection (slice 2) can adjust what a character is reaching toward, but it never
picks an immediate action and the sim runs unchanged without it.

**Time is game minutes, never ticks.** `minutes_of_day` reads the engine's own
clock (`total_game_minutes`), so a step at 07:00 happens at 07:00 whether a tick
is 1 minute or 15.
"""

from __future__ import annotations

MINUTES_PER_DAY = 1440

#: What a character does when its area is reached but the step does not ask for
#: anything active. `wait` is the documented fallback: standing where you are
#: supposed to be is the behaviour.
DEFAULT_ACTIVITY = "wait"

#: Activities a step may name. Anything else is treated as `wait` rather than
#: dropped, so a typo degrades to "be there" instead of silently freeing the
#: character to wander.
KNOWN_ACTIVITIES = ("work", "socialise", "eat", "drink", "sleep", "rest",
                    "patrol", "guard", "roam", "wait")

#: Activities that need an actual engine activity started. `socialise`, `patrol`,
#: `guard` and `roam` need nothing beyond being present — company is handled by
#: the social pass, and the others are satisfied by the travel itself.
BLOCKING_ACTIVITIES = {"work": "working", "rest": "resting"}


def parse_start(value):
    """``"HH:MM"`` (or ``"H:MM"``) → minutes past midnight, or None if unusable."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # Tolerate a bare minute count, which is what a form field may give us.
        return int(value) % MINUTES_PER_DAY
    text = str(value).strip()
    if not text or ":" not in text:
        return None
    parts = text.split(":")
    try:
        hours = int(parts[0])
        minutes = int(parts[1]) if len(parts) > 1 else 0
    except (TypeError, ValueError):
        return None
    if not (0 <= hours <= 24) or not (0 <= minutes < 60):
        return None
    return (hours % 24) * 60 + minutes


def normalize(schedule):
    """Validated, start-sorted copy. Malformed steps are dropped, not guessed.

    Dropping is deliberate: a step with no usable `start` cannot be placed in a
    day, and inventing one would make the character behave in a way nobody
    authored. An empty result means "no schedule", which is a valid state (the
    character falls back to pure need-driven behaviour, as before this task).
    """
    if not schedule:
        return []
    if isinstance(schedule, dict):
        schedule = schedule.get("steps") or []
    out = []
    for raw in schedule:
        if not isinstance(raw, dict):
            continue
        start = parse_start(raw.get("start"))
        if start is None:
            continue
        activity = str(raw.get("activity") or DEFAULT_ACTIVITY).strip().lower()
        if activity not in KNOWN_ACTIVITIES:
            activity = DEFAULT_ACTIVITY
        step = {"start": start, "activity": activity}
        area = raw.get("area")
        if area:
            step["area"] = str(area).strip()
        fallback = str(raw.get("fallback") or DEFAULT_ACTIVITY).strip().lower()
        if fallback not in KNOWN_ACTIVITIES:
            fallback = DEFAULT_ACTIVITY
        step["fallback"] = fallback
        out.append(step)
    out.sort(key=lambda s: s["start"])
    return out


def current_step(schedule, now_minutes):
    """The step in force at ``now_minutes`` past midnight, or None.

    Wraps: before the first step of the day, the *last* step is still in force
    (yesterday evening's sleep, typically). That is why a schedule whose first
    step is 07:00 does not leave a character stranded and idle between midnight
    and 07:00.
    """
    steps = normalize(schedule)
    if not steps:
        return None
    try:
        now = int(now_minutes) % MINUTES_PER_DAY
    except (TypeError, ValueError):
        return None
    chosen = None
    for step in steps:
        if step["start"] <= now:
            chosen = step
        else:
            break
    return chosen if chosen is not None else steps[-1]


def minutes_of_day(gs):
    """In-game minutes past midnight, from the engine's own clock.

    Falls back to ticks × tick-length when the facade helper is unavailable, so
    this works on a bare stub as well as a real world.
    """
    try:
        return int(gs.total_game_minutes()) % MINUTES_PER_DAY
    except Exception:
        pass
    try:
        minutes_per_tick = float(getattr(gs, "time_per_tick_minutes", 1) or 1)
    except (TypeError, ValueError):
        minutes_per_tick = 1.0
    try:
        return int(int(getattr(gs, "time_ticks", 0)) * minutes_per_tick) % MINUTES_PER_DAY
    except (TypeError, ValueError):
        return 0


def describe(schedule):
    """A one-line summary, for the inspector and for debugging a soak."""
    steps = normalize(schedule)
    if not steps:
        return "no schedule"
    parts = []
    for step in steps:
        hh, mm = divmod(step["start"], 60)
        where = f" at {step['area']}" if step.get("area") else ""
        parts.append(f"{hh:02d}:{mm:02d} {step['activity']}{where}")
    return "; ".join(parts)
