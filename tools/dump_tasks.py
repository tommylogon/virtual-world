#!/usr/bin/env python3
"""Concatenate dev-task notes from selected status folders into one markdown file.

Reads every ``docs/virtualWorld/dev_tasks/<status>/**/*.md`` and writes them,
in status order, to a single file with a header per task. ``cancelled`` is
excluded by default; pass ``--include-cancelled`` to add it back.

Usage::

    python tools/dump_tasks.py
    python tools/dump_tasks.py --out docs/dev_tasks_all.md
    python tools/dump_tasks.py --statuses todo review --out docs/dev_tasks_todo_review.md
    python tools/dump_tasks.py --include-cancelled
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEV_TASKS = ROOT / "docs" / "virtualWorld" / "dev_tasks"

DEFAULT_STATUSES = ("todo", "inprogress", "review", "done")


def _read_text(path: Path) -> str:
    """Read a task file, tolerating the older non-UTF-8-encoded ones.

    Seven legacy bug/task files predate the vault's UTF-8 convention and carry
    bytes that are not valid UTF-8. They are not all the same encoding, so try
    a small set and fall back to replacing undecodable bytes rather than
    failing the whole dump.
    """
    raw = path.read_bytes()
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="dev_tasks.md",
                    help="output path (default: dev_tasks.md at repo root)")
    ap.add_argument("--statuses", nargs="+", default=list(DEFAULT_STATUSES),
                    help="statuses to include, in order")
    ap.add_argument("--include-cancelled", action="store_true",
                    help="also include the cancelled folder")
    args = ap.parse_args()

    statuses = list(args.statuses)
    if args.include_cancelled and "cancelled" not in statuses:
        statuses.append("cancelled")

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out

    parts: list[str] = []
    total = 0
    for status in statuses:
        folder = DEV_TASKS / status
        if not folder.is_dir():
            continue
        files = sorted(folder.rglob("*.md"))
        if not files:
            continue
        parts.append(f"# Status: {status}\n")
        for path in files:
            text = _read_text(path)
            rel = path.relative_to(ROOT).as_posix()
            parts.append(f"<!-- {rel} -->\n")
            parts.append(text.rstrip() + "\n")
            total += 1

    if not parts:
        print("no task files found")
        return 1

    header = (
        f"# Dev tasks dump\n\n"
        f"Generated from `docs/virtualWorld/dev_tasks/` statuses: "
        f"{', '.join(statuses)}.\n"
        f"Total task files: {total}\n\n"
    )
    out.write_text(header + "\n".join(parts), encoding="utf-8")
    print(f"wrote {out} ({total} task files, statuses: {', '.join(statuses)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())