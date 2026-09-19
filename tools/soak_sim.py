#!/usr/bin/env python3
"""soak_sim.py - headless long-horizon soak runner for VirtualWorld.

Loads a scenario JSON, drives TickManager.tick_turn() in a tight loop for N
ticks (1 tick = ``time_per_tick_minutes`` of game time), and reports what
happened: wall-clock cost, death times/causes, vital drift, and log/memory
growth. It touches no global state and does not write the scenario, so it is
safe to run against a live world.

This is the "can the world run for weeks?" experiment. It deliberately makes
no LLM calls; characters act only through the deterministic tick path
(simple-NPC behaviors) or not at all.

Usage:
    python tools/soak_sim.py --ticks 30240 --engine-decay
    python tools/soak_sim.py --ticks 4320 --engine-decay --override "Energy=0,Hunger=0"
    python tools/soak_sim.py --ticks 30240 --engine-decay --apply-trait "goblin=high_metabolism"
"""

import argparse
import json
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from virtual_world_engine import VirtualWorld  # noqa: E402


def parse_kv_pairs(spec):
    """'a=1,b=2' -> {'a': 1, 'b': 2} (values parsed as float when numeric)."""
    out = {}
    if not spec:
        return out
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise SystemExit(f"Bad key=value chunk: {chunk!r}")
        key, value = chunk.split("=", 1)
        key, value = key.strip(), value.strip()
        try:
            out[key] = float(value)
        except ValueError:
            out[key] = value
    return out


def infer_cause(player):
    v = player.vitals
    if v.get("Thirst", 0) >= 100:
        return "dehydration"
    if v.get("Hunger", 0) >= 100:
        return "starvation"
    if v.get("Energy", 1) <= 0:
        return "exhaustion"
    if v.get("HP", 1) <= 0:
        return "hp_loss"
    return "unknown"


def fmt_span(ticks, minutes_per_tick):
    total_min = ticks * minutes_per_tick
    days = int(total_min // 1440)
    hours = int((total_min % 1440) // 60)
    mins = int(total_min % 60)
    return f"{days}d{hours:02d}h{mins:02d}m"


def main():
    ap = argparse.ArgumentParser(description="VirtualWorld headless soak runner")
    ap.add_argument("--scenario", default="data/scenarios/kraktooth_goblin_camp.json")
    ap.add_argument("--ticks", type=int, default=10080, help="ticks to simulate (10080 = 1 week @ 1min/tick)")
    ap.add_argument("--engine-decay", action="store_true",
                    help="drop each player's baked decay_rates so engine defaults apply")
    ap.add_argument("--override", default="", help="per-player decay overrides, e.g. 'Energy=0,Thirst=0'")
    ap.add_argument("--apply-trait", default="", help="apply a trait by tag, e.g. 'goblin=high_metabolism'")
    ap.add_argument("--neutral-environment", action="store_true",
                    help="in-memory only: force every area to a benign 37C/fresh/quiet environment "
                         "so cold- and air-driven per-tick drains do not confound the decay measurement")
    ap.add_argument("--progress", type=int, default=2000, help="progress print interval in ticks (0=off)")
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--report", default="", help="write a JSON report to this path")
    args = ap.parse_args()

    random.seed(args.seed)

    scenario_path = ROOT / args.scenario
    with open(scenario_path, "r", encoding="utf-8-sig") as fh:
        data = json.load(fh)

    world = VirtualWorld()
    world.load_from_dict(data)

    minutes_per_tick = getattr(world, "time_per_tick_minutes", 1) or 1
    players = world.player_manager.players

    overrides = parse_kv_pairs(args.override)
    trait_spec = parse_kv_pairs(args.apply_trait)
    if isinstance(trait_spec, dict):
        trait_spec = {str(k): str(v) for k, v in trait_spec.items()}

    # --- apply experiment configuration (in-memory only) ---
    if args.engine_decay or overrides:
        for p in players.values():
            if args.engine_decay:
                p.decay_rates = {}
            for stat, rate in overrides.items():
                p.decay_rates[stat] = rate
    if trait_spec:
        for p in players.values():
            tags = set(p.tags or [])
            for tag, trait_id in trait_spec.items():
                if tag in tags:
                    p.traits[trait_id] = True

    if args.neutral_environment:
        # 20C sits inside the engine's 5..35 "neutral" band, so core temp
        # holds at 37 and no hot/cold per-tick Energy/HP/Thirst effects fire.
        benign = {
            "light": "normal", "temperature": 20, "air": "fresh",
            "smell": "neutral", "noise": "quiet", "wind": "none", "humidity": "dry",
        }
        for node in world.graph.nodes.values():
            if node.type == "area":
                node.properties["environment"] = dict(benign)
        for p in players.values():
            p.vitals["Temperature"] = 37.0

    start_vitals = {name: dict(p.vitals) for name, p in players.items()}
    deaths = []
    dead_seen = set()

    if args.progress:
        print(f"[soak] {len(players)} characters | {args.ticks} ticks "
              f"({fmt_span(args.ticks, minutes_per_tick)} game time) | "
              f"{minutes_per_tick} min/tick")

    t0 = time.perf_counter()
    last_report = t0
    last_tick = 0

    for i in range(1, args.ticks + 1):
        world.tick_turn()

        for name, p in players.items():
            if name in dead_seen:
                continue
            if p.state == "dead":
                dead_seen.add(name)
                deaths.append({
                    "name": name,
                    "tick": i,
                    "game_span": fmt_span(i, minutes_per_tick),
                    "area": getattr(p, "current_area", None),
                    "cause": infer_cause(p),
                    "hunger": p.vitals.get("Hunger"),
                    "thirst": p.vitals.get("Thirst"),
                    "energy": p.vitals.get("Energy"),
                    "tags": list(p.tags or []),
                })

        if args.progress and i - last_tick >= args.progress:
            now = time.perf_counter()
            rate = (i - last_tick) / max(now - last_report, 1e-9)
            alive = len(players) - len(dead_seen)
            print(f"[soak] tick {i:>7}/{args.ticks}  {fmt_span(i, minutes_per_tick):>10}  "
                  f"alive {alive:>3}  dead {len(dead_seen):>3}  {rate:,.0f} ticks/s")
            last_tick = i
            last_report = now

    wall = time.perf_counter() - t0
    ticks_per_sec = args.ticks / max(wall, 1e-9)

    # --- survivors + final vitals ---
    survivors = [n for n in players if n not in dead_seen]
    final = {n: dict(players[n].vitals) for n in survivors}

    def avg(key, src):
        vals = [src[n][key] for n in src if src[n].get(key) is not None]
        return round(statistics.mean(vals), 1) if vals else None

    cause_counts = {}
    for d in deaths:
        cause_counts[d["cause"]] = cause_counts.get(d["cause"], 0) + 1

    summary = {
        "scenario": str(scenario_path.relative_to(ROOT)),
        "ticks": args.ticks,
        "game_span": fmt_span(args.ticks, minutes_per_tick),
        "minutes_per_tick": minutes_per_tick,
        "wall_seconds": round(wall, 2),
        "ticks_per_second": round(ticks_per_sec, 1),
        "projected_1week_wall_seconds": round(10080 / max(ticks_per_sec, 1e-9), 1),
        "characters": len(players),
        "deaths": len(deaths),
        "survivors": len(survivors),
        "causes": cause_counts,
        "game_log_entries": len(getattr(world, "game_log", []) or []),
        "turn_events": len(getattr(world, "turn_events", []) or []),
        "delayed_events": len(getattr(world, "delayed_events", []) or []),
        "graph_nodes": len(world.graph.nodes),
        "total_memories": sum(len(getattr(p, "memories", []) or []) for p in players.values()),
        "survivor_avg_vitals": {
            "Hunger": avg("Hunger", final),
            "Thirst": avg("Thirst", final),
            "Energy": avg("Energy", final),
            "HP": avg("HP", final),
        },
    }

    print("\n=== SOAK RESULT ===")
    for key in ("scenario", "ticks", "game_span", "wall_seconds", "ticks_per_second",
                "projected_1week_wall_seconds", "characters", "deaths", "survivors", "causes"):
        print(f"  {key}: {summary[key]}")
    print(f"  game_log_entries: {summary['game_log_entries']:,}")
    print(f"  turn_events: {summary['turn_events']:,}")
    print(f"  graph_nodes: {summary['graph_nodes']:,}")
    print(f"  total_memories: {summary['total_memories']:,}")

    if deaths:
        print("\n  Deaths (first 12):")
        for d in deaths[:12]:
            print(f"    {d['game_span']:>10}  {d['name']:<20} {d['cause']:<12} "
                  f"H={d['hunger']} T={d['thirst']} E={d['energy']} @ {d['area']}")
        spans = [d["tick"] for d in deaths]
        print(f"  death tick median={int(statistics.median(spans))} "
              f"min={min(spans)} max={max(spans)}")

    if survivors:
        print("\n  Survivor averages:")
        for k, v in summary["survivor_avg_vitals"].items():
            print(f"    {k}: {v}")

    if args.report:
        out = ROOT / args.report
        out.write_text(json.dumps({"summary": summary, "deaths": deaths}, indent=2), encoding="utf-8")
        print(f"\n[soak] report written to {out}")


if __name__ == "__main__":
    main()
