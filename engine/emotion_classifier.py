"""Optional zero-VRAM CPU emotion classifier for Track 1 appraisal (task-1001).

Wraps ``cirimus/modernbert-base-go-emotions`` (149M, ~72-86 ms median on CPU,
0 VRAM) or ``SamLowe/roberta-base-go_emotions`` (125M, ~55 ms CPU) and feeds
calibrated GoEmotions probabilities + Tier 1 structural guards into the
13-family Coupled Emotional Matrix (``engine/emotion_matrix``).

Controlled by ``runtime_config.get("emotion.classifier_backend", "none")``:
  - ``"none"`` (default): disabled, zero ML imports or model loads.
  - ``"modernbert"``: ``cirimus/modernbert-base-go-emotions`` on CPU.
  - ``"roberta"``: ``SamLowe/roberta-base-go_emotions`` on CPU.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from engine.emotion_matrix.coupling import apply_matrix_step
from engine.emotion_matrix.schema import (
    CharacterEmotionState,
    EmotionEvent,
    FAMILIES,
    MatrixStepResult,
)
from engine.runtime_config import config as runtime_config

logger = logging.getLogger(__name__)

# 28 GoEmotions labels -> weighted projection onto our 13 Matrix families.
GO_EMOTIONS_TO_FAMILY: Dict[str, List[Tuple[str, float]]] = {
    "admiration": [("love", 0.7), ("happiness", 0.4)],
    "amusement": [("happiness", 0.85), ("calm", 0.2)],
    "anger": [("anger", 1.0)],
    "annoyance": [("anger", 0.65)],
    "approval": [("calm", 0.35), ("happiness", 0.35), ("love", 0.2)],
    "caring": [("love", 0.85), ("calm", 0.45)],
    "confusion": [("surprise", 0.45), ("fear", 0.25)],
    "curiosity": [("surprise", 0.4), ("fear", 0.2)],
    "desire": [("arousal", 0.8), ("love", 0.25)],
    "disappointment": [("sadness", 0.85)],
    "disapproval": [("anger", 0.45), ("disgust", 0.4), ("shame", 0.2)],
    "disgust": [("disgust", 1.0)],
    "embarrassment": [("shame", 1.0)],
    "excitement": [("happiness", 0.8), ("arousal", 0.55)],
    "fear": [("fear", 1.0)],
    "gratitude": [("love", 0.65), ("happiness", 0.55), ("calm", 0.3)],
    "grief": [("sadness", 1.0)],
    "joy": [("happiness", 1.0)],
    "love": [("love", 1.0), ("happiness", 0.35)],
    "nervousness": [("fear", 0.85)],
    "optimism": [("happiness", 0.55), ("calm", 0.4)],
    "pride": [("happiness", 0.7), ("calm", 0.25)],
    "realization": [("surprise", 0.75)],
    "relief": [("calm", 0.95), ("happiness", 0.3)],
    "remorse": [("guilt", 1.0), ("shame", 0.45)],
    "sadness": [("sadness", 1.0)],
    "surprise": [("surprise", 1.0)],
    "neutral": [],
}

_MODEL_ALIASES: Dict[str, str] = {
    "modernbert": "cirimus/modernbert-base-go-emotions",
    "roberta": "SamLowe/roberta-base-go_emotions",
}


class GoEmotionsCPUBackend:
    """Lazy-loaded CPU-only GoEmotions sequence classifier (0 VRAM)."""

    def __init__(self, model_id: str = "cirimus/modernbert-base-go-emotions") -> None:
        self.model_id = model_id
        self._pipe = None
        self._load_failed = False

    def _ensure_loaded(self) -> bool:
        if self._pipe is not None:
            return True
        if self._load_failed:
            return False
        try:
            from transformers import pipeline
            self._pipe = pipeline(
                "text-classification",
                model=self.model_id,
                top_k=None,
                device=-1,  # CPU only - never touch GPU VRAM
                truncation=True,
                max_length=256,
            )
            logger.info("Loaded CPU emotion classifier: %s", self.model_id)
            return True
        except Exception as exc:
            self._load_failed = True
            logger.warning("Failed to load CPU emotion classifier %s: %s", self.model_id, exc)
            return False

    def classify(self, text: str) -> Dict[str, float]:
        if not self._ensure_loaded():
            return {}
        try:
            out = self._pipe(text)
            rows = out[0] if (isinstance(out, list) and out and isinstance(out[0], list)) else out
            return {str(r["label"]).lower(): float(r["score"]) for r in rows}
        except Exception as exc:
            logger.warning("Emotion classifier inference failed: %s", exc)
            return {}


# Singleton cache per model_id so weights load at most once per process.
_BACKENDS: Dict[str, GoEmotionsCPUBackend] = {}


def get_configured_backend() -> Optional[GoEmotionsCPUBackend]:
    """Return the configured CPU classifier backend, or None when disabled."""
    raw = str(runtime_config.get("emotion.classifier_backend", "none") or "none").strip().lower()
    if raw in ("", "none", "off", "false", "0"):
        return None
    model_id = _MODEL_ALIASES.get(raw, raw)
    backend = _BACKENDS.get(model_id)
    if backend is None:
        backend = GoEmotionsCPUBackend(model_id=model_id)
        _BACKENDS[model_id] = backend
    return backend


def build_classifier_input(
    event: EmotionEvent,
    recalled_memories: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Compose the compact event + tone + top-memory string for the classifier."""
    parts: List[str] = []
    if event.speech_text:
        tone = event.perceived_tone or event.speech_tone
        tone_str = f" ({tone})" if tone else ""
        parts.append(f"{event.source_name or 'Someone'}{tone_str}: {event.speech_text}")
    elif event.summary:
        parts.append(event.summary)
    if recalled_memories:
        mem = str(recalled_memories[0].get("text", "") or "").strip()
        if mem:
            parts.append(f"Memory: {mem[:180]}")
    return " | ".join(parts) or event.summary or ""


def _structural_tone_guards(
    event: EmotionEvent,
    rel_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    """Lightweight deterministic guards for explicit perceived tone & strain leaks."""
    guards: Dict[str, float] = {}
    tone = (event.perceived_tone or event.speech_tone or "").strip().lower()
    closeness = float((rel_profile or {}).get("closeness", 50.0))

    if event.tone_strained:
        guards["fear"] = max(guards.get("fear", 0.0), 10.0)
        guards["sadness"] = max(guards.get("sadness", 0.0), 6.0)
    if tone == "sarcastic":
        guards["anger"] = max(guards.get("anger", 0.0), 14.0 if closeness < 75 else 8.0)
        guards["shame"] = max(guards.get("shame", 0.0), 6.0)
    elif tone == "mocking":
        guards["shame"] = max(guards.get("shame", 0.0), 18.0)
        guards["anger"] = max(guards.get("anger", 0.0), 10.0)
    elif tone == "hostile":
        guards["anger"] = max(guards.get("anger", 0.0), 16.0)
        guards["fear"] = max(guards.get("fear", 0.0), 10.0)
    elif tone in ("warm", "gentle", "reassuring"):
        guards["calm"] = max(guards.get("calm", 0.0), 10.0)
        if closeness >= 65:
            guards["love"] = max(guards.get("love", 0.0), 6.0)
    elif tone == "teasing" and closeness >= 70:
        guards["happiness"] = max(guards.get("happiness", 0.0), 8.0)
    return guards


def appraise_event(
    player: Any,
    event: EmotionEvent,
    recalled_memories: Optional[List[Dict[str, Any]]] = None,
    rel_profile: Optional[Dict[str, Any]] = None,
    force_backend: Optional[GoEmotionsCPUBackend] = None,
) -> Optional[MatrixStepResult]:
    """Run Track 1 appraisal + Coupled Emotional Matrix step for ``player``.

    Updates ``player._emotion_matrix`` and projects onto ``player._emotions``.
    Returns None if no classifier backend is configured and no structural tone
    guard fires.
    """
    backend = force_backend if force_backend is not None else get_configured_backend()
    guards = _structural_tone_guards(event, rel_profile=rel_profile)

    if backend is None and not guards:
        return None

    t0 = time.perf_counter()
    raw_deltas: Dict[str, float] = {f: 0.0 for f in FAMILIES}
    top_probs: Dict[str, float] = {}
    appraisal = "tone guard"

    if backend is not None:
        text_in = build_classifier_input(event, recalled_memories)
        probs = backend.classify(text_in)
        if probs:
            top_labels = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
            top_probs = {k: round(v, 3) for k, v in top_labels[:5]}
            for label, score in top_labels:
                if score < 0.08:
                    continue
                for fam, weight in GO_EMOTIONS_TO_FAMILY.get(label, []):
                    raw_deltas[fam] += score * weight * 38.0
            non_neutral = [(k, v) for k, v in top_labels if k != "neutral" and v >= 0.08]
            if non_neutral:
                appraisal = "classifier read (" + ", ".join(f"{k}={v:.2f}" for k, v in non_neutral[:2]) + ")"

    for fam, val in guards.items():
        if abs(val) > abs(raw_deltas.get(fam, 0.0)):
            raw_deltas[fam] = val

    # Drop noise floor
    if all(abs(v) < 1.5 for v in raw_deltas.values()):
        return None

    state: CharacterEmotionState = player.emotion_matrix_state()
    lat_ms = (time.perf_counter() - t0) * 1000.0
    result = apply_matrix_step(
        engine_name="emotion_classifier_cpu" if backend is not None else "emotion_tone_guard",
        latency_ms=lat_ms,
        state=state,
        raw_deltas=raw_deltas,
        event=event,
        player=player,
        recalled_memories=recalled_memories or [],
        gut_appraisal=appraisal,
        explicit_suppress=False,
        metadata={
            "model": backend.model_id if backend is not None else "none",
            "top_probs": top_probs,
        },
    )

    # Project 13-family matrix back onto production 36-dim Player._emotions
    projected = state.to_36_dim_map()
    if projected:
        emap = player.emotions_map()
        for dim, val in projected.items():
            if dim in emap:
                emap[dim] = round(float(val), 2)

    return result
