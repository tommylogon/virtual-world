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
BASELINES: dict[str, float] = {
    "happy": 40.0,
    "sad": 8.0,
    "afraid": 10.0,
    "angry": 8.0,
    "envious": 5.0,
    "affectionate": 25.0,
    "disgusted": 5.0,
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


def describe(values: dict) -> str:
    """First-person mood paragraph, or '' when everything is near-neutral."""
    lines = []
    for key, base in BASELINES.items():
        value = values.get(key, base)
        dev = value - base
        magnitude = abs(dev)
        if magnitude < SPEAK_THRESHOLD:
            continue
        bands = _BANDS[key]
        # Stronger deviations pick earlier (more intense) phrases; dips into
        # a NEGATIVE reading of positive dims get their own phrasing below.
        idx = 0 if magnitude >= 45 else (1 if magnitude >= 30 else 2)
        phrase = bands[idx]
        if dev < 0:
            phrase = _absence_phrase(key)
        lines.append(phrase)
    return " ".join(lines)


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
