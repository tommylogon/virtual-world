"""LLM response parser and JSON repair for Python agent turns (Phase 1).

Ports ``static/js/agent/response-parser.ts`` + ``repairJSON`` into Python so
structured agent outputs (``inner_monologue``, ``action``, ``item``, ``target``,
``text``, ``speech``, ``volume``, ``tone``, ``emote``, ``learned_names``) can be
parsed and tested deterministically without a browser.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from engine.speech_tone import normalize_speech_tone

VALID_VOLUMES = frozenset({"whisper", "say", "sing", "shout", "scream"})
_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
_THINK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)


@dataclass
class ParsedTurn:
    inner: str = ""
    action: Optional[str] = None
    item: Optional[str] = None
    target: Optional[str] = None
    text: Optional[str] = None
    speech: Optional[str] = None
    speech_volume: str = "say"
    speech_tone: Optional[str] = None
    speech_target: Optional[str] = None
    emote: Optional[str] = None
    learned_names: List[str] = field(default_factory=list)
    parse_error: Optional[str] = None
    repaired: bool = False


def strip_thinking_and_fences(raw: str) -> str:
    """Remove <think>...</think> blocks and markdown code fences."""
    s = _THINK_RE.sub("", str(raw or "")).strip()
    m = _FENCE_RE.search(s)
    if m:
        s = m.group(1).strip()
    return s


def repair_json(raw: str) -> Tuple[Optional[Dict[str, Any]], bool]:
    """Parse a JSON object from messy LLM output, repairing common truncation."""
    s = strip_thinking_and_fences(raw)
    if not s:
        return None, False

    # Fast path: valid JSON object as-is
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return obj, False
    except json.JSONDecodeError:
        pass

    # Extract from first '{' onward
    start = s.find("{")
    if start == -1:
        return None, False
    frag = s[start:]

    # Try up to last '}'
    end = frag.rfind("}")
    if end > 0:
        try:
            obj = json.loads(frag[: end + 1])
            if isinstance(obj, dict):
                return obj, True
        except json.JSONDecodeError:
            pass

    # Repair trailing commas and unclosed strings/braces/brackets
    cleaned = re.sub(r",\s*([}\]])", r"\1", frag)
    in_str = False
    escape = False
    stack: List[str] = []
    for ch in cleaned:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_str:
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if not in_str:
            if ch in "{[":
                stack.append("}" if ch == "{" else "]")
            elif ch in "}]" and stack and stack[-1] == ch:
                stack.pop()

    repaired = cleaned
    if in_str:
        repaired += '"'
    repaired = repaired.rstrip(", \t\r\n")
    repaired += "".join(reversed(stack))

    try:
        obj = json.loads(repaired)
        if isinstance(obj, dict):
            return obj, True
    except json.JSONDecodeError:
        pass

    return None, False


def _clean_str(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    t = val.strip()
    if not t or t in ("...", "null", "none", "None") or re.fullmatch(r"<[^>]+>", t):
        return None
    return t


def parse_turn_response(raw: str, *, allow_action: bool = True) -> ParsedTurn:
    """Parse a raw LLM response into a normalized ParsedTurn."""
    obj, repaired = repair_json(raw)
    if obj is None:
        return ParsedTurn(parse_error="Failed to parse JSON object from LLM response")

    inner = _clean_str(obj.get("inner_monologue")) or ""
    speech = _clean_str(obj.get("speech"))
    raw_vol = (_clean_str(obj.get("volume")) or "say").lower()
    volume = raw_vol if raw_vol in VALID_VOLUMES else "say"
    tone = normalize_speech_tone(_clean_str(obj.get("tone")))
    emote = _clean_str(obj.get("emote"))

    raw_names = obj.get("learned_names")
    learned: List[str] = []
    if isinstance(raw_names, list):
        for n in raw_names:
            cn = _clean_str(n)
            if cn:
                learned.append(cn)
        learned = learned[:5]

    action = _clean_str(obj.get("action")) if allow_action else None
    item = _clean_str(obj.get("item")) if allow_action else None
    target = _clean_str(obj.get("target")) if allow_action else None
    text = _clean_str(obj.get("text")) if allow_action else None

    speech_target = _clean_str(obj.get("speech_target"))
    if not speech_target and speech and volume == "whisper" and not action:
        speech_target = _clean_str(obj.get("target"))

    return ParsedTurn(
        inner=inner,
        action=action,
        item=item,
        target=target,
        text=text,
        speech=speech,
        speech_volume=volume,
        speech_tone=tone,
        speech_target=speech_target,
        emote=emote,
        learned_names=learned,
        parse_error=None,
        repaired=repaired,
    )
