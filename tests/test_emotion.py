"""Tests for the multi-dimensional emotion engine (task-96)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player
from engine.emotion import (
    BASELINES, describe, dominant, dominant_expression, decay, derive_from_vitals,
    felt_from_llm, normalize, spike,
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


class TestDeriveFromVitals:
    """task-142: mood derived from physical state when nothing explicit is set."""

    HEALTHY = {"Energy": 100, "Hunger": 0, "Thirst": 0, "Bladder": 0,
               "Sanity": 100, "Social": 100, "Entertainment": 100,
               "Temperature": 37.0, "HP": 100}

    def _derived(self, **overrides):
        vitals = {**self.HEALTHY, **overrides}
        return derive_from_vitals(vitals, "awake")

    def test_healthy_is_silent(self):
        assert derive_from_vitals(self.HEALTHY, "awake") is None

    def test_missing_vitals_is_silent(self):
        assert derive_from_vitals(None, "awake") is None

    def test_state_dead_is_calm(self):
        derived = derive_from_vitals(self.HEALTHY, "dead")
        assert derived is not None
        assert "calm" in describe(derived)

    def test_sleeping_and_unconscious_are_silent(self):
        assert derive_from_vitals(self.HEALTHY, "sleeping") is None
        assert derive_from_vitals(self.HEALTHY, "unconscious") is None

    def test_starving_reads_as_craving(self):
        derived = self._derived(Hunger=80)
        assert derived["craving"] > BASELINES["craving"]
        assert "craving" in describe(derived)

    def test_dehydrated_reads_as_anxious(self):
        derived = self._derived(Thirst=80)
        assert derived["anxious"] > BASELINES["anxious"]
        assert "anxi" in describe(derived)

    def test_exhausted_reads_as_irritated(self):
        derived = self._derived(Energy=10)
        assert derived["irritated"] > BASELINES["irritated"]
        assert "irritat" in describe(derived)

    def test_cold_reads_as_uneasy(self):
        derived = self._derived(Temperature=34.0)
        assert derived["uneasy"] > BASELINES["uneasy"]
        assert "unease" in describe(derived)

    def test_overheated_reads_as_irritated(self):
        derived = self._derived(Temperature=39.0)
        assert derived["irritated"] > BASELINES["irritated"]

    def test_injured_reads_as_afraid(self):
        derived = self._derived(HP=40)
        assert derived["afraid"] > BASELINES["afraid"]

    def test_isolated_reads_as_lonely(self):
        derived = self._derived(Social=10)
        assert derived["lonely"] > BASELINES["lonely"]
        assert "loneliness" in describe(derived)

    def test_full_bladder_reads_as_irritated(self):
        derived = self._derived(Bladder=80)
        assert derived["irritated"] > BASELINES["irritated"]

    def test_signals_combine(self):
        derived = self._derived(Hunger=80, Energy=10)
        assert derived["craving"] > BASELINES["craving"]
        assert derived["irritated"] > BASELINES["irritated"]

    def test_every_derived_mood_has_hand_written_bands(self):
        # A derived dimension must never fall through to the generic
        # "You feel <dim> with unusual intensity." debug phrasing.
        derived_moods = [
            self._derived(Hunger=80),
            self._derived(Energy=10),
            self._derived(Temperature=34.0),
            self._derived(HP=40),
            self._derived(Social=10),
            derive_from_vitals(self.HEALTHY, "dead"),
        ]
        for derived in derived_moods:
            text = describe(derived)
            assert "unusual intensity" not in text
            assert "strong sense of" not in text


class TestEmotionDescriptionDerivation:
    """Player.emotions_description(): explicit affects win, vitals fill silence."""

    def _starving_player(self):
        p = Player()
        p.vitals["Hunger"] = 90
        return p

    def test_explicit_emotion_wins_over_vitals(self):
        p = self._starving_player()
        p.spike_emotion("happy", 40)
        text = p.emotions_description()
        assert "genuinely happy" in text
        assert "craving" not in text

    def test_vitals_fill_silence(self):
        p = self._starving_player()
        text = p.emotions_description()
        assert "craving" in text

    def test_healthy_neutral_is_empty(self):
        assert Player().emotions_description() == ""


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

    def test_unknown_emotion_is_graceful_noop(self, tmp_path):
        # task-96/350 contract change: creative LLM labels never 400 — they
        # resolve semantically (map_label) or no-op with `ignored`.
        client = self._client(tmp_path)
        from app import create_app
        app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})
        name = next(iter(app.world.players))
        r = client.post(f"/api/players/{name}/emotions",
                        json={"emotion": "sparkly", "delta": 5})
        assert r.status_code == 200
        assert r.get_json().get("ignored") == "sparkly"

    def test_missing_player_404(self, tmp_path):
        client = self._client(tmp_path)
        r = client.post("/api/players/Nobody/emotions",
                        json={"emotion": "sad", "delta": 5})
        assert r.status_code == 404


class TestDominantExpression:
    """dominant_expression: affect map -> canonical expression-portrait key."""

    def test_all_baseline_is_neutral(self):
        assert dominant_expression(dict(BASELINES)) == "neutral"

    def test_raised_joy_axis_selects_happy(self):
        m = dict(BASELINES)
        m["happy"] = m["happy"] + 20
        assert dominant_expression(m) == "happy"

    def test_sub_emotion_selects_its_axis_key(self):
        # anxious is the fear axis, whose portrait key is 'afraid'.
        m = dict(BASELINES)
        m["anxious"] = m["anxious"] + 20
        assert dominant_expression(m) == "afraid"

    def test_bond_and_calm_axes(self):
        m = dict(BASELINES)
        m["affectionate"] = m["affectionate"] + 20
        assert dominant_expression(m) == "affectionate"
        m = dict(BASELINES)
        m["calm"] = m["calm"] + 20
        assert dominant_expression(m) == "calm"

    def test_below_margin_is_neutral(self):
        m = dict(BASELINES)
        m["angry"] = m["angry"] + 3
        assert dominant_expression(m) == "neutral"

    def test_min_margin_override(self):
        m = dict(BASELINES)
        m["angry"] = m["angry"] + 3
        assert dominant_expression(m, min_margin=1.0) == "angry"

    def test_strongest_axis_wins(self):
        m = dict(BASELINES)
        m["happy"] = m["happy"] + 12
        m["sad"] = m["sad"] + 30
        assert dominant_expression(m) == "sad"

    def test_player_method_uses_affect_map(self):
        p = Player()
        assert p.dominant_expression() == "neutral"
        p.spike_emotion("afraid", 30)
        assert p.dominant_expression() == "afraid"


class TestOneModel:
    """The legacy single-label fields are **derived from** the map, not stored.

    Before this, `Player.emotion` was a real field written by four production paths
    while the face was chosen from the map — so the ordinary way to change how a
    character felt did not change their face. These pin the replacement: the
    properties, the widened vocabulary, the axis damping, and the fact that an
    untouched character is untouched rather than mildly serene.
    """

    def test_an_untouched_player_is_at_rest_and_stays_lazy(self):
        p = Player()
        # None, not a materialised baseline: decay skips an unmaterialised map.
        assert p._emotions is None
        assert p.emotion == "neutral"
        assert p.emotion_intensity == 0.0
        # …and *reading* the derived label must not materialise it.
        assert p._emotions is None, "reading the label must not build the map"

    def test_set_emotion_now_reaches_the_face(self):
        p = Player()
        p.set_emotion("afraid", 0.8)
        assert p.emotion == "afraid"
        assert p.dominant_expression() == "afraid", (
            "the whole point: a scripted emotion must show on the character")

    def test_set_emotion_accepts_the_whole_vocabulary(self):
        """Not the old seven. A `set_emotion` action could reach 7 of 36."""
        for label in ("grateful", "dread", "melancholic", "elated", "ashamed"):
            p = Player()
            p.set_emotion(label, 0.7)
            assert p.emotion == label, label

    def test_set_emotion_accepts_a_keyword_alias(self):
        p = Player()
        p.set_emotion("terrified", 0.9)          # an alias, not a dimension
        assert p.emotion == "afraid"
        assert p.emotions_map()["afraid"] > BASELINES["afraid"]

    def test_set_emotion_rejects_a_word_the_vocabulary_lacks(self):
        p = Player()
        with pytest.raises(ValueError, match="Unknown emotion"):
            p.set_emotion("wibble", 0.5)

    def test_setting_a_feeling_damps_its_siblings_but_not_other_axes(self):
        p = Player()
        p.set_emotion("afraid", 0.9)
        m = p.emotions_map()
        # Same axis (fear): the siblings are pulled back toward rest, so the
        # character is not maximally afraid *and* maximally anxious.
        assert m["afraid"] > m["anxious"] + BASELINES["anxious"] * 0.5
        # A different axis can be true at the same time — which is the reason the
        # map replaced the single slot.
        p.spike_emotion("grateful", 40)
        assert p.emotions_map()["grateful"] > BASELINES["grateful"]
        assert p.emotion == "afraid", "the leading feeling is still fear"

    def test_a_legacy_assignment_lands_in_the_map(self):
        p = Player()
        p.emotion = "furious"                     # an alias for angry
        assert p.emotion == "angry"
        assert p.dominant_expression() == "angry"

    def test_neutral_is_a_reset_not_a_feeling(self):
        """`LABEL_TO_DIM` maps neutral to calm, so taking it literally would
        leave every character mildly serene."""
        p = Player()
        p.set_emotion("afraid", 0.9)
        p.emotion = "neutral"
        assert p.emotion == "neutral"
        assert p.emotions_map() == BASELINES

    def test_intensity_round_trips_through_the_map(self):
        p = Player()
        p.set_emotion("sad", 0.5)
        assert p.emotion_intensity == pytest.approx(0.5, abs=0.02)
        p.emotion_intensity = 1.0
        # Intensity is *points above rest*, so full is baseline + 100 rather than
        # an absolute 100 — which is what makes 0.0 mean "at rest" and lets a
        # character's own baseline matter.
        assert p.emotions_map()["sad"] == pytest.approx(
            BASELINES["sad"] + 100.0, abs=1.0)

