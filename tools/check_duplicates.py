"""Detect literal, structural, and semantic duplicates across the repository.

Checks:
1. HTML templates (templates/*.html): duplicate `data-config` bindings and duplicate `id`s.
2. Structural & token similarity: normalized AST/block clones + Jaccard token pairs.
3. Literal clones (`--jscpd` or `--all`): invokes `npx --yes jscpd` for token clones.
4. Semantic vector similarity (`--semantic` or `--all`): batch-embeds functions via
   an OpenAI-compatible `/v1/embeddings` endpoint (e.g. llama.cpp or LM Studio) and
   computes an in-memory cosine similarity matrix.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv"}


@dataclass
class CodeUnit:
    """Normalized representation of a function or method for similarity checks."""

    lang: str
    file: str
    name: str
    line: int
    end_line: int
    struct_hash: str
    tokens: frozenset[str]
    snippet: str


class _TemplateAttrParser(HTMLParser):
    """Collect `id` and `data-config` occurrences with line numbers from HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: dict[str, list[int]] = defaultdict(list)
        self.data_configs: dict[str, list[int]] = defaultdict(list)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        line = self.getpos()[0]
        attr_map = dict(attrs)
        el_id = attr_map.get("id")
        if el_id:
            self.ids[el_id].append(line)
        cfg = attr_map.get("data-config")
        if cfg:
            self.data_configs[cfg].append(line)


def check_templates() -> list[dict[str, object]]:
    """Find duplicate `data-config` keys and duplicate element `id`s in templates."""
    findings: list[dict[str, object]] = []
    tpl_dir = ROOT / "templates"
    if not tpl_dir.exists():
        return findings

    for html_file in sorted(tpl_dir.glob("*.html")):
        parser = _TemplateAttrParser()
        parser.feed(html_file.read_text(encoding="utf-8", errors="replace"))
        rel = str(html_file.relative_to(ROOT))
        for key, lines in sorted(parser.data_configs.items()):
            if len(lines) > 1:
                findings.append({"kind": "duplicate-data-config", "file": rel, "key": key, "lines": lines})
        for el_id, lines in sorted(parser.ids.items()):
            if len(lines) > 1:
                findings.append({"kind": "duplicate-html-id", "file": rel, "key": el_id, "lines": lines})
    return findings


class _AstNormalizer(ast.NodeTransformer):
    """Strip variable names and literal values so structurally identical ASTs match."""

    def visit_Name(self, node: ast.Name) -> ast.AST:
        return ast.copy_location(ast.Name(id="_V", ctx=node.ctx), node)

    def visit_arg(self, node: ast.arg) -> ast.AST:
        return ast.copy_location(ast.arg(arg="_A", annotation=None), node)

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        return ast.copy_location(ast.Constant(value=type(node.value).__name__), node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self.generic_visit(node)
        node.name = "_FN"
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        self.generic_visit(node)
        node.name = "_FN"
        return node


_COMMON_PY_TOKENS = {
    "get", "set", "items", "keys", "values", "append", "extend", "update",
    "lower", "upper", "strip", "split", "join", "replace", "startswith", "endswith",
    "isinstance", "len", "str", "int", "float", "bool", "dict", "list", "set",
    "getattr", "hasattr", "setattr", "any", "all", "min", "max", "sorted", "enumerate",
}


def _py_tokens(node: ast.AST) -> frozenset[str]:
    """Extract domain-specific semantic tokens (called names and attribute names)."""
    toks: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name) and child.func.id not in _COMMON_PY_TOKENS:
                toks.add(f"call:{child.func.id}")
            elif isinstance(child.func, ast.Attribute) and child.func.attr not in _COMMON_PY_TOKENS:
                toks.add(f"attr:{child.func.attr}")
        elif isinstance(child, ast.Attribute) and child.attr not in _COMMON_PY_TOKENS:
            toks.add(f"attr:{child.attr}")
    return frozenset(toks)


def collect_python_units(min_lines: int) -> list[CodeUnit]:
    """Parse Python files under engine/ into normalized CodeUnits."""
    units: list[CodeUnit] = []
    engine_dir = ROOT / "engine"
    if not engine_dir.exists():
        return units

    for py_file in sorted(engine_dir.rglob("*.py")):
        if any(part in SKIP_DIRS for part in py_file.parts):
            continue
        src = py_file.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src, filename=str(py_file))
        except SyntaxError:
            continue
        rel = str(py_file.relative_to(ROOT))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            end_line = getattr(node, "end_lineno", node.lineno) or node.lineno
            if (end_line - node.lineno + 1) < min_lines:
                continue
            # Drop leading docstring before hashing so comment edits do not hide clones.
            body = list(node.body)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                body = body[1:]
            if len(body) < 3:
                continue
            clone = ast.Module(body=body, type_ignores=[])
            normalized = _AstNormalizer().visit(clone)
            dumped = ast.dump(normalized, include_attributes=False)
            struct_hash = hashlib.sha1(dumped.encode("utf-8")).hexdigest()[:16]
            src_lines = src.splitlines()
            fn_slice = "\n".join(src_lines[node.lineno - 1 : min(end_line, node.lineno + 39)])[:1500]
            units.append(CodeUnit(
                lang="python",
                file=rel,
                name=node.name,
                line=node.lineno,
                end_line=end_line,
                struct_hash=struct_hash,
                tokens=_py_tokens(node),
                snippet=f"{rel} :: {node.name}\n{fn_slice}",
            ))
    return units


_TS_FN_RE = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:function\s+([A-Za-z_$][\w$]*)|([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*(?::\s*[^{]+)?\{)"
)
_TS_IDENT_RE = re.compile(r"\b[A-Za-z_$][\w$]*\b")
_TS_STR_RE = re.compile(r"(['\"`])(?:\\.|(?!\1).)*\1")
_TS_KEYWORDS = {
    "if", "else", "for", "while", "return", "const", "let", "var", "await",
    "async", "function", "try", "catch", "finally", "throw", "new", "typeof",
    "true", "false", "null", "undefined", "switch", "case", "break", "continue",
}


def _normalize_ts_block(lines: list[str]) -> tuple[str, frozenset[str]]:
    """Produce an identifier-normalized hash and semantic token set for a TS block."""
    norm_lines: list[str] = []
    tokens: set[str] = set()
    for raw in lines:
        stripped = re.sub(r"//.*$", "", raw).strip()
        if not stripped:
            continue
        for m in _TS_IDENT_RE.finditer(stripped):
            ident = m.group(0)
            if ident not in _TS_KEYWORDS and len(ident) > 2:
                tokens.add(ident)
        no_str = _TS_STR_RE.sub("_S", stripped)
        norm = _TS_IDENT_RE.sub(lambda m: m.group(0) if m.group(0) in _TS_KEYWORDS else "_I", no_str)
        norm_lines.append(norm)
    digest = hashlib.sha1("\n".join(norm_lines).encode("utf-8")).hexdigest()[:16]
    return digest, frozenset(tokens)


def collect_ts_units(min_lines: int) -> list[CodeUnit]:
    """Scan static/js/**/*.ts for function/method blocks."""
    units: list[CodeUnit] = []
    js_dir = ROOT / "static" / "js"
    if not js_dir.exists():
        return units

    for ts_file in sorted(js_dir.rglob("*.ts")):
        if ts_file.name.endswith(".d.ts") or any(part in SKIP_DIRS for part in ts_file.parts):
            continue
        lines = ts_file.read_text(encoding="utf-8", errors="replace").splitlines()
        rel = str(ts_file.relative_to(ROOT))
        i = 0
        while i < len(lines):
            m = _TS_FN_RE.match(lines[i])
            if not m or "{" not in lines[i]:
                i += 1
                continue
            fn_name = m.group(1) or m.group(2) or "<anon>"
            if fn_name in _TS_KEYWORDS:
                i += 1
                continue
            depth = 0
            j = i
            while j < len(lines):
                depth += lines[j].count("{") - lines[j].count("}")
                if depth <= 0 and j > i:
                    break
                j += 1
            length = j - i + 1
            if length >= min_lines and j < len(lines):
                struct_hash, tokens = _normalize_ts_block(lines[i + 1 : j])
                fn_slice = "\n".join(lines[i : min(j + 1, i + 40)])[:1500]
                units.append(CodeUnit(
                    lang="typescript",
                    file=rel,
                    name=fn_name,
                    line=i + 1,
                    end_line=j + 1,
                    struct_hash=struct_hash,
                    tokens=tokens,
                    snippet=f"{rel} :: {fn_name}\n{fn_slice}",
                ))
            i = j + 1
    return units


def find_clones_and_near_dups(
    units: list[CodeUnit], threshold: float, limit: int
) -> tuple[list[list[CodeUnit]], list[tuple[float, CodeUnit, CodeUnit]]]:
    """Group exact structural clones and rank high-Jaccard near-duplicate pairs."""
    by_hash: dict[tuple[str, str], list[CodeUnit]] = defaultdict(list)
    for u in units:
        by_hash[(u.lang, u.struct_hash)].append(u)
    exact_groups = [grp for grp in by_hash.values() if len(grp) > 1]
    exact_groups.sort(key=lambda g: (-len(g), -(g[0].end_line - g[0].line)))

    exact_pairs: set[tuple[str, int, str, int]] = set()
    for grp in exact_groups:
        for idx, a in enumerate(grp):
            for b in grp[idx + 1 :]:
                exact_pairs.add((a.file, a.line, b.file, b.line))

    near_pairs: list[tuple[float, CodeUnit, CodeUnit]] = []
    by_lang: dict[str, list[CodeUnit]] = defaultdict(list)
    for u in units:
        if len(u.tokens) >= 8:
            by_lang[u.lang].append(u)

    for lang_units in by_lang.values():
        n = len(lang_units)
        for idx in range(n):
            a = lang_units[idx]
            for jdx in range(idx + 1, n):
                b = lang_units[jdx]
                if a.file == b.file and abs(a.line - b.line) < 5:
                    continue
                if (a.file, a.line, b.file, b.line) in exact_pairs:
                    continue
                inter = len(a.tokens & b.tokens)
                if inter < 5:
                    continue
                union = len(a.tokens | b.tokens)
                sim = inter / union if union else 0.0
                if sim >= threshold:
                    near_pairs.append((sim, a, b))

    near_pairs.sort(key=lambda row: -row[0])
    return exact_groups[:limit], near_pairs[:limit]


def _http_json(url: str, payload: dict | None = None) -> dict:
    """Perform a GET or POST JSON request against an OpenAI-compatible endpoint."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _resolve_embed_model(embed_url: str, embed_model: str) -> str:
    """Return configured model or pick the first loaded model from /models."""
    if embed_model:
        return embed_model
    try:
        data = _http_json(f"{embed_url.rstrip('/')}/models")
        models = data.get("data") or []
        for m in models:
            mid = m.get("id", "")
            if "embed" in mid.lower():
                return mid
        if models and models[0].get("id"):
            return str(models[0]["id"])
    except Exception:
        pass
    return "text-embedding-nomic-embed-text-v1.5"


def _embed_texts(texts: list[str], embed_url: str, embed_model: str, batch_size: int = 64) -> list[list[float]]:
    """Batch-embed snippets and L2-normalize each vector for cosine similarity."""
    base = embed_url.rstrip("/")
    model = _resolve_embed_model(base, embed_model)
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        res = _http_json(f"{base}/embeddings", {"input": batch, "model": model})
        rows = sorted(res.get("data", []), key=lambda r: r.get("index", 0))
        for row in rows:
            vec = [float(x) for x in row["embedding"]]
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            vectors.append([x / norm for x in vec])
    return vectors


def find_semantic_duplicates(
    units: list[CodeUnit],
    embed_url: str,
    embed_model: str,
    threshold: float,
    limit: int,
) -> list[tuple[float, CodeUnit, CodeUnit]]:
    """Find cross-function semantic duplicates via in-memory cosine similarity."""
    if len(units) < 2:
        return []
    vectors = _embed_texts([u.snippet for u in units], embed_url, embed_model)
    if len(vectors) != len(units):
        return []

    pairs: list[tuple[float, CodeUnit, CodeUnit]] = []
    try:
        import numpy as np  # type: ignore

        mat = np.asarray(vectors, dtype=np.float32)
        sim_mat = mat @ mat.T
        n = len(units)
        for i in range(n):
            a = units[i]
            row = sim_mat[i]
            # Vectorized threshold mask on upper triangle.
            hits = np.where(row[i + 1 :] >= threshold)[0]
            for offset in hits:
                j = i + 1 + int(offset)
                b = units[j]
                if a.lang != b.lang:
                    continue
                if a.struct_hash == b.struct_hash:
                    continue
                if a.file == b.file and abs(a.line - b.line) < 5:
                    continue
                pairs.append((float(row[j]), a, b))
    except ImportError:
        n = len(units)
        for i in range(n):
            a, va = units[i], vectors[i]
            for j in range(i + 1, n):
                b = units[j]
                if a.lang != b.lang or a.struct_hash == b.struct_hash:
                    continue
                if a.file == b.file and abs(a.line - b.line) < 5:
                    continue
                sim = sum(x * y for x, y in zip(va, vectors[j]))
                if sim >= threshold:
                    pairs.append((sim, a, b))

    pairs.sort(key=lambda r: -r[0])
    return pairs[:limit]


def run_jscpd(min_lines: int) -> int:
    """Invoke npx jscpd for cross-language literal/token clone detection."""
    npx = shutil.which("npx")
    if not npx:
        print("npx not found on PATH; skipping jscpd.", file=sys.stderr)
        return 0
    cmd = [
        npx, "--yes", "jscpd", "static/js", "engine", "templates",
        "--ignore", "**/*.js",
        "--min-lines", str(min_lines),
        "--min-tokens", "50",
        "--reporters", "console",
    ]
    return subprocess.run(cmd, cwd=str(ROOT), check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Check for UI, literal, structural, and semantic duplicates.")
    parser.add_argument("--min-lines", type=int, default=6, help="Minimum function lines to inspect (default: 6)")
    parser.add_argument("--threshold", type=float, default=0.80, help="Jaccard token similarity threshold (default: 0.80)")
    parser.add_argument("--semantic-threshold", type=float, default=0.88, help="Vector cosine similarity threshold (default: 0.88)")
    parser.add_argument("--limit", type=int, default=20, help="Max findings per section (default: 20)")
    parser.add_argument("--jscpd", action="store_true", help="Run `npx jscpd` literal token clone scan")
    parser.add_argument("--semantic", action="store_true", help="Run vector embedding similarity via /v1/embeddings")
    parser.add_argument("--all", action="store_true", help="Run structural/token, jscpd literal, and semantic vector passes")
    parser.add_argument(
        "--embed-url",
        default=os.environ.get("EMBEDDING_BASE_URL", "http://localhost:1234/v1"),
        help="OpenAI-compatible embeddings base URL (default: http://localhost:1234/v1)",
    )
    parser.add_argument(
        "--embed-model",
        default=os.environ.get("EMBEDDING_MODEL", ""),
        help="Embedding model ID (default: auto-detect from /models)",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON summary")
    args = parser.parse_args()

    run_literal = args.jscpd or args.all
    run_sem = args.semantic or args.all

    ui_findings = check_templates()
    units = collect_python_units(args.min_lines) + collect_ts_units(args.min_lines)
    exact_groups, near_pairs = find_clones_and_near_dups(units, args.threshold, args.limit)

    semantic_pairs: list[tuple[float, CodeUnit, CodeUnit]] = []
    semantic_error: str | None = None
    if run_sem:
        try:
            semantic_pairs = find_semantic_duplicates(
                units, args.embed_url, args.embed_model, args.semantic_threshold, args.limit
            )
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            semantic_error = f"Semantic embedding pass skipped ({exc})"

    if args.json:
        payload = {
            "ui_findings": ui_findings,
            "units_scanned": len(units),
            "exact_structural_groups": [
                [{"lang": u.lang, "file": u.file, "name": u.name, "lines": [u.line, u.end_line]} for u in g]
                for g in exact_groups
            ],
            "near_duplicate_pairs": [
                {
                    "similarity": round(sim, 3),
                    "a": {"lang": a.lang, "file": a.file, "name": a.name, "lines": [a.line, a.end_line]},
                    "b": {"lang": b.lang, "file": b.file, "name": b.name, "lines": [b.line, b.end_line]},
                }
                for sim, a, b in near_pairs
            ],
            "semantic_duplicate_pairs": [
                {
                    "similarity": round(sim, 3),
                    "a": {"lang": a.lang, "file": a.file, "name": a.name, "lines": [a.line, a.end_line]},
                    "b": {"lang": b.lang, "file": b.file, "name": b.name, "lines": [b.line, b.end_line]},
                }
                for sim, a, b in semantic_pairs
            ],
            "semantic_error": semantic_error,
        }
        print(json.dumps(payload, indent=2))
    else:
        print(f"=== UI TEMPLATE BINDINGS ({len(ui_findings)} findings) ===")
        for item in ui_findings:
            print(f"  [{item['kind']}] {item['file']} -> {item['key']} at lines {item['lines']}")

        print(f"\n=== STRUCTURAL CLONES (scanned {len(units)} functions, showing top {len(exact_groups)}) ===")
        for grp in exact_groups:
            locs = ", ".join(f"{u.file}:{u.line}({u.name})" for u in grp)
            print(f"  [{grp[0].lang} x{len(grp)}] {locs}")

        print(f"\n=== NEAR-DUPLICATE FUNCTIONS (Jaccard >= {args.threshold:.2f}, showing top {len(near_pairs)}) ===")
        for sim, a, b in near_pairs:
            print(f"  [{sim:.2f} {a.lang}] {a.file}:{a.line}({a.name})  <->  {b.file}:{b.line}({b.name})")

        if run_sem:
            print(f"\n=== SEMANTIC VECTOR DUPLICATES (cosine >= {args.semantic_threshold:.2f}, showing top {len(semantic_pairs)}) ===")
            if semantic_error:
                print(f"  {semantic_error}")
            else:
                for sim, a, b in semantic_pairs:
                    print(f"  [{sim:.3f} {a.lang}] {a.file}:{a.line}({a.name})  <->  {b.file}:{b.line}({b.name})")

    if run_literal:
        print("\n=== JSCPD LITERAL CLONE SCAN ===")
        run_jscpd(args.min_lines)

    return 1 if any(f["kind"] == "duplicate-data-config" for f in ui_findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
