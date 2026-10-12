#!/usr/bin/env python3
"""Guard the Feature Ledger: the canonical list of user-facing features, and the
front-end contract's `@docs` declarations checked against it.

A **feature** is something a person does, uses or interacts with — a system or a
surface, in a game or in the editor — deliberately *not* a module. A **mechanic**
is how it works: the operations and rules inside a feature (`attention.py` is a
mechanic, not a feature — nobody "uses attention"). The three earlier attempts to
measure documentation coverage all failed for that reason:

* module filenames are mechanics, so a per-module audit answers the wrong question;
* `@powers` is free-text prose (266 distinct strings across 156 modules), so there
  is nothing controlled to check a document against;
* note titles are 76 documents with no feature → note mapping.

So the denominator is declared once, in prose, in the ledger:
``docs/virtualWorld/Feature Ledger.md`` (the guide a reader sees is
``docs/virtualWorld/Feature Map.md``). This tool reads the ledger, checks every
module's ``@docs`` against the features in it, and reports both directions — the
modules whose feature cannot be identified, and the features no module claims.

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
#: The vault, for resolving a Docs cell to a file. ``ROOT`` is the module glob
#: root (the front end), not the repo root, so note resolution needs its own.
VAULT = Path("docs/virtualWorld")
LEDGER_PATH = Path("docs/virtualWorld/Feature Ledger.md")
INDEX_PATH = Path("docs/design/feature-index.md")
BASELINE_PATH = Path("docs/design/feature-baseline.txt")

POWERS_RE = re.compile(r"^\s*\*?\s*@powers\s+(.*)$")
DOCS_RE = re.compile(r"^\s*\*?\s*@docs\s+(.*)$")
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


def split_cells(row: str) -> list[str]:
    """Split a markdown table row on **unescaped** pipes only.

    A `[[Note|alias]]` inside a cell is legal markdown only as `[[Note\\|alias]]`,
    but writing the bare pipe truncates the cell silently rather than loudly:
    row 23's Docs cell parsed as ``[[Environment/Temperature System`` and the
    note it names lost its inbound relation with no error anywhere. Splitting on
    pipes that are not preceded by a backslash is what makes the alias survive.
    """
    parts = re.split(r"(?<!\\)\|", row)
    return [p.replace("\\|", "|").strip() for p in parts]


def parse_features() -> list[dict]:
    """Read the feature list out of the map. The map is the only declaration."""
    if not LEDGER_PATH.exists():
        sys.stderr.write(f"{LEDGER_PATH} missing — the feature list is the denominator.\n")
        raise SystemExit(2)
    features = []
    section = ""
    for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        m = ROW_RE.match(line)
        if not m:
            continue
        cells = split_cells(m.group(2))
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


def collect_headers() -> list[tuple[str, str, str]]:
    """(module path, ``@powers`` prose, ``@docs`` target) for every module.

    ``@powers`` is free-text prose. It is kept because a human reading the
    header benefits from it, and it is **never** used as a join key — matching
    266 distinct prose strings against feature names is a word game, not a
    check. ``@docs`` is the machine-readable edge: a real path to a vault note,
    or ``none``.
    """
    out = []
    for path in sorted(ROOT.rglob("*.js")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        powers, docs = "", ""
        for line in text.splitlines()[:60]:
            if not powers:
                m = POWERS_RE.match(line)
                if m:
                    powers = m.group(1).strip()
            if not docs:
                m = DOCS_RE.match(line)
                if m:
                    docs = m.group(1).strip()
            if powers and docs:
                break
        out.append((str(path).replace("\\", "/"), powers, docs))
    return out


def vault_key(target: str) -> str:
    """Normalise a note reference to a lowercase, extension-free key.

    ``docs/virtualWorld/World Building/Movement.md`` and
    ``[[World Building/Movement|Movement]]`` both become
    ``world building/movement``, so a module's ``@docs`` and a ledger row's
    Docs cell join on the same string.
    """
    s = target.strip()
    s = re.sub(r"^\[\[|\]\]$", "", s)
    s = s.split("|")[0].strip()
    s = re.sub(r"\.md$", "", s)
    s = re.sub(r"^docs/virtualWorld/", "", s)
    return s.strip().lower()


def resolve_note(key: str):
    """The vault file a key names, or None.

    Tries the vault-relative path first, then falls back to a basename search,
    because Obsidian resolves ``[[Rooms & Areas]]`` from any folder and the
    ledger writes bare basenames.
    """
    if not key or key == "none":
        return None
    direct = VAULT / (key + ".md")
    if direct.exists():
        return direct
    base = key.rsplit("/", 1)[-1] + ".md"
    for hit in VAULT.rglob(base):
        return hit
    return None


def ledger_notes(docs_cell: str) -> list[str]:
    """The vault keys a ledger row's Docs cell names (empty for ``none``)."""
    out = []
    for link in re.findall(r"\[\[([^\]]+)\]\]", docs_cell):
        key = vault_key(link)
        if key and key != "none":
            out.append(key)
    return out


def join_features(features, headers) -> dict:
    """feature label -> [module paths], built from each module's ``@docs``.

    A module claims a feature when its ``@docs`` target resolves to the same
    vault file the ledger row points at. Both sides are resolved through
    ``resolve_note`` because they are written differently — a module writes the
    full path (``Characters/Memory System.md``) and a ledger cell writes the
    bare basename (``[[Memory System]]``) — and Obsidian resolves both to the
    same note. That is a real, checkable edge; the old free-text ``@powers``
    word match was not.
    """
    by_note = {}
    for feat in features:
        for key in ledger_notes(feat["docs"]):
            note = resolve_note(key)
            if note is None:
                continue
            by_note.setdefault(str(note).replace("\\", "/").lower(), []).append(
                feat["label"])
    claimed = {}
    for path, _powers, docs in headers:
        note = resolve_note(vault_key(docs))
        if note is None:
            continue
        for label in by_note.get(str(note).replace("\\", "/").lower(), []):
            claimed.setdefault(label, []).append(path)
    return claimed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail on a NEW unmapped module")
    parser.add_argument("--update-baseline", action="store_true", help="record the unmapped list")
    parser.add_argument("--report", action="store_true", help="per-feature coverage table")
    parser.add_argument("--write", action="store_true", help="regenerate the feature index")
    args = parser.parse_args()

    features = parse_features()
    headers = collect_headers()
    claimed = join_features(features, headers)
    modules = [p for p, _pw, _d in headers]
    docs_none = [p for p, _pw, d in headers if vault_key(d) in ("", "none")]
    with_powers = [p for p, pw, _d in headers if pw]

    print(f"features read from {LEDGER_PATH}: {len(features)}")
    print(f"modules scanned:            {len(modules)}")
    print(f"  with an @docs target:     {len(modules) - len(docs_none)}")
    print(f"  @docs none:               {len(docs_none)}")
    print(f"  carrying @powers prose:   {len(with_powers)}  (informational only)")

    if args.update_baseline:
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text("\n".join(docs_none) + "\n", encoding="utf-8")
        print(f"{BASELINE_PATH}: recorded {len(docs_none)} module(s) with @docs none.")

    if args.report:
        print()
        print("%-42s %5s  %s" % ("FEATURE", "MODS", "NOTE"))
        print("-" * 96)
        for feat in features:
            mods = claimed.get(feat["label"], [])
            docs = feat["docs"].replace("**", "")
            print("%-42s %5d  %s" % (feat["label"][:42], len(mods), docs[:44]))
        orphans = [f["label"] for f in features if f["label"] not in claimed]
        print()
        print("features no module points at: %d" % len(orphans))
        for o in orphans:
            print("  -", o)
        print()
        print("modules whose @docs names no feature note: %d" % len(docs_none))
        for u in docs_none:
            print("  -", u)

    if args.write or not (args.check or args.update_baseline or args.report):
        lines = [
            "# Feature index",
            "",
            "Generated by `tools/feature_index.py` — do not hand-edit.",
            "The features are declared in prose in `docs/virtualWorld/Feature Ledger.md`;",
            "this file is the generated join between those features and the front-end",
            "modules whose `@docs` header points at the note that documents them.",
            "",
            f"- Features: **{len(features)}**",
            f"- Modules scanned: **{len(modules)}**",
            f"- Modules with an @docs target: **{len(modules) - len(docs_none)}**",
            f"- Modules with @docs none: **{len(docs_none)}**",
            "",
            "| # | Feature | Section | Status | Note | Modules pointing at it |",
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
        # The gate is now real: every feature's Docs note must resolve to a file
        # in the vault. No prose matching, no baseline of "unmapped" modules —
        # a module with `@docs none` is a legitimate state (pure infrastructure),
        # not a failure.
        missing = []
        for feat in features:
            for key in ledger_notes(feat["docs"]):
                if resolve_note(key) is None:
                    missing.append((feat["label"], key))
        if missing:
            print("Feature rows whose Docs note does not resolve:", file=sys.stderr)
            for label, key in missing:
                print(f"  - {label} -> {key}", file=sys.stderr)
            return 1
        print(f"Feature check OK ({len(features)} rows, every Docs note resolves).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
