"""Autonomic / involuntary body layer and vulnerability/regulation physics.

Owns the 8 non-voluntary physiological channels that sit strictly outside LLM
control: heart_rate, breathing, muscle_tension, vasomotor (flush/pallor),
sweat_chills, gut_throat, motor_tone, and eyes_tears.

All prompts rendered here obey docs/virtualWorld/Characters/Interiority & Subtext.md:
zero clinical headers, zero DBT jargon, zero raw numbers.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from prototypes.emotions.schema import (
    AUTONOMIC_CHANNELS,
    AUTONOMIC_INERTIA_DECAY,
    EMOTION_PROFILES,
    FAMILIES,
    FAMILY_BASELINES,
    SIGNED_AUTONOMIC_CHANNELS,
    CharacterEmotionState,
)


def species_autonomic_mode(player: Any) -> str:
    """Return 'none' (dead/undead/construct), 'animal', or 'humanoid'."""
    state = str(getattr(player, "state", "awake") or "awake").lower()
    if state in ("dead", "unconscious"):
        return "none"
    tags = {str(t).lower() for t in (getattr(player, "tags", None) or [])}
    species = str(getattr(player, "species", "") or "").lower()
    if tags & {"undead", "ghost", "construct", "golem", "skeleton"} or species in {
        "undead", "ghost", "construct", "golem", "skeleton",
    }:
        return "none"
    if tags & {"animal", "beast", "wolf", "dog", "cat"} or species in {
        "wolf", "dog", "cat", "bear", "deer", "rat", "fox", "horse", "bird",
    }:
        return "animal"
    return "humanoid"


def compute_vulnerability_load(player: Any, state: Optional[CharacterEmotionState] = None) -> Tuple[float, List[str]]:
    """Aggregate physiological and psychological vulnerability (0.0..1.0) from real ViWo state."""
    vitals = getattr(player, "vitals", None) or {}
    conditions = getattr(player, "conditions", None) or {}
    load = 0.0
    factors: List[str] = []

    def _v(key: str, default: float) -> float:
        try:
            return float(vitals.get(key, default))
        except (TypeError, ValueError):
            return default

    energy = _v("Energy", 100.0)
    if energy <= 30.0:
        load += 0.25 if energy <= 15.0 else 0.16
        factors.append("exhausted" if energy <= 15.0 else "low energy")

    hunger = _v("Hunger", 0.0)
    if hunger >= 70.0:
        load += 0.22 if hunger >= 85.0 else 0.14
        factors.append("starving" if hunger >= 85.0 else "hungry")

    thirst = _v("Thirst", 0.0)
    if thirst >= 70.0:
        load += 0.18 if thirst >= 85.0 else 0.10
        factors.append("parched" if thirst >= 85.0 else "thirsty")

    bladder = _v("Bladder", 0.0)
    if bladder >= 75.0:
        load += 0.12
        factors.append("urgent bladder pressure")

    sanity = _v("Sanity", 100.0)
    if sanity <= 45.0:
        load += 0.25 if sanity <= 25.0 else 0.15
        factors.append("frayed composure" if sanity > 25.0 else "severe mental strain")

    social = _v("Social", 100.0)
    if social <= 25.0:
        load += 0.14
        factors.append("isolated")

    hp = _v("HP", 100.0)
    max_hp = max(1.0, _v("Max_HP", 100.0))
    if (hp / max_hp) < 0.65:
        load += 0.22
        factors.append("injured")

    temp = _v("Temperature", 37.0)
    if temp < 35.5:
        load += 0.16
        factors.append("chilled")
    elif temp > 38.0:
        load += 0.14
        factors.append("overheated")

    active_conds = set()
    if isinstance(conditions, dict):
        active_conds = {k for k, v in conditions.items() if v}
    elif isinstance(conditions, (list, set, tuple)):
        active_conds = {str(x) for x in conditions}

    for cid, weight, label in (
        ("sick", 0.18, "sick"),
        ("poisoned", 0.22, "poisoned"),
        ("hypothermia", 0.25, "hypothermic"),
        ("frightened", 0.20, "frightened"),
        ("social_breakdown", 0.22, "social breakdown"),
        ("exhausted", 0.18, "exhaustion condition"),
        ("menstruating", 0.08, "cramps and fatigue"),
    ):
        if cid in active_conds:
            load += weight
            factors.append(label)

    if state is not None:
        unresolved_rumination = sum(
            ep.rumination_ticks for ep in state.episodes if not ep.resolved
        )
        if unresolved_rumination >= 3:
            load += min(0.18, unresolved_rumination * 0.03)
            factors.append("lingering rumination")
        if state.autonomic.get("heart_rate", 0.0) >= 45.0:
            load += 0.10
            factors.append("elevated pulse")

    return min(1.0, load), factors


def compute_positive_buffer(families: Dict[str, float]) -> float:
    """Happiness/love/calm cushion that raises the threshold against minor annoyance (0.0..1.0)."""
    score = 0.0
    for fam, weight in (("happiness", 0.45), ("love", 0.30), ("calm", 0.25)):
        over = max(0.0, families.get(fam, FAMILY_BASELINES[fam]) - FAMILY_BASELINES[fam])
        score += (over / 50.0) * weight
    return min(1.0, score)


def compute_regulation_capacity(
    player: Any,
    vulnerability_load: float,
    state: Optional[CharacterEmotionState] = None,
) -> Tuple[float, Dict[str, float]]:
    """Compute DBT Handout 4 regulation capacity (15..95) from WIS, traits, biology, moodiness."""
    stats = getattr(player, "stats", None) or {}
    wis = float(stats.get("WIS", 10) or 10)
    base = 44.0 + (wis - 10.0) * 3.0

    raw_traits = getattr(player, "traits", None) or {}
    trait_ids = set(raw_traits.keys()) if isinstance(raw_traits, dict) else {str(t) for t in raw_traits}

    trait_mod = 0.0
    for tid, delta in (
        ("patient", 12.0),
        ("stoic", 14.0),
        ("composed", 14.0),
        ("calm", 8.0),
        ("impatient", -10.0),
        ("impulsive", -12.0),
        ("jittery", -10.0),
        ("cowardly", -8.0),
        ("volatile", -14.0),
        ("paranoid", -10.0),
    ):
        if tid in trait_ids:
            trait_mod += delta

    biology_drain = vulnerability_load * 26.0
    moodiness_drain = 0.0
    if state is not None:
        active_rum = sum(ep.rumination_ticks for ep in state.episodes if not ep.resolved)
        moodiness_drain = min(16.0, active_rum * 2.5)

    cap = max(15.0, min(95.0, base + trait_mod - biology_drain - moodiness_drain))
    breakdown = {
        "wis_base": round(base, 1),
        "trait_mod": round(trait_mod, 1),
        "biology_drain": round(-biology_drain, 1),
        "moodiness_drain": round(-moodiness_drain, 1),
        "capacity": round(cap, 1),
    }
    return cap, breakdown


def update_autonomic(
    autonomic: Dict[str, float],
    families: Dict[str, float],
    player: Any,
    *,
    suppressed: bool = False,
    exertion: float = 0.0,
) -> Dict[str, float]:
    """Update the 8 non-voluntary autonomic channels from the COMBINED emotion vector + physics.

    All raised families contribute simultaneously (weighted sum), so mixed emotions
    blend physically (e.g. anger + sadness + shame -> hot face + tight jaw +
    stinging tears + hollow gut). Autonomic state approaches target with inertia
    rather than teleporting to zero.
    """
    mode = species_autonomic_mode(player)
    if mode == "none":
        return {ch: 0.0 for ch in AUTONOMIC_CHANNELS}

    pos_contribs: Dict[str, List[float]] = {ch: [] for ch in AUTONOMIC_CHANNELS}
    neg_contribs: Dict[str, List[float]] = {ch: [] for ch in AUTONOMIC_CHANNELS}
    for fam in FAMILIES:
        over = max(0.0, families.get(fam, FAMILY_BASELINES[fam]) - FAMILY_BASELINES[fam])
        if over < 6.0:
            continue
        strength = min(1.0, over / 60.0)
        weights = EMOTION_PROFILES[fam]["autonomic"]
        for ch, w in weights.items():
            val = w * strength * 76.0
            if val > 0.0:
                pos_contribs[ch].append(val)
            elif val < 0.0:
                neg_contribs[ch].append(-val)

    # Diminishing-returns blend per channel (1.00 * top1 + 0.30 * top2 + 0.12 * top3)
    # so 3-4 mildly raised emotions blend realistically instead of summing linearly to 100.
    def _blend(vals: List[float]) -> float:
        if not vals:
            return 0.0
        s = sorted(vals, reverse=True)
        weights_rank = (1.0, 0.30, 0.12, 0.05)
        return sum(v * weights_rank[min(i, len(weights_rank) - 1)] for i, v in enumerate(s))

    targets: Dict[str, float] = {
        ch: _blend(pos_contribs[ch]) - _blend(neg_contribs[ch])
        for ch in AUTONOMIC_CHANNELS
    }

    # Suppression effort tightens muscles and keeps pulse elevated even when trying to look flat.
    if suppressed:
        targets["muscle_tension"] += 22.0
        targets["heart_rate"] += 12.0
        targets["breathing"] += 10.0

    # Physical exertion & body vitals feed the exact same autonomic channels (interoceptive loop).
    vitals = getattr(player, "vitals", None) or {}
    if exertion > 0:
        targets["heart_rate"] += exertion * 55.0
        targets["breathing"] += exertion * 60.0
        targets["sweat_chills"] += exertion * 35.0
        targets["vasomotor"] += exertion * 20.0
    try:
        temp = float(vitals.get("Temperature", 37.0))
        if temp < 35.5:
            targets["sweat_chills"] -= 35.0
            targets["vasomotor"] -= 25.0
            targets["muscle_tension"] += 18.0
        elif temp > 38.0:
            targets["vasomotor"] += 35.0
            targets["sweat_chills"] += 35.0
        energy = float(vitals.get("Energy", 100.0))
        if energy < 25.0:
            targets["motor_tone"] -= 30.0
    except (TypeError, ValueError):
        pass

    out: Dict[str, float] = {}
    for ch in AUTONOMIC_CHANNELS:
        prev = float(autonomic.get(ch, 0.0))
        lo = -100.0 if ch in SIGNED_AUTONOMIC_CHANNELS else 0.0
        tgt = max(lo, min(100.0, targets[ch]))
        # Fast rise when autonomic response spikes; slower settling on the way down (inertia).
        if abs(tgt) >= abs(prev):
            val = prev + (tgt - prev) * 0.72
        else:
            step = AUTONOMIC_INERTIA_DECAY.get(ch, 6.0)
            if prev > tgt:
                val = max(tgt, prev - step)
            else:
                val = min(tgt, prev + step)
        out[ch] = round(max(lo, min(100.0, val)), 2)
    return out


def tick_autonomic(autonomic: Dict[str, float], player: Any) -> Dict[str, float]:
    """Advance physiological inertia by one tick toward resting baseline."""
    mode = species_autonomic_mode(player)
    if mode == "none":
        return {ch: 0.0 for ch in AUTONOMIC_CHANNELS}
    out = dict(autonomic)
    for ch in AUTONOMIC_CHANNELS:
        cur = float(out.get(ch, 0.0))
        step = AUTONOMIC_INERTIA_DECAY.get(ch, 6.0)
        if cur > 0.0:
            out[ch] = round(max(0.0, cur - step), 2)
        elif cur < 0.0:
            out[ch] = round(min(0.0, cur + step), 2)
    return out


def skill_check_penalties(autonomic: Dict[str, float], overloaded: bool) -> Dict[str, int]:
    """Grounded physical friction from involuntary autonomic state (never arbitrary verb bans)."""
    penalties: Dict[str, int] = {}
    tension = float(autonomic.get("muscle_tension", 0.0))
    breath = float(autonomic.get("breathing", 0.0))
    flush = abs(float(autonomic.get("vasomotor", 0.0)))
    tears = float(autonomic.get("eyes_tears", 0.0))

    if tension >= 60.0:
        penalties["Sleight of Hand"] = -3 if tension >= 80.0 else -2
    if breath >= 55.0:
        penalties["Stealth"] = -2 if breath < 80.0 else -3
    if flush >= 55.0 or tears >= 50.0 or overloaded:
        penalties["Deception"] = -3 if (overloaded and (flush >= 55.0 or tears >= 50.0)) else -2
    if overloaded:
        penalties["Persuasion"] = -2
        penalties["Investigation"] = -2
    return penalties


def _collect_persona_habits_quirks(player: Any) -> Tuple[List[str], List[str]]:
    """Read character habits/quirks from existing ViWo persona or player attributes.

    Mirrors ``engine/character_appearance.py`` ``PERSONALITY_FIELDS`` (habits, quirks)
    so personal involuntary tells draw from authored character data instead of
    inventing a separate tells property.
    """
    habits: List[str] = []
    quirks: List[str] = []
    persona = getattr(player, "persona", None)
    if isinstance(persona, dict):
        psec = persona.get("personality") or {}
        if isinstance(psec, dict):
            habits.extend(str(x) for x in (psec.get("habits") or []) if x)
            quirks.extend(str(x) for x in (psec.get("quirks") or []) if x)
    for attr, dest in (("habits", habits), ("quirks", quirks)):
        raw = getattr(player, attr, None)
        if isinstance(raw, (list, tuple, set)):
            dest.extend(str(x) for x in raw if x)
    return habits, quirks


_HABIT_STRESS_CUES: Tuple[Tuple[Tuple[str, ...], str, str, str], ...] = (
    # (keywords, stress_kind, own_phrase, observer_phrase)
    (("eyebrow", "scar"), "suppressed_or_tense", "your right index finger unconsciously smooths the arch of your scarred eyebrow", "smoothing a finger slowly along their scarred eyebrow"),
    (("glasses", "fog", "steam"), "flustered", "warmth rushes up your neck and fogs the insides of your glasses", "glasses fogging faintly as they push them up"),
    (("glasses", "push", "bridge"), "anxious", "your fingers twitch up to push your glasses back up your nose even though they haven't slipped", "pushing their glasses up the bridge of their nose with tense fingers"),
    (("sleeve", "sweater", "collar", "hood"), "anxious", "you pull your sleeves down over your knuckles and tuck inward", "pulling their sleeves over their hands and hunching into their collar"),
    (("lip", "gloss", "bite", "chew"), "flustered", "you catch yourself chewing hard at your bottom lip", "chewing nervously at their bottom lip"),
    (("tape", "hand", "flex", "knuckle", "fist", "callous"), "tense", "your right hand flexes and unflexes slowly at your side", "flexing and unflexing their right hand tightly"),
    (("anchor", "fold", "hands", "clipboard"), "suppressed_or_tense", "your hands fold neatly in front of you in a rigid, rehearsed line", "hands folded neatly in a suspiciously rigid posture"),
    (("ring", "twist", "silver"), "anxious", "your thumb keeps twisting a silver ring in tight circles", "twisting a ring tightly around their thumb"),
    (("ear", "left_ear", "look_away"), "suppressed_or_tense", "your gaze slides just past their ear to keep your face unreadable", "gaze fixed slightly past the listener's ear"),
    (("hair", "push_hair"), "tense", "you rake a hand back through your hair to steady yourself", "raking a hand back through their hair, expression flat"),
)


def _match_personal_tells(
    player: Any,
    state: CharacterEmotionState,
    *,
    overloaded: bool,
    suppressed_families: Optional[List[str]] = None,
) -> Tuple[List[str], List[str]]:
    """Map authored habits/quirks onto active autonomic states (own_phrases, observer_phrases)."""
    habits, quirks = _collect_persona_habits_quirks(player)
    items = habits + quirks
    if not items:
        return [], []

    auto = state.autonomic
    hr = float(auto.get("heart_rate", 0.0))
    tens = float(auto.get("muscle_tension", 0.0))
    vaso = float(auto.get("vasomotor", 0.0))
    tears = float(auto.get("eyes_tears", 0.0))
    suppressed = bool(suppressed_families)

    is_flustered = overloaded or vaso >= 30.0 or hr >= 36.0 or tears >= 28.0
    is_anxious = overloaded or hr >= 28.0 or tens >= 28.0 or vaso >= 25.0 or vaso <= -25.0
    is_tense = overloaded or tens >= 30.0 or hr >= 32.0
    is_suppressed_or_tense = suppressed or tens >= 32.0 or hr >= 34.0

    own_out: List[str] = []
    obs_out: List[str] = []
    for raw in items:
        norm = raw.strip().lower().replace("-", "_").replace(" ", "_")
        for keywords, kind, own_p, obs_p in _HABIT_STRESS_CUES:
            if not any(kw in norm for kw in keywords):
                continue
            fire = (
                (kind == "flustered" and is_flustered)
                or (kind == "anxious" and is_anxious)
                or (kind == "tense" and is_tense)
                or (kind == "suppressed_or_tense" and is_suppressed_or_tense)
            )
            if fire:
                if own_p not in own_out:
                    own_out.append(own_p)
                if obs_p not in obs_out:
                    obs_out.append(obs_p)
                break
    return own_out[:2], obs_out[:2]


_VOLUME_SLIP_TRAITS = frozenset({
    "jittery", "nervous", "clumsy", "impulsive", "volatile", "fiery", "reactive", "loud",
})


def compute_involuntary_volume_slip(
    intended_volume: str,
    autonomic: Dict[str, float],
    regulation_capacity: float,
    player: Any,
    *,
    overloaded: bool = False,
    suppressed: bool = False,
) -> Tuple[str, bool, str]:
    """Compute whether acute fluster/arousal causes an involuntary speech volume slip.

    Mirrors static/js/agent/involuntary.ts NERVOUS_TRAITS: an impulsive, fiery,
    or jittery character trying to whisper while flustered/overloaded can fail
    to drop their voice (whisper -> normal), letting someone nearby overhear.
    Returns ``(actual_volume, slipped, reason)``.
    """
    vol = (intended_volume or "normal").strip().lower()
    if vol not in ("whisper", "normal"):
        return vol, False, ""

    raw_traits = getattr(player, "traits", None) or {}
    trait_ids = {str(t).lower() for t in (raw_traits.keys() if isinstance(raw_traits, dict) else raw_traits)}
    pers_low = str(getattr(player, "personality", "") or "").lower()
    has_nervous_trait = bool(trait_ids & _VOLUME_SLIP_TRAITS) or any(
        w in pers_low for w in ("impulsive", "loud", "volatile", "fiery", "flustered")
    )
    is_composed = bool(trait_ids & {"stoic", "composed", "calm"}) and not overloaded

    hr = float(autonomic.get("heart_rate", 0.0))
    br = float(autonomic.get("breathing", 0.0))
    vaso = abs(float(autonomic.get("vasomotor", 0.0)))
    tens = float(autonomic.get("muscle_tension", 0.0))
    arousal_drive = (hr * 0.40) + (br * 0.25) + (vaso * 0.20) + (tens * 0.15)

    if vol == "whisper" and not is_composed:
        # Threshold drops when character carries impulsive/flustered traits or low regulation capacity.
        threshold = 34.0 if has_nervous_trait else 52.0
        if regulation_capacity <= 52.0:
            threshold -= 6.0
        if overloaded or arousal_drive >= threshold:
            return "normal", True, "flustered_volume_slip"

    if vol == "normal" and overloaded and not suppressed and not is_composed:
        if hr >= 62.0 and (tens >= 58.0 or has_nervous_trait):
            return "shout", True, "overloaded_voice_carry"

    return vol, False, ""


def render_own_body_prompt(
    state: CharacterEmotionState,
    player: Any,
    *,
    overloaded: bool,
    suppressed_families: List[str],
) -> str:
    """First-person embodied === YOUR STATE === prose (zero DBT labels, zero raw numbers)."""
    mode = species_autonomic_mode(player)
    if state.numbness_ticks > 0:
        return "You feel strangely hollow and detached, as if watching everything from behind thick glass."

    # Rank active raised families by deviation above baseline.
    raised: List[Tuple[float, str]] = []
    for fam in FAMILIES:
        over = state.families.get(fam, FAMILY_BASELINES[fam]) - FAMILY_BASELINES[fam]
        if over >= 14.0:
            raised.append((over, fam))
    raised.sort(reverse=True)

    auto = state.autonomic
    body_fragments: List[str] = []
    if mode == "humanoid":
        if auto.get("heart_rate", 0.0) >= 72.0:
            body_fragments.append("your heart hammers hard against your ribs")
        elif auto.get("heart_rate", 0.0) >= 48.0:
            body_fragments.append("your pulse beats fast and tight in your throat")
        elif auto.get("heart_rate", 0.0) >= 28.0:
            body_fragments.append("a restless flutter sits in your chest")

        vaso = auto.get("vasomotor", 0.0)
        if vaso >= 52.0:
            body_fragments.append("heat climbs across your cheeks and ears")
        elif vaso <= -42.0:
            body_fragments.append("your skin feels cold and drained of color")

        tens = auto.get("muscle_tension", 0.0)
        if tens >= 74.0:
            body_fragments.append("your jaw clamps tight and your hands tremble slightly as they curl into fists")
        elif tens >= 38.0:
            body_fragments.append("your jaw and shoulders lock tight")

        gut = auto.get("gut_throat", 0.0)
        if gut >= 60.0:
            body_fragments.append("a sick, heavy knot twists in your stomach and crowds your throat")
        elif gut >= 30.0:
            body_fragments.append("a tight knot sits in your gut")

        tears = auto.get("eyes_tears", 0.0)
        if tears >= 60.0:
            body_fragments.append("hot tears sting behind your eyes as if they might spill if you blink")
        elif tears >= 35.0:
            body_fragments.append("your eyes sting faintly")

        sc = auto.get("sweat_chills", 0.0)
        if sc <= -38.0:
            body_fragments.append("goosebumps prickle over your arms")
        elif sc >= 45.0:
            body_fragments.append("a clammy sheen breaks out on your palms")

        mt = auto.get("motor_tone", 0.0)
        if mt <= -45.0:
            body_fragments.append("your limbs feel heavy and dragged down")
        elif mt >= 45.0:
            body_fragments.append("restless, buoyant energy lifts through your chest")
    elif mode == "animal":
        if auto.get("sweat_chills", 0.0) <= -25.0 or auto.get("heart_rate", 0.0) >= 50.0:
            body_fragments.append("your hackles prickle upright and your ears pin back")
        if auto.get("muscle_tension", 0.0) >= 40.0:
            body_fragments.append("every muscle coils tight to spring or bolt")

    own_personal, _ = _match_personal_tells(
        player, state, overloaded=overloaded, suppressed_families=suppressed_families
    )
    if own_personal:
        body_fragments = own_personal[:1] + body_fragments

    if not raised and not body_fragments:
        return ""

    sentences: List[str] = []
    if body_fragments:
        picked = body_fragments[:3]
        if len(picked) == 1:
            line = picked[0][0].upper() + picked[0][1:] + "."
        else:
            line = picked[0][0].upper() + picked[0][1:] + ", " + ", and ".join(picked[1:]) + "."
        sentences.append(line)

    # Surface per-target feelings cleanly when contrasting targets exist (e.g., worried for A, angry at B).
    if state.target_families:
        tgt_bits: List[str] = []
        for tname, tfams in state.target_families.items():
            best_f = None
            best_v = 14.0
            for fam, val in tfams.items():
                over = float(val) - FAMILY_BASELINES.get(fam, 10.0)
                if fam != "calm" and over > best_v:
                    best_v = over
                    best_f = fam
            if best_f:
                tgt_bits.append(f"toward {tname}: {best_f}")
        if tgt_bits:
            sentences.append("Right now your feelings split by person (" + "; ".join(tgt_bits[:3]) + ").")

    # Blend urges from up to top 2 raised families so mixed emotions pull simultaneously.
    top_fams = [f for _, f in raised[:2]]
    if len(top_fams) == 1:
        prof = EMOTION_PROFILES[top_fams[0]]
        if prof["urge_phrase"]:
            sentences.append(prof["urge_phrase"][0].upper() + prof["urge_phrase"][1:] + ".")
    elif len(top_fams) >= 2:
        p1 = EMOTION_PROFILES[top_fams[0]]["urge_phrase"]
        p2 = EMOTION_PROFILES[top_fams[1]]["urge_phrase"]
        if p1 and p2:
            sentences.append(f"At the same time, {p1}, while {p2}.")

    if suppressed_families:
        sentences.append("Holding your face and voice flat is taking real effort.")

    if overloaded:
        sentences.append("Your thoughts scatter and it is hard to think clearly past the rush.")
    elif top_fams:
        tug = EMOTION_PROFILES[top_fams[0]].get("reasoning_tug", "")
        if tug and raised[0][0] >= 28.0:
            sentences.append(tug)

    return " ".join(sentences)


def render_observer_tells(
    state: CharacterEmotionState,
    player: Any,
    *,
    lighting: str = "normal",
    observer_insight: int = 10,
    familiarity: float = 0.0,
    overloaded: bool = False,
    suppressed_families: Optional[List[str]] = None,
) -> str:
    """Observable physical cues shown to another character in room-context.ts (People here:)."""
    mode = species_autonomic_mode(player)
    if mode == "none" or state.numbness_ticks > 0:
        return "expression unusually blank and distant" if state.numbness_ticks > 0 else ""

    auto = state.autonomic
    suppressed = bool(suppressed_families) and not overloaded
    perceptive = (observer_insight >= 13) or (familiarity >= 0.5)

    if lighting in ("pitch_black", "blind"):
        if auto.get("breathing", 0.0) >= 45.0 or overloaded:
            return "breathing sounds tight and unsteady in the dark"
        if auto.get("eyes_tears", 0.0) >= 55.0:
            return "a quiet, uneven sniffle breaks the silence"
        return ""

    if mode == "animal":
        cues = []
        if auto.get("heart_rate", 0.0) >= 45.0:
            cues.append("hackles raised, ears pinned")
        if auto.get("motor_tone", 0.0) <= -35.0:
            cues.append("tail tucked low")
        return ", ".join(cues)

    if lighting == "dim":
        cues = []
        if auto.get("muscle_tension", 0.0) >= 45.0:
            cues.append("posture rigid and coiled")
        elif auto.get("motor_tone", 0.0) <= -40.0:
            cues.append("shoulders slumped low")
        elif auto.get("motor_tone", 0.0) >= 45.0:
            cues.append("moving with light, restless energy")
        if auto.get("breathing", 0.0) >= 55.0:
            cues.append("chest rising with quick breaths")
        return ", ".join(cues)

    # Normal / bright light.
    raised = sorted(
        (
            (state.families.get(f, FAMILY_BASELINES[f]) - FAMILY_BASELINES[f], f)
            for f in FAMILIES
            if state.families.get(f, FAMILY_BASELINES[f]) - FAMILY_BASELINES[f] >= 16.0
        ),
        reverse=True,
    )

    _, obs_personal = _match_personal_tells(
        player, state, overloaded=overloaded, suppressed_families=suppressed_families
    )

    if suppressed:
        if not perceptive:
            return ""
        if obs_personal:
            return obs_personal[0]
        if raised:
            micro = EMOTION_PROFILES[raised[0][1]].get("masked_micro_tell", "")
            if micro:
                return micro
        return "keeping their expression carefully flat, though their posture stays stiff"

    # Build blended physical tells directly from autonomic channels (true even if emote is null).
    tells: List[str] = list(obs_personal[:1])
    vaso = auto.get("vasomotor", 0.0)
    if vaso >= 48.0:
        tells.append("cheeks and neck flushed hot")
    elif vaso <= -45.0:
        tells.append("face drained pale")

    tens = auto.get("muscle_tension", 0.0)
    if tens >= 68.0:
        tells.append("jaw clamped hard and hands trembling slightly in clenched fists")
    elif tens >= 40.0:
        tells.append("jaw set tight and hands tense")

    tears = auto.get("eyes_tears", 0.0)
    if tears >= 60.0:
        tells.append("eyes glossy with tears close to spilling")
    elif tears >= 35.0:
        tells.append("eyes red-rimmed and blinking fast")

    mt = auto.get("motor_tone", 0.0)
    if mt <= -48.0:
        tells.append("shoulders hunched and pulled inward")
    elif mt >= 48.0:
        tells.append("posture open and lively")

    if auto.get("breathing", 0.0) >= 55.0:
        tells.append("breathing visibly quick and shallow")
    if auto.get("gut_throat", 0.0) >= 65.0 and not tells:
        tells.append("looking queasy and swallowing hard")

    if tells:
        return ", ".join(tells[:3])

    if raised:
        over, fam = raised[0]
        bands = EMOTION_PROFILES[fam]["observable_tells"]
        idx = 0 if over >= 42.0 else (1 if over >= 26.0 else 2)
        return bands[idx]
    return ""


def render_vocal_interruption(
    speech: str,
    autonomic: Dict[str, float],
    *,
    overloaded: bool,
    is_human: bool = False,
    allow_human_rewrite: bool = False,
) -> Optional[str]:
    """Acute in-speech vocal break only (never appends duplicate physical emotes).

    Never silently rewrites a human player's typed dialogue unless explicitly allowed.
    """
    text = (speech or "").strip()
    if not text:
        return None
    if is_human and not allow_human_rewrite:
        return None

    breathing = float(autonomic.get("breathing", 0.0))
    throat = float(autonomic.get("gut_throat", 0.0))
    tears = float(autonomic.get("eyes_tears", 0.0))
    tension = float(autonomic.get("muscle_tension", 0.0))

    if not overloaded and max(breathing, throat, tears, tension) < 68.0:
        return None

    # Stutter on acute breathless/trembling overload.
    if breathing >= 68.0 or (overloaded and tension >= 70.0):
        m = re.match(r"^(\s*)([A-Za-z])([A-Za-z]*)(.*)$", text)
        if m:
            ws, ch, tail, rest = m.groups()
            head = f"{ch}-{ch}" if ch == "I" else f"{ch}-{ch.lower()}"
            return f"{ws}{head}{tail}{rest}"

    # Voice catch / choked pause on lump-in-throat or tears.
    if tears >= 62.0 or throat >= 65.0:
        idx = text.find(",")
        if idx == -1:
            idx = text.find(" ")
        if idx > 0:
            return f"{text[:idx]}... *voice catches* ...{text[idx:].lstrip()}"
        return f"{text} ...*voice catches*"

    return None
