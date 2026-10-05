"""Tests for tools/feature_index.py — the Feature Map <-> @powers join.

The regression this proves is the phrase match: a multi-word feature label
("Turn queue", "Use / use on") can only join when looked for as a phrase,
because the older word-prefix match never splits a label on spaces.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import feature_index as fi

FEATS = [
    {"label": "Turn queue", "terms": ["turn queue"]},
    {"label": "Use / use on", "terms": ["use on"]},
    {"label": "Move", "terms": ["move"]},
    {"label": "Soak lab", "terms": ["soak lab"]},
]


def test_multiword_label_matches_as_phrase():
    assert fi.match("Turn queue — who acts next", FEATS) == ["Turn queue"]
    assert fi.match("Use / use on — typed targets", FEATS) == ["Use / use on"]


def test_single_word_term_fallback_still_matches_gerund():
    # "movement" is claimed by "Move" through the word-prefix fallback.
    assert fi.match("movement and traversal", FEATS) == ["Move"]


def test_phrase_match_is_case_insensitive_and_ignores_markup():
    assert fi.match("SOAK LAB — dashboards", FEATS) == ["Soak lab"]
    assert fi.match("`Turn queue` strip", FEATS) == ["Turn queue"]


def test_unrelated_prose_names_no_feature():
    assert fi.match("purple monkey dishwasher", FEATS) == []


def test_split_cells_keeps_an_escaped_alias_pipe():
    # A bare `[[Note|alias]]` in a table row truncates the cell silently: row 23's
    # Docs cell parsed as "[[Environment/Temperature System" and the note it names
    # lost its inbound relation with no error anywhere. Obsidian needs `\|` inside
    # a table, and the parser must not cut there.
    cells = fi.split_cells(
        r" Temperature | Body temp | wired | [[Environment/Temperature System\|Temperature System]] ")
    assert cells[3] == "[[Environment/Temperature System|Temperature System]]"
    assert len(cells) == 4, cells


def test_split_cells_still_splits_on_a_real_column_separator():
    cells = fi.split_cells(" Move | Traverse ways | wired | [[Doors & Connections]] ")
    assert cells == ["Move", "Traverse ways", "wired", "[[Doors & Connections]]"]


def test_every_real_row_has_a_resolvable_docs_link():
    from tools.feature_pages import docs_links

    empty = [(f["n"], f["docs"]) for f in fi.parse_features() if not docs_links(f["docs"])]
    assert empty == [], empty


def test_row_numbers_are_unique_across_both_tables():
    # The editor table used to restart at 1, so "#5" named two different features.
    nums = [f["n"] for f in fi.parse_features()]
    dupes = sorted({n for n in nums if nums.count(n) > 1})
    assert dupes == [], dupes


def test_real_map_labels_match_their_own_phrases():
    # The controlled vocabulary must be self-consistent: every real label joins
    # when quoted verbatim, which is how the headers now name features.
    feats = fi.parse_features()
    assert len(feats) == 76, "the map grew to 76 rows on 2026-10-05 (43 in-game, 33 editor)"
    misses = [f["label"] for f in feats if f["label"] not in fi.match(f["label"], feats)]
    assert misses == [], misses
