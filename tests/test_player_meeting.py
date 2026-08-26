"""Tests for first-meeting Entertainment novelty boost (task-136).

Verifies that a character's first meeting with another character grants an
Entertainment boost, once only, with trait modifiers.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from player import Player
from engine.traits import TraitSystem


def _player(ent=50, traits=None):
    p = Player("TestPlayer")
    p.vitals["Entertainment"] = ent
    for trait_id in (traits or []):
        p.traits[trait_id] = {}
    return p


class TestFirstMeeting:
    def test_first_meeting_boosts_entertainment(self):
        """Meeting a new character grants the base boost."""
        p = _player(ent=50)
        was_new = p.register_first_meeting("Lyrie", tick=1)
        assert was_new is True
        assert "Lyrie" in p.relationships
        assert p.vitals["Entertainment"] == 60  # base 10

    def test_repeat_meeting_no_boost(self):
        """Seeing the same character again gives no extra boost."""
        p = _player(ent=50)
        p.register_first_meeting("Lyrie", tick=1)
        was_new = p.register_first_meeting("Lyrie", tick=2)
        assert was_new is False
        assert p.vitals["Entertainment"] == 60
        assert p.relationships["Lyrie"]["interaction_count"] == 0

    def test_meeting_clamped_at_100(self):
        """Boost is clamped at 100."""
        p = _player(ent=96)
        p.register_first_meeting("Lyrie", tick=1)
        assert p.vitals["Entertainment"] == 100

    def test_curious_gets_half_again(self):
        """curious trait: +50% boost."""
        p = _player(ent=50, traits=["curious"])
        p.register_first_meeting("Lyrie", tick=1)
        assert p.vitals["Entertainment"] == 65  # 10 * 1.5

    def test_homebody_gets_nothing(self):
        """homebody trait: no boost from meeting new people."""
        p = _player(ent=50, traits=["homebody"])
        p.register_first_meeting("Lyrie", tick=1)
        assert p.vitals["Entertainment"] == 50

    def test_update_relationship_also_grants_meeting_boost(self):
        """update_relationship on a stranger still counts as first meet."""
        p = _player(ent=50)
        p.update_relationship("Kaelen", tick=1, sentiment_change=0)
        assert "Kaelen" in p.relationships
        assert p.vitals["Entertainment"] == 60

    def test_first_sighting_stamped_on_meeting(self):
        """register_first_meeting marks the record so the name stays hidden
        for the rest of the first-sighting turn (task-154 leak fix)."""
        p = _player()
        p.register_first_meeting("Lyrie", tick=1)
        assert p.relationships["Lyrie"]["first_sighting"] is True

    def test_update_relationship_has_no_first_sighting_flag(self):
        """A real interaction reveals the name immediately."""
        p = _player()
        p.update_relationship("Kaelen", tick=1, sentiment_change=0)
        assert "first_sighting" not in p.relationships["Kaelen"]


class TestUnknownDisplayName:
    """Unknown display name + has_met (task-154)."""

    def test_derives_label_from_description(self):
        """Unknown label derives from the first sentence of the description."""
        p = Player("Lyrie")
        p.description = "A tall woman with long auburn hair, watching the door."
        assert p.unknown_display_name() == "the tall woman with long auburn hair, watching the door"

    def test_uses_explicit_unknown_name(self):
        """An explicitly authored unknown_name wins over derivation."""
        p = Player("Lyrie")
        p.unknown_name = "the hooded traveler"
        p.description = "A tall woman with long auburn hair."
        assert p.unknown_display_name() == "the hooded traveler"

    def test_fallback_to_stranger(self):
        """No description and no unknown_name → 'the stranger'."""
        p = Player("Nobody")
        assert p.unknown_display_name() == "the stranger"

    def test_tag_animal_label(self):
        """animal tag with no description → 'an animal' (e.g. the rat)."""
        p = Player("rat")
        p.tags = ["animal"]
        assert p.unknown_display_name() == "an animal"

    def test_tag_male_label(self):
        """male tag with no description → 'the man'."""
        p = Player("Kaelen")
        p.tags = ["male", "human"]
        assert p.unknown_display_name() == "the man"

    def test_tag_female_label(self):
        """female tag with no description → 'the woman'."""
        p = Player("Lyrie")
        p.tags = ["female", "elf"]
        assert p.unknown_display_name() == "the woman"

    def test_tag_girl_and_boy_labels(self):
        """girl/boy tags map to 'a girl' / 'a boy'."""
        p = Player("Girl")
        p.tags = ["girl"]
        assert p.unknown_display_name() == "a girl"
        p2 = Player("Boy")
        p2.tags = ["boy"]
        assert p2.unknown_display_name() == "a boy"

    def test_tag_label_case_insensitive(self):
        """Tags are matched case-insensitively and ignore whitespace."""
        p = Player("Rat")
        p.tags = ["Animal"]
        assert p.unknown_display_name() == "an animal"

    def test_tag_string_tags(self):
        """tags stored as a comma string still work."""
        p = Player("Rat")
        p.tags = "animal"
        assert p.unknown_display_name() == "an animal"

    def test_tags_beat_description(self):
        """A gender tag wins over a description-derived label."""
        p = Player("Lyrie")
        p.tags = ["female"]
        p.description = "A tall woman with long auburn hair."
        assert p.unknown_display_name() == "the woman"

    def test_has_met_until_relationship_exists(self):
        """has_met is False before a meeting, True after."""
        p = Player("Kaelen")
        assert p.has_met("Lyrie") is False
        p.register_first_meeting("Lyrie", tick=1)
        assert p.has_met("Lyrie") is True

    def test_pronoun_starting_description_label(self):
        """"She stands..." derives a person label, not "the she stands..."."""
        p = Player("Lyrie")
        p.description = "She stands bare and unadorned, her slender frame carrying a dancer's lithe strength."
        assert p.unknown_display_name() == "the woman who stands bare and unadorned, her slender frame carrying a dancer's lithe strength"
        p2 = Player("Kaelen")
        p2.description = "He watches from the corner, scarred and silent."
        assert p2.unknown_display_name() == "the man who watches from the corner, scarred and silent"

    def test_unknown_name_serialized(self):
        """to_dict includes unknown_name."""
        p = Player("Lyrie")
        p.unknown_name = "the hooded traveler"
        assert p.to_dict()["unknown_name"] == "the hooded traveler"
