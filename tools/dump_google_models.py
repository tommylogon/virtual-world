"""Dump the raw /v1beta/models response so the real shape is visible.

The probe filtered on `supportedMethods` and found 0 models, which means the
field name or structure differs from what was assumed. This prints the raw
JSON so the filter can be corrected against the actual payload instead of
against a guess.

    python tools/dump_google_models.py --key KEY
"""
import json
import os
import sys
import urllib.request

BASE = os.environ.get("GOOGLE_GEMINI_BASE", "https://generativelanguage.googleapis.com/v1beta")
KEY = sys.argv[sys.argv.index("--key") + 1] if "--key" in sys.argv \
    else os.environ.get("GOOGLE_GEMINI_API_KEY", "")

if not KEY:
    print("no key"); sys.exit(2)

url = f"{BASE}/models?key={KEY}"
with urllib.request.urlopen(url, timeout=15) as resp:
    data = json.loads(resp.read().decode("utf-8", "replace"))

models = data.get("models", [])
print(f"count={len(models)}")
for m in models[:20]:
    print(json.dumps(m, indent=1)[:600])
    print("---")