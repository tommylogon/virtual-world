"""Scale-correct ability scores per size tier (task-606).

A leviathan is not STR 9 and a housecat is not CON 20. Until this module
existed the engine had exactly one number for ability scores on a character that
is a person — 10, or whatever the stat block said — and the size tiers, new in
task-605, had nothing to say about strength. The 5e reference blocks are the
**baseline curve**, not the ceiling: a starship is `giant`, a ghost is `small`
and takes no space (task-653), a housecat is `tiny`. The tiers are the spine;
the values inside a tier are the authoring surface, which is what lets the same
curve fit fantasy, modern, sci-fi, horror and romance.

Nothing clamps ability scores, so STR 35 has always been storable — and so has
STR 1. This module is therefore about *authoring and flagging*, not about
enforcement:

* :func:`stats_for_size` produces a scale-correct block for a tier, so an author
  picking "giant" starts from something defensible;
* :func:`scale_issues` reports a block that contradicts its own size, so an
  editor can say "you called this a leviathan and gave it STR 9" instead of the
  discrepancy living silently until somebody tries to move it.

Deliberately **not** done here: clamping. A character is not corrected by the
engine; it is corrected by the author, and the engine's job is to make the
disagreement visible. A clamped stat silently loses the information that it was
wrong.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

from engine.size import SIZE_TIERS

#: The six abilities every character carries. Declared here rather than inferred
#: from whatever a stat block happens to contain, so "missing" is answerable.
ABILITIES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")

#: The 5e baseline curve (task-606's decided table), as **reference points**:
#: the canonical creature for each tier. `small` is a goblin at STR 8, `giant`
#: is a hill giant at STR 21. These are the numbers an editor panel shows and
#: the numbers `stats_for_size` derives from.
#:
#: They are NOT bounds, and that distinction is the whole design. A tier is a
#: bucket of body sizes, and 5e's *small* category contains both a goblin (STR 8)
#: and an imp; encoding the goblin as an exclusive range would flag every other
#: thing that legitimately belongs there. Enforcing a range is what
#: :func:`scale_issues` does instead, and it enforces a tolerance rather than a
#: box.
SIZE_TIER_REFERENCE: dict[str, dict] = {
    "tiny": {"STR": (2, 3), "CON": (9, 10)},
    "small": {"STR": (8, 8), "CON": (10, 10)},
    "normal": {"STR": (10, 13), "CON": (10, 12)},
    "huge": {"STR": (18, 19), "CON": (14, 16)},
    "giant": {"STR": (21, 23), "CON": (16, 21)},
    "titanic": {"STR": (27, 45), "CON": (22, 25)},
}

#: How far from a tier's reference point an ability score may be before it is
#: reported. A factor of two rather than a box, for the reason above: a wolf is
#: STR 12 and a goblin is STR 8 and both are `small`, and a rule that flagged
#: either would be a rule nobody could act on.
#:
#: A flag is only worth having if it is rare and true. This one fires on a
#: `giant` at STR 1 and on a character with no stat block at all, and stays
#: quiet on every creature 5e itself would place in that category.
TOLERANCE = 2.0

#: The abilities that scale with size. The rest are free: a dragon is no more
#: intelligent than a rat and no less wise, and only STR and CON answer to mass.
MASS_SCALED_ABILITIES = ("STR", "CON")

#: A default stat block per tier, for :func:`stats_for_size`. The value chosen
#: is the **low** end of the range for everything except `normal`, because a
#: block that errs low is a young or a weakling and reads as intentional, whereas
#: a block that errs high reads as a typo.
SIZE_TIER_DEFAULTS: dict[str, dict] = {
    "tiny": {"STR": 2, "DEX": 14, "CON": 9, "INT": 6, "WIS": 12, "CHA": 6},
    "small": {"STR": 8, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 8},
    "normal": {"STR": 11, "DEX": 12, "CON": 11, "INT": 10, "WIS": 10, "CHA": 10},
    "huge": {"STR": 18, "DEX": 8, "CON": 15, "INT": 6, "WIS": 7, "CHA": 7},
    "giant": {"STR": 21, "DEX": 6, "CON": 19, "INT": 5, "WIS": 7, "CHA": 8},
    "titanic": {"STR": 30, "DEX": 10, "CON": 24, "INT": 15, "WIS": 11, "CHA": 13},
}

#: Beyond this, a score is treated as unreachable rather than merely extreme.
#: 5e's creature range tops out at 30 (the Ancient White Dragon); the Tarrasque
#: is 45. So 30+ is "a monster", and anything under 1 is a data error — a
#: negative strength is not a character, it is a subtraction that leaked.
PLAUSIBLE_MIN = 1
PLAUSIBLE_MAX = 50


#: Tags marking something that is not a creature. The ability curve describes
#: what a body can do, and a straw practice dummy on a wooden frame has a body
#: without having a strength — it is tagged `giant` and `STR 1` on purpose,
#: because the whole point of it is that it cannot fight back. Checking it
#: against the curve would report a deliberate piece of authoring as a defect.
INANIMATE_TAGS = ("inanimate", "object", "training", "dummy", "furniture")


def is_inanimate(entity=None, *, tags=None) -> bool:
    """True when this is not a creature the ability curve should judge.

    Accepts a ``Player``, a node, or a raw library definition dict — a data file
    is exactly where this question gets asked.
    """
    source = tags
    if source is None:
        if entity is None:
            return False
        if isinstance(entity, dict):
            source = entity.get("tags")
        else:
            source = getattr(entity, "tags", None)
            if source is None:
                props = getattr(entity, "properties", None)
                source = (props or {}).get("tags") if isinstance(props, dict) else None
    if isinstance(source, str):
        source = [part.strip() for part in source.split(",")]
    lowered = {str(t).lower() for t in (source or ())}
    return bool(lowered & set(INANIMATE_TAGS))


def normalize_stat_block(raw) -> dict:
    """Accept a stat block in either case, and keep non-ability keys.

    The library had **two vocabularies** for the same six abilities: 37 files
    wrote `STR`/`DEX`/... and 31 wrote `str`/`dex`/..., with no overlap in style.
    Every writer did `player.stats = data.get("stats", ...)`, so a lowercase
    block replaced the uppercase defaults and then failed every
    `stats.get("STR", 10)` in the engine — `the butcher`, authored `str: 18`,
    fought at STR 10.

    That is this task's complaint in shipped data rather than as a hypothetical:
    a leviathan was not STR 9, it was *no* STR.

    Case-insensitive keys fold to the canonical uppercase spelling; anything that
    is not one of the six abilities (`attack_bonus`, and whatever an author adds
    next) is carried through untouched — this is a normaliser, not a filter.
    Where a block states both spellings the canonical one wins, because that is
    the one the engine reads.

    Lives here rather than at each call site because there are six writers
    (`engine/effects.py`, `engine/serialization.py`, three in
    `routes/player_ops.py`, one in `routes/library_ops.py`) and a normaliser
    that has to be remembered in six places is a normaliser that will be missed
    in the seventh.
    """
    if not isinstance(raw, dict):
        return {}
    out, staged = {}, {}
    for key, value in raw.items():
        name = str(key)
        if name.upper() in ABILITIES:
            if name in ABILITIES:
                out[name] = value
            else:
                staged.setdefault(name.upper(), value)
        else:
            out[name] = value
    for name, value in staged.items():
        out.setdefault(name, value)
    return out


def stats_for_size(size=None, *, overrides=None) -> dict:
    """A scale-correct stat block for *size*.

    ``overrides`` are applied last, so a caller can say
    ``stats_for_size("huge", overrides={"CON": 16})`` and get an ogre that is
    tougher than average without having to restate the other five.

    An unknown or absent size returns the ``normal`` block — a character with no
    authored size is a person, which is what every one of the 70 library
    characters is today.
    """
    tier = str(size or "normal").strip().lower()
    if tier not in SIZE_TIERS:
        tier = "normal"
    block = dict(SIZE_TIER_DEFAULTS[tier])
    for key, value in (overrides or {}).items():
        name = str(key).upper()
        if name in block:
            try:
                block[name] = int(value)
            except (TypeError, ValueError):
                continue
    return block


def ability_range(size, ability) -> tuple | None:
    """The reference *points* a size is built around, or ``None`` when the
    ability does not scale with mass and therefore has no reference at all."""
    tier = str(size or "normal").strip().lower()
    entry = SIZE_TIER_REFERENCE.get(tier) or {}
    name = str(ability or "").strip().upper()
    return tuple(entry[name]) if name in entry else None


def tolerance_band(size, ability) -> tuple | None:
    """The band a stat block of this size may sit in without being reported.

    The tier's reference, widened by :data:`TOLERANCE`. Returns ``None`` for an
    ability that does not scale with mass — the mental abilities have no band,
    because the size of a thing says nothing about its intelligence and a band
    here would be an invitation to author a dragon at INT 3.
    """
    reference = ability_range(size, ability)
    if reference is None:
        return None
    low = min(reference)
    high = max(reference)
    return (max(PLAUSIBLE_MIN, low / TOLERANCE), high * TOLERANCE)


def scale_issues(stats=None, size=None, *, entity=None) -> list:
    """Everything about this stat block that contradicts its size.

    Returns human-readable strings, because the callers are an editor hint and a
    test assertion and both want a sentence. An empty list means the block is
    consistent with the size, **or** that no size was authored — absence is not
    a finding, because a character with no size is a person and a person with
    STR 9 is a weedy person, not a bug.
    """
    if entity is not None:
        if stats is None:
            stats = getattr(entity, "stats", None)
        if size is None:
            size = getattr(entity, "size", None)

    # A straw dummy is tagged `giant` and STR 1 because it cannot fight back.
    # Judging it against a curve about what bodies can do reports a deliberate
    # piece of authoring as a defect, and a flag that is wrong about the one
    # training dummy in the library is a flag nobody trusts.
    if is_inanimate(entity):
        return []

    issues = []
    stats = stats or {}
    tier = str(size or "").strip().lower()
    if tier and tier not in SIZE_TIERS:
        issues.append(f"size '{tier}' is not one of {SIZE_TIERS}")
        tier = ""

    for ability in MASS_SCALED_ABILITIES:
        if ability not in stats:
            continue
        raw = stats[ability]
        try:
            value = int(raw)
        except (TypeError, ValueError):
            issues.append(f"{ability} is not a number ({raw!r})")
            continue
        if value < PLAUSIBLE_MIN or value > PLAUSIBLE_MAX:
            issues.append(
                f"{ability} {value} is outside anything playable "
                f"({PLAUSIBLE_MIN}-{PLAUSIBLE_MAX})")
            continue
        band = tolerance_band(tier, ability) if tier else None
        if not band:
            continue
        low, high = band
        low_txt, high_txt = f"{low:g}", f"{high:g}"
        if value < low or value > high:
            issues.append(
                f"{ability} {value} is far from what a {tier} creature should "
                f"have (reference {min(ability_range(tier, ability)):g}"
                f"-{max(ability_range(tier, ability)):g}, tolerated "
                f"{low_txt}-{high_txt})")

    if tier and not any(ability in stats for ability in MASS_SCALED_ABILITIES):
        issues.append(f"a {tier} character has no STR or CON at all")
    return issues


def is_scale_correct(stats=None, size=None, *, entity=None) -> bool:
    """True when nothing about this block contradicts its size."""
    return not scale_issues(stats, size, entity=entity)


def describe_curve() -> dict:
    """The whole curve, for an editor's reference panel.

    Rendered from the two tables rather than transcribed, so the panel cannot
    drift from what :func:`scale_issues` actually enforces.
    """
    return {
        tier: {
            "abilities": dict(SIZE_TIER_REFERENCE[tier]),
            "example": dict(SIZE_TIER_DEFAULTS[tier]),
            "tolerated": {
                ability: tuple(round(v, 1) for v in tolerance_band(tier, ability))
                for ability in MASS_SCALED_ABILITIES
            },
        }
        for tier in SIZE_TIERS
        if tier in SIZE_TIER_REFERENCE
    }
