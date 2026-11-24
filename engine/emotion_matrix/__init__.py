"""Production Coupled Emotional Matrix & 8-Channel Autonomic Body (task-1001).

Exports the 13-family coupled emotion model, per-target live overlays,
8-channel involuntary autonomic body with half-life inertia, persona
habit/quirk tell hooks, flustered volume slip, and 36-dim projection onto
``Player._emotions``.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from engine.emotion_matrix.schema import (
    AUTONOMIC_CHANNELS,
    CharacterEmotionState,
    EmotionEvent,
    EpisodeRecord,
    FAMILIES,
    FAMILY_BASELINES,
    MatrixStepResult,
)
from engine.emotion_matrix.autonomic import (
    compute_involuntary_volume_slip,
    compute_regulation_capacity,
    compute_vulnerability_load,
    render_observer_tells,
    render_own_body_prompt,
    update_autonomic,
)
from engine.emotion_matrix.coupling import (
    apply_matrix_step,
    apply_tick_decay,
)

# Reverse map from 36-dim production axis/dim names to the 13 Matrix families
# for lazy seeding when a Player already has values in Player._emotions.
_DIM_TO_FAMILY: Dict[str, str] = {
    "happy": "happiness",
    "excited": "happiness",
    "elated": "happiness",
    "proud": "happiness",
    "sad": "sadness",
    "lonely": "sadness",
    "melancholic": "sadness",
    "nostalgic": "sadness",
    "afraid": "fear",
    "anxious": "fear",
    "uneasy": "fear",
    "dread": "fear",
    "spooked": "fear",
    "angry": "anger",
    "irritated": "anger",
    "resentful": "anger",
    "aroused": "arousal",
    "eager": "arousal",
    "craving": "arousal",
    "curious": "arousal",
    "affectionate": "love",
    "loving": "love",
    "grateful": "love",
    "admiring": "love",
    "ashamed": "shame",
    "embarrassed": "shame",
    "guilty": "guilt",
    "envious": "envy",
    "jealous": "jealousy",
    "disgusted": "disgust",
    "repulsed": "disgust",
    "calm": "calm",
    "content": "calm",
    "peaceful": "calm",
    "satisfied": "calm",
    "surprised": "surprise",
}


def seed_state_from_emotions_map(emotions_map: Optional[Dict[str, Any]]) -> CharacterEmotionState:
    """Create a CharacterEmotionState seeded from an existing 36-dim _emotions map."""
    state = CharacterEmotionState()
    if not isinstance(emotions_map, dict):
        return state
    buckets: Dict[str, List[float]] = {}
    for dim, val in emotions_map.items():
        fam = _DIM_TO_FAMILY.get(str(dim).lower())
        if not fam:
            continue
        try:
            buckets.setdefault(fam, []).append(float(val))
        except (TypeError, ValueError):
            continue
    for fam, vals in buckets.items():
        if vals:
            # Take the strongest deviation from baseline in this family
            base = FAMILY_BASELINES.get(fam, 10.0)
            best = max(vals, key=lambda v: abs(v - base))
            state.families[fam] = max(0.0, min(100.0, best))
    return state


def serialize_matrix_state(state: Optional[CharacterEmotionState]) -> Optional[Dict[str, Any]]:
    """Serialize CharacterEmotionState to a JSON-safe dict for saves and API payloads."""
    if state is None:
        return None
    return {
        "families": {k: round(float(v), 2) for k, v in state.families.items()},
        "autonomic": {ch: round(float(state.autonomic.get(ch, 0.0)), 2) for ch in AUTONOMIC_CHANNELS},
        "target_families": {
            tgt: {fam: round(float(val), 2) for fam, val in fams.items()}
            for tgt, fams in (state.target_families or {}).items()
            if fams
        },
        "overload_streak": int(state.overload_streak),
        "numbness_ticks": int(getattr(state, "numbness_ticks", 0)),
        "episodes": [
            {
                "id": str(ep.id),
                "tick": int(ep.tick),
                "family": ep.family,
                "peak_delta": round(float(ep.peak_delta), 2),
                "prompting_event": dict(ep.prompting_event or {}),
                "appraisal": str(ep.appraisal or ""),
                "urges": list(ep.urges or []),
                "target_name": ep.target_name,
            }
            for ep in (state.episodes or [])[-12:]
        ],
    }


def deserialize_matrix_state(data: Optional[Dict[str, Any]]) -> Optional[CharacterEmotionState]:
    """Restore CharacterEmotionState from a serialized dict."""
    if not isinstance(data, dict):
        return None
    state = CharacterEmotionState()
    fams = data.get("families")
    if isinstance(fams, dict):
        for fam in FAMILIES:
            if fam in fams:
                try:
                    state.families[fam] = max(0.0, min(100.0, float(fams[fam])))
                except (TypeError, ValueError):
                    pass
    auto = data.get("autonomic")
    if isinstance(auto, dict):
        for ch in AUTONOMIC_CHANNELS:
            if ch in auto:
                try:
                    state.autonomic[ch] = max(-100.0, min(100.0, float(auto[ch])))
                except (TypeError, ValueError):
                    pass
    tfams = data.get("target_families")
    if isinstance(tfams, dict):
        for tgt, fdict in tfams.items():
            if isinstance(fdict, dict):
                cleaned: Dict[str, float] = {}
                for fam, val in fdict.items():
                    if fam in FAMILIES:
                        try:
                            cleaned[fam] = max(0.0, min(100.0, float(val)))
                        except (TypeError, ValueError):
                            pass
                if cleaned:
                    state.target_families[str(tgt)] = cleaned
    try:
        state.overload_streak = int(data.get("overload_streak", 0))
    except (TypeError, ValueError):
        state.overload_streak = 0
    try:
        state.numbness_ticks = int(data.get("numbness_ticks", 0))
    except (TypeError, ValueError):
        state.numbness_ticks = 0
    eps = data.get("episodes")
    if isinstance(eps, list):
        restored: List[EpisodeRecord] = []
        for ep in eps[-12:]:
            if not isinstance(ep, dict):
                continue
            try:
                restored.append(
                    EpisodeRecord(
                        id=str(ep.get("id", f"ep_{ep.get('tick', 0)}")),
                        tick=int(ep.get("tick", 0)),
                        family=str(ep.get("family", "neutral")),
                        peak_delta=float(ep.get("peak_delta", 0.0)),
                        prompting_event=dict(ep.get("prompting_event") or {}),
                        appraisal=str(ep.get("appraisal", "")),
                        urges=list(ep.get("urges") or []),
                        target_name=ep.get("target_name"),
                    )
                )
            except (TypeError, ValueError):
                continue
        state.episodes = restored
    return state


__all__ = [
    "AUTONOMIC_CHANNELS",
    "CharacterEmotionState",
    "EmotionEvent",
    "EpisodeRecord",
    "FAMILIES",
    "FAMILY_BASELINES",
    "MatrixStepResult",
    "apply_matrix_step",
    "apply_tick_decay",
    "compute_involuntary_volume_slip",
    "compute_regulation_capacity",
    "compute_vulnerability_load",
    "deserialize_matrix_state",
    "render_observer_tells",
    "render_own_body_prompt",
    "seed_state_from_emotions_map",
    "serialize_matrix_state",
    "update_autonomic",
]
