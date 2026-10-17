#!/usr/bin/env python3
"""
Weather library guard (task-772)
================================
Validates every record in ``data/library/weather/`` so a broken type cannot
reach the sky.

Checks (errors, exit 1):
  * required fields present: id, name, kind, icon, light_mult, time_dc,
    description, tags
  * filename stem == the record id, and ids are unique
  * kind is ``normal`` or ``extreme``
  * light_mult is a number, time_dc an int, tags a list, description a string

Warnings (not fatal):
  * a type no path can *enter* - the snowy bug: it multiplied cleanly but no row
    ever transitioned into it, so a winter world could not produce snow. A type
    is reachable via the base table, a **season** edge, a **terrain** edge, or
    the extreme tail (task-763); if none of those enter it, it can never occur.
  * a WEATHER_ALIASES target that names a type no record defines.

Usage:
    python tools/weather_library_check.py            # --check
    python tools/weather_library_check.py --report
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REGISTRY = ROOT / "data" / "library" / "weather"
START_STATE = "clear"   # ForecastSchedule.current_state default


def _load() -> list[tuple[Path, dict]]:
    out = []
    if not REGISTRY.is_dir():
        return out
    for path in sorted(REGISTRY.glob("*.json")):
        try:
            out.append((path, json.loads(path.read_text(encoding="utf-8-sig"))))
        except (OSError, ValueError) as exc:
            out.append((path, {"__error__": str(exc)}))
    return out


def check(report: bool = False) -> int:
    from engine.weather_forecast import DEFAULT_TRANSITION_TABLE, WEATHER_ALIASES
    from engine.weather_types import record_problems

    errors: list[str] = []
    warnings: list[str] = []
    seen: dict[str, Path] = {}
    ids: set[str] = set()

    rows = _load()
    if not rows:
        print(f"warn: no weather records under {REGISTRY}")
    for path, rec in rows:
        where = path.name
        if "__error__" in rec:
            errors.append(f"{where}: not valid JSON ({rec['__error__']})")
            continue
        # The same per-record validator the library save route uses, so a
        # record that saves is a record this accepts (task-772).
        errors.extend(f"{where}: {p}" for p in record_problems(path.stem, rec))
        rid = rec.get("id")
        if isinstance(rid, str):
            if rid in seen:
                errors.append(f"{where}: duplicate id {rid!r} (also {seen[rid].name})")
            seen[rid] = path
            ids.add(rid)

    # Reachability (task-763): a type must be enterable by SOME path - the base
    # table, a *season* edge, a *terrain* edge, or the always-on extreme tail.
    # Reading only the base table is what made the snowy bug a false negative
    # before, and would now false-positive every season/terrain-only extreme.
    from engine.weather_forecast import SEASON_WEATHER_BIAS, TERRAIN_WEATHER_BIAS

    reachable: set[str] = set()
    for row in DEFAULT_TRANSITION_TABLE.values():
        if isinstance(row, dict):
            reachable |= {s for s, w in row.items() if (w or 0) > 0}
    for bias in SEASON_WEATHER_BIAS.values():
        reachable |= {s for s, w in bias.items() if (w or 0) > 0}
    for bias in TERRAIN_WEATHER_BIAS.values():
        reachable |= {s for s, w in bias.items() if (w or 0) > 0}
    kinds = {rec["id"]: rec.get("kind")
             for _p, rec in rows
             if isinstance(rec, dict) and isinstance(rec.get("id"), str)}
    for rid in sorted(ids):
        if rid == START_STATE or rid in reachable:
            continue
        if kinds.get(rid) == "extreme":
            continue                 # the tail tier keeps every extreme reachable
        warnings.append(f"{rid}: unreachable - no transition, season or terrain "
                        f"edge enters it (add one or mark it a start state)")

    # Alias targets must name a real type.
    for spelling, target in sorted(WEATHER_ALIASES.items()):
        if target not in ids:
            warnings.append(f"alias {spelling!r} -> {target!r} names no record")

    if report:
        print(f"{len(rows)} record(s) under {REGISTRY}")
    for w in warnings:
        print(f"warn: {w}")
    for e in errors:
        print(f"error: {e}")
    print(f"weather library: {len(rows)} record(s), "
          f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(check(report="--report" in sys.argv))
