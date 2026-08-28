#!/usr/bin/env python3
# Query the semantic codebase index. Usage: python tools/codebase_query.py <query>
# Cosine-similarity over LM Studio Qwen embeddings (falls back to ranked keyword
# if the index isn't embedded or LM Studio is down).
import json, os, sys, requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDX = os.path.join(ROOT, "data", "codebase_index.json")
EMBED_URL = os.environ.get("EMBEDDING_BASE_URL", "http://localhost:1234/v1")

def dot(a, b):
    return sum(x*y for x, y in zip(a, b))

def norm(v):
    return (sum(x*x for x in v)) ** 0.5 or 1.0

def embed_one(text, model):
    r = requests.post(EMBED_URL.rstrip("/") + "/embeddings",
                      json={"model": model, "input": text}, timeout=60)
    r.raise_for_status()
    d = r.json()
    return d["data"][0]["embedding"] if isinstance(d, dict) else d[0]["embedding"]

def keyword_score(rel, meta, tokens):
    s = 0
    joined = " ".join(meta.get("symbols", [])).lower()
    path = rel.lower()
    for tok in tokens:
        if tok in joined: s += 3
        if tok in path: s += 1
    return s

def main():
    query = " ".join(sys.argv[1:]).strip()
    if not query:
        print("usage: python tools/codebase_query.py <query>")
        return
    idx = json.load(open(IDX, encoding="utf-8"))
    files = idx.get("files", {})
    tokens = [t for t in query.lower().split() if t]
    results = []
    if idx.get("embedded") and idx.get("model"):
        try:
            qv = embed_one(query, idx["model"])
            qn = norm(qv)
            for rel, meta in files.items():
                v = meta.get("vector")
                if v:
                    results.append((dot(qv, v) / (qn * norm(v)), rel))
        except Exception as e:
            print("semantic unavailable (", e, ") - keyword fallback")
    if not results:
        for rel, meta in files.items():
            s = keyword_score(rel, meta, tokens)
            if s > 0: results.append((float(s) / 10.0, rel))
    results.sort(key=lambda x: (-x[0], x[1]))
    print("best matches for:", repr(query), "(", len(results), ")")
    for score, rel in results[:30]:
        print("  %0.3f  %s" % (score, rel))

if __name__ == "__main__":
    main()