"""Server-side Memory Manager & Intermediator Reconsolidation (Phase 3, task-1003).

Replaces browser-side ``synthesizeConsciousThought`` in ``memory-context.ts``:
  - Synthesizes recalled memory traces into ONE mood-congruent first-person
    conscious thought using ``LLMClient`` + ``JSON_OBJECT``.
  - Caches by ``cue_signature`` per character so repeated sub-steps in the same
    turn never spam duplicate intermediator LLM calls.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from engine.agent.json_schemas import JSON_OBJECT
from engine.agent.llm_client import LLMClient
from engine.agent.response_parser import repair_json


class MemoryManager:
    """Server-side memory reconsolidation with cue-signature caching."""

    def __init__(self) -> None:
        self._cache: Dict[str, tuple[str, str]] = {}  # char_name -> (cue_sig, thought)

    @staticmethod
    def compute_cue_signature(
        area: str,
        mood: str,
        memories: List[Dict[str, Any]],
        recent_heard: List[str],
    ) -> str:
        raw = "|".join(
            [
                area.lower().strip(),
                mood.lower().strip(),
                ";".join(str(m.get("id") or m.get("text", "")[:40]) for m in memories[:6]),
                ";".join(recent_heard[-3:]),
            ]
        )
        return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]

    def synthesize_thought(
        self,
        llm: LLMClient,
        player: Any,
        *,
        area: str = "",
        present: Optional[List[str]] = None,
        memories: Optional[List[Dict[str, Any]]] = None,
        recent_heard: Optional[List[str]] = None,
    ) -> str:
        """Synthesize recalled traces into one brief conscious thought (cached)."""
        mems = list(memories or [])[:6]
        if not mems:
            return ""
        mood = getattr(player, "emotion", "neutral") or "neutral"
        heard = list(recent_heard or [])
        sig = self.compute_cue_signature(area, mood, mems, heard)
        cached = self._cache.get(player.name)
        if cached and cached[0] == sig:
            return cached[1]

        trace_lines = [f"- {str(m.get('text') or '').strip()}" for m in mems if m.get("text")]
        if not trace_lines:
            return ""

        present_str = ", ".join(present or []) or "no one else"
        heard_block = f"\nRecent words heard: {' | '.join(heard[-3:])}" if heard else ""
        prompt = (
            f'You are the inner memory reconsolidator for "{player.name}".\n'
            f"Current location: {area or 'unknown'}. Present: {present_str}. Current mood: {mood}.{heard_block}\n"
            "Recalled memory traces:\n"
            + "\n".join(trace_lines)
            + "\nSynthesize these traces into ONE brief, mood-congruent first-person conscious thought "
            "(2-4 sentences). Do not use bullet points, emojis, or meta-labels.\n"
            'Return ONLY valid JSON: {"thought": "...", "importance": 1-10}'
        )
        try:
            res = llm.chat([{"role": "user", "content": prompt}], response_format=JSON_OBJECT)
            obj, _ = repair_json(res.content)
            thought = str((obj or {}).get("thought") or "").strip()
        except Exception:
            thought = ""

        self._cache[player.name] = (sig, thought)
        return thought
