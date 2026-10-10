#!/usr/bin/env python3
"""Weather generator preview — a standalone spike.

Runs the *heuristic* weather generator (the model task-763 will land) over a
scenario and prints what it chose **and why**: the candidate distribution, the
factors that shaped it, the roll, and a calendar view. Read-only; it never
touches the engine, a save, or the running app, and it never writes.

This is a design instrument, not the engine. The transition table and the
weather vocabulary are imported from `engine/weather_forecast.py` so there is
one source for them; the season and terrain *factors* below are the prototype
numbers to iterate on — when they feel right, they move into the engine.

What it does **not** model (on purpose, see
`docs/design/weather-world-integration.md` §7): precipitation amount (there is
no mm field), snow accumulation, and neighbour coupling (a front spreading
across adjacent areas) — this previews the single-chain-per-world case.

Usage:
    python tools/weather_preview.py
    python tools/weather_preview.py --days 30 --seed 7 --climate alpine
    python tools/weather_preview.py --area area_deep_woods_10_10 --explain 10
    python tools/weather_preview.py --mode authored        # replay the schedule
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.weather_forecast import (  # noqa: E402
    DEFAULT_TRANSITION_TABLE, WEATHER_STATES, normalize_weather, season_for_month,
)

DEFAULT_SCENARIO = ROOT / "data" / "scenarios" / "kraktooth_goblin_camp.json"

#: Short ASCII codes so the calendar prints on any console (cp1252-safe).
CODE = {"clear": "CLR", "cloudy": "CLD", "windy": "WND", "rainy": "RAN",
        "stormy": "STM", "foggy": "FOG", "snowy": "SNW"}

#: Per-season multipliers on the transition weights. Prototype numbers.
SEASON_FACTOR = {
    "winter": {"snowy": 2.6, "cloudy": 1.3, "foggy": 1.1, "clear": 0.7,
               "stormy": 0.6, "windy": 1.1, "rainy": 0.8},
    "spring": {"rainy": 1.4, "windy": 1.2, "cloudy": 1.2, "snowy": 0.3, "clear": 1.0},
    "summer": {"clear": 1.5, "stormy": 1.4, "rainy": 1.0, "cloudy": 0.8, "snowy": 0.0},
    "autumn": {"foggy": 1.5, "cloudy": 1.3, "rainy": 1.2, "windy": 1.1, "clear": 0.8},
}

#: Per-climate (terrain) multipliers. Prototype numbers.
TERRAIN_FACTOR = {
    "arctic":    {"snowy": 3.0, "clear": 0.6, "rainy": 0.5, "stormy": 0.4},
    "alpine":    {"snowy": 2.2, "windy": 1.3, "foggy": 0.8, "rainy": 0.8, "clear": 0.9},
    "temperate": {},
    "arid":      {"clear": 1.6, "rainy": 0.4, "stormy": 0.6, "snowy": 0.0, "foggy": 0.5},
    "tropical":  {"rainy": 1.6, "stormy": 1.4, "clear": 0.8, "snowy": 0.0, "foggy": 1.1},
}


def load_scenario(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def climate_for(scenario: dict, override: str | None) -> tuple[str, Counter]:
    layer = (((scenario.get("world_scopes") or {}).get("world") or {})
             .get("layers") or {}).get("climate") or {}
    counts = Counter(str(v) for v in layer.values())
    if override:
        return override, counts
    if counts:
        return counts.most_common(1)[0][0], counts
    return "temperate", counts


def area_biome(scenario: dict, area: str | None) -> str | None:
    if not area:
        return None
    nodes = (scenario.get("graph") or {}).get("nodes") or {}
    node = nodes.get(area) or nodes.get(f"area_{area}")
    return (node or {}).get("properties", {}).get("biome")


def weighted(states: list[str], base: dict, *factors: dict) -> dict:
    out = {}
    for s in states:
        w = float(base.get(s, 0) or 0)
        for f in factors:
            w *= float(f.get(s, 1.0) if f else 1.0)
        out[s] = w
    return out


def roll(weights: dict, rng: random.Random) -> tuple[str, float, float]:
    total = sum(weights.values())
    if total <= 0:
        return "clear", 0.0, 0.0
    pick = rng.uniform(0, total)
    acc = 0.0
    for state, w in weights.items():
        acc += w
        if pick <= acc:
            return state, pick, total
    return list(weights)[-1], pick, total


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    ap.add_argument("--days", type=int, default=30, help="days to generate (default 30)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--mode", choices=["heuristic", "authored"], default="heuristic")
    ap.add_argument("--climate", help="terrain climate id (default: from the scenario)")
    ap.add_argument("--area", help="read the terrain biome from this area node")
    ap.add_argument("--explain", type=int, default=7,
                    help="print the full why for the first N days (default 7)")
    args = ap.parse_args()

    if not args.scenario.exists():
        print(f"no scenario at {args.scenario}", file=sys.stderr)
        return 1
    sc = load_scenario(args.scenario)
    cfg = sc.get("calendar_config") or {}
    dpw = int(cfg.get("days_per_week", 7))
    dpm = int(cfg.get("days_per_month", 30))
    mpy = int(cfg.get("months_per_year", 12))
    mpd = int(cfg.get("minutes_per_day", 1440))

    per_tick = float(sc.get("time_per_tick_minutes", 1) or 1)
    day = int(sc.get("time_ticks", 0) * per_tick // max(1, mpd)) + 1
    month = ((day - 1) // dpm % mpy) + 1
    season = season_for_month(month)

    fs = sc.get("forecast_schedule") or {}
    authored = fs.get("entries") or []
    start = normalize_weather(fs.get("current_state")) or (
        normalize_weather((authored[0] or {}).get("weather")) if authored else "") or "clear"
    if start not in WEATHER_STATES:
        start = "clear"

    climate, clim_counts = climate_for(sc, args.climate)
    biome = area_biome(sc, args.area)
    season_f = SEASON_FACTOR.get(season, {})
    terrain_f = TERRAIN_FACTOR.get(climate, {})

    print(f"Scenario : {args.scenario.name}")
    print(f"Calendar : {mpy} months x {dpm} days x {dpw}/week")
    print(f"Clock    : day {day}, month {month}  ->  season {season}")
    print(f"Schedule : mode={fs.get('mode')} entries={len(authored)} "
          f"(authored weather is a fallback, not the generator)")
    print(f"Generator: heuristic Markov, seed={args.seed}, one roll per day")
    clim_note = ""
    if clim_counts and sum(clim_counts.values()) < 10:
        clim_note = ("  [thin climate layer: %d cell(s) -> terrain is near-uniform;"
                     " paint climate or pass --climate]" % sum(clim_counts.values()))
    print(f"Terrain  : climate={climate}"
          + (f" (scenario climate layer: {dict(clim_counts)})" if clim_counts else " (no climate layer)")
          + (f", area biome={biome}" if biome else "") + clim_note)
    print(f"Start    : {start}")

    rng = random.Random(args.seed)
    table = DEFAULT_TRANSITION_TABLE
    current = start
    days: list[tuple[str, dict, float, float, str]] = []

    if args.mode == "authored":
        for i in range(args.days):
            entry = authored[i % len(authored)] if authored else {}
            current = normalize_weather(entry.get("weather")) or current
            days.append((current, {}, 0.0, 0.0, "authored entry"))
    else:
        for _ in range(args.days):
            base = table.get(current) or table.get("clear")
            w = weighted(list(base.keys()), base, season_f, terrain_f)
            chosen, pick, total = roll(w, rng)
            days.append((chosen, w, pick, total, f"{current} -> {chosen}"))
            current = chosen

    print("\n-- Calendar (day of month) " + "-" * 34)
    for i, (w, _ws, _p, _t, _n) in enumerate(days):
        if i % dpw == 0:
            print("  ", end="")
        print(f"{i + 1:02d}:{CODE.get(w, '???'):<3} ", end="")
        if i % dpw == dpw - 1:
            print()
    if len(days) % dpw:
        print()
    tally = Counter(w for w, *_ in days)
    print("  totals: " + ", ".join(f"{CODE.get(k, k)} {v}" for k, v in tally.most_common()))

    if args.mode == "heuristic" and args.explain:
        print("\n-- Why (the roll and the factors) " + "-" * 28)
        for i, (chosen, w, pick, total, note) in enumerate(days[:args.explain]):
            pct = {k: (v / total if total else 0) for k, v in w.items()}
            ranked = sorted(pct.items(), key=lambda kv: -kv[1])[:4]
            print(f"\nDay {i + 1:02d}  {note}   roll {pick:.2f}/{total:.2f} -> {chosen}")
            print("   candidates: " + " | ".join(f"{k} {p * 100:.0f}%" for k, p in ranked))
            base = table.get(note.split(' -> ')[0]) or table.get("clear")
            sf = {k: v for k, v in season_f.items() if k in (base or {})}
            tf = {k: v for k, v in terrain_f.items() if k in (base or {})}
            print(f"   base[{note.split(' -> ')[0]}]: {base}")
            print(f"   x season({season}): {sf or '{}'}")
            print(f"   x terrain({climate}): {tf or '{}'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
