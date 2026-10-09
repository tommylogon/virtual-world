"""Audit done/review dev-task files for claims the code no longer supports.

Read-only diagnostic (NOT a gate, no hook). It does not decide a task is
unfinished — it ranks suspicion so a human/subagent pass only has to read the
flagged subset, not all ~700 files.

Signals (strong -> weak):
  * status/folder mismatch
  * an unchecked acceptance box (``- [ ]``)
  * acceptance still says TODO
  * a supersede/replace link to another task id
  * a referenced file that no longer exists anywhere in the repo
  * a referenced ``tests/test_*.py`` that does not exist
  * a referenced ``task-NNN`` / ``bug-NN`` id that does not exist
  * body phrasing that admits incompleteness (deferred / not done / out of date)

Usage:
    python tools/task_done_audit.py [--status done|review|both] [--json PATH] [--area NAME]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS = os.path.join(ROOT, "docs", "virtualWorld", "dev_tasks")

FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---", re.S)
STATUS_RE = re.compile(r"^status:\s*(.+?)\s*$", re.M)
ID_RE = re.compile(r"\b(task|bug)-?(\d+)\b", re.I)
PATH_RE = re.compile(r"`([A-Za-z0-9_./\\-]+\.(?:py|ts|js|json|md|html|css))`")
SYMBOL_RE = re.compile(r"`([a-z_][a-z0-9_]*)\s*\(\)`")
UNCHECKED_RE = re.compile(r"^\s*[-*]\s*\[ \]\s*\S", re.M)
INCOMPLETE = re.compile(
    r"\b(deferred|not done|not implemented|never implemented|out of date|"
    r"superseded|replaced by|no longer|remains|still todo|partial)\b", re.I)
SUPERSEDE = re.compile(
    r"(supersed\w*|replaced by|folded into|obsoleted by)\s*[:\-]?\s*"
    r"((?:task|bug)-?\d+)", re.I)


def repo_files():
    """(basenames, stems) present in the repo, so a renamed file still matches."""
    names, stems = set(), set()
    try:
        out = subprocess.check_output(["git", "ls-files"], cwd=ROOT,
                                      encoding="utf-8", errors="replace")
        for line in out.splitlines():
            line = line.strip().replace("\\", "/")
            if line:
                base = os.path.basename(line)
                names.add(base)
                stems.add(os.path.splitext(base)[0])
    except Exception:
        pass
    # include untracked new files too, and treat DIRECTORY names as stems: a
    # file that was split into a folder (`prompt-builder.js` ->
    # `prompt-builder/*.ts`) is a rename, not a missing file, and would
    # otherwise dominate the report.
    for dirpath, dirnames, files in os.walk(ROOT):
        if ".git" in dirpath or ".kilo" in dirpath:
            continue
        for d in dirnames:
            stems.add(d)
        for f in files:
            names.add(f)
            stems.add(os.path.splitext(f)[0])
    return names, stems


def all_task_ids():
    ids = set()
    for dirpath, _, files in os.walk(TASKS):
        for f in files:
            m = re.match(r"(task|bug)-?(\d+)", f, re.I)
            if m:
                ids.add(f"{m.group(1).lower()}-{m.group(2)}")
    return ids


def parse(path):
    # These files carry mixed encodings (BOM, cp1252 mojibake); never fail on
    # decode, just read what is readable.
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        text = fh.read()
    fm = FRONTMATTER.search(text)
    status = ""
    if fm:
        m = STATUS_RE.search(fm.group(1))
        if m:
            status = m.group(1).strip().strip("\"'").lower()
    return text, status


def folder_of(path):
    rel = os.path.relpath(path, TASKS).replace("\\", "/")
    return rel.split("/")[0], rel.split("/")[1] if "/" in rel else ""


NOT_DONE_SECTION = re.compile(
    r"^#{1,4}\s*(not done|future|remaining|deferred|todo|still to do)\b",
    re.M | re.I)


def audit_file(path, files, stems, ids):
    text, status = parse(path)
    folder, area = folder_of(path)
    reasons = []

    if status and status not in ("done", "cancelled", "superseded") and folder == "done":
        reasons.append(("status-mismatch", f"frontmatter='{status}' folder='{folder}'"))
    if folder == "review" and status == "done":
        reasons.append(("status-mismatch", "frontmatter='done' folder='review'"))

    unchecked = UNCHECKED_RE.findall(text)
    if unchecked:
        reasons.append(("unchecked-acceptance", f"{len(unchecked)} unchecked box(es)"))

    if "## Acceptance" in text or "## acceptance" in text:
        tail = text.split("## Acceptance", 1)[-1]
        if re.search(r"^\s*[-*]\s*TODO\s*$", tail, re.M | re.I):
            reasons.append(("acceptance-todo", "acceptance section still TODO"))

    for m in SUPERSEDE.finditer(text):
        tid = m.group(2).lower()
        if tid in ids:
            reasons.append(("superseded-link", f"-> {tid}"))

    missing_files = []
    for ref in set(PATH_RE.findall(text)):
        base = os.path.basename(ref.replace("\\", "/"))
        stem = os.path.splitext(base)[0]
        # tolerate a rename: basename OR stem existing anywhere clears it
        if base not in files and stem not in stems:
            missing_files.append(ref)
    if missing_files:
        reasons.append(("missing-file", ", ".join(sorted(missing_files)[:4])))

    missing_tests = [r for r in missing_files if r.startswith("tests/test_")]
    if missing_tests:
        reasons.append(("missing-test", ", ".join(missing_tests[:4])))

    if NOT_DONE_SECTION.search(text):
        reasons.append(("not-done-section", NOT_DONE_SECTION.search(text).group(1).lower()))

    missing_ids = sorted({m.group(0).lower() for m in ID_RE.finditer(text)
                          if m.group(0).lower() not in ids})
    if missing_ids:
        reasons.append(("missing-task-ref", ", ".join(missing_ids[:5])))

    # Weak signal: only surface it when something stronger already fired, else
    # every done task that says "remains"/"future" gets flagged.
    hits = {h.lower() for h in INCOMPLETE.findall(text)}
    strong = [r for r in reasons if r[0] != "incomplete-phrasing"]
    if hits and strong:
        reasons.append(("incomplete-phrasing", ", ".join(sorted(hits))))

    return {"path": os.path.relpath(path, ROOT).replace("\\", "/"),
            "folder": folder, "area": area, "status": status,
            "reasons": reasons}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", choices=["done", "review", "both"], default="both")
    ap.add_argument("--area")
    ap.add_argument("--json")
    args = ap.parse_args()

    files, stems = repo_files()
    ids = all_task_ids()
    statuses = ["done", "review"] if args.status == "both" else [args.status]

    results = []
    for st in statuses:
        base = os.path.join(TASKS, st)
        for dirpath, _, fnames in os.walk(base):
            for f in fnames:
                if not f.endswith(".md"):
                    continue
                path = os.path.join(dirpath, f)
                _, area = folder_of(path)
                if args.area and area != args.area:
                    continue
                r = audit_file(path, files, stems, ids)
                if r["reasons"]:
                    results.append(r)

    # rank: strong signals first
    weight = {"unchecked-acceptance": 5, "acceptance-todo": 5,
              "not-done-section": 5, "missing-file": 4, "missing-test": 5,
              "superseded-link": 4, "status-mismatch": 3, "missing-task-ref": 2,
              "incomplete-phrasing": 1}
    for r in results:
        r["score"] = sum(weight.get(k, 1) for k, _ in r["reasons"])
    results.sort(key=lambda r: (-r["score"], r["path"]))

    by_area = {}
    for r in results:
        by_area.setdefault(r["folder"] + "/" + r["area"], 0)
        by_area[r["folder"] + "/" + r["area"]] += 1

    print(f"scanned done+review; {len(results)} file(s) flagged "
          f"(of {sum(1 for d,_,fs in os.walk(TASKS) for f in fs if f.endswith('.md') and ('/done/' in d.replace(chr(92),'/') or '/review/' in d.replace(chr(92),'/')))})\n")
    print("flagged by folder/area:")
    for k in sorted(by_area):
        print(f"  {k:<28} {by_area[k]}")
    print()
    print("top suspects (strongest signals):")
    for r in results[:40]:
        codes = ",".join(k for k, _ in r["reasons"])
        print(f"  [{r['score']:>2}] {r['path']}")
        print(f"        {codes}")
        for k, v in r["reasons"]:
            if k in ("missing-file", "missing-test", "superseded-link",
                     "status-mismatch", "acceptance-todo", "missing-task-ref"):
                print(f"          {k}: {v}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
