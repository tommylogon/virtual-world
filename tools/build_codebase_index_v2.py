#!/usr/bin/env python3
"""Build a chunked semantic codebase index.

Chunks the repo with the AST chunker, embeds every chunk via LM Studio,
and persists:
  data/codebase_chunks.json   -> per-chunk metadata (path, kind, name, lines, parent, text)
  data/codebase_vecs.npy      -> float32 matrix, row i == chunk i
  data/codebase_meta.json     -> {model, dim, count, built_at}

Env: EMBEDDING_BASE_URL (default http://localhost:1234/v1), EMBEDDING_MODEL.
"""
import json, os, sys, time
import numpy as np
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from codebase_chunker import chunk_file, repo_chunk_paths

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_DIRS = ["engine", "routes", "static/js", "tests"]
OUT_CHUNKS = os.path.join(ROOT, "data", "codebase_chunks.json")
OUT_VECS = os.path.join(ROOT, "data", "codebase_vecs.npy")
OUT_META = os.path.join(ROOT, "data", "codebase_meta.json")
EMBED_URL = os.environ.get("EMBEDDING_BASE_URL", "http://localhost:1234/v1")


def discover_model():
    try:
        r = requests.get(EMBED_URL.rstrip("/") + "/models", timeout=15)
        ids = [m.get("id") for m in r.json().get("data", []) if m.get("id")]
    except Exception:
        ids = []
    for i in ids:
        if "qwen" in i.lower() and "embed" in i.lower():
            return i
    for i in ids:
        if "embed" in i.lower():
            return i
    for i in ids:
        if "qwen" in i.lower():
            return i
    return os.environ.get("EMBEDDING_MODEL", ids[0] if ids else "text-embedding-qwen3-embedding-0.6b")


def embed_batch(texts, model, batch=48):
    out = []
    for i in range(0, len(texts), batch):
        chunk = texts[i:i + batch]
        r = requests.post(EMBED_URL.rstrip("/") + "/embeddings",
                          json={"model": model, "input": chunk}, timeout=180)
        r.raise_for_status()
        data = r.json()
        items = data["data"]
        if not isinstance(items, list):
            items = [items]
        out.extend(list(item)[1] if isinstance(item, (list, tuple)) else item["embedding"]
                   for item in items)
    return out


def main():
    # Gather chunks across all scanned paths.
    chunks = []
    for rel, full in repo_chunk_paths(SCAN_DIRS, ROOT):
        for c in chunk_file(full):
            c["path"] = rel
            chunks.append(c)
    if not chunks:
        print("no chunks found")
        return

    # Deduplicate by (path, kind, name, line_start).
    seen = set()
    dedup = []
    for c in chunks:
        key = (c["path"], c["kind"], c.get("name"), c["line_start"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(c)
    chunks = dedup

    model = discover_model()
    print(f"chunked {len(chunks)} chunks; embedding with {model}")

    texts = [c["text"] for c in chunks]
    vecs = embed_batch(texts, model)
    dim = len(vecs[0]) if vecs else 0
    if dim == 0:
        print("embedding returned nothing; aborting")
        return
    arr = np.asarray(vecs, dtype=np.float32)
    # normalize rows so cosine == dot
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    arr = arr / norms

    for c, v in zip(chunks, arr):
        c["vector"] = None  # vectors live in the matrix; keep json lean

    os.makedirs(os.path.dirname(OUT_CHUNKS), exist_ok=True)
    with open(OUT_CHUNKS, "w", encoding="utf-8") as f:
        json.dump(chunks, f)
    np.save(OUT_VECS, arr)
    meta = {"model": model, "dim": dim, "count": len(chunks), "built_at": time.time()}
    with open(OUT_META, "w", encoding="utf-8") as f:
        json.dump(meta, f)
    print(f"indexed {len(chunks)} chunks  dim={dim}  -> {OUT_CHUNKS}")


if __name__ == "__main__":
    main()
