"""Background social interactions — deterministic NPC <-> NPC (task-423, absorving task-417).

Two co-present background characters pick a social action; rules, the
relationship band and traits decide which one and how it lands; **each side
records its own outcome and its own memory**. Rikka teases Vekka: Rikka's memory
is "I teased Vekka in the sleeping halls" with Social up and closeness up, while
Vekka's is "Rikka teased me" with Social down and closeness down. One event, two
participants, two asymmetric consequences.

No LLM, no planning: a weighted draw over gated actions, then a computed outcome.
Deterministic — every roll is seeded from ``(actor, target, tick, action)``, so a
replay reproduces the same camp history.

The gate (task-417) is a *component* here rather than a separate pass: the
meeting must be same-area, both parties background, and capped per in-game day,
or the camp becomes a relationship treadmill in the crowded areas. Task-417's
"symmetric meeting" was the placeholder this replaces.

Relationship changes go through `engine/relationships.py` (task-420) so each one
carries a cause, and the band ladder that decides whether a tease is affectionate
or hostile is the same one the prompt renders — `closeness_band` / `band_at_least`.
"""

from __future__ import annotations

import random
from typing import Optional

from engine.relationships import (
    apply_relationship_delta,
    band_at_least,
    closeness_band,
)

#: Minimum game minutes between one character's interactions. With the daily cap
#: this spreads a day's allowance out instead of letting it land in a burst of
#: consecutive ticks.
SOCIAL_COOLDOWN_MINUTES = 90

#: Cap per background character per in-game day (task-417). Crowded areas
#: otherwise pair the same people over and over.
#:
#: **This cap is the bound, not a blocking activity.** task-423 §4 specified a
#: ~10-game-minute `conversing` activity on both participants to stop a character
#: taking ~1,000 interactions a week. Measured, the cap alone already holds the
#: rate to 6-7 per character per day at both 1 and 15 min/tick, while the activity
#: broke the survival ladder at short ticks: a 10-tick block at 1 min/tick
#: repeated over a day dropped camp Hygiene 70 -> 28 and Entertainment 38 -> 11,
#: because a blocked character cannot eat, sleep or wash, and a conversation pays
#: enough Entertainment that the "seek amusement" need stops firing. At 15
#: min/tick the activity rounded to one tick and never blocked anything, so the
#: damage was invisible there and would only have shown up as an unexplained
#: short-tick regression.
MEETINGS_PER_CHARACTER_PER_DAY = 6

#: Bands at or above which `confide` / `flirt` unlock — the Diary's
#: ``has_relationship: {min_quality}`` gate, expressed with the shared ladder.
CONFIDE_BAND = "friend"
FLIRT_BAND = "close_friend"

#: A band at or above this counts as *warm*, which is what decides whether an
#: ambiguous action (a tease, a joke) reads affectionate or hostile. This is the
#: load-bearing sign rule: a tease between friends is affection for both sides,
#: the same tease at low closeness is an attack.
WARM_BAND = "acquaintance"

#: Six-tier outcome ladder, borrowed from the author's Diary. The scale damps
#: failure relative to success on purpose: a symmetric ladder makes the camp
#: monotonically miserable within a week, because every social bid that does not
#: land still costs both sides.
TIER_SCALE = {
    "critical_failure": -1.0,
    "major_failure": -0.75,
    "minor_failure": -0.4,
    "success": 1.0,
    "major_success": 1.4,
    "critical_success": 1.8,
}
TIERS = tuple(TIER_SCALE)

#: Tier -> (actor emotion, target emotion). Only the strong tiers move affect;
#: a plain success is unremarkable and should not churn the emotion dict.
TIER_EMOTION = {
    "critical_failure": ("sad", 0.5),
    "major_failure": ("sad", 0.4),
    "minor_failure": ("neutral", 0.2),
    "success": ("happy", 0.3),
    "major_success": ("happy", 0.5),
    "critical_success": ("happy", 0.7),
}

#: Empathy: the target's affect mirrors the event roughly.
TIER_TARGET_EMOTION = {
    "critical_failure": ("angry", 0.4),
    "major_failure": ("sad", 0.3),
    "minor_failure": ("neutral", 0.2),
    "success": ("happy", 0.3),
    "major_success": ("happy", 0.5),
    "critical_success": ("happy", 0.6),
}

#: Narrative tags from the vocabulary already in the camp data, so generated
#: memories are retrievable by the same words authored ones use.
NARRATIVE_TAGS = {
    "chat": "trade", "joke": "fun", "tease": "fun", "compliment": "prestige",
    "confide": "secret", "flirt": "secret", "apologise": "debt", "bully": "rivalry",
}

#: Action tables. `dc` is the difficulty; `min_band` gates who it is available
#: with; the per-side dicts are the effect of a plain **success** (the tier scale
#: multiplies them); `hostile_variant` replaces the target's reading when the
#: band is cold.
ACTIONS = {
    "chat": {
        "dc": 8, "min_band": "unfriendly",
        "actor": {"Social": 3, "Entertainment": 1},
        "target": {"Social": 3, "Entertainment": 1},
        "rel_actor": 1, "rel_target": 1,
    },
    "joke": {
        "dc": 11, "min_band": "unfriendly",
        "actor": {"Social": 3, "Entertainment": 3},
        "target": {"Social": 2, "Entertainment": 3},
        "rel_actor": 1, "rel_target": 1,
        "hostile_variant": {
            "target": {"Social": -2, "Entertainment": -2},
            "rel_actor": 0, "rel_target": -1,
        },
    },
    "compliment": {
        "dc": 9, "min_band": "unfriendly",
        "actor": {"Social": 2, "Entertainment": 1},
        "target": {"Social": 3, "Entertainment": 3},
        "rel_actor": 1, "rel_target": 2,
        "hostile_variant": {
            "target": {"Social": -1, "Entertainment": 0},
            "rel_actor": 0, "rel_target": -1,
        },
    },
    "tease": {
        "dc": 10, "min_band": "unfriendly",
        "actor": {"Social": 3, "Entertainment": 3},
        "target": {"Social": 2, "Entertainment": 2},
        "rel_actor": 1, "rel_target": 1,
        "hostile_variant": {
            "target": {"Social": -3, "Entertainment": -2},
            "rel_actor": 0, "rel_target": -2,
        },
    },
    "confide": {
        "dc": 13, "min_band": CONFIDE_BAND,
        "actor": {"Social": 4, "Entertainment": 2},
        "target": {"Social": 4, "Entertainment": 3},
        "rel_actor": 2, "rel_target": 3,
    },
    "flirt": {
        "dc": 14, "min_band": FLIRT_BAND,
        "actor": {"Social": 3, "Entertainment": 4},
        "target": {"Social": 3, "Entertainment": 4},
        "rel_actor": 2, "rel_target": 3,
    },
    "apologise": {
        "dc": 7, "min_band": "unfriendly",
        "actor": {"Social": 1, "Entertainment": 0},
        "target": {"Social": 2, "Entertainment": 1},
        "rel_actor": 1, "rel_target": 3,
    },
    "bully": {
        "dc": 9, "min_band": "unfriendly",
        # A bully is never a warm event, however well it lands for the actor.
        "actor": {"Social": -1, "Entertainment": 2},
        "target": {"Social": -4, "Entertainment": -3},
        "rel_actor": 0, "rel_target": -3,
    },
}

#: Action is available to everyone who passes its band gate. `ignore` is not in
#: `ACTIONS`: it is the *absence* of an interaction (no activity, no memory, no
#: relationship change) and is handled as a draw result, not an action.
#:
#: An `ignore` costs **nothing** — not the daily meeting budget either. Declining
#: to engage is not an interaction, and charging for it would mean an introvert's
#: budget is spent by the very behaviour that characterises them, which reads as
#: punishment rather than disposition. They are simply approachable again next
#: tick, and the cap counts the conversations they actually had.
BASE_WEIGHTS = {
    "chat": 10.0, "joke": 6.0, "compliment": 5.0, "tease": 6.0,
    "confide": 3.0, "flirt": 2.0, "apologise": 2.0, "bully": 2.0,
}

#: Weight of "they don't engage". Introverts/loners raise this sharply; that is
#: how "an introvert picks `ignore` far more often than an extrovert" is true.
BASE_IGNORE_WEIGHT = 4.0

#: Vital thresholds for need pressure (task-423 §3). Company maintains Social
#: but does not fill it (task-431), so a low meter is what makes a character
#: *seek* company rather than merely tolerate it.
SOCIAL_LOW = 50
ENTERTAINMENT_LOW = 50


def _traits(player) -> dict:
    """The boolean/numeric trait facts the weight table reads."""
    try:
        from engine.traits import TraitSystem
    except Exception:
        return {}
    has = lambda name: TraitSystem.has_effect(player, name)  # noqa: E731
    social_gain = TraitSystem.get_first_effect(player, "social_gain")
    try:
        social_gain = float(social_gain) if social_gain is not None else 1.0
    except (TypeError, ValueError):
        social_gain = 1.0
    return {
        "social_gain": social_gain,
        "impatient": bool(has("impatient")),
        "patient": bool(has("patient")),
        "hostile": bool(has("hostile")),
        "attention_seeker": bool(has("attention_seeker")),
        "loner": "loner" in (getattr(player, "traits", None) or {}),
    }


def action_weights(actor, target, closeness: Optional[float] = None) -> dict:
    """Weight per action for *actor* toward *target*. Never argmax — a draw.

    Derived from traits, the relationship band and need pressure, so dispositions
    are visible in the *distribution* while any single choice stays surprising.
    """
    if closeness is None:
        closeness = _closeness(actor, getattr(target, "name", target))
    band = closeness_band(closeness)
    warm = band_at_least(closeness, WARM_BAND)
    traits = _traits(actor)
    weights = dict(BASE_WEIGHTS)

    # Gate: an action unavailable in this band is simply not in the draw.
    for name, spec in ACTIONS.items():
        if not band_at_least(closeness, spec["min_band"]):
            weights[name] = 0.0

    if not warm:
        # Cold band: the ambiguous actions read hostile, so an apology is the
        # natural move and warmth is presumptuous.
        weights["bully"] = weights.get("bully", 0.0) * 1.8
        weights["apologise"] = weights.get("apologise", 0.0) * 1.6
        weights["compliment"] = weights.get("compliment", 0.0) * 0.5
        weights["confide"] = weights.get("confide", 0.0) * 0.5
    else:
        # Warm: hostility reads as a betrayal and mostly stops.
        weights["bully"] = weights.get("bully", 0.0) * 0.15

    if traits["hostile"]:
        weights["bully"] = weights.get("bully", 0.0) * 2.5
        weights["compliment"] = weights.get("compliment", 0.0) * 0.5
        weights["apologise"] = weights.get("apologise", 0.0) * 0.4
    if traits["impatient"]:
        weights["tease"] = weights.get("tease", 0.0) * 1.6
        weights["confide"] = weights.get("confide", 0.0) * 0.5
    if traits["patient"]:
        weights["confide"] = weights.get("confide", 0.0) * 1.6
        weights["tease"] = weights.get("tease", 0.0) * 0.5
    if traits["attention_seeker"]:
        for name in ("chat", "joke", "flirt"):
            weights[name] = weights.get(name, 0.0) * 1.3

    # social_gain: extrovert 2, default 1, introvert/loner 0.
    social_gain = traits["social_gain"]
    if social_gain <= 0:
        for name in weights:
            weights[name] *= 0.35
    elif social_gain >= 2:
        for name in ("chat", "joke"):
            weights[name] = weights.get(name, 0.0) * 1.5

    # Need pressure: a lonely or bored character reaches out more.
    vitals = getattr(actor, "vitals", None) or {}
    if vitals.get("Social", 100) <= SOCIAL_LOW:
        for name in ("chat", "confide", "joke"):
            weights[name] = weights.get(name, 0.0) * 1.3
    if vitals.get("Entertainment", 100) <= ENTERTAINMENT_LOW:
        for name in ("joke", "tease"):
            weights[name] = weights.get(name, 0.0) * 1.3

    return {name: max(0.0, w) for name, w in weights.items()}


def ignore_weight(actor) -> float:
    """Weight of "they don't engage". Introverts and loners take this often."""
    traits = _traits(actor)
    weight = BASE_IGNORE_WEIGHT
    if traits["social_gain"] <= 0:
        weight *= 3.0
    elif traits["social_gain"] >= 2:
        weight *= 0.4
    if traits["attention_seeker"]:
        weight *= 0.6
    return weight


def _rng(actor_name: str, target_name: str, tick: int, action: str) -> random.Random:
    """Seeded per (actor, target, tick, action) so a replay reproduces history."""
    return random.Random(f"{actor_name}|{target_name}|{int(tick)}|{action}")


def _closeness(player, other_name: str) -> float:
    rel = (getattr(player, "relationships", None) or {}).get(other_name) or {}
    try:
        return float(rel.get("closeness", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def affinity(first, second) -> float:
    """Mutual closeness: the mean of each side's read of the other."""
    a = _closeness(first, getattr(second, "name", second))
    b = _closeness(second, getattr(first, "name", first))
    return (a + b) / 2.0


def choose_action(actor, target, tick: int) -> str:
    """Weighted draw over the gated actions. Returns an action name or "ignore"."""
    weights = action_weights(actor, target)
    names = list(weights)
    values = [weights[n] for n in names]
    names.append("ignore")
    values.append(ignore_weight(actor))
    if sum(values) <= 0:
        return "ignore"
    rng = _rng(getattr(actor, "name", ""), getattr(target, "name", ""), tick, "choose")
    return rng.choices(names, weights=values, k=1)[0]


def resolve_tier(actor, target, action: str, tick: int) -> str:
    """d20 + modifiers vs the action's DC, mapped onto the six-tier ladder.

    Modifiers reuse what exists rather than inventing a social stat: the actor's
    Persuasion skill and the relationship band. Natural 1 and natural 20 always
    land at the bottom and top tiers, so a doomed or blessed moment is legible.
    """
    spec = ACTIONS.get(action)
    if spec is None:
        return "success"
    rng = _rng(getattr(actor, "name", ""), getattr(target, "name", ""), tick,
               "resolve:" + action)
    roll = rng.randint(1, 20)
    if roll == 1:
        return "critical_failure"
    if roll == 20:
        return "critical_success"

    skills = getattr(actor, "skills", None) or {}
    try:
        persuasion = float(skills.get("Persuasion", 0) or 0)
    except (TypeError, ValueError):
        persuasion = 0.0
    modifier = int(persuasion // 5)
    closeness = affinity(actor, target)
    if band_at_least(closeness, WARM_BAND):
        modifier += 2
    elif closeness_band(closeness) in ("rival", "enemy", "mortal_enemy"):
        modifier -= 2

    margin = (roll + modifier) - int(spec["dc"])
    if margin <= -10:
        return "critical_failure"
    if margin <= -5:
        return "major_failure"
    if margin < 0:
        return "minor_failure"
    if margin < 5:
        return "success"
    if margin < 10:
        return "major_success"
    return "critical_success"


def _reading(action: str, closeness: float) -> dict:
    """The action's effect on both sides at this closeness.

    A cold band swaps in the hostile reading of an ambiguous action — the sign
    rule that keeps a tease affectionate between friends and an attack between
    rivals.
    """
    spec = ACTIONS[action]
    reading = {
        "actor": dict(spec.get("actor") or {}),
        "target": dict(spec.get("target") or {}),
        "rel_actor": int(spec.get("rel_actor", 0)),
        "rel_target": int(spec.get("rel_target", 0)),
    }
    variant = spec.get("hostile_variant")
    if variant and not band_at_least(closeness, WARM_BAND):
        reading["target"] = dict(variant.get("target") or {})
        reading["rel_actor"] = int(variant.get("rel_actor", reading["rel_actor"]))
        reading["rel_target"] = int(variant.get("rel_target", reading["rel_target"]))
    return reading


def _scale(vitals: dict, scale: float) -> dict:
    out = {}
    for stat, base in vitals.items():
        amount = int(round(base * scale))
        if amount:
            out[stat] = amount
    return out


def _apply_vitals(player, deltas: dict) -> None:
    vitals = getattr(player, "vitals", None)
    if not vitals:
        return
    for stat, amount in deltas.items():
        if stat not in vitals:
            continue
        try:
            current = float(vitals.get(stat, 0) or 0)
        except (TypeError, ValueError):
            continue
        vitals[stat] = max(0, min(100, current + amount))


def _apply_emotion(player, emotion: str, intensity: float) -> None:
    try:
        player.set_emotion(emotion, intensity)
    except Exception:
        pass


def memory_text(action: str, tier: str, other: str, area_name: str,
                first_person: bool, actor_name: str = "") -> str:
    """Templated memory text. Background text is templated; the LLM enriches it
    later on promotion (the established trace -> memory direction).

    Both sides come from one template per (action, landed): the actor reads
    "I teased Vekka in the sleeping halls", the target reads "Rikka teased me
    in the sleeping halls".
    """
    from engine.social_text import phrase
    landed = TIER_SCALE[tier] > 0
    if first_person:
        return f"I {phrase(action, tier, other, landed)} in the {area_name}."
    return f"{actor_name} {phrase(action, tier, 'me', landed)} in the {area_name}."


def perform(gs, actor, target, area_id: str, area_name: str, tick: int,
            action: Optional[str] = None) -> Optional[dict]:
    """Resolve one interaction between two co-present characters.

    Returns a summary dict, or None when the actor draws `ignore` (the absence of
    an interaction: no activity, no memory, no relationship change).

    ``action`` forces a specific action instead of drawing one — for a scripted
    interaction, and so tests can exercise an outcome without depending on the
    seed.
    """
    actor_name = getattr(actor, "name", "")
    target_name = getattr(target, "name", "")
    if action is None:
        action = choose_action(actor, target, tick)
    if action == "ignore" or action not in ACTIONS:
        return None

    closeness = affinity(actor, target)
    tier = resolve_tier(actor, target, action, tick)
    scale = TIER_SCALE[tier]
    reading = _reading(action, closeness)

    # Vitals: each side gets its own, and the tier signs them.
    actor_vitals = _scale(reading["actor"], scale)
    target_vitals = _scale(reading["target"], scale)
    _apply_vitals(actor, actor_vitals)
    _apply_vitals(target, target_vitals)

    # Affect (only strong tiers move it).
    emotion, intensity = TIER_EMOTION[tier]
    _apply_emotion(actor, emotion, intensity)
    t_emotion, t_intensity = TIER_TARGET_EMOTION[tier]
    _apply_emotion(target, t_emotion, t_intensity)

    # Relationship: through the one write path, so the cause is recorded.
    actor_rel = int(round(reading["rel_actor"] * max(0.0, scale)))
    target_rel = int(round(reading["rel_target"] * max(0.0, scale)))
    if actor_rel:
        apply_relationship_delta(actor, target_name, actor_rel, action,
                                 tick=tick, area_id=area_id)
    if target_rel:
        apply_relationship_delta(target, actor_name, target_rel, action,
                                 tick=tick, area_id=area_id)

    # Trace: the authoritative record, one entry per side.
    _trace(actor, tick, action, tier, area_name, target_name, actor_vitals,
           "actor", actor_name)
    _trace(target, tick, action, tier, area_name, actor_name, target_vitals,
           "target", actor_name)

    # Memory: the subjective layer, one templated entry per side, both tagged
    # with the event so "every memory Vekka has about Rikka" is a lookup.
    subject_ids = _subject_ids(gs, actor_name, target_name, area_id)
    _remember(actor, tick, action, tier, area_name, target_name, subject_ids,
              first_person=True)
    _remember(target, tick, action, tier, area_name, actor_name, subject_ids,
              first_person=False, actor_name=actor_name)

    _mark_interaction(gs, actor, target, tick)

    return {
        "actor": actor_name, "target": target_name, "action": action,
        "tier": tier, "area": area_name,
        "actor_vitals": actor_vitals, "target_vitals": target_vitals,
        "actor_closeness": actor_rel, "target_closeness": target_rel,
    }


def _subject_ids(gs, actor_name: str, target_name: str, area_id: str) -> list:
    """`entity_ids` for the memory: both participants and the area.

    This is the field that was 0/17 populated, and it is what makes a character's
    memories *about a person* a lookup instead of a keyword search (task-403).
    """
    ids = []
    for name in (actor_name, target_name):
        try:
            ids.append(gs.player_manager.get_player_node_id(name))
        except Exception:
            pass
    if area_id:
        ids.append(area_id)
    return [i for i in ids if i]


def _trace(player, tick, action, tier, area_name, counterpart, vitals, role,
           actor_name) -> None:
    try:
        from engine.trace import record
    except Exception:
        return
    record(
        player, tick, "social",
        f"{action} ({role}) with {counterpart}: {tier}",
        why=f"social:{action}",
        area=area_name,
        tags=["social", action, tier, "rel:" + str(counterpart),
              NARRATIVE_TAGS.get(action, "social")],
        salient=abs(TIER_SCALE[tier]) >= 1.4,
        delta=dict(vitals) or None,
    )


def _remember(player, tick, action, tier, area_name, counterpart, subject_ids,
              first_person: bool, actor_name: str = "") -> None:
    text = memory_text(action, tier, counterpart, area_name, first_person,
                       actor_name=actor_name)
    importance = 4 + int(abs(TIER_SCALE[tier]) * 2)
    player.add_memory(
        text, tick, importance=importance, memory_type="social",
        tags=["social", action, tier, "rel:" + str(counterpart),
              NARRATIVE_TAGS.get(action, "social")],
        source="background", entity_ids=subject_ids, location=area_name,
    )


def _mark_interaction(gs, actor, target, tick: int) -> None:
    """Stamp both participants so the cooldown applies to each of them."""
    for player in (actor, target):
        try:
            player._social_last_tick = int(tick)
        except Exception:
            pass


def _off_cooldown(player, gs, tick: int) -> bool:
    """True when enough game minutes have passed since this character's last
    interaction. Expressed in game minutes, so it does not shorten or stretch
    with the tick length."""
    last = getattr(player, "_social_last_tick", None)
    if last is None:
        return True
    try:
        minutes_per_tick = float(getattr(gs, "time_per_tick_minutes", 1) or 1)
    except (TypeError, ValueError):
        minutes_per_tick = 1.0
    elapsed = (int(tick) - int(last)) * minutes_per_tick
    return elapsed >= SOCIAL_COOLDOWN_MINUTES


# ────────────────────────── the gate (task-417) ──────────────────────────


def is_background(player) -> bool:
    """True when this character is run by the deterministic tier.

    An attended character's social life belongs to the LLM loop (task-412's
    seam); this pass must never pair them.
    """
    mode = getattr(player, "simulation_mode", "") or ""
    return mode == "background"


def is_available(player) -> bool:
    """Conscious, not mid-activity, and not otherwise engaged."""
    if getattr(player, "state", "") in ("dead", "unconscious"):
        return False
    if getattr(player, "activity", None):
        return False
    return True


def meetings_allowed(player, gs, tick: int) -> int:
    """Remaining meetings this character may take today (the task-417 cap).

    The counter rolls over on the in-game day, so it is tick-length independent.
    """
    per_player = getattr(gs, "_social_day", None)
    if per_player is None:
        per_player = gs._social_day = {}
    try:
        minutes_per_tick = float(getattr(gs, "time_per_tick_minutes", 1) or 1)
    except (TypeError, ValueError):
        minutes_per_tick = 1.0
    try:
        from engine.tick_manager import MINUTES_PER_DAY
        ticks_per_day = max(1, int(round(MINUTES_PER_DAY / max(0.001, minutes_per_tick))))
    except Exception:
        ticks_per_day = max(1, int(round(1440 / max(0.001, minutes_per_tick))))
    day = int(tick) // ticks_per_day
    key = getattr(player, "name", "")
    state = per_player.get(key)
    if not state or state.get("day") != day:
        per_player[key] = {"day": day, "count": 0}
        return MEETINGS_PER_CHARACTER_PER_DAY
    return MEETINGS_PER_CHARACTER_PER_DAY - int(state.get("count", 0))


def _record_meeting(gs, player) -> None:
    key = getattr(player, "name", "")
    state = (getattr(gs, "_social_day", None) or {}).get(key)
    if state:
        state["count"] = int(state.get("count", 0)) + 1


def pair_for_area(gs, area_id: str, area_name: str, tick: int) -> list:
    """Greedy deterministic pairing of the eligible characters in one area.

    Greedy by mutual affinity (descending), ties broken by name, so the same
    relationship state always yields the same pairs. Each character is in at most
    one pair per pass.
    """
    present = []
    for name, player in (gs.player_manager.players or {}).items():
        if getattr(player, "current_area", None) != area_name:
            continue
        if not is_background(player) or not is_available(player):
            continue
        if meetings_allowed(player, gs, tick) <= 0:
            continue
        if not _off_cooldown(player, gs, tick):
            continue
        present.append(player)
    if len(present) < 2:
        return []

    present.sort(key=lambda p: getattr(p, "name", ""))
    candidates = []
    for i, first in enumerate(present):
        for second in present[i + 1:]:
            candidates.append((-affinity(first, second),
                               getattr(first, "name", ""), getattr(second, "name", "")))
    candidates.sort()

    pairs, used = [], set()
    for _, a_name, b_name in candidates:
        if a_name in used or b_name in used:
            continue
        a, b = (gs.player_manager.players[a_name], gs.player_manager.players[b_name])
        if meetings_allowed(a, gs, tick) <= 0 or meetings_allowed(b, gs, tick) <= 0:
            continue
        used.update((a_name, b_name))
        pairs.append((a, b))
    return pairs


def run_social_pass(gs, tick: Optional[int] = None) -> list:
    """One social pass over the world: pair per area, resolve, cap.

    Per area, never globally — there is no distance in this world model, so
    nothing else would stop two characters on opposite sides of the camp from
    meeting (task-417).
    """
    if gs is None:
        return []
    if tick is None:
        tick = getattr(gs, "time_ticks", 0)
    resolved = []
    for area_id, area_name in _areas_with_background(gs):
        for actor, target in pair_for_area(gs, area_id, area_name, tick):
            outcome = perform(gs, actor, target, area_id, area_name, tick)
            if outcome is None:
                continue
            _record_meeting(gs, actor)
            _record_meeting(gs, target)
            resolved.append(outcome)
    return resolved


def _areas_with_background(gs) -> list:
    """(area_id, area_name) for areas holding two or more background characters."""
    counts = {}
    for player in (gs.player_manager.players or {}).values():
        if not is_background(player) or not is_available(player):
            continue
        name = getattr(player, "current_area", None)
        if name:
            counts[name] = counts.get(name, 0) + 1
    out = []
    for area_name in sorted(n for n, c in counts.items() if c >= 2):
        area_id = ""
        try:
            from engine.room_perception import resolve_area_node
            node = resolve_area_node(gs.graph, area_name)
            area_id = node.id if node else ""
        except Exception:
            area_id = ""
        out.append((area_id, area_name))
    return out
