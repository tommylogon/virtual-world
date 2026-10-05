#!/usr/bin/env python3
"""Migrate resource_distribution and hostile_distribution out of biomes.json.

Reads the bundled keys from data/worldpainter/biomes.json and writes one
library JSON file per entry under data/library/resource_distribution/ and
data/library/hostile_distribution/.

Idempotent: skips files that already exist unless --force is passed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIOMES_PATH = ROOT / "data" / "worldpainter" / "biomes.json"
RESOURCE_DIR = ROOT / "data" / "library" / "resource_distribution"
HOSTILE_DIR = ROOT / "data" / "library" / "hostile_distribution"


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in text.lower()).strip("_")


def _resource_entry_name(biome_id: str, idx: int, tags: list[str]) -> str:
    tag_part = "_".join(_slug(t) for t in tags[:2]) or "entry"
    return f"{_slug(biome_id)}_{tag_part}_{idx}"


def _hostile_entry_name(biome_id: str, idx: int, kind: str) -> str:
    return f"{_slug(biome_id)}_{_slug(kind)}_{idx}"


def migrate(force: bool = False) -> None:
    with BIOMES_PATH.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)

    resources = data.get("resource_distribution") or {}
    hostiles = data.get("hostile_distribution") or {}

    RESOURCE_DIR.mkdir(parents=True, exist_ok=True)
    HOSTILE_DIR.mkdir(parents=True, exist_ok=True)

    written_resource = 0
    written_hostile = 0

    for biome_id, entries in resources.items():
        for idx, entry in enumerate(entries):
            tags = [str(t) for t in (entry.get("tags") or [])]
            weight = entry.get("weight", 1)
            name = f"{biome_id} resource {idx + 1}"
            entry_id = _resource_entry_name(biome_id, idx, tags)
            payload = {
                "id": entry_id,
                "name": name,
                "biome_tags": [str(biome_id)],
                "location_tags": [],
                "item_tags": tags,
                "weight": weight,
                "conditions": {},
            }
            path = RESOURCE_DIR / f"{entry_id}.json"
            if path.exists() and not force:
                continue
            with path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
                f.write("\n")
            written_resource += 1

    for biome_id, entries in hostiles.items():
        for idx, entry in enumerate(entries):
            kind = str(entry.get("kind") or "")
            if not kind:
                continue
            entry_id = _hostile_entry_name(biome_id, idx, kind)
            name = f"{biome_id} {kind} {idx + 1}"
            payload = {
                "id": entry_id,
                "name": name,
                "biome_tags": [str(biome_id)],
                "location_tags": [],
                "kind": kind,
                "base_chance": entry.get("base_chance", 0.0),
                "per_area_from_settlement": entry.get("per_area_from_settlement", 0.0),
                "max_chance": entry.get("max_chance", 1.0),
                "conditions": {},
            }
            path = HOSTILE_DIR / f"{entry_id}.json"
            if path.exists() and not force:
                continue
            with path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
                f.write("\n")
            written_hostile += 1

    print(f"Wrote {written_resource} resource loot table(s) to {RESOURCE_DIR}")
    print(f"Wrote {written_hostile} hostile loot table(s) to {HOSTILE_DIR}")
    print("Next: remove the bundled keys from biomes.json after verifying the new files.")
    print("      python tools/migrate_loot_tables.py --strip-biomes")


def strip_biomes() -> None:
    with BIOMES_PATH.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if "resource_distribution" in data or "hostile_distribution" in data:
        data.pop("resource_distribution", None)
        data.pop("hostile_distribution", None)
        with BIOMES_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        print(f"Stripped bundled keys from {BIOMES_PATH}")
    else:
        print("No bundled keys found in biomes.json; nothing to strip.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate loot tables out of biomes.json")
    parser.add_argument("--force", action="store_true", help="Overwrite existing library files")
    parser.add_argument("--strip-biomes", action="store_true", help="Remove bundled keys from biomes.json")
    args = parser.parse_args()
    if args.strip_biomes:
        strip_biomes()
    else:
        migrate(force=args.force)


if __name__ == "__main__":
    main()
