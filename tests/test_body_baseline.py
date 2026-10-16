"""Sensitivity baselines are authorable state (task-848).

`PUT /api/players/<name>/body` writes `player.body_state[region]`
— the same value `pleasure_actions` reads. Injury stays unwritable:
wounds are sim state owned by combat/medicine.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player


def _client():
    from app import create_app
    app = create_app({"TESTING": True})
    app.world.add_player(Player("Baseline Probe"))
    return app.test_client(), app.world


def test_valid_write_persists_and_pleasure_reads_it():
    """The mechanism: the route writes body_state, the consumer reads it."""
    client, world = _client()
    resp = client.put("/api/players/Baseline Probe/body",
                      json={"sensitivity": {"nipple_left": 0.95}})
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json() == {"sensitivity": {"nipple_left": 0.95}}
    player = world.players["Baseline Probe"]
    assert player.body_state["nipple_left"]["sensitivity"] == 0.95


def test_unknown_region_is_rejected():
    """The catalog is the vocabulary — no invented regions."""
    client, _ = _client()
    resp = client.put("/api/players/Baseline Probe/body",
                      json={"sensitivity": {"third_arm": 0.5}})
    assert resp.status_code == 400, resp.get_json()
    assert "third_arm" in resp.get_json()["error"]


def test_out_of_range_is_rejected():
    """Sensitivity is 0..1; anything else is a 400, not a clamp."""
    client, world = _client()
    before = world.players["Baseline Probe"].body_state["torso"]["sensitivity"]
    for bad in (-0.1, 1.5, "a lot"):
        resp = client.put("/api/players/Baseline Probe/body",
                          json={"sensitivity": {"torso": bad}})
        assert resp.status_code == 400, (bad, resp.get_json())
    assert world.players["Baseline Probe"].body_state["torso"]["sensitivity"] == before


def test_unknown_player_is_404():
    """No such player, no write."""
    client, _ = _client()
    resp = client.put("/api/players/Nobody Here/body",
                      json={"sensitivity": {"torso": 0.5}})
    assert resp.status_code == 404


def test_seeded_wound_is_the_same_instance_combat_makes():
    """Authoring a broken leg goes through add_condition — speed,
    symptoms and healing all work because nothing was bypassed."""
    client, world = _client()
    resp = client.put("/api/players/Baseline Probe/body",
                      json={"injuries": [{"region": "leg_left", "level": 2}]})
    assert resp.status_code == 200, resp.get_json()
    player = world.players["Baseline Probe"]
    wounds = [c for c in player.conditions.get("injured", [])
              if c.get("body_part") == "leg_left"]
    assert len(wounds) == 1 and wounds[0].get("level") == 2, wounds


def test_seeded_wound_with_bleeding():
    """Bleeding rides along when asked."""
    client, world = _client()
    resp = client.put("/api/players/Baseline Probe/body",
                      json={"injuries": [{"region": "arm_right", "level": 3,
                                          "bleeding": True}]})
    assert resp.status_code == 200, resp.get_json()
    player = world.players["Baseline Probe"]
    assert any(c.get("body_part") == "arm_right"
               for c in player.conditions.get("bleeding", []))


def test_bad_wounds_are_rejected_and_write_nothing():
    """Unknown region or level outside 1..3 is a 400 with no instances."""
    client, world = _client()
    for bad in ({"region": "third_arm", "level": 2},
                {"region": "leg_left", "level": 9},
                {"region": "leg_left", "level": "a lot"}):
        resp = client.put("/api/players/Baseline Probe/body",
                          json={"injuries": [bad]})
        assert resp.status_code == 400, (bad, resp.get_json())
    player = world.players["Baseline Probe"]
    assert player.conditions.get("injured", []) == []
    assert player.conditions.get("bleeding", []) == []


def test_missing_marks_absence_as_a_condition():
    """A missing part is the mechanical fact of absence — same store,
    same readers, no parallel injury model."""
    client, world = _client()
    resp = client.put("/api/players/Baseline Probe/body",
                      json={"missing": ["hand_left"]})
    assert resp.status_code == 200, resp.get_json()
    player = world.players["Baseline Probe"]
    assert any(c.get("body_part") == "hand_left"
               for c in player.conditions.get("missing", []))
    resp = client.put("/api/players/Baseline Probe/body",
                      json={"missing": ["third_arm"]})
    assert resp.status_code == 400
