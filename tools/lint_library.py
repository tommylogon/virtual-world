"""Library lint: scan data/library/ JSON files for data-quality problems.

Checks (errors exit 1):
  1. dead_interests   — character interest_tags matching zero item tags
  2. missing_slots    — items tagged clothing/armor without equip_slots
  3. tag_case_drift   — same tag in multiple casings within a registry
  5. broken_contents  — item contents referencing missing library ids
Warnings (exit 0):
  4. singleton_tags   — item tags appearing on exactly one item
  6. area_tag_gaps    — library areas with no tags

Usage:
  python tools/lint_library.py                  # all checks against default data dir
  python tools/lint_library.py --check dead_interests --check missing_slots
  python tools/lint_library.py --data-dir path/to/library   # for fixture testing

Exit code: 1 if any ERROR-level check fires, else 0.
"""

import argparse
import glob
import json
import os
import sys

DEFAULT_LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "library")

ERROR_CHECKS = ("dead_interests", "missing_slots", "tag_case_drift", "broken_contents")
WARNING_CHECKS = ("singleton_tags", "area_tag_gaps")
ALL_CHECKS = ERROR_CHECKS + WARNING_CHECKS


def load_registry(lib_dir, name):
    pattern = os.path.join(lib_dir, name, "*.json")
    entries = {}
    for path in sorted(glob.glob(pattern)):
        file_id = os.path.splitext(os.path.basename(path))[0]
        try:
            with open(path, "r", encoding="utf-8") as handle:
                entries[file_id] = json.load(handle)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            print(f"ERROR {name}/{file_id}: unparseable JSON ({exc})")
    return entries


def content_ref_id(ref):
    """Match routes/library_routes._content_ref_id: string or {id: ...}."""
    if isinstance(ref, str):
        return ref.strip() or None
    if isinstance(ref, dict):
        return ref.get("id") or None
    return None


def check_dead_interests(items, characters, report):
    """Character interest tags that match no item tag (case-insensitive)."""
    item_tag_vocab = set()
    for item in items.values():
        for tag in item.get("tags", []):
            item_tag_vocab.add(str(tag).strip().lower())

    for char_id, char in sorted(characters.items()):
        interests = char.get("interest_tags") or []
        dead = [t for t in interests if str(t).strip().lower() not in item_tag_vocab]
        if dead and interests:
            report.error("dead_interests",
                         f"characters/{char_id}: dead interest tags: {', '.join(dead)}")


def check_missing_slots(items, report):
    """Items tagged clothing/armor must declare equip_slots."""
    for item_id, item in sorted(items.items()):
        tags = {str(t).strip().lower() for t in item.get("tags", [])}
        if ("clothing" in tags or "armor" in tags) and not (item.get("equip_slots") or []):
            report.error("missing_slots", f"items/{item_id}: wearable but equip_slots empty")


def _case_drift(entries, get_tags, label, report):
    casing_map = {}
    for entry_id, entry in sorted(entries.items()):
        for tag in get_tags(entry):
            low = str(tag).strip().lower()
            if not low:
                continue
            casing_map.setdefault(low, {})
            casing_map[low].setdefault(str(tag), []).append(entry_id)
    for low, variants in sorted(casing_map.items()):
        if len(variants) > 1:
            detail = "; ".join(f"'{v}' on {label}/{', '.join(ids)}" for v, ids in sorted(variants.items()))
            report.error("tag_case_drift", f"{low}: mixed casing — {detail}")


def check_broken_contents(items, report):
    """Item contents referencing library item ids that do not exist."""
    known_ids = set(items.keys())
    # Library filenames may differ from the 'id' field; accept both.
    for entry_id, entry in sorted(items.items()):
        if isinstance(entry, dict) and entry.get("id"):
            known_ids.add(entry["id"])
    for item_id, item in sorted(items.items()):
        refs = item.get("contents") or []
        for ref in refs:
            child_id = content_ref_id(ref)
            if child_id and child_id not in known_ids:
                report.error("broken_contents",
                             f"items/{item_id}: contents references missing library item '{child_id}'")


def check_singleton_tags(items, report):
    """Item tags appearing on exactly one item — typo or under-connected."""
    counts = {}
    owner = {}
    for item_id, item in items.items():
        for tag in set(str(t).strip().lower() for t in item.get("tags", [])):
            if not tag:
                continue
            counts[tag] = counts.get(tag, 0) + 1
            owner.setdefault(tag, []).append(item_id)
    singles = [t for t in sorted(counts) if counts[t] == 1]
    if singles:
        detail = ", ".join(f"{t} (items/{owner[t][0]})" for t in singles)
        report.warn("singleton_tags", f"{len(singles)} single-use tags: {detail}")


def check_area_tag_gaps(areas, report):
    """Library areas carrying no tags at all (informational)."""
    untagged = [area_id for area_id, area in sorted(areas.items())
                if not (area.get("tags") or [])]
    if untagged:
        report.warn("area_tag_gaps",
                    f"{len(untagged)} areas have no tags: {', '.join(untagged)}")


CHECKS = {
    "dead_interests": lambda ctx, r: check_dead_interests(ctx["items"], ctx["characters"], r),
    "missing_slots": lambda ctx, r: check_missing_slots(ctx["items"], r),
    "tag_case_drift": lambda ctx, r: (
        _case_drift(ctx["items"], lambda e: e.get("tags", []), "items", r),
        _case_drift(ctx["areas"], lambda e: e.get("tags", []), "areas", r),
    ),
    "broken_contents": lambda ctx, r: check_broken_contents(ctx["items"], r),
    "singleton_tags": lambda ctx, r: check_singleton_tags(ctx["items"], r),
    "area_tag_gaps": lambda ctx, r: check_area_tag_gaps(ctx["areas"], r),
}


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, check, message):
        self.errors.append((check, message))
        print(f"[ERROR] ({check}) {message}")

    def warn(self, check, message):
        self.warnings.append((check, message))
        print(f"[WARN ] ({check}) {message}")


def main():
    parser = argparse.ArgumentParser(description="Lint the virtual world data library.")
    parser.add_argument("--data-dir", default=None,
                        help="library dir override (for fixture testing)")
    parser.add_argument("--check", action="append", choices=ALL_CHECKS, dest="checks",
                        help="run only these checks (repeatable); default: all")
    args = parser.parse_args()

    lib_dir = os.path.abspath(args.data_dir) if args.data_dir else os.path.abspath(DEFAULT_LIB_DIR)
    selected = tuple(args.checks) if args.checks else ALL_CHECKS

    ctx = {
        "items": load_registry(lib_dir, "items"),
        "characters": load_registry(lib_dir, "characters"),
        "areas": load_registry(lib_dir, "areas"),
    }
    print(f"linting {lib_dir} — items={len(ctx['items'])} "
          f"characters={len(ctx['characters'])} areas={len(ctx['areas'])}")

    report = Report()
    for check in selected:
        CHECKS[check](ctx, report)

    print(f"\n{len(report.errors)} errors, {len(report.warnings)} warnings")
    sys.exit(1 if report.errors else 0)


if __name__ == "__main__":
    main()
