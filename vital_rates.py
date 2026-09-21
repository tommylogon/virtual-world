"""Canonical per-minute vital rates for long-horizon simulation.

Every rate in this module is expressed **per in-game minute** — not per
tick-as-a-session-beat, which is what the pre-2026-09 tuning assumed. A tick is
``world.time_per_tick_minutes`` of game time, which a scenario or the live
Engine Config can set to anything, so callers pass that length as ``minutes``
and the effect scales with it: a 15-minute tick drains 15 minutes' worth. Left
unscaled, decay and the clock disagree the moment the tick stops being a
minute — a 15-minute world would starve everyone 15x too slowly.

Fractional rates are applied through :func:`change`, a per-player per-stat
accumulator that carries the leftover between ticks. Sub-1 rates vanish under
plain ``int()``, so without the accumulator Hunger (0.0034/min) and Thirst
(0.025/min) would never move. Integer-style callers are unaffected: a whole
unit lands every tick and the accumulator stays at ~0.

Legacy effects authored for the old "1/tick" feel (trait micro-modifiers,
group drains) are scaled by :data:`LEGACY_PER_TICK` so their *relative*
balance survives translation to a per-minute world.
"""

from __future__ import annotations

# ── Baseline decay ──────────────────────────────────────────────────────
# Resources drain DOWN toward 0; drives (Hunger, Thirst) FILL toward 100
# (starving/dehydrated at max). Read by TickManager.tick_turn via
# VirtualWorld.baseline_decay and Player.decay_rates.
#
# From a FULL meter: Hunger reaches the starvation edge at ~3 weeks,
# Thirst the dehydration edge at ~3 days, Energy empties over a ~16h
# waking day. Social/Hygiene/Entertainment run on a ~1-2 day cycle;
# Sanity is deliberately slow (~14 days) and mostly condition-driven.
BASELINE_DECAY = {
    "Energy": 0.104,
    "Hunger": 0.0034,
    "Thirst": 0.0250,
    "Social": 0.020,
    "Hygiene": 0.020,
    "Sanity": 0.005,
    "Entertainment": 0.030,
    "Mana": 0.0,
}

# Bladder is not in BASELINE_DECAY — it has its own thirst-modulated fill.
# Filling every ~4h is realistic; the hygiene cost of each event is what
# must stay modest or Hygiene crashes four times a day.
BLADDER_FILL = 0.42
BLADDER_HYGIENE_PENALTY = 8.0

# ── Environmental per-minute effects ────────────────────────────────────
ENV_STALE_ENERGY = 0.02
ENV_HUMID_HYGIENE = 0.02
ENV_TOXIC_HP = 0.5
ENV_ROT_HYGIENE = 0.02
ENV_DARK_SANITY = 0.02
ENV_PERFUME_ENTERTAINMENT = 0.05

# ── Core-temperature per-minute effects ─────────────────────────────────
COLD_MILD_ENERGY = 0.05        # core 36..37
COLD_MODERATE_ENERGY = 0.10    # core 35..36
COLD_MODERATE_HP = 0.01
COLD_SEVERE_ENERGY = 0.15      # core 33..35
COLD_SEVERE_HP = 0.05
COLD_CRITICAL_HP = 0.15        # core < 33
HEAT_MILD_THIRST = 0.02        # core 37..38 — heat makes you thirstier
HEAT_MODERATE_THIRST = 0.05    # core 38..40
HEAT_MODERATE_HP = 0.05
HEAT_SEVERE_HP = 0.20          # core > 40

# ── Recovery ────────────────────────────────────────────────────────────
HP_REGEN = 0.02                # ~1.2/hr while well-fed, hydrated, sane
SLEEP_ENERGY_REGEN = 0.30      # net ~+0.20/min after baseline Energy drain

# ── Social / sanity coupling ────────────────────────────────────────────
# Company is MAINTENANCE, not a source. The gain deliberately equals the Social
# baseline, so standing near people stops the rot (net 0/min) without filling
# the meter — what actually builds Social is *interacting* with them (task-423's
# background social actions, and the foreground conversation loop).
#
# It used to be 0.030, which filled Social from mere co-presence: +0.010/min is
# +14.4/day with nothing competing, so Social pegged at 100 in a week and every
# social action landed on a capped vital. Raising it above the baseline is
# therefore a design change, not a tuning nudge — `social_gain` traits scale this
# in BOTH directions, and an extrovert (x2) exceeding the baseline is intended:
# being among people genuinely nourishes them, while an introvert (x0) is
# unaffected by the crowd.
SOCIAL_COMPANY_GAIN = 0.020
SOCIAL_ALONE_DRAIN = 0.020     # extra beyond baseline while alone
SOCIAL_ISOLATION_EXTRA = 0.020  # after 5 consecutive alone-ticks
SANITY_PENALTY_SOCIAL_LOW = 0.005
SANITY_PENALTY_SOCIAL_VERY_LOW = 0.010
SANITY_PENALTY_ENT_LOW = 0.005
SANITY_PENALTY_ENT_VERY_LOW = 0.010

# ── Legacy scaling ──────────────────────────────────────────────────────
# Trait micro-modifiers and group drains were authored as per-tick deltas
# (e.g. impatient Entertainment -3/tick). Scaling by 1/20 keeps their
# relative weight without letting a single trait swamp a per-minute meter.
LEGACY_PER_TICK = 0.05


def tick_minutes(world, default: float = 1.0) -> float:
    """How much game time one tick covers, tolerating junk from config/saves.

    The single place that reads ``time_per_tick_minutes`` for rate scaling, so
    the engine and the activity system cannot coerce it differently.
    """
    try:
        minutes = abs(float(getattr(world, "time_per_tick_minutes", default) or default))
    except (TypeError, ValueError):
        return default
    return minutes or default


def change(player, stat, per_minute, *, minutes=1, cap=None, floor=0):
    """Accumulate a per-minute change and apply whole units when they land.

    ``per_minute`` is signed (negative drains, positive restores/fills) and
    ``minutes`` is how much game time this tick covers — normally
    ``world.time_per_tick_minutes``. Pass it from every caller that is not
    already iterating minutes, or the effect silently freezes at the 1-minute
    rate while the clock runs faster.

    Returns the integer step actually applied this tick (0 most ticks for
    fractional rates), so callers can log or branch on real change.
    """
    vitals = getattr(player, "vitals", None)
    if not vitals or stat not in vitals or not per_minute:
        return 0
    try:
        minutes = abs(float(minutes))
    except (TypeError, ValueError):
        minutes = 1.0
    if not minutes:
        return 0
    accum = getattr(player, "_rate_accum", None)
    if accum is None:
        accum = player._rate_accum = {}
    accum[stat] = accum.get(stat, 0.0) + per_minute * minutes
    step = int(accum[stat])
    accum[stat] -= step
    if not step:
        return 0
    if cap is None:
        cap = vitals.get("Max_HP", 100) if stat == "HP" else 100
    vitals[stat] = max(floor, min(cap, vitals[stat] + step))
    return step
