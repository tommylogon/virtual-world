"""Python LLMClient for server-side agent execution (Phase 1 + task-999).

Talks directly to any OpenAI-compatible chat completions endpoint (LM Studio,
Ollama, OpenRouter, OpenAI, GonkaRouter, etc.) using ``requests`` (already a
core repo dependency). Includes:
  - Assistant ``'{'`` JSON prefill when ``suppress_local_thinking`` is enabled
    on JSON-mode calls (task-999), prepending ``'{'`` back before returning.
  - Automatic one-shot fallback if a provider rejects ``json_schema`` or a
    trailing assistant prefill message.
  - Clean token/timing metadata for diagnostics and Agent Lens.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Tuple

import requests


@dataclass
class LLMConfig:
    base_url: str = "http://127.0.0.1:1234/v1"
    api_key: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 1024
    timeout_s: float = 120.0
    suppress_local_thinking: bool = False
    reasoning_max_tokens: Optional[int] = None


@dataclass
class LLMResult:
    content: str
    reasoning: str = ""
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    raw: Dict[str, Any] = field(default_factory=dict)


class LLMClient:
    """Server-side OpenAI-compatible LLM client."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def _endpoint(self) -> str:
        base = self.config.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return f"{base}/chat/completions"

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        *,
        response_format: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        use_json_prefill: bool = False,
    ) -> Tuple[Dict[str, Any], bool]:
        msgs = [dict(m) for m in messages]
        prefilled = False
        is_json_mode = response_format is not None and response_format.get("type") in (
            "json_object",
            "json_schema",
        )
        if use_json_prefill and is_json_mode and (not msgs or msgs[-1].get("role") != "assistant"):
            msgs.append({"role": "assistant", "content": "{"})
            prefilled = True

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": msgs,
            "temperature": self.config.temperature if temperature is None else temperature,
            "max_tokens": self.config.max_tokens if max_tokens is None else max_tokens,
            "stream": stream,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        if self.config.reasoning_max_tokens is not None:
            payload["reasoning"] = {"max_tokens": int(self.config.reasoning_max_tokens)}
        return payload, prefilled

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        response_format: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResult:
        """Execute a non-streaming chat completion with clean fallbacks."""
        t0 = time.perf_counter()
        use_prefill = bool(self.config.suppress_local_thinking)
        payload, prefilled = self._build_payload(
            messages,
            response_format=response_format,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            use_json_prefill=use_prefill,
        )

        resp = requests.post(
            self._endpoint(),
            headers=self._headers(),
            json=payload,
            timeout=self.config.timeout_s,
        )

        # Fallback 1: provider rejected trailing assistant prefill
        if resp.status_code == 400 and prefilled:
            payload, prefilled = self._build_payload(
                messages,
                response_format=response_format,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                use_json_prefill=False,
            )
            resp = requests.post(
                self._endpoint(),
                headers=self._headers(),
                json=payload,
                timeout=self.config.timeout_s,
            )

        # Fallback 2: provider rejected json_schema -> retry with plain json_object
        if resp.status_code == 400 and response_format and response_format.get("type") == "json_schema":
            payload["response_format"] = {"type": "json_object"}
            resp = requests.post(
                self._endpoint(),
                headers=self._headers(),
                json=payload,
                timeout=self.config.timeout_s,
            )

        resp.raise_for_status()
        data = resp.json()
        lat_ms = (time.perf_counter() - t0) * 1000.0

        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        content = str(msg.get("content") or "")
        reasoning = str(msg.get("reasoning_content") or msg.get("reasoning") or "")

        if prefilled:
            stripped = content.lstrip()
            if not stripped.startswith("{"):
                content = "{" + content

        usage = data.get("usage") or {}
        return LLMResult(
            content=content,
            reasoning=reasoning,
            model=str(data.get("model") or self.config.model),
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            latency_ms=round(lat_ms, 1),
            raw=data,
        )

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        *,
        response_format: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterator[str]:
        """Yield content token chunks from an SSE chat-completions stream."""
        payload, prefilled = self._build_payload(
            messages,
            response_format=response_format,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            use_json_prefill=bool(self.config.suppress_local_thinking),
        )
        if prefilled:
            yield "{"
        with requests.post(
            self._endpoint(),
            headers=self._headers(),
            json=payload,
            stream=True,
            timeout=self.config.timeout_s,
        ) as resp:
            resp.raise_for_status()
            for raw_line in resp.iter_lines(decode_unicode=True):
                if not raw_line or not raw_line.startswith("data:"):
                    continue
                chunk = raw_line[5:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    obj = json.loads(chunk)
                    delta = ((obj.get("choices") or [{}])[0].get("delta") or {}).get("content")
                    if delta:
                        yield str(delta)
                except json.JSONDecodeError:
                    continue
