#!/usr/bin/env python3
"""Deterministic emitter for library item templates from a compact spec (task-513).

Hand-authoring a gear matrix as JSON invites drift: the same hunting bow in three
spellings, three tag lists, a wearable with no equip_slots. A spec table is
small, reviewable and re-runnable, matching the folder-authoring precedent
(`tools/compile_scenario.py`, `tools/build_scenario.py`).

The spec is keyed by item id and carries a `category`
(clothing / armor / weapon / tool / accessory / material). The category supplies
the defaults every item of that kind must have (actions, base tags, a default
equip slot, weapon damage), and the entry overrides them. Emission is
deterministic: sorted ids, a fixed field order, two-space JSON, one trailing
newline -- so re-running is byte-identical.

Usage:
    python tools/gen_library_items.py --spec <file> --check   # fail if drifted
    python tools/gen_library_items.py --spec <file> --apply   # write templates
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ITEM_DIR = Path(__file__).resolve().parent.parent / "data" / "library" / "items"

#: Stamped into every emitted template. `--apply` refuses to overwrite a file
#: that does not carry it (unless --force), so a spec id can never silently
#: clobber a hand-authored entry and drop the fields the spec does not model.
GENERATED_BY = "gen_library_items"

VALID_SLOTS = {
    "head", "neck", "torso", "arms", "hands", "legs", "feet", "back", "waist",
    "accessory", "hand_left", "hand_right",
}
VALID_DAMAGE_TYPES = {
    "slashing", "piercing", "bludgeoning", "fire", "cold", "lightning",
    "acid", "poison", "necrotic", "radiant", "force", "psychic",
}

#: category -> the fields every item of that kind must have.
CATEGORY_DEFAULTS = {
    "clothing": {"actions": "examine,take,equip,unequip", "tags": ["clothing"],
                 "equip_slots": ["torso"]},
    "armor": {"actions": "examine,take,equip,unequip", "tags": ["armor"],
              "equip_slots": ["torso"], "defense": 1},
    "weapon": {"actions": "examine,take,equip,unequip", "tags": ["weapon"],
               "equip_slots": ["hand_right"], "damage": 1,
               "damage_type": "bludgeoning"},
    "tool": {"actions": "examine,take,use", "tags": ["tool"]},
    "accessory": {"actions": "examine,take,equip,unequip", "tags": ["accessory"],
                  "equip_slots": ["accessory"]},
    "material": {"actions": "examine,take", "tags": ["material"]},
}

FIELD_ORDER = [
    "name", "description", "actions", "uses", "weight", "equip_slots",
    "current_state", "light_level", "defense", "damage", "damage_type",
    "insulation", "concealed", "tags", "affinity", "provenance", "triggers",
    "contents",
]


def build_item(item_id: str, entry: dict) -> dict:
    """Return the emitted template for one spec entry, or raise ValueError."""
    category = entry.get("category")
    if category not in CATEGORY_DEFAULTS:
        raise ValueError(f"{item_id}: unknown category {category!r}")
    item = json.loads(json.dumps(CATEGORY_DEFAULTS[category]))  # deep copy
    for key, value in entry.items():
        if key == "category":
            continue
        item[key] = value

    item.setdefault("uses", -1)
    item.setdefault("weight", 0.1)
    item.setdefault("current_state", "normal")
    item.setdefault("light_level", "dim")
    item.setdefault("triggers", [])
    item.setdefault("contents", [])

    if not item.get("name"):
        raise ValueError(f"{item_id}: has no name")
    if not item.get("description"):
        raise ValueError(f"{item_id}: has no description")

    slots = item.get("equip_slots") or []
    if category in ("clothing", "armor") and not slots:
        raise ValueError(f"{item_id}: {category} needs equip_slots")
    bad_slots = sorted(set(slots) - VALID_SLOTS)
    if bad_slots:
        raise ValueError(f"{item_id}: invalid equip_slots {bad_slots}")

    tags = item.get("tags") or []
    if any(str(t) != str(t).strip().lower() for t in tags):
        raise ValueError(f"{item_id}: tags must be lowercase and trimmed")

    if category == "weapon":
        if not item.get("damage"):
            raise ValueError(f"{item_id}: weapon needs damage")
        if item.get("damage_type") not in VALID_DAMAGE_TYPES:
            raise ValueError(f"{item_id}: invalid damage_type {item.get('damage_type')!r}")

    out = {key: item[key] for key in FIELD_ORDER if key in item}
    # Any field the spec added that is not in the canonical order is a mistake.
    extra = sorted(set(item) - set(FIELD_ORDER))
    if extra:
        raise ValueError(f"{item_id}: unknown field(s) {extra}")
    out["_generated_by"] = GENERATED_BY
    return out


def emit(spec: dict) -> dict:
    entries = spec.get("items") or {}
    if not entries:
        raise ValueError("spec has no items")
    out = {}
    for item_id in sorted(entries):
        out[item_id] = build_item(item_id, entries[item_id])
    return out


def _dump(item: dict) -> str:
    return json.dumps(item, indent=2, ensure_ascii=False) + "\n"


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _is_generated(entry) -> bool:
    return isinstance(entry, dict) and entry.get("_generated_by") == GENERATED_BY


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", required=True, help="path to the gear spec JSON")
    ap.add_argument("--check", action="store_true", help="fail if any emitted file differs")
    ap.add_argument("--apply", action="store_true", help="write the templates")
    ap.add_argument("--force", action="store_true",
                    help="overwrite a file that is not owned by this generator")
    args = ap.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8-sig"))
    try:
        items = emit(spec)
    except ValueError as exc:
        print(f"spec error: {exc}")
        return 2

    drift = []
    for item_id, item in items.items():
        path = ITEM_DIR / f"{item_id}.json"
        want = _dump(item)
        have = path.read_text(encoding="utf-8") if path.exists() else None
        if have != want:
            drift.append((path, want))

    if args.apply:
        foreign = [path for path, _ in drift
                   if path.exists() and not _is_generated(_load_json(path))]
        if foreign and not args.force:
            print("gen_library_items: refusing to overwrite file(s) not owned by "
                  "this generator (pass --force to override):")
            for path in foreign[:20]:
                print(f"  {path.name}")
            if len(foreign) > 20:
                print(f"  ... and {len(foreign) - 20} more")
            return 1
        for path, want in drift:
            path.write_text(want, encoding="utf-8")
        print(f"gen_library_items: wrote {len(drift)} of {len(items)} template(s).")
        return 0

    if args.check:
        if not ITEM_DIR.is_dir():
            print(f"gen_library_items: item directory not found: {ITEM_DIR}")
            return 1
        if drift:
            print(f"gen_library_items: {len(drift)} template(s) out of date:")
            for path, _ in drift[:20]:
                print(f"  {path.name}")
            if len(drift) > 20:
                print(f"  ... and {len(drift) - 20} more")
            return 1
        print(f"gen_library_items OK: {len(items)} template(s) match the spec.")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
