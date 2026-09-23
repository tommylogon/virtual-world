"""One relationship mutation path (task-420).

Relationship state was written from combat, first-meeting registration, the
foreground loop and the `label` command, each touching the dict itself. Two
consequences: no *cause* was recorded (a beating looked like a shared meal), and
the two fidelity tiers could disagree about how the same scalar evolves — so at a
promotion/demotion the value could jump.

`apply_relationship_delta` is now the only writer of `closeness`. It clamps in
one place, stamps the interaction, and records the cause on the trace.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from player import Player
from engine.relationships import (
    BAND_ORDER,
    CLOSENESS_MAX,
    CLOSENESS_MIN,
    apply_relationship_delta,
    apply_symmetric_delta,
    band_at_least,
    clamp_closeness,
    closeness_band,
    describe,
    ensure_relationship,
)

ROOT = Path(__file__).parent.parent


def _pair(closeness=0):
    a = Player("Rikka")
    b = Player("Vekka")
    if closeness:
        a.relationships["Vekka"] = {"closeness": closeness,
                                    "last_interaction_tick": 0, "interaction_count": 0}
    return a, b


# ── the band ladder is defined once ──────────────────────────────────────


@pytest.mark.parametrize("closeness,band", [
    (-100, "mortal_enemy"), (-75, "mortal_enemy"), (-74, "enemy"),
    (-50, "enemy"), (-49, "rival"), (-25, "rival"), (-24, "unfriendly"),
    (-1, "unfriendly"), (0, "neutral"), (1, "acquaintance"), (25, "acquaintance"),
    (26, "friend"), (50, "friend"), (51, "close_friend"), (75, "close_friend"),
    (76, "inseparable"), (100, "inseparable"),
])
def test_band_boundaries_match_the_prompt_ladder(closeness, band):
    """The ladder used to be inline in Player.get_relationship_nl; the prompt
    wording and any band-gated rule must agree on where the edges are."""
    assert closeness_band(closeness) == band


def test_describe_uses_the_shared_band_ladder():
    a, _ = _pair(60)
    assert "close friend" in describe(a, "Vekka")
    a.relationships["Vekka"]["label"] = "my brother"
    assert "my brother" in describe(a, "Vekka")


def test_band_gates_compare_by_position():
    assert band_at_least(60, "friend")
    assert not band_at_least(60, "inseparable")
    assert band_at_least(-80, "mortal_enemy")
    assert not band_at_least(0, "friend")
    assert BAND_ORDER.index("friend") < BAND_ORDER.index("inseparable")


# ── clamping lives in one place ──────────────────────────────────────────


def test_clamping_is_identical_whatever_the_cause():
    for cause in ("combat", "dialogue", "meeting", "gift"):
        a, _ = _pair(95)
        apply_relationship_delta(a, "Vekka", 50, cause, tick=1)
        assert a.relationships["Vekka"]["closeness"] == CLOSENESS_MAX

        b, _ = _pair(-95)
        apply_relationship_delta(b, "Vekka", -50, cause, tick=1)
        assert b.relationships["Vekka"]["closeness"] == CLOSENESS_MIN


def test_clamp_handles_junk():
    assert clamp_closeness("nonsense") == 0
    assert clamp_closeness(None) == 0
    assert clamp_closeness(1e9) == CLOSENESS_MAX


# ── the cause is recorded ────────────────────────────────────────────────


def test_every_delta_records_its_cause_on_the_trace():
    a, _ = _pair(10)
    apply_relationship_delta(a, "Vekka", -30, "combat", tick=5, area_id="Training Pit")

    entry = a.trace_log[-1]
    assert entry["kind"] == "relationship"
    assert entry["why"] == "social:combat"
    assert entry["area"] == "Training Pit"
    assert entry["delta"]["closeness"] == -30
    assert entry["delta"]["cause"] == "combat"
    assert entry["delta"]["with"] == "Vekka"
    assert "rel:Vekka" in entry["tags"]


def test_a_zero_delta_still_stamps_the_interaction_but_writes_no_trace():
    a, _ = _pair(10)
    before = len(a.trace_log)
    apply_relationship_delta(a, "Vekka", 0, "meeting", tick=7)
    assert a.relationships["Vekka"]["last_interaction_tick"] == 7
    assert a.relationships["Vekka"]["interaction_count"] == 1
    assert len(a.trace_log) == before


def test_the_interaction_stamp_advances():
    a, _ = _pair(0)
    apply_relationship_delta(a, "Vekka", 2, "meeting", tick=10)
    apply_relationship_delta(a, "Vekka", 2, "meeting", tick=25)
    rel = a.relationships["Vekka"]
    assert rel["last_interaction_tick"] == 25
    assert rel["interaction_count"] == 2


# ── symmetry is a property of the call ───────────────────────────────────


def test_a_symmetric_delta_moves_both_sides_by_the_same_amount():
    a, b = _pair(20)
    b.relationships["Rikka"] = {"closeness": 10, "last_interaction_tick": 0,
                                "interaction_count": 0}
    apply_symmetric_delta(a, b, 5, "meeting", tick=3, area_id="Chief's Pit")
    assert a.relationships["Vekka"]["closeness"] == 25
    assert b.relationships["Rikka"]["closeness"] == 15


def test_each_side_gets_its_own_trace_entry():
    a, b = _pair(0)
    apply_symmetric_delta(a, b, 3, "meeting", tick=4)
    assert a.trace_log[-1]["delta"]["with"] == "Vekka"
    assert b.trace_log[-1]["delta"]["with"] == "Rikka"


# ── record creation ──────────────────────────────────────────────────────


def test_ensure_relationship_reports_whether_it_created():
    a = Player("Rikka")
    rel, created = ensure_relationship(a, "Vekka", 0)
    assert created is True and rel["closeness"] == 0
    again, created = ensure_relationship(a, "Vekka", 5)
    assert created is False and again is rel


def test_a_delta_creates_the_record_it_needs():
    a = Player("Rikka")
    apply_relationship_delta(a, "Stranger", -30, "combat", tick=1)
    assert a.relationships["Stranger"]["closeness"] == -30


# ── the refactored callers keep their behaviour ───────────────────────────


def test_combat_betrayal_still_costs_thirty():
    """The 'psychotic friend' case at engine/combat.py — regression."""
    a, b = _pair(0)
    b.relationships["Rikka"] = {"closeness": 50, "last_interaction_tick": 0,
                                "interaction_count": 0}
    apply_relationship_delta(b, "Rikka", -30, "combat", tick=1)
    assert b.relationships["Rikka"]["closeness"] == 20


def test_update_relationship_grants_meeting_entertainment_only_once():
    a = Player("Rikka")
    a.vitals = {"Entertainment": 20}
    a.update_relationship("Vekka", 1, sentiment_change=5)
    first = a.vitals["Entertainment"]
    assert first > 20
    assert a.relationships["Vekka"]["closeness"] == 5

    a.update_relationship("Vekka", 2, sentiment_change=5)
    assert a.vitals["Entertainment"] == first  # no second boost
    assert a.relationships["Vekka"]["closeness"] == 10


def test_register_first_meeting_marks_the_first_sighting():
    a = Player("Rikka")
    assert a.register_first_meeting("Vekka", tick=1) is True
    assert a.relationships["Vekka"]["first_sighting"] is True
    assert a.register_first_meeting("Vekka", tick=2) is False


# ── the doctrine itself: one writer ──────────────────────────────────────


#: Files allowed to assign a whole relationship record. Both replace the store
#: from an incoming payload (a savegame or a PUT import) — that is
#: deserialization, not a relationship *mutation*, and no closeness is computed
#: there. Everything else must go through engine/relationships.py.
_ALLOWED_IMPORT_SITES = {
    "routes/player_ops.py",
}

_ASSIGN = re.compile(r"relationships\[[^\]]*\]\s*=|relationships\.setdefault")


def _assignment_sites():
    sites = {}
    for path in list((ROOT / "engine").rglob("*.py")) + list((ROOT / "routes").rglob("*.py")) + [ROOT / "player.py"]:
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        hits = [i + 1 for i, line in enumerate(text.splitlines()) if _ASSIGN.search(line)]
        if hits:
            sites[rel] = hits
    return sites


def test_relationships_are_written_only_through_the_one_path():
    """task-420: `relationships[...] = ` appears only in the mutation module,
    plus the two documented bulk-import sites."""
    sites = _assignment_sites()
    unexpected = {k: v for k, v in sites.items()
                  if k != "engine/relationships.py" and k not in _ALLOWED_IMPORT_SITES}
    assert unexpected == {}, f"direct relationship writes outside the one path: {unexpected}"
    assert "engine/relationships.py" in sites
    for allowed in _ALLOWED_IMPORT_SITES:
        assert allowed in sites, f"{allowed} no longer imports; drop it from the allowlist"
