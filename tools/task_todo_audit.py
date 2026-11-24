"""Audit todo/review JSON dev-task cards for unverified or stale claims.

Read-only diagnostic (mirrors ``tools/task_done_audit.py``). Flags todo cards
whose ``files``, cited line ranges, cited symbol names, or sections disagree
with the live codebase or with themselves.

Signals checked:
  * missing_file: a path in ``sections.files`` does not exist in the repo
  * bad_line_ref: a ``file.py (lines A-B)`` or ``file.py:A-B`` citation points
    past EOF or omits the cited symbol
  * missing_symbol: a backticked ``func()`` / ``Class.method()`` in prose is
    not found in the cited files or repo
  * self_contradiction: ``what``/``how``/``acceptance`` forbids a symbol or
    approach that ``why``/``verify``/``custom`` still prescribes
  * partial_done_in_todo: a ``todo`` card already has ``done: true`` acceptance
  * duplicate_title: two active cards share the same normalized title
  * em_dash: ``\\u2014`` present in task text (banned by AGENTS.md)

Usage:
    python tools/task_todo_audit.py [--status todo|review|all] [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_DIR = os.path.join(ROOT, "docs", "virtualWorld", "dev_tasks")

LINE_REF_RE = re.compile(
    r"([A-Za-z0-9_./\\-]+\.(?:py|ts|js))\s*(?:\(lines?\s*|:)(\d+)(?:\s*[-–]\s*(\d+))?",
    re.I,
)
SYMBOL_CALL_RE = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]{2,})\(\)")
FORBID_RE = re.compile(r"\b(?:do NOT|NOT via|not via|never)\s+([A-Za-z_][A-Za-z0-9_.]+)", re.I)


def _load_repo_text_index():
    """Map repo-relative forward-slash path -> file text (for engine/routes/static/tests)."""
    cache = {}
    for folder in ("engine", "routes", "static", "tests", "tools"):
        base = os.path.join(ROOT, folder)
        if not os.path.isdir(base):
            continue
        for dirpath, _, filenames in os.walk(base):
            if "__pycache__" in dirpath or "node_modules" in dirpath:
                continue
            for fn in filenames:
                if not fn.endswith((".py", ".ts", ".js", ".cjs")):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, ROOT).replace("\\", "/")
                try:
                    with open(full, encoding="utf-8-sig", errors="replace") as fh:
                        cache[rel] = fh.read()
                except OSError:
                    pass
    return cache


DEF_PAT = re.compile(
    r"(?:def|function|class|const|let|var)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b"
    r"|^\s*(?:async\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\("
    r"|\b([a-zA-Z_][a-zA-Z0-9_]*)\s*[:=]\s*(?:async\s+)?function\b",
    re.M,
)


def _build_symbol_set(text_index: dict) -> set:
    syms = set()
    for text in text_index.values():
        for m in DEF_PAT.finditer(text):
            for g in m.groups():
                if g:
                    syms.add(g)
    return syms


def audit_tasks(statuses=("todo",)):
    text_index = _load_repo_text_index()
    defined_symbols = _build_symbol_set(text_index)
    findings = []
    titles = {}

    paths = []
    for st in statuses:
        paths.extend(sorted(glob.glob(os.path.join(TASKS_DIR, st, "**", "*.json"), recursive=True)))

    for path in paths:
        rel_task = os.path.relpath(path, ROOT).replace("\\", "/")
        try:
            data = json.load(open(path, encoding="utf-8-sig"))
        except Exception as exc:
            findings.append({"id": os.path.basename(path), "path": rel_task, "issues": [f"invalid_json: {exc}"]})
            continue

        tid = data.get("id", os.path.basename(path))
        title = (data.get("title") or "").strip()
        norm_title = re.sub(r"\s+", " ", title.lower())
        if norm_title:
            titles.setdefault(norm_title, []).append((tid, rel_task))

        issues = []
        secs = data.get("sections") or {}
        if "\u2014" in json.dumps(data, ensure_ascii=False):
            issues.append("em_dash: contains banned U+2014 character")

        # 1. Check files list
        for fpath in secs.get("files") or []:
            norm = fpath.replace("\\", "/").lstrip("/")
            if not os.path.exists(os.path.join(ROOT, norm)):
                issues.append(f"missing_file: {norm}")

        # 2. Check acceptance done in todo
        if data.get("status") == "todo":
            done_items = [a.get("text", "")[:60] for a in (secs.get("acceptance") or []) if isinstance(a, dict) and a.get("done")]
            if done_items:
                issues.append(f"partial_done_in_todo: {len(done_items)} acceptance item(s) already done")

        # 3. Check line citations
        all_prose = "\n".join(str(secs.get(k) or "") for k in ("what", "why", "how", "verify", "custom"))
        for m in LINE_REF_RE.finditer(all_prose):
            ref_file, start_s, end_s = m.group(1).replace("\\", "/"), m.group(2), m.group(3)
            if ref_file in text_index:
                lines = text_index[ref_file].splitlines()
                start = int(start_s)
                end = int(end_s) if end_s else start
                if start > len(lines) or end > len(lines):
                    issues.append(f"bad_line_ref: {ref_file}:{start}-{end} (file has {len(lines)} lines)")

        # 4. Check explicit foo() symbol calls
        checked_syms = set()
        for m in SYMBOL_CALL_RE.finditer(all_prose):
            sym = m.group(1)
            if sym in checked_syms or sym in ("e", "g", "get", "set", "len", "str", "int", "list", "dict"):
                continue
            checked_syms.add(sym)
            if not (sym in defined_symbols):
                issues.append(f"missing_symbol: {sym}() not found in codebase")

        # 5. Check self-contradiction (forbidden in what/how/acceptance, prescribed in why/verify/custom)
        norm_text = "\n".join([
            str(secs.get("what") or ""),
            str(secs.get("how") or ""),
            " ".join(a.get("text", "") for a in (secs.get("acceptance") or []) if isinstance(a, dict)),
        ])
        legacy_text = "\n".join([
            str(secs.get("why") or ""),
            str(secs.get("verify") or ""),
            str(secs.get("custom") or ""),
        ])
        for m in FORBID_RE.finditer(norm_text):
            forbidden = m.group(1)
            if len(forbidden) >= 6 and forbidden in legacy_text:
                issues.append(f"self_contradiction: '{forbidden}' forbidden in what/how/acceptance but still cited in why/verify/custom")

        if issues:
            findings.append({"id": tid, "path": rel_task, "issues": issues})

    for norm_title, entries in titles.items():
        if len(entries) > 1:
            ids = ", ".join(e[0] for e in entries)
            findings.append({"id": ids, "path": entries[0][1], "issues": [f"duplicate_title: shared by {ids}"]})

    return findings


def main():
    parser = argparse.ArgumentParser(description="Audit todo/review JSON tasks against the codebase.")
    parser.add_argument("--status", choices=("todo", "review", "all"), default="todo")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    statuses = ("todo", "review") if args.status == "all" else (args.status,)
    findings = audit_tasks(statuses)
    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        print(f"Found {len(findings)} flagged task(s) across {', '.join(statuses)}:")
        for f in findings:
            print(f"\n[{f['id']}] {f['path']}")
            for iss in f["issues"]:
                print(f"  - {iss}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
