"""feature_pages.py — one page per Feature Map row, and a guard that keeps it true.

The Feature Map is the denominator: what a person can actually *do*. A row that
points at nothing is a coverage gap the map cannot show, and a page that nothing
links to is an island the graph hides. This tool makes "every feature has a page"
mechanically checkable and scaffolds the missing ones.

It **never overwrites prose**: `--scaffold` only creates a page that does not
exist yet. `--check` fails on a row without a page, a page without its required
sections, a page with no row behind it, or a page whose ``feature_id`` drifted
from the row it claims to document.

    python tools/feature_pages.py --scaffold   # create missing pages (never overwrites)
    python tools/feature_pages.py --report# row -> page -> section coverage
    python tools/feature_pages.py --check      # fail on any gap (exit 1)

The Feature Map row stays the source of truth for the label, the "what you can
do" sentence and the status; the page is the per-feature entry point that links
to the deep documentation. The row's own ``Docs`` cell keeps pointing at the deep
note (that is what "documented" means there), except for rows that had ``none`` —
those point at their new page.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from feature_index import parse_features  # noqa: E402  — one parser for one map
from doc_links import target_key  # noqa: E402  — one wikilink resolver

VAULT = ROOT / "docs" / "virtualWorld"
FEATURES_DIR = VAULT / "Features"

#: The sections a feature page must carry. `--check` fails without them, so a
#: page cannot rot into a bare stub.
REQUIRED_SECTIONS = ("## How it works", "## Where it lives", "## Connected")

#: Status word the Feature Map uses -> the tag namespace that mirrors it.
STATUS_WORDS = ("wired", "authored", "planned", "unwired")

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slug(label: str) -> str:
    """Filesystem-safe, link-stable id for a feature label.

    ``Take / drop / give`` -> ``take-drop-give``. Slugs are the page basenames,
    so they must be unique across the vault or Obsidian cannot resolve a bare
    ``[[slug]]`` — `--check` enforces that.
    """
    cleaned = re.sub(r"[*_`]", "", label)
    return _SLUG_RE.sub("-", cleaned.lower()).strip("-")


def status_word(status: str) -> str:
    """The status token of a Status cell (``**unwired** — because…`` -> ``unwired``)."""
    cleaned = re.sub(r"[*_`]", "", str(status or "")).strip().lower()
    for word in STATUS_WORDS:
        if cleaned.startswith(word):
            return word
    return "wired" if cleaned else "planned"


def docs_links(docs_cell: str) -> list[str]:
    """The wikilink targets in a Docs cell (``none`` yields nothing).

    Normalised through ``doc_links.target_key`` rather than a second regex: the
    escaped-pipe form ``[[Memory System\\|Memory]]`` used to come back as
    ``"Memory System\\"``, which silently mis-stemmed the join in
    ``doc_connected.features_by_doc`` and cost that note a whole inbound
    relation. One resolver, one answer.
    """
    if not docs_cell or docs_cell.strip().lower() == "none":
        return []
    out = []
    for raw in re.findall(r"\[\[([^\[\]]+?)\]\]", docs_cell):
        key = target_key(raw)
        if key and key not in out:
            out.append(key)
    return out


def page_path(label: str) -> Path:
    return FEATURES_DIR / f"{slug(label)}.md"


def section_key(section: str) -> str:
    return "in-game" if "game" in section.lower() else "in-editor"


def render_page(feature: dict, siblings: list[dict], today: str) -> str:
    """The scaffold for one feature page: thin, true, and link-rich.

    Deliberately *thin but true* rather than TODO-marked: every sentence in a
    fresh page is one the Feature Map already asserts. Enriching a page with real
    mechanics is the follow-up work, and `--report` shows which pages are still
    one line deep.
    """
    label = feature["label"]
    status = status_word(feature["status"])
    deep = docs_links(feature["docs"])
    deep_lines = "\n".join(f"- [[{t}]]" for t in deep) or \
        "- _No deep note linked from the row yet — this page is the only one._"
    sibling_links = ", ".join(f"[[{slug(s['label'])}]]" for s in siblings) or "none yet"
    return f"""---
type: feature
feature_id: {feature['n']}
status: {status}
section: {section_key(feature['section'])}
---
# {label}

**What you can do:** {feature['what']}

## How it works

{deep_lines}

## Where it lives

_Not recorded yet — add the code paths when you next touch this feature._

## Connected

- Feature Map: [[Feature Map|row {feature['n']}]] ({feature['section']})
- Sibling features: {sibling_links}
- All features: [[Features Overview]]

> [!note] Status — `{status}`
> Recorded from [[Feature Map|the Feature Map]] on {today}. This page is an entry point; the
> deep documentation is linked under **How it works**.
"""


def scaffold(today: str = "2026-10-05") -> int:
    """Create the pages that do not exist. Never touches an existing page."""
    features = parse_features()
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    created = 0
    for feature in features:
        target = page_path(feature["label"])
        if target.exists():
            continue
        siblings = [f for f in features
                    if f["section"] == feature["section"] and f["n"] != feature["n"]][:6]
        target.write_text(render_page(feature, siblings, today), encoding="utf-8")
        created += 1
    return created


def audit() -> tuple[list[str], list[str], int]:
    """Return (problems, rows, page_count). A problem is one line, human-readable."""
    features = parse_features()
    problems: list[str] = []
    seen_slugs: dict[str, int] = {}

    for feature in features:
        s = slug(feature["label"])
        if s in seen_slugs:
            problems.append(
                f"slug collision: rows {seen_slugs[s]} and {feature['n']} both slug to '{s}'")
        else:
            seen_slugs[s] = feature["n"]
        target = page_path(feature["label"])
        if not target.exists():
            problems.append(f"row {feature['n']} ({feature['label']}): no page at "
                            f"Features/{target.name}")
            continue
        text = target.read_text(encoding="utf-8")
        body = text.split("---", 2)[-1] if text.startswith("---") else text
        for section in REQUIRED_SECTIONS:
            if section not in body:
                problems.append(f"{target.name}: missing section '{section}'")
        if f"feature_id: {feature['n']}" not in text:
            problems.append(f"{target.name}: feature_id does not match row {feature['n']}")

    for existing in sorted(FEATURES_DIR.glob("*.md")) if FEATURES_DIR.exists() else []:
        if existing.name == "Features Overview.md":
            continue
        if existing.stem not in seen_slugs:
            problems.append(f"{existing.name}: page with no Feature Map row behind it")

    # The MOC is the folder's front door: it must exist and list every feature,
    # or the folder becomes 76 unlinked islands.
    overview = FEATURES_DIR / "Features Overview.md"
    if not overview.exists():
        problems.append("Features/Features Overview.md is missing (the folder's front door)")
    else:
        text = overview.read_text(encoding="utf-8")
        for feature in features:
            s = slug(feature["label"])
            if s not in text:
                problems.append(f"Features Overview.md does not list '{feature['label']}'")

    return problems, features, len(seen_slugs)


def report() -> None:
    features = parse_features()
    print(f"{'row':>4}  {'status':<9} {'section':<10} {'page':<34} deep docs")
    print("-" * 96)
    missing = 0
    for feature in features:
        target = page_path(feature["label"])
        exists = target.exists()
        missing += 0 if exists else 1
        deep = ", ".join(docs_links(feature["docs"])) or "—"
        print(f"{feature['n']:>4}  {status_word(feature['status']):<9} "
              f"{section_key(feature['section']):<10} "
              f"{('Features/' + target.name) if exists else 'MISSING':<34} {deep}")
    print("-" * 96)
    print(f"{len(features)} rows · {len(features) - missing} with a page · {missing} missing")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scaffold", action="store_true",
                        help="create pages for rows that have none (never overwrites)")
    parser.add_argument("--report", action="store_true",
                        help="print the row -> page -> deep-doc table")
    parser.add_argument("--check", action="store_true",
                        help="fail on a row without a page, a malformed page, or an orphan page")
    args = parser.parse_args()

    if args.scaffold:
        created = scaffold()
        print(f"scaffolded {created} feature page(s) into {FEATURES_DIR}")
        return 0

    if args.report:
        report()
        return 0

    problems, features, pages = audit()
    if problems:
        sys.stderr.write(f"{len(problems)} feature-page problem(s):\n")
        for line in problems:
            sys.stderr.write(f"  - {line}\n")
        return 1
    print(f"Feature pages OK ({pages} pages for {len(features)} rows).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())