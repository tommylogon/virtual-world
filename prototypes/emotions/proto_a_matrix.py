"""Prototype A - Pure Deterministic Coupled Matrix + Autonomic Physics.

Zero LLM calls, zero ML models, sub-millisecond latency. Serves as both a
standalone soak/background emotion engine and the deterministic baseline for
comparing Prototypes B (semantic embeddings) and C (pre-Actor limbic LLM).
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional, Set

from prototypes.emotions.coupling import apply_matrix_step, apply_tick_decay
from prototypes.emotions.schema import (
    DIM_TO_FAMILY,
    FAMILIES,
    CharacterEmotionState,
    EmotionEvent,
    MatrixStepResult,
)

# Deterministic lexical cues for structured fallback on untagged speech/event text.
_HOSTILE_WORDS = {
    "bitch", "stupid", "idiot", "hate", "shut up", "useless", "pathetic", "loser",
    "worthless", "trash", "disgusting", "freak", "coward", "liar", "bastard",
    "get out", "leave me alone", "fuck", "screw you", "moron", "jerk",
}
_THREAT_WORDS = {
    "kill", "hurt", "weapon", "knife", "gun", "attack", "cornered", "trapped",
    "blood", "monster", "goblin", "threat", "hit", "punch", "strike", "dark",
    "scream", "locked", "abandoned", "leave", "leaving",
}
_WARM_WORDS = {
    "love", "thank", "thanks", "proud", "safe", "sorry", "forgive", "trust",
    "amazing", "kind", "care", "glad", "happy", "smile", "hug", "gift",
    "saved", "missed", "sweet", "wonderful", "here for you",
}
_DISGUST_WORDS = {
    "rot", "rotten", "filth", "vomit", "blood", "corpse", "slimy", "gross",
    "stink", "sewage", "maggot", "cruel", "hypocrite", "fawning", "vile",
}
_SHAME_WORDS = {
    "embarrass", "humiliat", "laughed at", "exposed", "staring", "caught",
    "secret", "stupid mistake", "hid", "hiding", "ashamed", "failure",
}
_GUILT_WORDS = {
    "broke", "ruined", "destroyed", "forgot", "lied", "let down", "betrayed",
    "failed", "my fault", "harmed", "threw it away", "without telling",
}
_ENVY_WORDS = {
    "credit", "promoted", "won", "staff", "chief", "trophy", "praise",
    "better than", "richer", "everything", "has what i want",
}
_JEALOUS_WORDS = {
    "flirt", "flirting", "affair", "someone else", "rival", "more time alone",
    "texting", "ignoring me", "with her", "with him", "cheating",
}


def _contains_any(text_low: str, phrases: Set[str], *, skip_negated: bool = False) -> List[str]:
    found = []
    for p in phrases:
        if " " in p:
            idx = text_low.find(p)
            if idx != -1:
                if skip_negated and re.search(r"\b(?:don't|dont|not|never|no)\s+$", text_low[max(0, idx - 14) : idx]):
                    continue
                found.append(p)
        else:
            m = re.search(r"\b" + re.escape(p), text_low)
            if m:
                if skip_negated and re.search(r"\b(?:don't|dont|not|never|no)\s+$", text_low[max(0, m.start() - 14) : m.start()]):
                    continue
                found.append(p)
    return found


def _memory_family_boosts(recalled_memories: List[Dict[str, Any]]) -> Dict[str, float]:
    """Extract subtle emotional residue from recalled memories (both tags and memory_emotions)."""
    boosts: Dict[str, float] = {}
    for mem in recalled_memories[:4]:
        if not isinstance(mem, dict):
            continue
        entries = list(mem.get("memory_emotions") or [])
        if not entries and isinstance(mem.get("emotion"), dict):
            entries = [mem["emotion"]]
        for e in entries:
            lbl = str(e.get("label") or "").strip().lower()
            try:
                inten = float(e.get("intensity") or 5.0)
            except (TypeError, ValueError):
                inten = 5.0
            fam = DIM_TO_FAMILY.get(lbl, lbl if lbl in FAMILIES else "")
            if fam in FAMILIES:
                boosts[fam] = boosts.get(fam, 0.0) + min(14.0, inten * 1.4)
        for tag in mem.get("tags") or []:
            t = str(tag).strip().lower()
            if t in ("abandonment", "trauma", "danger", "threat"):
                boosts["fear"] = boosts.get("fear", 0.0) + 10.0
            elif t in ("rejection", "humiliation", "shame"):
                boosts["shame"] = boosts.get("shame", 0.0) + 10.0
                boosts["sadness"] = boosts.get("sadness", 0.0) + 8.0
            elif t in ("betrayal", "blowup", "fight"):
                boosts["anger"] = boosts.get("anger", 0.0) + 8.0
                boosts["fear"] = boosts.get("fear", 0.0) + 8.0
            elif t in ("warmth", "affection", "comfort"):
                boosts["love"] = boosts.get("love", 0.0) + 8.0
    return boosts


class ProtoAMatrixEngine:
    """Prototype A: Pure deterministic rule + coupled matrix + autonomic body engine."""

    name = "Proto A - Deterministic Coupled Matrix"

    def appraise(
        self,
        state: CharacterEmotionState,
        event: EmotionEvent,
        player: Any,
        world: Any,
        recalled_memories: List[Dict[str, Any]],
        rel_profile: Optional[Dict[str, Any]] = None,
    ) -> tuple[Dict[str, float], str, bool, Dict[str, Any]]:
        deltas: Dict[str, float] = {f: 0.0 for f in FAMILIES}
        reasons: List[str] = []
        suppress = False

        text = f"{event.summary} {event.speech_text}".strip()
        low = text.lower()
        tags = {t.lower() for t in event.tags}
        witness_count = len(event.witnesses)
        has_expectation = bool(event.expectations)

        rel = rel_profile or {}
        closeness = float(rel.get("closeness", 0.0) or 0.0)
        trust = float(rel.get("trust", 0.0) or 0.0)
        is_close = closeness >= 35.0 or trust >= 0.45
        is_hostile_rel = closeness <= -25.0 or trust <= -0.4

        # 1. Structured world event kinds (goals, threats, exposure, discrepancies, repair).
        if event.kind == "goal":
            if "blocked" in tags or "failed" in low:
                deltas["anger"] += 26.0
                deltas["sadness"] += 12.0
                reasons.append("an important goal was blocked")
            elif "reached" in tags or "achieved" in low:
                deltas["happiness"] += 34.0
                deltas["calm"] += 12.0
                reasons.append("achieved a valued goal")
            elif "rival_holds_goal_item" in tags or "envy" in tags:
                deltas["envy"] += 38.0
                deltas["anger"] += 12.0
                reasons.append("someone else holds what I have been working toward")
        elif event.kind == "threat":
            deltas["fear"] += 42.0
            deltas["surprise"] += 18.0
            reasons.append("faced a direct threat")
        elif event.kind == "exposure":
            deltas["shame"] += 34.0 + min(18.0, witness_count * 6.0)
            deltas["fear"] += 14.0
            reasons.append("felt exposed in front of others")
        elif event.kind == "discrepancy":
            deltas["surprise"] += 34.0
            if "betrayal" in tags:
                deltas["anger"] += 25.0
                deltas["sadness"] += 28.0
                deltas["love"] -= 20.0
                reasons.append("expectation broke in a way that feels like betrayal")
            else:
                deltas["fear"] += 16.0
                reasons.append("reality contradicted what I expected")
        elif event.kind in ("check_facts", "reassure"):
            deltas["shame"] -= 28.0
            deltas["fear"] -= 24.0
            deltas["jealousy"] -= 22.0
            deltas["calm"] += 22.0
            deltas["happiness"] += 14.0
            if is_close:
                deltas["love"] += 10.0
            reasons.append("checked the facts directly and received clear reassurance")
        elif event.kind == "repair":
            deltas["guilt"] -= 22.0
            deltas["shame"] -= 14.0
            deltas["calm"] += 16.0
            deltas["happiness"] += 10.0
            reasons.append("took concrete steps to repair the harm")

        # 2. Lexical cues from speech / event description (modulated by relationship, witnesses & tone!).
        ptone = (event.perceived_tone or "").strip().lower()
        is_relief_event = (
            event.kind in ("check_facts", "reassure", "repair") or "reassure" in tags
        ) and ptone not in ("sarcastic", "mocking", "hostile", "cold", "strained")
        is_playful_tease = ptone == "teasing"
        is_negative_tone = ptone in ("sarcastic", "mocking", "hostile", "cold")
        is_strained_tone = ptone == "strained" or event.tone_strained

        hostile_hits = [] if (is_relief_event or is_playful_tease) else _contains_any(low, _HOSTILE_WORDS, skip_negated=True)
        threat_hits = [] if (is_relief_event or is_playful_tease) else _contains_any(low, _THREAT_WORDS, skip_negated=True)
        warm_hits = [] if (is_negative_tone or is_strained_tone) else _contains_any(low, _WARM_WORDS)
        disgust_hits = [] if (is_relief_event or is_playful_tease) else _contains_any(low, _DISGUST_WORDS)
        shame_hits = [] if (is_relief_event or is_playful_tease) else _contains_any(low, _SHAME_WORDS)
        guilt_hits = [] if (is_relief_event or is_playful_tease) else _contains_any(low, _GUILT_WORDS)
        envy_hits = [] if (is_relief_event or is_playful_tease) else _contains_any(low, _ENVY_WORDS)
        jealous_hits = [] if (is_relief_event or is_playful_tease) else _contains_any(low, _JEALOUS_WORDS)

        # Perceived speech delivery tone modulation (task-994).
        if is_playful_tease:
            deltas["happiness"] += 22.0
            deltas["love"] += 14.0 if is_close else 4.0
            deltas["calm"] += 6.0
            reasons.append("caught the playful teasing tone and took it as affectionate banter")
        elif ptone in ("sarcastic", "mocking"):
            deltas["anger"] += 24.0
            deltas["shame"] += 22.0 + min(12.0, witness_count * 4.0)
            deltas["happiness"] -= 28.0
            if is_close:
                deltas["sadness"] += 22.0
                deltas["love"] -= 18.0
            reasons.append(f"felt stung by the {ptone} delivery")
        elif is_strained_tone:
            deltas["fear"] += 16.0
            deltas["sadness"] += 14.0
            deltas["surprise"] += 14.0
            deltas["calm"] -= 14.0
            reasons.append("noticed the speaker's voice sounded tight and strained beneath their words")
        elif ptone == "hostile":
            deltas["anger"] += 20.0
            deltas["happiness"] -= 18.0
            if is_close:
                deltas["sadness"] += 16.0
                deltas["love"] -= 14.0
            reasons.append("felt the sharp hostility in their delivery")
        elif ptone == "cold":
            deltas["sadness"] += 16.0 if is_close else 6.0
            deltas["anger"] += 10.0
            deltas["happiness"] -= 14.0
            if is_close:
                deltas["love"] -= 12.0
            reasons.append("felt pushed away by the cold, flat delivery")
        elif ptone == "apologetic":
            deltas["anger"] -= 14.0
            deltas["calm"] += 10.0
            if is_close:
                deltas["love"] += 6.0
            reasons.append("heard genuine contrition in their voice")
        elif ptone == "guarded":
            deltas["fear"] += 8.0
            deltas["sadness"] += 6.0
            deltas["calm"] -= 8.0
            reasons.append("picked up guarded tension in their voice")
        elif ptone == "warm":
            deltas["happiness"] += 14.0
            deltas["love"] += 12.0 if is_close else 4.0
            deltas["calm"] += 10.0
            reasons.append("heard genuine warmth in their delivery")

        if (hostile_hits or ("insult" in tags and not is_playful_tease)) and not is_playful_tease:
            if is_close:
                # Close partner / friend snapping hits sadness, love, shame, fear, anger together!
                deltas["sadness"] += 36.0
                deltas["anger"] += 26.0
                deltas["fear"] += 18.0
                deltas["disgust"] += 12.0
                deltas["love"] -= 20.0
                deltas["happiness"] -= 35.0
                if has_expectation:
                    deltas["surprise"] += 22.0
                    deltas["sadness"] += 8.0
                if witness_count > 0:
                    deltas["shame"] += 22.0 + min(12.0, witness_count * 4.0)
                    reasons.append("stung and humiliated by someone I care about snapping in front of others")
                else:
                    deltas["shame"] += 10.0
                    reasons.append("hurt and shaken by someone I trust lashing out at me")
            else:
                deltas["anger"] += 38.0
                deltas["disgust"] += 20.0
                deltas["fear"] += 8.0 if not is_hostile_rel else 12.0
                deltas["happiness"] -= 12.0
                if witness_count > 0:
                    deltas["shame"] += 8.0
                reasons.append("provoked by hostile words from someone I do not trust")

        if threat_hits or "danger" in tags:
            deltas["fear"] += 24.0
            reasons.append("picked up danger cues")

        is_hostile_event = (not is_playful_tease) and bool(
            hostile_hits or "insult" in tags or "betrayal" in tags or is_negative_tone
        )
        if (warm_hits or "affection" in tags or "praise" in tags) and not is_hostile_event:
            if "reassure" not in tags and event.kind not in ("check_facts", "reassure"):
                deltas["happiness"] += 24.0
                deltas["love"] += 22.0 if is_close else 10.0
                deltas["calm"] += 10.0
                reasons.append("received warmth or kindness")

        if disgust_hits or "contamination" in tags:
            deltas["disgust"] += 34.0
            reasons.append("triggered revulsion or contamination disgust")

        if guilt_hits or "transgression" in tags:
            deltas["guilt"] += 38.0
            reasons.append("caused harm or violated my own standard")

        if shame_hits or "hid_mistake" in tags:
            deltas["shame"] += 36.0 + min(14.0, witness_count * 5.0)
            reasons.append("feared being exposed and judged")

        if envy_hits or "envy" in tags:
            deltas["envy"] += 34.0
            reasons.append("compared myself against someone holding what I want")

        if jealous_hits or "rival_flirt" in tags or "jealousy" in tags:
            deltas["jealousy"] += 40.0 if is_close else 22.0
            deltas["fear"] += 14.0
            reasons.append("sensed a threat to a valued bond")

        # 3. Memory-recall emotional residue (re-feeling past experiences).
        # During a hostile/betrayal hit, recalling past warmth sharpens contrast hurt
        # (sadness + love erosion) rather than magically boosting live warmth.
        # During explicit reassurance/check_facts relief, old trauma memories are muted.
        mem_boosts = {} if is_relief_event else _memory_family_boosts(recalled_memories)
        for fam, b in mem_boosts.items():
            if is_hostile_event and fam in ("love", "happiness", "calm"):
                deltas["sadness"] += b * 0.75
                deltas["love"] -= b * 0.45
            else:
                deltas[fam] += b
        if mem_boosts:
            top_m = max(mem_boosts.items(), key=lambda kv: kv[1])[0]
            reasons.append(f"old memories surfaced and pulled {top_m} back into the moment")

        # 4. Character trauma / fear_tags match against event + recalled memories.
        fear_tags = {str(t).lower() for t in (getattr(player, "fear_tags", None) or [])}
        hit_fears = fear_tags & (tags | set(re.findall(r"[a-z_]+", low)))
        if hit_fears:
            deltas["fear"] += 28.0
            reasons.append(f"hit a personal fear trigger ({', '.join(sorted(hit_fears))})")

        appraisal = "; ".join(reasons) if reasons else "registered the moment without a strong emotional jolt"
        return deltas, appraisal, suppress, {"method": "deterministic_rules", "memory_boosts": mem_boosts}

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
