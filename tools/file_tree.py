#!/usr/bin/env python3
"""Write a directory tree of the repo to a text file.

Default output: ``file_tree.txt`` at the repo root. VCS, dependency and cache
directories are excluded so the listing is the project's own files; pass
``--include <name>`` to keep one back, or ``--exclude <name>`` to drop more.
``.kilo/worktrees`` (managed git worktrees) is always excluded.

Usage::

    python tools/file_tree.py
    python tools/file_tree.py --out docs/File\\ Tree.txt
    python tools/file_tree.py --include node_modules
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Directory names pruned anywhere in the tree.
DEFAULT_EXCLUDES = {
    ".git", "node_modules", "__pycache__", ".pytest_cache", ".playwright-mcp",
    ".mypy_cache", ".ruff_cache", ".venv", "venv",
}
# Repo-relative paths pruned (substrings of the tree, not single names).
SUB_EXCLUDES = {".kilo/worktrees", "file_tree.txt"}


def _excluded(rel: str, names: set) -> bool:
    """True if the repo-relative posix path should be skipped."""
    parts = rel.split("/")
    if any(part in names for part in parts):
        return True
    return any(rel == s or rel.startswith(s + "/") for s in SUB_EXCLUDES)


def walk(directory: Path, prefix: str, lines: list, counts: dict, names: set) -> None:
    try:
        entries = sorted(directory.iterdir(),
                         key=lambda p: (p.is_file(), p.name.lower()))
    except (PermissionError, OSError) as exc:                       # noqa: BLE001
        lines.append(f"{prefix}[cannot read: {exc}]")
        return

    entries = [e for e in entries
               if not _excluded(e.relative_to(ROOT).as_posix(), names)]
    for i, entry in enumerate(entries):
        last = i == len(entries) - 1
        connector = "`-- " if last else "|-- "
        if entry.is_dir():
            counts["dirs"] += 1
            lines.append(f"{prefix}{connector}{entry.name}/")
            walk(entry, prefix + ("    " if last else "|   "), lines, counts, names)
        else:
            counts["files"] += 1
            lines.append(f"{prefix}{connector}{entry.name}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="file_tree.txt", help="output path (default file_tree.txt)")
    ap.add_argument("--include", action="append", default=[],
                    help="re-include a normally-excluded directory name")
    ap.add_argument("--exclude", action="append", default=[],
                    help="additionally exclude a directory name")
    args = ap.parse_args()

    names = (DEFAULT_EXCLUDES - set(args.include)) | set(args.exclude)

    lines = [f"# File tree of {ROOT}", f"# generated {_dt.date.today().isoformat()}", ""]
    counts = {"dirs": 0, "files": 0}
    lines.append(f"{ROOT.name}/")
    walk(ROOT, "", lines, counts, names)

    lines.append("")
    lines.append(f"{counts['dirs']} directories, {counts['files']} files")
    lines.append(f"excluded dirs: {', '.join(sorted(names))}")
    lines.append(f"excluded paths: {', '.join(sorted(SUB_EXCLUDES))}")
    text = "\n".join(lines) + "\n"

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out} ({counts['dirs']} dirs, {counts['files']} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
