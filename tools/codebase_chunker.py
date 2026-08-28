#!/usr/bin/env python3
"""AST-based chunker for semantic codebase indexing.

Extracts per-module, per-class, per-function and per-comment chunks from Python
and JavaScript using tree-sitter. Each chunk carries lineage metadata (path,
kind, name, line_start, line_end, parent) and a text payload suitable for
embedding (signature + docstring + body/comment).

Traversal is an explicit-stack iterative DFS (no Python recursion in the walk)
so deep trees can't blow the interpreter stack. This is the chunking layer only;
it has no LM Studio / storage dependency.
"""
import os
import sys
from tree_sitter import Language, Parser
import tree_sitter_python as tsp
import tree_sitter_javascript as tsj

_PY = Parser(Language(tsp.language()))
_JS = Parser(Language(tsj.language()))

PY_DEF = {"function_definition", "class_definition"}
JS_DEF = {"function_declaration", "class_declaration", "method_definition",
          "generator_function_declaration"}
COMMENT = {"comment"}
JS_ARROW = {"lexical_declaration", "variable_declaration"}
MAX_CHUNK_CHARS = 1400


def _parse(text: bytes, path: str):
    if path.endswith(".py"):
        return _PY.parse(text)
    return _JS.parse(text)


def _name(node):
    n = node.child_by_field_name("name")
    return n.text.decode("utf-8", "ignore") if n is not None else None


def _text(node, src: bytes) -> str:
    return " ".join(src[node.start_byte:node.end_byte].decode("utf-8", "ignore").split())


def _chunk_text(header: str, body: str) -> str:
    t = (header + "\n" + body).strip()
    return t[:MAX_CHUNK_CHARS] if len(t) > MAX_CHUNK_CHARS else t


def _emit(out, rel, kind, name, node, text, parent):
    out.append({
        "path": rel, "kind": kind, "name": name,
        "line_start": node.start_point.row + 1, "line_end": node.end_point.row + 1,
        "parent": parent, "text": text,
    })


def _find_descendant(node, types):
    """Iteratively find the first descendant in `types`."""
    stack = list(reversed(node.children))
    while stack:
        c = stack.pop()
        if c.type in types:
            return c
        stack.extend(reversed(c.children))
    return None


def chunk_file(path: str):
    """Return a list of chunk dicts for a single file (iterative traversal)."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            src = f.read().encode("utf-8")
    except OSError:
        return []
    if not (path.endswith(".py") or path.endswith(".js") or path.endswith(".mjs")):
        return []
    tree = _parse(src, path)
    root = tree.root_node
    print("DBG: parsed", tree.root_node.type, "children", len(root.children), flush=True)
    out = []

    # Module-level chunk from top docstring/comments.
    module_docs = []
    for child in root.children:
        if child.type == "comment" or child.type == "docstring":
            module_docs.append(_text(child, src))
    if module_docs:
        _emit(out, path, "module", None, root, _chunk_text("module", " ".join(module_docs)), None)

    # Iterative DFS. Each stack entry: (node, parent_name).
    # When we emit a named def, node's descendants are pushed with parent = its name.
    stack = [(c, None) for c in reversed(root.children)]
    while stack:
        node, parent = stack.pop()
        print("DBG loop top type", node.type, "parent", parent, flush=True)

        if node.type in COMMENT:
            txt = _text(node, src)
            if txt.strip():
                _emit(out, path, "comment", None, node, _chunk_text(txt, ""), parent)
            continue

        if node.type in PY_DEF or node.type in JS_DEF:
            name = _name(node) or "<anonymous>"
            # use first string/comment child as docstring if present, else snapshot
            docstr = None
            for child in node.children:
                if child.type in ("string", "comment"):
                    docstr = _text(child, src)
                    break
            body = docstr if docstr else _text(node, src)
            _emit(out, path, "class" if "class" in node.type else "function",
                  name, node, _chunk_text(name, body), parent)
            parent = name

        elif node.type in JS_ARROW:
            # const name = (args) => ...  or  const name = function(...) {...}
            nm = None
            for child in node.children:
                if child.type == "identifier":
                    nm = child.text.decode("utf-8", "ignore")
                    break
            if nm:
                fn = _find_descendant(node, {"arrow_function", "function_expression"})
                if fn is not None:
                    _emit(out, path, "function", nm, node, _chunk_text(nm, _text(fn, src)), parent)

        # Push children (leaf nodes can be dropped; we only need structure nodes).
        kids = [c for c in node.children if c.child_count > 0 or c.type in COMMENT]
        for c in reversed(kids):
            stack.append((c, parent))

    return out


def repo_chunk_paths(scan_dirs, root):
    """Yield (rel, fullpath) for indexed files under scan_dirs."""
    for d in scan_dirs:
        base = os.path.join(root, d)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x not in
                           ("node_modules", "__pycache__", ".git", ".venv", "venv", ".kilocode")]
            for fn in filenames:
                if fn.endswith((".py", ".js", ".mjs")):
                    full = os.path.join(dirpath, fn)
                    rel = os.path.relpath(full, root).replace("\\", "/")
                    if rel.startswith("docs/"):
                        continue
                    yield rel, full


if __name__ == "__main__":
    import sys as _s
    if len(_s.argv) > 1:
        chunks = chunk_file(_s.argv[1])
        print(f"{len(chunks)} chunks from {_s.argv[1]}")
        for c in chunks[:25]:
            print(f"  [{c['kind']}] {c.get('name') or ''} lines {c['line_start']}-{c['line_end']}  :: {c['text'][:60]!r}")
