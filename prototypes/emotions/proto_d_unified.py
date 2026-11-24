"""Prototype D (Demo 4) - Unified Tri-Tier Emotion System (A + B + C).

Combines all three approaches into one coherent, latency-aware architecture over
the shared Coupled Emotional Matrix + 8-Channel Autonomic Body physics:

  Tier 1 (Proto A - Deterministic Structural Floor, <1 ms, always runs):
    Extracts hard simulation facts that no neural model should drift past:
    transgressions (guilt), hidden mistakes (shame), rival goal items (envy),
    rival flirting (jealousy), personal fear_tags trauma triggers, negation-safe
    relief/check_facts gating, and close-partner betrayal contrast.

  Tier 2 (Proto B - Fast Semantic Sensor, ~37 ms on 127.0.0.1 nomic-embed):
    Runs a single batched embedding pass over the event + recalled memories
    against the 65 DBT Handout 6 anchors. Catches unseen/untagged dialogue cues
    for background NPCs without LLM cost and signals semantic novelty/conflict
    to Tier 3.

  Tier 3 (Proto C - Cue-Gated Pre-Actor Limbic LLM, ~250-650 ms on 127.0.0.1):
    Runs ONLY when needed (spotlight characters with nuanced speech, social
    conflict, expectation breaches, mixed affection/trauma, or untagged subtext).
    Skipped completely on unchanged continuations, background NPCs, and clear
    non-speech structured events (goal/repair/threat). Receives Tier 1/2
    plain-English structural cues (never raw mood floats) and its output is
    fused with A + B under Tier 1's hard simulation floors.
"""
from __future__ import annotations

import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from prototypes.emotions.autonomic import compute_vulnerability_load
from prototypes.emotions.coupling import apply_matrix_step, apply_tick_decay
from prototypes.emotions.proto_a_matrix import ProtoAMatrixEngine
from prototypes.emotions.proto_b_semantic import ProtoBSemanticEngine
from prototypes.emotions.proto_c_dual_mind import ProtoCDualMindEngine
from prototypes.emotions.schema import (
    FAMILIES,
    CharacterEmotionState,
    EmotionEvent,
    MatrixStepResult,
)


def _compute_structural_guards(
    event: EmotionEvent,
    player: Any,
    rel_profile: Optional[Dict[str, Any]],
    a_deltas: Dict[str, float],
) -> Tuple[Dict[str, Tuple[str, float]], List[str]]:
    """Derive hard simulation floor/ceiling guards and plain-English cues from Tier 1 facts.

    Returns:
      guards: {family: ("min" | "max", value)}
      hints:  list of concise plain-English structural cues for Tier 3 grounding
    """
    guards: Dict[str, Tuple[str, float]] = {}
    hints: List[str] = []

    rel = rel_profile or {}
    closeness = float(rel.get("closeness", 0.0) or 0.0)
    trust = float(rel.get("trust", 0.0) or 0.0)
    is_close = closeness >= 35.0 or trust >= 0.45

    tags = {str(t).strip().lower() for t in event.tags}
    low = f"{event.summary} {event.speech_text}".lower()
    ptone = (event.perceived_tone or "").strip().lower()
    is_playful_tease = ptone == "teasing"
    is_strained_tone = ptone == "strained" or event.tone_strained
    is_relief = (
        event.kind in ("check_facts", "reassure", "repair") or "reassure" in tags
    ) and ptone not in ("sarcastic", "mocking", "hostile", "cold", "strained")

    if is_playful_tease:
        guards["happiness"] = ("min", 14.0)
        guards["anger"] = ("max", 0.0)
        guards["sadness"] = ("max", 0.0)
        hints.append("delivered playfully/teasingly by a close steady friend (affectionate banter, not an attack)")
        return guards, hints

    if is_strained_tone:
        guards["calm"] = ("max", 0.0)
        guards["fear"] = ("min", 12.0)
        guards["surprise"] = ("min", 10.0)
        hints.append("speaker tried to sound warm/composed, but their voice sounded tight and strained (concern/unease, not calm reassurance)")
        return guards, hints

    if ptone in ("sarcastic", "mocking"):
        guards["happiness"] = ("max", -16.0)
        guards["shame"] = ("min", 18.0)
        guards["anger"] = ("min", 16.0)
        if is_close:
            guards["sadness"] = ("min", 16.0)
        hints.append(f"listener perceived the delivery as {ptone} ({event.tone_perception_note or 'sharp and cutting'})")

    if is_relief:
        if event.kind in ("check_facts", "reassure"):
            guards["shame"] = ("max", -16.0)
            guards["fear"] = ("max", -16.0)
            guards["calm"] = ("min", 16.0)
            guards["anger"] = ("max", 0.0)
            guards["sadness"] = ("max", 0.0)
            hints.append("direct reassurance / fact-check relieved threat and rejection fears")
        elif event.kind == "repair":
            guards["guilt"] = ("max", -18.0)
            guards["calm"] = ("min", 12.0)
            hints.append("concrete repair action eased guilt")
        return guards, hints

    if "transgression" in tags:
        guards["guilt"] = ("min", 30.0)
        hints.append("character harmed someone or broke a personal standard (guilt is active)")
    if "hid_mistake" in tags:
        guards["shame"] = ("min", 28.0)
        hints.append("mistake was hidden and risks exposure (shame is active)")
    if "rival_holds_goal_item" in tags or "envy" in tags:
        guards["envy"] = ("min", 34.0)
        hints.append("rival holds a prized goal item/status (envy, not romantic jealousy)")
    if "rival_flirt" in tags or "jealousy" in tags:
        guards["jealousy"] = ("min", 34.0)
        hints.append("outsider threatens a valued close bond (jealousy)")

    if ("insult" in tags or "betrayal" in tags) and is_close:
        guards["love"] = ("max", -16.0)
        guards["happiness"] = ("max", -24.0)
        guards["sadness"] = ("min", 24.0)
        hints.append("trusted close person attacked/betrayed expectations (hurts sadness and erodes love)")
        if event.witnesses:
            guards["shame"] = ("min", 22.0)
            hints.append(f"{len(event.witnesses)} witness(es) saw the attack (public humiliation)")
    elif ("insult" in tags or "betrayal" in tags) and not is_close:
        guards["anger"] = ("min", 26.0)
        hints.append("hostile insult from an untrusted stranger (defensive anger)")

    fear_tags = {str(t).lower() for t in (getattr(player, "fear_tags", None) or [])}
    hit_fears = fear_tags & (tags | set(re.findall(r"[a-z_]+", low)))
    if hit_fears:
        guards["fear"] = ("min", 28.0)
        hints.append(f"personal trauma fear trigger fired ({', '.join(sorted(hit_fears))})")

    return guards, hints


class ProtoDUnifiedEngine:
    """Prototype D (Demo 4): Tri-tier unified A (rules) + B (fast semantic) + C (cue-gated LLM)."""

    name = "Proto D - Unified Tri-Tier (A + B + C)"

    def __init__(
        self,
        *,
        embed_url: str = "http://127.0.0.1:1234/v1/embeddings",
        embed_model: str = "text-embedding-nomic-embed-text-v1.5@q4_k_m",
        chat_url: str = "http://127.0.0.1:1234/v1/chat/completions",
        limbic_model: str = "qwen3.5-4b",
        actor_model: Optional[str] = None,
        offline: bool = False,
        allow_llm: bool = True,
        embed_fn: Optional[Callable[[List[str]], List[List[float]]]] = None,
        llm_fn: Optional[Callable[[List[Dict[str, str]]], str]] = None,
    ):
        self.offline = offline
        self.allow_llm = allow_llm
        self.tier_a = ProtoAMatrixEngine()
        self.tier_b = ProtoBSemanticEngine(
            lm_studio_url=embed_url,
            model_id=embed_model,
            offline=offline,
            embed_fn=embed_fn,
        )
        self.tier_c = ProtoCDualMindEngine(
            lm_studio_url=chat_url,
            limbic_model=limbic_model,
            actor_model=actor_model or limbic_model,
            offline=offline,
            llm_fn=llm_fn,
        )

    @property
    def limbic_model(self) -> str:
        return self.tier_c.limbic_model

    @limbic_model.setter
    def limbic_model(self, val: str) -> None:
        self.tier_c.limbic_model = val

    @property
    def actor_model(self) -> str:
        return self.tier_c.actor_model

    @actor_model.setter
    def actor_model(self, val: str) -> None:
        self.tier_c.actor_model = val

    def set_offline(self, offline: bool) -> None:
        """Toggle offline mode cleanly across B and C (clearing B's anchor cache on switch)."""
        self.offline = bool(offline)
        if self.tier_b.backend.offline != self.offline:
            self.tier_b.backend.offline = self.offline
            self.tier_b.backend.active_provider = "uninitialized"
            self.tier_b._anchor_vecs = None
        self.tier_c.offline = self.offline

    def _should_escalate_to_c(
        self,
        event: EmotionEvent,
        a_deltas: Dict[str, float],
        b_deltas: Dict[str, float],
        recalled_memories: List[Dict[str, Any]],
    ) -> Tuple[bool, str]:
        """Decide whether Tier 3 (Limbic LLM) is justified for this event."""
        tags = {str(t).strip().lower() for t in event.tags}
        if not self.allow_llm:
            return False, "llm_disabled_background_mode"
        if self.offline and self.tier_c._custom_llm is None:
            return False, "offline_mode"
        if "background" in tags or "soak" in tags:
            return False, "background_npc_fast_tier"
        # Pure non-speech structured world events (goals, repairs, raw combat threats)
        # are handled accurately and deterministically by Tier A + Tier B in <40ms.
        if not event.speech_text and event.kind in ("goal", "repair", "threat"):
            return False, f"structured_non_speech_{event.kind}"
        # Escalate to Tier 3 whenever there is spoken dialogue, social ambiguity,
        # expectation contrast, witnesses, or recalled memories interacting with the event.
        if event.speech_text or event.expectations or recalled_memories or event.kind in ("speech", "check_facts", "reassure", "discrepancy"):
            return True, "nuanced_social_or_speech_event"
        # Also escalate if Tier A missed the event entirely but Tier B detected semantic heat.
        a_peak = max((abs(v) for v in a_deltas.values()), default=0.0)
        b_peak = max((abs(v) for v in b_deltas.values()), default=0.0)
        if a_peak < 10.0 and b_peak >= 14.0:
            return True, "semantic_novelty_escalation"
        return False, "tier_ab_sufficient"

    def appraise(
        self,
        state: CharacterEmotionState,
        event: EmotionEvent,
        player: Any,
        world: Any,
        recalled_memories: List[Dict[str, Any]],
        rel_profile: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, float], str, bool, Dict[str, Any]]:
        tier_lats: Dict[str, float] = {}

        # 0. Cue-change gate before touching B or C (0 ms on identical continuation).
        ext_vuln_load, _ = compute_vulnerability_load(player, None)
        sig = self.tier_c._cue_signature(event, recalled_memories, ext_vuln_load)
        if sig == state.last_cue_signature and event.kind == "continuation":
            return (
                {f: 0.0 for f in FAMILIES},
                "unchanged scene cue; continuing current emotional momentum",
                False,
                {
                    "method": "cue_gated_skip",
                    "route": "cue_gated_skip",
                    "tiers_used": [],
                    "tier_latencies_ms": {},
                },
            )
        state.last_cue_signature = sig

        # 1. Tier 1 (Proto A - Deterministic Structural Guardrails, <1 ms).
        t_a0 = time.perf_counter()
        a_deltas, a_appraisal, a_suppress, a_meta = self.tier_a.appraise(
            state, event, player, world, recalled_memories, rel_profile
        )
        tier_lats["A"] = round((time.perf_counter() - t_a0) * 1000.0, 2)
        guards, hints = _compute_structural_guards(event, player, rel_profile, a_deltas)
        a_peak = max((abs(v) for v in a_deltas.values()), default=0.0)

        # 2. Tier 2 (Proto B - Fast Semantic Embedding Sensor, ~37 ms on 127.0.0.1 nomic).
        t_b0 = time.perf_counter()
        b_deltas, b_appraisal, b_suppress, b_meta = self.tier_b.appraise(
            state, event, player, world, recalled_memories, rel_profile
        )
        tier_lats["B"] = round((time.perf_counter() - t_b0) * 1000.0, 2)
        b_top = sorted(
            ((v, f) for f, v in b_deltas.items() if v >= 12.0),
            reverse=True,
        )[:3]
        if a_peak < 10.0 and b_top:
            hints.append(
                "semantic tone leaned toward " + ", ".join(f for _, f in b_top)
            )

        # 3. Tier 3 (Proto C - Escalate only for nuanced spotlight / speech events).
        escalate, route_reason = self._should_escalate_to_c(
            event, a_deltas, b_deltas, recalled_memories
        )

        tiers_used = ["A", "B"]
        c_deltas: Optional[Dict[str, float]] = None
        c_appraisal = ""
        c_suppress = False
        c_meta: Dict[str, Any] = {}

        if escalate:
            # Clear last_cue_signature before invoking tier_c.appraise so tier_c
            # does not double-gate a fresh event whose signature we already stored.
            saved_sig = state.last_cue_signature
            state.last_cue_signature = ""
            t_c0 = time.perf_counter()
            c_d, c_app, c_sup, c_m = self.tier_c.appraise(
                state,
                event,
                player,
                world,
                recalled_memories,
                rel_profile,
                structural_hint="; ".join(hints),
            )
            tier_lats["C"] = round((time.perf_counter() - t_c0) * 1000.0, 2)
            state.last_cue_signature = saved_sig
            c_meta = c_m
            if c_m.get("method") == "pre_actor_limbic_llm":
                tiers_used.append("C")
                c_deltas = c_d
                c_appraisal = c_app
                c_suppress = c_sup

        # 4. Deterministic Fusion + Tier 1 Hard Structural Floor Enforcement.
        fused: Dict[str, float] = {f: 0.0 for f in FAMILIES}
        sarcasm_override = False
        if c_deltas is not None:
            # Polarity Conflict Guard (Sarcasm / Subtext De-dilution):
            # When no hard structural guard applies, if Tier A's surface keywords guessed
            # positive warmth ("smile", "best") while Tier 3 LLM read strong negative
            # subtext/sarcasm, do not let bag-of-words warmth dilute the real sting.
            a_guessed_warm = (a_deltas.get("happiness", 0.0) >= 12.0 or a_deltas.get("love", 0.0) >= 12.0)
            c_read_negative = (
                c_deltas.get("happiness", 0.0) <= -15.0
                or max(
                    c_deltas.get("anger", 0.0),
                    c_deltas.get("shame", 0.0),
                    c_deltas.get("sadness", 0.0),
                    c_deltas.get("disgust", 0.0),
                ) >= 20.0
            )
            if not guards and a_guessed_warm and c_read_negative:
                sarcasm_override = True
                for f in FAMILIES:
                    b_val = min(0.0, b_deltas[f]) if f in ("happiness", "love", "calm") else b_deltas[f]
                    fused[f] = 0.10 * b_val + 0.90 * c_deltas[f]
            elif a_peak < 8.0:
                # When Tier A had zero lexical hit, trust C (0.85) + B (0.15).
                for f in FAMILIES:
                    fused[f] = 0.15 * b_deltas[f] + 0.85 * c_deltas[f]
            else:
                for f in FAMILIES:
                    fused[f] = 0.20 * a_deltas[f] + 0.10 * b_deltas[f] + 0.70 * c_deltas[f]
            route = "tier_abc_full"
            appraisal = c_appraisal or a_appraisal
            suppress = bool(c_suppress or a_suppress)
        else:
            # Fast zero-LLM fusion (A + B) for background NPCs, structured goals, or offline mode.
            if a_peak < 8.0:
                w_a, w_b = 0.20, 0.80
            else:
                w_a, w_b = 0.65, 0.35
            for f in FAMILIES:
                fused[f] = w_a * a_deltas[f] + w_b * b_deltas[f]
            route = "tier_ab_fast"
            appraisal = a_appraisal if a_peak >= 8.0 else b_appraisal
            suppress = bool(a_suppress or b_suppress)

        # Enforce Tier 1 structural floors & ceilings so hard sim facts never drift away.
        floors_applied: List[str] = []
        for fam, (kind, bound) in guards.items():
            if kind == "min" and fused[fam] < bound:
                fused[fam] = bound
                floors_applied.append(f"{fam}>={bound:+.0f}")
            elif kind == "max" and fused[fam] > bound:
                fused[fam] = bound
                floors_applied.append(f"{fam}<={bound:+.0f}")

        # Clamp individual raw deltas to sane bounds.
        for f in FAMILIES:
            fused[f] = round(max(-55.0, min(55.0, fused[f])), 2)

        meta: Dict[str, Any] = {
            "method": route,
            "route": route,
            "route_reason": route_reason,
            "tiers_used": tiers_used,
            "tier_latencies_ms": tier_lats,
            "floors_applied": floors_applied,
            "sarcasm_polarity_override": sarcasm_override,
            "b_provider": self.tier_b.backend.active_provider,
            "c_model": self.tier_c.limbic_model if "C" in tiers_used else None,
            "c_method": c_meta.get("method") if c_meta else None,
        }
        return fused, appraisal, suppress, meta

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

    def run_track2_actor(
        self,
        step_result: MatrixStepResult,
        event: EmotionEvent,
        player: Any,
        *,
        is_human: bool = False,
    ) -> Dict[str, Any]:
        return self.tier_c.run_track2_actor(
            step_result, event, player, is_human=is_human
        )

    def tick(
        self,
        state: CharacterEmotionState,
        player: Any,
        world: Any,
        ticks: int = 1,
    ) -> Dict[str, Any]:
        return apply_tick_decay(state, player, ticks=ticks)
