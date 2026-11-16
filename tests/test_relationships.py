"""One relationship mutation path (task-420).

Relationship state was written from combat, first-meeting registration, the
foreground loop and the `label` command, each touching the dict itself. Two
consequences: no *cause* was recorded (a beating looked like a shared meal), and
the two fidelity tiers could disagree about how the same scalar evolves  -  so at a
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
    ATTRACTION_MAX,
    ATTRACTION_MIN,
    BAND_ORDER,
    CLOSENESS_MAX,
    CLOSENESS_MIN,
    FEAR_MAX,
    FEAR_MIN,
    RELATIONSHIP_AXES,
    RESENTMENT_MAX,
    RESENTMENT_MIN,
    TRUST_MAX,
    TRUST_MIN,
    apply_relationship_axes_delta,
    apply_relationship_delta,
    apply_symmetric_delta,
    band_at_least,
    clamp_axis,
    clamp_closeness,
    closeness_band,
    describe,
    ensure_relationship,
    get_relationship_axes,
    get_relationship_axis,
    normalize_relationship,
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

    entry = a.lived_log[-1]
    assert entry["kind"] == "relationship"
    assert entry["why"] == "social:combat"
    assert entry["area"] == "Training Pit"
    assert entry["delta"]["closeness"] == -30
    assert entry["delta"]["cause"] == "combat"
    assert entry["delta"]["with"] == "Vekka"
    assert "rel:Vekka" in entry["tags"]


def test_a_zero_delta_still_stamps_the_interaction_but_writes_no_trace():
    a, _ = _pair(10)
    before = len(a.lived_log)
    apply_relationship_delta(a, "Vekka", 0, "meeting", tick=7)
    assert a.relationships["Vekka"]["last_interaction_tick"] == 7
    assert a.relationships["Vekka"]["interaction_count"] == 1
    assert len(a.lived_log) == before


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
    assert a.lived_log[-1]["delta"]["with"] == "Vekka"
    assert b.lived_log[-1]["delta"]["with"] == "Rikka"


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
    """The 'psychotic friend' case at engine/combat.py  -  regression."""
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
#: from an incoming payload (a savegame or a PUT import)  -  that is
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

def test_rename_player_rekeys_relationships_across_all_players():
    """task-619: renaming character A updates character B's relationship key to A."""
    from engine.player_manager import PlayerManager
    from graph import WorldGraph

    g = WorldGraph()
    pm = PlayerManager(g)
    alice = Player("Alice")
    bob = Player("Bob")
    pm.add_player(alice)
    pm.add_player(bob)

    # Establish relationship from Bob -> Alice
    apply_relationship_delta(bob, "Alice", 25, cause="meeting")
    assert bob.relationships["Alice"]["closeness"] == 25

    # Rename Alice -> Alicia
    pm.rename_player("Alice", "Alicia")

    # Verify Bob's relationship is re-keyed to Alicia with preserved closeness
    assert "Alice" not in bob.relationships
    assert "Alicia" in bob.relationships
    assert bob.relationships["Alicia"]["closeness"] == 25
    assert bob.relationships["Alicia"]["name"] == "Alicia"


# -- multi-axis relationships (task-972) -----------------------------------


def test_ensure_relationship_initializes_all_axes_to_zero():
    a = Player("Rikka")
    rel, created = ensure_relationship(a, "Vekka", tick=3)
    assert created is True
    for axis in RELATIONSHIP_AXES:
        assert rel[axis] == 0


def test_apply_relationship_axes_delta_updates_and_clamps_all_axes():
    a = Player("Rikka")
    rel = apply_relationship_axes_delta(
        a,
        "Vekka",
        {
            "closeness": 30,
            "trust": -150,
            "attraction": 120,
            "fear": -20,
            "resentment": 45,
            "unknown_axis": 99,
        },
        cause="dialogue",
        tick=12,
        area_id="Plaza",
    )
    assert rel["closeness"] == 30
    assert rel["trust"] == TRUST_MIN
    assert rel["attraction"] == ATTRACTION_MAX
    assert rel["fear"] == FEAR_MIN
    assert rel["resentment"] == 45
    assert "unknown_axis" not in rel
    assert rel["last_interaction_tick"] == 12
    assert rel["interaction_count"] == 1

    entry = a.lived_log[-1]
    assert entry["kind"] == "relationship"
    assert entry["why"] == "social:dialogue"
    assert entry["delta"]["trust"] == -150
    assert entry["delta"]["attraction"] == 120


def test_axis_upper_and_lower_bounds():
    a = Player("Rikka")
    apply_relationship_axes_delta(
        a,
        "Vekka",
        {"closeness": 500, "trust": 500, "attraction": 500, "fear": 500, "resentment": 500},
        cause="test",
        tick=1,
    )
    axes = get_relationship_axes(a, "Vekka")
    assert axes == {
        "closeness": CLOSENESS_MAX,
        "trust": TRUST_MAX,
        "attraction": ATTRACTION_MAX,
        "fear": FEAR_MAX,
        "resentment": RESENTMENT_MAX,
    }

    apply_relationship_axes_delta(
        a,
        "Vekka",
        {"closeness": -999, "trust": -999, "attraction": -999, "fear": -999, "resentment": -999},
        cause="test",
        tick=2,
    )
    axes = get_relationship_axes(a, "Vekka")
    assert axes == {
        "closeness": CLOSENESS_MIN,
        "trust": TRUST_MIN,
        "attraction": ATTRACTION_MIN,
        "fear": FEAR_MIN,
        "resentment": RESENTMENT_MIN,
    }


def test_clamp_axis_handles_invalid_inputs_and_unknown_axis():
    assert clamp_axis("trust", "bad") == 0
    assert clamp_axis("fear", float("nan")) == 0
    assert clamp_axis("attraction", None) == 0
    with pytest.raises(ValueError):
        clamp_axis("nonexistent", 10)


def test_legacy_relationship_dict_backward_compatibility():
    a = Player("Rikka")
    a.relationships["Vekka"] = {
        "closeness": 40,
        "last_interaction_tick": 5,
        "interaction_count": 2,
        "label": "ally",
        "name": "Vekka",
    }
    assert get_relationship_axis(a, "Vekka", "closeness") == 40
    assert get_relationship_axis(a, "Vekka", "trust") == 0
    assert get_relationship_axes(a, "Vekka") == {
        "closeness": 40,
        "trust": 0,
        "attraction": 0,
        "fear": 0,
        "resentment": 0,
    }
    apply_relationship_axes_delta(a, "Vekka", {"trust": 25, "fear": 10}, cause="dialogue", tick=6)
    rel = a.relationships["Vekka"]
    assert rel["closeness"] == 40
    assert rel["trust"] == 25
    assert rel["fear"] == 10
    assert rel["label"] == "ally"


def test_normalize_relationship_preserves_metadata_and_clamps_axes():
    norm = normalize_relationship({
        "closeness": 200,
        "trust": -200,
        "attraction": -5,
        "fear": 30,
        "label": "rival",
        "name": "Vekka",
        "last_interaction_tick": 9,
        "interaction_count": 4,
    })
    assert norm["closeness"] == 100
    assert norm["trust"] == -100
    assert norm["attraction"] == 0
    assert norm["fear"] == 30
    assert norm["resentment"] == 0
    assert norm["label"] == "rival"
    assert norm["last_interaction_tick"] == 9
    assert norm["interaction_count"] == 4


def test_serialization_round_trips_multi_axis_and_legacy_relationships():
    import json
    from engine.player_manager import PlayerManager
    from engine.serialization import WorldSerializer
    from graph import WorldGraph

    g = WorldGraph()
    pm = PlayerManager(g)
    alice = Player("Alice")
    bob = Player("Bob")
    pm.add_player(alice)
    pm.add_player(bob)

    apply_relationship_axes_delta(
        alice,
        "Bob",
        {"closeness": 35, "trust": 50, "attraction": 20, "fear": 5, "resentment": 10},
        cause="dialogue",
        tick=8,
    )
    # Legacy record on Bob -> Alice (missing new axes)
    bob.relationships["Alice"] = {
        "closeness": 15,
        "last_interaction_tick": 3,
        "interaction_count": 1,
        "label": "neighbor",
        "name": "Alice",
    }

    serializer = WorldSerializer(g, pm, None)
    alice_payload = json.loads(json.dumps(serializer._serialize_player("Alice", alice)))
    bob_payload = json.loads(json.dumps(serializer._serialize_player("Bob", bob)))

    g2 = WorldGraph()
    pm2 = PlayerManager(g2)
    serializer2 = WorldSerializer(g2, pm2, None)
    alice2 = serializer2._deserialize_player("Alice", alice_payload)
    bob2 = serializer2._deserialize_player("Bob", bob_payload)

    assert alice2.relationships["Bob"]["closeness"] == 35
    assert alice2.relationships["Bob"]["trust"] == 50
    assert alice2.relationships["Bob"]["attraction"] == 20
    assert alice2.relationships["Bob"]["fear"] == 5
    assert alice2.relationships["Bob"]["resentment"] == 10

    assert bob2.relationships["Alice"]["closeness"] == 15
    assert bob2.relationships["Alice"]["trust"] == 0
    assert bob2.relationships["Alice"]["attraction"] == 0
    assert bob2.relationships["Alice"]["fear"] == 0
    assert bob2.relationships["Alice"]["resentment"] == 0
    assert bob2.relationships["Alice"]["label"] == "neighbor"


