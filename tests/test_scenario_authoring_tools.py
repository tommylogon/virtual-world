"""Unit tests for the scenario data-integrity migration tools (task-408).

The checked-in camp is covered end-to-end by
``tests/test_scenario_data_integrity.py``. These cover the *behaviour* of the
tools on synthetic payloads: idempotency, and the three ways a reference can be
wrong (unresolvable, ambiguous, or disagreeing with the graph) — a tool that
guesses is worse than one that stops.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.author_character_aliases import author_alias  # noqa: E402
from tools.canonicalize_way_ids import canonicalize  # noqa: E402
from tools.scenario_refs import (  # noqa: E402
    AmbiguousRef,
    AreaResolver,
    normalize_ref,
    way_connection_pairs,
)
from tools.set_scenario_title import set_title  # noqa: E402


def _node(node_id, node_type, name, **props):
    return {"id": node_id, "type": node_type, "name": name, "properties": props}


def _camp():
    """A two-area, one-door camp with a name-addressed way and a name-addressed
    character location, plus a second character whose anchor is missing."""
    nodes = {
        "area_chiefs_pit": _node("area_chiefs_pit", "area", "Chief's Pit",
                                 environment={"light": "dim"}),
        "area_camp_entrance": _node("area_camp_entrance", "area", "Camp Entrance",
                                    environment={"light": "normal"}),
        "way_pit_to_entrance": _node("way_pit_to_entrance", "way", "passage to the camp entrance",
                                     area_from="area_chiefs_pit",
                                     area_to="Camp Entrance",
                                     current_state="open"),
        "player_Thrazz": _node("player_Thrazz", "character", "Thrazz", x=1, y=2),
        "player_Kiala": _node("player_Kiala", "character", "Kiala"),
    }
    edges = [
        {"source": "area_chiefs_pit", "target": "way_pit_to_entrance",
         "type": "connection", "properties": {}},
        {"source": "way_pit_to_entrance", "target": "area_camp_entrance",
         "type": "connection", "properties": {}},
        {"source": "area_camp_entrance", "target": "way_pit_to_entrance",
         "type": "connection", "properties": {}},
        {"source": "way_pit_to_entrance", "target": "area_chiefs_pit",
         "type": "connection", "properties": {}},
        {"source": "player_Thrazz", "target": "area_chiefs_pit",
         "type": "in", "properties": {}},
    ]
    return {
        "name": "Kraktooth Goblin Camp",
        "meta": {"title": "Kraktooth Goblin Camp"},
        "_scenario_name": "kraktooth_goblin_camp",
        "players": {
            "Thrazz": {"name": "Thrazz", "current_area": "Chief's Pit",
                       "description": "The chief.", "tags": ["goblin"],
                       "traits": {"high_metabolism": True}},
            "Kiala": {"name": "Kiala", "current_area": "Chief's Pit",
                      "description": "The squire."},
            "Zikka": {"name": "Zikka", "current_area": "Chief's Pit",
                      "description": "No anchor exists for this one."},
        },
        "graph": {"nodes": nodes, "edges": edges},
    }


# ── the resolver ───────────────────────────────────────────────────────────


def test_normalize_ref_folds_punctuation_and_case():
    assert normalize_ref("Chief's Pit") == "chiefspit"
    assert normalize_ref("Sparse Forest (West woods 10,14)") == "sparseforestwestwoods1014"
    assert normalize_ref(None) == ""


def test_resolver_prefers_id_then_exact_name_then_folded():
    data = _camp()
    resolver = AreaResolver(data["graph"]["nodes"])
    assert resolver.resolve("area_camp_entrance") == "area_camp_entrance"
    assert resolver.resolve("Camp Entrance") == "area_camp_entrance"
    assert resolver.resolve("campentrance") == "area_camp_entrance"
    assert resolver.resolve("Nowhere") is None
    assert resolver.resolve("") is None
    assert resolver.resolve(None) is None
    assert "area_camp_entrance" in resolver


def test_resolver_refuses_to_guess_between_equally_good_matches():
    nodes = {
        "area_cave": _node("area_cave", "area", "Cave"),
        "area_the_cave": _node("area_the_cave", "area", "The Cave"),
        "area_the_cave_2": _node("area_the_cave_2", "area", "the cave!"),
    }
    resolver = AreaResolver(nodes)
    # An exact name is still unambiguous.
    assert resolver.resolve("Cave") == "area_cave"
    assert resolver.resolve("The Cave") == "area_the_cave"
    # The folded form matches three areas; guessing would move a way to the
    # wrong side of the camp.
    with pytest.raises(AmbiguousRef):
        resolver.resolve("the cave")


def test_resolver_matches_a_node_by_its_declared_id_not_its_key():
    nodes = {"weird key": _node("area_pond", "area", "Pond")}
    resolver = AreaResolver(nodes)
    assert resolver.resolve("area_pond") == "weird key"
    assert resolver.resolve("Pond") == "weird key"


def test_way_connection_pairs_reads_both_edge_directions():
    data = _camp()
    pairs = way_connection_pairs(data["graph"]["nodes"], data["graph"]["edges"])
    assert pairs["way_pit_to_entrance"] == {"area_chiefs_pit", "area_camp_entrance"}


# ── way-id canonicalization ────────────────────────────────────────────────


def test_canonicalize_rewrites_a_name_addressed_endpoint():
    data = _camp()
    report = canonicalize(data)
    assert [c[:2] for c in report["rewritten"]] == [
        ("way_pit_to_entrance", "area_to")
    ]
    assert data["graph"]["nodes"]["way_pit_to_entrance"]["properties"]["area_to"] == (
        "area_camp_entrance"
    )
    assert not report["unresolved"] and not report["ambiguous"]
    assert not report["disagreements"]


def test_canonicalize_is_idempotent():
    data = _camp()
    canonicalize(data)
    assert canonicalize(data)["rewritten"] == []


def test_canonicalize_reports_an_unresolvable_endpoint_instead_of_guessing():
    data = _camp()
    data["graph"]["nodes"]["way_pit_to_entrance"]["properties"]["area_to"] = "Nowhere"
    report = canonicalize(data)
    assert report["unresolved"] == [("way_pit_to_entrance", "area_to", "Nowhere")]
    # The resolvable field still gets rewritten; the tool reports, it does not
    # silently drop half the fix.
    assert data["graph"]["nodes"]["way_pit_to_entrance"]["properties"]["area_from"] == (
        "area_chiefs_pit"
    )


def test_canonicalize_reports_a_resolution_the_graph_contradicts():
    data = _camp()
    nodes = data["graph"]["nodes"]
    # The graph says the way only touches the pit; the authored property claims
    # the camp entrance. A name that resolves somewhere the graph does not
    # connect is a genuine disagreement, not a formatting drift.
    data["graph"]["edges"] = [
        e for e in data["graph"]["edges"]
        if not (e["source"] == "area_camp_entrance" or e["target"] == "area_camp_entrance")
    ]
    report = canonicalize(data)
    disagreements = report["disagreements"]
    assert len(disagreements) == 1
    way_id, field, value, resolved, sides = disagreements[0]
    assert (way_id, field) == ("way_pit_to_entrance", "area_to")
    assert value == "Camp Entrance"
    assert resolved == "area_camp_entrance"
    assert sides == ["area_chiefs_pit"]
    # It is still rewritten, and the disagreement is reported rather than
    # silently resolved in the graph's favour.
    assert nodes["way_pit_to_entrance"]["properties"]["area_to"] == "area_camp_entrance"


def test_canonicalize_reports_an_ambiguous_endpoint():
    data = _camp()
    nodes = data["graph"]["nodes"]
    nodes["area_second_cave"] = _node("area_second_cave", "area", "Second Cave")
    nodes["area_the_second_cave"] = _node("area_the_second_cave", "area", "second cave")
    # Not an exact name of either area, but it folds onto both.
    nodes["way_pit_to_entrance"]["properties"]["area_to"] = "second  cave"
    report = canonicalize(data)
    assert len(report["ambiguous"]) == 1
    assert report["ambiguous"][0][:2] == ("way_pit_to_entrance", "area_to")
    # An ambiguous reference is never rewritten.
    assert nodes["way_pit_to_entrance"]["properties"]["area_to"] == "second  cave"


def test_canonicalize_prefers_an_exact_name_over_a_folded_collision():
    data = _camp()
    nodes = data["graph"]["nodes"]
    nodes["area_second_cave"] = _node("area_second_cave", "area", "Second Cave")
    nodes["area_the_second_cave"] = _node("area_the_second_cave", "area", "second cave")
    nodes["way_pit_to_entrance"]["properties"]["area_to"] = "Second Cave"
    report = canonicalize(data)
    assert not report["ambiguous"]
    assert nodes["way_pit_to_entrance"]["properties"]["area_to"] == "area_second_cave"


# ── character aliases ──────────────────────────────────────────────────────


def test_author_alias_adds_the_node_and_its_location_edge():
    data = _camp()
    report = author_alias(data)
    assert report["added"] == [
        ("character_kiala", "player_Kiala"),
        ("character_thrazz", "player_Thrazz"),
    ]

    authored = data["graph"]["nodes"]["character_thrazz"]
    assert authored["name"] == "Thrazz"
    assert authored["properties"]["description"] == "The chief."
    assert authored["properties"]["tags"] == ["goblin"]
    assert authored["properties"]["traits"] == {"high_metabolism": True}
    # Runtime anchors keep their own props; the authored node never carries them.
    assert data["graph"]["nodes"]["player_Thrazz"]["properties"] == {"x": 1, "y": 2}

    located = [e for e in data["graph"]["edges"] if e.get("type") == "in"]
    assert [(e["source"], e["target"]) for e in located] == [
        ("player_Thrazz", "area_chiefs_pit"),
        ("character_kiala", "area_chiefs_pit"),
        ("character_thrazz", "area_chiefs_pit"),
    ]


def test_author_alias_skips_a_player_with_no_anchor():
    data = _camp()
    report = author_alias(data)
    # Zikka has no player_ anchor in the payload, so there is nothing to
    # collapse into and no alias is written.
    assert report["skipped"] == [
        ("Zikka", "no player_Zikka anchor to collapse into")
    ]
    assert "character_zikka" not in data["graph"]["nodes"]


def test_author_alias_is_idempotent():
    data = _camp()
    author_alias(data)
    before = len(data["graph"]["edges"]), len(data["graph"]["nodes"])
    report = author_alias(data)
    assert report["added"] == []
    assert (len(data["graph"]["edges"]), len(data["graph"]["nodes"])) == before


def test_authored_aliases_collapse_to_one_node_per_person():
    from engine.character_identity import collapse_character_identity

    data = _camp()
    data["graph"]["nodes"]["player_Zikka"] = _node("player_Zikka", "character", "Zikka")
    author_alias(data)
    report = collapse_character_identity(data["graph"], data["players"])

    assert report["collapsed"] == [
        ("character_thrazz", "player_Thrazz"),
        ("character_kiala", "player_Kiala"),
        ("character_zikka", "player_Zikka"),
    ]
    assert report["aliases"]["character_thrazz"] == "player_Thrazz"
    assert not [k for k in data["graph"]["nodes"] if k.startswith("character_")]
    characters = [n for n in data["graph"]["nodes"].values()
                  if n["type"] == "character"]
    assert len(characters) == 3
    # The authored description wins over the anchor's, per PROSE_KEYS.
    thrazz = data["graph"]["nodes"]["player_Thrazz"]["properties"]
    assert thrazz["description"] == "The chief."
    assert (thrazz["x"], thrazz["y"]) == (1, 2)
    assert collapse_character_identity(data["graph"], data["players"])["collapsed"] == []


# ── the title ──────────────────────────────────────────────────────────────


def test_set_title_writes_name_meta_and_keeps_the_internal_id():
    data = _camp()
    report = set_title(data, "Kraktooth Goblin Camp")
    assert report["changes"] == []
    assert data["name"] == "Kraktooth Goblin Camp"
    assert data["meta"]["title"] == "Kraktooth Goblin Camp"
    assert data["_scenario_name"] == "kraktooth_goblin_camp", (
        "a deliberate internal id must not be clobbered by a display title"
    )


def test_set_title_fills_a_blank_internal_id():
    data = _camp()
    data["_scenario_name"] = ""
    data["meta"] = {}
    report = set_title(data, "Kraktooth Goblin Camp")
    assert ("_scenario_name", None, "Kraktooth Goblin Camp") in report["changes"]
    assert data["_scenario_name"] == "Kraktooth Goblin Camp"


def test_set_title_preserves_other_meta_keys():
    data = _camp()
    data["meta"] = {"author": "tom", "title": "old"}
    set_title(data, "New Title")
    assert data["meta"] == {"author": "tom", "title": "New Title"}
