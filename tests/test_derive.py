"""Tests for the experience-driven relationship derivation (task-350).

Covers the engine/derive reducer (memory -> derived per-person profile), the
Player.felt_toward bridge (recipient-decided feeling -> experience), the
memory-driven `emotions` block, and the alias/handle resolver.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player
from engine.derive import derive_person_profile


def test_no_signal_is_neutral_stranger():
    v = Player("Vera")
    p = derive_person_profile(v, "Rex")
    assert p["role"] == "stranger"
    assert p["consent"] == 0.0
    assert p["_has_signal"] is False


def test_felt_toward_writes_tagged_experience_memory():
    v = Player("Vera")
    assert v.felt_toward("Rex", "uneasy", 7, tick=1) is True
    mem = v.memories[-1]
    assert "rel:Rex" in mem["tags"]
    assert any(t.startswith("fear:") for t in mem["tags"])


def test_uneasy_person_harder_to_grab_than_trusted_at_equal_closeness():
    v = Player("Vera")
    v.relationships["Rex"] = {"closeness": 50, "last_interaction_tick": 1, "interaction_count": 1}
    v.relationships["Sol"] = {"closeness": 50, "last_interaction_tick": 1, "interaction_count": 1}
    v.felt_toward("Rex", "afraid", 9, 1)
    v.felt_toward("Rex", "uneasy", 8, 2)
    v.felt_toward("Sol", "grateful", 9, 1)
    rex = derive_person_profile(v, "Rex")
    sol = derive_person_profile(v, "Sol")
    assert rex["consent"] < sol["consent"]
    assert rex["_has_signal"] and sol["_has_signal"]


def test_role_emerges_from_dimensions_not_scalar():
    v = Player("Vera")
    v.add_memory("he lingers too close, stares, keeps finding excuses to touch", 7, importance=9, tags=["rel:X", "attraction:+4", "trust:-1.5"])
    p = derive_person_profile(v, "X")
    assert p["role"] in ("creep", "hostile")
    assert p["attraction"] > 20 and p["trust"] < 0


def test_serialization_includes_derived_read():
    v = Player("Vera")
    v.felt_toward("Rex", "afraid", 8, 1)
    rel = v.to_dict()["relationships"]["Rex"]
    assert "role" in rel
    assert "consent" in rel
    assert "summary" in rel


def test_memory_emotions_block_moves_profile():
    """A memory carrying a structured emotions{who,data} block moves the
    mechanically relevant derived dimensions (memory-driven feelings)."""
    p = Player("Vera")
    p.memories.append({
        "text": "the butcher cornered me", "importance": 7, "tags": ["fear"],
        "emotions": {"who": "Rex", "why": "he blocked my way",
                      "data": {"fear": 2, "affection": -4, "disgust": 1, "anger": 1}},
    })
    prof = derive_person_profile(p, "Rex")
    assert prof["fear"] > 10
    assert prof["attraction"] < -20
    assert prof["trust"] < 0
    assert prof["consent"] < 0


def test_expand_emotion_data_clamps_and_maps():
    from engine.derive import expand_emotion_data
    assert expand_emotion_data({"fear": 99, "affection": -99}) == [("fear", 5.0), ("attraction", -5.0)]
    assert ("trust", -1.0) in expand_emotion_data({"anger": 1})
    assert expand_emotion_data({"bogus": 10}) == []


def test_resolve_alias_and_description_handle():
    """task-350: agent-facing handles (the man / a subjective alias) resolve
    to the real player name so felt_toward / learn_names never key by a label."""
    from virtual_world_engine import VirtualWorld
    from area import Area
    from routes.player_ops import _resolve_other
    world = VirtualWorld()
    world.movement.add_area(Area("Main Hall", "hall", []))
    vera = Player("Vera"); vera.current_area = "Main Hall"
    rex = Player("Rex"); rex.current_area = "Main Hall"
    rex.description = "a tall man who lingers too close"
    sol = Player("Sol"); sol.current_area = "Main Hall"
    sol.description = "a quiet woman with kind eyes"
    world.add_player(vera); world.add_player(rex); world.add_player(sol)

    class App:
        def __init__(self):
            self.world = world
    app = App()
    try:
        node = world.graph.get_node(world._player_node_id("Rex"))
        node.properties["aliases"] = "the Butcher"
    except Exception:
        pass
    assert _resolve_other(app, "Vera", "the Butcher") == "Rex"
    assert _resolve_other(app, "Vera", "the tall man") == "Rex"
    assert _resolve_other(app, "Vera", "Rex") == "Rex"
    assert _resolve_other(app, "Vera", "the quiet woman") == "Sol"
    assert _resolve_other(app, "Vera", "the bogus person") is None


def test_felt_toward_records_under_resolved_name():
    v = Player("Vera")
    assert v.felt_toward("Rex", "afraid", 8, tick=1) is True
    assert "Rex" in v.relationships
    assert "the man" not in v.relationships