"""task-605: size is a character property, not a `size_*` trait.

Size started as a trait (task-187) and is now a first-class property, because a
prefixed trait key is invisible in the graph editor and cannot be filtered on.
Two things read it: way `max_size` passage gating, and per-area occupancy
(task-653).

These tests pin the PRECEDENCE, because the interesting failure is silent: a
property that defaults to "normal" outranks every hand-authored trait, and the
way gate quietly stops working.
"""
import pytest

from engine.size import SIZE_DEFAULT, SIZE_TIERS, size_name, size_tier


class _P:
    """Stand-in for Player: a size property plus a traits dict."""

    def __init__(self, size=None, traits=None):
        self.size = size
        self.traits = traits or {}


def test_bare_character_is_normal():
    assert size_name(_P()) == SIZE_DEFAULT
    assert size_tier(_P()) == SIZE_TIERS.index(SIZE_DEFAULT)


def test_trait_still_works_when_no_property_is_authored():
    """task-187 authored worlds must keep working unchanged."""
    p = _P(traits={"size_huge": {}})
    assert size_name(p) == "huge"
    assert size_tier(p) == SIZE_TIERS.index("huge")


def test_property_wins_when_both_are_present():
    p = _P(size="giant", traits={"size_huge": {}})
    assert size_name(p) == "giant"


def test_unrecognised_property_falls_back_to_the_trait():
    p = _P(size="colossal", traits={"size_huge": {}})
    assert size_name(p) == "huge"


def test_unrecognised_property_with_no_trait_is_normal():
    assert size_name(_P(size="colossal")) == SIZE_DEFAULT


def test_property_is_case_and_whitespace_insensitive():
    assert size_name(_P(size="  GIANT ")) == "giant"


def test_no_player_is_normal():
    assert size_name(None) == SIZE_DEFAULT


def test_every_documented_tier_resolves_to_its_own_index():
    for i, tier in enumerate(SIZE_TIERS):
        assert size_tier(_P(size=tier)) == i
        assert size_name(_P(traits={"size_" + tier: {}})) == tier
