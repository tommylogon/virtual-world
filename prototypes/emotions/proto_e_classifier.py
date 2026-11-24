"""Prototype E - Zero-LLM Local Emotion Classifier (GoEmotions CPU + Coupled Matrix).

Replaces generative LLM Track 1 appraisal with a lightweight local HuggingFace
emotion classifier (`SamLowe/roberta-base-go_emotions`, 28 classes, CPU-only,
0 VRAM, ~20-40 ms/call) fused with Tier 1 structural simulation guards and fed
into the shared Coupled Emotional Matrix + 8-Channel Autonomic Body.

No generative LLM ever touches emotion numbers here: the classifier outputs
calibrated class probabilities (0..1) and Python owns 100% of the numeric
mapping, coupling, vulnerability scaling, personal tells, and inertia.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from prototypes.emotions.coupling import apply_matrix_step, apply_tick_decay
from prototypes.emotions.proto_a_matrix import ProtoAMatrixEngine
from prototypes.emotions.proto_d_unified import _compute_structural_guards
from prototypes.emotions.schema import (
    FAMILIES,
    CharacterEmotionState,
    EmotionEvent,
    MatrixStepResult,
)


#: Mapping from 28 GoEmotions labels -> 13 Matrix families (family, scale_weight).
#: Positive weights raise the family; negative weights (e.g. relief) cool distress.
GO_EMOTIONS_TO_MATRIX: Dict[str, List[Tuple[str, float]]] = {
    "admiration": [("love", 22.0), ("happiness", 14.0)],
    "amusement": [("happiness", 26.0), ("calm", 8.0)],
    "anger": [("anger", 34.0), ("calm", -18.0)],
    "annoyance": [("anger", 22.0), ("calm", -12.0)],
    "approval": [("happiness", 14.0), ("calm", 10.0)],
    "caring": [("love", 26.0), ("calm", 10.0)],
    "confusion": [("surprise", 20.0), ("fear", 8.0), ("calm", -10.0)],
    "curiosity": [("surprise", 12.0)],
    "desire": [("arousal", 20.0), ("envy", 10.0)],
    "disappointment": [("sadness", 24.0), ("happiness", -16.0)],
    "disapproval": [("anger", 18.0), ("disgust", 14.0), ("shame", 10.0)],
    "disgust": [("disgust", 32.0), ("anger", 10.0), ("calm", -12.0)],
    "embarrassment": [("shame", 34.0), ("fear", 10.0), ("calm", -16.0)],
    "excitement": [("happiness", 28.0), ("surprise", 12.0)],
    "fear": [("fear", 34.0), ("calm", -20.0)],
    "gratitude": [("love", 24.0), ("happiness", 18.0), ("calm", 12.0)],
    "grief": [("sadness", 36.0), ("happiness", -24.0), ("calm", -16.0)],
    "joy": [("happiness", 32.0), ("calm", 12.0)],
    "love": [("love", 32.0), ("happiness", 18.0), ("calm", 10.0)],
    "nervousness": [("fear", 26.0), ("shame", 12.0), ("calm", -16.0)],
    "optimism": [("happiness", 20.0), ("calm", 12.0)],
    "pride": [("happiness", 22.0)],
    "realization": [("surprise", 22.0)],
    "relief": [("calm", 28.0), ("fear", -22.0), ("shame", -14.0), ("sadness", -12.0)],
    "remorse": [("guilt", 34.0), ("sadness", 14.0), ("shame", 10.0)],
    "sadness": [("sadness", 32.0), ("happiness", -20.0), ("calm", -12.0)],
    "surprise": [("surprise", 28.0), ("calm", -10.0)],
    "neutral": [],
}


class GoEmotionsBackend:
    """Lazy-loaded local CPU transformers classifier for GoEmotions."""

    def __init__(self, model_id: str = "cirimus/modernbert-base-go-emotions"):
        self.model_id = model_id
        self._pipe = None

    def _ensure_loaded(self) -> None:
        if self._pipe is not None:
            return
        from transformers import pipeline

        self._pipe = pipeline(
            "text-classification",
            model=self.model_id,
            top_k=None,
            device=-1,  # CPU-only: 0 VRAM contention with Actor LLM
            truncation=True,
            max_length=256,
        )

    def classify(self, text: str) -> Dict[str, float]:
        self._ensure_loaded()
        out = self._pipe(text)
        # transformers pipeline with top_k=None returns [[{"label": ..., "score": ...}, ...]]
        rows = out[0] if (isinstance(out, list) and out and isinstance(out[0], list)) else out
        return {str(r["label"]).lower(): float(r["score"]) for r in rows}


class GLiClassBackend:
    """Lazy-loaded local CPU zero-shot GLiClass classifier over our exact 13 Matrix families."""

    LABELS: Tuple[str, ...] = (
        "anger",
        "disgust",
        "envy",
        "fear",
        "happiness",
        "jealousy",
        "love",
        "sadness",
        "shame",
        "guilt",
        "calm",
        "surprise",
        "romantic attraction",
    )
    LABEL_MAP: Dict[str, str] = {"romantic attraction": "arousal"}

    def __init__(self, model_id: str = "knowledgator/gliclass-edge-v3.0"):
        self.model_id = model_id
        self._pipe = None

    def _ensure_loaded(self) -> None:
        if self._pipe is not None:
            return
        from gliclass import GLiClassModel, ZeroShotClassificationPipeline
        from transformers import AutoTokenizer

        model = GLiClassModel.from_pretrained(self.model_id)
        tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self._pipe = ZeroShotClassificationPipeline(
            model,
            tokenizer,
            classification_type="multi-label",
            device="cpu",
        )

    def classify(self, text: str) -> Dict[str, float]:
        self._ensure_loaded()
        out = self._pipe(text, list(self.LABELS), threshold=0.05)
        rows = out[0] if (isinstance(out, list) and out and isinstance(out[0], list)) else out
        scores: Dict[str, float] = {}
        for r in rows:
            lbl = str(r["label"]).lower()
            fam = self.LABEL_MAP.get(lbl, lbl)
            scores[fam] = float(r["score"])
        return scores


class ProtoEClassifierEngine:
    """Zero-LLM Track 1: Tier 1 Structural Guards + Local CPU Emotion Classifier."""

    def __init__(
        self,
        model_id: str = "cirimus/modernbert-base-go-emotions",
        *,
        backend_kind: str = "go_emotions",
    ):
        self.tier_a = ProtoAMatrixEngine()
        self.backend_kind = backend_kind
        if backend_kind == "gliclass":
            self.backend = GLiClassBackend(model_id=model_id)
            self.name = f"Proto E - GLiClass CPU ({model_id})"
        else:
            self.backend = GoEmotionsBackend(model_id=model_id)
            self.name = f"Proto E - GoEmotions CPU ({model_id})"

    def _build_classifier_input(
        self,
        event: EmotionEvent,
        recalled_memories: List[Dict[str, Any]],
    ) -> str:
        parts: List[str] = []
        if event.speech_text:
            tone_str = f" ({event.perceived_tone})" if event.perceived_tone else ""
            parts.append(f"{event.source_name or 'Someone'}{tone_str}: {event.speech_text}")
        elif event.summary:
            parts.append(event.summary)
        if recalled_memories:
            mem = str(recalled_memories[0].get("text", "") or "").strip()
            if mem:
                parts.append(f"Memory: {mem[:180]}")
        return " | ".join(parts) or event.summary

    def appraise(
        self,
        state: CharacterEmotionState,
        event: EmotionEvent,
        player: Any,
        world: Any,
        recalled_memories: List[Dict[str, Any]],
        rel_profile: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, float], str, bool, Dict[str, Any]]:
        t0 = time.perf_counter()
        a_deltas, a_app, a_sup, _ = self.tier_a.appraise(
            state, event, player, world, recalled_memories, rel_profile
        )
        guards, hints = _compute_structural_guards(event, player, rel_profile, a_deltas)

        text_in = self._build_classifier_input(event, recalled_memories)
        probs = self.backend.classify(text_in)
        clf_ms = (time.perf_counter() - t0) * 1000.0

        # Project calibrated probabilities onto the 13 Matrix families.
        clf_deltas: Dict[str, float] = {f: 0.0 for f in FAMILIES}
        top_labels: List[Tuple[str, float]] = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
        if self.backend_kind == "gliclass":
            for fam, score in top_labels:
                if score < 0.12 or fam not in clf_deltas:
                    continue
                clf_deltas[fam] += score * 34.0
        else:
            for label, score in top_labels:
                if score < 0.08 or label == "neutral":
                    continue
                for fam, weight in GO_EMOTIONS_TO_MATRIX.get(label, []):
                    clf_deltas[fam] += score * weight

        # Clamp classifier deltas to engine-owned bounds before fusing with Tier 1 floors.
        fused: Dict[str, float] = {}
        for fam in FAMILIES:
            # Blend classifier signal with deterministic Tier 1 structural rules.
            val = clf_deltas[fam] * 0.75 + a_deltas.get(fam, 0.0) * 0.45
            val = max(-28.0, min(32.0, val))
            if fam in guards:
                op, bound = guards[fam]
                if op == "min":
                    val = max(val, bound)
                elif op == "max":
                    val = min(val, bound)
            fused[fam] = round(val, 2)

        top3 = ", ".join(f"{lbl}={sc:.2f}" for lbl, sc in top_labels[:3] if lbl != "neutral")
        appraisal = f"classifier read ({top3 or 'neutral'})" + (f"; {hints[0]}" if hints else "")
        meta = {
            "method": "go_emotions_cpu_classifier",
            "route": "tier_e_classifier_cpu",
            "model": self.backend.model_id,
            "classifier_ms": round(clf_ms, 1),
            "top_probs": {lbl: round(sc, 3) for lbl, sc in top_labels[:5]},
        }
        return fused, appraisal, a_sup, meta

    def process_event(
        self,
        state: CharacterEmotionState,
        event: EmotionEvent,
        player: Any,
        world: Any,
        recalled_memories: List[Dict[str, Any]],
        rel_profile: Optional[Dict[str, Any]] = None,
    ) -> MatrixStepResult:
        t0 = time.perf_counter()
        raw_deltas, appraisal, suppress, meta = self.appraise(
            state, event, player, world, recalled_memories, rel_profile
        )
        lat_ms = (time.perf_counter() - t0) * 1000.0
        return apply_matrix_step(
            engine_name=self.name,
            latency_ms=lat_ms,
            state=state,
            raw_deltas=raw_deltas,
            event=event,
            player=player,
            recalled_memories=recalled_memories,
            gut_appraisal=appraisal,
            explicit_suppress=suppress,
            metadata=meta,
        )

    def tick(
        self,
        state: CharacterEmotionState,
        player: Any,
        world: Any,
        ticks: int = 1,
    ) -> Dict[str, Any]:
        return apply_tick_decay(state, player, ticks=ticks)
