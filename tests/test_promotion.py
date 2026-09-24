"""Promotion/demotion memory bridge (task-399).

Covers the handoff acceptance criteria: activation consolidates a background
span into exactly one bounded ``source: "background"`` memory, repeated
activation never duplicates it, foreground actions are never summarized as
background, and the consolidation marks survive save/load.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player
from engine import promotion, trace as trace_mod


class _GS:
    """Minimal game-state stub: the two clock fields the bridge reads."""

    def __init__(self, tick=0, minutes=1):
        self.time_ticks = tick
        self.time_per_tick_minutes = minutes


def _player(area="Chief's Pit"):
    p = Player("Gribba")
    p.current_area = area
    return p


def _bg(p, gs, kind="act", what="worked", why="schedule:work"):
    trace_mod.record(p, gs.time_ticks, kind, what, why=why, area=p.current_area)


def _bg_memories(p):
    return [m for m in p.memories if m.get("source") == "background"]


# ───────────────────────────── offload ────────────────────────────────────

def test_offload_demotes_and_stamps_the_boundary():
    p, gs = _player(), _GS(tick=100)
    assert promotion.offload(gs, p) is True
    assert p.simulation_mode == "background"
    assert p.last_offload_tick == 100


def test_offloading_an_already_background_character_is_a_noop():
    p, gs = _player(), _GS(tick=100)
    promotion.offload(gs, p)
    assert promotion.offload(gs, p) is False


# ───────────────────────────── promotion ──────────────────────────────────

def test_promoting_an_attended_character_does_nothing():
    p, gs = _player(), _GS(tick=100)
    assert promotion.promote(gs, p) is None
    assert _bg_memories(p) == []


def test_promotion_writes_one_bounded_background_memory():
    p, gs = _player(), _GS(tick=10)
    promotion.offload(gs, p)

    gs.time_ticks = 40
    _bg(p, gs, what="worked", why="schedule:work")
    gs.time_ticks = 45
    _bg(p, gs, kind="move", what="travelled", why="needs:hunger")
    gs.time_ticks = 70

    text = promotion.promote(gs, p)
    assert p.simulation_mode == "active"
    memories = _bg_memories(p)
    assert len(memories) == 1
    assert memories[0]["text"] == text
    assert len(text) <= promotion.MEMORY_CHAR_LIMIT
    assert "routine" in text and "work" in text


def test_repeated_promotion_does_not_duplicate_the_memory():
    p, gs = _player(), _GS(tick=10)
    promotion.offload(gs, p)
    gs.time_ticks = 30
    _bg(p, gs)
    promotion.promote(gs, p)

    assert promotion.promote(gs, p) is None
    assert len(_bg_memories(p)) == 1


def test_a_second_span_adds_exactly_one_more_memory():
    p, gs = _player(), _GS(tick=10)
    promotion.offload(gs, p)
    gs.time_ticks = 20
    _bg(p, gs, what="worked", why="schedule:work")
    promotion.promote(gs, p)

    assert promotion.offload(gs, p) is True
    gs.time_ticks = 40
    _bg(p, gs, what="slept", why="needs:energy")
    promotion.promote(gs, p)

    assert len(_bg_memories(p)) == 2


def test_foreground_actions_are_never_summarized_as_background():
    p, gs = _player(), _GS(tick=10)
    promotion.offload(gs, p)
    gs.time_ticks = 20
    _bg(p, gs, what="worked", why="schedule:work")
    promotion.promote(gs, p)

    # A foreground action between the two spans.
    gs.time_ticks = 40
    trace_mod.record(p, gs.time_ticks, "plan", "FOREGROUND_MARKER",
                     why="goal:plan", area=p.current_area)

    promotion.offload(gs, p)
    gs.time_ticks = 60
    _bg(p, gs, what="slept", why="needs:energy")
    gs.time_ticks = 70
    text = promotion.promote(gs, p)

    assert "FOREGROUND_MARKER" not in text
    assert "FOREGROUND_MARKER" not in " ".join(
        m["text"] for m in _bg_memories(p))
    assert len(_bg_memories(p)) == 2


def test_an_empty_span_writes_no_memory_but_still_promotes():
    p, gs = _player(), _GS(tick=10)
    promotion.offload(gs, p)
    gs.time_ticks = 25
    assert promotion.promote(gs, p) is None
    assert p.simulation_mode == "active"
    assert _bg_memories(p) == []


# ───────────────────────────── invariants ─────────────────────────────────

def test_the_summary_is_deterministic_for_a_fixed_span():
    entries = [
        {"t": 11, "kind": "act", "what": "ate", "why": "needs:hunger",
         "salient": False, "area": "Camp"},
        {"t": 12, "kind": "move", "what": "moved", "why": "needs:drink",
         "salient": False, "area": "Camp"},
    ]
    gs = _GS()
    assert (promotion.summarize(gs, entries, since_tick=10, end_tick=20)
            == promotion.summarize(gs, entries, since_tick=10, end_tick=20))


def test_consolidation_marks_survive_serialization():
    p, gs = _player(), _GS(tick=10)
    promotion.offload(gs, p)
    gs.time_ticks = 20
    _bg(p, gs)
    promotion.promote(gs, p)

    data = p.to_dict()
    assert data["last_offload_tick"] == 10
    assert data["background_consolidated_through"] == 20


def test_a_reloaded_player_does_not_double_consolidate():
    p, gs = _player(), _GS(tick=10)
    promotion.offload(gs, p)
    gs.time_ticks = 20
    _bg(p, gs)
    promotion.promote(gs, p)
    assert len(_bg_memories(p)) == 1

    # Reload the marks *and the trace* onto a fresh player and promote again:
    # the span is already consolidated, so no second memory is written.
    payload = p.to_dict()
    reloaded = _player()
    reloaded.last_offload_tick = payload["last_offload_tick"]
    reloaded.background_consolidated_through = payload["background_consolidated_through"]
    trace_mod.load(reloaded, payload["trace"])
    reloaded.simulation_mode = "background"
    gs.time_ticks = 25
    assert promotion.promote(gs, reloaded) is None
