#!/usr/bin/env python3
"""Backfill embeddings for code-graph nodes that lack vectors.

Usage:
    python backfill_embeddings.py [root]

Root defaults to env CODEGRAPH_ROOT or F:\\AI\\viwo\\virtual-world.
Skips nodes that already have vectors. Idempotent.

Env: NEO4J_URI/USERNAME/PASSWORD, EMBEDDING_BASE_URL, EMBEDDING_MODEL.
"""
import os
import sys
import requests
from neo4j import GraphDatabase

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASSWORD", "password")
EMBED_URL = os.environ.get("EMBEDDING_BASE_URL", "http://localhost:1234/v1")
EMBED_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")
DEFAULT_ROOT = os.environ.get("CODEGRAPH_ROOT", "F:\\AI\\viwo\\virtual-world")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))


def text_of(n):
    parts = []
    name = n.get("name") or "?"
    doc = n.get("docstring") or ""
    src = n.get("source_code") or ""
    sig = n.get("signature") or ""
    if sig:
        parts.append(sig)
    if doc:
        parts.append(doc)
    if src and len(src) < 3000:
        parts.append(src)
    if not parts:
        parts.append(name)
    return name + " :: " + " ".join(parts)[:2400]


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOT
    with driver.session() as s:
        rows = list(s.run("""
            MATCH (n:Embeddable)
            WHERE n.root_path = $root AND n.vector IS NULL
            RETURN elementId(n) AS id, n.name AS name, n.docstring AS doc,
                   n.source_code AS src, n.signature AS sig, n.qualified_name AS q
            LIMIT 5000
        """, root=root))
    print(f"need embedding: {len(rows)}")
    if not rows:
        driver.close()
        return

    texts = [text_of(r) for r in rows]
    vecs = []
    for i in range(0, len(texts), 32):
        chunk = texts[i:i + 32]
        r = requests.post(EMBED_URL.rstrip("/") + "/embeddings",
                          json={"model": EMBED_MODEL, "input": chunk}, timeout=240)
        r.raise_for_status()
        vecs.extend(d["embedding"] for d in r.json()["data"])
        print(f"  embedded {min(i + 32, len(texts))}/{len(texts)}", flush=True)

    with driver.session() as s:
        for (r0, v) in zip(rows, vecs):
            s.run("MATCH (n) WHERE elementId(n) = $id SET n.vector = $v",
                  id=r0["id"], v=v)
    print(f"DONE: {len(vecs)} vectors attached")
    driver.close()


if __name__ == "__main__":
    main()
