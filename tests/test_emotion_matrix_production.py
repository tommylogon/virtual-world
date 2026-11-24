"""Production integration tests for Coupled Emotional Matrix, 8-channel
autonomic body, flustered volume slip, and optional CPU classifier (task-1001).
"""
from __future__ import annotations

from engine.emotion_classifier import appraise_event, get_configured_backend
from engine.emotion_matrix import (
    EmotionEvent,
    deserialize_matrix_state,
    serialize_matrix_state,
)
from player import Player


class _MockGoEmotionsBackend:
    model_id = "mock-go-emotions"

    def __init__(self, probs):
        self._probs = probs

    def classify(self, text: str):
        return dict(self._probs)


def test_default_classifier_backend_is_disabled():
    assert get_configured_backend() is None


def test_lazy_emotion_matrix_untouched_player():
    p = Player("Kayla")
    assert p._emotion_matrix is None
    assert p.somatic_description() == ""
    assert p.observer_tells() == ""
    assert p.serialize_emotion_matrix() is None


def test_appraise_event_updates_matrix_autonomic_and_36_dim_map():
    p = Player("Kayla")
    ev = EmotionEvent(
        kind="speech",
        summary="Zoe asked a tense question.",
        source_name="Zoe",
        speech_text="But we can't, can we?",
        speech_tone="serious",
        perceived_tone="serious",
        tone_strained=True,
        tick=21,
    )
    mock_backend = _MockGoEmotionsBackend({"fear": 0.45, "nervousness": 0.30, "neutral": 0.25})
    res = appraise_event(p, ev, force_backend=mock_backend)
    assert res is not None
    assert p._emotion_matrix is not None
    assert p._emotion_matrix.families["fear"] > 20.0
    assert "Zoe" in p._emotion_matrix.target_families
    assert p.emotions_map()["afraid"] > 15.0
    assert p._emotion_matrix.autonomic["heart_rate"] > 0.0


def test_serialize_and_deserialize_roundtrip():
    p = Player("Sammy")
    ev = EmotionEvent(
        kind="speech",
        summary="Someone mocked Sammy.",
        source_name="Jake",
        speech_text="Nice job, genius.",
        speech_tone="sarcastic",
        perceived_tone="sarcastic",
        tick=5,
    )
    appraise_event(p, ev, force_backend=None)
    payload = p.serialize_emotion_matrix()
    assert payload is not None
    assert "families" in payload and "autonomic" in payload
    assert "somatic_description" in payload
    assert "observer_tells" in payload

    p2 = Player("Sammy")
    p2.load_emotion_matrix(payload)
    assert p2._emotion_matrix is not None
    assert p2._emotion_matrix.families["anger"] == serialize_matrix_state(p._emotion_matrix)["families"]["anger"]
    assert deserialize_matrix_state(None) is None


def test_decay_emotions_decays_matrix_and_autonomic():
    p = Player("Zoe")
    st = p.emotion_matrix_state()
    st.families["fear"] = 75.0
    st.autonomic["heart_rate"] = 60.0
    p.decay_emotions()
    assert st.families["fear"] < 75.0
    assert st.autonomic["heart_rate"] < 60.0
