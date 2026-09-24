"""Central dice and check resolution (task-472).

One place that answers: *what do I roll, what modifies it, and how good is the
result.* Before this, `roll_dice` lived in the skill system, `skill_check`
ignored the character's ability scores, saves rolled their own way, and there was
no advantage/disadvantage, no criticals, no degrees of success and no opposed
checks — every call site re-invented a piece.

Contents
--------
* **Dice** — `roll_dice`, `parse_dice`, `roll`, `roll_d20` (advantage and
  disadvantage roll two d20 and keep the high/low one; having both cancels).
* **Modifiers** — `ability_mod` (5e ``(score-10)//2``), `SKILL_ABILITY` (which
  ability each skill key off), `skill_modifiers` / `save_modifiers` collecting
  the ability modifier, the skill/stat value, trait mods and *condition* effects
  in one auditable breakdown.
* **Checks** — `resolve` (one d20, a DC, advantage, degrees, a logged
  breakdown), `opposed` (two resolves compared), and `CheckResult` for callers
  that want the parts rather than a tuple.
* **Bands** — `DCS` and `dc_band`, so DCs stop being magic numbers at call sites.

The legacy `SkillSystem.skill_check` / `saving_throw` are thin adapters over
this module and keep their old tuple + message format.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

# ───────────────────────────── bands ──────────────────────────────────────

#: Named difficulties. Opposed checks use `opposed()` instead of a DC.
DCS = {
    "trivial": 5,
    "very_easy": 5,
    "easy": 10,
    "medium": 15,
    "hard": 20,
    "very_hard": 25,
    "near_impossible": 30,
}

#: Upper bound -> label, matching the historical `skill_check` wording.
_DC_BANDS = ((5, "very easy"), (10, "easy"), (15, "medium"),
             (20, "hard"), (10 ** 9, "very hard"))

#: 5e ability keys, and the order used for display/saves.
STAT_NAMES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")

#: Which ability each skill keys off (D&D 5e). An unknown skill keys off nothing
#: (modifier 0) so homebrew/soak skills keep working.
SKILL_ABILITY = {
    "Acrobatics": "DEX", "Animal Handling": "WIS", "Arcana": "INT",
    "Athletics": "STR", "Deception": "CHA", "History": "INT",
    "Insight": "WIS", "Intimidation": "CHA", "Investigation": "INT",
    "Medicine": "WIS", "Nature": "INT", "Perception": "WIS",
    "Performance": "CHA", "Persuasion": "CHA", "Religion": "INT",
    "Sleight of Hand": "DEX", "Stealth": "DEX", "Survival": "WIS",
}

SKILL_NAMES = tuple(SKILL_ABILITY)


def dc_band(dc: int) -> str:
    """The historical label for a DC (very easy … very hard)."""
    for limit, label in _DC_BANDS:
        if dc <= limit:
            return label
    return "very hard"


def ability_mod(score, default: int = 10) -> int:
    """5e ability modifier: ``(score - 10) // 2``. Never clamped."""
    try:
        return (int(score if score is not None else default) - 10) // 2
    except (TypeError, ValueError):
        return 0


# ───────────────────────────── dice ───────────────────────────────────────

_DICE_RE = re.compile(r"^\s*(?:(\d*)d(\d+))\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)


def roll_dice(num_dice: int = 1, sides: int = 20, modifier: int = 0,
              rng=None) -> int:
    """Sum of *num_dice* d*sides* plus *modifier* — the single dice primitive."""
    rng = rng or random
    return sum(rng.randint(1, sides) for _ in range(int(num_dice))) + int(modifier)


def parse_dice(expr: str):
    """Parse ``"2d6+3"`` / ``"d20"`` / ``"4"`` -> ``(count, sides, modifier)``.

    Bare integers are a flat modifier with no dice (count 0), so ``"4"`` is a
    constant 4 rather than 4d20.
    """
    text = str(expr).strip()
    if re.fullmatch(r"[+-]?\d+", text):
        return (0, 0, int(text))
    match = _DICE_RE.match(text)
    if not match:
        raise ValueError(f"Not a dice expression: {expr!r}")
    count = int(match.group(1) or 1)
    sides = int(match.group(2))
    modifier = int((match.group(3) or "0").replace(" ", ""))
    return (count, sides, modifier)


def roll(expr: str, rng=None) -> int:
    """Roll a dice expression, e.g. ``roll("2d6+3")``."""
    count, sides, modifier = parse_dice(expr)
    if count == 0:
        return modifier
    return roll_dice(count, sides, modifier, rng=rng)


@dataclass
class D20Roll:
    """A d20 result, including what advantage did."""

    faces: list                    # every d20 rolled
    kept: int                      # the face used
    mode: str = "normal"           # normal | advantage | disadvantage


def roll_d20(advantage: bool = False, disadvantage: bool = False,
             roll_fn=None, rng=None) -> D20Roll:
    """One d20, or two for advantage/disadvantage (both cancel each other).

    ``roll_fn`` lets a caller inject the single-die roll (SkillSystem keeps a
    patchable `roll_dice`), and is called once per die.
    """
    one = roll_fn or (lambda: roll_dice(1, 20, 0, rng=rng))
    if advantage and disadvantage:
        advantage = disadvantage = False
    if not (advantage or disadvantage):
        return _as_kept([one()], "normal")
    faces = [one(), one()]
    mode = "advantage" if advantage else "disadvantage"
    kept = max(faces) if advantage else min(faces)
    return D20Roll(faces=faces, kept=kept, mode=mode)


def _as_kept(faces, mode) -> D20Roll:
    return D20Roll(faces=faces, kept=faces[0], mode=mode)


# ───────────────────────── modifiers ──────────────────────────────────────

@dataclass
class Modifier:
    source: str
    value: int

    def to_dict(self) -> dict:
        return {"source": self.source, "value": self.value}


def _condition_definitions():
    try:
        from engine.player_conditions import CONDITION_DEFINITIONS
        return CONDITION_DEFINITIONS or {}
    except Exception:
        return {}


#: Condition lists use descriptive lowercase names ("dexterity", "sight",
#: "willpower", "concentration"); map them onto the check keys we match against.
_ALIASES = {
    "strength": "STR", "dexterity": "DEX", "constitution": "CON",
    "intelligence": "INT", "wisdom": "WIS", "charisma": "CHA",
    "sight": "Perception", "hearing": "Perception", "perception": "Perception",
    "concentration": "WIS", "willpower": "WIS", "self_control": "WIS",
}


def _norm(name) -> str:
    text = str(name).strip()
    return _ALIASES.get(text.lower(), text).lower()


def condition_flags(player, *targets):
    """(advantage, disadvantage, auto_fail) from the character's conditions.

    A condition definition may carry ``check_advantage`` / ``check_disadvantage``
    / ``auto_fail_checks`` lists naming skills, abilities or the literal
    ``"attack"`` / ``"*"``. An instance may override the definition.
    """
    names = {_norm(target) for target in targets if target}
    names.add("*")
    names.add("all")

    advantage = disadvantage = auto_fail = False
    definitions = _condition_definitions()
    for cond_id, instances in (getattr(player, "conditions", {}) or {}).items():
        definition = definitions.get(cond_id, {}) or {}
        for instance in (instances or [{}]):
            for key, flag in (("check_advantage", "adv"),
                              ("check_disadvantage", "dis"),
                              ("auto_fail_checks", "fail")):
                raw = instance.get(key, definition.get(key, [])) or []
                if {_norm(x) for x in raw} & names:
                    if flag == "adv":
                        advantage = True
                    elif flag == "dis":
                        disadvantage = True
                    else:
                        auto_fail = True
    return advantage, disadvantage, auto_fail


def skill_modifiers(player, skill: str):
    """(ability, [Modifier...]) for a skill check.

    The ability comes from `SKILL_ABILITY`; the value is the skill's own number
    plus trait modifiers. Proficiency is not modelled separately — the skill
    value *is* the trained number.
    """
    ability = SKILL_ABILITY.get(skill)
    mods = []
    if ability:
        score = (getattr(player, "stats", None) or {}).get(ability, 10)
        mods.append(Modifier(f"{ability} mod", ability_mod(score)))
    value = int(((getattr(player, "skills", None) or {}).get(skill, 0)) or 0)
    if value:
        mods.append(Modifier(skill, value))
    try:
        from engine.traits import TraitSystem
        trait_mods = TraitSystem.get_skill_check_mods(player) or {}
        bonus = int(trait_mods.get(skill, 0)) + int(trait_mods.get("*", 0))
        if bonus:
            mods.append(Modifier("traits", bonus))
    except Exception:
        pass
    # Role profile (task-476): a `role:` tag biases the checks the role is good
    # at. Merged here so it is the same pipeline as ability/value/traits and so
    # skill_check, resolve and opposed all see it; a roleless character adds
    # nothing (engine/roles.py).
    try:
        from engine import roles as roles_mod
        role_bonus = int((roles_mod.skill_mods(player) or {}).get(skill, 0))
        if role_bonus:
            mods.append(Modifier("role", role_bonus))
    except Exception:
        pass
    # Proficiency (task-480): an optional term kept separate from the trained
    # skill value, so the sheet expresses both. Default 0 — exactly the
    # pre-task-480 result (task-472 deliberately left it out).
    try:
        from engine import skill_progress as progress_mod
        prof = int(progress_mod.proficiency_bonus(player))
        if prof:
            mods.append(Modifier("proficiency", prof))
    except Exception:
        pass
    return ability, mods


def save_modifiers(player, stat: str):
    """(mods, ability) for a save: ability mod (or skill value) + trait bonuses."""
    mods = []
    ability = stat if stat in STAT_NAMES else None
    if ability:
        score = (getattr(player, "stats", None) or {}).get(ability, 10)
        mods.append(Modifier(f"{ability} mod", ability_mod(score)))
    else:
        value = int(((getattr(player, "skills", None) or {}).get(stat, 0)) or 0)
        if value:
            mods.append(Modifier(stat, value))
    try:
        from engine.traits import TraitSystem
        flat, per_stat = TraitSystem.get_save_bonus(player)
        if flat:
            mods.append(Modifier("traits", int(flat)))
        if int((per_stat or {}).get(stat, 0)):
            mods.append(Modifier(f"traits ({stat})", int(per_stat[stat])))
    except Exception:
        pass
    return mods, ability


# ───────────────────────────── checks ─────────────────────────────────────

@dataclass
class CheckResult:
    actor: str
    kind: str
    dc: object
    faces: list = field(default_factory=list)
    kept: int = 0
    mode: str = "normal"
    modifiers: list = field(default_factory=list)
    total: int = 0
    success: bool = False
    margin: int = 0
    tier: str = "fail"
    auto_fail: bool = False
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "actor": self.actor, "kind": self.kind, "dc": self.dc,
            "faces": self.faces, "kept": self.kept, "mode": self.mode,
            "modifiers": [m.to_dict() for m in self.modifiers],
            "total": self.total, "success": self.success,
            "margin": self.margin, "tier": self.tier,
            "auto_fail": self.auto_fail, "message": self.message,
        }


def _degree(kept: int, total: int, dc) -> str:
    if kept == 1:
        return "crit_fail"
    if kept == 20:
        return "crit_success"
    if dc is None:
        return "success" if total >= 0 else "fail"
    if total < dc:
        return "fail"
    return "strong_success" if (total - dc) >= 5 else "success"


def resolve(player, *, kind: str, dc=None, advantage: bool = False,
            disadvantage: bool = False, extra_mods=(), roll_fn=None,
            logger=None, context: str = "") -> CheckResult:
    """Resolve one d20 check for *player*.

    ``kind`` is a skill name, an ability (``"DEX"``), or any label a condition
    can gate (``"attack"``). Advantage/disadvantage come from the caller and from
    the character's conditions; both together cancel. Non-none ``dc`` decides
    success; ``dc=None`` is an opposed-style roll the caller compares.
    """
    skill = kind if kind in SKILL_ABILITY else None
    ability = kind if kind in STAT_NAMES else None
    if skill is not None:
        derived_ability, mods = skill_modifiers(player, skill)
        ability = derived_ability
    elif ability is not None:
        mods, _ = save_modifiers(player, ability)
    else:
        mods, _ = [], None

    for extra in extra_mods or ():
        if isinstance(extra, Modifier):
            mods.append(extra)
        else:
            source, value = extra
            mods.append(Modifier(str(source), int(value)))

    cond_adv, cond_dis, auto_fail = condition_flags(player, skill, ability, kind)
    advantage = bool(advantage or cond_adv)
    disadvantage = bool(disadvantage or cond_dis)

    rolled = roll_d20(advantage=advantage, disadvantage=disadvantage,
                      roll_fn=roll_fn)
    bonus = sum(m.value for m in mods)
    total = rolled.kept + bonus
    success = (not auto_fail) and (dc is None or total >= dc)
    tier = "auto_fail" if auto_fail else _degree(rolled.kept, total, dc)

    label = skill or ability or kind
    band = f" ({dc_band(dc)})" if dc is not None else ""
    detail = " + ".join(str(m.value) for m in mods) or "0"
    mode = "" if rolled.mode == "normal" else f" [{rolled.mode}]"
    message = (
        f"[Check] {label} vs DC {dc}{band}{mode}: "
        f"roll={rolled.kept} + {detail} = {total} => {tier}"
    )
    if auto_fail:
        message = f"[Check] {label} vs DC {dc}{band}: AUTO-FAIL (a condition prevents it)"
    if context:
        message = f"{message} ({context})"

    result = CheckResult(
        actor=getattr(player, "name", ""), kind=label, dc=dc,
        faces=rolled.faces, kept=rolled.kept, mode=rolled.mode,
        modifiers=mods, total=total, success=success,
        margin=(total - dc) if dc is not None else 0, tier=tier,
        auto_fail=auto_fail, message=message,
    )
    if logger is not None:
        try:
            logger.add_log_entry(message)
        except Exception:
            pass
    return result


def opposed(player, defender, *, kind: str, defender_kind: str = None,
            roll_fn=None, defender_roll_fn=None) -> tuple:
    """Compare two checks; ties go to the defender.

    Returns ``(attacker_result, defender_result, attacker_wins)`` — the shape
    theft-vs-Perception and social-vs-Insight need (task-468).
    """
    a = resolve(player, kind=kind, roll_fn=roll_fn)
    d = resolve(defender, kind=defender_kind or kind, roll_fn=defender_roll_fn)
    winner = a.total > d.total
    a.success = winner
    d.success = not winner
    a.tier = "success" if winner else "fail"
    d.tier = "fail" if winner else "success"
    return a, d, winner
