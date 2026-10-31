"""Targeted unit tests for Memory Recall Transparency and Dynamics (task-786).

Verifies:
1. Multi-signal retrieval score breakdown across the 7 channels:
   - Spatial proximity
   - Social presence
   - Conversational echo
   - Emotional congruency
   - Physical need
   - Temporal recency
   - Semantic embedding
2. Emotional salience boost when active emotion intensity >= 6.
3. Recalled memory provenance structure (percent_match, primary_signal, channels, points).
4. Absence memories (kind: "absence") written, retrieved, and superseded by presence observations.
5. Sleep consolidation (routine episodic memory fading vs emotional salience reinforcement).
"""

import pytest
from engine.memory_retrieval import (
    extract_cues,
    is_active_memory,
    retrieve_associative_memories,
    score_memory,
)
from engine.memory_dynamics import consolidate_sleep, EPISODIC, SEMANTIC
from player import Player


class MockPlayer:
    def __init__(self, name="TestHero", memories=None):
        self.name = name
        self.memories = list(memories or [])


def test_seven_channel_breakdown_and_provenance():
    """Verify that score_memory calculates explicit components for all 7 channels."""
    mem = {
        "id": "mem_feast",
        "text": "Mikka served roasted chicken in the Banquet Hall while laughing happily.",
        "location": "area_banquet_hall",
        "entity_ids": ["player_mikka", "item_roasted_chicken", "area_banquet_hall"],
        "tags": ["food", "feast", "mikka", "joy"],
        "importance": 6,
        "tick": 90,
        "emotion": {"label": "joy", "intensity": 7},
    }

    # Cues activating multiple channels:
    # 1. Spatial: area_banquet_hall
    # 2. Social: Mikka present
    # 3. Conversational: dialogue mentions "chicken feast"
    # 4. Emotional: joy (intensity 7 >= 6 => salience boost!)
    # 5. Need: need:food
    # 6. Recency: current tick 100 vs mem tick 90
    # 7. Semantic: explicit semantic score in cues
    cues = {
        "area_id": "area_banquet_hall",
        "actors": ["player_mikka"],
        "dialogue": ["chicken feast"],
        "emotion": "joy",
        "emotion_intensity": 7.0,
        "needs": ["need:food"],
        "semantic_scores": {"mem_feast": 0.8},
    }

    score, breakdown = score_memory(mem, cues, current_tick=100)
    assert breakdown["active"] is True
    assert score > 5.0

    channels = breakdown["channels"]
    assert channels["spatial"] > 0
    assert channels["social"] > 0
    assert channels["conversational"] > 0
    assert channels["emotional"] > 0
    assert channels["need"] > 0
    assert channels["recency"] > 0
    assert channels["semantic"] > 0

    prov = breakdown["_provenance"]
    assert prov["percent_match"] > 50
    assert prov["primary_signal"] in channels
    assert prov["points"]["spatial"] > 0
    assert prov["points"]["social"] > 0
    assert prov["points"]["need"] > 0


def test_mood_congruence_salience_multiplier():
    """Verify memories receive mood-congruent salience boost when emotion intensity >= 6."""
    mem_fear = {
        "id": "mem_ambush",
        "text": "The shadowy figure lunged with a rusted dagger.",
        "tags": ["combat", "fear", "danger"],
        "importance": 7,
        "tick": 50,
        "emotion": {"label": "fear", "intensity": 8},
    }

    # Low intensity fear (intensity 4 < 6)
    cues_calm = {
        "emotion": "fear",
        "emotion_intensity": 4.0,
        "dialogue": ["careful"],
    }
    score_calm, breakdown_calm = score_memory(mem_fear, cues_calm, current_tick=60)

    # High intensity fear (intensity 8 >= 6)
    cues_terrified = {
        "emotion": "fear",
        "emotion_intensity": 8.0,
        "dialogue": ["careful"],
    }
    score_terrified, breakdown_terrified = score_memory(mem_fear, cues_terrified, current_tick=60)

    # High intensity emotion match must yield a higher emotional score
    assert breakdown_terrified["channels"]["emotional"] > breakdown_calm["channels"]["emotional"]
    assert score_terrified > score_calm


def test_retrieve_associative_memories_attaches_provenance():
    """Verify retrieve_associative_memories injects _provenance into each recalled item."""
    mem1 = {
        "id": "m1",
        "text": "Stored fresh water in the pantry barrel.",
        "location": "area_pantry",
        "tags": ["water", "drink"],
        "importance": 5,
        "tick": 20,
    }
    player = MockPlayer(memories=[mem1])

    cues = {
        "area_id": "area_pantry",
        "needs": ["need:drink"],
    }

    result = retrieve_associative_memories(
        player, cues, tick=25, min_score=1.0, do_reinforce=True
    )
    assert len(result["memories"]) == 1
    recalled = result["memories"][0]

    assert "_provenance" in recalled
    assert recalled["_provenance"]["primary_signal"] in ("spatial", "need")
    assert recalled["_provenance"]["percent_match"] > 0
    assert "channels" in recalled["_provenance"]
    assert "points" in recalled["_provenance"]

    # When reinforced, stored memory in player.memories also gets _provenance stamped
    assert "_provenance" in player.memories[0]


def test_absence_memory_lifecycle_and_superseding():
    """Verify absence memories are created, retrieved, and superseded by presence."""
    p = Player(name="Scout")
    abs_mem = p.record_absence(target="item_bacon", location="area_kitchen", tick=10)
    assert abs_mem["kind"] == "absence"
    assert abs_mem["data"]["polarity"] == "absent"
    assert "item_bacon" in abs_mem["entity_ids"]
    assert abs_mem["location"] == "area_kitchen"

    # In kitchen hungry at tick 15 -> absence memory is recalled so character knows it's empty
    cues = {
        "area_id": "area_kitchen",
        "needs": ["need:food"],
    }
    result = retrieve_associative_memories(p, cues, tick=15, min_score=1.0, do_reinforce=False)
    recalled_ids = [m["id"] for m in result["memories"]]
    assert abs_mem["id"] in recalled_ids

    # Later at tick 30, scout observes bacon placed in the kitchen
    obs_mem = p.record_observation(
        subject_id="item_bacon",
        text="A fresh strip of bacon lies on the kitchen table.",
        tick=30,
        kind="item",
        location="area_kitchen"
    )

    # Absence memory must now be marked superseded by the new presence observation
    assert abs_mem.get("superseded_by") == obs_mem["id"]

    # At tick 35, retrieve again: absence memory must NOT be recalled because it is superseded
    result2 = retrieve_associative_memories(p, cues, tick=35, min_score=1.0, do_reinforce=False)
    recalled_ids2 = [m["id"] for m in result2["memories"]]
    assert abs_mem["id"] not in recalled_ids2


def test_sleep_consolidation_fades_routine_and_reinforces_salient():
    """Verify sleep consolidation fades routine noise and reinforces emotional/high-imp memories."""
    routine_breakfast = {
        "id": "mem_toast",
        "text": "Ate a slice of plain toast at sunrise.",
        "category": EPISODIC,
        "importance": 3,
        "activation": 0.8,
        "confidence": 0.7,
        "tick": 10,
    }
    salient_near_death = {
        "id": "mem_dragon",
        "text": "Barely rolled away as the dragon fire melted the shield.",
        "category": EPISODIC,
        "importance": 8,
        "activation": 0.7,
        "confidence": 0.7,
        "tick": 12,
        "emotion": {"label": "fear", "intensity": 9},
    }

    p = MockPlayer(memories=[routine_breakfast, salient_near_death])
    res = consolidate_sleep(p, current_tick=100)

    assert res["faded"] == 1
    assert res["reinforced"] == 1

    # Routine breakfast activation stepped down
    assert routine_breakfast["activation"] < 0.8

    # Salient near-death activation and confidence boosted
    assert salient_near_death["activation"] > 0.7
    assert salient_near_death["confidence"] > 0.7
    assert salient_near_death["reinforcements"] >= 1
