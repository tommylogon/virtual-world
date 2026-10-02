"""Doc resolver: which note covers this module path or this library node (task-578).

@module docs_ops
@contributes the doc index (module @docs + node docs) and the /api/docs handlers
@docs none — developer tooling; the contract is this module's own docstring

Two sources, and only two — the upstream tasks' links:

* the ``@docs`` header on a JS or Python module (task-576), keyed by the
  repo-relative module path, e.g. ``engine/tick_manager.py``;
* the ``docs`` field on a library entry (task-577), keyed by the entry id, which
  is the registry filename stem, e.g. ``way_4f2a``.

The corpus is indexed once per process and cached. The index is rebuilt when any
file it was built from changes mtime (or the set of files changes), not on a
timer: a stale index in a dev tool is worse than no index.

The rendered **body** is served only for the narrative vault
(``docs/virtualWorld/**``) and never for ``dev_tasks/``; the dev-task tree is
internal working material. Path traversal and absolute paths are rejected.
``GET /api/docs/resolve`` returns an empty list — not a 404 — for an unknown
key, because "this has no docs" is a normal answer the UI must be able to show.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote

from flask import jsonify, request

try:
    from tools import js_module_index as _idx
except ImportError:  # pragma: no cover - run as a script from tools/
    import js_module_index as _idx  # type: ignore

REPO_ROOT = Path(__file__).resolve().parent.parent
VAULT = REPO_ROOT / "docs" / "virtualWorld"
JS_ROOT = REPO_ROOT / "static" / "js"
PY_ROOTS = (REPO_ROOT / "engine", REPO_ROOT / "routes")
LIBRARY_ROOT = REPO_ROOT / "data" / "library"

_H1_RE = re.compile(r"^#\s+(.*)$")
_SKIP_SUMMARY_PREFIX = ("#", ">", "-", "*", "|", "```", "---", "!", "<")

_CACHE: dict = {"index": None, "paths": [], "stamp": None, "builds": 0}


def _rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _docs_value(meta: dict) -> str:
    raw = (meta.get("docs") or "").strip().strip("`")
    if not raw or raw.lower() in ("none", "n/a", "-"):
        return ""
    return raw


def _note_meta(path: Path) -> dict:
    """Title (first H1) and a one-line summary (first body line after it)."""
    title = path.stem
    summary = ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"title": title, "summary": summary}
    seen_title = False
    for line in text.splitlines():
        s = line.strip()
        m = _H1_RE.match(s)
        if m and not seen_title:
            title = m.group(1).strip()
            seen_title = True
            continue
        if not seen_title or not s or s.startswith(_SKIP_SUMMARY_PREFIX):
            continue
        summary = re.sub(r"[*_`\[\]]", "", s).strip()[:240]
        break
    return {"title": title, "summary": summary}


def _module_docs() -> dict:
    out = {}
    for p in sorted(JS_ROOT.rglob("*.js")):
        if "vendor" in p.parts or "node_modules" in p.parts:
            continue
        d = _docs_value(_idx.parse(p))
        if d:
            out[_rel(p)] = d
    for root in PY_ROOTS:
        for p in sorted(root.rglob("*.py")):
            d = _docs_value(_idx.parse_py(p))
            if d:
                out[_rel(p)] = d
    return out


def _node_docs() -> dict:
    out = {}
    if not LIBRARY_ROOT.exists():
        return out
    for p in sorted(LIBRARY_ROOT.rglob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and isinstance(data.get("docs"), str) and data["docs"].strip():
            out[p.stem] = data["docs"].strip()
    return out


def _scan_paths() -> list:
    paths = []
    for p in JS_ROOT.rglob("*.js"):
        if "vendor" not in p.parts and "node_modules" not in p.parts:
            paths.append(p)
    for root in PY_ROOTS:
        paths.extend(root.rglob("*.py"))
    if LIBRARY_ROOT.exists():
        paths.extend(LIBRARY_ROOT.rglob("*.json"))
    return paths


def _stamp(paths) -> tuple:
    latest = 0
    for p in paths:
        try:
            latest = max(latest, p.stat().st_mtime_ns)
        except OSError:
            latest = max(latest, 1)
    return (len(paths), latest)


def _build() -> dict:
    module_docs = _module_docs()
    node_docs = _node_docs()
    # The files the index depends on: the sources, plus every note the links
    # point at. `docs` values are repo-relative, so resolve against the root.
    paths = list(_scan_paths())
    for target in list(module_docs.values()) + list(node_docs.values()):
        note = REPO_ROOT / target
        if note.exists():
            paths.append(note)
    index = {"module": module_docs, "node": node_docs}
    _CACHE.update(index=index, paths=paths, stamp=_stamp(paths))
    _CACHE["builds"] += 1
    return index


def _maybe_index() -> dict:
    if _CACHE["index"] is not None and _CACHE["stamp"] == _stamp(_CACHE["paths"]):
        return _CACHE["index"]
    return _build()


def _body_url(docs_path: str):
    """A URL to fetch the rendered body, or None when it is not servable."""
    resolved = _safe_vault_path(docs_path)
    if resolved is None:
        return None
    return "/api/docs/body?path=" + quote(docs_path)


def _entry(docs_path: str) -> dict:
    note = REPO_ROOT / docs_path
    meta = _note_meta(note) if note.is_file() else {"title": Path(docs_path).stem,
                                                    "summary": ""}
    return {
        "title": meta["title"],
        "path": docs_path,
        "summary": meta["summary"],
        "body_url": _body_url(docs_path),
    }


def _safe_vault_path(raw: str):
    """Resolve a repo-relative path inside the narrative vault, or None.

    Rejects absolute paths and traversal, and never returns anything under
    ``dev_tasks/``. Callers must treat "not allowed" and "not found" the same,
    so repeating the check cannot leak the dev-task tree.
    """
    if not raw:
        return None
    normalised = raw.replace("\\", "/")
    if normalised.startswith("/"):
        return None
    if ".." in normalised.split("/"):
        return None
    candidate = (REPO_ROOT / normalised).resolve()
    try:
        rel = candidate.relative_to(VAULT.resolve())
    except ValueError:
        return None
    if "dev_tasks" in rel.parts:
        return None
    if not candidate.is_file():
        return None
    return candidate


# ── handlers ──────────────────────────────────────────────────────────────


def handle_docs_resolve(app):
    module = request.args.get("module")
    node = request.args.get("node")
    index = _maybe_index()
    if module:
        docs_path = index["module"].get(module.strip())
    elif node:
        docs_path = index["node"].get(node.strip())
    else:
        return jsonify({"error": "provide ?module= or ?node="}), 400
    if not docs_path:
        return jsonify([])
    return jsonify([_entry(docs_path)])


def handle_docs_body(app):
    raw = request.args.get("path", "")
    path = _safe_vault_path(raw)
    if path is None:
        # Same response for "outside the allowlist", "dev_tasks", and "missing".
        return jsonify({"error": "not found"}), 404
    text = path.read_text(encoding="utf-8", errors="replace")
    return app.response_class(text, mimetype="text/markdown; charset=utf-8")
