"""Incorporeal undead: what cannot be done to them (task-490).

The still-open half of task-309. That task gave undead identities — the
``undead`` tag (not alive, corporeal) and the ``ghost`` tag (incorporeal,
unseen until manifested) — and wired them into visibility and vitals. What it
left out is the other side of the coin: **what those identities do to an
attacker**. A 5e ghost cannot be cut, cannot be chilled, cannot be poisoned, and
cannot be grabbed; today it can be all four, because nothing here existed.

The identities live in :mod:`engine.player_manager` (``is_undead`` /
``is_incorporeal``, both tag checks). This module turns them into a *defence
profile* and applies it; the two hook points are damage resolution in
:mod:`engine.combat` and condition application in :mod:`engine.conditions`.

**Why a separate profile and not more entries in ``aggregate_bonuses``.**
Resistances there are a flat subtraction assembled from equipped items
(``resisted_damage`` does ``base - resist``). 5e resistance *halves* and
immunity *negates*, neither of which is expressible as a flat number, and
folding undead into the item aggregate would make a sword do less damage to a
ghost, which is not what either rule means. So a profile is a separate, explicit
thing with its own arithmetic.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Optional

#: Damage types an undead is outright immune to. 5e lists cold, necrotic and
#: poison; the engine's own type vocabulary is what matters here, so the
#: canonical spellings are listed and matched case-insensitively.
UNDEAD_IMMUNE_DAMAGE: FrozenSet[str] = frozenset({
    "cold", "necrotic", "poison", "poisoned",
})

#: Damage types an undead resists but is not immune to. Kept for creatures that
#: carry a broader profile than the base undead one.
UNDEAD_RESIST_DAMAGE: FrozenSet[str] = frozenset({
    "lightning", "thunder", "force",
})

#: Conditions a ghost cannot be put into. 5e's "All except exhaustion" list: a
#: ghost has no body to hold, no limbs to twist, no strength to tire. ``exhausted``
#: is deliberately NOT here — the 5e wording is "all conditions except
#: exhaustion", and dropping it would be the same kind of well-meaning edit that
#: turns a rule into a different rule.
GHOST_IMMUNE_CONDITIONS: FrozenSet[str] = frozenset({
    "grappled", "restrained", "prone", "paralysed", "petrified",
    "unconscious", "stunned", "charmed", "deaf",
    "blushing", "nipple_hard", "sensitized", "wet", "wetness",
    "aroused", "highly_aroused", "overstimulated", "frantic",
    "injured", "bleeding", "hypothermia", "suffocating",
})

#: Conditions a *corporeal* undead (a zombie) is immune to. Much shorter: it has
#: a body, so it can be grappled and bleeds, but it does not tire and does not
#: feel pain.
UNDEAD_IMMUNE_CONDITIONS: FrozenSet[str] = frozenset({
    "exhausted", "blushing", "nipple_hard", "sensitized", "aroused",
    "highly_aroused", "frantic", "overstimulated",
})


#: Sentinel in a damage profile's ``resist`` set meaning "resist damage that came
#: from a nonmagical weapon", whatever its damage type.
#:
#: It has to be a sentinel rather than a damage type because the 5e rule is about
#: the *weapon*, not the injury: a ghost resists a mundane blade whether it cuts,
#: bludgeons or pierces. Keying it on ``slashing`` would miss every other weapon.
NONMAGICAL_WEAPON = "*nonmagical_weapon*"


def _has_tag(player, tag: str) -> bool:
    return tag in (getattr(player, "tags", None or []))


def is_incorporeal_undead(player) -> bool:
    """A ghost: undead *and* incorporeal.

    The full 5e ghost profile. ``is_undead_ghost`` in the player manager is the
    broader "spectral entity" alias and would wrongly include a plain zombie, so
    this checks both tags rather than reusing it.
    """
    return _has_tag(player, "undead") and _has_tag(player, "ghost")


def damage_profile(player) -> Dict[str, FrozenSet[str]]:
    """What this character resists or is immune to.

    Returns ``{"resist": set(...), "immune": set(...)}``. ``resist`` may contain
    :data:`NONMAGICAL_WEAPON`, which means "halve anything a mundane weapon
    does" and is only applied by a caller that knows where the hit came from —
    see ``apply_damage_resistance``'s ``from_nonmagical_weapon``.

    An ordinary character gets two empty sets rather than None, so a caller can
    apply the result without branching on character type.
    """
    if is_incorporeal_undead(player):
        return {"resist": {NONMAGICAL_WEAPON} | set(UNDEAD_RESIST_DAMAGE),
                "immune": set(UNDEAD_IMMUNE_DAMAGE)}
    if _has_tag(player, "undead"):
        return {"resist": set(), "immune": set(UNDEAD_IMMUNE_DAMAGE)}
    return {"resist": set(), "immune": set()}


def condition_immunities(player) -> FrozenSet[str]:
    """Conditions that cannot be applied to this character."""
    if is_incorporeal_undead(player):
        return GHOST_IMMUNE_CONDITIONS
    if _has_tag(player, "undead"):
        return UNDEAD_IMMUNE_CONDITIONS
    return frozenset()


def is_immune_to_condition(player, condition: str) -> bool:
    return str(condition) in condition_immunities(player)


def _matches(damage_type: str, table) -> bool:
    """Case-insensitive match, tolerating a few spelling variants."""
    if not damage_type:
        return False
    key = str(damage_type).strip().lower()
    return key in table


def apply_damage_resistance(damage: int, damage_type: str,
                            profile: Optional[dict] = None,
                            from_nonmagical_weapon: bool = False) -> dict:
    """Halve resisted damage, zero immune damage.

    Returns ``{"damage": int, "resisted": bool, "immune": bool}``. 5e semantics:
    resistance halves, immunity negates, and a halved 1 is 0 — which is why this
    is written as ``damage // 2`` rather than a float round, so a resisted point
    of bludgeoning damage really does become nothing.

    ``from_nonmagical_weapon`` is what arms the
    :data:`NONMAGICAL_WEAPON` half of a profile. It is a parameter rather than
    something derived here because only the caller knows whether there was a
    weapon at all — a bare-fisted hit is not a weapon hit.
    """
    profile = profile or {}
    immune = profile.get("immune") or ()
    resist = profile.get("resist") or ()
    if _matches(damage_type, immune):
        return {"damage": 0, "resisted": False, "immune": True}
    resisted_by_type = _matches(damage_type, resist)
    resisted_by_weapon = from_nonmagical_weapon and NONMAGICAL_WEAPON in resist
    if resisted_by_type or resisted_by_weapon:
        return {"damage": max(0, int(damage) // 2), "resisted": True,
                "immune": False}
    return {"damage": int(damage), "resisted": False, "immune": False}


def resistance_for_weapon(player, weapon_props: dict) -> dict:
    """Damage profile with the weapon's magicalness taken into account.

    An incorporeal undead resists **nonmagical** weapons specifically — that is
    the 5e rule and it is the whole reason a ghost is a problem: reach it with
    something enchanted. So a magical weapon disarms the
    :data:`NONMAGICAL_WEAPON` half of the profile, while the damage-type
    immunities still apply. A magic sword is not a cold weapon.

    A weapon with no stated magicalness is treated as nonmagical, because that is
    the conservative reading: the world has to say a weapon is enchanted for it
    to be, and defaulting the other way would make every mundane sword useless
    against ghosts without anyone deciding that.
    """
    profile = damage_profile(player)
    if NONMAGICAL_WEAPON not in profile["resist"]:
        return profile
    if weapon_props and _is_magical(weapon_props):
        return {"resist": set(profile["resist"]) - {NONMAGICAL_WEAPON},
                "immune": set(profile["immune"])}
    return profile


def is_nonmagical_weapon(weapon_props: dict) -> bool:
    """True when there *is* a weapon and it is not magical.

    A bare-fisted hit returns False, so the :data:`NONMAGICAL_WEAPON` rule does
    not fire against one: a ghost is hard to hurt with a sword, not with a fist
    going straight through it.
    """
    return bool(weapon_props) and not _is_magical(weapon_props)


def _is_magical(weapon_props: dict) -> bool:
    for key in ("magical", "is_magical", "enchanted", "magic"):
        value = weapon_props.get(key)
        if isinstance(value, bool) and value:
            return True
        if isinstance(value, str) and value.strip().lower() in ("true", "yes", "1"):
            return True
    # a spell id means it was not forged, it was cast
    return bool(str(weapon_props.get("spell_id") or "").strip())


#: In-world line when an attack simply does not land on a ghost. Deliberately
#: flavourful rather than numeric — combat reports wounds, not hit points.
IMMUNE_HIT_LINES = (
    "The blow passes straight through {target} — there is nothing solid there to strike.",
    "{target} is not touched by it at all.",
    "It should have connected. It does not; {target} is not there in the way that matters.",
)

RESIST_HIT_LINES = (
    "It lands, but half of it is lost to {target}.",
    "The blow barely takes hold on {target}.",
)


def hit_line(damage: int, damage_type: str, profile: Optional[dict],
             target_name: str, from_nonmagical_weapon: bool = False,
             rng=None) -> str:
    """The flavour line for a resisted or immune hit, or "" for a normal one."""
    result = apply_damage_resistance(max(0, damage), damage_type, profile,
                                    from_nonmagical_weapon)
    if result["immune"]:
        table = IMMUNE_HIT_LINES
    elif result["resisted"]:
        table = RESIST_HIT_LINES
    else:
        return ""
    if rng is not None:
        return rng.choice(table).format(target=target_name)
    return table[0].format(target=target_name)
