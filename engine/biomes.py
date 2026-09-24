"""WorldPainter biome/feature taxonomy (task-497).

Data-first definition of the tiles a painted world is drawn from: each biome maps
to the engine **area tags** an area gets and the **forage skills** that work
there, with deterministic description fragments; features (road, bridge, town,
ruin, ...) name where they may appear; and resource/hostile distribution tables
say what a painted area is likely to hold.

The taxonomy is *data*: :func:`validate` is generic, so adding a biome is a JSON
edit that reuses existing area tags and forage skills — no code change. The
foraging layer already recognises the biome tags (``engine/foraging.py``
``AREA_SKILL_BONUS``) and the resource tags come from its ``SKILL_TABLES``
vocabulary, so a painted area forages with the machinery that already exists.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from engine import foraging

#: The shipped taxonomy.
DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "worldpainter", "biomes.json",
)

#: Hostiles the distribution tables may name.
HOSTILE_KINDS = ("predator", "bandit", "monster")

_cache: Dict[str, dict] = {}


# ───────────────────────────── loading ────────────────────────────────────

def load(path: Optional[str] = None, *, fresh: bool = False) -> dict:
    """Load and cache the taxonomy. ``fresh`` bypasses the cache (tests)."""
    key = os.path.abspath(path or DATA_PATH)
    if fresh or key not in _cache:
        with open(key, "r", encoding="utf-8-sig") as f:
            _cache[key] = json.load(f)
    return _cache[key]


def clear_cache() -> None:
    _cache.clear()


def biomes(path: Optional[str] = None) -> Dict[str, dict]:
    return load(path).get("biomes") or {}


def features(path: Optional[str] = None) -> Dict[str, dict]:
    return load(path).get("features") or {}


def resource_distribution(path: Optional[str] = None) -> Dict[str, list]:
    return load(path).get("resource_distribution") or {}


def hostile_distribution(path: Optional[str] = None) -> Dict[str, list]:
    return load(path).get("hostile_distribution") or {}


def biome(biome_id, path: Optional[str] = None) -> Optional[dict]:
    return biomes(path).get(str(biome_id))


def area_tags(biome_id, path: Optional[str] = None) -> List[str]:
    """The engine area tags a painted area of *biome_id* carries."""
    rec = biome(biome_id, path) or {}
    return [str(t).lower() for t in (rec.get("tags") or [])]


def forage_skill_bonus(biome_id, path: Optional[str] = None) -> Dict[str, int]:
    """``foraging.AREA_SKILL_BONUS`` merged over a biome's tags (max per skill).

    This is the concrete "usable by engine/foraging.py": a painted forest area is
    foragable exactly as a hand-authored one is, with no extra wiring.
    """
    out: Dict[str, int] = {}
    for tag in area_tags(biome_id, path):
        for skill, bonus in foraging.AREA_SKILL_BONUS.get(tag, {}).items():
            out[skill] = max(out.get(skill, 0), int(bonus))
    return out


def _forage_vocabulary() -> set:
    """The tag vocabulary the foraging tables draw from (task-497 reuse)."""
    vocab = set()
    for entries in foraging.SKILL_TABLES.values():
        for entry in entries:
            for t in (entry.get("tags") or []):
                vocab.add(str(t).lower())
    return vocab


# ──────────────────────────── validation ──────────────────────────────────

def _num(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def validate(data: Optional[dict] = None, path: Optional[str] = None) -> List[str]:
    """Return human-readable problems with the taxonomy; ``[]`` when clean."""
    problems: List[str] = []
    data = data if data is not None else load(path)

    bios = data.get("biomes")
    feats = data.get("features")
    if not isinstance(bios, dict) or not bios:
        return ["no biomes defined"]

    recognized = {str(t).lower() for t in foraging.AREA_SKILL_BONUS}
    skills = set(foraging.SKILL_TABLES)
    vocab = _forage_vocabulary()

    for bid, rec in bios.items():
        if not isinstance(rec, dict):
            problems.append(f"biome {bid}: not an object")
            continue
        if not rec.get("name"):
            problems.append(f"biome {bid}: missing name")
        if not rec.get("terrain"):
            problems.append(f"biome {bid}: missing terrain")
        tags = [str(t).lower() for t in (rec.get("tags") or [])]
        if not tags:
            problems.append(f"biome {bid}: no area tags")
        elif not (set(tags) & recognized):
            problems.append(
                f"biome {bid}: no area tag foraging recognises "
                f"({sorted(recognized)}); areas would be barren")
        for skill in (rec.get("forage_skills") or []):
            if str(skill).lower() not in skills:
                problems.append(f"biome {bid}: unknown forage skill '{skill}'")
        if not rec.get("floor"):
            problems.append(f"biome {bid}: missing floor")
        if not [d for d in (rec.get("descriptions") or []) if str(d).strip()]:
            problems.append(f"biome {bid}: no description fragments")

    for fid, rec in (feats or {}).items():
        if not isinstance(rec, dict):
            problems.append(f"feature {fid}: not an object")
            continue
        if not rec.get("name"):
            problems.append(f"feature {fid}: missing name")
        if not (rec.get("tags") or []):
            problems.append(f"feature {fid}: no tags")
        for ref in (rec.get("biomes") or []):
            if ref not in bios:
                problems.append(f"feature {fid}: unknown biome '{ref}'")
        if not [d for d in (rec.get("descriptions") or []) if str(d).strip()]:
            problems.append(f"feature {fid}: no description fragments")

    resources = data.get("resource_distribution") or {}
    for bid, entries in resources.items():
        if bid not in bios:
            problems.append(f"resource_distribution: unknown biome '{bid}'")
        for entry in entries:
            etags = {str(t).lower() for t in (entry.get("tags") or [])}
            if not etags:
                problems.append(f"resource_distribution[{bid}]: entry with no tags")
                continue
            unknown = etags - vocab
            if unknown:
                problems.append(
                    f"resource_distribution[{bid}]: tags not in the foraging "
                    f"vocabulary {sorted(unknown)}")
            weight = _num(entry.get("weight"), 0)
            if weight is None or weight <= 0:
                problems.append(f"resource_distribution[{bid}]: non-positive weight")
    for bid in bios:
        if bid not in resources:
            problems.append(f"resource_distribution: biome '{bid}' has no rules")

    hostiles = data.get("hostile_distribution") or {}
    for bid, entries in hostiles.items():
        if bid not in bios:
            problems.append(f"hostile_distribution: unknown biome '{bid}'")
        for entry in entries:
            kind = str(entry.get("kind") or "")
            if kind not in HOSTILE_KINDS:
                problems.append(
                    f"hostile_distribution[{bid}]: unknown kind '{kind}' "
                    f"({list(HOSTILE_KINDS)})")
            base = _num(entry.get("base_chance"))
            per = _num(entry.get("per_area_from_settlement"))
            cap = _num(entry.get("max_chance"))
            if base is None or not (0 <= base <= 1):
                problems.append(f"hostile_distribution[{bid}]: base_chance out of [0,1]")
            if per is None or per < 0:
                problems.append(f"hostile_distribution[{bid}]: per_area_from_settlement must be >= 0")
            if base is not None and cap is not None and cap < base:
                problems.append(f"hostile_distribution[{bid}]: max_chance < base_chance")
    for bid in bios:
        if bid not in hostiles:
            problems.append(f"hostile_distribution: biome '{bid}' has no rules")

    return problems
