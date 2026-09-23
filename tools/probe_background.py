#!/usr/bin/env python3
"""probe_background.py — inspect the background survival runner.

Unlike the soak (a long endurance run), this is a short, chatty diagnostic:
it says what it is doing at each step and prints the intermediate numbers, so
you can see *why* a long run behaves the way it does.

What it prints:
  1. CONFIG   — scenario, tick count, how many are in background fidelity.
  2. REACH    — per character: area, whether the area is itself water, and the
                nearest drink target the navigator finds (area + exit label).
  3. RUN      — ticks forward with progress (alive / thirst median).
  4. REPORT   — survival, thirst & hunger spread, what the runner actually did
                (trace reason histogram), and how many food/drink items remain.

Usage:
    python tools/probe_background.py
    python tools/probe_background.py --ticks 2880 --scenario data/scenarios/x.json
"""

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from virtual_world_engine import VirtualWorld  # noqa: E402
from engine.background_simulation import (  # noqa: E402
    BackgroundSimulation, DRINK_TAGS, FOOD_TAGS,
)


def say(msg):
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser(description="Background-survival probe")
    ap.add_argument("--scenario", default="data/scenarios/kraktooth_goblin_camp.json")
    ap.add_argument("--ticks", type=int, default=1500)
    ap.add_argument("--progress", type=int, default=300)
    args = ap.parse_args()

    path = ROOT / args.scenario
    world = VirtualWorld()
    world.load_from_dict(json.loads(path.read_text(encoding="utf-8-sig")))
    for p in world.players.values():
        p.decay_rates = {}
        p.simulation_mode = "background"
        p.next_due_tick = 0
    sim = BackgroundSimulation(world)

    say("=" * 72)
    say("BACKGROUND PROBE")
    say(f"  scenario : {args.scenario}")
    say(f"  ticks    : {args.ticks} ({args.ticks} game minutes)")
    say(f"  players  : {len(world.players)} (all forced to background)")
    say("=" * 72)

    say("\n1) REACHABILITY (nearest drink target per character)")
    for name, p in list(world.players.items()):
        step = sim._target_step(p, DRINK_TAGS)
        say(f"   {name:<26} {str(p.current_area):<24} "
            f"in_water={str(sim._in_water_area(p)):<5} drink_to={step}")

    say(f"\n2) RUNNING {args.ticks} ticks...")
    t0 = time.perf_counter()
    for i in range(1, args.ticks + 1):
        world.tick_turn()
        if args.progress and i % args.progress == 0:
            alive = [p for p in world.players.values() if p.state != "dead"]
            thirst = [p.vitals.get("Thirst", 0) for p in alive]
            rate = i / max(time.perf_counter() - t0, 1e-9)
            say(f"   t={i:>6} alive={len(alive):>3}/{len(world.players)} "
                f"thirst_med={int(statistics.median(thirst)) if thirst else '-'} "
                f"{rate:,.1f} ticks/s")

    alive = [p for p in world.players.values() if p.state != "dead"]
    dead = [p for p in world.players.values() if p.state == "dead"]

    def spread(stat):
        vals = sorted(p.vitals.get(stat, 0) for p in alive)
        if not vals:
            return "-"
        return f"min={vals[0]} median={int(statistics.median(vals))} max={vals[-1]}"

    counts = Counter()
    for p in world.players.values():
        for e in p.trace_log:
            counts[(e["kind"], e["why"])] += 1

    remaining = Counter()
    for node in world.graph.nodes.values():
        tags = {str(t).lower() for t in (node.properties.get("tags") or [])}
        if tags & set(FOOD_TAGS):
            remaining["food"] += 1
        if tags & set(DRINK_TAGS):
            remaining["drink"] += 1

    say("\n3) REPORT")
    say(f"   survival     : {len(alive)}/{len(world.players)} alive"
        + (f", {len(dead)} dead" if dead else ""))
    say(f"   thirst       : {spread('Thirst')}")
    say(f"   hunger       : {spread('Hunger')}")
    say(f"   energy       : {spread('Energy')}")
    say(f"   consumables  : {dict(remaining)}")
    say(f"   trace by kind/why:")
    for key, n in counts.most_common(12):
        say(f"     {key[0]:<10} {key[1] or '(none)':<16} {n}")
    say("=" * 72)


if __name__ == "__main__":
    main()
