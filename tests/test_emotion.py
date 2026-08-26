"""Tests for the multi-dimensional emotion engine (task-96)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player
from engine.emotion import (
    BASELINES, describe, dominant, decay, felt_from_llm, normalize, spike,
)


class TestSpikeAndClamp:
    def test_baseline_map_complete(self):
        p = Player()
        m = p.emotions_map()
        assert set(m.keys()) == set(BASELINES.keys())
        assert m == BASELINES

    def test_spike_raises_dimension(self):
        p = Player()
        p.spike_emotion("afraid", 30)
        assert p.emotions_map()["afraid"] == pytest.approx(40.0)

    def test_spike_clamps_at_100(self):
        p = Player()
        p.spike_emotion("angry", 500)
        assert p.emotions_map()["angry"] == 100.0

    def test_negative_spike_clamps_at_0(self):
        p = Player()
        p.spike_emotion("happy", -500)
        assert p.emotions_map()["happy"] == 0.0

    def test_unknown_dimension_ignored(self):
        p = Player()
        p.spike_emotion("confused", 50)
        assert "confused" not in p.emotions_map()

    def test_non_numeric_delta_ignored(self):
        values = normalize(None)
        spike(values, "happy", "lots")
        assert values["happy"] == BASELINES["happy"]


class TestDecay:
    def test_decay_toward_baseline_not_zero(self):
        p = Player()
        p.spike_emotion("afraid", 60)          # 10 → 70
        for _ in range(100):
            p.decay_emotions()
        m = p.emotions_map()
        assert m["afraid"] == pytest.approx(BASELINES["afraid"])
        # Baseline dims stay put — calm is a state
        assert m["sad"] == pytest.approx(BASELINES["sad"])

    def test_decay_never_overshoots(self):
        values = {"happy": BASELINES["happy"] + 1.0}
        decay(values, per_tick=5.0)
        assert values["happy"] == BASELINES["happy"]

    def test_below_baseline_rises_back(self):
        values = {"affectionate": 2.0}         # baseline 25
        decay(values, per_tick=3.0)
        assert values["affectionate"] == 5.0

    def test_untouched_player_skips_work(self):
        p = Player()                            # _emotions is None
        p.decay_emotions()                      # must not initialize
        assert p._emotions is None


class TestDescribe:
    def test_near_baseline_is_silent(self):
        assert describe(normalize(None)) == ""

    def test_strong_afraid_gets_top_band(self):
        values = normalize(None)
        values["afraid"] = 90
        text = describe(values)
        assert "terrified" in text

    def test_moderate_happy(self):
        values = normalize(None)
        values["happy"] = 75                    # dev 35 → mid band
        assert "genuinely happy" in describe(values)

    def test_absence_phrase_for_collapsed_positive_dim(self):
        values = normalize(None)
        values["happy"] = 5                     # far below baseline
        assert "far away" in describe(values)

    def test_dominant_picks_biggest_deviation(self):
        values = normalize(None)
        values["angry"] = 80
        key, dev = dominant(values)
        assert key == "angry"
        assert dev == pytest.approx(72.0)


class TestLLMFelt:
    def test_valid_declaration(self):
        felt = felt_from_llm({"label": "Afraid", "intensity": 6})
        assert felt == ("afraid", 9.0)          # 15 * 0.6

    def test_unknown_label_rejected(self):
        assert felt_from_llm({"label": "hangry", "intensity": 8}) is None

    def test_intensity_clamped_and_capped(self):
        _, delta = felt_from_llm({"label": "angry", "intensity": 99})
        assert delta == pytest.approx(15.0)

    def test_garbage_rejected(self):
        assert felt_from_llm(None) is None
        assert felt_from_llm("afraid") is None
        assert felt_from_llm({"label": "sad"}) is None


class TestPersistence:
    def test_to_dict_includes_emotions(self):
        p = Player()
        p.spike_emotion("envious", 40)
        data = p.to_dict()
        assert data["emotions"]["envious"] == pytest.approx(45.0)

    def test_roundtrip_via_load_emotions(self):
        p = Player()
        p.load_emotions({"afraid": 88, "bogus": 999})
        assert p.emotions_map()["afraid"] == 88.0
        assert "bogus" not in p.emotions_map()

    def test_scenario_load_restores_emotions(self):
        from app import create_app
        import tempfile, os, json
        with tempfile.TemporaryDirectory() as td:
            app = create_app({"TESTING": True, "DATA_DIR": td})
            name = list(app.world.players.keys())[0]
            client = app.test_client()
            client.post(f"/api/players/{name}/emotions",
                        json={"emotion": "happy", "delta": 25})
            state = client.get("/api/state").get_json()
            stored = state["players"][name]["emotions"]
            assert stored["happy"] == pytest.approx(65.0)
            desc = state["players"][name].get("emotions_description", "")
            assert isinstance(desc, str)


class TestRoute:
    def _client(self, tmp_path):
        from app import create_app
        return create_app({"TESTING": True, "DATA_DIR": str(tmp_path)}).test_client()

    def test_get_and_post(self, tmp_path):
        client = self._client(tmp_path)
        from app import create_app
        app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})
        name = next(iter(app.world.players))
        r = client.post(f"/api/players/{name}/emotions",
                        json={"emotion": "envious", "delta": 20})
        assert r.status_code == 200
        assert r.get_json()["emotions"]["envious"] == pytest.approx(25.0)
        g = client.get(f"/api/players/{name}/emotions").get_json()
        assert g["emotions"]["envious"] == pytest.approx(25.0)

    def test_unknown_emotion_is_400(self, tmp_path):
        client = self._client(tmp_path)
        from app import create_app
        app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})
        name = next(iter(app.world.players))
        r = client.post(f"/api/players/{name}/emotions",
                        json={"emotion": "sparkly", "delta": 5})
        assert r.status_code == 400

    def test_missing_player_404(self, tmp_path):
        client = self._client(tmp_path)
        r = client.post("/api/players/Nobody/emotions",
                        json={"emotion": "sad", "delta": 5})
        assert r.status_code == 404
