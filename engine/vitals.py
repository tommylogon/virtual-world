"""Vital polarity registry — the single source for how each vital reads.

Three types (task-337):
* ``resource`` — ↑ good, decays downward over time (HP, Energy, ...)
* ``drive``    — ↑ bad, fills upward over time  (Hunger, Thirst, Bladder)
* ``band``     — comfort window, both extremes bad (Temperature; Pleasure later)

Hunger/Thirst flipped from satiation to drive semantics 2026-08-23:
every scenario ever authored food/drink as negative-amount relief, so the
content convention wins and the engine follows.

Use these helpers instead of hardcoding comparisons or "adjusted by N"
messages — UI bars, prompt text and feedback all derive from here.
"""

from typing import Dict

VITAL_POLARITY: Dict[str, str] = {
    # resources: ↑ good, decay ↓
    "HP": "resource",
    "Energy": "resource",
    "Social": "resource",
    "Hygiene": "resource",
    "Sanity": "resource",
    "Entertainment": "resource",
    "Comfort": "resource",
    "Mana": "resource",
    "Satisfaction": "resource",   # future vital (pleasure system)
    # drives: ↑ bad, fill ↑
    "Hunger": "drive",
    "Thirst": "drive",
    "Bladder": "drive",
    # Pleasure system (task-207): all three DECAY when unstimulated, so they
    # use resource mechanics in the baseline-decay loop despite arousal being
    # a "need" narratively.
    "Arousal": "resource",        # eases off slowly when nothing feeds it
    "Stimulation": "resource",    # direct contact meter — drains toward 0
    "Pleasure": "resource",       # afterglow metric — fades fastest
    # bands: comfort window, both extremes bad
    "Temperature": "band",
}

DISPLAY_NAMES = {
    "HP": "HP",
    "Energy": "energy",
    "Hunger": "hunger",
    "Thirst": "thirst",
    "Bladder": "bladder",
    "Social": "social",
    "Hygiene": "hygiene",
    "Sanity": "sanity",
    "Entertainment": "entertainment",
    "Comfort": "comfort",
    "Arousal": "arousal",
    "Stimulation": "stimulation",
    "Pleasure": "pleasure",
}


def polarity(stat: str) -> str:
    """'resource' | 'drive' | 'band'. Unknown stats default to resource."""
    return VITAL_POLARITY.get(stat, "resource")


def is_drive(stat: str) -> bool:
    return polarity(stat) == "drive"


def clamp(stat: str, value) -> int:
    """Clamp to the vital's live range: drives/resources 0..100.
    Bands are NOT clamped here (they drift around a target)."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, value))


def format_vital_change(stat: str, amount: int) -> str:
    """Player-facing adjustment line that states direction AND whether it
    helps or hurts — replaces the ambiguous '{stat} adjusted by N.'"""
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return f"{stat} shifts."
    if amount == 0:
        return f"{stat} unchanged."
    name = DISPLAY_NAMES.get(stat, stat.lower())
    signed = f"{amount:+d}"
    if polarity(stat) == "drive":
        if amount < 0:
            return f"Your {name} eases ({signed})."
        return f"Your {name} builds ({signed})."
    # resource (bands shouldn't route through here, but degrade gracefully)
    if amount > 0:
        return f"{stat} +{abs(amount)} — improves."
    return f"{stat} -{abs(amount)} — worsens."


def format_vitals_readout(vitals: dict) -> str:
    """Format a vitals dict for the ``stats`` command — one line per vital,
    polarity-aware. Drives note they fill toward crisis; bands note the
    comfort window. Resources need no annotation (high = good)."""
    if not vitals:
        return "(none)"
    lines = []
    for stat, value in vitals.items():
        p = polarity(stat)
        if p == "drive":
            lines.append(f"  {stat}: {value} — fills toward 100")
        elif p == "band":
            lines.append(f"  {stat}: {value} — comfort band")
        else:
            lines.append(f"  {stat}: {value}")
    return "\n".join(lines)
