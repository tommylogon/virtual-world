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

Progress prints every --progress-seconds (live rate, ETA, deaths so far);
the final report breaks down causes, survival, vitals and growth.

Usage:
    python tools/soak_sim.py --ticks 30240 --engine-decay
    python tools/soak_sim.py --ticks 4320 --engine-decay --neutral-environment \
        --override "Energy=0,Hunger=0" --set "Thirst=0"
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

TICKS_PER_DAY = 1440  # at time_per_tick_minutes == 1


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


def human_duration(seconds):
    seconds = max(0, int(round(seconds)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def progress_bar(frac, width=20):
    frac = max(0.0, min(1.0, frac))
    filled = int(frac * width)
    return "[" + "#" * filled + "." * (width - filled) + "]"


def say(msg, end="\n"):
    """Print immediately — long runs are watched live, not tail-buffered."""
    sys.stdout.write(msg + end)
    sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser(description="VirtualWorld headless soak runner")
    ap.add_argument("--scenario", default="data/scenarios/kraktooth_goblin_camp.json")
    ap.add_argument("--ticks", type=int, default=10080, help="ticks to simulate (10080 = 1 week @ 1min/tick)")
    ap.add_argument("--engine-decay", action="store_true",
                    help="drop each player's baked decay_rates so engine defaults apply")
    ap.add_argument("--override", default="", help="per-player decay overrides, e.g. 'Energy=0,Thirst=0'")
    ap.add_argument("--apply-trait", default="", help="apply a trait by tag, e.g. 'goblin=high_metabolism'")
    ap.add_argument("--set", dest="set_vitals", default="",
                    help="seed every player's starting vitals, e.g. 'Thirst=0,Hunger=0,Energy=100'")
    ap.add_argument("--background-all", action="store_true",
                    help="run every character in background fidelity (deterministic survival runner, no LLM)")
    ap.add_argument("--neutral-environment", action="store_true",
                    help="in-memory only: force every area to a benign 20C/fresh/quiet environment "
                         "so cold- and air-driven drains do not confound the decay measurement")
    ap.add_argument("--progress", type=int, default=0, help="progress interval in ticks (0 = time-based only)")
    ap.add_argument("--progress-seconds", type=float, default=5.0,
                    help="progress interval in wall seconds (0 = tick-based only)")
    ap.add_argument("--debug-hp", action="store_true",
                    help="log every HP drop with the character's conditions, core temp and area env")
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

    if args.background_all:
        for p in players.values():
            p.simulation_mode = "background"
            p.next_due_tick = 0

    set_vitals = parse_kv_pairs(args.set_vitals)
    if set_vitals:
        for p in players.values():
            for stat, val in set_vitals.items():
                p.vitals[stat] = val

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
        # Weather is re-applied every tick from forecast_schedule/override
        # (world_template ships a baked snowy gale), which would overwrite the
        # neutral environment above and freeze every exterior character. Clear
        # both so "neutral" actually means neutral.
        world.forecast_override = None
        sched = getattr(world, "forecast_schedule", None)
        if isinstance(sched, dict):
            sched["entries"] = []
            sched["current_state"] = "clear"
            sched["transition_table"] = {}
        world._forecast_sched_obj = None

    start_vitals = {name: dict(p.vitals) for name, p in players.items()}
    deaths = []
    dead_seen = set()
    cause_counts = {}

    # --- experiment banner ---
    say("=" * 72)
    say("SOAK RUN")
    say(f"  scenario        : {scenario_path.relative_to(ROOT)}")
    say(f"  characters      : {len(players)}")
    say(f"  horizon         : {args.ticks} ticks = {fmt_span(args.ticks, minutes_per_tick)} game time"
        f" ({minutes_per_tick} min/tick)")
    say(f"  engine decay    : {'on (baked rates dropped)' if args.engine_decay else 'off (scenario rates)'}")
    if overrides:
        say(f"  decay overrides : {overrides}")
    if set_vitals:
        say(f"  starting vitals : {set_vitals}")
    if trait_spec:
        say(f"  traits applied  : {trait_spec}")
    say(f"  environment     : {'NEUTRAL (forced 20C/fresh/quiet)' if args.neutral_environment else 'as authored'}")
    if args.background_all:
        say("  fidelity        : ALL background (deterministic survival runner, no LLM)")
    say(f"  seed            : {args.seed}")
    say(f"  progress every  : {args.progress_seconds:g}s / {args.progress} ticks"
        if (args.progress or args.progress_seconds) else "  progress        : off")
    say("=" * 72)

    t0 = time.perf_counter()
    last_report = t0
    last_tick = 0
    deaths_at_last = 0
    prev_hp = {name: p.vitals.get("HP") for name, p in players.items()}
    # 0 means "off" for each channel; don't coerce to 1 or it prints every tick.
    progress_ticks = args.progress if args.progress > 0 else args.ticks + 1
    progress_secs = max(args.progress_seconds, 0.0)
    progress_on = bool(args.progress or args.progress_seconds)

    for i in range(1, args.ticks + 1):
        world.tick_turn()

        for name, p in players.items():
            if name in dead_seen:
                continue
            if p.state == "dead":
                dead_seen.add(name)
                cause = infer_cause(p)
                cause_counts[cause] = cause_counts.get(cause, 0) + 1
                deaths.append({
                    "name": name,
                    "tick": i,
                    "game_span": fmt_span(i, minutes_per_tick),
                    "area": getattr(p, "current_area", None),
                    "cause": cause,
                    "hunger": p.vitals.get("Hunger"),
                    "thirst": p.vitals.get("Thirst"),
                    "energy": p.vitals.get("Energy"),
                    "tags": list(p.tags or []),
                })

        if args.debug_hp:
            for name, p in players.items():
                hp = p.vitals.get("HP")
                before = prev_hp.get(name)
                if before is not None and hp is not None and hp < before:
                    node = (world.graph.get_node(world.area_node_id(p.current_area))
                            if p.current_area else None)
                    env = node.properties.get("environment") if node else None
                    conds = list((getattr(p, "conditions", None) or {}).keys())
                    say(f"  [hp] t={i} {name} {before}->{hp} (-{before - hp})  "
                        f"temp={p.vitals.get('Temperature')} area={p.current_area} "
                        f"cond={conds} env={env}")
                prev_hp[name] = hp

        if progress_on and (i - last_tick >= progress_ticks
                            or (progress_secs and time.perf_counter() - last_report >= progress_secs)):
            now = time.perf_counter()
            elapsed = now - t0
            inst_rate = (i - last_tick) / max(now - last_report, 1e-9)
            avg_rate = i / max(elapsed, 1e-9)
            eta = (args.ticks - i) / max(avg_rate, 1e-9)
            new_deaths = len(deaths) - deaths_at_last
            death_note = f" (+{new_deaths} now, {cause_counts})" if new_deaths else ""
            say(f"{progress_bar(i / args.ticks)} {100 * i / args.ticks:5.1f}%  "
                f"tick {i:>7}/{args.ticks}  {fmt_span(i, minutes_per_tick):>10}  "
                f"{avg_rate:,.1f} t/s (now {inst_rate:,.1f})  "
                f"elapsed {human_duration(elapsed)}  ETA {human_duration(eta)}  "
                f"alive {len(players) - len(dead_seen):>3} dead {len(dead_seen):>3}{death_note}")
            last_tick = i
            last_report = now
            deaths_at_last = len(deaths)

    wall = time.perf_counter() - t0
    ticks_per_sec = args.ticks / max(wall, 1e-9)

    # --- survivors + final vitals ---
    survivors = [n for n in players if n not in dead_seen]
    final = {n: dict(players[n].vitals) for n in survivors}

    def stat_of(key, src, fn):
        vals = [src[n][key] for n in src if src[n].get(key) is not None]
        return round(fn(vals), 1) if vals else None

    def proj(ticks):
        return round(ticks / max(ticks_per_sec, 1e-9), 1)

    death_ticks = [d["tick"] for d in deaths]
    summary = {
        "scenario": str(scenario_path.relative_to(ROOT)),
        "ticks": args.ticks,
        "game_span": fmt_span(args.ticks, minutes_per_tick),
        "minutes_per_tick": minutes_per_tick,
        "wall_seconds": round(wall, 2),
        "ticks_per_second": round(ticks_per_sec, 1),
        "projected_wall_seconds": {
            "1day": proj(1 * TICKS_PER_DAY),
            "1week": proj(7 * TICKS_PER_DAY),
            "1month": proj(30 * TICKS_PER_DAY),
        },
        "characters": len(players),
        "deaths": len(deaths),
        "survivors": len(survivors),
        "causes": cause_counts,
        "death_ticks": {
            "first": min(death_ticks) if death_ticks else None,
            "median": int(statistics.median(death_ticks)) if death_ticks else None,
            "last": max(death_ticks) if death_ticks else None,
        },
        "game_log_entries": len(getattr(world, "game_log", []) or []),
        "turn_events": len(getattr(world, "turn_events", []) or []),
        "delayed_events": len(getattr(world, "delayed_events", []) or []),
        "graph_nodes": len(world.graph.nodes),
        "total_memories": sum(len(getattr(p, "memories", []) or []) for p in players.values()),
        "total_trace": sum(len(getattr(p, "trace_log", []) or []) for p in players.values()),
        "survivor_vitals": {
            k: {
                "avg": stat_of(k, final, statistics.mean),
                "min": stat_of(k, final, min),
                "max": stat_of(k, final, max),
            }
            for k in ("Hunger", "Thirst", "Energy", "HP", "Social", "Hygiene", "Sanity", "Entertainment")
        },
    }

    say("")
    say("=" * 72)
    say("SOAK RESULT")
    say("=" * 72)
    say(f"  ran             : {args.ticks} ticks ({summary['game_span']}) in {human_duration(wall)}"
        f"  ->  {ticks_per_sec:,.1f} ticks/s")
    say(f"  projected cost  : 1 day {human_duration(summary['projected_wall_seconds']['1day'])}"
        f" | 1 week {human_duration(summary['projected_wall_seconds']['1week'])}"
        f" | 1 month {human_duration(summary['projected_wall_seconds']['1month'])}")
    say(f"  survival        : {summary['survivors']}/{summary['characters']} alive,"
        f" {summary['deaths']} dead  {cause_counts if cause_counts else ''}")
    if death_ticks:
        say(f"  death times     : first {fmt_span(min(death_ticks), minutes_per_tick)}"
            f" | median {fmt_span(int(statistics.median(death_ticks)), minutes_per_tick)}"
            f" | last {fmt_span(max(death_ticks), minutes_per_tick)}")
    say(f"  growth          : log {summary['game_log_entries']:,} |"
        f" turn_events {summary['turn_events']:,} | delayed {summary['delayed_events']:,} |"
        f" graph {summary['graph_nodes']:,} | memories {summary['total_memories']:,} |"
        f" trace {summary['total_trace']:,}")

    if deaths:
        say("")
        say("  deaths (first 12):")
        for d in deaths[:12]:
            say(f"    {d['game_span']:>10}  {d['name']:<22} {d['cause']:<12} "
                f"H={d['hunger']} T={d['thirst']} E={d['energy']} @ {d['area']}")

    if survivors:
        say("")
        say("  survivor vitals (avg / min / max):")
        for k, v in summary["survivor_vitals"].items():
            if v["avg"] is not None:
                say(f"    {k:<14} {v['avg']:>6} / {v['min']:>6} / {v['max']:>6}")

    if args.report:
        out = ROOT / args.report
        out.write_text(json.dumps({"summary": summary, "deaths": deaths}, indent=2), encoding="utf-8")
        say(f"\n[soak] report written to {out}")


if __name__ == "__main__":
    main()
