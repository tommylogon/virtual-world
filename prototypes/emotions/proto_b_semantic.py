"""Prototype B - Local Semantic Embedding Vector-Field Hybrid + Autonomic Dynamics.

Encodes incoming dialogue, world events, and recalled memories against a DBT
Handout 6 Prompting-Event & Interpretation Anchor Bank (all 13 core families),
using:
  1. LM Studio embeddings (text-embedding-qwen3-embedding-0.6b on localhost:1234),
  2. fallback to local sentence_transformers (all-MiniLM-L6-v2),
  3. fallback to deterministic character n-gram hashing for offline tests.

Then modulates the semantic emotion field with relationship context, witness
exposure, expectation discrepancy, and recalled memory vectors before feeding
the shared Coupled Emotional Matrix W + 8-channel Autonomic Body physics.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

from prototypes.emotions.coupling import apply_matrix_step, apply_tick_decay
from prototypes.emotions.schema import (
    FAMILIES,
    CharacterEmotionState,
    EmotionEvent,
    MatrixStepResult,
)

#: DBT Handout 6 Prompting Events & Interpretations compressed into rich
#: semantic anchors per family (multiple anchors per family for sharper recall).
DBT_SEMANTIC_ANCHORS: Dict[str, List[str]] = {
    "anger": [
        "being insulted, cursed at, disrespected, treated unfairly, or called cruel names",
        "having an important goal blocked, losing power status or respect, things going wrong",
        "someone attacking or threatening you or someone you care about, infuriating provocation",
    ],
    "disgust": [
        "seeing blood, rot, vomit, filth, corpses, contaminated or slimy dirty things",
        "witnessing extreme cruelty, hypocrisy, betrayal of moral values, vile behavior",
        "feeling sickened, repulsed, physically or mentally polluted, wanting to recoil and wash",
    ],
    "envy": [
        "coveting a rival's prize, trophy, chief's staff, promotion, or luxury possessions",
        "resenting a peer who won the status, authority, or reward you wanted for yourself",
        "bitter jealousy over another person's wealth, achievement, or stolen credit",
    ],
    "fear": [
        "life, health, safety, or wellbeing threatened, trapped in the dark, danger or violence",
        "being abandoned, rejected, left alone, flashback to a painful scary past event",
        "losing control, expecting failure or harm, silence and unfamiliar threat",
    ],
    "happiness": [
        "receiving wonderful news, praise, esteem, acceptance, or succeeding at a hard task",
        "warm laughter, fun, relief, getting what you hoped for, feeling included and safe",
        "reality turning out better than feared, shared joy and reassurance",
    ],
    "jealousy": [
        "a romantic partner or close friend flirting with a rival, threat of losing a loved one",
        "feeling replaced, ignored while a competitor gets attention from someone you love",
        "suspicion of disloyalty, partner pulling away, wanting more time alone, affair",
    ],
    "love": [
        "deep affection, tenderness, kindness, someone caring for you and keeping promises",
        "mutual gaze, warmth, holding hands, sharing a special close moment with someone trusted",
        "feeling appreciated, adored, safe and emotionally close to a cherished person",
    ],
    "sadness": [
        "hurt by cruel words from someone you love, feeling rejected, neglected, or excluded",
        "losing someone or something irretrievably, loneliness, disappointment, defeat, grief",
        "feeling powerless, hopeless, alienated, or reminded of painful past abandonment",
    ],
    "shame": [
        "humiliated in public, laughed at, mocked, criticized in front of watching bystanders",
        "caught hiding a secret or mistake, exposed as defective, inferior, or unlovable",
        "feeling mortified, rejected by people you care about, wanting to shrink and disappear",
    ],
    "guilt": [
        "breaking, ruining, or damaging someone's belonging and hiding it instead of confessing",
        "violating your own personal values, lying, breaking a promise, hurting someone you care about",
        "remorse and regret wishing you had acted differently and needing to make amends",
    ],
    "calm": [
        "honest reassurance, peaceful resolution, safe quiet room, problem settled cleanly",
        "deep breath, steady composure, tension lifting, feeling safe and unhurried",
    ],
    "surprise": [
        "sudden unexpected shock, startling turn of events, expectation completely contradicted",
        "caught off guard by an abrupt outburst, sudden reveal, or missing expected person",
    ],
    "arousal": [
        "strong physical attraction, intense desire, craving, eager curiosity and anticipation",
        "flirtatious touch, thrilling tension, hungry wanting and magnetic pull",
    ],
}


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return dot / (na * nb)


def _hash_embed(texts: List[str], dim: int = 256) -> List[List[float]]:
    """Deterministic character-trigram + word hash embedding for zero-network tests."""
    out: List[List[float]] = []
    for text in texts:
        vec = [0.0] * dim
        low = str(text or "").lower()
        words = re.findall(r"[a-z]+", low)
        tokens = list(words)
        for w in words:
            if len(w) >= 4:
                for i in range(len(w) - 2):
                    tokens.append(w[i : i + 3])
        for tok in tokens:
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest()[:8], 16)
            vec[h % dim] += 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 1e-12:
            vec = [x / norm for x in vec]
        out.append(vec)
    return out


class EmbeddingBackend:
    """Pluggable batch embedder: LM Studio -> sentence_transformers -> deterministic hash."""

    def __init__(
        self,
        *,
        lm_studio_url: str = "http://127.0.0.1:1234/v1/embeddings",
        model_id: str = "text-embedding-nomic-embed-text-v1.5@q4_k_m",
        prefer_lm_studio: bool = True,
        offline: bool = False,
        embed_fn: Optional[Callable[[List[str]], List[List[float]]]] = None,
    ):
        self.lm_studio_url = lm_studio_url
        self.model_id = model_id
        self.prefer_lm_studio = prefer_lm_studio
        self.offline = offline
        self._custom_embed = embed_fn
        self.active_provider = "uninitialized"
        self._lm_failed = False

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self._custom_embed is not None:
            self.active_provider = "custom"
            return self._custom_embed(texts)
        if not self.offline and self.prefer_lm_studio and not self._lm_failed:
            try:
                payload = json.dumps({"model": self.model_id, "input": texts}).encode("utf-8")
                req = urllib.request.Request(
                    self.lm_studio_url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                    rows = sorted(body["data"], key=lambda item: item.get("index", 0))
                    self.active_provider = f"lm_studio:{self.model_id}"
                    return [row["embedding"] for row in rows]
            except Exception:
                self._lm_failed = True

        if not self.offline:
            try:
                from embeddings import embed_batch
                vecs = embed_batch(texts)
                if vecs and any(any(v) for v in vecs):
                    self.active_provider = "sentence_transformers:all-MiniLM-L6-v2"
                    return vecs
            except Exception:
                pass

        self.active_provider = "hash_fallback"
        return _hash_embed(texts)


class ProtoBSemanticEngine:
    """Prototype B: Dense DBT Semantic Anchor Field + Contextual Modulation + Matrix W."""

    name = "Proto B - Local Semantic Embedding Hybrid"

    def __init__(
        self,
        *,
        lm_studio_url: str = "http://127.0.0.1:1234/v1/embeddings",
        model_id: str = "text-embedding-nomic-embed-text-v1.5@q4_k_m",
        offline: bool = False,
        embed_fn: Optional[Callable[[List[str]], List[List[float]]]] = None,
    ):
        self.backend = EmbeddingBackend(
            lm_studio_url=lm_studio_url,
            model_id=model_id,
            offline=offline,
            embed_fn=embed_fn,
        )
        self._anchor_vecs: Optional[Dict[str, List[List[float]]]] = None

    def _ensure_anchors(self) -> Dict[str, List[List[float]]]:
        if self._anchor_vecs is not None:
            return self._anchor_vecs
        flat_texts: List[str] = []
        slices: List[Tuple[str, int, int]] = []
        for fam in FAMILIES:
            anchors = DBT_SEMANTIC_ANCHORS[fam]
            start = len(flat_texts)
            flat_texts.extend(anchors)
            slices.append((fam, start, len(flat_texts)))
        vecs = self.backend.embed(flat_texts)
        self._anchor_vecs = {fam: vecs[s:e] for fam, s, e in slices}
        return self._anchor_vecs

    def _score_vectors(self, q_vecs: List[List[float]]) -> List[Dict[str, float]]:
        """Compute contrast-sharpened cosine affinity across all 13 DBT families for a batch."""
        anchors = self._ensure_anchors()
        results: List[Dict[str, float]] = []
        for q in q_vecs:
            raw_sims: Dict[str, float] = {}
            for fam, avecs in anchors.items():
                raw_sims[fam] = max((_cosine(q, a) for a in avecs), default=0.0)
            mean_sim = sum(raw_sims.values()) / max(1, len(raw_sims))
            std_sim = math.sqrt(
                sum((v - mean_sim) ** 2 for v in raw_sims.values()) / max(1, len(raw_sims))
            )
            denom = max(0.035, std_sim)
            results.append(
                {fam: max(0.0, (val - mean_sim) / denom) for fam, val in raw_sims.items()}
            )
        return results

    def _score_texts(self, texts: List[str]) -> List[Dict[str, float]]:
        """Batch-embed texts in a single provider roundtrip and score against anchors."""
        if not texts:
            return []
        self._ensure_anchors()
        q_vecs = self.backend.embed(texts)
        if not q_vecs:
            return [{f: 0.0 for f in FAMILIES} for _ in texts]
        return self._score_vectors(q_vecs)

    def _score_text(self, text: str) -> Dict[str, float]:
        """Compute contrast-sharpened cosine affinity across all 13 DBT families."""
        scored = self._score_texts([text])
        return scored[0] if scored else {f: 0.0 for f in FAMILIES}

    def appraise(
        self,
        state: CharacterEmotionState,
        event: EmotionEvent,
        player: Any,
        world: Any,
        recalled_memories: List[Dict[str, Any]],
        rel_profile: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, float], str, bool, Dict[str, Any]]:
        rel = rel_profile or {}
        closeness = float(rel.get("closeness", 0.0) or 0.0)
        trust = float(rel.get("trust", 0.0) or 0.0)
        is_close = closeness >= 35.0 or trust >= 0.45
        witness_count = len(event.witnesses)

        # Build a clean situational utterance for semantic embedding without leaking
        # relationship praise words ("close trusted person") into conflict/guilt queries.
        witness_clause = (
            f" in front of {witness_count} watching witnesses"
            if witness_count > 0
            else " alone in private"
        )
        exp_clause = (
            f" while expecting {'; '.join(event.expectations)}"
            if event.expectations
            else ""
        )
        ptone = (event.perceived_tone or "").strip().lower()
        tone_clause = ""
        if event.tone_perception_note:
            tone_clause = f"; delivery {event.tone_perception_note}"
        elif ptone:
            tone_clause = f"; delivered {ptone}"
        event_text = (
            f"{event.kind}: {event.summary}. "
            f"{(event.source_name + ' said: ' + event.speech_text) if event.speech_text and event.source_name else event.speech_text} "
            f"({witness_clause.strip()}{exp_clause}{tone_clause})"
        ).strip()

        tags_low = {t.lower() for t in event.tags}
        is_playful_tease = ptone == "teasing"
        is_negative_tone = ptone in ("sarcastic", "mocking", "hostile", "cold")
        is_strained_tone = ptone == "strained" or event.tone_strained
        is_relief_event = (
            event.kind in ("check_facts", "reassure", "repair") or "reassure" in tags_low
        ) and not (is_negative_tone or is_strained_tone)

        mem_blob = (
            " ".join(str(m.get("text") or "") for m in recalled_memories[:3]).strip()
            if (recalled_memories and not is_relief_event)
            else ""
        )
        batch_texts = [event_text] + ([mem_blob] if mem_blob else [])
        batch_scores = self._score_texts(batch_texts)
        event_z = batch_scores[0]
        raw_mem_z = batch_scores[1] if len(batch_scores) > 1 else {}

        is_hostile_event = (not is_relief_event) and (not is_playful_tease) and bool(
            {"insult", "betrayal"} & tags_low
            or is_negative_tone
            or event_z.get("anger", 0.0) >= 0.85
            or event_z.get("disgust", 0.0) >= 0.85
        )

        # Also score top recalled memories semantically so past memories shift the vector field.
        # During a hostile/betrayal hit, recalling warm memories sharpens contrast hurt
        # rather than boosting live love/happiness.
        mem_z: Dict[str, float] = {f: 0.0 for f in FAMILIES}
        for f, z in raw_mem_z.items():
            if is_hostile_event and f in ("love", "happiness", "calm"):
                mem_z["sadness"] = mem_z.get("sadness", 0.0) + z * 0.35
            else:
                mem_z[f] = z * 0.45

        deltas: Dict[str, float] = {f: 0.0 for f in FAMILIES}
        for fam in FAMILIES:
            combined_z = event_z[fam] + mem_z[fam]
            if combined_z >= 0.55:
                # Map z-score (0.55 .. 2.8) smoothly onto a +8 .. +44 point shift.
                deltas[fam] = min(46.0, (combined_z - 0.35) * 19.0)

        # Relational & structural modulation (turning surface tone into character-specific impact):
        if is_playful_tease:
            for neg_fam in ("anger", "disgust", "shame", "guilt", "fear", "sadness", "envy", "jealousy"):
                deltas[neg_fam] = min(0.0, deltas[neg_fam])
            deltas["happiness"] += 22.0
            deltas["love"] += 14.0 if is_close else 4.0
            deltas["calm"] += 8.0
        elif is_strained_tone:
            deltas["calm"] = min(0.0, deltas["calm"]) - 12.0
            deltas["happiness"] = min(0.0, deltas["happiness"]) - 8.0
            deltas["fear"] += 18.0
            deltas["sadness"] += 14.0
            deltas["surprise"] += 14.0
        elif event.kind in ("check_facts", "reassure"):
            # Relief/reassurance cools negative spirals even if topic words ("confessed",
            # "hated") overlap negative anchors in embedding space.
            for neg_fam in ("shame", "fear", "jealousy", "sadness", "anger", "envy"):
                deltas[neg_fam] = min(0.0, deltas[neg_fam])
            deltas["shame"] -= 26.0
            deltas["fear"] -= 22.0
            deltas["jealousy"] -= 20.0
            deltas["calm"] += 20.0
            deltas["happiness"] += 14.0
        elif event.kind == "repair":
            for neg_fam in ("guilt", "shame", "anger"):
                deltas[neg_fam] = min(0.0, deltas[neg_fam])
            deltas["guilt"] -= 22.0
            deltas["calm"] += 15.0
        else:
            # Close-bond hurt & expectation contrast when a trusted person attacks or betrays.
            if is_hostile_event:
                deltas["love"] = min(deltas["love"], 0.0)
                deltas["happiness"] = min(deltas["happiness"], 0.0)
            if is_close and (is_hostile_event or deltas["anger"] >= 14.0 or deltas["disgust"] >= 14.0):
                deltas["sadness"] += 22.0
                deltas["anger"] += 14.0
                deltas["love"] -= 22.0
                deltas["happiness"] -= 28.0
                deltas["fear"] += 10.0
                if event.expectations:
                    deltas["surprise"] += 16.0
            elif is_hostile_event and not is_close:
                deltas["anger"] += 22.0
                deltas["disgust"] += 12.0
            # Public witnesses amplify shame whenever negative social evaluation lands.
            if witness_count > 0 and (
                is_hostile_event or deltas["shame"] >= 8.0 or deltas["anger"] >= 16.0 or deltas["sadness"] >= 16.0
            ):
                deltas["shame"] += 14.0 + min(10.0, witness_count * 4.0)
            # Explicit structured tags reinforce clear engine facts (goals/fears).
            if "rival_holds_goal_item" in tags_low:
                deltas["envy"] += 22.0
            if "rival_flirt" in tags_low:
                deltas["jealousy"] += 24.0
            if "transgression" in tags_low:
                deltas["guilt"] += 20.0
            if "hid_mistake" in tags_low:
                deltas["shame"] += 18.0

        top_active = sorted(
            ((v, f) for f, v in deltas.items() if v >= 8.0),
            reverse=True,
        )[:3]
        if top_active:
            names = ", ".join(f for _, f in top_active)
            appraisal = f"semantic vector resonance pulled strongest toward {names}"
        else:
            appraisal = "low semantic emotional contrast for this event"

        meta = {
            "method": "semantic_embedding_field",
            "embedding_provider": self.backend.active_provider,
            "event_z": {k: round(v, 2) for k, v in event_z.items() if v >= 0.4},
            "memory_z": {k: round(v, 2) for k, v in mem_z.items() if v >= 0.2},
        }
        return deltas, appraisal, False, meta

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
        dt = (time.perf_counter() - t0) * 1000.0
        return apply_matrix_step(
            engine_name=self.name,
            latency_ms=dt,
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
