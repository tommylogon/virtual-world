"""Biome narrative pools and way phrase generators for WorldPainter (task-887).

Assigns non-empty descriptions to compiled way nodes and visible_in_direction
text to incoming connection edges (area -> way). Phrasing is driven by
data/worldpainter/way_narratives.json, selecting deterministically via stable
weighted indexing so adjacent ways exhibit natural variation without random drift.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Tuple

from engine import biomes
from engine.world_compile_stable import _stable_index

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "worldpainter", "way_narratives.json",
)

_NARRATIVES_CACHE: Optional[Dict[str, dict]] = None

_TERRAIN_MAP: Dict[str, str] = {
    "forest": "woods",
    "rock": "rock",
    "water": "water",
    "farm": "cultivated",
    "urban": "urban",
    "indoor": "indoor",
}


def load_narratives() -> Dict[str, dict]:
    """Load the way narratives json file, caching in memory."""
    global _NARRATIVES_CACHE
    if _NARRATIVES_CACHE is None:
        if os.path.exists(DATA_PATH):
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                _NARRATIVES_CACHE = json.load(f)
        else:
            _NARRATIVES_CACHE = {"kinds": {}, "transitions": {}}
    return _NARRATIVES_CACHE


def classify_terrain(biome_id: Optional[str], road: Optional[str] = None) -> str:
    """Classify the terrain for a cell into a broad narrative class."""
    if road:
        return "road"
    if not biome_id:
        return "open"
    rec = biomes.biome(biome_id) or {}
    t = str(rec.get("terrain") or "").strip().lower()
    return _TERRAIN_MAP.get(t, "open")


def get_way_narrative(
    biome_from: Optional[str],
    biome_to: Optional[str],
    road_from: Optional[str] = None,
    road_to: Optional[str] = None,
    kind: str = "open",
    direction: str = "",
    seed: str = "",
    scope_id: str = "",
    way_id: str = "",
) -> Tuple[str, str, str]:
    """Return (description, view_from_a, view_from_b) for a compiled way.

    - description: Full sentence for the way node properties.
    - view_from_a: visible_in_direction looking from area A towards area B.
    - view_from_b: visible_in_direction looking from area B towards area A.
    """
    data = load_narratives()
    kinds = data.get("kinds", {})
    transitions = data.get("transitions", {})
    default_pool = transitions.get("default", {
        "descriptions": ["A clear pathway connecting the two areas."],
        "forward_views": ["a clear path leading forward"],
        "reverse_views": ["a clear path leading forward"],
    })

    # 1. Structural kind override (door, stairs, entrance)
    if kind in kinds:
        pool = kinds[kind]
        descs = pool.get("descriptions") or default_pool["descriptions"]
        f_views = pool.get("forward_views") or default_pool["forward_views"]
        r_views = pool.get("reverse_views") or f_views

        idx_desc = _stable_index(f"{scope_id}:{way_id}:desc:{seed}:{kind}", len(descs))
        idx_a = _stable_index(f"{scope_id}:{way_id}:a:{direction}:{seed}:{kind}", len(f_views))
        idx_b = _stable_index(f"{scope_id}:{way_id}:b:{direction}:{seed}:{kind}", len(r_views))
        return descs[idx_desc], f_views[idx_a], r_views[idx_b]

    # 2. Transition between two cells
    b_from = str(biome_from or "").strip().lower()
    b_to = str(biome_to or "").strip().lower()
    cls_from = classify_terrain(biome_from, road_from)
    cls_to = classify_terrain(biome_to, road_to)

    pool = None
    reversed_match = False

    # Check specific biome pair
    if b_from and b_to:
        pair = f"{b_from}:{b_to}"
        rev_pair = f"{b_to}:{b_from}"
        if pair in transitions:
            pool = transitions[pair]
            reversed_match = False
        elif rev_pair in transitions:
            pool = transitions[rev_pair]
            reversed_match = True

    # Check terrain class pair
    if pool is None:
        pair = f"{cls_from}:{cls_to}"
        rev_pair = f"{cls_to}:{cls_from}"
        if pair in transitions:
            pool = transitions[pair]
            reversed_match = False
        elif rev_pair in transitions:
            pool = transitions[rev_pair]
            reversed_match = True

    # Check single class fallback
    if pool is None:
        if f"{cls_from}:{cls_from}" in transitions:
            pool = transitions[f"{cls_from}:{cls_from}"]
            reversed_match = False
        elif f"{cls_to}:{cls_to}" in transitions:
            pool = transitions[f"{cls_to}:{cls_to}"]
            reversed_match = False
        else:
            pool = default_pool
            reversed_match = False

    descs = pool.get("descriptions") or default_pool["descriptions"]
    if reversed_match:
        views_a = pool.get("reverse_views") or pool.get("forward_views") or default_pool["forward_views"]
        views_b = pool.get("forward_views") or pool.get("reverse_views") or default_pool["reverse_views"]
    else:
        views_a = pool.get("forward_views") or default_pool["forward_views"]
        views_b = pool.get("reverse_views") or pool.get("forward_views") or default_pool["reverse_views"]

    idx_desc = _stable_index(f"{scope_id}:{way_id}:desc:{seed}", len(descs))
    idx_a = _stable_index(f"{scope_id}:{way_id}:a:{direction}:{seed}", len(views_a))
    idx_b = _stable_index(f"{scope_id}:{way_id}:b:{direction}:{seed}", len(views_b))

    return descs[idx_desc], views_a[idx_a], views_b[idx_b]
