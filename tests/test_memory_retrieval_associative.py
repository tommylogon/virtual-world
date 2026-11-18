"""Targeted unit tests for Associative Memory Retrieval 3.0 (task-908).

Verifies:
1. Multi-facet intersection surge (Jake + olives > Jake alone or olives alone).
2. Zero-padding elimination (empty room returns 0 memories; no fake top-3).
3. Temporal validity window (invalid_at <= current_tick is excluded).
4. Bodily need probe (need:food surfaces food/snack memories).
5. Open question tripwires (question surfaces when watched entity enters perception).
6. Explanations and lane partitioning.
"""

import pytest
from engine.memory_retrieval import (
    extract_cues,
    is_active_memory,
    is_open_question_match,
    retrieve_associative_memories,
    score_memory,
)


class MockPlayer:
    def __init__(self, name="Kayla", memories=None):
        self.name = name
        self.memories = list(memories or [])


def test_intersection_surge_favors_multi_facet_match():
    # Kayla has three memories:
    # A: Jake hates olives (mentions both Jake and olives)
    # B: Jake borrowed my notes (mentions Jake only)
    # C: Olives are salty (mentions olives only)
    mem_a = {
        "id": "mem_a",
        "text": "Jake wrinkled his nose and told me he despises black olives.",
        "entity_ids": ["player_jake_halloway"],
        "tags": ["jake", "food", "olives"],
        "importance": 6,
        "tick": 10,
    }
    mem_b = {
        "id": "mem_b",
        "text": "Jake borrowed my chemistry notes during study period.",
        "entity_ids": ["player_jake_halloway"],
        "tags": ["jake", "school"],
        "importance": 6,
        "tick": 10,
    }
    mem_c = {
        "id": "mem_c",
        "text": "Black olives taste like salty rubber tires on cheap pizza.",
        "entity_ids": ["item_pizza"],
        "tags": ["food", "olives"],
        "importance": 6,
        "tick": 10,
    }

    player = MockPlayer(memories=[mem_b, mem_c, mem_a])

    # Situation: Jake is present in the room, and someone says "want olives with that?"
    cues = {
        "actors": ["player_jake_halloway", "Jake Halloway"],
        "dialogue": ["want olives with that"],
        "items": ["slice of pizza"],
        "area_id": "area_cafeteria",
    }

    result = retrieve_associative_memories(
        player, cues, tick=20, max_results=5, min_score=1.0, explain=True, do_reinforce=False
    )
    recalled = result["memories"]
    assert len(recalled) >= 1
    assert recalled[0]["id"] == "mem_a", f"Expected intersection memory mem_a to win, got {recalled[0]['id']}"

    # Intersection boost should be credited in explanation
    explanation = recalled[0]["explanation"]
    assert explanation["intersection_boost"] > 0
    assert "actor" in explanation["facets_hit"]
    assert "dialogue" in explanation["facets_hit"]


def test_zero_padding_eliminated_for_irrelevant_situation():
    # Player has memories about a forest and a library
    memories = [
        {"id": "m1", "text": "Deep in the dark forest the owls shriek.", "importance": 5, "tick": 2},
        {"id": "m2", "text": "Studied ancient runes in the quiet library.", "importance": 5, "tick": 5},
    ]
    player = MockPlayer(memories=memories)

    # Empty cafeteria, no relevant dialogue, no needs, no matching actors
    cues = {
        "actors": [],
        "dialogue": [],
        "items": ["cafeteria tray"],
        "area_id": "area_cafeteria",
    }

    result = retrieve_associative_memories(
        player, cues, tick=50, max_results=6, min_score=1.5, do_reinforce=False
    )
    # Must NOT pad with top 3 when score is low!
    assert len(result["memories"]) == 0, f"Expected 0 padded memories, got {len(result['memories'])}"


def test_temporal_validity_window_filters_invalidated_memories():
    # A memory that was true at tick 10 but invalidated at tick 50
    stale_belief = {
        "id": "mem_stale",
        "text": "I hid a bag of Takis in my bedroom desk drawer.",
        "entity_ids": ["item_takis", "area_bedroom"],
        "tags": ["food", "takis"],
        "tick": 10,
        "valid_at": 10,
        "invalid_at": 50,  # Checked drawer at tick 50 and it was empty!
    }
    fresh_belief = {
        "id": "mem_fresh",
        "text": "Bought a fresh granola bar from the vending machine.",
        "entity_ids": ["item_granola_bar"],
        "tags": ["food", "snack"],
        "tick": 55,
        "valid_at": 55,
        "invalid_at": None,
    }

    player = MockPlayer(memories=[stale_belief, fresh_belief])

    # Hungry at tick 60
    cues = {
        "needs": ["need:food"],
        "area_id": "area_hallway",
    }

    result = retrieve_associative_memories(
        player, cues, tick=60, min_score=1.0, do_reinforce=False, explain=True
    )
    recalled_ids = [m["id"] for m in result["memories"]]
    assert "mem_stale" not in recalled_ids, "Stale invalidated memory must not surface in active recall"
    assert "mem_fresh" in recalled_ids, "Fresh memory must surface when hungry"


def test_bodily_need_probe_surfaces_food_without_dialogue():
    snack_memory = {
        "id": "snack_1",
        "text": "Stored extra beef jerky in my backpack pocket.",
        "entity_ids": ["item_backpack"],
        "tags": ["food", "snack", "jerky"],
        "importance": 6,
        "tick": 15,
    }
    history_memory = {
        "id": "hist_1",
        "text": "Mr. Harrison lectured about the Cold War for forty minutes.",
        "tags": ["school", "history"],
        "importance": 4,
        "tick": 12,
    }

    player = MockPlayer(memories=[history_memory, snack_memory])

    # Sitting silently in classroom, but starving
    cues = {
        "actors": [],
        "dialogue": [],
        "needs": ["need:food"],
        "area_id": "area_classroom",
    }

    result = retrieve_associative_memories(
        player, cues, tick=30, min_score=1.0, do_reinforce=False
    )
    recalled = result["memories"]
    assert len(recalled) == 1
    assert recalled[0]["id"] == "snack_1"


def test_open_question_tripwire_matches_perception():
    # Kayla has an open question wondering who took her strawberry gum
    question_entry = {
        "id": "q_gum",
        "text": "Who took my unopened pack of strawberry gum from my gym locker?",
        "category": "question",
        "type": "question",
        "watch_refs": ["item_gum", "concept:gum", "strawberry gum", "player_sammy_lopez"],
        "about": ["strawberry gum", "gym locker", "Sammy Lopez"],
        "hypotheses": [{"text": "Sammy might have taken it", "confidence": 0.4}],
        "status": "open",
        "answered_by": None,
    }
    normal_memory = {
        "id": "norm_1",
        "text": "Sammy borrowed my lipstick last Friday.",
        "entity_ids": ["player_sammy_lopez"],
        "importance": 5,
        "tick": 5,
    }

    player = MockPlayer(memories=[normal_memory, question_entry])

    # Situation: Sammy Lopez is standing nearby, and someone mentions "bubblegum"
    cues = {
        "actors": ["player_sammy_lopez", "Sammy Lopez"],
        "dialogue": ["blowing giant bubblegum bubbles"],
        "area_id": "area_cafeteria",
    }

    result = retrieve_associative_memories(
        player, cues, tick=20, do_reinforce=False
    )
    questions_lane = result["lanes"]["open_questions"]
    assert len(questions_lane) == 1
    assert questions_lane[0]["id"] == "q_gum"
    assert "matched_refs" in questions_lane[0]


def test_dislike_tags_accelerate_decay_and_suppress_passive_recall():
    from engine import memory_dynamics as md
    from engine.memory_retrieval import score_memory

    politics_mem = {
        "id": "mem_pol",
        "text": "Heard someone talking about city council politics.",
        "tags": ["politics"],
        "importance": 3,
        "tick": 10,
        "location": "area_cafeteria",
        "activation": 1.0,
    }
    neutral_mem = {
        "id": "mem_neu",
        "text": "Saw a blue backpack by the cafeteria door.",
        "tags": ["backpack"],
        "importance": 3,
        "tick": 10,
        "location": "area_cafeteria",
        "activation": 1.0,
    }
    player = MockPlayer(memories=[politics_mem, neutral_mem])
    player.dislike_tags = ["politics"]
    player.interest_tags = ["skateboarding"]
    player.fear_tags = []

    md.apply_decay(player, rate=0.1, tick=15)
    # Politics memory decays 2x faster than neutral low-importance memory
    assert politics_mem["activation"] < neutral_mem["activation"]

    cues = extract_cues({
        "area_id": "area_cafeteria",
        "dislike_tags": ["politics"],
        "interest_tags": ["skateboarding"],
    })
    pol_score, pol_bd = score_memory(politics_mem, cues, current_tick=15)
    neu_score, neu_bd = score_memory(neutral_mem, cues, current_tick=15)
    assert pol_bd["dislike_dampened"] is True
    assert neu_bd["dislike_dampened"] is False
    assert pol_score < neu_score


def test_retrieval_bug586_speaker_and_addressee_attribution():
    # Identical quoted words from two different speakers must bind to the actual speaker.
    mem_jake = {
        "id": "mem_jake",
        "text": 'Jake said to Kayla: "Meet me by the boathouse at midnight."',
        "entity_ids": ["player_jake"],
        "importance": 5,
        "tick": 10,
    }
    mem_marcus = {
        "id": "mem_marcus",
        "text": 'Marcus said to Kayla: "Meet me by the boathouse at midnight."',
        "entity_ids": ["player_marcus"],
        "importance": 5,
        "tick": 10,
    }
    mem_topic = {
        "id": "mem_topic",
        "text": "The old boathouse roof leaks during midnight storms.",
        "importance": 5,
        "tick": 10,
    }
    player = MockPlayer(name="Kayla", memories=[mem_jake, mem_marcus, mem_topic])

    cues_payload = {
        "actors": ["Jake", "Marcus"],
        "dialogue": [
            {
                "speaker": "Marcus",
                "target": "Kayla",
                "text": "Meet me by the boathouse at midnight.",
            }
        ],
        "query": "Meet me by the boathouse at midnight.",
    }
    res = retrieve_associative_memories(
        player, cues_payload, tick=20, max_results=5, min_score=1.0, explain=True, do_reinforce=False
    )
    by_id = {m["id"]: m for m in res["memories"]}
    assert res["memories"][0]["id"] == "mem_marcus"
    assert by_id["mem_marcus"]["explanation"]["channels"]["conversational"] > 0
    assert "speaker_bound" in by_id["mem_marcus"]["explanation"]["facets_hit"]
    assert by_id["mem_jake"]["explanation"]["channels"]["conversational"] == 0.0
    assert by_id["mem_marcus"]["score"] > by_id["mem_jake"]["score"]
    # Unattributed non-quote topic memory still recalls on overlapping tokens
    assert "mem_topic" in by_id

    # Same speaker, different addressee: matching addressee beats conflicting addressee
    mem_to_anna = {
        "id": "mem_to_anna",
        "text": 'Jake whispered to Anna: "Keep the silver key hidden."',
        "entity_ids": ["player_jake"],
        "importance": 5,
        "tick": 10,
    }
    mem_to_kayla = {
        "id": "mem_to_kayla",
        "text": 'Jake whispered to Kayla: "Keep the silver key hidden."',
        "entity_ids": ["player_jake"],
        "importance": 5,
        "tick": 10,
    }
    cue_addr = extract_cues(
        {
            "dialogue": [
                {"speaker": "Jake", "target": "Kayla", "text": "Keep the silver key hidden."}
            ]
        },
        player=player,
    )
    assert "player_jake" in cue_addr["actor_ids"]
    assert "player_kayla" not in cue_addr["actor_ids"]
    s_anna, bd_anna = score_memory(mem_to_anna, cue_addr, current_tick=20)
    s_kayla, bd_kayla = score_memory(mem_to_kayla, cue_addr, current_tick=20)
    assert bd_kayla["matched_target_bound"] is True
    assert bd_anna["matched_target_bound"] is False
    assert s_kayla > s_anna


def test_retrieval_bug587_emotion_current_and_multidimensional_affect():
    from engine import emotion as emo_mod

    # 1. player.emotion.current + 0..1 intensity is recognized (not dropped as empty)
    cues_live = extract_cues({"emotion": {"current": "afraid", "intensity": 0.8}})
    assert cues_live["emotion"] == "afraid"
    assert cues_live["emotion_intensity"] == pytest.approx(8.0)

    # 2. Neutral resting 0..100 emotion baseline map emits no active affect cues
    cues_baseline = extract_cues({"emotions": emo_mod.baseline()})
    assert cues_baseline["emotion"] == ""
    assert cues_baseline["emotion_vector"] == {}

    # 3. Mixed high-stakes emotions: afraid + guilty + affectionate
    emo_map = emo_mod.baseline()
    emo_map["afraid"] = 75.0
    emo_map["guilty"] = 50.0
    emo_map["affectionate"] = 60.0
    mixed_cues = extract_cues(
        {
            "actors": ["Jake"],
            "emotion": {"current": "afraid", "intensity": 0.75},
            "emotions": emo_map,
            "dialogue": ["cellar"],
        }
    )

    mem_secondary = {
        "id": "mem_sec",
        "text": "I felt deeply guilty about leaving the latch unbolted.",
        "memory_emotions": [{"label": "guilty", "intensity": 7}],
        "importance": 5,
        "tick": 10,
    }
    mem_single = {
        "id": "mem_single",
        "text": "The dark stairwell made me afraid.",
        "emotion": {"label": "afraid", "intensity": 7},
        "importance": 5,
        "tick": 10,
    }
    mem_multi = {
        "id": "mem_multi",
        "text": "Terrified and guilty, I still wanted to protect everyone.",
        "memory_emotions": [
            {"label": "afraid", "intensity": 8},
            {"label": "guilty", "intensity": 7},
            {"label": "affectionate", "intensity": 6},
        ],
        "importance": 5,
        "tick": 10,
    }
    mem_targeted = {
        "id": "mem_targeted",
        "text": "Jake cornered me near the cellar stairs.",
        "emotions": {
            "who": "Jake",
            "why": "he locked the cellar",
            "data": {"fear": 3, "affection": -4},
        },
        "importance": 5,
        "tick": 10,
    }

    _, bd_sec = score_memory(mem_secondary, mixed_cues, current_tick=20)
    _, bd_single = score_memory(mem_single, mixed_cues, current_tick=20)
    _, bd_multi = score_memory(mem_multi, mixed_cues, current_tick=20)
    _, bd_targeted = score_memory(mem_targeted, mixed_cues, current_tick=20)

    # Secondary dimension alone scores non-zero
    assert bd_sec["channels"]["emotional"] > 0
    assert "guilty" in bd_sec["matched_emotion_dimensions"]
    # Multi-dimensional overlap outscores single-dimension overlap
    assert bd_multi["channels"]["emotional"] > bd_single["channels"]["emotional"]
    # Target-bound emotions match actor + why, and negative affection (-4) does not match affectionate
    assert bd_targeted["channels"]["emotional"] > bd_single["channels"]["emotional"]
    assert "affectionate" not in bd_targeted["matched_emotion_dimensions"]


def test_retrieval_bug602_vector_store_and_channel7_semantic_recall(tmp_path):
    from engine.vector_store import VectorStore

    mem_match = {
        "id": "mem_vec_hit",
        "text": "Tucked the spare brass key under the ceramic planter.",
        "importance": 4,
        "tick": 5,
    }
    mem_ortho = {
        "id": "mem_vec_miss",
        "text": "Enjoyed peppermint tea on the porch.",
        "importance": 4,
        "tick": 5,
    }
    player = MockPlayer(name="Kayla", memories=[mem_ortho, mem_match])
    player.id = "player_kayla"

    store = VectorStore(str(tmp_path))
    store.upsert(
        [
            {"key": "Kayla::mem_vec_hit", "vector": [1.0, 0.0]},
            {"key": "Kayla::mem_vec_miss", "vector": [0.0, 1.0]},
        ],
        model="test",
        dims=2,
    )

    # Query shares zero keywords; relies on VectorStore query_vector + data_dir
    res = retrieve_associative_memories(
        player,
        {
            "query": "missing entrance unlock",
            "query_vector": [1.0, 0.0],
            "data_dir": str(tmp_path),
        },
        tick=20,
        min_score=1.0,
        explain=True,
        do_reinforce=False,
    )
    ids = [m["id"] for m in res["memories"]]
    assert "mem_vec_hit" in ids
    assert "mem_vec_miss" not in ids
    hit_entry = next(m for m in res["memories"] if m["id"] == "mem_vec_hit")
    assert hit_entry["explanation"]["channels"]["semantic"] > 0
    assert "semantic" in hit_entry["explanation"]["facets_hit"]

    # Zero/negative semantic score must not tag the semantic facet
    _, bd_zero = score_memory(
        mem_ortho,
        {"semantic_scores": {"mem_vec_miss": 0.0}},
        current_tick=20,
    )
    assert bd_zero["channels"]["semantic"] == 0.0
    assert "semantic" not in bd_zero["facets_hit"]


def test_retrieval_bug603_two_hop_ways_exact_locations_ids_inventory_and_stealth():
    from graph import EDGE_CARRYING, EDGE_CONNECTION, Edge, Node, WorldGraph

    g = WorldGraph()
    for nid, nname in [
        ("area_room_a", "Room A"),
        ("area_room_b", "Room B"),
        ("area_secret", "Secret Vault"),
        ("area_hall", "Hall"),
        ("area_hallway", "Hallway"),
    ]:
        g.add_node(Node(id=nid, type="area", name=nname))

    g.add_node(Node(id="way_b_a", type="way", name="Oak Door", properties={"current_state": "open"}))
    g.add_node(Node(id="way_b_secret", type="way", name="Hidden Panel", properties={"current_state": "hidden"}))
    g.add_edge(Edge(source="area_room_b", target="way_b_a", type=EDGE_CONNECTION, properties={"direction": "north"}))
    g.add_edge(Edge(source="way_b_a", target="area_room_a", type=EDGE_CONNECTION, properties={"direction": "enter"}))
    g.add_edge(Edge(source="area_room_b", target="way_b_secret", type=EDGE_CONNECTION, properties={"direction": "east"}))
    g.add_edge(Edge(source="way_b_secret", target="area_secret", type=EDGE_CONNECTION, properties={"direction": "enter"}))

    g.add_node(Node(id="player_kayla", type="character", name="Kayla"))
    g.add_node(Node(id="item_flashlight", type="item", name="Flashlight"))
    g.add_node(Node(id="item_hidden_dagger", type="item", name="Hidden Dagger", properties={"current_state": "hidden"}))
    g.add_edge(Edge(source="item_flashlight", target="player_kayla", type=EDGE_CARRYING))

    class _Sneaky:
        def __init__(self):
            self.name = "Sneaky Pete"
            self.id = "player_sneaky_pete"
            self.hidden = True
            self.stealthed = True
            self.conditions = ["hidden"]

    class _World:
        def __init__(self, graph):
            self.graph = graph
            self.time_ticks = 30
            self.players = {"Sneaky Pete": _Sneaky()}

        def _player_node_id(self, name):
            return f"player_{name.strip().lower().replace(' ', '_')}"

    world = _World(g)
    player = MockPlayer(name="Kayla", memories=[])
    player.id = "player_kayla"
    player.known = set()

    # 1. 2-hop way traversal: Room B discovers Room A (not way_b_a, not hidden Secret Vault)
    cues_b = extract_cues({"area_id": "Room B"}, world=world, player=player)
    assert "area_room_a" in cues_b["adjacent_area_ids"]
    assert "room a" in cues_b["adjacent_area_ids"]
    assert "way_b_a" not in cues_b["adjacent_area_ids"]
    assert "area_secret" not in cues_b["adjacent_area_ids"]

    mem_room_a = {"id": "m_a", "text": "Left a notebook on the table.", "location": "Room A", "importance": 5, "tick": 10}
    mem_secret = {"id": "m_sec", "text": "Gold bars stacked inside.", "location": "area_secret", "importance": 5, "tick": 10}
    s_a, bd_a = score_memory(mem_room_a, cues_b, current_tick=30)
    s_sec, bd_sec = score_memory(mem_secret, cues_b, current_tick=30)
    assert bd_a["channels"]["spatial"] == pytest.approx(1.5)
    assert bd_sec["channels"]["spatial"] == 0.0

    # 2. Substring false-positive eliminated: "Hall" does NOT match "Hallway"
    cues_hall = extract_cues({"area_id": "area_hall"}, world=world, player=player)
    mem_hallway = {"id": "m_hw", "text": "Dropped a glove.", "location": "area_hallway", "importance": 5, "tick": 10}
    _, bd_hw = score_memory(mem_hallway, cues_hall, current_tick=30)
    assert bd_hw["channels"]["spatial"] == 0.0

    # 3. Space-vs-underscore player entity_id mismatch resolved
    mem_space_id = {
        "id": "m_space",
        "text": "He handed over the spare key.",
        "entity_ids": ["player_jake halloway"],
        "importance": 5,
        "tick": 10,
    }
    cues_actor = extract_cues({"actors": ["Jake Halloway"]})
    _, bd_space = score_memory(mem_space_id, cues_actor, current_tick=30)
    assert bd_space["channels"]["social"] >= 2.5

    # 4. Carried inventory from graph + stealth filtering of hidden actors/items
    mem_flash = {"id": "m_flash", "text": "Tested the spare batteries.", "entity_ids": ["item_flashlight"], "importance": 5, "tick": 10}
    mem_sneaky = {"id": "m_sneak", "text": "Watched from the shadows.", "entity_ids": ["player_sneaky_pete"], "importance": 5, "tick": 10}
    mem_hidden_item = {"id": "m_hid_item", "text": "Tucked a blade away.", "entity_ids": ["item_hidden_dagger"], "importance": 5, "tick": 10}
    player.memories = [mem_flash, mem_sneaky, mem_hidden_item]

    res = retrieve_associative_memories(
        player,
        {
            "area_id": "Room B",
            "actors": ["Sneaky Pete"],
            "items": ["Hidden Dagger"],
        },
        world=world,
        tick=30,
        min_score=1.0,
        explain=True,
        do_reinforce=False,
    )
    recalled_ids = {m["id"] for m in res["memories"]}
    assert "m_flash" in recalled_ids
    assert "m_sneak" not in recalled_ids
    assert "m_hid_item" not in recalled_ids


def test_time_lock_denies_future_memories_by_tick_and_world_datetime():
    from virtual_world_engine import VirtualWorld
    from player import Player

    world = VirtualWorld()
    world.calendar_config = {
        "start_year": 2016,
        "start_month": 5,
        "start_day": 14,
        "days_per_month": 30,
        "months_per_year": 12,
    }
    world.time_per_tick_minutes = 5
    world.clock_start_hour = 8
    world.clock_start_minute = 0
    world.time_ticks = 10  # 2016-05-14T08:50:00

    assert world.datetime_for_tick(10) == "2016-05-14T08:50:00"
    assert world.calendar_label_for_tick(10) == "May 14, 2016 08:50"

    player = Player("Kayla")
    past_mem = player.add_memory(
        "Kayla met Zoe at the library in May.",
        tick=5,
        entity_ids=["player_Zoe"],
        location="Library",
        world_datetime=world.datetime_for_tick(5),
    )
    future_tick_mem = player.add_memory(
        "Kayla found the October ledger later.",
        tick=500,
        entity_ids=["player_Zoe"],
        location="Library",
        world_datetime="2016-10-14T09:00:00",
    )
    future_dt_mem = player.add_memory(
        "Kayla remembered a future August conversation.",
        tick=8,
        entity_ids=["player_Zoe"],
        location="Library",
        world_datetime="2016-08-01T12:00:00",
    )

    res = retrieve_associative_memories(
        player,
        {"area_id": "Library", "actors": ["Zoe"]},
        world=world,
        tick=10,
        min_score=0.1,
        explain=True,
        do_reinforce=False,
    )
    recalled_ids = {m["id"] for m in res["memories"]}
    assert past_mem["id"] in recalled_ids
    assert future_tick_mem["id"] not in recalled_ids
    assert future_dt_mem["id"] not in recalled_ids
    locked_reasons = [r.get("reason") for r in res.get("rejected", [])]
    assert locked_reasons.count("future_time_locked") == 2
