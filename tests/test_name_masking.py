"""Tests for engine/name_masking.py — stranger-description name scrubbing."""

from engine.name_masking import mask_name_in_text


def test_masks_full_name_in_first_sentence():
    text = "miki doki, mid-twenties american, 5'8\", dramatic hourglass build (K-cup)."
    out = mask_name_in_text(text, "miki doki", "the woman")
    assert "miki doki" not in out.lower()
    assert out.startswith("the woman, mid-twenties")


def test_masks_aliases_longest_first():
    text = "miki doki waved, miki waved back."
    out = mask_name_in_text(text, "miki doki", "the woman", aliases=["miki"])
    assert "miki doki" not in out.lower()
    # the short alias must not have already broken the long one
    assert "the woman waved, the woman waved back." == out


def test_case_insensitive_partial_words_not_hit():
    text = "Miki Doki paused. A mikiot something happened."
    out = mask_name_in_text(text, "miki doki", "the woman")
    assert "Miki Doki" not in out
    assert "mikiot" in out  # word boundary respected


def test_noop_on_empty_inputs():
    assert mask_name_in_text("", "miki", "the woman") == ""
    assert mask_name_in_text("hello", "", "the woman") == "hello"


def test_known_names_pass_through_unchanged():
    text = "miki doki grins."
    assert mask_name_in_text(text, "miki doki", "miki doki") == text
