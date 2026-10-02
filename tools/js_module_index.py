#!/usr/bin/env python3
"""Generate (and guard) the module index — front end and back end.

Every non-vendor module under ``static/js`` is expected to open with a leading
comment block carrying this contract, and every module under ``engine/`` and
``routes/`` is expected to carry the same contract at the top of its module
docstring (task-576). The file keeps its historical ``js_`` name so
``npm run module:check`` and the docs that cite it keep working.

    /**
     * @module <name> — <one-line purpose>
     * @contributes <what state/behaviour it owns>
     * @powers <user-facing feature(s) it enables>
     * @relates <depends on / used by>
     * @docs <docs path or 'none'>
     */

Usage:
    python tools/js_module_index.py --write            # regenerate the index
    python tools/js_module_index.py --update-baseline  # accept today's uncovered files
    python tools/js_module_index.py --check            # fail on a NEW contract gap

``@docs`` is checked too, because a folder is not a document: 26 of 43 unresolved
declarations were things like ``docs/virtualWorld/Library System/``, which satisfy
the contract while pointing at nothing readable. A target must be ``none`` or
resolve to a real note. The declared features live in
``docs/virtualWorld/Feature Map.md`` and are checked separately by
``tools/feature_index.py``.

The baselines exist so the not-yet-documented files and today's bad ``@docs``
targets don't block the guard; new modules are held to the contract from day one.
``docs/design/js-module-baseline.txt`` is the JS list and
``docs/design/py-module-baseline.txt`` the Python one, so the back end's much
larger existing debt can ratchet down without blocking the front end.

Python tags are read from the real module docstring (via ``ast``), not a fixed
line window, so a header may sit anywhere in a long docstring.
"""
from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path

ROOT = Path("static/js")
# task-576: the same contract covers the back end. The rules engine is where a
# feature's behaviour actually lives, so a docs map that stops at `static/js`
# documents less than half the codebase. This file keeps its historical name so
# `npm run module:check` and every doc that cites it keep working; it is now
# language-agnostic.
PY_ROOTS = (Path("engine"), Path("routes"))
SKIP_DIRS = {"vendor", "node_modules"}
INDEX_PATH = Path("docs/design/js-module-index.md")
BASELINE_PATH = Path("docs/design/js-module-baseline.txt")
DOCS_BASELINE_PATH = Path("docs/design/js-docs-baseline.txt")
PY_BASELINE_PATH = Path("docs/design/py-module-baseline.txt")
VAULT = Path("docs/virtualWorld")

TAGS = ("module", "contributes", "powers", "relates", "docs")
TAG_RE = re.compile(r"^\s*\*?\s*@(" + "|".join(TAGS) + r")\s+(.*)$")


def _leading_block(text: str, limit: int = 60) -> str:
    """Return the leading comment block (or '') from the first *limit* lines."""
    out = []
    in_block = False
    for line in text.splitlines()[:limit]:
        s = line.strip()
        if not in_block:
            # A TypeScript-emitted script may start with a directive, e.g.
            # "use strict"; — step over it to reach the documentation block.
            if s in ('"use strict";', "'use strict';"):
                continue
            if s.startswith(("/*", "//", "/**")):
                in_block = True
            else:
                break
        out.append(line)
        if in_block and s.endswith("*/") and not s.startswith("//"):
            break
    return "\n".join(out)


def parse(path: Path):
    # utf-8-sig strips a leading BOM. A BOM before ``/**`` otherwise defeats
    # _leading_block's startswith check, so a complete header parses as empty
    # (task-658: room-context.js was baselined for exactly this).
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    block = _leading_block(text)
    meta = {}
    for line in block.splitlines():
        m = TAG_RE.match(line)
        if m:
            meta.setdefault(m.group(1), m.group(2).strip())
    return meta


def parse_py(path: Path):
    """The same contract, read from a Python module docstring (task-576).

    Tags are plain lines at the top of the module docstring:

        \"\"\"One-line purpose.

        @module foraging
        @contributes the skill-gated draw, forage tables, regrowth
        @docs docs/virtualWorld/Gameplay/Search & Forage.md
        \"\"\"

    The whole module docstring is searched (via ``ast``), with the leading 80
    raw lines as a fallback for a module that has no parseable docstring. A tag
    only counts at the start of a line (indentation allowed), so a ``@docs``
    mentioned in prose mid-sentence is not mistaken for a declaration.
    """
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    source = "\n".join(text.splitlines()[:80])
    try:
        tree = ast.parse(text)
        first = tree.body[0] if tree.body else None
        if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)):
            source = first.value.value
    except SyntaxError:
        pass
    meta = {}
    for line in source.splitlines():
        m = TAG_RE.match(line)
        if m:
            meta.setdefault(m.group(1), m.group(2).strip())
    return meta


def language(path: Path) -> str:
    return "py" if path.suffix == ".py" else "js"


def collect():
    entries = []
    for path in sorted(ROOT.rglob("*.js")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        entries.append((path, parse(path)))
    for root in PY_ROOTS:
        for path in sorted(root.rglob("*.py")):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            entries.append((path, parse_py(path)))
    return entries


def uncovered(entries):
    return [str(p).replace("\\", "/") for p, meta in entries
            if not meta.get("module") or not meta.get("contributes")]


def _docs_note_candidates(value: str):
    """Where a declared @docs target could legitimately live."""
    raw = value.strip().strip("`")
    rel = raw.replace("\\", "/")
    yield Path(rel)
    # a vault-relative path, and the same path with a .md extension
    for base in (VAULT, Path("docs")):
        yield base / rel
        yield base / (rel + ".md")
    # a bare note title resolves anywhere in the vault
    if "/" not in rel:
        yield VAULT / (rel + ".md")


def docs_problems(entries):
    """@docs targets that are not a document.

    A folder satisfies the contract while pointing at nothing readable, which is
    how 26 declarations "resolved". Returns (path, reason) for each.
    """
    problems = []
    for path, meta in entries:
        if not (meta.get("module") and meta.get("contributes")):
            continue  # already handled by the uncovered baseline
        raw = (meta.get("docs") or "").strip()
        rel = str(path).replace("\\", "/")
        # `@docs none` is a decision; `@docs none — <reason>` is the documented
        # form (task-576), so test the first token, not the whole value.
        head = raw.split(None, 1)[0].lower() if raw else ""
        if not raw or head in ("none", "n/a", "-"):
            continue
        if raw.endswith(("/", "\\")):
            problems.append((rel, "folder target — a directory is not a note: %s" % raw))
            continue
        for cand in _docs_note_candidates(raw):
            if cand.is_dir():
                problems.append((rel, "folder target — %s is a directory" % cand.as_posix()))
                break
            if cand.is_file():
                break
        else:
            problems.append((rel, "does not resolve to a file: %s" % raw))
    return problems


def write_index(entries):
    covered = [(p, m) for p, m in entries if m.get("module") and m.get("contributes")]
    gaps = [(p, m) for p, m in entries if not (m.get("module") and m.get("contributes"))]

    lines = [
        "# Module index",
        "",
        "Generated by `tools/js_module_index.py` — do not hand-edit.",
        "Each row is the module's own `@module` / `@contributes` / `@powers` contract.",
        "Front-end (`.js`) and back-end (`.py`) modules share the contract.",
        "",
        f"- Modules scanned: **{len(entries)}**",
        f"- Documented: **{len(covered)}**",
        f"- Awaiting a contract header: **{len(gaps)}**",
        "",
        "## Documented modules",
        "",
        "| Module | Lang | Purpose | File | Contributes | Powers | Docs |",
        "|---|---|---|---|---|---|---|",
    ]
    for path, meta in covered:
        rel = str(path).replace("\\", "/")

        def cell(key):
            return (meta.get(key) or "").replace("|", "\\|")

        module_value = cell("module")
        for sep in ("\u2014", "\u2013"):
            if sep in module_value:
                name, _, purpose = module_value.partition(sep)
                break
        else:
            name, purpose = module_value, ""
        lines.append(
            f"| `{name.strip()}` | {language(path)} | {purpose.strip()} | `{rel}` | "
            f"{cell('contributes')} | {cell('powers')} | {cell('docs')} |"
        )

    lines += ["", "## Awaiting a contract header", "",
              "These predate the contract; the guard ignores them until they are documented.", ""]
    for path, _ in gaps:
        lines.append(f"- `{str(path).replace(chr(92), '/')}`")
    lines.append("")

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"{INDEX_PATH}: {len(covered)} documented, {len(gaps)} awaiting.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="regenerate the index")
    parser.add_argument("--check", action="store_true", help="fail on new uncovered modules")
    parser.add_argument("--update-baseline", action="store_true", help="record the uncovered list")
    args = parser.parse_args()

    entries = collect()
    gaps = uncovered(entries)
    js_gaps = [g for g in gaps if g.endswith(".js")]
    py_gaps = [g for g in gaps if g.endswith(".py")]
    bad_docs = docs_problems(entries)

    if args.update_baseline:
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text("\n".join(js_gaps) + "\n", encoding="utf-8")
        print(f"{BASELINE_PATH}: recorded {len(js_gaps)} uncovered JS module(s).")
        PY_BASELINE_PATH.write_text("\n".join(py_gaps) + "\n", encoding="utf-8")
        print(f"{PY_BASELINE_PATH}: recorded {len(py_gaps)} uncovered Python module(s).")
        DOCS_BASELINE_PATH.write_text(
            "\n".join("%s\t%s" % (p, r) for p, r in bad_docs) + "\n", encoding="utf-8")
        print(f"{DOCS_BASELINE_PATH}: recorded {len(bad_docs)} bad @docs target(s).")
    if args.write or not (args.check or args.update_baseline):
        write_index(entries)

    if args.check:
        for label, baseline, current in (
                ("JS", BASELINE_PATH, js_gaps),
                ("Python", PY_BASELINE_PATH, py_gaps)):
            if not baseline.exists():
                print(f"{baseline} missing — run --update-baseline once.")
                return 2
            known = set(baseline.read_text(encoding="utf-8").split())
            new_gaps = [g for g in current if g not in known]
            if new_gaps:
                print(f"New {label} modules missing the @module/@contributes contract:")
                for g in new_gaps:
                    print("  -", g)
                return 1

        if not DOCS_BASELINE_PATH.exists():
            print(f"{DOCS_BASELINE_PATH} missing — run --update-baseline once.")
            return 2
        known_docs = set()
        for line in DOCS_BASELINE_PATH.read_text(encoding="utf-8").splitlines():
            if "\t" in line:
                known_docs.add(line.split("\t", 1)[0])
        new_docs = [(p, r) for p, r in bad_docs if p not in known_docs]
        if new_docs:
            print("New @docs targets that are not a note (a folder or a dead path):")
            for p, r in new_docs:
                print("  - %s: %s" % (p, r))
            return 1

        print(f"Contract check OK ({len(gaps)} known-uncovered, "
              f"{len(bad_docs)} known-bad-@docs, no new).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
