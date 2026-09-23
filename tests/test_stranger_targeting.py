"""Targeting an unmet character by the appearance label the scene shows.

Regression: an LLM actor was handed "the woman" in its scene listing, then
"approach the woman" failed with "There's no 'woman' here to approach." because
`_match_character_name` only matched real names/aliases/descriptions, never the
`unknown_display_name()` label perception actually shows.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from area import Area
from player import Player
from virtual_world_engine import VirtualWorld


def _world_with_unmet_woman():
    world = VirtualWorld()
    world.movement.add_area(Area("Kitchen", "A test kitchen.", []))
    viewer = world.active_player
    world.name_matcher._set_player_area(viewer, "Kitchen")

    stranger = Player("Lyrie")
    stranger.tags = ["female"]
    stranger.current_area = "Kitchen"
    world.player_manager.add_player(stranger)
    world.name_matcher._set_player_area("Lyrie", "Kitchen")
    # add_player() makes the new player active — restore the viewer so the
    # stranger is not excluded as "self".
    world.player_manager.set_active_player(viewer)
    return world, viewer


def test_appearance_label_resolves_an_unmet_character():
    world, _viewer = _world_with_unmet_woman()
    resolved, candidates = world._match_character_name("the woman")
    assert resolved == "Lyrie", (resolved, candidates)
    assert candidates == []


def test_partial_appearance_label_resolves():
    world, _viewer = _world_with_unmet_woman()
    resolved, candidates = world._match_character_name("woman")
    assert resolved == "Lyrie", (resolved, candidates)


def test_unrelated_label_does_not_match():
    world, _viewer = _world_with_unmet_woman()
    resolved, candidates = world._match_character_name("the man")
    assert resolved is None, (resolved, candidates)


def test_label_tier_is_skipped_once_met():
    """After meeting, the real name is what the scene shows and what matches."""
    world, viewer = _world_with_unmet_woman()
    player = world.player_manager.players[viewer]
    player.register_first_meeting("Lyrie", tick=1)
    resolved, candidates = world._match_character_name("Lyrie")
    assert resolved == "Lyrie", (resolved, candidates)
