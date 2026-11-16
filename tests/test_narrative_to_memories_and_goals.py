"""Tests for task-849: Narrative authoring feeds memories and goals."""

import pytest
from app import create_app
from player import Player
from graph import Node
from engine.character_store import apply_node_properties, hydrate_player_from_node


def test_narrative_biography_and_secrets_feed_memories():
    node = Node(id="char_test", type="character", name="Lyra")
    node.properties["persona"] = {
        "narrative": {
            "biography": {
                "early_life": "Grew up in the Whispering Woods with an eccentric herbalist.",
                "adulthood": "Apprenticed to the Royal Alchemist in Sunspire.",
                "current_situation": "Seeking rare phosphorescent moss in Eldenford.",
            },
            "secrets": {
                "deepest_secret": "Stole the Forbidden Codex from Sunspire Vault.",
                "hidden_facts": [
                    "Can read ancient Netherese runes.",
                ],
            },
        }
    }

    player = Player("Lyra")
    apply_node_properties(player, node.properties)

    texts = [m.get("text", "") for m in player.memories]
    assert any("Early life: Grew up in the Whispering Woods" in t for t in texts)
    assert any("Adulthood: Apprenticed to the Royal Alchemist" in t for t in texts)
    assert any("Current situation: Seeking rare phosphorescent moss" in t for t in texts)
    assert any("Deepest secret: Stole the Forbidden Codex" in t for t in texts)
    assert any("Secret fact: Can read ancient Netherese runes" in t for t in texts)

    # All narrative memories have source="backstory"
    for m in player.memories:
        assert m.get("source") == "backstory"
        assert m.get("category") == "semantic"


def test_personality_aspirations_and_narrative_arc_feed_goals():
    node = Node(id="char_test_2", type="character", name="Corin")
    node.properties["persona"] = {
        "personality": {
            "aspirations": [
                "Find the cure for the Sunspire Blight",
                "Rebuild the family apothecary",
            ]
        },
        "narrative": {
            "arc": "Redemption through selfless healing",
        }
    }

    player = Player("Corin")
    apply_node_properties(player, node.properties)

    assert len(player.goals) >= 2
    whats = [g.get("what") for g in player.goals if isinstance(g, dict)]
    assert "Find the cure for the Sunspire Blight" in whats
    assert "Rebuild the family apothecary" in whats

    for g in player.goals:
        assert g.get("motivation") == "Redemption through selfless healing"
        assert g.get("status") == "active"


def test_reapplying_node_properties_does_not_duplicate_memories_or_goals():
    node = Node(id="char_test_3", type="character", name="Bryn")
    node.properties["persona"] = {
        "personality": {
            "aspirations": ["Master swordcraft"],
        },
        "narrative": {
            "biography": {
                "early_life": "Trained under the hill giants.",
            },
            "secrets": {
                "deepest_secret": "Lost the ancestral blade.",
            },
        }
    }

    player = Player("Bryn")
    apply_node_properties(player, node.properties)
    initial_mem_count = len(player.memories)
    initial_goal_count = len(player.goals)

    # Re-apply node properties (simulating sync or re-hydration)
    apply_node_properties(player, node.properties)
    assert len(player.memories) == initial_mem_count
    assert len(player.goals) == initial_goal_count
