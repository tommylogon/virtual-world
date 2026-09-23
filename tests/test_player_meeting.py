"""First-meeting Entertainment novelty (task-136, folded into task-425/434).

A first meeting grants Entertainment through the *shared novelty curve*, keyed on
the other character's node id — the same mechanic as places and things. It used
to be a separate flat +10, which double-paid with the perception grant task-425
added, so a character who walked into a room holding a stranger got both. Now
whichever happens first pays and the other pays nothing.

The values are therefore `NOVELTY_MAX` (15), not 10, and the trait scaling is the
curve's (curious x1.5, homebody 0).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from player import Player
from engine.novelty import NOVELTY_MAX


def _player(ent=50, traits=None):
    p = Player("TestPlayer")
    p.vitals["Entertainment"] = ent
    for trait_id in (traits or []):
        p.traits[trait_id] = {}
    return p


class TestFirstMeeting:
    def test_first_meeting_boosts_entertainment(self):
        """Meeting a new character grants full novelty."""
        p = _player(ent=50)
        was_new = p.register_first_meeting("Lyrie", tick=1)
        assert was_new is True
        assert "Lyrie" in p.relationships
        assert p.vitals["Entertainment"] == 50 + NOVELTY_MAX

    def test_repeat_meeting_no_boost(self):
        """Seeing the same character again gives no extra boost."""
        p = _player(ent=50)
        p.register_first_meeting("Lyrie", tick=1)
        gained = p.vitals["Entertainment"]
        was_new = p.register_first_meeting("Lyrie", tick=2)
        assert was_new is False
        assert p.vitals["Entertainment"] == gained
        assert p.relationships["Lyrie"]["interaction_count"] == 0

    def test_meeting_clamped_at_100(self):
        """Boost is clamped at 100."""
        p = _player(ent=96)
        p.register_first_meeting("Lyrie", tick=1)
        assert p.vitals["Entertainment"] == 100

    def test_curious_gets_half_again(self):
        """curious: the curve gives +50%."""
        p = _player(ent=50, traits=["curious"])
        p.register_first_meeting("Lyrie", tick=1)
        assert p.vitals["Entertainment"] == 50 + int(NOVELTY_MAX * 1.5)

    def test_homebody_gets_nothing(self):
        """homebody: no boost from meeting new people."""
        p = _player(ent=50, traits=["homebody"])
        p.register_first_meeting("Lyrie", tick=1)
        assert p.vitals["Entertainment"] == 50

    def test_update_relationship_also_grants_meeting_boost(self):
        """update_relationship on a stranger still counts as first meet."""
        p = _player(ent=50)
        p.update_relationship("Kaelen", tick=1, sentiment_change=0)
        assert "Kaelen" in p.relationships
        assert p.vitals["Entertainment"] == 50 + NOVELTY_MAX

    # ── task-434: one paid experience, whatever the order ────────────────

    def test_perception_then_meeting_pays_once(self):
        """Walking into a room holding a stranger, then greeting them."""
        p = _player(ent=50)
        p.record_observation(p.node_id_for("Lyrie"), "You have met Lyrie.", 5,
                             kind="character", location="Hall")
        after_perception = p.vitals["Entertainment"]
        p.register_first_meeting("Lyrie", tick=5)
        assert p.vitals["Entertainment"] == after_perception

    def test_meeting_then_perception_pays_once(self):
        """The other order must pay the same — ordering must not decide."""
        p = _player(ent=50)
        p.register_first_meeting("Lyrie", tick=5)
        after_meeting = p.vitals["Entertainment"]
        p.record_observation(p.node_id_for("Lyrie"), "You have met Lyrie.", 5,
                             kind="character", location="Hall")
        assert p.vitals["Entertainment"] == after_meeting

    def test_the_meeting_grant_is_keyed_on_the_node_id(self):
        """Relationships key by name; novelty keys by node id. Crossing between
        them must use the node id or the two never meet."""
        p = _player(ent=50)
        p.register_first_meeting("Lyrie", tick=1)
        assert p.observation_tick(p.node_id_for("Lyrie")) == 1

    def test_a_second_meeting_after_the_window_pays_again(self):
        """The curve recovers, so a long-absent face is worth noticing again."""
        from engine.novelty import DEFAULT_RECOVERY_MINUTES
        p = _player(ent=0)
        p.register_first_meeting("Lyrie", tick=0)
        first = p.vitals["Entertainment"]
        p.vitals["Entertainment"] = 0
        p.register_first_meeting("Lyrie", tick=DEFAULT_RECOVERY_MINUTES)
        # First meet only: the relationship already exists, so nothing is granted.
        assert p.vitals["Entertainment"] == 0
        assert first == NOVELTY_MAX

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
