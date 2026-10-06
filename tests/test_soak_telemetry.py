"""Soak telemetry (task-543) — the run-owned measurement store.

The assertions here are mostly about the *boundary* and the *vocabulary*, because
those are the two things that fail silently. A leak into the lived log, or an
unknown `why` quietly accepted, produces no error and a wrong dashboard.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import lived_log
from engine.soak_telemetry import (
    UNATTRIBUTED,
    TelemetryRecorder,
    is_valid_why,
    recording,
    summarise,
    why_group,
)
from player import Player


# ── the vocabulary ───────────────────────────────────────────────────────

def test_why_rejects_unknown_prefixes():
    assert is_valid_why("needs:hunger")
    assert is_valid_why("traversal:ok")
    for bad in ("", "hunger", "needs", "mystery:thing", "nonsense"):
        assert not is_valid_why(bad), bad


def test_why_rejects_a_bare_prefix():
    """`plan:` alone is a category with no meaning — an unfinished tag, not an
    intent. Accepting it would put a meaningless slice in the breakdown."""
    assert not is_valid_why("plan:")
    assert not is_valid_why("needs:")


def test_llm_is_excluded_structurally():
    """A soak makes no LLM calls, so `llm:` is impossible rather than rare.
    Keeping it would leave a permanently empty category inviting "why is this
    always zero?" every time someone reads the breakdown."""
    assert not is_valid_why("llm:novel")
    assert not is_valid_why("llm:anything-at-all")


def test_why_group_buckets_and_falls_back():
    assert why_group("plan:patrol") == "plan"
    assert why_group("traversal:blocked") == "traversal"
    assert why_group("") == UNATTRIBUTED
    assert why_group("mystery:thing") == "other"


# ── the boundary ─────────────────────────────────────────────────────────

def test_no_recorder_outside_a_soak_costs_nothing_and_records_nothing():
    p = Player("Gribba")
    lived_log.record(p, 1, "act", "ate", why="needs:hunger")
    assert len(p.lived_log) == 1


def test_telemetry_never_writes_to_the_lived_log():
    """The one-way rule. A leak here would promote a soak character and summarise
    *measurement data* as lived experience."""
    p = Player("Gribba")
    with recording(TelemetryRecorder("run-1")) as rec:
        lived_log.record(p, 1, "act", "ate", why="needs:hunger")
    assert len(p.lived_log) == 1
    assert len(rec.events()) == 1
    assert rec.presence_intervals() == []


def test_the_tap_fires_before_rollup_so_a_lossy_store_cannot_feed_a_lossless_one():
    """The tap is on the write path, so `rollup()` collapsing the lived log is
    invisible to telemetry. If this ever regresses, telemetry quietly becomes
    as lossy as the store it was supposed to replace."""
    p = Player("Gribba")
    n = 249
    with recording(TelemetryRecorder("run-1")) as rec:
        for tick in range(1, n + 1):
            lived_log.record(p, tick, "act", f"routine {tick}", why="plan:patrol")
        lived_log.rollup(p, min_run=5)
    assert len(p.lived_log) < n              # rollup collapsed the runs
    assert len(rec.events()) == n            # telemetry saw every write


def test_a_broken_recorder_cannot_break_a_game_turn():
    class Hostile:
        def action(self, *a, **k):
            raise RuntimeError("telemetry exploded")

    p = Player("Gribba")
    with recording(Hostile()):
        lived_log.record(p, 1, "act", "ate", why="needs:hunger")
    assert len(p.lived_log) == 1


def test_recording_restores_the_previous_recorder():
    outer = TelemetryRecorder("outer")
    inner = TelemetryRecorder("inner")
    p = Player("Gribba")
    with recording(outer):
        with recording(inner):
            lived_log.record(p, 1, "act", "a", why="needs:hunger")
        lived_log.record(p, 2, "act", "b", why="needs:thirst")
    assert len(inner.events()) == 1
    assert len(outer.events()) == 1


# ── presence intervals ───────────────────────────────────────────────────

def test_intervals_are_emitted_on_change_not_per_tick():
    rec = TelemetryRecorder("run-1")
    for tick in range(1, 101):
        rec.observe_area("Jake", "Storehouse", tick)
    assert rec.presence_intervals() == []          # never moved
    rec.observe_area("Jake", "Longhouse", 101)
    intervals = rec.presence_intervals()
    assert intervals == [{"character": "Jake", "area": "Storehouse",
                          "from_tick": 1, "to_tick": 101}]
    rec.close_all(200)
    assert rec.presence_intervals()[-1]["to_tick"] == 200


def test_interval_count_scales_with_moves_not_run_length():
    """The property that makes this cheap: 10,000 ticks of standing still is one
    record, and 10,000 moves is 10,000 records. Per-tick sampling cannot do that."""
    still = TelemetryRecorder("run-still")
    for tick in range(10_000):
        still.observe_area("Still", "Room", tick)
    still.close_all(10_000)
    assert len(still.presence_intervals()) == 1

    mover = TelemetryRecorder("run-move")
    for tick in range(1, 10_000):
        mover.observe_area("Mover", f"Room{tick % 2}", tick)
    mover.close_all(10_000)
    # 9,999 moves -> 9,999 intervals. Same tick count as the character who stood
    # still for the whole run and produced one.
    assert len(mover.presence_intervals()) == 9_999


def test_intervals_tile_the_run_with_no_gaps_or_overlaps():
    rec = TelemetryRecorder("run-1")
    areas = ["A", "B", "C", "B", "A"]
    for tick, area in enumerate(areas):
        rec.observe_area("Jake", area, tick)
    rec.close_all(len(areas))
    report = summarise(rec.presence_intervals())
    assert report["gaps"] == 0
    assert report["overlaps"] == 0
    assert report["intervals"] == len(areas)


def test_summarise_detects_a_gap():
    """A gap means presence is *unknown*, not that nobody was there. The swimlane
    must be able to tell the difference, so the check has to be able to fail."""
    intervals = [
        {"character": "Jake", "area": "A", "from_tick": 0, "to_tick": 10},
        {"character": "Jake", "area": "B", "from_tick": 20, "to_tick": 30},
    ]
    assert summarise(intervals)["gaps"] == 1


def test_a_character_who_never_moves_still_gets_a_band():
    """Seeded at tick 0 by the runner. Without it, "never moved" and "was
    nowhere" are indistinguishable in the view."""
    rec = TelemetryRecorder("run-1")
    rec.observe_area("Still", "Camp", 0)
    rec.close_all(500)
    assert rec.presence_for("Still") == [
        {"character": "Still", "area": "Camp", "from_tick": 0, "to_tick": 500}]


def test_close_character_ends_a_band_at_a_death():
    rec = TelemetryRecorder("run-1")
    rec.observe_area("Doomed", "Pit", 0)
    rec.death("Doomed", 40, "exhaustion", area="Pit")
    rec.close_character("Doomed", 40)
    assert rec.presence_for("Doomed")[0]["to_tick"] == 40


# ── events, aggregation, disk ────────────────────────────────────────────

def test_unknown_why_is_rejected_and_counted_not_fatal():
    rec = TelemetryRecorder("run-1")
    assert rec.action("Jake", 1, "act", "did a thing", why="mystery:thing") is None
    assert rec.rejected_why == {"mystery:thing": 1}
    assert rec.rejected_events == 1
    assert rec.events() == []
    # A bad tag is visible in the breakdown rather than taking down the run.
    assert rec.action("Jake", 2, "act", "ate", why="needs:hunger") is not None


def test_unattributed_is_kept_but_not_ranked():
    rec = TelemetryRecorder("run-1")
    rec.action("Jake", 1, "act", "cost applied", why="")
    rec.action("Jake", 2, "act", "ate", why="needs:hunger")
    ranked = rec.why_breakdown()
    assert [r["group"] for r in ranked] == ["needs"]
    assert ranked[0]["share"] == 1.0        # not diluted by the undecided record
    assert rec.unattributed_count == 1     # but still reported


def test_why_breakdown_ranks_by_prefix_so_rules_compete():
    rec = TelemetryRecorder("run-1")
    rec.action("Jake", 1, "act", "a", why="plan:provision")
    rec.action("Jake", 2, "act", "b", why="plan:patrol")
    rec.action("Jake", 3, "act", "c", why="needs:hunger")
    ranked = rec.why_breakdown()
    assert ranked[0] == {"group": "plan", "count": 2, "share": 0.6667}
    assert ranked[1]["group"] == "needs"


def test_hot_window_truncates_the_oldest_and_says_so():
    rec = TelemetryRecorder("run-1", hot_window=10)
    for tick in range(50):
        rec.action("Jake", tick, "act", "a", why="needs:hunger")
    assert len(rec.events()) == 10
    assert rec.events()[0]["tick"] == 40
    assert rec.to_payload()["truncated_events"] == 40


def test_jsonl_is_written_and_readable_independently_of_memory():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "run.jsonl")
        rec = TelemetryRecorder("run-1", jsonl_path=path)
        rec.observe_area("Jake", "Camp", 0)
        rec.observe_area("Jake", "Trail", 5)
        rec.action("Jake", 5, "move", "went to Trail", why="goal:travel", area="Trail")
        rec.close_all(9)
        rec.close()

        with open(path, encoding="utf-8") as handle:
            lines = [json.loads(line) for line in handle if line.strip()]

        # The file alone must reconstruct presence: an audit must never be gated
        # on what fitted in the recorder's hot window.
        presence = [line for line in lines if line["type"] == "presence"]
        assert len(presence) == 2
        assert presence[0]["area"] == "Camp"
        assert presence[0]["to_tick"] == 5
        assert sum(1 for line in lines if line["type"] != "presence") == 1


def test_payload_carries_everything_the_view_needs():
    rec = TelemetryRecorder("run-1")
    rec.observe_area("Jake", "Camp", 0)
    rec.action("Jake", 1, "act", "ate", why="needs:hunger", area="Camp")
    rec.condition("Jake", 2, "sick", True, area="Camp")
    rec.close_all(3)
    payload = rec.to_payload(include_events=True)
    for key in ("characters", "areas", "intervals", "why", "kinds",
                "unattributed", "counts", "rejected_why"):
        assert key in payload, key
    assert payload["characters"] == ["Jake"]
    assert payload["areas"] == ["Camp"]
    assert payload["kinds"][0]["kind"] == "act"
    assert len(payload["events"]) == 2


def test_field_names_are_words():
    """Field names are read by a dashboard and grepped by a person. `c`/`f`/`t`
    cost nothing to avoid and cost a lot to decode later."""
    rec = TelemetryRecorder("run-1")
    rec.observe_area("Jake", "Camp", 0)
    rec.close_all(3)
    interval = rec.presence_intervals()[0]
    assert set(interval) == {"character", "area", "from_tick", "to_tick"}
