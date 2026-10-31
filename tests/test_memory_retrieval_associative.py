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
