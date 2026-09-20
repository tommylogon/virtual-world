#!/usr/bin/env python3
"""Repair (and guard against) mojibake in the docs vault.

Symptom: text that was UTF-8 got read as cp1252 and re-saved as UTF-8, turning
em dashes / en dashes / ellipses into three-character sequences. These are the
only three sequences currently present under ``docs/virtualWorld`` (detected by
scanning codepoints, not by eye).

Usage:
    python tools/fix_docs_mojibake.py --check      # exit 1 if any are found
    python tools/fix_docs_mojibake.py --fix        # rewrite the affected files
    python tools/fix_docs_mojibake.py --check --path docs
"""
from __future__ import annotations

import argparse
from pathlib import Path

# mojibake sequence -> correct character
REPLACEMENTS = {
    "\u00e2\u20ac\u201d": "\u2014",   # a-EUR-rdquo (0x94) -> em dash
    "\u00e2\u20ac\u201c": "\u2013",   # a-EUR-ldquo (0x93) -> en dash
    "\u00e2\u20ac\u00a6": "\u2026",   # a-EUR-brokenbar (0xA6) -> ellipsis
}

# Any occurrence of this 2-character prefix is mojibake, mapped or not — used so
# an unknown variant can never be reported as "clean".
MOJIBAKE_MARK = "\u00e2\u20ac"

DEFAULT_ROOT = "docs/virtualWorld"


def _scan(root: Path):
    """Yield (path, text, hits) for every .md under *root* containing mojibake."""
    for path in sorted(root.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        hits = text.count(MOJIBAKE_MARK)
        if hits:
            yield path, text, hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", default=DEFAULT_ROOT, help="docs root to scan")
    parser.add_argument("--check", action="store_true", help="report only (exit 1 on findings)")
    parser.add_argument("--fix", action="store_true", help="rewrite affected files")
    args = parser.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f"{root}: not found")
        return 2

    found = list(_scan(root))
    total = sum(hits for _, _, hits in found)

    if not found:
        print(f"{root}: clean — no mojibake sequences found.")
        return 0

    for path, _, hits in found:
        print(f"  {hits:>4}  {path}")

    if args.fix:
        leftovers = []
        for path, text, _ in found:
            for bad, good in REPLACEMENTS.items():
                text = text.replace(bad, good)
            path.write_text(text, encoding="utf-8")
            if MOJIBAKE_MARK in text:
                leftovers.append(str(path))
        print(f"\nRepaired {len(found)} file(s), {total} sequence(s).")
        if leftovers:
            print("Still holding an UNMAPPED variant — extend REPLACEMENTS:")
            for path in leftovers:
                print("  ", path)
            return 1
        return 0

    print(f"\n{len(found)} file(s), {total} sequence(s). Run with --fix to repair.")
    return 1 if args.check else 0


if __name__ == "__main__":
    raise SystemExit(main())
