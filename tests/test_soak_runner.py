"""Tests for the shared headless soak engine (engine/soak_runner.py).

These run real ticks against tiny scenarios, so every test is short-horizon.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import soak_runner as sr

SMALL = "data/scenarios/combat_pit.json"


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
    assert all(not p.startswith("data/scenarios/autosave") for p in paths)
