"""
Code Graph MCP Server
=====================
Semantic codebase search over the Neo4j code knowledge graph.

Implements the standard `code_knowledge_graph.py` schema from F:\\AI\\code\\utils:
CodeFile / CodeClass / CodeFunction / CodeMethod / CodeModule / Embeddable nodes
with docstrings, signatures, source, line ranges, CALLS / IMPORTS / DEFINES /
INHERITS edges and an embeddings vector index (`embeddable_vector`).

Tools:
    search_code(query, top_k, kind)      semantic search via LM Studio + Neo4j vector index
    search_keywords(query, top_k)         keyword search (name/qualified_name/docstring)
    code_callers(name) / code_callees(name)   CALLS graph walks
    file_structure(path)                 everything a file defines
    graph_stats()                        health check

Env:
    NEO4J_URI      (default bolt://localhost:7687)
    NEO4J_USERNAME (default neo4j)
    NEO4J_PASSWORD (default password)
    EMBEDDING_BASE_URL (default http://localhost:1234/v1)
    EMBEDDING_MODEL    (default text-embedding-nomic-embed-text-v1.5)
    CODEGRAPH_INDEX    (default embeddings_vector alias to embeddable_vector)
"""
import os
import logging

from fastmcp import FastMCP
from neo4j import GraphDatabase
import requests

logging.basicConfig(level=logging.WARNING)

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASSWORD", "password")
EMBED_URL = os.environ.get("EMBEDDING_BASE_URL", "http://localhost:1234/v1")
EMBED_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")
VECTOR_INDEX = os.environ.get("CODEGRAPH_INDEX", "embeddable_vector")

mcp = FastMCP("Code Graph")

_driver = None


def _get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    return _driver


def _embed(text: str):
    """Embed text via LM Studio (OpenAI-compatible). Returns 768-dim vector."""
    r = requests.post(EMBED_URL.rstrip("/") + "/embeddings",
                      json={"model": EMBED_MODEL, "input": [text[:3000]]},
                      timeout=60)
    r.raise_for_status()
    d = r.json()
    return d["data"][0]["embedding"]


def _format_hit(node, score):
    labels = node.get("labels", [])
    kind = labels[0].replace("Code", "").lower() if labels else "?"
    qname = node.get("qualified_name") or node.get("relative_path") or node.get("name")
    doc = (node.get("docstring") or "").replace("\n", " ")[:200]
    sig = node.get("signature") or ""
    ls, le = node.get("line_start"), node.get("line_end")
    loc = f":{ls}-{le}" if ls else ""
    path = node.get("filepath") or node.get("relative_path") or ""
    out = [f"[{kind}] {node.get('name')}  (score {score:.3f})  {qname}{loc}"]
    if path:
        out.append(f"    path: {path}")
    if sig:
        out.append(f"    signature: {sig}")
    if doc:
        out.append(f"    doc: {doc}...")
    return "\n".join(out)


def _semantic(query: str, top_k: int, kind: str = None):
    """Vector search. kind in {file,class,function,method,module,comment} or None for all."""
    vec = _embed(query)
    kind_clause = ""
    if kind:
        kind_clause = (
            "AND any(l IN labels(node) WHERE l = 'Code" + kind.capitalize()
            + "' OR l = '" + kind.capitalize() + "')"
        )
    with _get_driver().session() as session:
        res = session.run(f"""
            CALL db.index.vector.queryNodes('{VECTOR_INDEX}', $k, $vec)
            YIELD node, score
            RETURN labels(node) AS labels, node.name AS name,
                   node.qualified_name AS qname, node.docstring AS doc,
                   node.signature AS signature, node.filepath AS filepath,
                   node.relative_path AS rel, node.line_start AS ls,
                   node.line_end AS le, score {kind_clause}
            ORDER BY score DESC
            LIMIT $k
        """, k=top_k, vec=vec)
        rows = [dict(r) for r in res]
    return "\n\n".join(_format_hit(r, r["score"]) for r in rows) if rows else "No results."


def _keyword(query: str, top_k: int):
    """Keyword search: pull a candidate batch via name/qname CONTAINS, then
    rank in Python by token overlap. Handles identifiers and short queries."""
    tokens = [t for t in query.lower().split() if len(t) > 1]
    with _get_driver().session() as session:
        # Cheap prefilter: name or qname contains the full query or any token.
        res = session.run("""
            MATCH (n:Embeddable)
            WHERE n.name IS NOT NULL
              AND (toLower(n.name) CONTAINS $q
                   OR toLower(n.name) CONTAINS $tok
                   OR (n.qualified_name IS NOT NULL AND toLower(n.qualified_name) CONTAINS $q))
            RETURN labels(n) AS labels, n.name AS name,
                   n.qualified_name AS qname, n.docstring AS doc,
                   n.signature AS signature, n.filepath AS filepath,
                   n.relative_path AS rel, n.line_start AS ls,
                   n.line_end AS le
            LIMIT 200
        """, q=query.lower(), tok=(tokens[0] if tokens else query.lower()), k=top_k)
        rows = [dict(r) for r in res]

    # Post-rank in Python: token hits on name/qname > doc/signature.
    def _score(r):
        name = (r["name"] or "").lower()
        qname = (r["qname"] or "").lower()
        doc = (r["doc"] or "").lower()
        sig = (r["signature"] or "").lower()
        s = 0
        for t in tokens:
            if t in name:
                s += 5
            if t in qname:
                s += 3
            if t in doc:
                s += 1
            if t in sig:
                s += 1
        return (-s, name)
    rows.sort(key=_score)
    rows = [r for r in rows if _score(r)[0] < 0 or not tokens][:top_k]
    if not rows:
        return "No results."
    out = []
    for i, r in enumerate(rows):
        out.append(r)
    return "\n\n".join(_format_hit(r, 1.0 - i * 0.05) for i, r in enumerate(out))


# ──────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────
@mcp.tool()
def search_code(query: str, top_k: int = 8, kind: str = "") -> str:
    """Semantic code search. Embed `query` via LM Studio, find the closest
    files/classes/functions/methods in the Neo4j code graph.

    Args:
        query: Natural-language question or concept, e.g. "where is carry weight enforced".
        top_k: Number of results (default 8, max 25).
        kind: Optional filter: file, class, function, method, module, comment.
            Empty = search everything.
    """
    if not query.strip():
        return "Please provide a query."
    return _semantic(query.strip(), min(max(int(top_k), 1), 25), kind.strip().lower() or None)


@mcp.tool()
def search_keywords(query: str, top_k: int = 10) -> str:
    """Keyword search over entity names, qualified names, docstrings and signatures.
    Good for exact identifiers like `vector_store`, `carry_weight`, `upsert`.
    """
    if not query.strip():
        return "Please provide a query."
    return _keyword(query.strip(), min(max(int(top_k), 1), 50))


@mcp.tool()
def code_callers(name: str) -> str:
    """Find who calls a function or method named `name`.

    Args:
        name: Function or method name (e.g. `upsert`, `tick_turn`).
    """
    with _get_driver().session() as session:
        res = session.run("""
            MATCH (caller)-[:CALLS]->(callee)
            WHERE callee.name = $name
              AND (callee:CodeFunction OR callee:CodeMethod)
            RETURN DISTINCT caller.name AS caller_name,
                   caller.qualified_name AS caller_qname,
                   caller.filepath AS caller_file,
                   callee.qualified_name AS callee_qname
            LIMIT 50
        """, name=name)
        rows = [dict(r) for r in res]
    if not rows:
        return f"No callers found for `{name}`."
    lines = [f"Callers of {name} ({len(rows)}):"]
    for r in rows[:25]:
        lines.append(f"  {r['caller_qname']}  {r['caller_file'] or ''}")
    return "\n".join(lines)


@mcp.tool()
def code_callees(name: str) -> str:
    """Find what a function or method named `name` calls."""
    with _get_driver().session() as session:
        res = session.run("""
            MATCH (caller)-[:CALLS]->(callee)
            WHERE caller.name = $name
            RETURN DISTINCT callee.name AS callee_name,
                   callee.qualified_name AS callee_qname,
                   callee.filepath AS callee_file
            LIMIT 50
        """, name=name)
        rows = [dict(r) for r in res]
    if not rows:
        return f"No callees found for `{name}`."
    lines = [f"Callees of {name} ({len(rows)}):"]
    for r in rows[:25]:
        lines.append(f"  {r['callee_qname']}  {r['callee_file'] or ''}")
    return "\n".join(lines)


@mcp.tool()
def file_structure(path: str) -> str:
    """List everything defined in a file (classes, functions, methods) with line ranges.

    Args:
        path: filepath as stored in the graph, e.g. `engine/items/carry_weight.py`
            or an absolute path substring.
    """
    with _get_driver().session() as session:
        res = session.run("""
            MATCH (f:CodeFile)
            WHERE f.filepath CONTAINS $path OR f.relative_path CONTAINS $path
            OPTIONAL MATCH (f)-[:DEFINES]->(x)
            RETURN f.filepath AS filepath, f.relative_path AS rel,
                   collect(DISTINCT {
                       kind: head(labels(x)),
                       name: x.name,
                       qname: x.qualified_name,
                       ls: x.line_start, le: x.line_end
                   }) AS defines
            LIMIT 3
        """, path=path)
        rows = [dict(r) for r in res]
    if not rows:
        return f"No file matches `{path}`. Try search_code first for the right path."
    out = []
    for r in rows:
        out.append(f"File: {r['filepath'] or r['rel']}  ({len(r['defines'])} definitions)")
        for d in sorted(r["defines"], key=lambda x: (x.get("ls") or 0)):
            k = (d.get("kind") or "").replace("Code", "")
            out.append(f"  [{k}] {d.get('name')}  {d.get('qname')}  "
                       f"(lines {d.get('ls')}-{d.get('le')})")
    return "\n".join(out)


@mcp.tool()
def graph_stats() -> str:
    """Health check: entity counts, vector coverage, index state."""
    with _get_driver().session() as session:
        counts = session.run("""
            MATCH (n:Embeddable) RETURN labels(n) AS labs, count(n) AS cnt
            ORDER BY cnt DESC
        """).data()
        vecs = session.run("""
            MATCH (n:Embeddable) WHERE n.vector IS NOT NULL RETURN count(n) AS v, size(n.vector) AS d LIMIT 1
        """).single()
        calls = session.run("MATCH ()-[r:CALLS]->() RETURN count(r) AS c").single()
    lines = ["Code Graph stats:"]
    for row in counts:
        lines.append(f"  {row['labs'][0]}: {row['cnt']}")
    if vecs:
        lines.append(f"  embedded vectors: {vecs['v']} (dim {vecs['d']})")
    if calls:
        lines.append(f"  CALLS edges: {calls['c']}")
    return "\n".join(lines)


@mcp.resource("codegraph://stats")
def stats_resource() -> str:
    """Readable code-graph health snapshot."""
    return graph_stats()


if __name__ == "__main__":
    mcp.run()
