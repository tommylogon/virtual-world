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

**And the ceiling** (task-538). This module also answers "what is the top of
this vital on this character?", which used to be a literal ``100`` written out in
about ten places — ``player.py``, ``effects.py``, both deserialisers, both vital
effect handlers, ``vital_rates.change``, ``combat.py``, ``traits.py`` and the
HP-regeneration gate in ``tick_manager``. The literal was harmless only because
``Max_HP`` was itself always 100; a stat block that declares a real maximum
(``"hit_dice": "2d6"`` -> 12 HP, a 5e goblin at 7) made every one of those
sites wrong at once, and two of them wrong *silently*:

* ``heal`` clamped to 100, so healing a 7-HP goblin by 5 produced 12 HP;
* the regen gate read "HP < 100", so a 7-HP goblin at full health was
  permanently "below maximum" and regenerated forever.

Call :func:`ceiling` rather than writing the number.
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


#: Vitals that model a *socialised human* life and do not apply to fauna. A bear
#: has hunger, thirst, energy and temperature; it does not get lonely, bored, or
#: suffer a social breakdown (task-399 backsim).
ANIMAL_SKIPPED_VITALS = frozenset({"Social", "Sanity", "Entertainment"})


def is_animal(player) -> bool:
    """True for characters tagged ``animal`` (fauna, not people)."""
    tags = getattr(player, "tags", None) or []
    return "animal" in {str(t).lower() for t in tags}


def clamp(stat: str, value) -> int:
    """Clamp to the vital's live range: drives/resources 0..100.
    Bands are NOT clamped here (they drift around a target)."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, value))


# ── The ceiling (task-538) ───────────────────────────────────────────────

#: The scale a vital falls back to when a character declares no maximum.
#: Percent-style resources and drives are 0..100. **HP is not in here on
#: purpose**: the fallback for HP is :data:`DEFAULT_MAX_HP`, which is the
#: table default for a *person*, not an assumption that HP is always 100.
DEFAULT_VITAL_MAX = 100

#: HP's default maximum. Kept at 100 for every character that does not author
#: one, because ~525 library items and 68 library characters predate this task
#: and must keep hydrating to the vitals they always had (the acceptance
#: criterion for task-538). It is a *default*, not a scale: any character that
#: declares `Max_HP` or `hit_dice` is bounded by its own value everywhere.
DEFAULT_MAX_HP = 100

#: Vitals whose live range is anatomical rather than 0-100. Temperature is a
#: body temperature in degrees and is driven by its own band model in
#: ``tick_manager`` (``cold_floor``/``normal``/``heat_ceiling``), so clamping it
#: to 0-100 was always a fiction. Mana is a percentage like everything else.
BAND_VITAL_FLOOR = {
    "Temperature": 0.0,
}


def ceiling(vitals: dict | None, stat: str) -> float:
    """The top of ``stat`` for this character — the one answer (task-538).

    Resolution order, and the order is the whole point:

    1. an authored ``Max_{stat}`` companion in the character's own vitals
       (``Max_HP``, ``Max_Mana``, …). This is the ``Max_`` convention
       ``routes/player_ops`` already looked for, so a stat block that sets
       ``Max_HP: 7`` is bounded by 7 here;
    2. for HP, a value derived from ``hit_dice`` — see
       :func:`engine.vitals.hit_dice_max`, applied by the deserialisers at load
       time rather than here, so this function stays a pure reader;
    3. the vital's natural scale: ``DEFAULT_MAX_HP`` for HP, 100 for the
       percentage resources and drives, and ``inf`` for a band vital like
       Temperature, which has a comfort window rather than a ceiling.

    Never silently returns 100 for HP. That is the bug this replaced.
    """
    vitals = vitals or {}
    if not isinstance(vitals, dict):
        return DEFAULT_MAX_HP
    max_key = f"Max_{stat}"
    if max_key in vitals:
        try:
            return float(vitals[max_key])
        except (TypeError, ValueError):
            pass
    if stat == "HP":
        return DEFAULT_MAX_HP
    if stat in BAND_VITAL_FLOOR:
        # A band is bounded by its own comfort window, not by a maximum; the
        # tick manager decides what counts as lethal.
        return float("inf")
    return DEFAULT_VITAL_MAX


def clamp_to_ceiling(vitals: dict, stat: str, value) -> float:
    """Clamp ``value`` into this character's live range for ``stat``.

    The one place a vital is written against its ceiling, so ``heal`` and
    ``adjust_vital`` cannot disagree about where the top is. Floors at 0 for
    every vital including HP (dead is 0, not negative) and, for a band vital,
    at the anatomical floor rather than 0.
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0
    top = ceiling(vitals, stat)
    floor = BAND_VITAL_FLOOR.get(stat, 0.0)
    if top == float("inf"):
        return max(floor, value)
    return max(floor, min(top, value))


# ── Hit dice (task-538) ──────────────────────────────────────────────────

#: How ``hit_dice`` resolves at load time. A **bestiary** wants the average —
#: the 7 HP of an orc is a stat line, not a dice roll, and re-rolling it on
#: every load would make a creature's health drift every time a save was read.
#: A character that *rolls up* wants the roll, which is what
#: ``mode="roll"`` is for.
HIT_DICE_MODES = ("average", "roll")


def parse_hit_dice(expression) -> tuple[int, int, int] | None:
    """``"7d8+14"`` -> ``(7, 8, 14)``; ``(2, 6, -1)`` -> itself.

    Returns ``None`` for anything it cannot read rather than guessing — a typo
    in a stat block must be visible, not silently resolved to zero HP. A bare
    ``"d8"`` means 1d8, matching how weapon damage already reads (``task-607``
    fixed the same shorthand in ``equipment_bonuses.parse_damage``).
    """
    if isinstance(expression, (list, tuple)):
        parts = list(expression) + [0, 0, 0]
        try:
            return int(parts[0]), int(parts[1]), int(parts[2])
        except (TypeError, ValueError):
            return None
    if isinstance(expression, dict):
        return parse_hit_dice(
            expression.get("dice") or expression.get("hit_dice")
            or expression.get("expression")
        )
    text = str(expression or "").strip().replace(" ", "")
    if not text or "d" not in text.lower():
        return None
    import re

    match = re.match(r"^(\d*)[dD](\d+)(?:([+-])(\d+))?$", text)
    if not match:
        return None
    count = int(match.group(1)) if match.group(1) else 1
    sides = int(match.group(2))
    if sides <= 0 or count <= 0:
        return None
    bonus = int(match.group(4)) * (1 if match.group(3) == "+" else -1) \
        if match.group(3) else 0
    return count, sides, bonus


def hit_dice_max(expression, mode: str = "average", rng=None) -> int | None:
    """Resolve a hit-dice expression to a ``Max_HP`` value, or ``None``.

    ``average`` is the default and the right answer for a bestiary: 7d8+14 is
    49, which is what the stat block means. ``roll`` is for a character that
    rolls up at creation — pass ``rng`` (anything with ``randint``) or the
    standard library is used.

    The result is floored at 1: a stat block that resolves to 0 or less is
    authored wrong, and a character with no maximum at all is a far worse
    failure mode than one point of health.
    """
    parsed = parse_hit_dice(expression)
    if parsed is None:
        return None
    count, sides, bonus = parsed
    if str(mode).lower() == "roll":
        import random

        roller = rng or random
        total = sum(roller.randint(1, sides) for _ in range(count)) + bonus
    else:
        # The true mean, rounded half-up — 2d6 is 7, not the 6 an integer
        # division gives, and `round()` is banker's rounding so half-up has to
        # be spelled out. Half-up is the convention every stat block uses.
        import math

        total = math.floor(count * (sides + 1) / 2 + bonus + 0.5)
    return max(1, int(total))


def apply_hit_dice(vitals: dict, data: dict) -> dict:
    """Derive ``Max_HP`` from ``hit_dice`` when the data declares one.

    **An explicit ``Max_HP`` wins.** The ~525 library items and 68 library
    characters predate this task and set ``Max_HP`` directly, and a stat block
    that declares both has already said what it wants; the formula is only ever
    the fallback. Recording that as a decision here rather than raising is the
    deliberate choice — a bestiary listing both is redundant, not contradictory,
    and failing the load over it would be worse than honouring the number.

    Returns the same ``vitals`` dict, mutated in place.
    """
    if not isinstance(data, dict) or not isinstance(vitals, dict):
        return vitals
    # `hit_dice` can arrive at the top level (a save) or inside a `vitals`
    # block (a library character), so both shapes are read here.
    nested = data.get("vitals")
    sources = [data]
    if isinstance(nested, dict):
        sources.append(nested)
    expression = None
    mode = "average"
    for source in sources:
        if source.get("hit_dice") is not None:
            expression = source["hit_dice"]
            mode = (source.get("hit_dice_mode") or source.get("hit_dice_roll")
                    or "average")
            break
    if expression is None:
        return vitals
    if any(s.get("Max_HP") is not None for s in sources):
        return vitals
    resolved = hit_dice_max(expression, mode=mode)
    if resolved is None:
        return vitals
    vitals["Max_HP"] = resolved
    current = vitals.get("HP")
    if current is None:
        vitals["HP"] = resolved
    else:
        try:
            vitals["HP"] = max(0, min(resolved, int(current)))
        except (TypeError, ValueError):
            vitals["HP"] = resolved
    return vitals


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
