"""Novelty — Entertainment from places, things and people (task-425).

One mechanic for three subjects. A subject that has not been experienced for a
while is fresh again, and freshness pays:

    freshness = clamp((now - last_experienced_tick[subject]) / recovery, 0, 1) ** 2
    bonus     = round(NOVELTY_MAX * freshness)

so bouncing between two areas gives +15 on the new one, **0** on the one just
left, and **0** immediately on return; leave it alone for the recovery window and
it pays again, rising toward +15 as the subject goes stale. It saturates back at
the original value and never above it.

**Why the curve is squared, not linear.** A linear ramp pays a little for any gap
at all: a two-room bounce every 10 minutes earned +1 a hop, which is 6/hour
against Entertainment's 1.8/hour decay — a treadmill, the exact failure the
window was supposed to prevent. Squaring makes a short gap worth almost nothing
(10 minutes of 120 pays 0, 40 minutes pays 2) while a real absence still pays in
full, which is also what "rising toward +15" should feel like: a place you left
five minutes ago is not remotely interesting, and one you have not seen all day
is.

`last_experienced_tick` is the subject's **live observation memory**
(``Player.observation_tick``) — task-403 writes one per subject and refreshes it
in place, so there is no second structure to keep in step. Absence of a memory
means "never experienced", which pays full.

The window is the other half of the farm guard, and it is deliberately comparable
to the decay time: Entertainment empties in roughly 2.3 days, so a 2-hour window
means a route earns variety while loitering does not. Tune it with
``entertainment.novelty_recovery_minutes``.
"""

from __future__ import annotations

from engine.runtime_config import config

#: Saturated novelty, and the value a first-ever subject pays.
NOVELTY_MAX = 15

RECOVERY_KEY = "entertainment.novelty_recovery_minutes"
#: Fallback when the config key is unreadable. 2 hours: long enough that a
#: two-room bounce earns nothing, short enough that a camp's worth of wandering
#: keeps paying.
DEFAULT_RECOVERY_MINUTES = 120

#: Total novelty a character can earn per in-game day, whatever it sees.
#:
#: **This is the bound that actually matters.** The recovery window alone guards
#: *bouncing* (two rooms, no credit) but not *roaming*: with 31 areas a character
#: revisits a given one only after about five hours, so every arrival was a fresh
#: area and every arrival paid — a fresh subject per action against 43/day of
#: decay is unbounded. Measured with only the area subject paying and social
#: switched off, a single day still pinned Entertainment at 81 average.
#:
#: Deliberately below Entertainment's daily decay (~43), so novelty is a top-up
#: and *things* — the authored recreational fixtures — are what hold the meter
#: up. This is task-425's "diminishing returns within a day" option, which the
#: measurement showed was needed alongside the window, not instead of it.
NOVELTY_DAILY_BUDGET = 30


def recovery_minutes() -> float:
    """Game minutes for a subject to become fully fresh again."""
    try:
        value = float(config.get(RECOVERY_KEY, DEFAULT_RECOVERY_MINUTES))
    except (TypeError, ValueError):
        return float(DEFAULT_RECOVERY_MINUTES)
    return value if value > 0 else float(DEFAULT_RECOVERY_MINUTES)


def _traits(player):
    try:
        from engine.traits import TraitSystem
    except Exception:
        return False, False, False
    return (
        TraitSystem.has_effect(player, "curious"),
        TraitSystem.has_effect(player, "homebody"),
        TraitSystem.has_effect(player, "wanderlust"),
    )


def _minutes_per_tick(player) -> float:
    """The tick length this player's clock runs at.

    Observation memories are stamped with a **tick**, so a window expressed in
    game minutes has to be converted before it is compared against a tick delta.
    Getting this wrong is not subtle: at 15 min/tick a "2 hour" window divided
    against ticks is 30 hours, which silently stopped short-tick camps from
    re-earning novelty and showed up as a 59-vs-89 Entertainment split between
    the 15 and 1 min/tick soaks.
    """
    try:
        minutes = float(getattr(player, "minutes_per_tick", 1.0) or 1.0)
    except (TypeError, ValueError):
        return 1.0
    return minutes if minutes > 0 else 1.0


def effective_window(player) -> float:
    """The recovery window in **ticks**, after traits.

    Derived from ``entertainment.novelty_recovery_minutes`` and the player's tick
    length, so the window is the same amount of *game time* whatever the tick.
    Only the window is trait-adjusted: `wanderlust` re-enchants twice as fast, so
    it recovers on half the window. That is how the old `+3 on re-entry`
    behaviour survives the curve.
    """
    try:
        minutes = recovery_minutes()
    except (TypeError, ValueError):
        minutes = float(DEFAULT_RECOVERY_MINUTES)
    _, _, wanderlust = _traits(player)
    if wanderlust:
        minutes = minutes / 2.0
    ticks = minutes / _minutes_per_tick(player)
    return ticks if ticks > 0 else float(DEFAULT_RECOVERY_MINUTES)


def freshness(player, subject_id: str, tick: int, *, window: float | None = None) -> float:
    """How fresh ``subject_id`` is to *player* at *tick*, 0.0-1.0.

    Never experienced = 1.0 (full novelty). The recovered *fraction* is squared
    so a short gap is worth almost nothing and only a real absence pays — see the
    module docstring for why a linear ramp was a farm.

    This is the *raw* measure, in ticks — the window argument, and
    ``effective_window`` by default, is already a tick count derived from game
    minutes. Callers that observe and pay in one step must measure before they
    refresh (see ``grant_freshness``).
    """
    if player is None:
        return 0.0
    try:
        span = float(window) if window else effective_window(player)
    except (TypeError, ValueError):
        span = float(DEFAULT_RECOVERY_MINUTES)
    if span <= 0:
        span = float(DEFAULT_RECOVERY_MINUTES)

    last = player.observation_tick(subject_id)
    if last is None:
        return 1.0
    try:
        elapsed = float(tick) - float(last)
    except (TypeError, ValueError):
        return 1.0
    if elapsed <= 0:
        return 0.0
    recovered = min(1.0, elapsed / span)
    return recovered * recovered


def novelty_bonus(player, subject_id: str, tick: int, *, maximum: int = NOVELTY_MAX,
                  window: float | None = None) -> int:
    """Entertainment for experiencing ``subject_id`` (0 when stale).

    Shorthand for measuring freshness and paying it in one step, for callers whose
    subject has **not** just been observed. A caller that observes and pays
    together — the arrival path — must use ``grant_freshness`` with the value
    ``observe_area`` reported instead, because this re-reads the tick that
    observing just wrote and would return 0.
    """
    if player is None:
        return 0
    if window is None:
        window = effective_window(player)
    return _pay(player, maximum, freshness(player, subject_id, tick, window=window), tick)


def _day_index(player, tick) -> int:
    """The in-game day a tick falls in, at this character's tick length."""
    try:
        from engine.tick_manager import MINUTES_PER_DAY
        minutes_per_day = float(MINUTES_PER_DAY)
    except Exception:
        minutes_per_day = 1440.0
    try:
        minutes = float(tick) * _minutes_per_tick(player)
    except (TypeError, ValueError):
        return 0
    return int(minutes // max(1.0, minutes_per_day))


def novelty_budget_remaining(player, tick) -> float:
    """Novelty this character may still earn today. Rolls over on the in-game day."""
    day = _day_index(player, tick)
    if getattr(player, "_novelty_day", None) != day:
        player._novelty_day = day
        player._novelty_spent = 0
    spent = float(getattr(player, "_novelty_spent", 0) or 0)
    return max(0.0, float(NOVELTY_DAILY_BUDGET) - spent)


def _pay(player, maximum, fresh, tick) -> int:
    """Trait scaling, the daily budget, and the clamp — shared by both paths."""
    if player is None or fresh is None or fresh <= 0:
        return 0
    if "Entertainment" not in getattr(player, "vitals", {}):
        return 0
    curious, homebody, _ = _traits(player)
    if homebody:
        return 0
    gained = round(int(maximum) * float(fresh))
    if curious:
        gained = int(gained * 1.5)
    gained = min(max(0, gained), int(novelty_budget_remaining(player, tick)))
    if gained:
        player._novelty_spent = float(getattr(player, "_novelty_spent", 0) or 0) + gained
        player.vitals["Entertainment"] = min(
            100, player.vitals.get("Entertainment", 0) + gained)
    return gained


def grant_freshness(player, fresh, tick, *, maximum: int = NOVELTY_MAX) -> int:
    """Pay a freshness value that was **already measured**.

    The arrival path needs this: ``observe_area`` measures each subject's
    freshness *before* refreshing the observation (that is the whole reason it
    reports one), so a caller that instead recomputed it would read the tick the
    observation had just written and pay 0 — which is exactly what
    ``_grant_arrival_entertainment`` did, silently, so perceived novelty never
    paid anything.
    """
    return _pay(player, maximum, fresh, tick)


def grant(player, subject_id: str, tick: int, *, maximum: int = NOVELTY_MAX,
          window: float | None = None) -> int:
    """Measure the subject's novelty now and pay it.

    Returns the amount granted so callers can decide whether the experience was
    worth narrating (a stale subject grants nothing and is not news).

    For a subject that was just observed, use ``grant_freshness`` with the
    freshness the observation reported.
    """
    if player is None or not subject_id:
        return 0
    return novelty_bonus(player, subject_id, tick, maximum=maximum, window=window)
