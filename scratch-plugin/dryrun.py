import sys
sys.path.insert(0, r"F:\AI\viwo\virtual-world\tools")
import build_code_graph as b

# count files
root = r"F:\AI\viwo\virtual-world"
files = []
for dirpath, dirnames, filenames in b.os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in b.IGNORE_DIRS]
    for fn in filenames:
        ext = b.Path(fn).suffix.lower()
        full = b.os.path.join(dirpath, fn)
        rel = b.os.path.relpath(full, root).replace("\\", "/")
        if ext not in b.FILE_EXTS or "docs/" in rel:
            continue
        top = rel.split("/")[0]
        if top in b.SCAN_TOP or "/" not in rel:
            files.append(rel)
print("files:", len(files))
from collections import Counter
kinds = Counter()
for rel in files[:40]:
    full = b.os.path.join(root, rel.replace("/", b.os.sep))
    ext = b.Path(full).suffix.lower()
    res = b.extract_python(b.Path(full), rel) if ext == ".py" else b.extract_javascript(b.Path(full), rel)
    if not res:
        print("  SKIP (parse fail):", rel)
        continue
    fe, ents, lines = res
    ents += b.extract_comments(lines, rel, ents)
    for e in ents:
        kinds[e["kind"]] += 1
    print(f"  {rel}: {len(ents)} entities, file doc={len(fe['docstring'])}")
print("kinds sample:", dict(kinds))
