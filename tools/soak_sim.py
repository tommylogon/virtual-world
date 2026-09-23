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

The loop itself lives in ``engine/soak_runner.py`` so the web UI at ``/soak``
runs exactly the same code; this file is the CLI shell (arg parsing, live
progress printing, report writing).

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
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.soak_runner import (  # noqa: E402
    ROOT as RUNNER_ROOT,
    SoakConfig,
    SoakRun,
    human_duration,
    progress_bar,
    resolve_scenario,
    fmt_span,
)


def say(msg, end="\n"):
    """Print immediately — long runs are watched live, not tail-buffered."""
    sys.stdout.write(msg + end)
    sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser(description="VirtualWorld headless soak runner")
    ap.add_argument("--scenario", default="data/scenarios/kraktooth_goblin_camp.json")
    ap.add_argument("--ticks", type=int, default=10080, help="ticks to simulate (10080 = 1 week @ 1min/tick)")
    ap.add_argument("--minutes-per-tick", type=float, default=None,
                    help="override the scenario's time_per_tick_minutes; vitals scale to it, "
                         "so one game week is 10080/N ticks (N=15 -> 672)")
    ap.add_argument("--engine-decay", action="store_true",
                    help="drop each player's baked decay_rates so engine defaults apply")
    ap.add_argument("--override", default="", help="per-player decay overrides, e.g. 'Energy=0,Thirst=0'")
    ap.add_argument("--apply-trait", default="", help="apply a trait by tag, e.g. 'goblin=high_metabolism'")
    ap.add_argument("--set", dest="set_vitals", default="",
                    help="seed every player's starting vitals, e.g. 'Thirst=0,Hunger=0,Energy=100'")
    ap.add_argument("--background-all", action="store_true",
                    help="run every character in background fidelity (deterministic survival runner, no LLM)")
    ap.add_argument("--mature", action="store_true",
                    help="in-memory only: turn mature_content on, which adds the "
                         "Arousal/Stimulation/Pleasure vitals and their decay. The camp "
                         "scenario ships with it off, so without this the soak runs a "
                         "world missing that whole subsystem")
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

    # SoakConfig's field types want real dicts; parse_kv_pairs understands the
    # raw flag strings, so let from_dict normalise them.
    config = SoakConfig.from_dict({
        "scenario": args.scenario,
        "ticks": args.ticks,
        "minutes_per_tick": args.minutes_per_tick,
        "engine_decay": args.engine_decay,
        "decay_overrides": args.override,
        "starting_vitals": args.set_vitals,
        "traits": args.apply_trait,
        "background_all": args.background_all,
        "mature": args.mature,
        "neutral_environment": args.neutral_environment,
        "debug_hp": args.debug_hp,
        "seed": args.seed,
    })
    run = SoakRun(config)

    progress_ticks = args.progress if args.progress > 0 else config.ticks + 1
    progress_secs = max(args.progress_seconds, 0.0)
    progress_on = bool(args.progress or args.progress_seconds)

    state = {"last_tick": 0, "last_report": time.perf_counter(), "banner": False,
             "deaths_at_last": 0}

    def print_banner():
        minutes = run.minutes_per_tick
        say("=" * 72)
        say("SOAK RUN")
        say(f"  scenario        : {resolve_scenario(config.scenario).relative_to(RUNNER_ROOT)}")
        say(f"  characters      : {run.character_count}")
        say(f"  horizon         : {config.ticks} ticks = {fmt_span(config.ticks, minutes)} game time"
            f" ({minutes:g} min/tick)")
        say(f"  engine decay    : {'on (baked rates dropped)' if config.engine_decay else 'off (scenario rates)'}")
        if config.decay_overrides:
            say(f"  decay overrides : {config.decay_overrides}")
        if config.starting_vitals:
            say(f"  starting vitals : {config.starting_vitals}")
        if config.traits:
            say(f"  traits applied  : {config.traits}")
        say(f"  environment     : {'NEUTRAL (forced 20C/fresh/quiet)' if config.neutral_environment else 'as authored'}")
        if config.background_all:
            say("  fidelity        : ALL background (deterministic survival runner, no LLM)")
        say(f"  seed            : {config.seed}")
        say(f"  progress every  : {args.progress_seconds:g}s / {args.progress} ticks"
            if progress_on else "  progress        : off")
        say("=" * 72)

    def on_tick(i):
        if not state["banner"]:
            print_banner()
            state["banner"] = True
        if not progress_on:
            return
        now = time.perf_counter()
        if (i - state["last_tick"] >= progress_ticks
                or (progress_secs and now - state["last_report"] >= progress_secs)):
            new_deaths = len(run.deaths) - state["deaths_at_last"]
            death_note = f" (+{new_deaths} now, {run.deaths_by_cause})" if new_deaths else ""
            say(f"{progress_bar(i / config.ticks)} {100 * i / config.ticks:5.1f}%  "
                f"tick {i:>7}/{config.ticks}  {fmt_span(i, run.minutes_per_tick):>10}  "
                f"{run.ticks_per_second:,.1f} t/s (now {run.instant_tps:,.1f})  "
                f"elapsed {human_duration(run.elapsed_s)}  ETA {human_duration(run.eta_s)}  "
                f"alive {run.alive:>3} dead {run.dead:>3}{death_note}")
            state["last_tick"] = i
            state["last_report"] = now
            state["deaths_at_last"] = len(run.deaths)

    # Ctrl+C asks the loop to stop at the next tick and finalise a partial
    # report, instead of tearing down mid-tick with no summary.
    try:
        signal.signal(signal.SIGINT, lambda *_: run.cancel())
    except (ValueError, AttributeError):
        pass
    run.execute(on_tick=on_tick)
    if not state["banner"]:
        print_banner()

    summary = run.summary
    if not summary:
        say(f"\n[soak] run failed: {run.error}")
        return

    say("")
    say("=" * 72)
    say("SOAK RESULT")
    say("=" * 72)
    say(f"  ran             : {summary['ticks_completed']} ticks ({summary['game_span']})"
        f" in {human_duration(summary['wall_seconds'])}  ->  {summary['ticks_per_second']:,.1f} ticks/s")
    say(f"  projected cost  : 1 day {human_duration(summary['projected_wall_seconds']['1day'])}"
        f" | 1 week {human_duration(summary['projected_wall_seconds']['1week'])}"
        f" | 1 month {human_duration(summary['projected_wall_seconds']['1month'])}")
    say(f"  survival        : {summary['survivors']}/{summary['characters']} alive,"
        f" {summary['deaths']} dead  {summary['causes'] if summary['causes'] else ''}")
    if summary["death_ticks"]["first"] is not None:
        say(f"  death times     : first {fmt_span(summary['death_ticks']['first'], summary['minutes_per_tick'])}"
            f" | median {fmt_span(summary['death_ticks']['median'], summary['minutes_per_tick'])}"
            f" | last {fmt_span(summary['death_ticks']['last'], summary['minutes_per_tick'])}")
    say(f"  growth          : log {summary['game_log_entries']:,} |"
        f" turn_events {summary['turn_events']:,} | delayed {summary['delayed_events']:,} |"
        f" graph {summary['graph_nodes']:,} | memories {summary['total_memories']:,} |"
        f" trace {summary['total_trace']:,}")

    if run.deaths:
        say("")
        say("  deaths (first 12):")
        for d in run.deaths[:12]:
            say(f"    {d['game_span']:>10}  {d['name']:<22} {d['cause']:<12} "
                f"H={d['hunger']} T={d['thirst']} E={d['energy']} @ {d['area']}")

    if summary["survivor_vitals"]:
        say("")
        say("  survivor vitals (avg / min / max):")
        for k, v in summary["survivor_vitals"].items():
            say(f"    {k:<14} {v['avg']:>6} / {v['min']:>6} / {v['max']:>6}")

    if args.report:
        out = ROOT / args.report
        out.write_text(json.dumps({"summary": summary, "deaths": run.deaths}, indent=2), encoding="utf-8")
        say(f"\n[soak] report written to {out}")


if __name__ == "__main__":
    main()
