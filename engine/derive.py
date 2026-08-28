"""Experience-driven relationship derivation (task-350).

The relationship store holds a single blunt closeness scalar. This
module derives a *richer, per-person* read of a relationship from the
two things that actually carry information:

  - player.memories (the experience store). Any memory tagged with
    rel:<other> contributes to that person profile; per-dimension tags
    (trust:-3, fear:+2, attraction:+1 ...) carry the direction and
    magnitude, weighted by the memory importance (1-10) and any live
    salience_override (surfaced memories weigh more).
  - player.relationships[other] (a seed): closeness and interaction_count
    (re: familiarity) still feed the profile, so the system degrades
    gracefully and never loses existing data.

The result is a Profile (a plain dict of derived dimensions) that game
systems read to *gate* actions, and that the prompt builder renders as a
natural-language read for the agent. NO LLM is involved in the derivation;
the LLM only supplies the raw felt-emotion (see Player.felt_toward), which
is recorded as a tagged memory and folded back in here.

Dimensions (clamped to [-100, 100]): trust, fear, attraction, familiarity,
disgust, respect, closeness.

Derived views:
  consent  (-1..1) - will they let this person close? (trust - fear)/80
  moodToward       - current affect toward this person (0..1)
  role             - inferred kind: parent / lover / friend / rival /
                     creep / stranger (structurally distinct, not a scalar)
  summary          - one natural-language line for the prompt
"""

from __future__ import annotations

from typing import Optional

DIMS: tuple[str, ...] = (
    "trust", "fear", "attraction", "familiarity", "disgust", "respect", "closeness",
)

CONSENT_SCALE = 80.0

SIGNAL_DIMS = ("trust", "fear", "attraction", "disgust", "respect")


def _fresh() -> dict:
    return {"trust": 0.0, "fear": 0.0, "attraction": 0.0,
            "familiarity": 0.0, "disgust": 0.0, "respect": 0.0, "closeness": 0.0}


def clamp(v: float, lo: float = -100.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v)))



#: Max magnitude the engine will accept for a single `emotions.data` delta
#: (task-350 memory-driven feelings). The LLM picks the flavor + size; the
#: engine clamps here so the model can never set an unbounded number.
EMOTION_DELTA_MAX = 5.0

#: `emotions.data` key (as the LLM writes it) -> (derive dimension, scale).
#: Negative-emotion keys are flipped onto the dimension direction (anger
#: erodes trust, so a positive `anger` value LOWERS trust).
DATA_KEY_TO_DIM = {
    "fear": ("fear", 1.0),
    "afraid": ("fear", 1.0),
    "disgust": ("disgust", 1.0),
    "disgusted": ("disgust", 1.0),
    "affection": ("attraction", 1.0),
    "affectionate": ("attraction", 1.0),
    "attraction": ("attraction", 1.0),
    "trust": ("trust", 1.0),
    "familiarity": ("familiarity", 1.0),
    "respect": ("respect", 1.0),
    "anger": ("trust", -1.0),
    "envy": ("trust", -0.7),
    "closeness": ("closeness", 1.0),
}


def expand_emotion_data(data: dict):
    """Normalize an `emotions.data` map into [(derive_dim, clamped_delta), ...].

    Clamps each delta to +/-EMOTION_DELTA_MAX and maps the LLM key onto the
    right derive dimension + direction. Unknown keys are dropped. This is the
    engine-owned boundary: the model picks flavor/size, the engine bounds + maps.
    """
    out = []
    for key, raw in (data or {}).items():
        key = str(key).strip().lower()
        mapped = DATA_KEY_TO_DIM.get(key)
        if not mapped:
            continue
        dim, scale = mapped
        try:
            delta = clamp(float(raw), -EMOTION_DELTA_MAX, EMOTION_DELTA_MAX) * scale
        except (TypeError, ValueError):
            continue
        out.append((dim, delta))
    return out


def fold_emotions_into_profile(profile: dict, memory: dict, other_name: str) -> bool:
    """Fold a memory's structured `emotions:{who,data}` into the profile.

    Mirrors `_memory_for`'s tag path but reads the structured block directly,
    so a memory stored with `emotions` (not only rel:/dim: tags) still moves the
    mechanically relevant dimensions. Returns True when it contributed.
    """
    mem = memory or {}
    emo = mem.get("emotions") or {}
    who = str(emo.get("who") or "").strip().lower()
    about = (who == other_name.lower()) or any(
        str(t).lower().startswith("rel:") and str(t)[4:].lower() == other_name.lower()
        for t in (mem.get("tags") or [])
    )
    if not about:
        return False
    weight = float(mem.get("importance", 5))
    salience = int(mem.get("salience_override", 0) or 0)
    if salience:
        weight *= 1.0 + salience / 3.0
    found = False
    for dim, delta in expand_emotion_data(emo.get("data")):
        if dim in profile:
            profile[dim] += delta * weight
            found = True
    return found

def _memory_for(profile: dict, memory: dict, other_name: str) -> bool:
    """Fold one memory into profile if it is about other_name.

    Returns True when the memory was relevant (so callers can detect signal).
    """
    tags = memory.get("tags") or []
    rel_match = any(
        str(t).lower().startswith("rel:") and str(t)[4:].lower() == other_name.lower()
        for t in tags
    )
    if not rel_match:
        return False
    weight = float(memory.get("importance", 5))
    salience = int(memory.get("salience_override", 0) or 0)
    if salience:
        weight *= 1.0 + salience / 3.0
    found = False
    for t in tags:
        t = str(t).lower()
        for dim in DIMS:
            if t.startswith(dim + ":"):
                try:
                    profile[dim] += float(t.split(":", 1)[1]) * weight
                except (TypeError, ValueError):
                    continue
                found = True
    return found


def derive_person_profile(player, other_name: str) -> dict:
    """Build the derived profile of player relationship toward other_name.

    Pure, deterministic, no LLM. Reads player.memories / player.relationships.
    """
    profile = _fresh()
    has_signal = False
    rel = (getattr(player, "relationships", None) or {}).get(other_name)
    if rel:
        profile["closeness"] = clamp(float(rel.get("closeness", 0)))
        profile["familiarity"] = clamp(float(rel.get("interaction_count", 0)) * 2.0)

    for memory in (getattr(player, "memories", None) or []):
        tag_hit = _memory_for(profile, memory, other_name)
        emo_hit = fold_emotions_into_profile(profile, memory, other_name)
        if tag_hit or emo_hit:
            has_signal = True

    profile["_has_signal"] = has_signal and any(
        abs(profile[d]) > 1e-6 for d in SIGNAL_DIMS
    )
    return finalize(profile, player)


def finalize(profile: dict, player=None) -> dict:
    """Clamp dims and derive the consent / mood / role / summary views."""
    for k in DIMS:
        profile[k] = clamp(profile[k])
    trust = profile.get("trust", 0.0)
    fear = profile.get("fear", 0.0)
    profile["consent"] = clamp((trust - fear) / CONSENT_SCALE, -1.0, 1.0)

    emo = (player.emotions_map()) if player is not None and hasattr(player, "emotions_map") else {}
    toward = emo.get("afraid", 0.0)
    toward = max(toward, emo.get("disgusted", 0.0))
    toward = max(toward, emo.get("affectionate", 0.0))
    profile["moodToward"] = clamp(toward / 100.0, 0.0, 1.0)

    profile["role"] = _infer_role(profile)
    profile["summary"] = _to_nl(profile)
    return profile


def _infer_role(profile: dict) -> str:
    """Infer a structurally distinct role from the dimensions.

    A creep (high attraction, low trust) is structurally different from a
    lover (high attraction AND high trust) - different dimensions, not
    different points on one scalar.
    """
    trust = profile.get("trust", 0.0)
    fear = profile.get("fear", 0.0)
    disgust = profile.get("disgust", 0.0)
    attraction = profile.get("attraction", 0.0)
    familiarity = profile.get("familiarity", 0.0)

    if fear >= 25 or disgust >= 25:
        return "hostile"
    if trust >= 50 and attraction >= 40:
        return "lover"
    if trust >= 20 and familiarity >= 5:
        return "friend"
    if attraction >= 30 and trust < 10:
        return "creep"
    if trust <= -15:
        return "rival"
    if familiarity >= 10:
        return "acquaintance"
    return "stranger"


def _to_nl(profile: dict) -> str:
    """One natural-language line the prompt builder can hand the agent.

    The agent never sees raw numbers - only a qualitative read the engine
    computed. This is the only output that crosses into the prompt.
    """
    parts = []
    c = profile.get("consent", 0.0)
    if c <= -0.25:
        parts.append("you would pull away from this person")
    elif c >= 0.25:
        parts.append("you would let this person close")
    trust = profile.get("trust", 0.0)
    if trust >= 25:
        parts.append("you trust them")
    elif trust <= -15:
        parts.append("you do not trust them")
    fear = profile.get("fear", 0.0)
    if fear >= 15:
        parts.append("they unsettle you")
    dis = profile.get("disgust", 0.0)
    if dis >= 15:
        parts.append("they turn your stomach")
    parts.append("(" + profile["role"] + ")")
    return "; ".join(parts) if parts else "no strong feelings yet"


def relationship_block(player, other_name: str) -> str:
    """Prompt-surface block for this relationship (agent-facing)."""
    profile = derive_person_profile(player, other_name)
    return "Your read on " + other_name + ": " + profile["summary"] + ". (" + profile["role"] + ")"
