"""Tests for the shared headless soak engine (engine/soak_runner.py).

These run real ticks against tiny scenarios, so every test is short-horizon.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import soak_runner as sr

SMALL = "data/scenarios/combat_pit.json"
# A scenario with a real cast that makes background decisions. Loading it is
# heavier than SMALL, so it is used only where a test needs actual decisions.
CAMP = "data/scenarios/kraktooth_goblin_camp.json"


def _config(**over):
    base = {"scenario": SMALL, "ticks": 12, "sample_every": 4}
    base.update(over)
    return sr.SoakConfig.from_dict(base)


def _drain_registry():
    for run in list(sr._RUNS.values()):
        run.cancel()
    deadline = time.time() + 20
    while sr.active_run() and time.time() < deadline:
        time.sleep(0.02)
    for rid in list(sr._RUNS.keys()):
        try:
            sr.remove_run(rid)
        except RuntimeError:
            pass


# ─────────────────────────── helpers ───────────────────────────

def test_parse_kv_pairs_accepts_strings_and_mappings():
    assert sr.parse_kv_pairs("Energy=0,Thirst=1.5,label=hi") == {
        "Energy": 0.0, "Thirst": 1.5, "label": "hi"}
    assert sr.parse_kv_pairs({"a": 1, "b": "x"}) == {"a": 1, "b": "x"}
    assert sr.parse_kv_pairs("") == {}


def test_parse_kv_pairs_rejects_bad_chunk():
    try:
        sr.parse_kv_pairs("just-a-word")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_time_math():
    assert sr.ticks_per_day(1) == 1440
    assert sr.ticks_per_day(15) == 96
    assert sr.fmt_span(96, 15) == "1d00h00m"
    assert sr.fmt_span(0, 1) == "0d00h00m"
    assert sr.human_duration(0) == "0s"
    assert sr.human_duration(3661) == "1h01m01s"
    assert sr.progress_bar(0.5, 10) == "[#####.....]"


def test_resolve_scenario_rejects_escape_and_missing():
    for bad in ("../outside.json", "data/scenarios/does_not_exist.json"):
        try:
            sr.resolve_scenario(bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} should be rejected")
    assert sr.resolve_scenario(SMALL).name == "combat_pit.json"


# ─────────────────────────── run lifecycle ───────────────────────────

def test_short_run_produces_report_samples_and_exports():
    run = sr.SoakRun(_config())
    summary = run.execute()

    assert run.status == sr.STATUS_FINISHED
    assert summary["ticks_completed"] == 12
    assert summary["characters"] >= 1
    assert summary["deaths"] + summary["survivors"] == summary["characters"]
    if summary["survivors"]:
        assert summary["survivor_vitals"]
    assert summary["sample_count"] == len(run.samples()) >= 1
    # Samples carry aggregate vitals + growth for the charts.
    first = run.samples()[0]
    assert first["tick"] == 4
    assert "vitals" in first and "growth" in first
    # Character drill-down series were recorded.
    name = run.characters[0]["name"]
    series = run.character_series(name)
    assert series and len(series["ticks"]) == len(run.samples())
    assert any(len(v) == len(run.samples()) for v in series["series"].values())

    for kind in ("samples", "deaths", "characters", "growth"):
        text = run.export_csv(kind)
        assert text.strip()
        assert "," in text.splitlines()[0]

    report = run.report()
    assert report["summary"]["ticks_completed"] == 12
    assert report["config"]["scenario"] == SMALL
    assert "samples" not in report
    assert len(run.report(include_samples=True)["samples"]) == len(run.samples())


def test_config_parsing_of_run_wide_overrides():
    cfg = _config(engine_decay=True, decay_overrides="Energy=0",
                  starting_vitals="Thirst=0", traits="goblin=high_metabolism",
                  mature=True, neutral_environment=True, minutes_per_tick=15,
                  seed=7)
    assert cfg.engine_decay is True
    assert cfg.decay_overrides == {"Energy": 0.0}
    assert cfg.starting_vitals == {"Thirst": 0.0}
    assert cfg.traits == {"goblin": "high_metabolism"}
    assert cfg.minutes_per_tick == 15.0
    assert cfg.seed == 7


def test_registry_allows_only_one_active_run():
    _drain_registry()
    first = sr.start_run(_config(ticks=200000))
    try:
        assert sr.active_run() is first
        try:
            sr.start_run(_config())
        except RuntimeError:
            pass
        else:
            raise AssertionError("second concurrent run should be rejected")
        first.cancel()
        deadline = time.time() + 20
        while first.status not in sr.TERMINAL and time.time() < deadline:
            time.sleep(0.02)
        assert first.status in (sr.STATUS_STOPPED, sr.STATUS_FINISHED)
        assert first.summary is not None
        assert sr.list_runs()
        assert sr.remove_run(first.id) is True
        assert sr.get_run(first.id) is None
    finally:
        _drain_registry()


def test_restores_global_rng_after_run():
    import random as _random
    _random.seed(999)
    before = _random.random()
    _random.seed(999)
    sr.SoakRun(_config()).execute()
    assert _random.random() == before


def test_list_scenarios_includes_template_and_scenarios():
    scenarios = sr.list_scenarios()
    paths = {s["path"] for s in scenarios}
    assert SMALL in paths
    assert "world_template.json" in paths


# ─────────────────── telemetry integration (task-543) ───────────────────

def test_a_run_records_telemetry_the_dashboard_can_draw():
    run = sr.SoakRun(_config(telemetry=True))
    run.execute()
    payload = run.telemetry_payload()

    assert payload["enabled"] is True
    assert payload["counts"]["intervals"] > 0
    assert payload["characters"] and payload["areas"]
    # The whole point of the store: presence is knowable.
    assert payload["integrity_ok"], payload["integrity"]
    assert payload["integrity"]["gaps"] == 0
    assert payload["integrity"]["overlaps"] == 0
    # And the vocabulary closed over a real run, with nothing rejected.
    assert payload["rejected_events"] == 0, payload["rejected_why"]
    for row in payload["why"]:
        assert 0 < row["share"] <= 1


def test_telemetry_intervals_cover_the_run_with_no_gaps():
    run = sr.SoakRun(_config(telemetry=True))
    run.execute()
    intervals = run.telemetry_payload()["intervals"]
    by_character = {}
    for interval in intervals:
        by_character.setdefault(interval["character"], []).append(interval)
    assert by_character
    for character, group in by_character.items():
        group.sort(key=lambda iv: iv["from_tick"])
        assert group[0]["from_tick"] == 0, f"{character} has no opening interval"
        for prev, nxt in zip(group, group[1:]):
            assert nxt["from_tick"] == prev["to_tick"], f"{character} has a gap"
        assert group[-1]["to_tick"] == run.tick


def test_interval_count_tracks_moves_not_run_length():
    """Two runs of very different length, same cast: the short one must not
    simply have proportionally fewer intervals just because it ran fewer ticks."""
    short = sr.SoakRun(_config(ticks=6, telemetry=True))
    short.execute()
    long = sr.SoakRun(_config(ticks=60, telemetry=True))
    long.execute()
    short_intervals = short.telemetry_payload()["counts"]["intervals"]
    long_intervals = long.telemetry_payload()["counts"]["intervals"]
    assert short_intervals > 0
    # 10x the ticks must not mean 10x the records; it means "more moves".
    assert long_intervals < short_intervals * 10


def test_a_cancelled_run_closes_its_intervals_at_the_tick_it_reached():
    run = sr.SoakRun(_config(ticks=5000, telemetry=True))
    run.start()
    deadline = time.time() + 20
    while run.tick < 3 and time.time() < deadline:
        time.sleep(0.01)
    run.cancel()
    deadline = time.time() + 20
    while run.status not in sr.TERMINAL and time.time() < deadline:
        time.sleep(0.02)
    # Read the reached tick *after* termination: reading it before the cancel
    # lands is a race, and the run keeps ticking until the flag is observed.
    reached = run.tick
    intervals = run.telemetry_payload()["intervals"]
    assert intervals
    # Not at the configured tick count, which the run never reached.
    assert max(iv["to_tick"] for iv in intervals) == reached


def test_telemetry_can_be_switched_off():
    run = sr.SoakRun(_config(telemetry=False))
    run.execute()
    payload = run.telemetry_payload()
    assert payload["enabled"] is False
    assert payload["intervals"] == []


def test_telemetry_is_absent_from_a_save():
    """Run-owned measurement must not leak into the save or onto the player. A
    save taken after a soak round-trips without it."""
    import json
    from virtual_world_engine import VirtualWorld

    with open(sr.ROOT / SMALL, encoding="utf-8-sig") as handle:
        data = json.load(handle)
    world = VirtualWorld()
    world.load_from_dict(data)

    run = sr.SoakRun(_config(telemetry=True))
    run.execute()
    assert run.telemetry_payload()["counts"]["intervals"] > 0

    saved = world.to_dict()
    assert "telemetry" not in saved
    for pdata in saved["players"].values():
        assert "telemetry" not in pdata
    # A scenario payload drops the lived log too — it is runtime history, and
    # keeping it would add 200 entries per character to every scenario file.
    scenario = world.to_scenario_dict()
    for pdata in scenario["players"].values():
        assert "lived_log" not in pdata


def test_the_tap_does_not_change_what_the_lived_log_records():
    """The fan-out must be invisible to the store it taps.

    The naive form of this criterion — "the lived log is unchanged by a soak" —
    is wrong: a soak *does* write lived-log entries, because background
    decisions record into it. The real property is determinism: the same seeded
    run must produce the same lived-log volume whether or not a recorder is
    listening. If the tap ever started mutating, deduplicating or reordering the
    primary write, these two numbers would diverge.

    Uses a scenario that actually makes background decisions — the tiny
    `combat_pit` scenario records none in a short run, so it cannot prove
    anything here.
    """
    def _camp(**over):
        return sr.SoakConfig.from_dict({
            "scenario": CAMP, "ticks": 8, "background_all": True,
            "seed": 4242, "telemetry": True, **over,
        })

    with_tap = sr.SoakRun(_camp())
    with_tap.execute()
    without_tap = sr.SoakRun(_camp(telemetry=False))
    without_tap.execute()

    assert with_tap.telemetry_payload()["counts"]["events"] > 0, \
        "this scenario must make background decisions, or the test proves nothing"
    # `run.growth` is the *initial* growth, captured before any tick; the samples
    # carry the running totals, so the last sample is the "after" reading.
    with_growth = with_tap.samples()[-1]["growth"]
    without_growth = without_tap.samples()[-1]["growth"]
    assert with_growth["total_lived_log"] > 0
    assert with_growth["total_lived_log"] == without_growth["total_lived_log"]


def test_a_soak_does_not_alter_the_scenario_file():
    """The runner loads the scenario and must leave it byte-identical."""
    path = sr.ROOT / SMALL
    original = path.read_bytes()
    sr.SoakRun(_config(telemetry=True)).execute()
    assert path.read_bytes() == original


def test_list_scenarios_excludes_autosave():
    paths = {s["path"] for s in sr.list_scenarios()}
    assert all(not p.startswith("data/scenarios/autosave") for p in paths)

    assert all(not p.startswith("data/scenarios/autosave") for p in paths)
