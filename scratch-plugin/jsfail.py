import sys, traceback
sys.path.insert(0, r"F:\AI\viwo\virtual-world\tools")
from pathlib import Path
import pyjsparser

root = r"F:\AI\viwo\virtual-world"
for rel in ["static/js/world-sync.js", "static/js/main.js", "static/js/api.js"]:
    src = Path(root, rel).read_text(encoding="utf-8", errors="ignore")
    try:
        pyjsparser.parse(src)
        print(f"OK   {rel} ({len(src)} B)")
    except Exception as e:
        print(f"FAIL {rel}: {str(e)[:200]}")
