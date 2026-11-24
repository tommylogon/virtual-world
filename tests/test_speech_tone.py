"""Tests for speech delivery tone (task-994): intended_tone -> perceived_tone.

Covers:
  - engine/speech_tone.py canonical vocabulary, normalization, prefix stripping, adverbs
  - Subjective listener-side perception (speaker overload strain leak, listener mood
    misread of teasing -> mocking, low-closeness teasing -> mocking, oblivious stranger
    missing subtle sarcasm)
  - routes/action_handlers.py [tone:<val>] and [lang:<val>] parsing & forwarding
  - engine/speech.py SpeechBroadcaster per-listener recent_hearing perceived_tone
"""
from __future__ import annotations

import pytest

from engine.speech_tone import (
    SPEECH_TONES,
    format_tone_adverb,
    normalize_speech_tone,
    perceive_speech_tone,
    strip_speech_prefixes,
)


def test_normalize_and_strip_prefixes():
    assert len(SPEECH_TONES) == 8
    assert normalize_speech_tone("sarcastic") == "sarcastic"
    assert normalize_speech_tone("playful") == "teasing"
    assert normalize_speech_tone("dryly") == "sarcastic"
    assert normalize_speech_tone("plain") is None
    assert normalize_speech_tone("neutral") is None
    assert normalize_speech_tone(None) is None

    clean, lang, tone = strip_speech_prefixes("[tone:sarcastic] [lang:elvish] Oh, brilliant job.")
    assert clean == "Oh, brilliant job."
    assert lang == "elvish"
    assert tone == "sarcastic"

    clean2, lang2, tone2 = strip_speech_prefixes("[lang:goblin] [tone:playful] Watch your step.")
    assert clean2 == "Watch your step."
    assert lang2 == "goblin"
    assert tone2 == "teasing"

    assert format_tone_adverb("sarcastic") == "sarcastically"
    assert format_tone_adverb("warm", strained_leak=True) == "in a strained, forced tone"


def test_perceive_speech_tone_subjectivity():
    # 1. Steady close friend teasing -> perceived as teasing (playful).
    r1 = perceive_speech_tone("teasing", closeness=65.0, listener_insight=10)
    assert r1["perceived_tone"] == "teasing"
    assert r1["misread_reason"] is None

    # 2. Same teasing remark to deeply ashamed listener -> mislands as mocking!
    r2 = perceive_speech_tone(
        "teasing",
        closeness=65.0,
        listener_insight=10,
        listener_families={"shame": 50.0, "sadness": 20.0, "anger": 8.0},
    )
    assert r2["perceived_tone"] == "mocking"
    assert r2["misread_reason"] == "listener_mood_misread"

    # 3. Same teasing remark from a stranger -> mislands as mocking!
    r3 = perceive_speech_tone("teasing", closeness=0.0, listener_insight=10)
    assert r3["perceived_tone"] == "mocking"
    assert r3["misread_reason"] == "low_closeness_misread"

    # 4. Warm delivery from an overloaded/shaking speaker -> leaks through as strained!
    r4 = perceive_speech_tone(
        "warm",
        closeness=55.0,
        listener_insight=12,
        speaker_overloaded=True,
        speaker_autonomic={"heart_rate": 72.0, "muscle_tension": 70.0},
    )
    assert r4["perceived_tone"] == "strained"
    assert r4["strained_leak"] is True
    assert r4["adverb"] == "in a strained, forced tone"

    # 5. Low-Insight stranger misses subtle sarcasm -> taken at face value (None).
    r5 = perceive_speech_tone("sarcastic", closeness=0.0, listener_insight=7)
    assert r5["perceived_tone"] is None
    assert r5["misread_reason"] == "missed_subtle_sarcasm"


def test_perceive_speech_tone_spatial_proximity():
    # Strained (non-overloaded) speaker delivering a warm cover line:
    # - Close same-area listener (closeness=30, WIS=12) catches the strain.
    # - Adjacent-area listener (distance=1, same_area=False) hears warm at face value!
    # - Across-the-room listener (proximity_checked=True, proximity_hops=None) also misses mild strain.
    strained_auto = {"heart_rate": 62.0, "muscle_tension": 60.0}
    close_res = perceive_speech_tone(
        "warm",
        closeness=30.0,
        listener_insight=12,
        speaker_autonomic=strained_auto,
        speaker_overloaded=False,
        same_area=True,
        proximity_hops=1,
        proximity_checked=True,
    )
    assert close_res["perceived_tone"] == "strained"
    assert close_res["strained_leak"] is True

    across_res = perceive_speech_tone(
        "warm",
        closeness=30.0,
        listener_insight=12,
        speaker_autonomic=strained_auto,
        speaker_overloaded=False,
        same_area=True,
        proximity_hops=None,
        proximity_checked=True,
    )
    assert across_res["perceived_tone"] == "warm"
    assert across_res["strained_leak"] is False

    adjacent_res = perceive_speech_tone(
        "warm",
        closeness=35.0,
        listener_insight=13,
        speaker_autonomic=strained_auto,
        speaker_overloaded=False,
        same_area=False,
        distance=1,
    )
    assert adjacent_res["perceived_tone"] == "warm"
    assert adjacent_res["strained_leak"] is False

    # Outright overloaded speaker yelling across 1 open hop still leaks to a very close/sharp listener.
    overloaded_adj = perceive_speech_tone(
        "warm",
        closeness=50.0,
        listener_insight=14,
        speaker_autonomic={"heart_rate": 85.0, "muscle_tension": 80.0},
        speaker_overloaded=True,
        same_area=False,
        distance=1,
    )
    assert overloaded_adj["perceived_tone"] == "strained"

    # Subtle sarcasm heard from an adjacent area by a non-close moderate-WIS listener is missed.
    distant_sarc = perceive_speech_tone(
        "sarcastic",
        closeness=18.0,
        listener_insight=10,
        same_area=False,
        distance=1,
    )
    assert distant_sarc["perceived_tone"] is None
    assert distant_sarc["misread_reason"] == "missed_subtle_sarcasm"


def test_broadcast_speech_and_action_route_subjective_tone():
    import logging
    from app import create_app
    from engine.relationships import ensure_relationship
    from player import Player

    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app = create_app({"TESTING": True})
    world = app.world

    speaker = Player("Jake")
    speaker.current_area = "Kitchen"

    friend = Player("Elena")
    friend.current_area = "Kitchen"
    rel_f, _ = ensure_relationship(friend, "Jake", tick=1)
    rel_f["closeness"] = 70

    stranger = Player("Rando")
    stranger.current_area = "Kitchen"
    stranger.stats["WIS"] = 10

    for p in (speaker, friend, stranger):
        world.add_player(p)
    world.active_player = "Jake"

    client = app.test_client()
    resp = client.post("/api/action", json={"action": "say [tone:teasing] You're a menace.", "character": "Jake"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "teasingly" in data["output"]
    assert "menace" in data["output"].lower()

    # Same line heard DIFFERENTLY by close steady friend vs stranger!
    f_heard = friend.recent_hearing[-1]
    s_heard = stranger.recent_hearing[-1]
    assert f_heard["intended_tone"] == "teasing"
    assert f_heard["perceived_tone"] == "teasing"
    assert s_heard["intended_tone"] == "teasing"
    assert s_heard["perceived_tone"] == "mocking"

    # Now make speaker severely distressed and try delivering "warm": friend hears strained!
    speaker.load_emotions({"afraid": 85.0, "anxious": 80.0})
    resp2 = client.post("/api/action", json={"action": "say [tone:warm] I'm totally fine.", "character": "Jake"})
    assert resp2.status_code == 200
    f_heard2 = friend.recent_hearing[-1]
    assert f_heard2["intended_tone"] == "warm"
    assert f_heard2["perceived_tone"] == "strained"
    assert f_heard2.get("tone_strained") is True


def test_broadcast_speech_cross_area_distance_dampens_strain():
    import logging
    from app import create_app
    from engine.relationships import ensure_relationship
    from graph import EDGE_CONNECTION, Edge, Node
    from player import Player

    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app = create_app({"TESTING": True})
    world = app.world
    g = world.graph

    a1 = Node("area_yard_a", "area", "Driveway", properties={"environment": {"noise": "quiet"}})
    a2 = Node("area_yard_b", "area", "Dessert Tables", properties={"environment": {"noise": "quiet"}})
    w = Node("way_open_yard", "way", "open yard", properties={"state": "open"})
    for n in (a1, a2, w):
        g.add_node(n)
    g.add_edge(Edge("area_yard_a", "way_open_yard", EDGE_CONNECTION, properties={"direction": "east"}))
    g.add_edge(Edge("way_open_yard", "area_yard_a", EDGE_CONNECTION, properties={"direction": "west"}))
    g.add_edge(Edge("area_yard_b", "way_open_yard", EDGE_CONNECTION, properties={"direction": "west"}))
    g.add_edge(Edge("way_open_yard", "area_yard_b", EDGE_CONNECTION, properties={"direction": "east"}))

    kayla = Player("Kayla")
    kayla.current_area = "Driveway"
    kayla.load_emotions({"afraid": 70.0, "anxious": 65.0})

    kyrie = Player("Kyrie")
    kyrie.current_area = "Driveway"
    kyrie.stats["WIS"] = 13
    rel_k, _ = ensure_relationship(kyrie, "Kayla", tick=1)
    rel_k["closeness"] = 70

    maria = Player("Maria")
    maria.current_area = "Dessert Tables"
    maria.stats["WIS"] = 12
    rel_m, _ = ensure_relationship(maria, "Kayla", tick=1)
    rel_m["closeness"] = 35

    for p in (kayla, kyrie, maria):
        world.add_player(p)

    # Kayla shouts a casual warm cover line across the open yard while strained (non-overloaded):
    # - Kyrie standing right beside her in Driveway catches the strained leak.
    # - Maria in adjacent Dessert Tables hears it as warm at face value!
    world.narration.broadcast_speech(
        "Kayla",
        "Nothing, Mrs. Lopez! Sammy just dropped her fork!",
        area_name="Driveway",
        speech_level="shout",
        tone="warm",
    )
    assert kyrie.recent_hearing[-1]["perceived_tone"] == "strained"
    assert kyrie.recent_hearing[-1].get("tone_strained") is True
    assert maria.recent_hearing[-1]["distance"] >= 1
    assert maria.recent_hearing[-1]["perceived_tone"] == "warm"
    assert not maria.recent_hearing[-1].get("tone_strained")
