#!/usr/bin/env python3
"""Guard the Feature Map: the canonical list of user-facing features, and the
front-end contract's `@powers` declarations checked against it.

A feature is a thing a person can do in a game or in the editor — deliberately
*not* a module. `attention.py` is a mechanism; nobody "uses attention". The three
earlier attempts to measure documentation coverage all failed for that reason:

* module filenames are mechanisms, so a per-module audit answers the wrong question;
* `@powers` is free-text prose (266 distinct strings across 156 modules), so there
  is nothing controlled to check a document against;
* note titles are 76 documents with no feature → note mapping.

So the denominator is declared once, in prose, in the map:
``docs/virtualWorld/Feature Map.md``. This tool reads it, checks every module's
``@powers`` against the features in it, and reports both directions — the modules
whose feature cannot be identified, and the features no module claims.

Usage:
    python tools/feature_index.py --check            # fail on a NEW unmapped module
    python tools/feature_index.py --update-baseline  # accept today's unmapped modules
    python tools/feature_index.py --report           # per-feature coverage table
    python tools/feature_index.py --write            # regenerate docs/design/feature-index.md

The baseline exists so today's prose that names no feature does not block the
guard; new modules are held to it from day one, exactly like ``js_module_index``.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path("static/js")
SKIP_DIRS = {"vendor", "node_modules"}
MAP_PATH = Path("docs/virtualWorld/Feature Map.md")
INDEX_PATH = Path("docs/design/feature-index.md")
BASELINE_PATH = Path("docs/design/feature-baseline.txt")

POWERS_RE = re.compile(r"^\s*\*?\s*@powers\s+(.*)$")
# a numbered row of either feature table: | 12 | Search / forage | ... | wired | [[none]] |
ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|(.+)$")

# Words that carry no identity, so a feature key is only its distinctive terms.
STOPWORDS = {
    "and", "or", "the", "a", "an", "of", "to", "in", "on", "for", "with", "by",
    "at", "from", "as", "is", "are", "you", "your", "it", "its", "can", "do",
    "does", "what", "them", "they", "their", "then", "than", "that", "this",
    "see", "using", "use", "used", "via", "per", "into", "out", "up", "down",
}

# The map writes a few of its features in prose rather than as a table row
# ("Search / forage" is a row, but "Recent edits / undo" carries a slash too).
# Slashes and ampersands are separators, not identity: "Open / close" -> {open, close}.
def _terms(label: str) -> list[str]:
    cleaned = re.sub(r"[*_`]", "", label)
    parts = re.split(r"[/&]| - |,|\band\b", cleaned.lower())
    return [p.strip() for p in parts if p.strip() and p.strip() not in STOPWORDS]


def parse_features() -> list[dict]:
    """Read the feature list out of the map. The map is the only declaration."""
    if not MAP_PATH.exists():
        sys.stderr.write(f"{MAP_PATH} missing — the feature list is the denominator.\n")
        raise SystemExit(2)
    features = []
    section = ""
    for line in MAP_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        m = ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        if len(cells) < 4:
            continue
        label = cells[0].replace("**", "").strip()
        terms = _terms(label)
        if not terms:
            continue
        features.append({
            "n": int(m.group(1)),
            "label": label,
            "section": section,
            "what": cells[1],
            "status": cells[2],
            "docs": cells[3],
            "terms": terms,
        })
    return features


def collect_powers() -> list[tuple[str, str]]:
    out = []
    for path in sorted(ROOT.rglob("*.js")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines()[:60]:
            m = POWERS_RE.match(line)
            if m:
                out.append((str(path).replace("\\", "/"), m.group(1).strip()))
                break
    return out


def match(powers: str, features: list[dict]) -> list[str]:
    """Which features does this @powers text name?

    A term matches by word-prefix, so "Move" claims a module that says
    "movement" and "Examine" claims "examining" — the headers are written as
    gerund phrases and the map as noun phrases, and demanding an exact word match
    would report almost every module as unmapped for a spelling difference.

    Any one term is enough. A feature's terms are its distinctive words, so
    "Take / drop / give" is claimed by a module that says "take", and a term
    under four characters is ignored because it cannot be distinctive.
    """
    text = re.sub(r"[*_`]", "", powers.lower())
    words = set(re.findall(r"[a-z]+", text))
    hits = []
    for feat in features:
        for term in feat["terms"]:
            if len(term) < 4:
                continue
            if any(w.startswith(term) for w in words):
                hits.append(feat["label"])
                break
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail on a NEW unmapped module")
    parser.add_argument("--update-baseline", action="store_true", help="record the unmapped list")
    parser.add_argument("--report", action="store_true", help="per-feature coverage table")
    parser.add_argument("--write", action="store_true", help="regenerate the feature index")
    args = parser.parse_args()

    features = parse_features()
    modules = collect_powers()
    mapped = {path: match(powers, features) for path, powers in modules}
    unmapped = [p for p, _ in modules if not mapped[p]]

    print(f"features read from {MAP_PATH}: {len(features)}")
    print(f"modules declaring @powers:     {len(modules)}")
    print(f"  naming at least one feature: {len(modules) - len(unmapped)}")
    print(f"  naming none:                 {len(unmapped)}")

    if args.update_baseline:
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text("\n".join(unmapped) + "\n", encoding="utf-8")
        print(f"{BASELINE_PATH}: recorded {len(unmapped)} unmapped module(s).")

    if args.report:
        claimed = {}
        for path, hits in mapped.items():
            for h in hits:
                claimed.setdefault(h, []).append(path)
        print()
        print("%-42s %5s  %s" % ("FEATURE", "MODS", "NOTE"))
        print("-" * 96)
        for feat in features:
            mods = claimed.get(feat["label"], [])
            docs = feat["docs"].replace("**", "")
            print("%-42s %5d  %s" % (feat["label"][:42], len(mods), docs[:44]))
        orphans = [f["label"] for f in features if f["label"] not in claimed]
        print()
        print("features no module names: %d" % len(orphans))
        for o in orphans:
            print("  -", o)
        print()
        print("modules whose feature could not be identified: %d" % len(unmapped))
        for u in unmapped:
            print("  -", u)

    if args.write or not (args.check or args.update_baseline or args.report):
        claimed = {}
        for path, hits in mapped.items():
            for h in hits:
                claimed.setdefault(h, []).append(path)
        lines = [
            "# Feature index",
            "",
            "Generated by `tools/feature_index.py` — do not hand-edit.",
            "The features are declared in prose in `docs/virtualWorld/Feature Map.md`;",
            "this file is the generated join between those features and the front-end",
            "modules that claim them via `@powers`.",
            "",
            f"- Features: **{len(features)}**",
            f"- Modules scanned: **{len(modules)}**",
            f"- Modules naming a feature: **{len(modules) - len(unmapped)}**",
            f"- Modules naming none: **{len(unmapped)}**",
            "",
            "| # | Feature | Section | Status | Note | Modules claiming it |",
            "|---|---|---|---|---|---|",
        ]
        for feat in features:
            mods = claimed.get(feat["label"], [])
            listing = ", ".join("`%s`" % m for m in sorted(mods)[:4])
            if len(mods) > 4:
                listing += " (+%d more)" % (len(mods) - 4)
            lines.append(
                f"| {feat['n']} | {feat['label']} | {feat['section']} | {feat['status']} | "
                f"{feat['docs']} | {listing or '—'} |"
            )
        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        INDEX_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n{INDEX_PATH}: {len(features)} features, {len(modules)} modules.")

    if args.check:
        if not BASELINE_PATH.exists():
            print(f"{BASELINE_PATH} missing — run --update-baseline once.")
            return 2
        known = set(BASELINE_PATH.read_text(encoding="utf-8").split())
        new_unmapped = [u for u in unmapped if u not in known]
        if new_unmapped:
            print("New modules whose @powers names no feature in the Feature Map:")
            for u in new_unmapped:
                print("  -", u)
            return 1
        print(f"Feature check OK ({len(unmapped)} known-unmapped, no new).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
