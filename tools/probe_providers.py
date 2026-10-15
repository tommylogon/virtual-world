"""Probe each provider's OpenAI-compatible /chat/completions endpoint.

Usage:
    python tools/probe_providers.py [--timeout 15]

Reads credentials from the environment (VW_* / *_API_KEY / *_BASE / *_MODEL).
Prints one line per provider: name, status, http_code, and the first 120 chars
of the reply (or the error). Designed to run from a plain shell, so it does not
import any project modules.

    python tools/probe_providers.py
    GOOGLE_GEMINI_API_KEY=... python tools/probe_providers.py
"""
import json
import os
import sys
import urllib.error
import urllib.request

TIMEOUT = int(os.environ.get("PROBE_TIMEOUT", "15"))

PROVIDERS = [
    ("LM Studio (local)", os.environ.get("VW_LLM_BASE", "http://localhost:1234/v1"),
     os.environ.get("VW_LLM_MODEL", "glm-4-9b-0414"), ""),
    ("Google AI Studio", os.environ.get("GOOGLE_GEMINI_BASE", ""),
     os.environ.get("GOOGLE_GEMINI_MODEL", "gemini-1.5-flash"),
     os.environ.get("GOOGLE_GEMINI_API_KEY", "")),
    ("NVIDIA NIM", os.environ.get("NVIDIA_NIM_BASE", ""),
     os.environ.get("NVIDIA_NIM_MODEL", "llama-3.3-70b-instruct"),
     os.environ.get("NVIDIA_NIM_API_KEY", "")),
    ("Groq Cloud", os.environ.get("GROQ_BASE", ""),
     os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
     os.environ.get("GROQ_API_KEY", "")),
    ("Mistral AI", os.environ.get("MISTRAL_BASE", ""),
     os.environ.get("MISTRAL_MODEL", "mistral-large-latest"),
     os.environ.get("MISTRAL_API_KEY", "")),
    ("OpenRouter", os.environ.get("OPENROUTER_BASE", ""),
     os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-r1"),
     os.environ.get("OPENROUTER_API_KEY", "")),
]


def probe(name, base, model, key):
    if not base:
        return f"{name:22} SKIP  no base URL set"
    url = base.rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": model or "(unset)",
        "messages": [{"role": "user", "content": "Reply with exactly one word: ok"}],
        "max_tokens": 8,
        "temperature": 0,
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            code = resp.status
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        code = e.code
        raw = e.read().decode("utf-8", "replace")
    except Exception as e:
        return f"{name:22} ERR   {type(e).__name__}: {e}"
    snippet = raw.replace("\n", " ")[:120]
    return f"{name:22} {code}    {snippet}"


def main():
    print(f"probe timeout={TIMEOUT}s")
    for name, base, model, key in PROVIDERS:
        print(probe(name, base, model, key))


if __name__ == "__main__":
    main()