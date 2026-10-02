#!/usr/bin/env python3
"""Backfill the wilderness item-affinity vocabulary (task-571).

No library item declared which biomes it belongs in, so a repo-wide grep of
`data/library/items/` for the compiled wilderness area tags (forest, woods,
dense, rocky, farmland, shore, ruin, ...) returned zero matches.  The tag-chain
population engine (`engine/population.py`) intersects an area's tags against an
item's, so every compiled wilderness cell planned empty.

The item schema now has an `affinity` field -- a list of area/biome tags -- and
`LibraryIndex` unions it with `tags`.  This script derives affinity for the
library's *raw natural resources* from the tags they already carry, so the
vocabulary is authored (reproducible and reviewable) rather than guessed at
runtime.

Deliberately excluded:

- furniture / building / settlement pieces -- they are placed by the furniture
  role, not scattered loose;
- prepared food (preserve / kitchen / meal / cooked / baked / brew / ...) -- an
  apple is not a forest even though a wild berry is. An explicit `forage` tag
  overrides this: the raw gatherables carry it.

Usage:
    python tools/backfill_item_affinity.py --check   # fail if any file would change
    python tools/backfill_item_affinity.py --apply   # write the affinity field
    python tools/backfill_item_affinity.py --report  # coverage by affinity
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ITEM_DIR = Path(__file__).resolve().parent.parent / "data" / "library" / "items"

#: tag -> area tags it implies. Ordered is irrelevant; affinities union.
TAG_AFFINITY = {
    "berry": ["forest", "woods"],
    "fruit": ["forest", "woods"],
    "herb": ["forest", "woods"],
    "medicinal": ["forest", "woods"],
    "plant": ["forest", "woods"],
    "forage": ["forest", "woods"],
    "mushroom": ["forest", "woods", "dense"],
    "fungus": ["forest", "woods", "dense"],
    "grub": ["forest", "woods", "dense"],
    "bait": ["forest", "woods", "dense"],
    "bug": ["forest", "woods", "dense"],
    "root": ["forest", "farmland"],
    "vegetable": ["farmland"],
    "grain": ["farmland"],
    "crop": ["farmland"],
    "seed": ["farmland"],
    "stone": ["rocky"],
    "ore": ["rocky"],
    "mineral": ["rocky"],
    "coal": ["rocky"],
    "fish": ["shore"],
    "shellfish": ["shore"],
    "seaweed": ["shore"],
    "scrap": ["ruin"],
    "junk": ["ruin"],
}

#: A tag here means the item is a worked/placed thing, not a loose resource.
EXCLUDE_TAGS = {"furniture", "building", "settlement", "structure", "container"}

#: Processed-food markers; a raw gatherable overrides them (see below).
PROCESSED_TAGS = {
    "preserve", "kitchen", "meal", "cooked", "baked", "brew", "jam", "stew",
    "soup", "pie", "cake", "bread", "roast", "cider", "cheese", "butter",
    "flour", "dried", "smoked", "pickled", "food", "drink",
}

#: Tags that mark an item as gatherable/harvested in the wild even though it is
#: also tagged `food`/`drink` (a raw fish is a shore resource; a fish pie is not).
RAW_OVERRIDE_TAGS = {"forage", "fish", "shellfish", "seaweed", "mushroom"}

#: Tags that make raw-material classification possible at all.
RESOURCE_TAGS = set(TAG_AFFINITY)


def _tags(entry: dict) -> set:
    tags = entry.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    return {str(t).strip().lower() for t in tags if str(t).strip()}


def derive_affinity(entry: dict) -> list:
    """The affinity this item's own tags imply, or [] when it is not a resource."""
    tags = _tags(entry)
    if tags & EXCLUDE_TAGS:
        return []
    if not (tags & RESOURCE_TAGS):
        return []
    if (tags & PROCESSED_TAGS) and not (tags & RAW_OVERRIDE_TAGS):
        return []
    out = []
    for tag, vocab in TAG_AFFINITY.items():
        if tag in tags:
            for a in vocab:
                if a not in out:
                    out.append(a)
    return out


def _expected(entry: dict) -> list:
    """Author-declared affinity wins; otherwise derive one from tags."""
    declared = entry.get("affinity") or []
    if isinstance(declared, str):
        declared = [t.strip() for t in declared.split(",") if t.strip()]
    if declared:
        return [str(a).strip().lower() for a in declared]
    return derive_affinity(entry)


def _with_affinity(entry: dict, affinity: list) -> dict:
    """Insert `affinity` directly after `tags`, preserving key order."""
    out = {}
    inserted = False
    for key, value in entry.items():
        if key == "affinity":
            continue
        out[key] = value
        if key == "tags":
            out["affinity"] = affinity
            inserted = True
    if not inserted:
        out["affinity"] = affinity
    return out


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _dump(entry: dict) -> str:
    return json.dumps(entry, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="fail if any file would change")
    ap.add_argument("--apply", action="store_true", help="write the affinity field")
    ap.add_argument("--report", action="store_true", help="show coverage by affinity")
    args = ap.parse_args()

    if not ITEM_DIR.is_dir():
        print(f"affinity backfill: item directory not found: {ITEM_DIR}")
        return 1
    item_paths = sorted(ITEM_DIR.glob("*.json"))
    if not item_paths:
        print(f"affinity backfill: no item files found under {ITEM_DIR}")
        return 1

    changes = []
    coverage = {}
    total_with = 0
    for path in item_paths:
        entry = _load(path)
        if not isinstance(entry, dict):
            continue
        expected = _expected(entry)
        if expected:
            total_with += 1
            for a in expected:
                coverage[a] = coverage.get(a, 0) + 1
        current = entry.get("affinity")
        current_norm = current if isinstance(current, list) else []
        if current_norm == expected:
            continue
        changes.append((path, expected))

    if args.report:
        print(f"{total_with} item(s) carry affinity.")
        for a, n in sorted(coverage.items()):
            print(f"  {a}: {n}")
        print(f"{len(changes)} file(s) would change.")
        return 0

    if args.apply:
        for path, expected in changes:
            entry = _load(path)
            path.write_text(_dump(_with_affinity(entry, expected)), encoding="utf-8")
        print(f"affinity backfill: wrote {len(changes)} file(s).")
        return 0

    if args.check:
        if changes:
            print(f"affinity backfill: {len(changes)} file(s) out of date:")
            for path, expected in changes[:20]:
                print(f"  {path.name}: {expected}")
            if len(changes) > 20:
                print(f"  ... and {len(changes) - 20} more")
            return 1
        print(f"affinity backfill OK: {total_with} item(s) carry affinity, no changes.")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
