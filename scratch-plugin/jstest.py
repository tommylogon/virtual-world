import sys
sys.path.insert(0, r"F:\AI\viwo\virtual-world\tools")
import build_code_graph as b
from pathlib import Path

root = r"F:\AI\viwo\virtual-world"
rel = "static/js/world-sync.js"
res = b.extract_javascript(Path(root, "static", "js", "world-sync.js"), rel)
if res:
    fe, ents, lines = res
    ents = ents + b.extract_comments(lines, rel, ents)
    print("entities:", len(ents))
    for e in ents[:12]:
        print("  ", e["kind"], e["name"], e["line_start"], "-", e["line_end"])
else:
    print("PARSE FAIL")
