"""List the models a Google API key can see.

A key that is genuinely invalid fails here too, but a key that is valid for
some models and not others will list what it has access to. Distinguishes
"key is wrong" from "model name is wrong".

    python tools/probe_google_models.py [--timeout 15]
"""
import json
import os
import sys
import urllib.error
import urllib.request

TIMEOUT = int(os.environ.get("PROBE_TIMEOUT", "15"))
KEY = os.environ.get("GOOGLE_GEMINI_API_KEY", "")
BASE = os.environ.get("GOOGLE_GEMINI_BASE", "https://generativelanguage.googleapis.com/v1beta")


def main():
    if not KEY:
        print("SKIP  GOOGLE_GEMINI_API_KEY is not set")
        return 1
    url = f"{BASE}/models?key={KEY}"
    req = urllib.request.Request(url, method="GET")
    print(f"GET   {BASE}/models?key=***")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            code = resp.status
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        code = e.code
        raw = e.read().decode("utf-8", "replace")
    except Exception as e:
        print(f"ERR   {type(e).__name__}: {e}")
        return 1
    print(f"CODE  {code}")
    if code == 200:
        try:
            data = json.loads(raw)
            names = [m.get("name", "").replace("models/", "") for m in data.get("models", [])]
            print(f"MODELS ({len(names)})  {', '.join(names[:20])}")
        except Exception as e:
            print("BODY  " + raw[:400])
    else:
        print("BODY  " + raw.replace("\n", " ")[:400])
    return 0 if code == 200 else 1


if __name__ == "__main__":
    sys.exit(main())