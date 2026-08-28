import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, r"F:\AI\viwo\virtual-world\tools")
import build_code_graph as b
from pathlib import Path

# Test markdown
res = b.extract_markdown(Path(r"F:\AI\viwo\virtual-world\readme.md"), "readme.md")
if res:
    fe, ents, lines = res
    print(f"MD: {len(ents)} sections")
    for e in ents[:5]:
        print("  ", e["kind"], e["name"], "::", e["docstring"][:70])

# Test a docs file with headings
res2 = b.extract_markdown(Path(r"F:\AI\viwo\virtual-world\docs\virtualWorld\_Index.md"), "docs/virtualWorld/_Index.md")
if res2:
    fe, ents, lines = res2
    print(f"\nMD docs: {len(ents)} sections")
    for e in ents[:6]:
        print("  ", e["name"], "::", e["docstring"][:50])

# Test JSON library item
res3 = b.extract_json(Path(r"F:\AI\viwo\virtual-world\data\library\areas\attic.json"), "data/library/areas/attic.json")
if res3:
    fe, ents, lines = res3
    print(f"\nJSON attic: {len(ents)} entities")
    for e in ents[:5]:
        print("  ", e["kind"], e["name"], "::", e["docstring"][:60])

# Test item json
res4 = b.extract_json(Path(r"F:\AI\viwo\virtual-world\data\library\items\small_key.json"), "data/library/items/small_key.json")
if res4:
    fe, ents, lines = res4
    print(f"\nJSON key: {len(ents)} entities")
    for e in ents[:3]:
        print("  ", e["kind"], e["name"], "::", e["docstring"][:60])
