#!/usr/bin/env python3
"""tag_domains.py — domain/role tag pass for the population chain (task-324).

Adds the shared domain tags that let task-9 walk
area domains -> role-tagged furniture -> domain items.

Dry-run by default; pass --apply to write. Idempotent: re-running only adds
missing tags, never removes existing ones.

Usage:
    python tools/tag_domains.py            # report what would change
    python tools/tag_domains.py --apply    # write changes
    python tools/tag_domains.py --apply --domains goblin   # limit scope
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "data" / "library"


def tag_file_def(tag):
    """Metadata for a new tag file. Category 'domain' = what a place is FOR."""
    name = tag.replace("_", " ").title()
    return {
        "id": tag,
        "name": name,
        "description": f"Domain tag used by the population chain: {name.lower()}.",
        "category": "domain",
        "contexts": ["placement", "generic", "dungeon"],
        "implies": [],
        "applies_to": ["area", "item"],
        "color": "#4ec9b0",
        "icon": "\U0001F3F7\uFE0F",
        "examples": [],
    }


# Domain/role tags this pass needs. Missing ones get a tag file created.
NEEDED_TAGS = [
    "display", "furniture", "container", "storage", "food", "medical",
    "animal", "water", "occult", "social",
    "cooking", "sleeping", "workshop", "shrine", "scouting", "mining",
    "waste", "prison", "nursery", "training", "goblin_camp", "entrance",
    "armory", "guard",
]

# ── Area domain table (library area id -> tags to ADD, existing kept) ──
AREA_DOMAINS = {
    "camp_entrance": ["goblin_camp", "entrance", "guard"],
    "camp_entrance_trail": ["goblin_camp", "entrance"],
    "chief_s_pit": ["goblin_camp", "social", "cooking"],
    "chief_s_den": ["goblin_camp", "social", "storage"],
    "sleeping_halls": ["goblin_camp", "sleeping"],
    "goblin_nursery": ["goblin_camp", "nursery"],
    "nursery": ["goblin_camp", "nursery"],
    "cooking_area": ["goblin_camp", "cooking", "food"],
    "food_storage": ["goblin_camp", "storage", "food"],
    "workshop": ["goblin_camp", "workshop"],
    "scrap_pile": ["goblin_camp", "workshop", "storage"],
    "training_pit": ["goblin_camp", "training", "armory"],
    "prison_pens": ["goblin_camp", "prison"],
    "shaman_lair": ["goblin_camp", "shrine", "occult"],
    "healing_area": ["goblin_camp", "medical"],
    "scouting_rooms": ["goblin_camp", "scouting"],
    "mine_access": ["goblin_camp", "mining"],
    "storage_caves": ["goblin_camp", "storage"],
    "animal_pens": ["goblin_camp", "animal"],
    "water_source": ["goblin_camp", "water"],
    "waste_disposal": ["goblin_camp", "waste"],
    "side_tunnels": ["goblin_camp", "storage"],
}

# ── Furniture role+domain table (library item id -> tags to ADD) ──
FURNITURE_TAGS = {
    "barrel": ["storage", "food"],
    "crate": ["storage"],
    "shelves": ["display"],
    "table": ["display"],
    "cupboard": ["storage"],
    "trunk": ["storage"],
    "nightstand": ["storage"],
    "desk": ["display"],
    "wardrobe_g1": ["storage"],
    "wardrobe_master": ["storage"],
    "wardrobe_attic": ["storage"],
    "locker": ["storage"],
    "sideboard": ["display", "storage"],
    "vanity": ["storage"],
    "bed": ["sleeping"],
    "cot": ["sleeping"],
    "child_bed": ["sleeping", "nursery"],
    "crib": ["furniture", "container", "nursery"],
    "toy_box": ["storage", "nursery"],
    "rocking_horse": ["nursery"],
    "fireplace": ["cooking", "display"],
    "stove": ["cooking"],
    "meat_hooks": ["furniture", "display", "cooking", "food"],
    "cleaver_rack": ["furniture", "display", "cooking"],
    "altar": ["furniture", "display", "shrine"],
    "bookshelf_item": ["display"],
    "garden_bench": ["display"],
    "lab_table": ["display"],
    "booth_table": ["display"],
}

# ── Item domain table (library item id -> tags to ADD) ──
ITEM_TAGS = {
    # weapons -> training/armory (+ guard for entrance posts)
    "knife": ["armory", "guard"], "small_knife": ["armory", "guard"],
    "rusty_hatchet": ["armory", "guard"], "spear": ["armory", "guard"],
    "club": ["armory", "guard"], "heavy_club": ["armory"],
    "cleaver": ["armory", "cooking"], "crossbow": ["armory", "guard"],
    # tools -> workshop (+ guard/entrance light + rope)
    "rope": ["workshop", "entrance"], "pry_bar": ["workshop"],
    "torch": ["workshop", "light", "guard", "entrance"],
    "lantern": ["workshop", "light", "guard", "entrance"],
    "unlit_torch": ["workshop", "light", "entrance"],
    # food -> food/cooking
    "bread": ["food"], "berries": ["food"], "mushrooms": ["food"],
    "dried_meat": ["food"], "hanging_dried_meats": ["food", "cooking"],
    "wheel_of_cheese": ["food"], "cheese_shred": ["food"],
    "cauldron": ["cooking"],
    # occult -> shrine (+ guard fetishes on posts)
    "bone": ["occult", "shrine", "guard"], "bones": ["occult", "shrine", "guard"],
    "talisman": ["occult", "shrine"], "bravery_charm": ["occult", "shrine"],
    # medical
    "healing_herbs": ["medical"], "bandages": ["medical"],
    "ace_bandage": ["medical"], "healing_potion": ["medical"],
    # scouting
    "crude_map": ["scouting", "entrance"], "brass_spyglass": ["scouting"],
    # water / storage
    "water_skin": ["water"], "half_full_waterskin": ["water"],
    "backpack": ["storage"],
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ensure_tag_files(tag_dir: Path, dry_run: bool):
    created, existing = [], []
    for tag in NEEDED_TAGS:
        path = tag_dir / f"{tag}.json"
        if path.exists():
            existing.append(tag)
            continue
        created.append(tag)
        if not dry_run:
            dump(path, tag_file_def(tag))
    return created, existing


def add_tags_to_file(path: Path, additions, dry_run: bool):
    """Add tags to a library file's top-level 'tags' array. Returns (changed, before, after)."""
    if not path.exists():
        return False, [], []
    data = load(path)
    tags = data.get("tags")
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    tags = [str(t) for t in (tags or [])]
    lower = {t.lower() for t in tags}
    before = list(tags)
    for t in additions:
        if t.lower() not in lower:
            tags.append(t)
            lower.add(t.lower())
    if tags == before:
        return False, before, before
    data["tags"] = tags
    if not dry_run:
        dump(path, data)
    return True, before, tags


def run_group(kind: str, table: dict, subdir: str, dry_run: bool):
    print(f"\n== {kind} ({len(table)} entries) ==")
    changed = 0
    for entry_id, additions in sorted(table.items()):
        path = LIBRARY / subdir / f"{entry_id}.json"
        if not path.exists():
            print(f"  MISSING {subdir}/{entry_id}.json")
            continue
        did, before, after = add_tags_to_file(path, additions, dry_run)
        if did:
            changed += 1
            print(f"  {entry_id}: {before} + {[t for t in additions if t not in before]} -> {after}")
    print(f"  {changed} file(s) {'would change' if dry_run else 'changed'}")
    return changed


def main():
    ap = argparse.ArgumentParser(description="Apply domain/role tags for the population chain.")
    ap.add_argument("--apply", action="store_true", help="Write changes (default: dry-run)")
    args = ap.parse_args()
    dry_run = not args.apply

    tag_dir = LIBRARY / "tags"
    print(f"{'DRY RUN' if dry_run else 'APPLYING'} — library={LIBRARY}")
    created, existing = ensure_tag_files(tag_dir, dry_run)
    print("Tag files: created", created, "| already present", len(existing))

    total = 0
    total += run_group("Area domains", AREA_DOMAINS, "areas", dry_run)
    total += run_group("Furniture roles/domains", FURNITURE_TAGS, "items", dry_run)
    total += run_group("Item domains", ITEM_TAGS, "items", dry_run)

    print(f"\nTotal files {'to change' if dry_run else 'changed'}: {total}")
    if dry_run:
        print("Re-run with --apply to write.")


if __name__ == "__main__":
    main()
