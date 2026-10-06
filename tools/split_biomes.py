"""Split bundled biomes.json into one-file-per-entry library directories.

Reads ``data/worldpainter/biomes.json`` and writes:
- ``data/library/biomes/<id>.json`` for each biome
- ``data/library/features/<id>.json`` for each feature

The original ``biomes.json`` is left in place so the loader can fall back to it.
"""
from __future__ import annotations

import json
import os

BIOMES_SRC = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "worldpainter", "biomes.json",
)
BIOME_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "library", "biomes",
)
FEATURE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "library", "features",
)


def migrate() -> None:
    with open(BIOMES_SRC, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    bios = data.get("biomes") or {}
    feats = data.get("features") or {}

    os.makedirs(BIOME_DIR, exist_ok=True)
    os.makedirs(FEATURE_DIR, exist_ok=True)

    written_biomes = 0
    for bid, rec in bios.items():
        path = os.path.join(BIOME_DIR, f"{bid}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=2, ensure_ascii=False)
        written_biomes += 1

    written_features = 0
    for fid, rec in feats.items():
        path = os.path.join(FEATURE_DIR, f"{fid}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=2, ensure_ascii=False)
        written_features += 1

    print(f"Wrote {written_biomes} biome files to {BIOME_DIR}")
    print(f"Wrote {written_features} feature files to {FEATURE_DIR}")


if __name__ == "__main__":
    migrate()
