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


def freshness(player, subject_id: str, tick: int, *, window: float | None = None) -> float:
    """How fresh ``subject_id`` is to *player* at *tick*, 0.0-1.0.

    Never experienced = 1.0 (full novelty). The recovered *fraction* is squared
    so a short gap is worth almost nothing and only a real absence pays — see the
    module docstring for why a linear ramp was a farm.
    """
    if player is None:
        return 0.0
    try:
        span = float(window) if window else recovery_minutes()
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
    """Entertainment to grant for experiencing ``subject_id`` (0 when stale).

    Trait scaling lives here so every subject kind reads the same rule:
    ``curious`` gets half again as much, ``homebody`` gets nothing, and
    ``wanderlust`` re-enchants twice as fast (it recovers on half the window),
    which is how the old ``+3 on re-entry`` behaviour survives the curve.
    """
    curious, homebody, wanderlust = _traits(player)
    if homebody:
        return 0
    span = window if window else recovery_minutes()
    if wanderlust:
        span = float(span) / 2.0
    gained = round(int(maximum) * freshness(player, subject_id, tick, window=span))
    if curious:
        gained = int(gained * 1.5)
    return max(0, gained)


def grant(player, subject_id: str, tick: int, *, maximum: int = NOVELTY_MAX,
          window: float | None = None) -> int:
    """Apply the novelty bonus for a subject to the player's Entertainment.

    Returns the amount granted so callers can decide whether the experience was
    worth narrating (a stale subject grants nothing and is not news).
    """
    if player is None or not subject_id:
        return 0
    if "Entertainment" not in getattr(player, "vitals", {}):
        return 0
    gained = novelty_bonus(player, subject_id, tick, maximum=maximum, window=window)
    if gained:
        player.vitals["Entertainment"] = min(
            100, player.vitals.get("Entertainment", 0) + gained)
    return gained
