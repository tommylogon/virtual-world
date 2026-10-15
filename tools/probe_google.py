"""Probe Google's Gemini API in its NATIVE format, with retry.

Google's API is not OpenAI-compatible: it does not speak /chat/completions.
The generic probe (tools/probe_providers.py) hits it and gets 404 for that
reason. This file speaks Gemini's real shape:

    GET  /v1beta/models?key=<API_KEY>                       -> list of models
    POST /v1beta/models/<model>:generateContent?key=<KEY>  -> chat completion

The model name is DISCOVERED, not assumed. Step 1 lists what the key can see
and filters to models that actually support generateContent; step 2 picks the
best candidate (flash preferred, then pro, then anything else) and calls it.
That removes the whole class of "404 model not found" failures that come from
hardcoding a model name that isn't on this API version.

Free-tier Gemini models return 503 "model is currently experiencing high
demand" under load. That is a capacity signal, not a credential failure, so the
generate step retries with a backoff before declaring the provider down.

Reads the key from GOOGLE_GEMINI_API_KEY in the environment, or --key on the
command line. Never hardcoded, never written to a file.

    python tools/probe_google.py [--timeout 15] [--retries 4]
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

TIMEOUT = int(os.environ.get("PROBE_TIMEOUT", "15"))
RETRIES = int(os.environ.get("PROBE_RETRIES", "4"))
# --key overrides GOOGLE_GEMINI_API_KEY. Use it to test a key from the shell
# without writing it to a file; it still never lands in a repo file.
KEY = sys.argv[sys.argv.index("--key") + 1] if "--key" in sys.argv \
    else os.environ.get("GOOGLE_GEMINI_API_KEY", "")
BASE = os.environ.get("GOOGLE_GEMINI_BASE", "https://generativelanguage.googleapis.com/v1beta")


def _get(url):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def _post(url, body):
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def list_models():
    """Return the models this key can see, filtered to generateContent."""
    url = f"{BASE}/models?key={KEY}"
    print(f"GET   {BASE}/models?key=***")
    try:
        code, raw = _get(url)
    except urllib.error.HTTPError as e:
        code, raw = e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"ERR   {type(e).__name__}: {e}")
        return None, None
    print(f"CODE  {code}")
    if code != 200:
        print("BODY  " + raw.replace("\n", " ")[:400])
        return None, None
    try:
        data = json.loads(raw)
    except Exception as e:
        print(f"ERR   models list did not parse: {e}")
        return None, None
    models = data.get("models", [])
    supported = []
    for m in models:
        name = (m.get("name") or "").replace("models/", "")
        # The real field is supportedGenerationMethods, not supportedMethods.
        methods = m.get("supportedGenerationMethods", []) or []
        if "generateContent" not in methods or not name:
            continue
        # Image and TTS models speak generateContent too; they are not text
        # chat models and would 400 or produce media. Drop them by name.
        if any(k in name for k in ("image", "tts", "nano-banana")):
            continue
        supported.append((name, m.get("displayName") or name))
    print(f"MODELS ({len(supported)} text-capable support generateContent)")
    for name, display in supported[:15]:
        print(f"       - {name}  ({display})")
    return supported, raw


def pick_model(supported):
    """Best candidate: flash preferred, then pro, then anything else."""
    if not supported:
        return None
    names = [n for n, _ in supported]
    for pref in ("gemini-flash-latest", "gemini-2.5-flash",
                 "gemini-2.0-flash", "gemini-1.5-flash",
                 "gemini-pro-latest", "gemini-2.5-pro",
                 "gemini-2.0-pro", "gemini-1.5-pro"):
        if pref in names:
            return pref
    return names[0]


def main():
    if not KEY:
        print("SKIP  GOOGLE_GEMINI_API_KEY is not set (pass --key)")
        return 1
    supported, _ = list_models()
    if not supported:
        return 1
    model = pick_model(supported)
    print(f"CHOSE {model}")
    url = f"{BASE}/models/{model}:generateContent?key={KEY}"
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": "Reply with exactly one word: ok"}]}],
        "generationConfig": {"maxOutputTokens": 8, "temperature": 0},
    }).encode("utf-8")
    print(f"POST  {BASE}/models/{model}:generateContent?key=***")
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            code, raw = _post(url, body)
        except urllib.error.HTTPError as e:
            code, raw = e.code, e.read().decode("utf-8", "replace")
        except Exception as e:
            print(f"ERR   {type(e).__name__}: {e}")
            return 1
        last = (code, raw)
        if code == 200:
            print(f"CODE  {code}  (attempt {attempt})")
            print("BODY  " + raw.replace("\n", " ")[:200])
            return 0
        if code == 503:
            print(f"CODE  {code}  (attempt {attempt}/{RETRIES})  {raw.replace(chr(10), ' ')[:120]}")
            if attempt < RETRIES:
                time.sleep(2 ** attempt)
            continue
        print(f"CODE  {code}  (attempt {attempt})")
        print("BODY  " + raw.replace("\n", " ")[:400])
        return 1
    code, raw = last or (0, "")
    print(f"CODE  {code}  (all {RETRIES} attempts exhausted)")
    print("BODY  " + raw.replace("\n", " ")[:400])
    return 1


if __name__ == "__main__":
    sys.exit(main())