"""Terrain hazard registry (task-745).

Policy is **data**: ``data/worldpainter/hazards.json`` maps a hazard id to the
ability check it demands, a strength-keyed DC ladder, and the consequences of
failure. The compiler (task-747) attaches a hazard id to a generated way or area;
this module is the reader the engine uses at the moment of crossing, so the
numbers live in one place and an author can retune them without a code change.

A ladder maps a **strength threshold** (1..20) to a DC. For an encounter of
strength ``S`` the highest threshold ``<= S`` wins; a strength below the lowest
rung uses the lowest, and above the highest uses the highest — so a table is
total over any strength the world can present.

@module hazards
@contributes the terrain hazard registry: strength-keyed DC ladders and on-fail consequences (task-745)
@docs docs/virtualWorld/World Building/WorldPainter.md
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Tuple

from engine import abilities as abilities_mod

#: The shipped registry.
DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "worldpainter", "hazards.json",
)

_cache: Dict[str, dict] = {}


def load(path: Optional[str] = None, *, fresh: bool = False) -> dict:
    """Load and cache the registry. ``fresh`` bypasses the cache (tests)."""
    key = os.path.abspath(path or DATA_PATH)
    if fresh or key not in _cache:
        try:
            with open(key, "r", encoding="utf-8-sig") as handle:
                _cache[key] = json.load(handle)
        except (OSError, ValueError):
            _cache[key] = {}
    return _cache[key]


def clear_cache() -> None:
    """Drop the cached registry so a save is visible without a restart."""
    _cache.clear()


def hazards(path: Optional[str] = None) -> Dict[str, dict]:
    data = load(path)
    out = data.get("hazards")
    return out if isinstance(out, dict) else {}


def hazard(hazard_id: str, path: Optional[str] = None) -> Optional[dict]:
    rec = hazards(path).get(str(hazard_id))
    return rec if isinstance(rec, dict) else None


def ladder(rec: dict) -> List[Tuple[int, int]]:
    """The ``rec``'s DC ladder as sorted ``(threshold, dc)`` pairs."""
    dc = rec.get("dc") if isinstance(rec, dict) else None
    if not isinstance(dc, dict):
        return []
    rungs: List[Tuple[int, int]] = []
    for key, value in dc.items():
        try:
            rungs.append((int(key), int(value)))
        except (TypeError, ValueError):
            continue
    return sorted(rungs)


def dc_for(hazard_id: str, strength: int, path: Optional[str] = None) -> Optional[int]:
    """The DC a hazard demands at an encounter strength, or ``None``."""
    rungs = ladder(hazard(hazard_id, path) or {})
    if not rungs:
        return None
    chosen = rungs[0][1]
    for threshold, dc in rungs:
        if strength >= threshold:
            chosen = dc
        else:
            break
    return chosen


def validate(data: Optional[dict] = None, path: Optional[str] = None) -> List[str]:
    """Return human-readable problems with the registry; ``[]`` when clean."""
    problems: List[str] = []
    if data is None:
        data = load(path)
    entries = data.get("hazards")
    if not isinstance(entries, dict) or not entries:
        return ["no hazards defined"]
    for hid, rec in entries.items():
        problems.extend(hazard_problems(hid, rec))
    return problems


def hazard_problems(hid: str, rec: dict) -> List[str]:
    """Per-hazard problems, shared by :func:`validate` and the vocabulary save
    route (task-589), so a save refuses exactly what ``validate()`` would."""
    if not isinstance(rec, dict):
        return [f"hazard {hid}: not an object"]
    problems: List[str] = []
    if not str(rec.get("name") or "").strip():
        problems.append(f"hazard {hid}: missing name")
    ability = str(rec.get("ability") or "")
    if ability not in abilities_mod.ABILITIES:
        problems.append(
            f"hazard {hid}: ability must be one of {list(abilities_mod.ABILITIES)}")
    rungs = ladder(rec)
    if not rungs:
        problems.append(f"hazard {hid}: dc must be a non-empty threshold-to-dc ladder")
    else:
        thresholds = [t for t, _ in rungs]
        if len(set(thresholds)) != len(thresholds):
            problems.append(f"hazard {hid}: dc thresholds must be unique")
        if any(dc < 1 for _, dc in rungs):
            problems.append(f"hazard {hid}: dc values must be positive")
    on_fail = rec.get("on_fail")
    if not isinstance(on_fail, dict):
        problems.append(f"hazard {hid}: on_fail must be an object")
    else:
        for key in ("conditions", "tags"):
            vals = on_fail.get(key)
            if vals is not None and (not isinstance(vals, list)
                                     or not all(isinstance(v, str) and v.strip()
                                                for v in vals)):
                problems.append(
                    f"hazard {hid}: on_fail.{key} must be a list of non-empty strings")
    for key in ("message_success", "message_fail"):
        if not str(rec.get(key) or "").strip():
            problems.append(f"hazard {hid}: missing {key}")
    return problems
