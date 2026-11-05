"""Unit tests for task-404: Character life experience authoring and import."""

import json
import pytest
from player import Player
from engine.life_experience import (
    apply_experience_to_scenario,
    generate_life_experience,
    import_diary_export,
    load_experience_into_player,
)


def test_generator_determinism():
    res1 = generate_life_experience("Arix", seed=101, background="wanderer", stages=4)
    res2 = generate_life_experience("Arix", seed=101, background="wanderer", stages=4)

    assert len(res1.memories) == 4
    assert len(res2.memories) == 4
    for m1, m2 in zip(res1.memories, res2.memories):
        assert m1["text"] == m2["text"]
        assert m1["importance"] == m2["importance"]
        assert m1["tags"] == m2["tags"]
        assert m1["category"] == m2["category"]

    # Different seed produces different selection or ordering
    res3 = generate_life_experience("Arix", seed=999, background="wanderer", stages=4)
    # At least some ordering or text should vary across seeds
    assert json.dumps(res1.to_dict()) != json.dumps(res3.to_dict())


def test_loading_into_player_and_idempotency():
    res = generate_life_experience("Arix", seed=42, background="scholar", stages=3)
    player = Player("Arix")

    added1 = load_experience_into_player(player, res)
    assert added1 == len(res.memories)
    assert len(player.memories) == len(res.memories)

    # All loaded memories have source='preconceived'
    for m in player.memories:
        assert m["source"] == "preconceived"
        assert m["type"] == "backstory"

    # Loading a second time does not duplicate memories
    added2 = load_experience_into_player(player, res)
    assert added2 == 0
    assert len(player.memories) == len(res.memories)


def test_location_and_entity_resolution_with_scenario():
    scenario = {
        "graph": {
            "nodes": [
                {"id": "area_library", "name": "Grand Library", "type": "area"},
                {"id": "char_mentor", "name": "Archivist Marcus", "type": "character"},
            ]
        }
    }

    # Generate with scholar background which hints at library
    res = generate_life_experience("Kaelen", seed=42, background="scholar", stages=4, scenario_dict=scenario)

    # Check that known node was resolved and missing hints were recorded in report
    rep = res.report
    assert "unresolved_locations" in rep
    # Unresolved locations should contain hints like 'scriptorium' that aren't in scenario
    assert any("scriptorium" in item.get("hint", "") for item in rep["unresolved_locations"])

    # Any memory with a location must point to an actual node in scenario
    valid_ids = {"area_library", "char_mentor"}
    for m in res.memories:
        if "location" in m and m["location"]:
            assert m["location"] in valid_ids


def test_authored_goals_map_to_player():
    res = generate_life_experience("Corin", seed=42, background="soldier", stages=4)
    assert len(res.goals) >= 1

    player = Player("Corin")
    load_experience_into_player(player, res)

    # Goal should be present in player.goals
    assert len(player.goals) >= 1
    goal_texts = [g.get("what", g.get("text")) for g in player.goals]
    assert any("defensive strengths" in t for t in goal_texts)


def test_aura_diary_importer():
    diary_payload = {
        "character": "Anna Anjou",
        "events": [
            {
                "event_id": "evt_001",
                "age_days": 3650,
                "date": "Spring 1042",
                "raw_memory": "The day the bell tower cracked, everyone in the square fell silent.",
                "emotional_impact": 0.85,
                "choice_made": "Stayed with my grandmother",
                "location_id": "area_square",
                "involved_persons": ["Father Thomas", "Unknown Stranger"],
            },
            {
                "event_id": "evt_002",
                "age_days": 5840,
                "date": "Autumn 1048",
                "raw_memory": "",
                "outcome_text": "I was caught reading after lights out in the dormitory.",
                "choice_made": "Hid the candle under the floorboards",
                "emotional_impact": 0.4,
                "location_id": "nonexistent_dorm",
                "involved_persons": ["Prefect Vane"],
            }
        ],
        "emotional_trajectory": [{"day": 3650, "valence": 0.1}],
        "milestones": [
            {
                "id": "recover_heirloom",
                "description": "Recover my grandmother's locket",
                "active_pursuit": True,
                "priority": 1,
            }
        ]
    }

    scenario = {
        "graph": {
            "nodes": [
                {"id": "area_square", "name": "Town Square", "type": "area"},
                {"id": "char_father_thomas", "name": "Father Thomas", "type": "character"},
            ]
        }
    }

    result = import_diary_export(diary_payload, "Anna Anjou", scenario_dict=scenario)

    assert len(result.memories) == 2
    # First memory uses raw_memory
    assert "bell tower cracked" in result.memories[0]["text"]
    # Importance scaled from 0.85 impact -> >= 8
    assert result.memories[0]["importance"] >= 8
    # Location resolved to real node
    assert result.memories[0]["location"] == "area_square"
    # Involved persons: Father Thomas resolved, Unknown Stranger omitted
    assert result.memories[0].get("entity_ids") == ["char_father_thomas"]

    # Second memory used outcome + choice fallback
    assert "caught reading" in result.memories[1]["text"]
    assert "Hid the candle" in result.memories[1]["text"]
    # Unresolved location omitted
    assert "location" not in result.memories[1]

    # Report details
    rep = result.report
    assert any("nonexistent_dorm" in item.get("location_id", "") for item in rep["unresolved_locations"])
    assert any("Unknown Stranger" in item.get("person", "") for item in rep["unresolved_entities"])
    assert any("emotional_trajectory" in field for field in rep["unsupported_fields"])

    # Milestone mapped to goal
    assert len(result.goals) == 1
    assert "grandmother's locket" in result.goals[0]["text"]


def test_apply_experience_to_scenario():
    scenario = {
        "players": {
            "Arix": {
                "preconceived_knowledge": {
                    "memories": [{"text": "Pre-existing memory"}]
                }
            }
        }
    }
    res = generate_life_experience("Arix", seed=42, background="wanderer", stages=2)
    updated = apply_experience_to_scenario(scenario, "Arix", res)

    memories = updated["players"]["Arix"]["preconceived_knowledge"]["memories"]
    assert len(memories) == 3
    assert memories[0]["text"] == "Pre-existing memory"

    # Re-applying does not duplicate
    updated_again = apply_experience_to_scenario(updated, "Arix", res)
    assert len(updated_again["players"]["Arix"]["preconceived_knowledge"]["memories"]) == 3
