#!/usr/bin/env python3
"""Build the code knowledge graph for a codebase (ast-based, no native parsers).

Extracts files, classes, methods, functions AND standalone comments via
Python's stdlib `ast` (py) and pure-Python `pyjsparser` (js), stores entities
into Neo4j using the same schema as F:\\AI\\code\\utils\\code_knowledge_graph.py
(CodeFile/CodeClass/CodeFunction/CodeMethod/CodeComment, all :Embeddable), adds
DEFINES/CONTAINS/CALLS/IMPORTS/INHERITS edges and embeds every entity via LM
Studio into the existing `embeddable_vector` index (768-dim, nomic).

Usage:
    python build_code_graph.py <root> [--clear-old] [--no-embed]

Root defaults to the repo this script lives in.
Env: NEO4J_URI/USERNAME/PASSWORD, EMBEDDING_BASE_URL, EMBEDDING_MODEL.
"""
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import requests
from neo4j import GraphDatabase

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASSWORD", "password")
EMBED_URL = os.environ.get("EMBEDDING_BASE_URL", "http://localhost:1234/v1")
EMBED_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")
VECTOR_INDEX = "embeddable_vector"

IGNORE_DIRS = {"__pycache__", ".git", ".venv", "venv", "node_modules", ".mypy_cache",
               ".pytest_cache", ".ruff_cache", "data", ".kilo", "docs", "static/vendor"}
FILE_EXTS = {".py": "python", ".js": "javascript", ".mjs": "javascript"}
# Only these top-level dirs are indexed (plus bare root files).
SCAN_TOP = {"engine", "routes", "static", "tests", "tools"}

try:
    import pyjsparser
    HAVE_JS = True
except ImportError:
    HAVE_JS = False

# Modern JS (classes, optional chaining) needs acorn via Node. Shelled out per file.
NODE = os.environ.get("NODE_EXE", "node")
EXTRACT_JS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extract_js.mjs")
HAVE_NODE_JS = os.path.exists(EXTRACT_JS) and shutil.which(NODE) is not None


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------------------
# Python extraction (stdlib ast)
# ---------------------------------------------------------------------------

def py_docstring(node):
    try:
        if (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, (ast.Constant, ast.Str))):
            val = node.body[0].value.s
            if isinstance(val, str):
                return textwrap.dedent(val).strip()
    except Exception:
        pass
    return ""


def py_signature(node):
    args = node.args
    parts = []
    for a in args.args:
        s = a.arg
        if a.annotation:
            s += ": " + ast.unparse(a.annotation)
        parts.append(s)
    if args.vararg:
        parts.append("*" + args.vararg.arg)
    for a in args.kwonlyargs:
        s = a.arg
        if a.annotation:
            s += ": " + ast.unparse(a.annotation)
        parts.append(s)
    if args.kwarg:
        parts.append("**" + args.kwarg.arg)
    sig = "(" + ", ".join(parts) + ")"
    if node.returns:
        sig += " -> " + ast.unparse(node.returns)
    return sig


def py_calls(node):
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name):
                out.add(n.func.id)
            elif isinstance(n.func, ast.Attribute):
                out.add(n.func.attr)
    return out


def py_imports(tree):
    imports = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, [], False))
        elif isinstance(node, ast.ImportFrom):
            imports.append((node.module or "", [a.name for a in node.names], True))
    return imports


def extract_python(path: Path, rel: str):
    try:
        src = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None

    entities = []
    file_doc = py_docstring(tree)

    def add_function(node, cls_qname=None, cls_bases=()):
        qname = f"{rel}::{cls_qname}::{node.name}" if cls_qname else f"{rel}::{node.name}"
        src_lines = src.splitlines()
        src_code = " ".join(src_lines[node.lineno - 1: node.end_lineno][:40])[:1200]
        info = {
            "kind": "CodeMethod" if cls_qname else "CodeFunction",
            "name": node.name, "qualified_name": qname,
            "docstring": py_docstring(node), "signature": py_signature(node),
            "source_code": src_code,
            "filepath": str(path), "relative_path": rel,
            "line_start": node.lineno, "line_end": node.end_lineno or node.lineno,
            "decorators": [ast.unparse(d) for d in getattr(node, "decorator_list", [])],
            "calls": sorted(py_calls(node)), "bases": list(cls_bases),
            "class_qname": cls_qname, "parent_qname": cls_qname,
        }
        entities.append(info)
        return info

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            bases = []
            for b in node.bases:
                try:
                    bases.append(ast.unparse(b))
                except Exception:
                    bases.append("?")
            qname_c = f"{rel}::{node.name}"
            entities.append({
                "kind": "CodeClass", "name": node.name, "qualified_name": qname_c,
                "docstring": py_docstring(node), "signature": "", "source_code": "",
                "filepath": str(path), "relative_path": rel,
                "line_start": node.lineno, "line_end": node.end_lineno or node.lineno,
                "bases": bases, "decorators": [ast.unparse(d) for d in node.decorator_list],
                "calls": [],
            })
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    add_function(item, qname_c, bases)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add_function(node)

    file_entity = {
        "kind": "CodeFile", "name": path.name, "qualified_name": rel,
        "docstring": file_doc, "signature": "", "source_code": "",
        "filepath": str(path), "relative_path": rel,
        "line_start": 1, "line_end": len(src.splitlines()) or 1,
        "decorators": [], "calls": [], "imports": py_imports(tree),
    }
    return file_entity, entities, src.splitlines()


# ---------------------------------------------------------------------------
# JavaScript extraction (pyjsparser, pure python)
# ---------------------------------------------------------------------------

def js_imports(body):
    out = []
    for node in body:
        t = node.get("type", "")
        if t in ("ImportDeclaration", "ExportNamedDeclaration", "ExportAllDeclaration"):
            if node.get("source"):
                mod = node["source"].get("value", "")
                names = [sp.get("imported", {}).get("name") or sp.get("local", {}).get("name")
                         for sp in node.get("specifiers", [])]
                out.append((mod, [n for n in names if n], False))
    return out


def _js_val(node):
    if isinstance(node, dict):
        return node.get("name") or node.get("id", {}).get("name") or node.get("value")
    return str(node)


def _js_loc(node):
    loc = node.get("loc", {}) if isinstance(node, dict) else {}
    return loc.get("start", {}).get("line", 1), loc.get("end", {}).get("line", 1)


def js_walk(node, entities, rel, path, parent_qname=None):
    """Recursive js AST walk. Each function/class/method becomes an entity."""
    if not isinstance(node, dict):
        return
    t = node.get("type", "")
    if t in ("FunctionDeclaration", "ClassDeclaration"):
        name = _js_val(node.get("id")) or "<anonymous>"
        qname = f"{rel}::{parent_qname}::{name}" if parent_qname else f"{rel}::{name}"
        kind = "CodeClass" if t == "ClassDeclaration" else "CodeFunction"
        body = node.get("body")
        ls, le = _js_loc(node)
        ent = {
            "kind": kind, "name": name, "qualified_name": qname,
            "docstring": "", "signature": "", "source_code": "",
            "filepath": str(path), "relative_path": rel,
            "line_start": ls, "line_end": le, "decorators": [], "calls": [],
            "bases": [], "class_qname": qname if kind == "CodeClass" else parent_qname,
        }
        entities.append(ent)
        # Class body: methods + nested
        members = body.get("body", []) if isinstance(body, dict) else []
        for m in members:
            js_walk(m, entities, rel, path, qname)
        return

    if t in ("MethodDefinition", "PropertyDefinition"):
        key = node.get("key") or {}
        name = key.get("name") or key.get("value") or "<anonymous>"
        qname = f"{rel}::{parent_qname}::{name}" if parent_qname else f"{rel}::{name}"
        ls, le = _js_loc(node)
        entities.append({
            "kind": "CodeMethod", "name": name, "qualified_name": qname,
            "docstring": "", "signature": "", "source_code": "",
            "filepath": str(path), "relative_path": rel,
            "line_start": ls, "line_end": le, "decorators": [], "calls": [],
            "bases": [], "class_qname": parent_qname,
        })
        js_walk(node.get("value"), entities, rel, path, qname)
        return

    if t == "VariableDeclaration":
        for decl in node.get("declarations", []):
            init = decl.get("init")
            if init and init.get("type") in ("ArrowFunctionExpression", "FunctionExpression"):
                nm = _js_val(decl.get("id")) or "<anonymous>"
                qname = f"{rel}::{parent_qname}::{nm}" if parent_qname else f"{rel}::{nm}"
                ls, le = _js_loc(node)
                entities.append({
                    "kind": "CodeFunction", "name": nm, "qualified_name": qname,
                    "docstring": "", "signature": "", "source_code": "",
                    "filepath": str(path), "relative_path": rel,
                    "line_start": ls, "line_end": le, "decorators": [], "calls": [],
                    "bases": [], "class_qname": parent_qname,
                })
        return

    for k, v in node.items():
        if isinstance(v, dict):
            js_walk(v, entities, rel, path, parent_qname)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    js_walk(item, entities, rel, path, parent_qname)


def extract_javascript(path: Path, rel: str):
    """Extract JS via acorn (Node). Falls back to pyjsparser if node is missing."""
    if HAVE_NODE_JS:
        try:
            r = subprocess.run([NODE, EXTRACT_JS, str(path), rel],
                               capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                data = json.loads(r.stdout)
                if not data.get("error"):
                    entities = data.get("entities", [])
                    for e in entities:
                        e["relative_path"] = rel
                        e["bases"] = e.get("bases", [])
                        e["class_qname"] = e.get("class_qname")
                        e["parent_qname"] = e.get("parent_qname")
                    file_entity = {
                        "kind": "CodeFile", "name": path.name, "qualified_name": rel,
                        "docstring": data.get("file_doc", ""), "signature": "", "source_code": "",
                        "filepath": str(path), "relative_path": rel,
                        "line_start": 1, "line_end": len(path.read_text(encoding="utf-8", errors="ignore").splitlines()) or 1,
                        "decorators": [], "calls": [], "imports": data.get("imports", []),
                    }
                    return file_entity, entities, path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception as e:
            log(f"  WARN node extraction failed for {rel}: {e}")
    if not HAVE_JS:
        log("  WARN: no JS parser available, skipping")
        return None
    src = path.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = pyjsparser.parse(src)
    except Exception:
        return None
    entities = []
    js_walk(tree, entities, rel, path)
    file_doc = ""
    if tree.get("comments"):
        file_doc = " ".join(str(c.get("value", "")) for c in tree["comments"][:4])
    file_entity = {
        "kind": "CodeFile", "name": path.name, "qualified_name": rel,
        "docstring": file_doc, "signature": "", "source_code": "",
        "filepath": str(path), "relative_path": rel,
        "line_start": 1, "line_end": len(src.splitlines()) or 1,
        "decorators": [], "calls": [], "imports": js_imports(tree.get("body", [])),
    }
    return file_entity, entities, src.splitlines()


# ---------------------------------------------------------------------------
# Comment extraction (line-based, both languages)
# ---------------------------------------------------------------------------

PY_COMMENT_RE = re.compile(r"^\s*#\s*(.+)$")
JS_COMMENT_RE = re.compile(r"^\s*//\s*(.+)$|^\s*/\*\s*(.+?)\s*\*/$")


def extract_comments(lines, file_rel, entities):
    """Each comment line -> own CodeComment entity, tied to innermost function."""
    shells = [e for e in entities if e["kind"] in ("CodeClass", "CodeFunction", "CodeMethod")]
    shells.sort(key=lambda e: e["line_start"])
    comments = []
    for i, raw in enumerate(lines):
        line_no = i + 1
        m = PY_COMMENT_RE.match(raw)
        text = m.group(1).strip() if m else None
        if text is None:
            m2 = JS_COMMENT_RE.match(raw)
            if m2:
                text = (m2.group(1) or m2.group(2) or "").strip()
        if not text or len(text) < 3:
            continue
        parent = None
        parent_start = -1
        for e in shells:
            if e["line_start"] <= line_no <= e["line_end"] and e["line_start"] >= parent_start:
                parent = e
                parent_start = e["line_start"]
        qname = f"{parent['qualified_name']}::<comment>{line_no}" if parent \
            else f"{file_rel}::<comment>{line_no}"
        comments.append({
            "kind": "CodeComment", "name": f"comment@{line_no}",
            "qualified_name": qname, "docstring": text,
            "signature": "", "source_code": "",
            "filepath": "", "relative_path": file_rel,
            "line_start": line_no, "line_end": line_no,
            "decorators": [], "calls": [], "bases": [],
            "class_qname": parent.get("class_qname") if parent else None,
            "parent_qname": parent["qualified_name"] if parent else None,
        })
    return comments


# ---------------------------------------------------------------------------
# Aggregation + Neo4j store
# ---------------------------------------------------------------------------

DRIVER = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))


def entity_text(e):
    t = e.get("docstring", "")
    if len(t) < 1 and e.get("source_code"):
        t = e["source_code"]
    if e["kind"] in ("CodeFunction", "CodeMethod") and e.get("source_code"):
        t = (t + "\n" + e["source_code"])[:2400]
    return e.get("name", "") + " :: " + (t or "")


def main():
    root_raw = sys.argv[1] if len(sys.argv) > 1 else ROOT_DIR
    root = str(Path(root_raw).resolve())
    clear = "--clear-old" in sys.argv
    do_embed = "--no-embed" not in sys.argv
    log(f"Scanning {root}")

    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fn in filenames:
            ext = Path(fn).suffix.lower()
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace("\\", "/")
            if ext not in FILE_EXTS or "docs/" in rel:
                continue
            top = rel.split("/")[0]
            if top in SCAN_TOP or "/" not in rel:
                files.append((full, rel, ext))
    files.sort()
    log(f"Found {len(files)} source files")

    if clear:
        with DRIVER.session() as s:
            s.run("MATCH (n) WHERE n.root_path = $root DETACH DELETE n", root=root)
        log(f"Cleared old graph for {root}")

    all_files = []   # (file_entity, entities)
    for full, rel, ext in files:
        path = Path(full)
        res = extract_python(path, rel) if ext == ".py" else extract_javascript(path, rel)
        if not res:
            continue
        file_entity, entities, lines = res
        entities = entities + extract_comments(lines, rel, entities)
        file_entity["root_path"] = root
        file_entity["language"] = "python" if ext == ".py" else "javascript"
        for e in entities:
            e["root_path"] = root
            e["language"] = file_entity["language"]
        all_files.append((file_entity, entities))

    n_entities = sum(1 + len(ents) for _, ents in all_files)
    log(f"Extracted {n_entities} entities across {len(all_files)} files")

    # ---- compute edges (order-independent) -------------------------------
    defines, contains, calls, inherits, imports = [], [], [], [], []
    file_ids = {fe["qualified_name"] for fe, _ in all_files}
    by_qname = {}
    for fe, ents in all_files:
        by_qname[fe["qualified_name"]] = fe
        for e in ents:
            by_qname[e["qualified_name"]] = e
    name_index = {}
    for fe, ents in all_files:
        for e in [fe] + ents:
            name_index.setdefault(e["name"], set()).add(e["qualified_name"])

    for fe, ents in all_files:
        fq = fe["qualified_name"]
        for m, names, is_from in fe.get("imports", ()):
            imports.append((fq, m, names, is_from))
        for e in ents:
            # file defines everything whose qname starts with fq + "::" at top level
            if e["kind"] in ("CodeClass", "CodeFunction"):
                defines.append((fq, e["qualified_name"]))
            # contains: class -> method whose qname is class::method (no parents between)
            if e["kind"] == "CodeMethod" and e.get("class_qname"):
                contains.append((e["class_qname"], e["qualified_name"]))
            # class inherits
            for base in e.get("bases", []):
                if base:
                    inherits.append((e["qualified_name"], base))
            # calls (by name, intra-repo only)
            for c in e.get("calls", []):
                for target in name_index.get(c, ()):
                    if target != e["qualified_name"] and target in by_qname:
                        calls.append((e["qualified_name"], target))

    # ---- write to Neo4j --------------------------------------------------
    with DRIVER.session() as s:
        s.run("MATCH (n) WHERE n.root_path = $root DETACH DELETE n", root=root)
        log("Storing entities...")
        for fe, ents in all_files:
            for e in [fe] + ents:
                kind = e["kind"]
                s.run(f"""
                    MERGE (n:Embeddable {{qualified_name: $q}})
                    SET n.name = $name, n.docstring = $doc, n.signature = $sig,
                        n.source_code = $src, n.filepath = $fp, n.relative_path = $rel,
                        n.line_start = $ls, n.line_end = $le, n.language = $lang,
                        n.decorators = $decs, n.bases = $bases, n.root_path = $root
                    WITH n
                    SET n:`{kind}`
                """, q=e["qualified_name"], name=e.get("name", ""),
                    doc=e.get("docstring", "")[:2400], sig=e.get("signature", ""),
                    src=e.get("source_code", "")[:2000], fp=e.get("filepath", ""),
                    rel=e.get("relative_path", ""), ls=e.get("line_start", 1),
                    le=e.get("line_end", 1), lang=e.get("language", ""),
                    decs=e.get("decorators", []), bases=e.get("bases", []),
                    root=e.get("root_path", ""))

        log("Wiring edges...")
        if defines:
            s.run("""
                UNWIND $pairs AS p
                MATCH (a:Embeddable {qualified_name: p[0]})
                MATCH (b:Embeddable {qualified_name: p[1]})
                MERGE (a)-[:DEFINES]->(b)
            """, pairs=defines)
        if contains:
            s.run("""
                UNWIND $pairs AS p
                MATCH (a:Embeddable {qualified_name: p[0]})
                MATCH (b:Embeddable {qualified_name: p[1]})
                MERGE (a)-[:CONTAINS]->(b)
            """, pairs=contains)
        if calls:
            s.run("""
                UNWIND $pairs AS p
                MATCH (a:Embeddable {qualified_name: p[0]})
                MATCH (b:Embeddable {qualified_name: p[1]})
                MERGE (a)-[:CALLS]->(b)
            """, pairs=calls)
        if inherits:
            s.run("""
                UNWIND $pairs AS p
                MATCH (a:Embeddable {qualified_name: p[0]})
                MERGE (b:CodeClass {name: p[1]})
                MERGE (a)-[:INHERITS]->(b)
            """, pairs=inherits)
        if imports:
            s.run("""
                UNWIND $pairs AS p
                MERGE (m:CodeModule {name: p[1]})
                MATCH (f:Embeddable {qualified_name: p[0]})
                MERGE (f)-[:IMPORTS {names: p[2], is_from: p[3]}]->(m)
            """, pairs=imports)
        log("Edges wired")

    # ---- embed + attach vectors ------------------------------------------
    if do_embed:
        items = []
        for fe, ents in all_files:
            items.append((fe["qualified_name"], entity_text(fe)))
            for e in ents:
                items.append((e["qualified_name"], entity_text(e)))
        texts = [t for _, t in items]
        log(f"Embedding {len(texts)} entities via {EMBED_MODEL}...")
        vecs = []
        for i in range(0, len(texts), 32):
            chunk = texts[i:i + 32]
            r = requests.post(EMBED_URL.rstrip("/") + "/embeddings",
                              json={"model": EMBED_MODEL, "input": chunk}, timeout=240)
            r.raise_for_status()
            vecs.extend(d["embedding"] for d in r.json()["data"])
        if vecs and len(vecs) == len(texts):
            with DRIVER.session() as s:
                for (q, _), v in zip(items, vecs):
                    s.run("MATCH (n:Embeddable {qualified_name: $q}) SET n.vector = $v",
                          q=q, v=v)
            log(f"Attached {len(vecs)} vectors (dim {len(vecs[0])})")
    else:
        log("Skipped embedding (--no-embed)")

    log(f"DONE: {n_entities} entities for {root}")
    DRIVER.close()


if __name__ == "__main__":
    main()
