"""Faction and ownership as tags (task-550).

The vocabulary is ``faction:<name>`` on a character and ``held_by:<name>`` on an
area, both from ``engine/ownership.py``. These tests cover the resolution, the
three decisions that module makes (tag-not-scope, commons-by-default,
record-don't-punish), and the whole-cast ownership map of the checked-in camp so
an unowned shared need-resource is a **test failure** rather than something only
a dashboard would show.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import ownership  # noqa: E402
from engine.ownership import (  # noqa: E402
    CONTESTED_WHY,
    describe_standing_on,
    factions_of,
    holders_of,
    is_owned_by,
    note_contested_use,
    ownership_map,
    owns_any,
    unowned_need_areas,
)

ROOT = Path(__file__).parent.parent
CAMP = ROOT / "data" / "scenarios" / "kraktooth_goblin_camp.json"

#: The need-resources task-550 names: the camp's single water source and its
#: single waste pile. Every character in the cast depends on these.
NEED_TAGS = {
    "water": ("water", "drink", "beverage"),
    "food": ("food", "eat", "edible", "meal"),
    "relief": ("latrine", "toilet", "privy", "restroom"),
}

#: Every need-area that is deliberately a **commons**, named per need.
#:
#: This list is the point of the test. An unheld need-resource is not illegal
#: (decision 2: an unclaimed area is a commons), so the invariant cannot be
#: "everything is claimed" — it is "everything is accounted for". The Murk Lake
#: and the Raven River are wild water that nobody would ever fence, so they stay
#: a commons. A NEW unclaimed water area fails this test, which is exactly the
#: "visible in a test failure rather than only in a dashboard" acceptance.
KNOWN_COMMONS = {
    "water": ["Murk Lake", "Raven River"],
    "food": [],
    "relief": [],
}


def _payload():
    with open(CAMP, encoding="utf-8-sig") as handle:
        return json.load(handle)


def _nodes(payload):
    return payload["graph"]["nodes"]


def _area(payload, name):
    for node in _nodes(payload).values():
        if node.get("type") == "area" and node.get("name") == name:
            return node
    raise AssertionError(f"no area named {name!r}")


def _node_like(node_id, node_type, name, tags):
    class _N:
        pass

    n = _N()
    n.id, n.type, n.name = node_id, node_type, name
    n.properties = {"tags": list(tags)}
    return n


def _graph_for(payload):
    """The graph-ish object ``unowned_need_areas`` / ``ownership_map`` read."""
    class _Graph:
        nodes = {}

    _Graph.nodes = {
        key: _node_like(key, node.get("type"), node.get("name"),
                        (node.get("properties") or {}).get("tags") or [])
        for key, node in _nodes(payload).items()
    }
    return _Graph


# ── the vocabulary ─────────────────────────────────────────────────────────


def test_prefixed_tags_are_read_and_normalised():
    # Case-insensitive on the prefix and the name (tags are lowercased
    # everywhere else in the engine), whitespace tolerated, an empty name and a
    # bare tag both ignored.
    node = _node_like("area_x", "area", "X", ["held_by:Goblin", "held_by: human ",
                                              "goblin_camp", "held_by:"])
    assert holders_of(node) == {"goblin", "human"}
    assert factions_of(_node_like("p", "character", "P", ["faction:goblin"])) == {"goblin"}
    assert holders_of(_node_like("b", "area", "B", ["goblin", "Held_By:nope"])) == {"nope"}


def test_a_prefixed_name_is_accepted_where_a_bare_one_is():
    """A caller holding a tag list must not read a prefixed tag as unknown.

    Otherwise `is_owned_by(props, "held_by:goblin")` is False and the area looks
    unheld — the one failure this vocabulary cannot afford, because it makes a
    claimed commons look like a hole.
    """
    node = _node_like("area_x", "area", "X", ["held_by:goblin"])
    assert is_owned_by(node, "held_by:goblin") is True
    assert is_owned_by(node, "goblin") is True
    assert owns_any(["faction:human"], ["held_by:goblin"]) is False
    assert owns_any(["faction:goblin"], ["held_by:goblin"]) is True


def test_a_bare_tag_is_not_a_claim():
    """`goblin` on an area is a domain tag; only `held_by:goblin` is a claim.

    This is the whole reason the tag is prefixed. `human` already means "a human
    place" on an area, and the camp areas all carry `goblin_camp`, so an
    unprefixed faction vocabulary would make every claim ambiguous.
    """
    node = _node_like("area_x", "area", "X", ["goblin", "human", "goblin_camp"])
    assert holders_of(node) == set()
    assert is_owned_by(node, "goblin") is False


def test_a_props_dict_and_a_node_agree():
    assert holders_of({"tags": ["held_by:goblin"]}) == {"goblin"}
    assert holders_of(_node_like("a", "area", "A", ["held_by:goblin"])) == {"goblin"}
    assert holders_of(None) == set()
    assert holders_of({}) == set()


def test_owns_any_is_set_intersection():
    assert owns_any(["goblin"], {"goblin", "human"}) is True
    assert owns_any(["frog"], {"goblin"}) is False
    assert owns_any([], {"goblin"}) is False
    assert owns_any(["goblin"], set()) is False


# ── decision 1: a tag, not the scope ───────────────────────────────────────


def _camp_scope_id(payload):
    """The id of the goblin camp's scope, found rather than written down.

    task-565 migrated this id off `deep_woods_2`, and a test that hard-codes a
    scope id is a test that fails the next time the id is fixed for the same
    reason. The camp is identified by the areas it holds instead.
    """
    scopes = payload.get("world_scopes") or {}
    for scope_id, scope in scopes.items():
        if "goblin_camp" in {str(t) for t in (scope.get("tags") or ())}:
            return scope_id
    held = {n["id"] for n in _nodes(payload).values()
            if n.get("type") == "area"
            and is_owned_by(n.get("properties") or {}, "goblin")}
    for scope_id, scope in scopes.items():
        area_ids = set(scope.get("area_ids") or ())
        if area_ids and held <= area_ids:
            return scope_id
    raise AssertionError("no scope holds the goblin camp's areas")


def test_ownership_is_a_tag_not_a_scope_derivation():
    """The two vocabularies must be able to disagree, or the choice is untestable.

    The camp's own scope holds exactly the 21 ``goblin_camp``-tagged areas, so on
    today's data "owner = in the camp scope" and "owner = carries
    ``held_by:goblin``" give the same answer for the camp. They are not the same
    rule, and the difference is visible on Eldenford: a human holding
    (``held_by:human``) in a scope of its own, NOT inside the goblin scope at all.
    A scope answers "where is this", never "whose is this".
    """
    payload = _payload()
    scopes = payload.get("world_scopes") or {}
    in_camp_scope = set((scopes.get(_camp_scope_id(payload)) or {})
                        .get("area_ids") or ())
    assert in_camp_scope, "the camp scope should still hold areas"

    eldenford = _area(payload, "Eldenford")
    assert eldenford["id"] not in in_camp_scope, (
        "fixture drifted: Eldenford is inside the goblin scope now, so a "
        "scope-based derivation would make the goblins the owners of a human "
        "village and this test would no longer be testing the distinction"
    )
    assert is_owned_by(eldenford["properties"], "human") is True
    assert is_owned_by(eldenford["properties"], "goblin") is False


def test_the_camp_holdings_are_the_tagged_areas_not_the_scoped_ones():
    """The sharpest form of decision 1: a commons inside a scope is a commons.

    ``goblin_camp``-tagged areas and ``held_by:goblin`` areas are the same 21
    today. What proves the rule is the TAG is that dropping it from a scoped
    holding makes that holding a commons, and nothing about the scope puts it
    back.
    """
    payload = _payload()
    goblin_holdings = {n["name"] for n in _nodes(payload).values()
                       if n.get("type") == "area"
                       and is_owned_by(n["properties"], "goblin")}
    assert len(goblin_holdings) == 21

    # Murk Lake carries the `water` tag the camp's Croak-Mother lives in, and is
    # a commons: no holder, on purpose.
    murk = _area(payload, "Murk Lake")
    assert holders_of(murk["properties"]) == set()
    assert murk["name"] not in goblin_holdings

    in_camp_scope = set(
        (payload.get("world_scopes") or {})
        .get(_camp_scope_id(payload), {}).get("area_ids") or ())
    water_source = _area(payload, "Water Source")
    assert water_source["id"] in in_camp_scope, (
        "fixture drifted: Water Source left the camp scope, so the un-tag "
        "half of this test would prove nothing"
    )
    props = water_source["properties"]
    removed = [t for t in props["tags"] if t.startswith("held_by:")]
    props["tags"] = [t for t in props["tags"] if not t.startswith("held_by:")]
    try:
        assert is_owned_by(props, "goblin") is False
        assert unowned_need_areas(_graph_for(payload), ("water",)) == sorted(
            KNOWN_COMMONS["water"] + ["Water Source"]
        )
    finally:
        props["tags"].extend(removed)
    assert is_owned_by(props, "goblin") is True


# ── decision 2: a commons by default ───────────────────────────────────────


def test_every_need_resource_is_either_claimed_or_a_named_commons():
    """The measured problem: nobody owned anything, so everybody converged.

    Every water / food / relief area must either name a holder or appear in
    ``KNOWN_COMMONS``. The water source and the waste pile the task names by
    heart are claimed; the wild water is a commons on purpose. Anything else is a
    hole.
    """
    payload = _payload()
    graph = _graph_for(payload)
    for need, tags in NEED_TAGS.items():
        serving = [node.name for node in graph.nodes.values()
                   if node.type == "area"
                   and {str(t).lower() for t in (node.properties or {}).get("tags", [])}
                   & {t.lower() for t in tags}]
        assert serving, f"the camp has no {need} area at all"
        unaccounted = unowned_need_areas(graph, tags)
        assert unaccounted == KNOWN_COMMONS[need], (
            f"{need}: unclaimed and not a declared commons: {unaccounted}. "
            f"Declared commons are {KNOWN_COMMONS[need]}. An unheld "
            "need-resource is a commons every character converges on, which is "
            "how the humans ended up living in the goblin camp."
        )


def test_unowned_need_areas_reports_the_hole_and_excludes_claimed_ones():
    payload = _payload()
    graph = _graph_for(payload)

    for need, tags in NEED_TAGS.items():
        assert unowned_need_areas(graph, tags) == KNOWN_COMMONS[need]
    # No tags -> nothing asked for, nothing reported.
    assert unowned_need_areas(graph, ()) == []
    # Asking about a need the world has no vocabulary for is empty, not an error.
    assert unowned_need_areas(graph, ("quicksilver",)) == []

    # A synthetic unclaimed area does show up, and it is reported by NAME.
    graph.nodes["area_lost"] = _node_like(
        "area_lost", "area", "Lost Spring", ["water"]
    )
    assert unowned_need_areas(graph, ("water",)) == sorted(
        KNOWN_COMMONS["water"] + ["Lost Spring"]
    )
    # A non-area carrying the tag is not a water source.
    graph.nodes["item_well"] = _node_like("item_well", "item", "Well", ["water"])
    assert "Well" not in unowned_need_areas(graph, ("water",))


def test_a_contested_holding_carries_every_holder():
    node = _node_like("a", "area", "Border Market", ["held_by:goblin", "held_by:human"])
    assert holders_of(node) == {"goblin", "human"}
    assert is_owned_by(node, "goblin") and is_owned_by(node, "human")
    assert owns_any(["human"], holders_of(node))


# ── the whole-cast ownership map ───────────────────────────────────────────


def test_the_camp_ownership_map_is_what_the_task_describes():
    """The map, asserted, so a later edit that unclaims the water is visible."""
    payload = _payload()

    factions = sorted({
        f for p in payload["players"].values()
        for f in factions_of(p)
    })
    assert factions == ["goblin", "human"], (
        f"the camp roster's factions changed: {factions}"
    )
    assert set(ownership_map(_graph_for(payload), [])) == {"goblin", "human"}, (
        "a caller that passes no roster must still get the holders that exist"
    )

    owned = ownership_map(_graph_for(payload), factions)
    assert set(owned) == {"goblin", "human"}

    goblin_holdings = owned["goblin"]
    assert len(goblin_holdings) == 21, (
        f"the goblin camp is 21 areas, not {len(goblin_holdings)}: {goblin_holdings}"
    )
    # The two resources the task names by heart.
    assert "Water Source" in goblin_holdings
    assert "Waste Disposal" in goblin_holdings
    # A human place is not a goblin holding.
    assert "Eldenford" not in goblin_holdings
    assert owned["human"] == ["Eldenford"]

    # A commons: the wild water nobody claimed. That is the interesting case and
    # it must stay reachable by everybody.
    for commons in ("Murk Lake", "Raven River"):
        node = _area(payload, commons)
        assert holders_of(node["properties"]) == set(), (
            f"{commons} was claimed; it is a commons in this camp"
        )


#: The camp roster's factions, asserted whole. A character in neither list
#: belongs to neither faction — the wild animals, and the frog in Murk Lake.
#: That is a real state (they are the commons), and it is safe precisely because
#: ``note_contested_use`` never accuses a character that declares no faction.
FACTION_ROSTER = {
    "goblin": ["Arix", "Belne", "Gribba", "Kiala", "Krikka", "Mikka", "Rikka",
               "Thrazz", "Vekka", "Zikka"],
    "human": ["Eldenford Blacksmith", "Eldenford Elder", "Eldenford Farmer",
              "Eldenford Merchant", "Eldenford Road Guard Captain", "Leslie",
              "player_human_explorer"],
}

#: Belongs to neither faction, on purpose: wild animals and one frog.
UNAFFILIATED = ["Croak-Mother", "Old Iron-Back", "Rag-Tail", "Shadow-Pelt",
                "Silver-Talon", "Tusker"]


def test_the_whole_cast_is_accounted_for():
    """Every character is in a faction or explicitly in neither.

    The task's acceptance: an unowned shared resource should be visible in a
    test failure rather than only in a dashboard. Same discipline for the cast —
    a character that quietly gains or loses a faction shows up here.
    """
    payload = _payload()
    by_name = {p.get("name", k): factions_of(p) for k, p in payload["players"].items()}

    for faction, members in FACTION_ROSTER.items():
        for name in members:
            assert by_name.get(name) == {faction}, (
                f"{name} should be faction:{faction}, has {by_name.get(name)}"
            )

    for name in UNAFFILIATED:
        assert by_name.get(name) == set(), (
            f"{name} is declared unaffiliated; a faction tag appeared on it"
        )

    accounted = set(FACTION_ROSTER["goblin"]) | set(FACTION_ROSTER["human"]) \
        | set(UNAFFILIATED)
    assert accounted == set(by_name), (
        "the camp roster changed; update FACTION_ROSTER / UNAFFILIATED. "
        f"new: {sorted(set(by_name) - accounted)}"
    )


def test_the_animals_were_never_accused_of_taking_the_camps_water():
    """The unaffiliated cast is why the no-faction rule has to exist.

    `Croak-Mother` is a frog living in Murk Lake, a commons, and the other five
    are wild animals that wander the camp's edges. None of them is a goblin, so
    a rule that reads "no faction" as "not an owner" would have generated a
    contested-use event for all six every time they drank.
    """
    payload = _payload()
    for name in UNAFFILIATED:
        player = next(p for k, p in payload["players"].items() if p.get("name") == name)
        for area_name in ("Water Source", "Waste Disposal"):
            node = _area(payload, area_name)
            assert holders_of(node["properties"]), f"{area_name} should be claimed"
            assert factions_of(player) == set()
            assert note_contested_use(
                _Player(name, player.get("tags") or []), node, "water", _Gs()
            ) is None


# ── decision 3: record, do not refuse and do not punish ────────────────────


class _Gs:
    def __init__(self, ticks=42):
        self.time_ticks = ticks
        self.log = []

    def add_log_entry(self, text):
        self.log.append(text)


class _Player:
    def __init__(self, name, tags):
        self.name = name
        self.tags = list(tags)
        self.lived_log = []


def test_contested_use_records_an_event_and_still_serves_the_need():
    player = _Player("Leslie", ["human", "faction:human"])
    area = _node_like("area_water_source", "area", "Water Source",
                      ["water", "held_by:goblin"])
    gs = _Gs()

    entry = note_contested_use(player, area, "water", gs)

    assert entry is not None
    assert entry["why"] == f"{CONTESTED_WHY}:water"
    assert entry["area"] == "Water Source"
    assert entry["tags"] == ["need", "ownership"]
    assert entry["salient"] is True
    assert "Leslie" in entry["what"]
    # The fact reaches both places a reader looks.
    assert player.lived_log == [entry]
    assert gs.log and "held by the goblin" in gs.log[0]
    # Nothing was refused and nothing was charged: the need is served either way.
    assert not hasattr(player, "vitals")


def test_an_owner_using_their_own_resource_records_nothing():
    player = _Player("Gribba", ["goblin", "faction:goblin"])
    area = _node_like("area_water_source", "area", "Water Source",
                      ["water", "held_by:goblin"])
    gs = _Gs()

    assert note_contested_use(player, area, "water", gs) is None
    assert player.lived_log == []
    assert gs.log == []


def test_a_commons_is_never_contested():
    player = _Player("Rag-Tail", ["wolf"])
    area = _node_like("area_raven_river", "area", "Raven River", ["water", "river"])
    gs = _Gs()

    assert note_contested_use(player, area, "water", gs) is None
    assert gs.log == []


def test_a_character_with_no_faction_is_not_accused():
    """An unauthored character is not a trespasser.

    Without `faction:`, a character's membership is unknown, and reading that as
    "not a goblin" would accuse every wolf in the camp of stealing goblin water.
    Unknown is not the same as foreign.
    """
    player = _Player("Rag-Tail", ["wolf"])
    area = _node_like("area_water_source", "area", "Water Source",
                      ["water", "held_by:goblin"])
    gs = _Gs()

    assert note_contested_use(player, area, "water", gs) is None
    assert gs.log == []
    assert player.lived_log == []


def test_a_factionless_character_is_still_not_blocked_from_a_commons():
    player = _Player("Tusker", ["boar"])
    commons = _node_like("area_murk_lake", "area", "Murk Lake", ["water", "lake"])
    assert note_contested_use(player, commons, "water", _Gs()) is None


def test_note_contested_use_survives_a_broken_game_log():
    player = _Player("Leslie", ["human", "faction:human"])
    area = _node_like("a", "area", "Water Source", ["water", "held_by:goblin"])

    class _Broken:
        time_ticks = 1

        def add_log_entry(self, text):
            raise RuntimeError("logger is down")

    assert note_contested_use(player, area, "water", _Broken()) is not None
    assert player.lived_log, "the lived log is the record that matters"


def test_note_contested_use_ignores_missing_arguments():
    area = _node_like("a", "area", "Water Source", ["water", "held_by:goblin"])
    assert note_contested_use(None, area, "water", _Gs()) is None
    assert note_contested_use(_Player("L", ["human"]), None, "water", _Gs()) is None


# ── the description clause ─────────────────────────────────────────────────


@pytest.mark.parametrize("factions,holders,expected", [
    (["faction:goblin"], ["held_by:goblin"], ""),
    (["faction:human"], ["held_by:goblin"], "held by the goblin"),
    (["faction:human"], ["held_by:human", "held_by:goblin"], ""),
    ([], ["held_by:goblin"], "held by the goblin"),
    (["faction:human"], [], ""),
    (["faction:x"], ["held_by:a", "held_by:b"], "held by the a and the b"),
    (["faction:x"], ["held_by:a", "held_by:b", "held_by:c"],
     "held by the a and 2 others"),
])
def test_describe_standing_on(factions, holders, expected):
    assert describe_standing_on(factions, holders) == expected


def test_the_prefixes_are_the_ones_the_tools_stamp():
    """The authoring tool and the engine must not drift on the spelling."""
    import tools.claim_areas as claim_areas

    assert claim_areas._area_tag("goblin") == f"{ownership.HELD_BY_PREFIX}goblin"
    assert claim_areas._faction_tag("goblin") == f"{ownership.FACTION_PREFIX}goblin"
