#!/usr/bin/env python3
# Build a SEMANTIC codebase index via LM Studio (Qwen embedding model).
# Auto-discovers an embedding model from /v1/models, batches embed calls,
# stores vectors in data/codebase_index.json. Falls back to keyword-only.
# Env: EMBEDDING_BASE_URL (default http://localhost:1234/v1), EMBEDDING_MODEL.
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "codebase_index.json")
SCAN_DIRS = ["engine","routes","static/js","static/js/agent","static/js/shared",
             "static/js/inspector","static/js/ui","static/js/stream","tests"]
EMBED_URL = os.environ.get("EMBEDDING_BASE_URL", "http://localhost:1234/v1")

PY_DEF = re.compile(r"^\s*(?:async\s+|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(|:)")
JS_DEF = re.compile(r"\b(function\s+[A-Za-z_$][\w$]*|(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=\s*(?:async\s*)?\(|class\s+[A-Za-z_$][\w$]*)")

import requests
def discover_model():
    try:
        r = requests.get(EMBED_URL.rstrip("/") + "/models", timeout=15)
        ids = [m.get("id") for m in r.json().get("data", []) if m.get("id")]
    except Exception:
        ids = []
    for i in ids:
        if "qwen" in i.lower() and "embed" in i.lower(): return i
    for i in ids:
        if "embed" in i.lower(): return i
    for i in ids:
        if "qwen" in i.lower(): return i
    return os.environ.get("EMBEDDING_MODEL", ids[0] if ids else "Qwen3-Embedding-0.6B")

def embed_batch(texts, model):
    outs = []
    for i in range(0, len(texts), 24):
        chunk = texts[i:i+24]
        r = requests.post(EMBED_URL.rstrip("/") + "/embeddings",
                          json={"model": model, "input": chunk}, timeout=90)
        r.raise_for_status()
        data = r.json()
        outs += [d["embedding"] for d in data["data"]]
    return outs

def extract(path):
    names = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if path.endswith(".py"):
                m = PY_DEF.match(line)
                if m: names.append(m.group(1))
            else:
                m = JS_DEF.match(line)
                if m: names.append(m.group(1).replace("function ", "").replace("class ", "").split("=")[0].strip())
    return names

def main():
    files = {}
    for d in SCAN_DIRS:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base): continue
        for root, _, fns in os.walk(base):
            if "node_modules" in root: continue
            for fn in fns:
                if not fn.endswith((".py", ".js")): continue
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, ROOT).replace("\\", "/")
                if rel.startswith("docs/") or rel.startswith("node_modules/"): continue
                names = extract(p)
                if names:
                    files[rel] = {"symbols": names, "text": rel + " " + " ".join(names).lower()}
    model = discover_model()
    try:
        rels = list(files.keys())
        vecs = embed_batch([files[r]["text"] for r in rels], model)
        for r, v in zip(rels, vecs): files[r]["vector"] = v
        print("embedded", len(files), "files with model", model, "| dim", len(vecs[0]) if vecs else 0)
        embedded = True
    except Exception as e:
        print("embedding unavailable (", e, ") - keyword-only")
        embedded = False
        model = None
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"embedded": embedded, "model": model, "files": files}, f)
    print("indexed", len(files), "files ->", OUT, "| semantic:", embedded)

if __name__ == "__main__":
    main()