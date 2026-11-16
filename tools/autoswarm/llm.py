"""tools/autoswarm/llm.py - Unified LLM client for ViWo AutoSwarm.

Routes requests across available providers:
- deepseek: api.deepseek.com (deepseek-chat)
- google: generativelanguage.googleapis.com (gemini-2.5-flash)
- alibaba: dashscope-intl.aliyuncs.com (qwen-plus)
- local: localhost:1234 (LM Studio fast models like qwen3.5-2b)

Credentials are loaded automatically from OpenCode auth.json, .env, or os.environ.
Never logs secret tokens or keys.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
REGISTRY_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "model_bench" / "model_registry.json"

def is_model_usable(model_id: str) -> bool:
    """Check if a model is flagged as blocked or do_not_use in the model registry."""
    if not REGISTRY_PATH.exists():
        return True
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)
        entry = registry.get(model_id)
        if entry and isinstance(entry, dict):
            if entry.get("status") in ("blocked", "do_not_use"):
                return False
    except Exception:
        pass
    return True

def _load_auth_credentials() -> Dict[str, Dict[str, Any]]:
    """Load credentials from opencode auth.json if present."""
    creds: Dict[str, Dict[str, Any]] = {}
    auth_path = Path.home() / ".local" / "share" / "opencode" / "auth.json"
    if auth_path.exists():
        try:
            with open(auth_path, "r", encoding="utf-8") as f:
                creds = json.load(f)
        except Exception:
            pass
    return creds

CREDS = _load_auth_credentials()

def get_api_key(provider: str) -> Optional[str]:
    """Retrieve API key for provider from auth.json or environment."""
    if provider in CREDS and isinstance(CREDS[provider], dict) and "key" in CREDS[provider]:
        return CREDS[provider]["key"]
    env_keys = {
        "deepseek": ["DEEPSEEK_API_KEY"],
        "google": ["GOOGLE_GEMINI_API_KEY", "GEMINI_API_KEY"],
        "alibaba": ["ALIBABA_API_KEY", "DASHSCOPE_API_KEY"],
        "groq": ["GROQ_API_KEY"],
        "mistral": ["MISTRAL_API_KEY"],
    }
    for env_var in env_keys.get(provider, []):
        val = os.environ.get(env_var)
        if val:
            return val
    return None

def call_deepseek(messages: List[Dict[str, str]], model: str = "deepseek-chat", max_tokens: int = 1000, temperature: float = 0.6) -> str:
    if not is_model_usable(model):
        raise ValueError(f"Model '{model}' is flagged as blocked or do_not_use in model registry.")
    key = get_api_key("deepseek")
    if not key:
        raise ValueError("DeepSeek API key not found in auth.json or environment.")
    url = "https://api.deepseek.com/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res["choices"][0]["message"].get("content", "").strip()

def call_gemini(messages: List[Dict[str, str]], model: str = "gemini-2.5-flash", temperature: float = 0.6) -> str:
    if not is_model_usable(model):
        raise ValueError(f"Model '{model}' is flagged as blocked or do_not_use in model registry.")
    key = get_api_key("google")
    if not key:
        raise ValueError("Google Gemini API key not found in auth.json or environment.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    
    # Format messages to Gemini contents structure
    contents = []
    system_instruction = None
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            system_instruction = {"parts": [{"text": content}]}
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": content}]})
        else:
            contents.append({"role": "user", "parts": [{"text": content}]})

    payload: Dict[str, Any] = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
        }
    }
    if system_instruction:
        payload["systemInstruction"] = system_instruction

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        parts = res.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts).strip()

def call_local(messages: List[Dict[str, str]], model: str = "qwen3.5-2b", max_tokens: int = 500, temperature: float = 0.5) -> str:
    if not is_model_usable(model):
        raise ValueError(f"Model '{model}' is flagged as blocked or do_not_use in model registry.")
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        LM_STUDIO_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        choice = res["choices"][0]["message"]
        content = choice.get("content") or choice.get("reasoning_content") or ""
        return content.strip()

def call_tier(role: str, messages: List[Dict[str, str]], max_tokens: int = 800) -> str:
    """Smart router:
    - 'super_agent' / 'planner': DeepSeek -> Gemini -> Local fallback
    - 'dialogue' / 'playtest': Local qwen3.5-2b -> DeepSeek fallback
    - 'auditor': Gemini -> DeepSeek -> Local fallback
    """
    if role in ("super_agent", "planner"):
        try:
            return call_deepseek(messages, max_tokens=max_tokens)
        except Exception as e:
            try:
                return call_gemini(messages)
            except Exception:
                return call_local(messages, max_tokens=max_tokens)

    elif role in ("dialogue", "playtest"):
        try:
            return call_local(messages, max_tokens=max_tokens)
        except Exception:
            try:
                return call_deepseek(messages, max_tokens=max_tokens)
            except Exception:
                return call_gemini(messages)

    elif role == "auditor":
        try:
            return call_gemini(messages)
        except Exception:
            try:
                return call_deepseek(messages, max_tokens=max_tokens)
            except Exception:
                return call_local(messages, max_tokens=max_tokens)

    # Default router
    try:
        return call_local(messages, max_tokens=max_tokens)
    except Exception:
        return call_deepseek(messages, max_tokens=max_tokens)
