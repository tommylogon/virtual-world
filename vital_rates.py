"""Canonical per-minute vital rates for long-horizon simulation.

VirtualWorld's core clock is one in-game minute per tick (the engine default
and what every long-run scenario pins ``time_per_tick_minutes`` to). Every
rate in this module is therefore expressed **per in-game minute** — not per
tick-as-a-session-beat, which is what the pre-2026-09 tuning assumed.

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
SOCIAL_COMPANY_GAIN = 0.030
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


def change(player, stat, per_minute, *, cap=None, floor=0):
    """Accumulate a per-minute change and apply whole units when they land.

    ``per_minute`` is signed (negative drains, positive restores/fills).
    Returns the integer step actually applied this tick (0 most ticks for
    fractional rates), so callers can log or branch on real change.
    """
    vitals = getattr(player, "vitals", None)
    if not vitals or stat not in vitals or not per_minute:
        return 0
    accum = getattr(player, "_rate_accum", None)
    if accum is None:
        accum = player._rate_accum = {}
    accum[stat] = accum.get(stat, 0.0) + per_minute
    step = int(accum[stat])
    accum[stat] -= step
    if not step:
        return 0
    if cap is None:
        cap = vitals.get("Max_HP", 100) if stat == "HP" else 100
    vitals[stat] = max(floor, min(cap, vitals[stat] + step))
    return step
