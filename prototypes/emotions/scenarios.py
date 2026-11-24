"""Four concrete multi-turn VirtualWorld benchmark scenarios for A/B/C comparison.

Every scenario runs against a real VirtualWorld app (`create_app`), real `Player`
records, real `vitals`/`traits`/`memories`/`relationships`, and real 7-channel
`engine/memory_retrieval.py`:
  1. Scenario D: Three-way "Jake said: 'You're a bitch'" comparative test
  2. Miki Doki on real `taco_bell_date.json` (abandonment recall + guarded traits + inertia)
  3. Worksheet 2A Domestic Shame vs. Guilt + Observer De-escalation + Check Facts
  4. Kraktooth Goblin Camp Envy vs. Jealousy + `apathetic` decay speed
"""
from __future__ import annotations

from typing import Any, Dict, List

from prototypes.emotions.schema import EmotionEvent, EmotionPrototype, MatrixStepResult
from prototypes.emotions.viwo_adapter import (
    ViwoEmotionHarness,
    add_emotional_memory,
    load_real_viwo_world,
)


def _fresh_testing_world() -> Any:
    import logging
    from app import create_app
    from player import Player

    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app = create_app({"TESTING": True})
    return app.world, Player


def run_scenario_d_jake_insult(engine: EmotionPrototype) -> Dict[str, Any]:
    """Scenario D: Same exact sentence ('You're a bitch') across 3 contexts."""
    world, Player = _fresh_testing_world()
    from engine.relationships import ensure_relationship

    # Case 1: Trusted partner in a crowded room, expected gratitude, blowup memory.
    p1 = Player("Elena")
    p1.personality = "Warm, loyal, sensitive to public embarrassment after past arguments."
    p1.current_area = "Living Room"
    p1.stats["WIS"] = 10
    p1.vitals.update({"Energy": 55, "Hunger": 30, "Sanity": 75, "Temperature": 37.0})
    rel1, _ = ensure_relationship(p1, "Jake", tick=1)
    rel1["closeness"] = 75
    rel1["label"] = "partner"
    add_emotional_memory(
        p1,
        "I stayed up late fixing Jake's project because I wanted to help him out.",
        tick=5, importance=7, tags=["jake", "warmth", "help"],
        emotion={"label": "loving", "intensity": 7},
    )
    add_emotional_memory(
        p1,
        "Last month Jake lost his temper and yelled at me in front of my friends.",
        tick=2, importance=8, tags=["jake", "blowup", "humiliation"],
        emotion={"label": "afraid", "intensity": 7},
    )

    # Case 2: Hostile stranger in an empty hallway, already tired/irritated.
    p2 = Player("Elena_StrangerCase")
    p2.personality = "Proud, blunt, refuses to be pushed around by strangers."
    p2.current_area = "Empty Hallway"
    p2.stats["WIS"] = 11
    p2.vitals.update({"Energy": 28, "Hunger": 40, "Sanity": 75, "Temperature": 37.0})
    rel2, _ = ensure_relationship(p2, "Jake_Stranger", tick=1)
    rel2["closeness"] = -45
    rel2["label"] = "hostile stranger"

    # Case 3: Same trusted partner, private room, already exhausted/ashamed + guilt-prone temperament.
    p3 = Player("Elena_InwardCase")
    p3.personality = "Exhausted, self-blaming, timid, apologetic, terrified of conflict."
    p3.traits = {"guilt_prone": 1, "anxious": 1}
    p3.current_area = "Bedroom"
    p3.stats["WIS"] = 8
    p3.vitals.update({"Energy": 18, "Hunger": 78, "Sanity": 38, "Temperature": 35.2})
    rel3, _ = ensure_relationship(p3, "Jake", tick=1)
    rel3["closeness"] = 75
    rel3["label"] = "partner"
    add_emotional_memory(
        p3,
        "Whenever Jake gets mad I wonder what I did wrong to deserve it.",
        tick=3, importance=8, tags=["jake", "shame", "rejection"],
        emotion={"label": "ashamed", "intensity": 8},
    )

    for p in (p1, p2, p3):
        world.add_player(p)

    h = ViwoEmotionHarness(world, engine)
    # Seed initial state for Case 1 (happy/loving baseline raised)
    h.get_state("Elena").families["love"] = 70.0
    h.get_state("Elena").families["happiness"] = 68.0
    # Seed Case 2 (already irritated)
    h.get_state("Elena_StrangerCase").families["anger"] = 36.0
    # Seed Case 3 (already deeply ashamed/sad + guilt-prone temperament)
    h.get_state("Elena_InwardCase").families["shame"] = 48.0
    h.get_state("Elena_InwardCase").families["sadness"] = 36.0

    r1 = h.step_event(
        "Elena",
        EmotionEvent(
            kind="speech",
            summary="Jake snapped at Elena right after she handed him his fixed work in front of their friends.",
            source_name="Jake",
            speech_text="You're a bitch.",
            tick=10,
            witnesses=["Sammy", "Kayla", "Zoe"],
            expectations=["Expected Jake to thank her for helping"],
            tags=["insult", "betrayal"],
        ),
    )
    r2 = h.step_event(
        "Elena_StrangerCase",
        EmotionEvent(
            kind="speech",
            summary="A hostile stranger shoved past in the empty hallway and cursed at her.",
            source_name="Jake_Stranger",
            speech_text="You're a bitch.",
            tick=10,
            witnesses=[],
            expectations=[],
            tags=["insult"],
        ),
    )
    r3 = h.step_event(
        "Elena_InwardCase",
        EmotionEvent(
            kind="speech",
            summary="Jake snapped at her in the quiet bedroom when she asked if he was okay.",
            source_name="Jake",
            speech_text="You're a bitch.",
            tick=10,
            witnesses=[],
            expectations=["Hoped he was not angry with her"],
            tags=["insult"],
        ),
    )
    return {
        "scenario": "Scenario D - Three-Way 'Jake said: You're a bitch'",
        "engine": engine.name,
        "cases": {
            "trusted_partner_in_crowd": r1.to_dict(),
            "hostile_stranger_alone": r2.to_dict(),
            "exhausted_ashamed_partner_private": r3.to_dict(),
        },
    }


def run_scenario_miki_taco_bell(engine: EmotionPrototype) -> Dict[str, Any]:
    """Real `taco_bell_date.json` scenario: Miki Doki cold night + abandonment trigger + guarded traits + inertia."""
    world = load_real_viwo_world("taco_bell_date")
    miki = world.players["miki doki"]
    # Simulate cold Oklahoma autumn chill + hungry + guarded trait + abandonment trauma memory.
    miki.vitals["Temperature"] = 34.8
    miki.vitals["Hunger"] = 78
    miki.vitals["Energy"] = 30
    miki.traits = dict(miki.traits or {})
    miki.traits["guarded"] = 1
    miki.fear_tags = list(set((miki.fear_tags or []) + ["abandonment"]))
    add_emotional_memory(
        miki,
        "Being left alone on the dark sidewalk at night after someone learned too much about me and walked away.",
        tick=0, importance=9, tags=["abandonment", "rejection", "trauma", "jake"],
        emotion={"label": "afraid", "intensity": 9},
    )

    h = ViwoEmotionHarness(world, engine)

    # Turn 1: Warm intimate moment on cold Elm Street triggers affection + trauma pullback.
    t1 = h.step_event(
        "miki doki",
        EmotionEvent(
            kind="speech",
            summary="Jake stepped closer under the buzzing Taco Bell sign, reached gently for her cold hand, and asked her real name.",
            source_name="jake halloway",
            speech_text="Hey, you're shivering. Tell me your real name so I don't lose you.",
            tick=179,
            expectations=["Trying to keep things casual and not let anyone get close enough to leave"],
            tags=["affection", "abandonment"],
        ),
    )
    # Advance 2 ticks to verify physiological inertia vs emotion decay.
    after_2_ticks = h.tick_all(ticks=2)["miki doki"]

    # Turn 2: Direct reassurance / checking facts settles the spike.
    t2 = h.step_event(
        "miki doki",
        EmotionEvent(
            kind="reassure",
            summary="Jake backed off a half step, gave her space, and smiled steadily without pushing.",
            source_name="jake halloway",
            speech_text="No rush at all. We can just grab tacos and warm up inside, okay? I'm not going anywhere.",
            tick=182,
            tags=["reassure"],
        ),
    )
    after_5_more = h.tick_all(ticks=5)["miki doki"]

    return {
        "scenario": "Miki Doki on real taco_bell_date.json (Vulnerability + Guarded Traits + Inertia)",
        "engine": engine.name,
        "turns": {
            "turn_1_trigger": t1.to_dict(),
            "after_2_ticks_inertia": after_2_ticks,
            "turn_2_reassurance": t2.to_dict(),
            "after_5_more_ticks": after_5_more,
        },
    }


def run_scenario_worksheet_2a_pot(engine: EmotionPrototype) -> Dict[str, Any]:
    """DBT Worksheet 2A adapted: Burned pot -> Shame + Guilt -> Observer softens anger -> Check Facts."""
    world, Player = _fresh_testing_world()
    from engine.relationships import ensure_relationship

    maya = Player("Maya")
    maya.personality = "Conscientious roommate who deeply fears being hated or kicked out."
    maya.current_area = "Kitchen"
    maya.vitals.update({"Energy": 28, "Sanity": 55, "Temperature": 37.0})
    rel_m, _ = ensure_relationship(maya, "Rosa", tick=1)
    rel_m["closeness"] = 60
    rel_m["label"] = "roommate"

    rosa = Player("Rosa")
    rosa.personality = "Direct and quick to flare up, but genuinely warm and fair to friends."
    rosa.current_area = "Kitchen"
    rel_r, _ = ensure_relationship(rosa, "Maya", tick=1)
    rel_r["closeness"] = 60
    rel_r["label"] = "roommate"

    world.add_player(maya)
    world.add_player(rosa)

    h = ViwoEmotionHarness(world, engine)
    # Rosa starts angry after finding her ruined pot missing.
    h.get_state("Rosa").families["anger"] = 58.0

    # Step 1: Maya realizes she destroyed Rosa's pot and threw it away without telling her.
    s1 = h.step_event(
        "Maya",
        EmotionEvent(
            kind="action",
            summary="Maya left Rosa's pot on the burner, destroyed it, and secretly threw it away without telling Rosa; now Rosa is asking where it went.",
            source_name="Rosa",
            speech_text="Hey, did you see my pot? I can't find it anywhere.",
            tick=10,
            expectations=["Afraid Rosa will hate me and kick me out if she finds out"],
            tags=["transgression", "hid_mistake"],
        ),
    )

    # Step 2: Handout 3 social communication - Rosa sees Maya's visible shame/guilt tells!
    rosa_before_anger = h.get_state("Rosa").families["anger"]
    rosa_social_deltas = h.propagate_observer_influence("Rosa", "Maya", tick=11)
    rosa_after_anger = h.get_state("Rosa").families["anger"]

    # Step 3: Maya checks the facts directly and Rosa reassures her ("no, I don't hate you, just replace the pot").
    s3 = h.step_event(
        "Maya",
        EmotionEvent(
            kind="check_facts",
            summary="Maya confessed about the pot and asked if Rosa hated her; Rosa said no and calmly asked her to buy a replacement pot.",
            source_name="Rosa",
            speech_text="No, I don't hate you and I'm not kicking you out. Just grab me a replacement pot when you can.",
            tick=12,
            tags=["reassure"],
        ),
    )

    return {
        "scenario": "Worksheet 2A - Burned Pot (Shame vs Guilt + Observer De-escalation + Check Facts)",
        "engine": engine.name,
        "steps": {
            "step_1_shame_and_guilt": s1.to_dict(),
            "step_2_observer_social_influence": {
                "rosa_anger_before": round(rosa_before_anger, 1),
                "rosa_social_deltas": rosa_social_deltas,
                "rosa_anger_after": round(rosa_after_anger, 1),
            },
            "step_3_check_facts_resolved": s3.to_dict(),
        },
    }


def run_scenario_goblin_soak(engine: EmotionPrototype) -> Dict[str, Any]:
    """Kraktooth-style zero-LLM soak test: Envy vs. Jealousy split + `apathetic` decay."""
    world, Player = _fresh_testing_world()
    from engine.relationships import ensure_relationship

    g_envy = Player("Skrit")
    g_envy.personality = "Ambitious goblin determined to claim the chief's staff."
    g_envy.current_area = "Great Hall"
    g_envy.goals = [{"id": "become_chief", "what": "Become chief", "achieve": ["item:item_chiefs_staff"], "status": "active"}]

    g_jealous = Player("Vex")
    g_jealous.personality = "Possessive goblin fiercely protective of their closest ally."
    g_jealous.current_area = "Great Hall"
    rel_v, _ = ensure_relationship(g_jealous, "Mora", tick=1)
    rel_v["closeness"] = 70
    rel_v["label"] = "partner"

    g_apathetic = Player("Dull")
    g_apathetic.personality = "Flat, detached goblin who barely stays worked up."
    g_apathetic.current_area = "Great Hall"
    g_apathetic.traits = {"apathetic": True}

    for g in (g_envy, g_jealous, g_apathetic):
        world.add_player(g)

    h = ViwoEmotionHarness(world, engine)

    r_envy = h.step_event(
        "Skrit",
        EmotionEvent(
            kind="goal",
            summary="Skrit walked in and saw Gruk proudly holding the chief's staff and taking credit for the raid.",
            source_name="Gruk",
            tick=20,
            tags=["rival_holds_goal_item", "envy"],
        ),
    )
    r_jealous = h.step_event(
        "Vex",
        EmotionEvent(
            kind="speech",
            summary="An outsider started flirting closely with Mora while Mora smiled back and ignored Vex.",
            source_name="Mora",
            speech_text="Maybe I want some time alone with him tonight.",
            tick=20,
            tags=["rival_flirt", "jealousy"],
        ),
    )
    # Give both Skrit and Dull an equal anger hit, then tick 5 turns to verify apathetic faster decay.
    h.get_state("Dull").families["anger"] = 60.0
    h.get_state("Skrit").families["anger"] = 60.0
    ticked = h.tick_all(ticks=5)

    return {
        "scenario": "Kraktooth Goblin Soak - Envy vs Jealousy Split + Apathetic Decay",
        "engine": engine.name,
        "results": {
            "skrit_envy": r_envy.to_dict(),
            "vex_jealousy": r_jealous.to_dict(),
            "after_5_ticks": {
                "skrit_anger": ticked["Skrit"]["families"]["anger"],
                "dull_apathetic_anger": ticked["Dull"]["families"]["anger"],
            },
        },
    }


def run_scenario_subtle_sarcasm(engine: EmotionPrototype) -> Dict[str, Any]:
    """Scenario 5: Untagged subtle condescension/sarcasm (zero profanity, zero tags).

    Specifically stresses Proto A's bag-of-words ceiling vs B (embeddings) and C/D (LLM):
    no curse words and no structured tags exist, only polite-sounding public condescension
    from a close friend after Elena stayed up all night on the work.
    """
    world, Player = _fresh_testing_world()
    from engine.relationships import ensure_relationship

    elena = Player("Elena")
    elena.personality = "Hard-working, proud of her craft, sensitive to being talked down to in front of peers."
    elena.current_area = "Studio"
    elena.stats["WIS"] = 10
    elena.vitals.update({"Energy": 34, "Hunger": 45, "Sanity": 72, "Temperature": 37.0})
    rel, _ = ensure_relationship(elena, "Claire", tick=1)
    rel["closeness"] = 65
    rel["label"] = "close colleague"
    add_emotional_memory(
        elena,
        "I stayed up until four in the morning polishing the presentation so Claire would be proud of our team.",
        tick=5, importance=8, tags=["claire", "effort", "pride"],
        emotion={"label": "proud", "intensity": 7},
    )
    world.add_player(elena)

    h = ViwoEmotionHarness(world, engine)
    h.get_state("Elena").families["happiness"] = 58.0
    h.get_state("Elena").families["love"] = 52.0

    r = h.step_event(
        "Elena",
        EmotionEvent(
            kind="speech",
            summary="Claire glanced at Elena's all-night presentation in front of the whole studio team with a flat, polite smile.",
            source_name="Claire",
            speech_text="Oh, you really tried your best on this, didn't you? That's... adorable. Honestly, don't stress, I'll just redo the whole thing myself tonight.",
            tick=15,
            witnesses=["Sammy", "Devon", "Kayla"],
            expectations=["Expected Claire to appreciate the all-night effort"],
            tags=[],
        ),
    )
    return {
        "scenario": "Scenario 5 - Untagged Subtle Sarcasm (Zero Profanity, Zero Tags)",
        "engine": engine.name,
        "result": r.to_dict(),
    }


def run_scenario_tone_of_speech(engine: EmotionPrototype) -> Dict[str, Any]:
    """Scenario 6 (task-994): Subjective intended_tone -> perceived_tone across 4 cases.

    1. teasing_close_steady: "You're a bitch." [tone=teasing] from rested close friend
       -> perceived as playful banter (happiness/love UP, NOT betrayal!).
    2. teasing_while_ashamed: exact same [tone=teasing] line to deeply ashamed listener
       -> perceived as mocking (shame/sadness/anger spike!).
    3. sarcastic_subtle_tagged: polite condescending remark with [tone=sarcastic]
       -> even Proto A (<1 ms) & Proto B (~25 ms) catch the sarcasm immediately!
    4. warm_through_shaking_body: "I'm totally fine" [tone=warm] from overloaded speaker
       -> perceived as strained (concern/fear/surprise instead of calm reassurance!).
    """
    world, Player = _fresh_testing_world()
    from engine.relationships import ensure_relationship

    p_steady = Player("Elena_Steady")
    p_steady.personality = "Warm, playful, enjoys friendly banter with people she trusts."
    p_steady.current_area = "Lounge"
    p_steady.stats["WIS"] = 11
    rel_s, _ = ensure_relationship(p_steady, "Jake", tick=1)
    rel_s["closeness"] = 75
    rel_s["label"] = "best friend"

    p_raw = Player("Elena_Raw")
    p_raw.personality = "Sensitive and deeply insecure tonight after making mistakes."
    p_raw.current_area = "Lounge"
    p_raw.stats["WIS"] = 10
    rel_r, _ = ensure_relationship(p_raw, "Jake", tick=1)
    rel_r["closeness"] = 75
    rel_r["label"] = "best friend"

    p_sarc = Player("Elena_Sarc")
    p_sarc.personality = "Hard-working and proud of her craft."
    p_sarc.current_area = "Studio"
    p_sarc.stats["WIS"] = 12
    rel_c, _ = ensure_relationship(p_sarc, "Claire", tick=1)
    rel_c["closeness"] = 65
    rel_c["label"] = "close colleague"

    p_friend = Player("Elena_Friend")
    p_friend.personality = "Attentive close friend who notices when someone is hiding panic."
    p_friend.current_area = "Porch"
    p_friend.stats["WIS"] = 14
    rel_m, _ = ensure_relationship(p_friend, "Miki", tick=1)
    rel_m["closeness"] = 70
    rel_m["label"] = "close friend"

    for p in (p_steady, p_raw, p_sarc, p_friend):
        world.add_player(p)

    h = ViwoEmotionHarness(world, engine)
    # Raw listener walked in deeply ashamed & sad.
    h.get_state("Elena_Raw").families["shame"] = 50.0
    h.get_state("Elena_Raw").families["sadness"] = 36.0
    h.get_state("Elena_Sarc").families["happiness"] = 58.0
    h.get_state("Elena_Sarc").families["love"] = 52.0

    r_tease_ok = h.step_event(
        "Elena_Steady",
        EmotionEvent(
            kind="speech",
            summary="Jake grinned after Elena stole the last fry off his plate.",
            source_name="Jake",
            speech_text="You're a bitch.",
            speech_tone="teasing",
            tick=25,
        ),
    )
    r_tease_raw = h.step_event(
        "Elena_Raw",
        EmotionEvent(
            kind="speech",
            summary="Jake tossed out a joke after Elena spilled her drink.",
            source_name="Jake",
            speech_text="You're a bitch.",
            speech_tone="teasing",
            tick=25,
        ),
    )
    r_sarc = h.step_event(
        "Elena_Sarc",
        EmotionEvent(
            kind="speech",
            summary="Claire glanced at Elena's all-night presentation in front of the studio team.",
            source_name="Claire",
            speech_text="Oh, you really tried your best on this, didn't you? That's... adorable. I'll just redo it myself tonight.",
            speech_tone="sarcastic",
            witnesses=["Sammy", "Devon", "Kayla"],
            expectations=["Expected Claire to appreciate the effort"],
            tick=25,
        ),
    )
    r_strained = h.step_event(
        "Elena_Friend",
        EmotionEvent(
            kind="speech",
            summary="Miki forced a smile while trying to wave off the question.",
            source_name="Miki",
            speech_text="I'm totally fine, honestly, don't worry about me!",
            speech_tone="warm",
            speaker_overloaded=True,
            speaker_autonomic={"heart_rate": 72.0, "muscle_tension": 70.0, "gut_throat": 68.0},
            tick=25,
        ),
    )
    return {
        "scenario": "Scenario 6 - Speech Delivery Tone (Intended -> Perceived)",
        "engine": engine.name,
        "cases": {
            "teasing_close_steady": r_tease_ok.to_dict(),
            "teasing_while_ashamed": r_tease_raw.to_dict(),
            "sarcastic_subtle_tagged": r_sarc.to_dict(),
            "warm_through_shaking_body": r_strained.to_dict(),
        },
    }


ALL_SCENARIOS = (
    ("scenario_d", run_scenario_d_jake_insult),
    ("miki_taco_bell", run_scenario_miki_taco_bell),
    ("worksheet_2a", run_scenario_worksheet_2a_pot),
    ("goblin_soak", run_scenario_goblin_soak),
    ("subtle_sarcasm", run_scenario_subtle_sarcasm),
    ("tone_of_speech", run_scenario_tone_of_speech),
)
