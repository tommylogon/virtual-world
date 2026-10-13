"""The disposition score registry: one declaration of every decision score (task-800).

A character decides by scoring candidates on a small, named set of quantities and
then picking one. Traits, needs, emotion, memories, relationships, obligations and
GIMP's goal all write into the *same* score set - it is the shared currency of the
disposition, the layer above MOSIAC that ranks what MOSIAC puts on the table.

The problem this module fixes: the 100-trait / 200-modifier catalogue (see
`docs/virtualWorld/design/Character Pursuits.md`) named its targets -
``choice.utility.forceful_action``, ``attention.salience.threat``,
``choice.risk_penalty_multiplier``, ``choice.abandon_threshold`` - and **none of
those names existed in the code**. Worse, they are not one kind: one is a summed
utility, one a multiplier, one a threshold, one a salience weight. ``add_delta``
means something different for each, and "clamp the aggregate to its declared range"
is undefined until every score declares a **(kind, base, range)**.

So this file is the single declaration, in the manner of ``tools/way_properties.py``:
the kind vocabulary, the score set, and the combine/pick each decision uses. The
gate ``tools/disposition_index.py --check`` fails when a score's declared base
drifts from the engine constant that actually reads it, when a decision names a
score that is not declared, and when a personality/modifier file references an
undeclared score - the same "drift is not hypothetical" job way_properties does.

Seeded from the task-799 spike, which proved three deliberately-unlike decisions
fit one registry: **relieve** (additive utility, argmin), the **social pass**
(multiplicative weights, seeded weighted draw) and **hunt** (threshold, then a
utility). The union of their kinds is the whole set, and one *pick* is not enough -
hence ``COMBINES`` / ``PICKS`` here and the pick *implementation* in task-804.
Task-801 adds the fourth, **survive** - the soak's per-turn need decision - and the
action-side feature table (``ACTION_FEATURES``) that gives the trait weights
something to multiply.

This module **declares**; it does not resolve. The pick modes (task-804), the
action-side features (task-801), the character-side weights (task-802) and the
value gates (task-803) read from here.

@module disposition
@contributes SCORE_KINDS, SCORES, DECISIONS, ACTION_FEATURES, TARGET_FEATURES, TRAIT_MODIFIERS, VALUE_GATES, by_name, validate_score, scores_for, features_of, trait_weights, character_weights, gated_verbs, filter_actions, resolve, whispers, check_registry
@docs docs/virtualWorld/design/Character Pursuits.md
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

#: The kinds a decision score can be. Every contributor (a trait, a need, a
#: memory, an emotion, an obligation, a goal) writes into a score of a declared
#: kind, and the kind - not a shared scalar meaning - decides how the number is
#: read. That is why one registry can hold a summed utility, a probability-like
#: weight and a hard drive at once.
SCORE_KINDS = (
    "utility",     # a term in a summed total; combined additively
    "weight",      # a base weight in a draw; modifiers multiply it
    "multiplier",  # scales an existing weight or score
    "gate",        # a hard exclusion; a falsy value removes the candidate
    "threshold",   # a drive that must be crossed before the decision is on the table
    "salience",    # how loudly a channel presents itself for attention
)

#: How a decision folds its scores into one number.
COMBINES = ("add", "multiply", "threshold")

#: How a decision turns its combined score(s) into a single pick. The *implementation*
#: of these modes is task-804; here they are declared so a decision can name its own.
PICKS = ("argmin", "argmax", "weighted-draw", "threshold-then-utility")

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")


@dataclass(frozen=True)
class Score:
    """One named decision score.

    ``base`` is the value an unauthored character or candidate carries before any
    contributor fires, and ``lo``/``hi`` are the clamp the aggregate is held to -
    the two things ``add_delta`` was meaningless without.
    """

    name: str
    kind: str
    base: float
    lo: float
    hi: float
    notes: str = ""
    #: Set when the declaration is ahead of, or behind, the engine - a score that
    #: nothing reads yet, or a name the engine carries that is not honoured here.
    caveat: str = ""


@dataclass(frozen=True)
class Decision:
    """A decision that reads scores, and how it combines and picks them."""

    name: str
    combine: str
    pick: str
    scores: Tuple[str, ...]
    notes: str = ""


# ── where to relieve: the privacy utility (engine/relief.py) ───────────────────
# Additive utility, argmin (lower is better). Per-actor weights so task-549 can
# vary them by species or faction without touching the scoring function.
_SCORES_RELIEVE: Tuple[Score, ...] = (
    Score("relief.witnesses", "utility", 0.0, 0.0, 100.0,
          notes="other living characters in the area; the term that caused the hub"),
    Score("relief.private_bonus", "utility", 0.0, 0.0, 1.0,
          notes="1.0 when the area is authored secluded (is_private)"),
    Score("relief.fixture_bonus", "utility", 0.0, 0.0, 1.0,
          notes="1.0 when the area is, or holds, a relief fixture"),
    Score("relief.weight.witness", "weight", 1.0, 0.0, 10.0,
          notes="per-actor weight on relief.witnesses"),
    Score("relief.weight.private", "weight", 1.5, 0.0, 10.0,
          notes="per-actor weight on relief.private_bonus; > 1 so a secluded room "
                "beats one onlooker but not an unbounded walk"),
    Score("relief.weight.fixture", "weight", 1.0, 0.0, 10.0,
          notes="per-actor weight on relief.fixture_bonus"),
    Score("relief.weight.public", "weight", 3.0, 0.0, 10.0,
          notes="declared in engine/relief.py PRIVACY_WEIGHTS",
          caveat="unread: score_privacy sums witness/private/fixture only; the "
                 "public case is handled by is_private() via PUBLIC_TAGS. Either "
                 "wire this weight or retire it."),
)

# ── the social pass: a weighted draw over gated actions (engine/background_social.py) ──
# Multiplicative modifiers on a base weight; seeded weighted draw (never argmax).
_SOCIAL_ACTIONS = ("chat", "joke", "compliment", "tease", "confide", "flirt",
                   "apologise", "bully")
_SOCIAL_BASE = {
    "chat": 10.0, "joke": 6.0, "compliment": 5.0, "tease": 6.0,
    "confide": 3.0, "flirt": 2.0, "apologise": 2.0, "bully": 2.0,
    "ignore": 4.0,
}
_SCORES_SOCIAL: Tuple[Score, ...] = tuple(
    Score(f"social.weight.{action}", "weight", _SOCIAL_BASE[action], 0.0, 100.0,
          notes=("weight of declining to engage; introverts/loners raise it"
                 if action == "ignore" else f"base weight of the `{action}` action"))
    for action in (*_SOCIAL_ACTIONS, "ignore")
) + (
    Score("social.multiplier.affect", "multiplier", 1.0, 1.0, 1.6,
          notes="a felt emotion tilts an action it expresses; capped at AFFECT_TILT"),
    Score("social.multiplier.trait", "multiplier", 1.0, 0.0, 10.0,
          notes="a trait scales a weight (e.g. social_gain, loner)"),
    Score("social.gate.band", "gate", 1.0, 0.0, 1.0,
          notes="0 drops an action unavailable at this relationship band"),
)

# ── the wolf deciding to hunt (proposed; task-799 seed, no consumer yet) ───────
_SCORES_HUNT: Tuple[Score, ...] = (
    Score("hunt.threshold.hunger", "threshold", 70.0, 0.0, 100.0,
          notes="hunger must cross this before a hunt is on the table",
          caveat="proposed (task-799 seed); no engine consumer yet"),
    Score("hunt.utility.prey_value", "utility", 0.0, 0.0, 100.0,
          notes="expected value of the prey: size and proximity against effort",
          caveat="proposed (task-799 seed); no engine consumer yet"),
    Score("hunt.utility.risk", "utility", 0.0, 0.0, 100.0,
          notes="chance of failure / injury, subtracted from prey value",
          caveat="proposed (task-799 seed); no engine consumer yet"),
    Score("hunt.gate.fitness", "gate", 1.0, 0.0, 1.0,
          notes="0 when injured or the prey would win",
          caveat="proposed (task-799 seed); no engine consumer yet"),
    Score("hunt.salience.pack_kill", "salience", 0.0, 0.0, 100.0,
          notes="a pack-mate's kill raises the decision's profile",
          caveat="proposed (task-799 seed); no engine consumer yet"),
)

# ── survival: which need to answer (engine/background_simulation.py) ───────────
# The soak's per-turn decision. A need must cross its threshold before it is on
# the table, then the action expected to relieve the most is preferred. The
# thresholds are the real constants the runner reads, cross-checked by the gate.
# `energy`/`hygiene`/`entertainment`/`sanity`/`social` are depleting meters, so
# their threshold is a *floor* (act when below), not a ceiling.
_SCORES_SURVIVE: Tuple[Score, ...] = (
    Score("survive.threshold.thirst", "threshold", 45.0, 0.0, 100.0,
          notes="Thirst at/above this is pressing (background_simulation.THIRST_THRESHOLD)"),
    Score("survive.threshold.hunger", "threshold", 50.0, 0.0, 100.0,
          notes="Hunger at/above this is pressing (HUNGER_THRESHOLD)"),
    Score("survive.threshold.bladder", "threshold", 60.0, 0.0, 100.0,
          notes="Bladder at/above this is pressing (BLADDER_THRESHOLD)"),
    Score("survive.threshold.energy", "threshold", 30.0, 0.0, 100.0,
          notes="Energy at/below this is pressing - a floor, not a ceiling (ENERGY_THRESHOLD)"),
    Score("survive.threshold.hygiene", "threshold", 40.0, 0.0, 100.0,
          notes="Hygiene at/below this is pressing (HYGIENE_THRESHOLD)"),
    Score("survive.threshold.entertainment", "threshold", 40.0, 0.0, 100.0,
          notes="Entertainment at/below this is pressing (ENTERTAINMENT_THRESHOLD)"),
    Score("survive.threshold.sanity", "threshold", 40.0, 0.0, 100.0,
          notes="Sanity at/below this is pressing (SANITY_THRESHOLD)"),
    Score("survive.threshold.social", "threshold", 50.0, 0.0, 100.0,
          notes="Social at/below this seeks company (SOCIAL_THRESHOLD)"),
    Score("survive.utility.need_relief", "utility", 0.0, 0.0, 100.0,
          notes="expected reduction of the pressing need; the amount is a live "
                "read (task-802), not a constant"),
    Score("survive.gate.available", "gate", 1.0, 0.0, 1.0,
          notes="0 when nothing reachable here can satisfy the need"),
    Score("attention.salience.remembered", "salience", 0.0, 0.0, 100.0,
          notes="a memory naming the target, or a pressing need, raises the "
                "decision's profile (task-802 live modifier)"),
)

#: Every decision score, once.
SCORES: Tuple[Score, ...] = (
    _SCORES_RELIEVE + _SCORES_SOCIAL + _SCORES_HUNT + _SCORES_SURVIVE
)

#: The decisions, and how each combines and picks. The three are the task-799
#: spike, kept as the worked examples the vocabulary is proved against.
DECISIONS: Tuple[Decision, ...] = (
    Decision("relieve", "add", "argmin",
             tuple(s.name for s in _SCORES_RELIEVE),
             notes="engine/relief.score_privacy; lower total is better"),
    Decision("social", "multiply", "weighted-draw",
             tuple(s.name for s in _SCORES_SOCIAL),
             notes="engine/background_social; seeded draw, never argmax"),
    Decision("hunt", "threshold", "threshold-then-utility",
             tuple(s.name for s in _SCORES_HUNT),
             notes="proposed (task-799 seed)"),
    Decision("survive", "threshold", "threshold-then-utility",
             tuple(s.name for s in _SCORES_SURVIVE),
             notes="engine/background_simulation; act on the most pressing need"),
)


# ── the action side: what a verb contributes (task-801) ────────────────────────
# `score(action) = weights . features`. Without this table the trait weights
# (task-802) multiply nothing. A value of 1.0 means "this verb exercises the
# channel"; how much a channel counts is a live read (task-802), so it is not a
# constant here. Grounded in the real vocabularies the engine already uses:
# engine/relief.py RELIEF_TAGS / PRIVATE_TAGS, engine/background_simulation.py
# FOOD_TAGS / DRINK_TAGS.
_SOCIAL_VERBS = ("chat", "joke", "compliment", "tease", "confide", "flirt",
                 "apologise", "bully")

#: verb -> {declared score: contribution}. Every soak candidate verb appears.
ACTION_FEATURES: Dict[str, Dict[str, float]] = {
    # need-satisfying actions: they address whatever is pressing
    "drink": {"survive.utility.need_relief": 1.0},
    "eat": {"survive.utility.need_relief": 1.0},
    "sleep": {"survive.utility.need_relief": 1.0},
    "rest": {"survive.utility.need_relief": 1.0},
    "relieve": {"survive.utility.need_relief": 1.0},
    "bathe": {"survive.utility.need_relief": 1.0},
    "bath": {"survive.utility.need_relief": 1.0},
    # moving toward a need's source is prospective relief, cheaper than starving
    "go": {"survive.utility.need_relief": 1.0},
    "approach": {"survive.utility.need_relief": 1.0},
}
for _verb in _SOCIAL_VERBS:
    # the verb IS the candidate whose weight is the score (social.weight.<verb>)
    ACTION_FEATURES[_verb] = {f"social.weight.{_verb}": 1.0}

#: target tag -> the declared score the target contributes by carrying it.
TARGET_FEATURES: Dict[str, str] = {
    "food": "survive.utility.need_relief",
    "edible": "survive.utility.need_relief",
    "eat": "survive.utility.need_relief",
    "meal": "survive.utility.need_relief",
    "drink": "survive.utility.need_relief",
    "water": "survive.utility.need_relief",
    "beverage": "survive.utility.need_relief",
    "bed": "survive.utility.need_relief",
    "sleep": "survive.utility.need_relief",
    "latrine": "relief.fixture_bonus",
    "toilet": "relief.fixture_bonus",
    "privy": "relief.fixture_bonus",
    "restroom": "relief.fixture_bonus",
    "bathroom": "relief.fixture_bonus",
    "private": "relief.private_bonus",
    "secluded": "relief.private_bonus",
    "isolated": "relief.private_bonus",
}

#: The verbs the background/soak tier chooses between per turn. Every one must
#: contribute to at least one declared score, or the feature table has a hole.
SOAK_VERBS: Tuple[str, ...] = (
    "drink", "eat", "sleep", "rest", "relieve", "bathe", "go", "approach",
) + _SOCIAL_VERBS


def features_of(verb: str, target_tags=()) -> Dict[str, float]:
    """The declared scores *verb*, and the target's tags, contribute to.

    The action-side half of ``score(action) = weights . features``. Amounts are
    1.0: the verb declares *which channel* it exercises; how much a channel counts
    is a live read from state (task-802).
    """
    out: Dict[str, float] = dict(
        ACTION_FEATURES.get((verb or "").strip().lower(), {}))
    for tag in target_tags or ():
        name = TARGET_FEATURES.get(str(tag).strip().lower())
        if name:
            out[name] = out.get(name, 0.0) + 1.0
    return out


def check_features() -> List[str]:
    """Feature-table problems: an undeclared score, or an uncovered soak verb."""
    problems: List[str] = []
    declared = {s.name for s in SCORES}
    for verb, features in ACTION_FEATURES.items():
        for name in features:
            if name not in declared:
                problems.append(
                    f"ACTION_FEATURES[{verb!r}] names undeclared score `{name}`")
    for tag, name in TARGET_FEATURES.items():
        if name not in declared:
            problems.append(
                f"TARGET_FEATURES[{tag!r}] names undeclared score `{name}`")
    for verb in SOAK_VERBS:
        if not features_of(verb):
            problems.append(f"soak verb `{verb}` contributes to no declared score")
    return problems


# ── the character side: traits and live state (task-802) ───────────────────────
# `weights` in `score(action) = weights . features`. A character's weights come
# from its traits - authored once - plus modifiers read from live state (emotion,
# needs, relationships, recent memories), which is how fear, hunger, loyalty and
# trauma reach the score without a special system.
#
# COEFFICIENTS ARE UNVERIFIED STARTING POINTS. They are small and directional;
# none is empirically calibrated, and the traits named are real ids from
# `data/library/traits/`. Treat them as the shape of the table, not its final
# numbers.
DIAL_NEUTRAL = 0.5


@dataclass(frozen=True)
class TraitModifier:
    """A trait's contribution to one score: ``(dial - 0.5) * coefficient``."""

    trait: str
    score: str
    coefficient: float
    notes: str = ""


#: trait -> score dials. Boolean-present traits read as dial 1.0, absent as 0.5
#: (neutral), so an unauthored character scores exactly average and does not move.
TRAIT_MODIFIERS: Tuple[TraitModifier, ...] = (
    TraitModifier("cowardly", "relief.weight.witness", 2.0,
                  "a coward minds onlookers more"),
    TraitModifier("prudish", "relief.weight.private", 2.0,
                  "values seclusion more"),
    TraitModifier("exhibitionist", "relief.weight.private", -2.0,
                  "values seclusion less"),
    TraitModifier("hostile", "social.weight.bully", 3.0,
                  "the same direction engine/background_social already scales (bully * 2.5)"),
    TraitModifier("patient", "social.weight.bully", -2.0,
                  "a patient character does not reach for a fight"),
    TraitModifier("impatient", "social.weight.tease", 1.6,
                  "matches background_social's tease branch"),
    TraitModifier("loner", "social.weight.ignore", 2.0,
                  "introverts raise the ignore weight (task-423)"),
    TraitModifier("extrovert", "social.weight.ignore", -1.0),
    TraitModifier("chatty", "social.weight.chat", 2.0),
    TraitModifier("glutton", "survive.utility.need_relief", 1.0,
                  "food answers a bigger need for a glutton"),
    TraitModifier("cleanfreak", "survive.utility.need_relief", 1.0,
                  "hygiene answers a bigger need"),
    TraitModifier("small_bladder", "survive.threshold.bladder", -0.4,
                  "a smaller bladder lowers the bladder threshold (acts sooner)"),
    TraitModifier("big_bladder", "survive.threshold.bladder", 0.4),
)

#: Emotion dimension -> the social weight a felt axis tilts, by normalized
#: strength (0..1). Dimensions only - `afraid` is a dimension, `terrified` a
#: label (engine/background_social.py). More than one axis may fire.
EMOTION_TILTS: Dict[str, str] = {
    "angry": "social.weight.bully",
    "afraid": "social.weight.confide",
    "sad": "social.weight.confide",
    "lonely": "social.weight.confide",
    "excited": "social.weight.joke",
    "grateful": "social.weight.compliment",
    "affectionate": "social.weight.flirt",
    "guilty": "social.weight.apologise",
}

#: Vital -> the survive threshold score it is compared against (declared above).
NEED_THRESHOLDS: Dict[str, str] = {
    "Thirst": "survive.threshold.thirst",
    "Hunger": "survive.threshold.hunger",
    "Bladder": "survive.threshold.bladder",
    "Energy": "survive.threshold.energy",
    "Hygiene": "survive.threshold.hygiene",
    "Entertainment": "survive.threshold.entertainment",
    "Sanity": "survive.threshold.sanity",
    "Social": "survive.threshold.social",
}

#: Drives fill toward 100 (act above the threshold); the rest deplete (act below).
_DRIVE_VITALS = frozenset({"Thirst", "Hunger", "Bladder"})


def _dial(player, trait: str) -> float:
    """The trait's dial value in [0,1], defaulting neutral (0.5).

    Delegates to `engine.traits.TraitSystem.dial_value` (task-806), which reads
    `Player.personality_dials` first - the key distinct from the prose personality
    string - then a truthy capability in `Player.traits`. Absent reads 0.5, so an
    unauthored character does not move.
    """
    from engine.traits import TraitSystem
    return TraitSystem.dial_value(player, trait)


def trait_weights(player) -> Dict[str, float]:
    """Additive score deltas derived from the character's traits alone."""
    out: Dict[str, float] = {}
    for mod in TRAIT_MODIFIERS:
        delta = (_dial(player, mod.trait) - DIAL_NEUTRAL) * mod.coefficient
        if delta:
            out[mod.score] = out.get(mod.score, 0.0) + delta
    return out


def emotion_weights(player) -> Dict[str, float]:
    """Score deltas from the character's raised affect axes (task-652's model)."""
    try:
        from engine.emotion import raised_axes
        axes = raised_axes(getattr(player, "emotions_map", lambda: {})())
    except Exception:  # noqa: BLE001
        return {}
    if not axes:
        return {}
    strongest = max(axes.values()) or 1.0
    out: Dict[str, float] = {}
    for axis, amount in axes.items():
        score = EMOTION_TILTS.get(str(axis).lower())
        if not score:
            continue
        strength = min(1.0, float(amount) / strongest)
        out[score] = out.get(score, 0.0) + strength
    return out


def need_weights(player) -> Dict[str, float]:
    """The most-pressing need, supplied as expected relief; plus its salience.

    An unauthored or satisfied character contributes nothing (0.0 overshoot), so
    this only fires when a need is genuinely past its threshold.
    """
    vitals = getattr(player, "vitals", None) or {}
    index = by_name()
    worst = 0.0
    for vital, score_name in NEED_THRESHOLDS.items():
        value = vitals.get(vital)
        if value is None:
            continue
        threshold = index[score_name].base
        # drives fill toward 100 (overshoot above); meters deplete (overshoot below)
        overshoot = (float(value) - threshold) if vital in _DRIVE_VITALS \
            else (threshold - float(value))
        worst = max(worst, overshoot)
    if worst <= 0:
        return {}
    relief = min(100.0, worst)
    return {
        "survive.utility.need_relief": relief,
        "attention.salience.remembered": 1.0,
    }


def relationship_weights(player, other: str) -> Dict[str, float]:
    """Closeness unlocks the warm actions; a stranger contributes nothing."""
    if not other:
        return {}
    try:
        from engine.relationships import get_relationship
        rel = get_relationship(player, other) or {}
        closeness = float(rel.get("closeness", 0) or 0)
    except Exception:  # noqa: BLE001
        return {}
    out: Dict[str, float] = {}
    if closeness >= 25:
        out["social.weight.confide"] = out.get("social.weight.confide", 0.0) + 1.0
    if closeness >= 50:
        out["social.weight.flirt"] = out.get("social.weight.flirt", 0.0) + 1.0
    return out


def memory_weights(player, other: str = "") -> Dict[str, float]:
    """A memory naming the target raises the decision's salience.

    The memory is only a *prompt to attention*, never a world write - a character
    who remembers someone weighs the choice to engage them more heavily.
    """
    if not other:
        return {}
    needle = str(other).lower()
    for memory in getattr(player, "memories", None) or []:
        text = str((memory or {}).get("text", "")).lower()
        if needle and needle in text:
            return {"attention.salience.remembered": 1.0}
    return {}


def live_weights(player, *, other: str = "") -> Dict[str, float]:
    """Emotion + needs + relationships + memories, merged into one delta map."""
    out: Dict[str, float] = {}
    for source in (emotion_weights(player), need_weights(player),
                   relationship_weights(player, other), memory_weights(player, other)):
        for score, delta in source.items():
            out[score] = out.get(score, 0.0) + delta
    return out


def character_weights(player, *, other: str = "") -> Dict[str, float]:
    """The full character-side weight map: traits plus live modifiers."""
    out = trait_weights(player)
    for score, delta in live_weights(player, other=other).items():
        out[score] = out.get(score, 0.0) + delta
    return out


def check_character() -> List[str]:
    """Undeclared scores referenced by the trait / emotion / need tables."""
    problems: List[str] = []
    declared = {s.name for s in SCORES}
    for mod in TRAIT_MODIFIERS:
        if mod.score not in declared:
            problems.append(
                f"TRAIT_MODIFIERS[{mod.trait!r}] names undeclared score `{mod.score}`")
    for axis, score in EMOTION_TILTS.items():
        if score not in declared:
            problems.append(
                f"EMOTION_TILTS[{axis!r}] names undeclared score `{score}`")
    for vital, score in NEED_THRESHOLDS.items():
        if score not in declared:
            problems.append(
                f"NEED_THRESHOLDS[{vital!r}] names undeclared score `{score}`")
    return problems


# ── value gates: traits and morality as hard exclusions (task-803) ─────────────
# A weight says "rather not"; a gate says "cannot". Personality must never make an
# impossible action *possible*, and morality is an exclusion, not a preference - so
# a gate only ever REMOVES a candidate, and it is applied after the capability gates
# (budget, prerequisites, location), never as a score delta.
@dataclass(frozen=True)
class ValueGate:
    """A trait id or authored moral flag -> the verb classes it excludes."""

    flag: str
    verbs: Tuple[str, ...]
    notes: str = ""


#: The gate table. Flags are read from the character's `traits` and `morals`. The
#: moral flags (`honest` / `nonviolent` / `loyal`) are authored character data, not
#: capability traits; `prudish` is a real library trait, so that gate can fire today.
VALUE_GATES: Tuple[ValueGate, ...] = (
    ValueGate("honest", ("steal", "pickpocket"), "cannot take what is not yours"),
    ValueGate("nonviolent", ("attack", "kill", "bully"), "will not harm another"),
    ValueGate("loyal", ("betray",), "will not betray an ally"),
    ValueGate("prudish", ("flirt",), "will not flirt (a real library trait)"),
)


def _flags(player) -> set:
    """The truthy trait ids and moral flags a character carries."""
    flags: set = set()
    for source in (getattr(player, "traits", None), getattr(player, "morals", None)):
        if isinstance(source, dict):
            flags |= {str(k).lower() for k, v in source.items() if v}
    return flags


def gated_verbs(player) -> set:
    """Every verb the character's values exclude, whatever else is true."""
    flags = _flags(player)
    out: set = set()
    for gate in VALUE_GATES:
        if gate.flag in flags:
            out |= {v.lower() for v in gate.verbs}
    return out


def is_gated(player, verb: str) -> bool:
    """True when the character's values exclude *verb*."""
    return (verb or "").strip().lower() in gated_verbs(player)


def filter_actions(player, verbs) -> List[str]:
    """*verbs* with every value-gated option removed.

    Subtracts only. It can never add a verb, so a gate cannot enable an action the
    capability gate denied - the invariant the acceptance names.
    """
    gated = gated_verbs(player)
    return [v for v in verbs if str(v).strip().lower() not in gated]


def check_gates() -> List[str]:
    """A flag with no verbs is a dead entry; a verb in two flags is a note."""
    problems: List[str] = []
    for gate in VALUE_GATES:
        if not gate.verbs:
            problems.append(f"VALUE_GATES[{gate.flag!r}] excludes nothing")
    return problems


# ── the resolver: scores -> one pick (task-804) ───────────────────────────────
# One pick rule is not enough (task-799): the three decisions resolve three ways.
# This is the family. It is deterministic given the candidates, the weights and a
# seed, and ties break on the candidate key - so a replay picks the same action.
@dataclass(frozen=True)
class Outcome:
    """A pick: the winning key, its combined score, and why (top contributors)."""

    decision: str
    key: str
    score: float
    mode: str
    #: (score_name, value) for the winner, largest magnitude first - the debugging
    #: read the acceptance asks for ("fled because cowardly = safety +2").
    contributions: Tuple[Tuple[str, float], ...]


def score_candidate(decision_name: str, features, weights=None) -> Dict[str, float]:
    """One candidate's value per score: declared base + weight + feature.

    *features* is the action-side contribution (task-801: ``ACTION_FEATURES`` /
    ``TARGET_FEATURES``); *weights* the character-side delta (task-802:
    ``character_weights``). Both default to zero, so a bare candidate reads each
    score at its declared base.
    """
    weights = weights or {}
    out: Dict[str, float] = {}
    for score in scores_for(decision_name):
        out[score.name] = (
            score.base
            + float(weights.get(score.name, 0.0))
            + float(features.get(score.name, 0.0))
        )
    return out


def _combine(decision: Decision, per_score: Dict[str, float]) -> float:
    """Fold a candidate's per-score values into one number, per the decision."""
    if decision.combine == "multiply":
        total = 1.0
        for value in per_score.values():
            total *= max(0.0, value)   # a gate at 0.0 zeroes the whole candidate
        return total
    return sum(per_score.values())


def _thresholds_met(decision: Decision, per_score: Dict[str, float]) -> bool:
    """True when every threshold score reached its declared base."""
    index = by_name()
    for name in decision.scores:
        score = index[name]
        if score.kind == "threshold" and per_score[name] < score.base:
            return False
    return True


def _contributions(per_score: Dict[str, float], limit: int = 5):
    return tuple(sorted(per_score.items(),
                        key=lambda kv: (-abs(kv[1]), kv[0]))[:limit])


def resolve(decision_name: str, candidates, *, weights=None, seed=None) -> Outcome:
    """Turn ``(key, features)`` candidates into one pick.

    *candidates* is an iterable of ``(key, features)``. The combine and pick come
    from the decision's declaration, so the same code serves a deterministic argmin
    (relieve), a seeded weighted draw (the social pass) and a threshold-then-utility
    (hunt / survive). Raises ``KeyError`` on an unknown decision, ``ValueError`` on
    an empty candidate set or an unknown pick.
    """
    decision = next((d for d in DECISIONS if d.name == decision_name), None)
    if decision is None:
        raise KeyError(f"unknown decision: {decision_name}")

    entries = []
    for key, features in candidates:
        per_score = score_candidate(decision_name, features or {}, weights)
        entries.append((str(key), _combine(decision, per_score), per_score))
    if not entries:
        raise ValueError(f"{decision_name}: no candidates")
    # Sorted by key first, so max/min/choices all see a deterministic order and a
    # tie resolves to the same candidate on every run.
    entries.sort(key=lambda e: e[0])

    if decision.pick == "argmin":
        winner = min(entries, key=lambda e: e[1])
    elif decision.pick == "argmax":
        winner = max(entries, key=lambda e: e[1])
    elif decision.pick == "weighted-draw":
        rng = random.Random(seed)
        draw = [max(0.0, e[1]) for e in entries]
        winner = entries[0] if sum(draw) <= 0 else rng.choices(entries, weights=draw, k=1)[0]
    elif decision.pick == "threshold-then-utility":
        eligible = [e for e in entries if _thresholds_met(decision, e[2])] or entries
        winner = max(eligible, key=lambda e: e[1])
    else:
        raise ValueError(f"{decision_name}: unknown pick `{decision.pick}`")

    return Outcome(decision_name, winner[0], winner[1], decision.pick,
                   _contributions(winner[2]))


# ── whispers: the same weights as prose for the LLM (task-805) ─────────────────
# The soak reads the numbers; the LLM reads these lines. Both come from the same
# authored traits, so the two tiers share one vocabulary instead of two.
WHISPERS: Dict[str, str] = {
    "cowardly": "You mind having an audience; being watched makes you uneasy.",
    "prudish": "You keep your distance from flirtation.",
    "exhibitionist": "Being seen thrills you - you show yourself more freely than most.",
    "hostile": "You are quick to confront and slow to back down.",
    "patient": "You can wait; you rarely reach for a fight.",
    "impatient": "You act before you think.",
    "loner": "You would rather keep to yourself.",
    "extrovert": "You seek out company.",
    "chatty": "You like to talk.",
    "glutton": "Food looms large for you.",
    "cleanfreak": "You dislike being grimy.",
    "small_bladder": "You need to relieve yourself sooner than most.",
    "big_bladder": "You can hold it longer than most.",
}

_NEED_WHISPERS: Dict[str, str] = {
    "Thirst": "You are thirsty.",
    "Hunger": "You are hungry.",
    "Bladder": "You need to relieve yourself.",
    "Energy": "You are tired.",
    "Hygiene": "You feel grimy.",
    "Entertainment": "You are bored.",
    "Sanity": "You feel frayed.",
    "Social": "You feel lonely.",
}


def pressing_need(player):
    """The labeled vital furthest past its threshold, or ``None``."""
    vitals = getattr(player, "vitals", None) or {}
    index = by_name()
    worst, worst_vital = 0.0, None
    for vital, score_name in NEED_THRESHOLDS.items():
        value = vitals.get(vital)
        if value is None:
            continue
        threshold = index[score_name].base
        overshoot = (float(value) - threshold) if vital in _DRIVE_VITALS \
            else (threshold - float(value))
        if overshoot > worst:
            worst, worst_vital = overshoot, vital
    return worst_vital


def whispers(player, other: str = "") -> List[str]:
    """The character's weights as prose lines for the LLM prompt.

    One line per active trait that moves a score, plus a line for a pressing need
    and (when relevant) a remembered target. Deterministic and de-duplicated.
    """
    lines: List[str] = []
    for mod in TRAIT_MODIFIERS:
        if (_dial(player, mod.trait) - DIAL_NEUTRAL) * mod.coefficient:
            line = WHISPERS.get(mod.trait)
            if line:
                lines.append(line)
    need = pressing_need(player)
    if need:
        lines.append(_NEED_WHISPERS[need])
    if memory_weights(player, other):
        lines.append(f"You remember {other}.")
    seen: set = set()
    out: List[str] = []
    for line in lines:
        if line and line not in seen:
            seen.add(line)
            out.append(line)
    return out


def by_name() -> Dict[str, Score]:
    """Every score keyed by name. Raises on a duplicate declaration."""
    index: Dict[str, Score] = {}
    for score in SCORES:
        if score.name in index:
            raise ValueError(f"duplicate score declaration: {score.name}")
        index[score.name] = score
    return index


def validate_score(name: str) -> Score:
    """The declared score *name*, or ``KeyError`` if it is not declared."""
    index = by_name()
    if name not in index:
        raise KeyError(f"undeclared decision score: {name}")
    return index[name]


def scores_for(decision_name: str) -> Tuple[Score, ...]:
    """Every score the named decision reads, in declaration order."""
    index = by_name()
    for decision in DECISIONS:
        if decision.name == decision_name:
            return tuple(index[n] for n in decision.scores)
    raise KeyError(f"unknown decision: {decision_name}")


def check_registry() -> List[str]:
    """Internal consistency problems, as human-readable lines ([] when clean).

    This is the part of the gate that needs no engine: every score declared with a
    known kind and a name that is namespaced and unique, a base inside its own
    range; every decision using a known combine and pick, referencing only declared
    scores. The engine cross-check and the personality-file scan live in
    ``tools/disposition_index.py``.
    """
    problems: List[str] = []
    seen: set = set()
    for score in SCORES:
        if score.name in seen:
            problems.append(f"duplicate score name: {score.name}")
        seen.add(score.name)
        if not _NAME_RE.match(score.name):
            problems.append(f"{score.name}: not a namespaced name (a.b)")
        if score.kind not in SCORE_KINDS:
            problems.append(f"{score.name}: unknown kind `{score.kind}`")
        if not (score.lo <= score.base <= score.hi):
            problems.append(
                f"{score.name}: base {score.base} outside range "
                f"[{score.lo}, {score.hi}]")
        if score.lo > score.hi:
            problems.append(f"{score.name}: lo {score.lo} > hi {score.hi}")

    declared = {s.name for s in SCORES}
    for decision in DECISIONS:
        if decision.combine not in COMBINES:
            problems.append(f"{decision.name}: unknown combine `{decision.combine}`")
        if decision.pick not in PICKS:
            problems.append(f"{decision.name}: unknown pick `{decision.pick}`")
        for name in decision.scores:
            if name not in declared:
                problems.append(
                    f"{decision.name}: references undeclared score `{name}`")
    problems += check_features()
    problems += check_character()
    problems += check_gates()
    return problems
