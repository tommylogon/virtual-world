"""Multi-dimensional character affect (task-96).

Each character carries a map of emotion dimensions on a 0-100 scale::

    {"happy": 55, "sad": 8, "afraid": 30, "angry": 12, ...}

Design notes (deliberate departures from F:\\AI\\Aura\\Diary):
  - Affect only. Energy/social needs already live in vitals/closeness here,
    so the dimension set is purely emotional.
  - Values drift toward a per-dimension BASELINE each tick instead of
    decaying toward zero, so calm is a state, not an absence.
  - Prompt rendering uses first-person band phrases (Diary-style range
    tables) so the LLM feels mood without seeing raw numbers.

Tunables come from ``engine/runtime_config`` at call time (task-304 rule):
``emotion.decay_per_tick``, ``emotion.recall_spike_scale``,
``emotion.llm_spike_max``.
"""

from __future__ import annotations

from engine.runtime_config import config as runtime_config

#: Dimension -> neutral resting level (0-100).
#: Note: the OLD 7 (happy/sad/afraid/angry/envious/affectionate/disgusted) are
#: preserved, and a richer set of sub-emotions is layered on top so creative
#: labels can register on the affect map instead of being silently dropped.
BASELINES: dict[str, float] = {
    # JOY
    "happy": 40.0, "excited": 30.0, "elated": 22.0, "proud": 30.0,
    # SADNESS
    "sad": 8.0, "lonely": 10.0, "melancholic": 12.0, "nostalgic": 18.0,
    # FEAR
    "afraid": 10.0, "anxious": 12.0, "uneasy": 12.0, "dread": 8.0, "spooked": 10.0,
    # ANGER
    "angry": 8.0, "irritated": 12.0, "resentful": 10.0,
    # AROUSAL
    "aroused": 12.0, "eager": 26.0, "craving": 15.0, "curious": 35.0,
    # BOND
    "affectionate": 25.0, "loving": 26.0, "grateful": 24.0, "admiring": 30.0,
    # SHAME
    "ashamed": 8.0, "embarrassed": 10.0, "guilty": 8.0,
    # ENVY
    "envious": 5.0, "jealous": 8.0,
    # DISGUST
    "disgusted": 5.0, "repulsed": 5.0,
    # CALM
    "calm": 50.0, "content": 46.0, "peaceful": 46.0, "satisfied": 40.0,
    # SURPRISE
    "surprised": 15.0,
}

#: Dimension -> axis group (for UI grouping and generic phrasing).
AXES: dict[str, str] = {
    "happy": "joy", "excited": "joy", "elated": "joy", "proud": "joy",
    "sad": "sadness", "lonely": "sadness", "melancholic": "sadness", "nostalgic": "sadness",
    "afraid": "fear", "anxious": "fear", "uneasy": "fear", "dread": "fear", "spooked": "fear",
    "angry": "anger", "irritated": "anger", "resentful": "anger",
    "aroused": "arousal", "eager": "arousal", "craving": "arousal", "curious": "arousal",
    "affectionate": "bond", "loving": "bond", "grateful": "bond", "admiring": "bond",
    "ashamed": "shame", "embarrassed": "shame", "guilty": "shame",
    "envious": "envy", "jealous": "envy",
    "disgusted": "disgust", "repulsed": "disgust",
    "calm": "calm", "content": "calm", "peaceful": "calm", "satisfied": "calm",
    "surprised": "surprise",
}

#: Dimension -> (vital, per-point factor). Recalled memory emotions nudge the
#: matching mental vital subtly (Sanity / Entertainment / Social). A negative
#: factor drains; a positive restores.
VITAL_EFFECTS: dict[str, tuple[str, float]] = {
    "happy": ("Entertainment", 0.35), "excited": ("Entertainment", 0.35),
    "elated": ("Entertainment", 0.35), "proud": ("Social", 0.20),
    "sad": ("Social", -0.25), "lonely": ("Social", -0.40),
    "melancholic": ("Sanity", -0.20), "nostalgic": ("Entertainment", 0.15),
    "afraid": ("Sanity", -0.35), "anxious": ("Sanity", -0.30),
    "uneasy": ("Sanity", -0.25), "dread": ("Sanity", -0.35), "spooked": ("Sanity", -0.30),
    "angry": ("Sanity", -0.20), "irritated": ("Sanity", -0.15), "resentful": ("Sanity", -0.20),
    "aroused": ("Entertainment", 0.15), "eager": ("Entertainment", 0.20),
    "craving": ("Entertainment", 0.10), "curious": ("Entertainment", 0.20),
    "affectionate": ("Social", 0.30), "loving": ("Social", 0.30),
    "grateful": ("Social", 0.25), "admiring": ("Social", 0.25),
    "ashamed": ("Sanity", -0.25), "embarrassed": ("Sanity", -0.20), "guilty": ("Sanity", -0.25),
    "envious": ("Social", -0.15), "jealous": ("Social", -0.20),
    "disgusted": ("Sanity", -0.15), "repulsed": ("Sanity", -0.15),
    "calm": ("Sanity", 0.25), "content": ("Entertainment", 0.15),
    "peaceful": ("Sanity", 0.25), "satisfied": ("Entertainment", 0.20),
    "surprised": ("Entertainment", 0.10),
}

#: Rich label vocabulary -> closest affect dimension. Covers the editor/generator
#: word list so every label maps somewhere sensible. Novel agent labels that are
#: not here fall back to semantic embedding (client-side) or are a graceful no-op.
LABEL_TO_DIM: dict[str, str] = {
    "neutral": "calm",
    "happy": "happy", "glad": "happy", "joy": "happy", "delighted": "happy",
    "elated": "elated", "excited": "excited", "thrilled": "excited", "mischievous": "excited",
    "proud": "proud",
    "sad": "sad", "down": "sad", "melancholic": "melancholic", "wistful": "melancholic",
    "lonely": "lonely", "nostalgic": "nostalgic", "bored": "melancholic", "tired": "melancholic", "hollow": "melancholic",
    "afraid": "afraid", "fear": "afraid", "scared": "afraid", "terrified": "afraid", "frightened": "afraid", "panic": "afraid",
    "anxious": "anxious", "nervous": "anxious", "worried": "anxious", "restless": "anxious", "paranoid": "anxious",
    "uneasy": "uneasy", "unnerved": "uneasy", "spooked": "spooked", "dread": "dread",
    "angry": "angry", "mad": "angry", "furious": "angry", "irritated": "irritated", "frustrated": "irritated",
    "resentful": "resentful", "bitter": "resentful", "defiant": "angry",
    "aroused": "aroused", "eager": "eager", "craving": "craving", "hungry": "craving", "curious": "curious",
    "affectionate": "affectionate", "loving": "loving", "grateful": "grateful", "admiring": "admiring",
    "ashamed": "ashamed", "embarrassed": "embarrassed", "guilty": "guilty",
    "envious": "envious", "jealous": "jealous",
    "disgusted": "disgusted", "repulsed": "repulsed",
    "calm": "calm", "content": "content", "peaceful": "peaceful", "satisfied": "satisfied",
    "relieved": "calm", "safe": "calm", "quiet": "calm",
    "determined": "excited", "brave": "proud", "resolute": "excited", "focused": "content",
    "surprised": "surprised",
}

#: Dimension -> (relationship drive, sign factor). Used when a socially-recalled
#: memory shifts the listener's relationship toward the speaker. Drives match the
#: derived profile names (trust / fear / disgust / attraction). A positive factor
#: moves the drive up; negative moves it down.
RELATIONSHIP_VALENCE: dict[str, tuple[str, float]] = {
    "affectionate": ("trust", 0.5), "loving": ("trust", 0.5),
    "grateful": ("trust", 0.5), "admiring": ("trust", 0.4), "proud": ("trust", 0.3),
    "happy": ("trust", 0.2), "excited": ("trust", 0.15), "elated": ("trust", 0.2),
    "content": ("trust", 0.1), "satisfied": ("trust", 0.1), "calm": ("trust", 0.1), "peaceful": ("trust", 0.1),
    "nostalgic": ("trust", 0.2), "curious": ("trust", 0.1),
    "afraid": ("fear", 0.5), "anxious": ("fear", 0.4), "uneasy": ("fear", 0.35),
    "dread": ("fear", 0.5), "spooked": ("fear", 0.4),
    "angry": ("trust", -0.5), "irritated": ("trust", -0.3), "resentful": ("trust", -0.4),
    "envious": ("trust", -0.3), "jealous": ("trust", -0.4),
    "disgusted": ("disgust", 0.5), "repulsed": ("disgust", 0.5),
    "ashamed": ("trust", 0.3), "embarrassed": ("trust", 0.3), "guilty": ("trust", 0.3),
    "aroused": ("attraction", 0.6),
    "lonely": ("trust", 0.1), "melancholic": ("trust", 0.1), "sad": ("trust", 0.1),
    "eager": ("trust", 0.1), "craving": ("trust", 0.05), "surprised": ("trust", 0.1),
}

#: How far above baseline a dimension must sit before it is worth narrating.
#: Below-baseline dips use half this gate (a missing feeling still reads).
SPEAK_THRESHOLD = 18.0

#: First-person band phrases, high → low deviation. Index 0 = strongest.
_BANDS: dict[str, tuple[str, str, str]] = {
    "happy": (
        "You are elated — everything feels bright and possible.",
        "You feel genuinely happy.",
        "There is a quiet warmth in you.",
    ),
    "sad": (
        "You are crushed by sorrow — it takes effort just to stay upright.",
        "A heavy sadness sits on you.",
        "You feel low, a dull ache behind everything.",
    ),
    "afraid": (
        "You are terrified — your heart hammers and every shadow moves.",
        "You are afraid, watchful and tense.",
        "A nervous dread you can't quite name lingers.",
    ),
    "angry": (
        "You are livid — it takes everything not to lash out.",
        "Anger simmers in you, hot and close.",
        "You are irritated, shorter-tempered than usual.",
    ),
    "envious": (
        "Envy burns in you — what they have should be yours.",
        "You feel envious, acutely aware of what you lack.",
        "A small jealous pang colors how you look at others.",
    ),
    "affectionate": (
        "Warmth floods you — you want to be close to someone, now.",
        "You feel affectionate and open.",
        "You feel a gentle fondness toward those around you.",
    ),
    "disgusted": (
        "Disgust churns in you — you want it AWAY from you.",
        "You are repulsed and keep your distance.",
        "Something here turns your stomach slightly.",
    ),
    "calm": (
        "You are utterly at peace — nothing touches you.",
        "A deep calm settles over you.",
        "You feel pleasantly calm.",
    ),
}


def baseline() -> dict[str, float]:
    """A fresh neutral emotion map (copy — safe to mutate/store)."""
    return dict(BASELINES)


def normalize(values: dict | None) -> dict[str, float]:
    """Coerce a stored map into a complete, clamped dimension map."""
    out = baseline()
    for key, value in (values or {}).items():
        if key in out:
            try:
                out[key] = max(0.0, min(100.0, float(value)))
            except (TypeError, ValueError):
                continue
    return out


def spike(values: dict, emotion: str, delta: float) -> dict[str, float]:
    """Apply ``delta`` to one dimension, clamped. Returns the mutated map."""
    if emotion not in values:
        return values
    try:
        delta = float(delta)
    except (TypeError, ValueError):
        return values
    values[emotion] = max(0.0, min(100.0, values[emotion] + delta))
    return values


def decay(values: dict, per_tick: float | None = None) -> dict[str, float]:
    """Drift every dimension toward its baseline by ``per_tick`` points."""
    if per_tick is None:
        per_tick = float(runtime_config.get("emotion.decay_per_tick", 1.5))
    rate = max(0.0, float(per_tick))
    for key, base in BASELINES.items():
        current = values.get(key, base)
        if current > base:
            values[key] = max(base, current - rate)
        elif current < base:
            values[key] = min(base, current + rate)
    return values


def dominant(values: dict) -> tuple[str, float]:
    """The most deviant-from-baseline dimension and its deviation."""
    best_key, best_dev = "", 0.0
    for key, base in BASELINES.items():
        dev = abs(values.get(key, base) - base)
        if dev > best_dev:
            best_key, best_dev = key, dev
    return best_key, best_dev


def derive_from_vitals(vitals: dict, state: str = "") -> dict | None:
    """task-142: build a provisional affect map from physical/vital signals.

    Returns a point-spiked map (ready for :func:`describe`) when at least one
    signal deviates, or None when the character is asleep/unconscious or has no
    meaningful physical pressures.

    Signal thresholds follow the *current* vital semantics (task-337 flip):
    Hunger/Thirst/Bladder are DRIVES that FILL toward 100 (so "desperate" is
    HIGH, not low); Energy/Hygiene/etc. are resources that DRAIN toward 0.
    """
    if vitals is None:
        return None
    state = str(state or "")
    if state == "dead":
        # Detached, calm — a ghost pov (the living rarely see it).
        return {"calm": 80.0}
    if state in ("unconscious", "sleeping"):
        # Asleep (or under) — no mood worth narrating mid-sleep.
        return None

    try:
        def _low(resource: str, threshold: float) -> bool:
            return float(vitals.get(resource, 100)) <= threshold

        def _high(drive: str, threshold: float) -> bool:
            return float(vitals.get(drive, 0)) >= threshold

        temp = float(vitals.get("Temperature", 37.0))
        moves: list[tuple[str, float]] = []
        if _low("Energy", 25):
            moves.append(("irritated", 22))
            moves.append(("melancholic", 12))
        if _high("Hunger", 75):
            moves.append(("craving", 20))
            moves.append(("anxious", 12))
        if _high("Thirst", 75):
            moves.append(("anxious", 18))
        if _low("Entertainment", 25):
            moves.append(("melancholic", 16))
        if _low("Sanity", 25):
            moves.append(("anxious", 24))
        if temp < 35:
            moves.append(("uneasy", 18))
        elif temp > 38:
            moves.append(("irritated", 18))
        if _high("Bladder", 75):
            moves.append(("irritated", 12))
            moves.append(("anxious", 8))
        if _low("HP", 50):
            moves.append(("afraid", 18))
        if not moves:
            return None
    except (TypeError, ValueError):
        return None

    out = baseline()
    for dim, points in moves:
        spike(out, dim, points)
    return out


def describe(values: dict) -> str:
    """First-person mood paragraph, or '' when everything is near-neutral.

    N4: only the TWO most-deviant dimensions narrate (dominant + one
    secondary), so a slightly-shifted multi-dimension map reads "nervous,
    and a little hopeful" instead of a three-line list of faint stirrings.
    """
    scored = []
    for key, base in BASELINES.items():
        value = values.get(key, base)
        dev = value - base
        magnitude = abs(dev)
        if magnitude < SPEAK_THRESHOLD:
            continue
        scored.append((magnitude, dev, key))
    if not scored:
        return ""
    scored.sort(key=lambda t: -t[0])
    phrases = []
    for magnitude, dev, key in scored[:2]:
        bands = _BANDS.get(key) or _generic_bands(key)
        idx = 0 if magnitude >= 45 else (1 if magnitude >= 30 else 2)
        phrase = bands[idx]
        if dev < 0:
            phrase = _absence_phrase(key)
        phrases.append(phrase)
    if not phrases:
        return ""
    if len(phrases) == 1:
        return phrases[0]
    return phrases[0] + " Also, " + phrases[1][0].lower() + phrases[1][1:]


_ABSENCE: dict[str, str] = {
    "happy": "Happiness feels far away right now.",
    "sad": "Whatever weighed you down has lifted.",
    "afraid": "The fear has drained out of you.",
    "angry": "Your anger has cooled.",
    "envious": "You feel strangely free of jealousy.",
    "affectionate": "You feel emotionally numb, distant from everyone.",
    "disgusted": "Whatever disgusted you has passed.",
}


def _absence_phrase(key: str) -> str:
    return _ABSENCE.get(key, "")


def _generic_bands(key: str) -> tuple[str, str, str]:
    """Fallback narrative for dimensions without hand-written bands."""
    return (
        f"You feel {key} with unusual intensity.",
        f"A strong sense of {key} weighs on you.",
        f"You feel a faint stirring of {key}.",
    )


def map_label(label) -> list[tuple[str, float]]:
    """Map an emotion label to one or more (dimension, weight) pairs.

    Exact match first, then substring containment over the curated vocabulary.
    Returns [] for truly unknown labels (a graceful no-op) so creative or
    agent-invented labels never crash the emotion path.
    """
    if not label:
        return []
    key = str(label).strip().lower()
    if not key:
        return []
    if key in LABEL_TO_DIM:
        return [(LABEL_TO_DIM[key], 1.0)]
    for lab, dim in LABEL_TO_DIM.items():
        if lab in key or key in lab:
            return [(dim, 1.0)]
    return []


def felt_from_llm(raw, max_intensity: float | None = None) -> tuple[str, float] | None:
    """Normalize an LLM-declared ``{"label","intensity"}`` into (dim, delta).

    Returns None when unusable. Intensity 1-10 maps to a capped point spike
    (``emotion.llm_spike_max``); unknown labels are ignored so a creative LLM
    can't invent dimensions.
    """
    if not isinstance(raw, dict):
        return None
    label = str(raw.get("label") or "").strip().lower()
    if label not in BASELINES:
        return None
    try:
        intensity = float(raw.get("intensity") or 0)
    except (TypeError, ValueError):
        return None
    intensity = max(0.0, min(10.0, intensity))
    if intensity <= 0:
        return None
    if max_intensity is None:
        max_intensity = float(runtime_config.get("emotion.llm_spike_max", 15.0))
    return label, round(max_intensity * (intensity / 10.0), 2)
