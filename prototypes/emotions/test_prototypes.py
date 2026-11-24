"""Comprehensive pytest suite for Emotion Prototypes A, B, and C inside VirtualWorld.

Runs fast and deterministically (offline/mocked LLM for unit tests) while exercising
real VirtualWorld worlds, Player records, vitals, traits, relationships, and
engine/memory_retrieval.py.
"""
from __future__ import annotations

import json
import pytest

from prototypes.emotions.autonomic import (
    render_observer_tells,
    render_vocal_interruption,
    species_autonomic_mode,
)
from prototypes.emotions.proto_a_matrix import ProtoAMatrixEngine
from prototypes.emotions.proto_b_semantic import ProtoBSemanticEngine
from prototypes.emotions.proto_c_dual_mind import ProtoCDualMindEngine
from prototypes.emotions.proto_d_unified import ProtoDUnifiedEngine
from prototypes.emotions.scenarios import (
    run_scenario_d_jake_insult,
    run_scenario_goblin_soak,
    run_scenario_miki_taco_bell,
    run_scenario_subtle_sarcasm,
    run_scenario_tone_of_speech,
    run_scenario_worksheet_2a_pot,
)
from prototypes.emotions.schema import (
    AUTONOMIC_CHANNELS,
    FAMILIES,
    FAMILY_BASELINES,
    CharacterEmotionState,
    EmotionEvent,
)
from prototypes.emotions.viwo_adapter import ViwoEmotionHarness, load_real_viwo_world


def _mock_limbic_llm(messages):
    """Deterministic stub for Track 1 LLM JSON testing."""
    user = messages[-1]["content"].lower()
    if "you're a bitch" in user and "partner" in user and "witnesses present: sammy" in user:
        return json.dumps({
            "gut_appraisal": "He snapped in front of our friends right after I tried to help.",
            "deltas": {"sadness": 42, "anger": 28, "shame": 26, "fear": 18, "disgust": 12, "love": -22, "happiness": -40},
            "suppress": True,
        })
    if "pot" in user and "don't hate" not in user:
        return json.dumps({
            "gut_appraisal": "I ruined her pot and hid it instead of being honest.",
            "deltas": {"shame": 40, "guilt": 42, "fear": 18, "happiness": -25},
            "suppress": False,
        })
    if "don't hate" in user or "no rush at all" in user:
        return json.dumps({
            "gut_appraisal": "She is not kicking me out; the worst-case story in my head was wrong.",
            "deltas": {"shame": -30, "fear": -24, "calm": 22, "happiness": 16},
            "suppress": False,
        })
    if "chief's staff" in user:
        return json.dumps({
            "gut_appraisal": "Gruk has the staff I earned.",
            "deltas": {"envy": 40, "anger": 14, "happiness": -15},
            "suppress": False,
        })
    if "time alone with him" in user:
        return json.dumps({
            "gut_appraisal": "I am losing Mora to an outsider.",
            "deltas": {"jealousy": 44, "fear": 18, "anger": 15, "happiness": -20},
            "suppress": False,
        })
    if "perceived delivery tone: teasing" in user:
        return json.dumps({
            "gut_appraisal": "He is joking around with me over stealing his fry.",
            "deltas": {"happiness": 24, "love": 14, "calm": 6},
            "suppress": False,
        })
    if "perceived delivery tone: mocking" in user:
        return json.dumps({
            "gut_appraisal": "I know he called it a joke, but it stung right where I already feel awful.",
            "deltas": {"shame": 30, "sadness": 26, "anger": 18, "happiness": -28},
            "suppress": True,
        })
    if "perceived delivery tone: strained" in user:
        return json.dumps({
            "gut_appraisal": "She says she is fine, but her voice is tight and shaking - something is wrong.",
            "deltas": {"fear": 20, "sadness": 16, "surprise": 16, "calm": -16},
            "suppress": False,
        })
    if "adorable" in user and "redo" in user:
        return json.dumps({
            "gut_appraisal": "She humiliated me in front of the whole team with a fake polite smile.",
            "deltas": {"shame": 38, "anger": 30, "sadness": 28, "love": -22, "happiness": -34},
            "suppress": True,
        })
    return json.dumps({
        "gut_appraisal": "Caught off guard and tense.",
        "deltas": {"fear": 30, "love": 18, "surprise": 12},
        "suppress": True,
    })


_ALL_FOUR_FACTORIES = [
    lambda: ProtoAMatrixEngine(),
    lambda: ProtoBSemanticEngine(offline=True),
    lambda: ProtoCDualMindEngine(llm_fn=_mock_limbic_llm),
    lambda: ProtoDUnifiedEngine(offline=True, llm_fn=_mock_limbic_llm),
]


@pytest.mark.parametrize("engine_factory", _ALL_FOUR_FACTORIES)
def test_all_three_prototypes_run_all_four_viwo_scenarios(engine_factory):
    eng = engine_factory()
    d = run_scenario_d_jake_insult(eng)
    c1 = d["cases"]["trusted_partner_in_crowd"]
    c2 = d["cases"]["hostile_stranger_alone"]
    c3 = d["cases"]["exhausted_ashamed_partner_private"]

    # Scenario D: Trusted partner insult must shift multiple emotions INCLUDING love/happiness down!
    assert c1["applied_deltas"].get("happiness", 0) < 0
    assert c1["applied_deltas"].get("love", 0) < 0
    assert c1["after_families"]["sadness"] > FAMILY_BASELINES["sadness"] + 15
    assert c1["after_families"]["shame"] > c2["after_families"]["shame"]

    # Exhausted + ashamed prior mood + guilt-prone temperament must turn the hit inward into shame/sadness.
    assert c3["after_families"]["shame"] > c2["after_families"]["shame"]
    assert c3["prompt_your_state"] != ""
    # Strict Interiority & Subtext rule: zero clinical DBT worksheet headers in prompt!
    for forbidden in ("Vulnerability Factors:", "Prompting Event:", "Action Urge:", "Overload:"):
        assert forbidden not in c1["prompt_your_state"]
        assert forbidden not in c3["prompt_your_state"]


@pytest.mark.parametrize("engine_factory", _ALL_FOUR_FACTORIES)
def test_real_taco_bell_date_scenario_guarded_traits_and_autonomic_inertia(engine_factory):
    eng = engine_factory()
    res = run_scenario_miki_taco_bell(eng)
    t1 = res["turns"]["turn_1_trigger"]
    i2 = res["turns"]["after_2_ticks_inertia"]
    t2 = res["turns"]["turn_2_reassurance"]

    assert t1["vulnerability_load"] > 0.3
    assert len(t1["recalled_memories"]) >= 1
    assert any(v > 20 for v in t1["autonomic"].values())
    # Adrenaline / autonomic inertia: does not teleport to 0 after just 2 ticks.
    assert i2["autonomic"]["heart_rate"] > 0
    # Reassurance cools down fear/shame and raises calm.
    assert t2["applied_deltas"].get("calm", 0) > 0


@pytest.mark.parametrize("engine_factory", _ALL_FOUR_FACTORIES)
def test_worksheet_2a_shame_vs_guilt_and_observer_deescalation(engine_factory):
    eng = engine_factory()
    res = run_scenario_worksheet_2a_pot(eng)
    s1 = res["steps"]["step_1_shame_and_guilt"]
    s2 = res["steps"]["step_2_observer_social_influence"]
    s3 = res["steps"]["step_3_check_facts_resolved"]

    # Both shame AND guilt fire simultaneously, not collapsed into one bucket.
    assert s1["after_families"]["shame"] > FAMILY_BASELINES["shame"] + 15
    assert s1["after_families"]["guilt"] > FAMILY_BASELINES["guilt"] + 15
    # Guilt drives repair/apologise tilt; shame drives withdraw/ignore tilt.
    assert "social.weight.apologise" in s1["disposition_tilts"]
    # Handout 3 social communication: Rosa seeing Maya's visible contrition softens Rosa's anger!
    assert s2["rosa_anger_after"] < s2["rosa_anger_before"]
    # Checking the facts resolves shame episode.
    assert any(ep["resolved"] for ep in s3["episodes"])


@pytest.mark.parametrize("engine_factory", _ALL_FOUR_FACTORIES)
def test_goblin_soak_envy_vs_jealousy_and_apathetic_decay(engine_factory):
    eng = engine_factory()
    res = run_scenario_goblin_soak(eng)
    sk = res["results"]["skrit_envy"]
    vx = res["results"]["vex_jealousy"]
    dk = res["results"]["after_5_ticks"]

    assert sk["after_families"]["envy"] > sk["after_families"]["jealousy"]
    assert vx["after_families"]["jealousy"] > vx["after_families"]["envy"]
    # Apathetic trait actually decays anger faster!
    assert dk["dull_apathetic_anger"] < dk["skrit_anger"]


def test_species_autonomic_gating_and_lighting_masking_insight():
    from player import Player

    ghost = Player("Specter")
    ghost.state = "dead"
    assert species_autonomic_mode(ghost) == "none"

    wolf = Player("Fang")
    wolf.species = "wolf"
    assert species_autonomic_mode(wolf) == "animal"

    human = Player("Miki")
    st = CharacterEmotionState()
    st.families["anger"] = 68.0
    st.autonomic["vasomotor"] = 65.0
    st.autonomic["muscle_tension"] = 70.0
    st.autonomic["breathing"] = 58.0

    # Suppressed below overload: invisible to low-insight stranger, visible micro-tell to perceptive friend.
    stranger_view = render_observer_tells(
        st, human, lighting="normal", observer_insight=10, familiarity=0.0,
        overloaded=False, suppressed_families=["anger"],
    )
    insight_view = render_observer_tells(
        st, human, lighting="normal", observer_insight=15, familiarity=0.8,
        overloaded=False, suppressed_families=["anger"],
    )
    dark_view = render_observer_tells(
        st, human, lighting="pitch_black", observer_insight=10, familiarity=0.0,
        overloaded=False, suppressed_families=[],
    )
    assert stranger_view == ""
    assert "jaw" in insight_view.lower() or "neck" in insight_view.lower()
    assert "breathing" in dark_view.lower()


def test_human_embodied_vs_director_override_and_speech_protection():
    world = load_real_viwo_world("taco_bell_date")
    h = ViwoEmotionHarness(world, ProtoAMatrixEngine())

    # Default Embodied mode forbids manual emotion override.
    with pytest.raises(PermissionError):
        h.apply_human_override("jake halloway", {"anger": 0.0})

    # Director / Adjustable mode allows player override.
    h.set_human_override_mode("jake halloway", True)
    updated = h.apply_human_override("jake halloway", {"calm": 80.0})
    assert updated["calm"] == 80.0

    # Vocal interruption never silently rewrites human typed speech by default.
    auto = {ch: 80.0 for ch in AUTONOMIC_CHANNELS}
    assert render_vocal_interruption("I am fine.", auto, overloaded=True, is_human=True) is None
    assert render_vocal_interruption("I am fine.", auto, overloaded=True, is_human=False) is not None


def test_cue_change_gating_skips_redundant_llm_calls():
    calls = {"count": 0}

    def counting_llm(messages):
        calls["count"] += 1
        return _mock_limbic_llm(messages)

    world = load_real_viwo_world("taco_bell_date")
    eng = ProtoCDualMindEngine(llm_fn=counting_llm)
    h = ViwoEmotionHarness(world, eng)

    evt1 = EmotionEvent(kind="continuation", summary="Quiet moment sitting at the booth.", tick=1)
    h.step_event("miki doki", evt1)
    assert calls["count"] == 1

    # Identical continuation cue must reuse gate and NOT invoke LLM again!
    evt2 = EmotionEvent(kind="continuation", summary="Quiet moment sitting at the booth.", tick=2)
    r2 = h.step_event("miki doki", evt2)
    assert calls["count"] == 1
    assert r2.metadata["method"] == "cue_gated_skip"


def test_unary_plus_json_extraction_for_small_llms():
    from prototypes.emotions.proto_c_dual_mind import _extract_json_object

    raw = '{"gut_appraisal":"Relief sets in.", "deltas":{"fear":-45, "calm":+30, "happiness":+15}, "suppress":false}'
    parsed = _extract_json_object(raw)
    assert parsed is not None
    assert parsed["deltas"]["calm"] == 30
    assert parsed["deltas"]["fear"] == -45


def test_proto_d_smart_tier_routing_floor_enforcement_and_sarcasm():
    calls = {"count": 0}

    def drifty_llm(messages):
        calls["count"] += 1
        user = messages[-1]["content"].lower()
        if "adorable" in user and "redo" in user:
            return json.dumps({
                "gut_appraisal": "She humiliated me in front of the studio with a polite smile.",
                "deltas": {"shame": 38, "anger": 30, "sadness": 28, "love": -22, "happiness": -34},
                "suppress": True,
            })
        # Deliberately omit `guilt` on a transgression to prove Tier 1 floor enforces it!
        return json.dumps({
            "gut_appraisal": "I feel exposed and embarrassed.",
            "deltas": {"shame": 40, "fear": 15},
            "suppress": False,
        })

    # 1. Structured non-speech goal skips Tier 3 LLM completely (0 LLM calls).
    world = load_real_viwo_world("taco_bell_date")
    eng = ProtoDUnifiedEngine(offline=True, llm_fn=drifty_llm)
    h = ViwoEmotionHarness(world, eng)
    r_goal = h.step_event(
        "miki doki",
        EmotionEvent(
            kind="goal",
            summary="A rival claimed the stage trophy first.",
            source_name="Rival",
            tick=1,
            tags=["rival_holds_goal_item", "envy"],
        ),
    )
    assert calls["count"] == 0
    assert r_goal.metadata["route"] == "tier_ab_fast"
    assert r_goal.after_families["envy"] > FAMILY_BASELINES["envy"] + 25

    # 2. Transgression speech escalates to Tier 3 AND enforces Tier 1 guilt floor even if LLM forgets guilt.
    r_trans = h.step_event(
        "miki doki",
        EmotionEvent(
            kind="action",
            summary="Broke her roommate's pot and threw it away secretly.",
            source_name="Rosa",
            speech_text="Hey, did you see my pot?",
            tick=2,
            tags=["transgression", "hid_mistake"],
        ),
    )
    assert calls["count"] == 1
    assert r_trans.metadata["route"] == "tier_abc_full"
    assert any(f.startswith("guilt>=") for f in r_trans.metadata["floors_applied"])
    assert r_trans.after_families["guilt"] >= FAMILY_BASELINES["guilt"] + 25

    # 3. Identical continuation cue hits cue_gated_skip without burning Tier 3.
    evt_c1 = EmotionEvent(kind="continuation", summary="Sitting quietly in the kitchen.", tick=3)
    h.step_event("miki doki", evt_c1)
    c_before = calls["count"]
    evt_c2 = EmotionEvent(kind="continuation", summary="Sitting quietly in the kitchen.", tick=4)
    r_skip = h.step_event("miki doki", evt_c2)
    assert calls["count"] == c_before
    assert r_skip.metadata["route"] == "cue_gated_skip"

    # 4. Subtle untagged sarcasm (zero curse words, zero tags): D catches the hurt cleanly
    # and triggers sarcasm_polarity_override so A's false "smile" warmth does not dilute it.
    sarc = run_scenario_subtle_sarcasm(ProtoDUnifiedEngine(offline=True, llm_fn=drifty_llm))["result"]
    assert sarc["metadata"]["route"] == "tier_abc_full"
    assert sarc["metadata"]["sarcasm_polarity_override"] is True
    assert sarc["applied_deltas"].get("happiness", 0) < -30
    assert sarc["after_families"]["shame"] > FAMILY_BASELINES["shame"] + 30


@pytest.mark.parametrize("engine_factory", _ALL_FOUR_FACTORIES)
def test_tone_of_speech_subjective_perception_across_all_four_prototypes(engine_factory):
    eng = engine_factory()
    res = run_scenario_tone_of_speech(eng)
    c_ok = res["cases"]["teasing_close_steady"]
    c_raw = res["cases"]["teasing_while_ashamed"]
    c_sarc = res["cases"]["sarcastic_subtle_tagged"]
    c_strain = res["cases"]["warm_through_shaking_body"]

    # 1. Steady friend teasing -> perceived as teasing, lifts happiness/love (NOT anger/betrayal!).
    assert c_ok["metadata"]["speech_tone"]["perceived_tone"] == "teasing"
    assert c_ok["applied_deltas"].get("happiness", 0) > 10
    assert c_ok["applied_deltas"].get("anger", 0) <= 0

    # 2. Same teasing remark when listener is deeply ashamed -> perceived as mocking, hurts!
    assert c_raw["metadata"]["speech_tone"]["perceived_tone"] == "mocking"
    assert c_raw["applied_deltas"].get("shame", 0) > 10
    assert c_raw["applied_deltas"].get("happiness", 0) < 0

    # 3. Polite sarcasm WITH [tone=sarcastic] -> caught by ALL 4 engines (even Proto A & B!).
    assert c_sarc["metadata"]["speech_tone"]["perceived_tone"] == "sarcastic"
    assert c_sarc["applied_deltas"].get("happiness", 0) < 0
    assert c_sarc["after_families"]["shame"] > FAMILY_BASELINES["shame"] + 15

    # 4. Warm words through an overloaded shaking body -> leaks as strained (concern, NOT calm!).
    assert c_strain["metadata"]["speech_tone"]["perceived_tone"] == "strained"
    assert c_strain["metadata"]["speech_tone"]["strained_leak"] is True
    assert c_strain["applied_deltas"].get("fear", 0) > 5
    assert c_strain["applied_deltas"].get("calm", 0) < 0


def test_emotion_lab_flask_endpoints_end_to_end():
    from prototypes.emotions.lab_app import create_lab_app

    app = create_lab_app()
    client = app.test_client()

    r_home = client.get("/")
    assert r_home.status_code == 200
    assert b"VirtualWorld Emotion Lab - Prototypes A / B / C / D" in r_home.data

    r_init = client.post("/api/lab/init", json={"scenario": "taco_bell_date"})
    assert r_init.status_code == 200
    init_data = r_init.get_json()
    assert "miki doki" in init_data["characters"]
    assert len(init_data["scenarios"]) >= 1

    r_step = client.post(
        "/api/lab/step",
        json={
            "character": "miki doki",
            "kind": "speech",
            "source_name": "jake halloway",
            "speech_text": "You're a bitch.",
            "summary": "Jake snapped at her under the Taco Bell sign.",
            "witnesses": ["Sammy"],
            "expectations": ["Expected him to be kind"],
            "vitals": {"Energy": 30, "Hunger": 75, "Temperature": 35.0},
            "traits": ["guarded"],
            "live_lm": False,
            "run_track2": True,
        },
    )
    assert r_step.status_code == 200
    step_data = r_step.get_json()
    for key in ("A", "B", "C", "D"):
        assert key in step_data["results"]
        assert "after_families" in step_data["results"][key]
        assert "autonomic" in step_data["results"][key]
        assert step_data["results"][key]["prompt_your_state"] != ""
    assert step_data["track2"] is not None

    r_tick = client.post("/api/lab/tick", json={"character": "miki doki", "ticks": 2})
    assert r_tick.status_code == 200
    tick_data = r_tick.get_json()
    for key in ("A", "B", "C", "D"):
        assert "after_families" in tick_data["results"][key]
        assert "autonomic" in tick_data["results"][key]


def test_task997_per_target_emotions_persona_tells_and_volume_slip():
    from app import create_app
    from player import Player
    from prototypes.emotions.autonomic import compute_involuntary_volume_slip
    from prototypes.emotions.proto_a_matrix import ProtoAMatrixEngine
    from prototypes.emotions.schema import EmotionEvent
    from prototypes.emotions.viwo_adapter import ViwoEmotionHarness

    app = create_app({"TESTING": True})
    world = app.world

    astrid = Player("Astrid")
    astrid.stats["WIS"] = 14
    astrid.traits = {"protective": 1, "honest": 1, "composed": 1}
    astrid.persona = {
        "personality": {
            "habits": ["rakes_hair_back_when_tense"],
            "quirks": ["smooths_scarred_eyebrow"],
        }
    }
    sammy = Player("Sammy")
    sammy.traits = {"impulsive": 1, "jittery": 1}
    sammy.persona = {
        "personality": {
            "habits": ["chews_lip_gloss"],
            "quirks": ["glasses_fog_when_flustered"],
        }
    }
    world.add_player(astrid)
    world.add_player(sammy)

    h = ViwoEmotionHarness(world, ProtoAMatrixEngine())

    # 1. Per-target contrasting live emotions: fear for Sammy, guilt toward Maria, anger at Jake.
    r_sammy = h.step_event(
        "Astrid",
        EmotionEvent(
            kind="threat",
            summary="Realized Sammy is in over her head with four girls sharing one boy.",
            source_name="Sammy",
            target_name="Sammy",
            tick=1,
            tags=["threat"],
        ),
    )
    r_maria = h.step_event(
        "Astrid",
        EmotionEvent(
            kind="action",
            summary="Lied to Maria across the yard about flan on Sammy's coat.",
            source_name="Maria",
            target_name="Maria",
            tick=2,
            tags=["transgression", "cover_lie"],
        ),
    )
    r_jake = h.step_event(
        "Astrid",
        EmotionEvent(
            kind="speech",
            summary="Jake called Sammy 'my Sammy' and claimed he was completely innocent.",
            source_name="Jake",
            target_name="Jake",
            speech_text="Please don't murder my Sammy. I'm completely innocent.",
            tick=3,
            tags=["insult"],
        ),
    )
    assert "Sammy" in r_jake.target_families
    assert "Maria" in r_jake.target_families
    assert "Jake" in r_jake.target_families
    assert r_jake.target_families["Maria"].get("guilt", 0) > 20.0
    assert r_jake.target_families["Jake"].get("anger", 0) > 20.0
    assert "Sammy" in r_jake.prompt_your_state or "Maria" in r_jake.prompt_your_state or "Jake" in r_jake.prompt_your_state

    # 2. Personal habit/quirk tell surfaces in observer tells when stressed.
    r_sam = h.step_event(
        "Sammy",
        EmotionEvent(
            kind="exposure",
            summary="Astrid overheard her mention marrying four people.",
            source_name="Astrid",
            tick=4,
            witnesses=["Kayla", "Kyrie", "Zoe"],
            tags=["hid_mistake"],
        ),
    )
    assert "lip" in r_sam.observer_tells_normal.lower() or "glasses" in r_sam.observer_tells_normal.lower()

    # 3. Flustered involuntary volume slip: impulsive Sammy trying to whisper under high arousal slips to normal!
    actual_vol, slipped, reason = compute_involuntary_volume_slip(
        "whisper",
        {"heart_rate": 55.0, "breathing": 45.0, "vasomotor": 50.0, "muscle_tension": 45.0},
        regulation_capacity=48.0,
        player=sammy,
        overloaded=False,
    )
    assert actual_vol == "normal"
    assert slipped is True
    assert reason == "flustered_volume_slip"
