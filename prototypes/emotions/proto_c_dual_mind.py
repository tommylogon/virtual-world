"""Prototype C - Dual-Track Parallel Mind (Pre-Actor Limbic Appraiser LLM + Engine Body).

Track 1 (Pre-Actor Limbic Appraiser):
  Runs a fast local LLM on LM Studio (mirroring task-948's cue-gated
  getMemoryLLMClient() stage) BEFORE the Actor wakes up. Reads event + witnesses
  + recalled memories + Active Mind expectations + prior mood + vulnerability +
  traits/fears and outputs a signed (+/-) multi-emotion shift vector across all
  13 Matrix families plus a concise gut appraisal and suppression impulse.

Engine Physics Layer (strictly outside LLM control):
  Enforces vulnerability scaling, prior-moodiness tilt, sparse 13x13 coupling W,
  trait/memory/witness secondary emotions, Emotional Overload, and the 8-channel
  Autonomic Body with physiological inertia.

Track 2 (Actor Conscious Mind):
  Wakes up inside that reacting body via `run_track2_actor(...)` and writes
  voluntary inner_monologue, speech, emote, and action - unable to wish away its
  flushed neck, clenched jaw, or pounding heart.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

from prototypes.emotions.autonomic import compute_vulnerability_load, render_vocal_interruption
from prototypes.emotions.coupling import apply_matrix_step, apply_tick_decay
from prototypes.emotions.proto_a_matrix import ProtoAMatrixEngine
from prototypes.emotions.schema import (
    FAMILIES,
    FAMILY_BASELINES,
    CharacterEmotionState,
    EmotionEvent,
    MatrixStepResult,
)

#: Engine-owned numeric scale for qualitative Track 1 intensity bands.
#: The LLM classifies meaning/direction only; Python owns 100% of the numeric values.
QUALITATIVE_BAND_DELTAS: Dict[str, float] = {
    "slight": 6.0,
    "up_slight": 6.0,
    "+slight": 6.0,
    "mild": 12.0,
    "up_mild": 12.0,
    "+mild": 12.0,
    "moderate": 18.0,
    "up_moderate": 18.0,
    "+moderate": 18.0,
    "strong": 26.0,
    "up_strong": 26.0,
    "+strong": 26.0,
    "extreme": 34.0,
    "up_extreme": 34.0,
    "+extreme": 34.0,
    "drop_slight": -6.0,
    "down_slight": -6.0,
    "-slight": -6.0,
    "drop_mild": -12.0,
    "down_mild": -12.0,
    "-mild": -12.0,
    "drop_moderate": -20.0,
    "down_moderate": -20.0,
    "-moderate": -20.0,
    "drop_strong": -28.0,
    "down_strong": -28.0,
    "-strong": -28.0,
    "drop_extreme": -32.0,
    "down_extreme": -32.0,
    "-extreme": -32.0,
}


def _parse_qualitative_delta(val: Any) -> Optional[float]:
    """Convert a qualitative band label (or legacy fallback number) to an engine-owned delta."""
    if isinstance(val, str):
        key = val.strip().lower().replace(" ", "_")
        if key in QUALITATIVE_BAND_DELTAS:
            return QUALITATIVE_BAND_DELTAS[key]
        try:
            num = float(key)
        except ValueError:
            return None
        return max(-32.0, min(34.0, num))
    if isinstance(val, (int, float)):
        return max(-32.0, min(34.0, float(val)))
    return None


LIMBIC_SYSTEM_PROMPT = """You are Track 1 (the fast, automatic emotional appraisal system) inside a character's mind.
You do NOT choose actions or dialogue, and you do NOT output numbers. You ONLY classify how THIS NEW incoming event shifts relevant emotions using qualitative intensity bands, given who the character is, what they remember, what they expected, who is watching, and what they were already feeling.

Valid emotion keys (use ONLY keys from this list):
anger, disgust, envy, fear, happiness, jealousy, love, sadness, shame, guilt, calm, surprise, arousal

Valid shift bands (use ONLY these string labels - NEVER raw numbers):
- Increasing: "slight", "mild", "moderate", "strong", "extreme"
- Decreasing: "drop_slight", "drop_mild", "drop_moderate", "drop_strong"

Rules:
- Output INCREMENTAL SHIFTS caused by THIS event only (NOT the prior mood itself). Omit emotions that did not change.
- Reserve "strong" and "extreme" for genuine shocks, direct betrayals, or major threats; normal tense remarks are "slight" or "mild".
- Reassurance, apology, kindness, or checking facts that relieves worry MUST use decreasing bands on fear/shame/sadness/anger (e.g. "drop_moderate") and increasing bands on calm/happiness (e.g. "mild" or "moderate").
- Real negative events shift MULTIPLE emotions simultaneously, including drops (e.g. a trusted partner snapping: sadness "strong", anger "moderate", shame "moderate", fear "mild", love "drop_mild", happiness "drop_strong", calm "drop_moderate").
- Separate shame (exposed/humiliated -> shrink/hide) from guilt (remorse for breaking something, lying, or violating own values -> confess/repair).
- Separate envy (wanting an object/status/credit another holds) from jealousy (fearing loss of a valued relationship to a rival).
- Respect the perceived delivery tone when provided: playful teasing from a steady close friend is affectionate banter; mocking or sarcastic delivery stings even when words look polite; a strained/forced voice under warm words signals hidden distress (fear/unease, NOT calm).
- "arousal" means romantic or sexual attraction ONLY (omit unless genuinely romantic/erotic).
- Set "suppress": true only if the character instinctively tries to hide or mask what they feel.
- Output ONLY a single valid JSON object with no markdown fences and no extra text:
{"gut_appraisal":"one concise sentence in first person","deltas":{"fear":"mild","calm":"drop_mild"},"suppress":false}"""


ACTOR_SYSTEM_PROMPT = """You are Track 2 (the conscious mind) of a character living inside a physical body in VirtualWorld.
Your body's reactions (pounding pulse, hot face, tight jaw, knot in stomach, tears) are ALREADY happening outside your control - you can try to hide them, act through them, breathe, snap, or ask a question, but you cannot pretend your body is calm when it is not.
Output ONLY a single valid JSON object:
{"inner_monologue":"...","speech":"... or null","emote":"third-person body language phrase or null","action":"wait | speak | examine | leave | apologize | confront | breathe"}"""


def _extract_json_object(raw: str) -> Optional[Dict[str, Any]]:
    """Extract the first valid JSON object from raw LLM output (handles thinking tags, fences, and unary +)."""
    if not raw:
        return None
    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.S).strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I | re.M).strip()
    # Small local models frequently emit unary plus signs like `"calm": +30` which strict JSON rejects.
    cleaned = re.sub(r"(:\s*)\+(?=\d)", r"\1", cleaned)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    # Brace-balanced scan for embedded JSON object.
    start = cleaned.find("{")
    while start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(cleaned)):
            ch = cleaned[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = cleaned[start : i + 1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict):
                            return parsed
                    except Exception:
                        break
        start = cleaned.find("{", start + 1)
    return None


def _call_lm_studio_chat(
    messages: List[Dict[str, str]],
    *,
    url: str = "http://127.0.0.1:1234/v1/chat/completions",
    model_id: str = "qwen3.5-4b",
    max_tokens: Optional[int] = None,
    temperature: float = 0.25,
    timeout: int = 60,
    reasoning_effort: str = "none",
    json_prefill: bool = True,
) -> str:
    """Call an OpenAI-compatible local chat endpoint mirroring LLMClient's thinking controls.

    Matches static/js/llm-client.ts & routes/benchmark.py:
      - Omitting max_tokens (None) grants Auto/model-max headroom so thinking models
        do not starve before emitting JSON.
      - reasoning_effort="none" disables thinking via provider flags AND (when
        json_prefill=True) prefills an assistant `{` turn so local thinking models
        (gemma-4-e4b, lfm3-1.7b) skip hidden scratchpads and jump directly into JSON.
      - Never dumps raw reasoning_content into content; retries once without a hard
        max_tokens cap if finish_reason == "length".
    """
    def _send(cap: Optional[int], use_prefill: bool) -> Tuple[str, str]:
        req_msgs = list(messages)
        if use_prefill:
            req_msgs.append({"role": "assistant", "content": "{"})
        body: Dict[str, Any] = {
            "model": model_id,
            "messages": req_msgs,
            "temperature": temperature,
        }
        if cap is not None and cap > 0:
            body["max_tokens"] = cap
        if reasoning_effort == "none":
            body["enable_thinking"] = False
            body["reasoning"] = {"exclude": True}
            body["extra_body"] = {"thinking": {"type": "disabled"}}
        elif reasoning_effort and reasoning_effort != "default":
            body["reasoning_effort"] = reasoning_effort
            body["reasoning"] = {"effort": reasoning_effort}
            body["extra_body"] = {"thinking": {"type": "enabled"}}
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choice = data["choices"][0]
            msg = choice["message"]
            content = (msg.get("content") or "").strip()
            finish = str(choice.get("finish_reason") or "")
            if use_prefill and content and not content.startswith("{") and not content.startswith("```"):
                content = "{" + content
            return content, finish

    use_prefill = bool(json_prefill and reasoning_effort == "none")
    content, finish = _send(max_tokens, use_prefill)
    # Mirror LLMClient length-truncation retry: if a hard cap cut off the JSON,
    # retry once with Auto (max_tokens=None).
    if (finish == "length" or not content) and max_tokens is not None:
        content, _ = _send(None, use_prefill)
    return content


class ProtoCDualMindEngine:
    """Prototype C: Pre-Actor Limbic Appraiser LLM + Deterministic Matrix & Autonomic Body."""

    name = "Proto C - Dual-Track Parallel Mind (Limbic LLM + Body)"

    def __init__(
        self,
        *,
        lm_studio_url: str = "http://127.0.0.1:1234/v1/chat/completions",
        limbic_model: str = "qwen3.5-4b",
        actor_model: Optional[str] = None,
        offline: bool = False,
        llm_fn: Optional[Callable[[List[Dict[str, str]]], str]] = None,
    ):
        self.lm_studio_url = lm_studio_url
        self.limbic_model = limbic_model
        self.actor_model = actor_model or limbic_model
        self.offline = offline
        self._custom_llm = llm_fn
        self._fallback = ProtoAMatrixEngine()

    def _cue_signature(
        self,
        event: EmotionEvent,
        recalled_memories: List[Dict[str, Any]],
        vuln_load: float,
    ) -> str:
        blob = json.dumps(
            {
                "kind": event.kind,
                "summary": event.summary,
                "speech": event.speech_text,
                "tone": event.perceived_tone or event.speech_tone,
                "source": event.source_name,
                "witnesses": sorted(event.witnesses),
                "expectations": list(event.expectations),
                "mems": [m.get("id") or m.get("text") for m in recalled_memories[:3]],
                "vuln_bucket": round(vuln_load, 1),
            },
            sort_keys=True,
        )
        return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]

    def _build_limbic_prompt(
        self,
        state: CharacterEmotionState,
        event: EmotionEvent,
        player: Any,
        recalled_memories: List[Dict[str, Any]],
        rel_profile: Optional[Dict[str, Any]],
        vuln_factors: List[str],
        *,
        structural_hint: str = "",
    ) -> str:
        char_name = getattr(player, "name", "Character")
        personality = str(getattr(player, "personality", "") or "").strip()
        traits = list((getattr(player, "traits", None) or {}).keys()) if isinstance(getattr(player, "traits", None), dict) else list(getattr(player, "traits", None) or [])
        fears = list(getattr(player, "fear_tags", None) or [])

        mood_phrases: List[str] = []
        for f in FAMILIES:
            diff = state.families[f] - FAMILY_BASELINES[f]
            if diff >= 25.0:
                mood_phrases.append(f"strongly elevated {f}")
            elif diff >= 10.0:
                mood_phrases.append(f"mildly elevated {f}")
            elif diff <= -20.0:
                mood_phrases.append(f"depleted {f}")
        prior_mood_line = ", ".join(mood_phrases) if mood_phrases else "steady baseline"
        rel = rel_profile or {}
        rel_line = (
            f"Relationship with {event.source_name}: closeness={rel.get('closeness', 0)}, "
            f"role={rel.get('role', 'acquaintance')}, summary={rel.get('summary', 'none')}"
            if event.source_name
            else "No specific other character targeted."
        )
        mem_lines = [f"- {m.get('text', '')}" for m in recalled_memories[:4]]
        mem_block = "\n".join(mem_lines) if mem_lines else "(none)"
        exp_block = "; ".join(event.expectations) if event.expectations else "(none)"
        wit_block = ", ".join(event.witnesses) if event.witnesses else "alone (no witnesses)"
        vuln_block = ", ".join(vuln_factors) if vuln_factors else "rested and physically fine"

        target_lines: List[str] = []
        for tname, tfams in (state.target_families or {}).items():
            raised_t = [
                f"{fam}"
                for fam, val in tfams.items()
                if fam != "calm" and (float(val) - FAMILY_BASELINES.get(fam, 10.0)) >= 14.0
            ]
            if raised_t:
                target_lines.append(f"{tname}: {', '.join(raised_t[:3])}")
        target_block = "; ".join(target_lines) if target_lines else "(none yet)"

        tone_line = ""
        if event.perceived_tone or event.tone_perception_note:
            tone_desc = event.tone_perception_note or f"sounded {event.perceived_tone}"
            tone_line = f"Perceived delivery tone: {event.perceived_tone or 'plain'} ({tone_desc})\n"

        return (
            f"Character: {char_name}\n"
            f"Personality: {personality or 'ordinary person'}\n"
            f"Traits: {', '.join(traits) if traits else 'none'} | Fears: {', '.join(fears) if fears else 'none'}\n"
            f"Physical vulnerability right now: {vuln_block}\n"
            f"Prior mood going into this moment: {prior_mood_line}\n"
            f"Active feelings toward specific people: {target_block}\n"
            f"{rel_line}\n"
            f"Witnesses present: {wit_block}\n"
            f"Expectations before this moment: {exp_block}\n"
            f"Memories that just surfaced:\n{mem_block}\n"
            + (f"Structural engine cues: {structural_hint}\n" if structural_hint else "")
            + f"\nNEW EVENT ({event.kind}): {event.summary}\n"
            + (f"SPOKEN LINE from {event.source_name or 'someone'}: \"{event.speech_text}\"\n" if event.speech_text else "")
            + tone_line
            + "\nReturn ONLY the JSON emotional CHANGE (deltas) caused by this new event."
        )

    def appraise(
        self,
        state: CharacterEmotionState,
        event: EmotionEvent,
        player: Any,
        world: Any,
        recalled_memories: List[Dict[str, Any]],
        rel_profile: Optional[Dict[str, Any]] = None,
        *,
        structural_hint: str = "",
    ) -> Tuple[Dict[str, float], str, bool, Dict[str, Any]]:
        # Cue-change signature hashes external cues + raw vitals (NOT post-step autonomic
        # heart-rate feedback), so identical continuation cues actually skip redundant calls.
        ext_vuln_load, _ = compute_vulnerability_load(player, None)
        vuln_load, vuln_factors = compute_vulnerability_load(player, state)
        sig = self._cue_signature(event, recalled_memories, ext_vuln_load)

        # Cue-change gating (task-948 invariant): skip redundant LLM call if cue is identical.
        if sig == state.last_cue_signature and event.kind == "continuation":
            return (
                {f: 0.0 for f in FAMILIES},
                "unchanged scene cue; continuing current emotional momentum",
                False,
                {"method": "cue_gated_skip", "model": self.limbic_model},
            )
        state.last_cue_signature = sig

        if self.offline and self._custom_llm is None:
            deltas, appraisal, suppress, meta = self._fallback.appraise(
                state, event, player, world, recalled_memories, rel_profile
            )
            meta["method"] = "offline_fallback_proto_a"
            return deltas, appraisal, suppress, meta

        user_prompt = self._build_limbic_prompt(
            state,
            event,
            player,
            recalled_memories,
            rel_profile,
            vuln_factors,
            structural_hint=structural_hint,
        )
        messages = [
            {"role": "system", "content": LIMBIC_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        raw_out = ""
        try:
            if self._custom_llm is not None:
                raw_out = self._custom_llm(messages)
            else:
                raw_out = _call_lm_studio_chat(
                    messages,
                    url=self.lm_studio_url,
                    model_id=self.limbic_model,
                    max_tokens=512,
                    temperature=0.2,
                    reasoning_effort="none",
                    json_prefill=True,
                )
            parsed = _extract_json_object(raw_out)
        except Exception as exc:
            deltas, appraisal, suppress, meta = self._fallback.appraise(
                state, event, player, world, recalled_memories, rel_profile
            )
            meta["method"] = "llm_error_fallback_proto_a"
            meta["error"] = str(exc)
            return deltas, appraisal, suppress, meta

        if not parsed or not isinstance(parsed.get("deltas"), dict):
            deltas, appraisal, suppress, meta = self._fallback.appraise(
                state, event, player, world, recalled_memories, rel_profile
            )
            meta["method"] = "parse_error_fallback_proto_a"
            meta["raw_output"] = raw_out
            return deltas, appraisal, suppress, meta

        deltas = {f: 0.0 for f in FAMILIES}
        for key, val in parsed["deltas"].items():
            k = str(key).strip().lower()
            if k in deltas:
                mapped = _parse_qualitative_delta(val)
                if mapped is not None:
                    deltas[k] = mapped
        appraisal = str(parsed.get("gut_appraisal") or "").strip() or "reacted instinctively to the moment"
        suppress = bool(parsed.get("suppress", False))
        return (
            deltas,
            appraisal,
            suppress,
            {
                "method": "pre_actor_limbic_llm",
                "model": self.limbic_model if self._custom_llm is None else "custom_llm",
                "raw_output": raw_out,
            },
        )

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
        """Run Track 2 (Conscious Actor LLM) waking up inside Track 1's reacting body."""
        char_name = getattr(player, "name", "Character")
        personality = str(getattr(player, "personality", "") or "").strip()
        mem_lines = "\n".join(
            f"- {m.get('text', '')}" for m in step_result.recalled_memories[:3]
        ) or "(none)"

        actor_prompt = (
            f"You are {char_name}.\n"
            f"Personality: {personality or 'ordinary person'}\n\n"
            f"=== YOUR STATE ===\n"
            f"Mood: {step_result.prompt_your_state or 'You feel steady.'}\n\n"
            f"=== I REMEMBER ===\n{mem_lines}\n\n"
            f"=== JUST HAPPENED ===\n"
            f"{event.summary}"
            + (f'\n{event.source_name or "Someone"} said: "{event.speech_text}"' if event.speech_text else "")
            + (f"\nWitnesses present: {', '.join(event.witnesses)}" if event.witnesses else "")
            + "\n\nRespond as your conscious mind (Track 2) with ONLY valid JSON."
        )
        messages = [
            {"role": "system", "content": ACTOR_SYSTEM_PROMPT},
            {"role": "user", "content": actor_prompt},
        ]
        t0 = time.perf_counter()
        if self.offline and self._custom_llm is None:
            return {
                "offline": True,
                "latency_ms": 0.0,
                "actor_prompt": actor_prompt,
                "inner_monologue": "(offline mode - Track 2 LLM skipped)",
                "speech": None,
                "speech_after_involuntary": None,
                "emote": None,
                "action": "wait",
                "observer_still_sees": step_result.observer_tells_normal,
            }

        try:
            raw = (
                self._custom_llm(messages)
                if self._custom_llm is not None
                else _call_lm_studio_chat(
                    messages,
                    url=self.lm_studio_url,
                    model_id=self.actor_model,
                    max_tokens=None,
                    temperature=0.65,
                    reasoning_effort="none",
                    json_prefill=True,
                )
            )
            dt = (time.perf_counter() - t0) * 1000.0
            parsed = _extract_json_object(raw) or {}
            if not parsed and raw:
                parsed = {"inner_monologue": raw.strip(), "speech": None, "emote": None, "action": "wait"}
        except Exception as exc:
            return {
                "error": str(exc),
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "actor_prompt": actor_prompt,
                "observer_still_sees": step_result.observer_tells_normal,
            }

        speech = parsed.get("speech")
        vocal_break = render_vocal_interruption(
            str(speech or ""),
            step_result.autonomic,
            overloaded=step_result.overloaded,
            is_human=is_human,
        )
        return {
            "latency_ms": round(dt, 2),
            "model": self.actor_model,
            "actor_prompt": actor_prompt,
            "inner_monologue": parsed.get("inner_monologue"),
            "speech": speech,
            "speech_after_involuntary": vocal_break or speech,
            "vocal_interruption_fired": bool(vocal_break),
            "emote": parsed.get("emote"),
            "action": parsed.get("action"),
            "observer_still_sees": step_result.observer_tells_normal,
        }

    def tick(
        self,
        state: CharacterEmotionState,
        player: Any,
        world: Any,
        ticks: int = 1,
    ) -> Dict[str, Any]:
        return apply_tick_decay(state, player, ticks=ticks)
