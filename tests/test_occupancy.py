"""task-653: per-area max occupancy computed from occupant SIZE, with entities
that take no space.

A headcount cannot express a room. "Four occupants" is no answer to "can the
tarrasque come in?", and it is equally wrong for a fairy's house as for a throne
room. Occupancy here is a **sum of footprints** derived from the size tier that
way ``max_size`` passage gating already reads — a second reader of one axis.

The two things that make it more than a scaled headcount:

* **Zero space is not "tiny."** A 1 cm spider is tiny and takes up one unit; a
  ghost is *intangible* and takes up nothing however large it was authored.
* An entity bigger than the room still fits **alone**. Capacity is a budget and a
  reportable state, not a collision system.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.occupancy import (
    DEFAULT_MAX_OCCUPANCY, TIER_SPACE, area_budget, describe_occupancy, fits,
    occupancy_report, occupancy_used, occupants, space_of, takes_no_space,
)
from graph import Node
from player import Player

AREA = "Dark Cave"   # an area the default world's cast does not stand in


@pytest.fixture()
def world():
    from app import create_app
    return create_app({"TESTING": True}).world


def _add(world, name, area=AREA, size=None, tags=None):
    p = Player(name)
    p.current_area = area
    if size is not None:
        p.size = size
    if tags:
        p.tags = list(tags)
    world.add_player(p)
    if area:
        world.set_player_area(p.name, area)
    return p


def _area_id(world):
    """The node id of the area these tests measure.

    Deliberately NOT `world._get_current_area_id()`: that answers for whoever the
    *active* player is, which is not the same question.
    """
    for candidate in (AREA, f"area_{AREA.lower().replace(' ', '_')}"):
        if world.graph.get_node(candidate) is not None:
            return candidate
    raise AssertionError(f"test area {AREA!r} is not in this world")


def _set_budget(world, value):
    node = world.graph.get_node(_area_id(world))
    node.properties["max_occupancy"] = value


# ── the model: a size becomes a footprint ────────────────────────────────

def test_each_size_tier_has_a_footprint_and_they_are_not_linear():
    assert set(TIER_SPACE) == {"tiny", "small", "normal", "huge", "giant",
                               "titanic"}
    values = list(TIER_SPACE.values())
    assert values == sorted(values), values
    # A titanic thing is not six normals; it does not fit beside them.
    assert TIER_SPACE["titanic"] > TIER_SPACE["giant"] * 2


def test_footprint_comes_from_the_size_tier():
    for tier, expected in TIER_SPACE.items():
        p = Player("x")
        p.size = tier
        assert space_of(p) == expected, tier


def test_an_unset_size_reads_as_normal():
    assert space_of(Player("nobody")) == TIER_SPACE["normal"]


def test_a_bare_graph_node_reads_as_normal_not_as_a_giant():
    """The AGENTS.md trap: a character node is created *bare*, so an
    implementation that read `.size` off it would find nothing."""
    node = Node(id="c1", type="character", name="Someone")
    assert space_of(node) == TIER_SPACE["normal"]


def test_a_graph_node_with_properties_reads_its_size():
    """...and the other half: a node that *does* carry its size must not be
    ignored either, or a graph-only dragon counts as a person."""
    node = Node(id="c2", type="character", name="Dragon",
                properties={"size": "titanic"})
    assert space_of(node) == TIER_SPACE["titanic"]


def test_a_size_trait_is_the_fallback_for_a_world_predating_the_property():
    """task-605 keeps the `size_*` trait for exactly this reason."""
    p = Player("legacy")
    p.size = None
    p.traits = {"size_giant": {}}
    assert space_of(p) == TIER_SPACE["giant"]


def test_an_unknown_size_is_normal_rather_than_an_error():
    p = Player("odd")
    p.size = "colossal"
    assert space_of(p) == TIER_SPACE["normal"]


# ── entities that take no space ──────────────────────────────────────────

def test_a_ghost_takes_no_space_however_large_it_is():
    """Zero space is intangibility, not smallness."""
    ghost = Player("Wraith")
    ghost.size = "titanic"
    ghost.tags = ["ghost"]
    assert takes_no_space(ghost) is True
    assert space_of(ghost) == 0


def test_an_empty_room_is_never_over_capacity():
    report = {"budget": 100, "used": 0, "occupants": [],
              "full": False, "remaining": 100, "headcount": 0, "area": "x"}
    assert report["full"] is False
    assert describe_occupancy(report) == ""


@pytest.mark.parametrize("tag", ["ghost", "incorporeal", "intangible",
                                 "ethereal", "phasing"])
def test_every_zero_space_spelling_is_recognised(tag):
    """One answer to "what takes no space", not a guess per call site."""
    p = Player("x")
    p.tags = [tag]
    assert takes_no_space(p) is True, tag


def test_zero_space_is_case_insensitive_and_reads_a_comma_string():
    p = Player("x")
    p.tags = "Ghost, ethereal"
    assert takes_no_space(p) is True


def test_a_tiny_living_thing_still_takes_space():
    """The distinction that matters: 1 cm is not the same as not there."""
    spider = Player("Spiderling")
    spider.size = "tiny"
    assert space_of(spider) == TIER_SPACE["tiny"]
    assert takes_no_space(spider) is False


def test_a_bare_node_carries_no_tags_so_it_is_not_mistaken_for_a_ghost():
    node = Node(id="c3", type="character", name="Bare")
    assert takes_no_space(node) is False


def test_a_dead_player_is_not_occupying_the_room(world):
    corpse = _add(world, "Corpse")
    corpse.add_condition("dead")
    assert occupancy_used(_area_id(world), world.players, world.graph) == 0
    assert occupancy_used(_area_id(world), world.players, world.graph,
                          include_dead=True) == TIER_SPACE["normal"]


# ── the budget is authorable ─────────────────────────────────────────────

def test_an_area_with_no_declared_budget_gets_the_default(world):
    node = world.graph.get_node(_area_id(world))
    node.properties.pop("max_occupancy", None)
    assert area_budget(node) == DEFAULT_MAX_OCCUPANCY


def test_an_authored_budget_wins(world):
    _set_budget(world, 20)
    assert area_budget(world.graph.get_node(_area_id(world))) == 20


def test_a_zero_budget_means_unbounded_not_emptied(world):
    """`0` is the obvious way to write "unbounded" in an editor; refusing every
    arrival on that reading would be a nasty surprise."""
    _set_budget(world, 0)
    assert area_budget(world.graph.get_node(_area_id(world))) == DEFAULT_MAX_OCCUPANCY


def test_a_junk_budget_falls_back_rather_than_crashing(world):
    _set_budget(world, "roomy")
    assert area_budget(world.graph.get_node(_area_id(world))) == DEFAULT_MAX_OCCUPANCY


# ── the sum, and the four that fit where four people do not ─────────────

def test_four_people_fill_the_same_budget_as_one_ogre(world):
    _set_budget(world, 16)
    for i in range(4):
        _add(world, f"Person{i}")
    report = occupancy_report(_area_id(world), world.players, world.graph)
    assert report["used"] == 4 * TIER_SPACE["normal"] == 16
    assert report["full"] is True
    assert report["headcount"] == 4


def test_one_ogre_fills_the_same_budget_alone(world):
    _set_budget(world, 16)
    _add(world, "Ogre", size="huge")
    report = occupancy_report(_area_id(world), world.players, world.graph)
    assert report["used"] == TIER_SPACE["huge"] == 16
    assert report["headcount"] == 1


def test_a_room_is_over_capacity_when_a_dragon_arrives(world):
    _set_budget(world, 100)
    _add(world, "Dragon", size="titanic")
    report = occupancy_report(_area_id(world), world.players, world.graph)
    assert report["used"] > report["budget"]
    assert report["full"] is True
    assert report["remaining"] == 0


def test_a_room_holds_a_dragon_alone_because_it_is_empty(world):
    """Capacity is a budget, not a gate on identity."""
    _set_budget(world, 8)
    # The dragon is asking to come IN — it is not in the room yet, which is the
    # whole question `fits` answers.
    dragon = Player("Dragon")
    dragon.size = "titanic"
    assert fits(_area_id(world), dragon, world.players, world.graph) is True
    # And once it has arrived, the room reports itself over capacity rather than
    # pretending the dragon does not fit.
    _add(world, "Dragon", size="titanic")
    report = occupancy_report(_area_id(world), world.players, world.graph)
    assert report["used"] > report["budget"]


def test_a_dragon_cannot_walk_into_a_room_that_is_already_full(world):
    _set_budget(world, 16)
    _add(world, "Ogre", size="huge")            # 16, exactly full
    dragon = Player("Dragon")
    dragon.size = "titanic"
    assert fits(_area_id(world), dragon, world.players, world.graph) is False


def test_a_ghost_always_fits_however_full_the_room_is(world):
    _set_budget(world, 1)
    _add(world, "Ogre", size="huge")
    ghost = Player("Wraith")
    ghost.size = "titanic"
    ghost.tags = ["ghost"]
    assert fits(_area_id(world), ghost, world.players, world.graph) is True


def test_a_small_thing_can_slip_into_a_room_a_giant_cannot(world):
    _set_budget(world, 20)
    _add(world, "Ogre", size="huge")             # 16 of 20
    assert fits(_area_id(world), Player("small_one"), world.players,
                world.graph) is True
    big = Player("giant_one")
    big.size = "giant"                           # 40
    assert fits(_area_id(world), big, world.players, world.graph) is False


# ── occupants, and the bare-node resident ────────────────────────────────

def test_occupants_reports_the_live_players(world):
    _add(world, "Kaelen")
    _add(world, "Lyrie")
    names = [n for n, _e in occupants(_area_id(world), world.players, world.graph)]
    assert sorted(names) == ["Kaelen", "Lyrie"]


def test_a_graph_only_resident_is_counted_at_its_own_size(world):
    """A world with graph residents but no Player must not score every one of
    them as `normal` — that is the bare-node trap again."""
    from graph import Edge
    dragon = Node(id="graph_dragon", type="character", name="Graph Dragon",
                  properties={"size": "titanic"})
    world.graph.add_node(dragon)
    world.graph.add_edge(Edge(source=dragon.id, target=_area_id(world), type="in"))

    report = occupancy_report(_area_id(world), world.players, world.graph)
    assert report["used"] == TIER_SPACE["titanic"], report
    assert report["occupants"][0]["size"] == "titanic"


def test_a_player_and_a_graph_node_for_the_same_character_count_once(world):
    from graph import Edge
    _add(world, "Kaelen")
    node = world.graph.get_node(world._player_node_id("Kaelen"))
    assert world.graph.get_edges_for_target(_area_id(world), "in")
    report = occupancy_report(_area_id(world), world.players, world.graph)
    assert report["headcount"] == 1, report


# ── the words ────────────────────────────────────────────────────────────

def test_an_empty_room_says_nothing_at_all():
    """A phrase on every area trains the reader to skip the sentence."""
    assert describe_occupancy(
        {"budget": 100, "used": 0, "occupants": []}) == ""


def _report(used, budget, occupants=()):
    return {"budget": budget, "used": used, "occupants": list(occupants)}


def test_a_room_grows_from_busy_to_full():
    assert describe_occupancy(_report(40, 100)) == "The room is busy."
    assert describe_occupancy(_report(80, 100)) == "The room is crowded."
    assert describe_occupancy(_report(100, 100)) == "The room is full."
    assert describe_occupancy(_report(20, 100)) == ""


def test_an_over_capacity_room_names_what_does_not_fit():
    occupants = [{"name": "Vhaidra", "size": "titanic", "space": 200,
                  "intangible": False}]
    text = describe_occupancy(_report(200, 100, occupants))
    assert "Vhaidra" in text and "titanic" in text, text


def test_a_crowd_of_ghosts_is_not_a_crowd(world):
    _set_budget(world, 100)
    for i in range(30):
        _add(world, f"Wraith{i}", tags=["ghost"])
    report = occupancy_report(_area_id(world), world.players, world.graph)
    assert report["used"] == 0
    assert report["headcount"] == 30
    assert describe_occupancy(report) == ""


# ── the wiring: it is readable from the world and it shows up in prose ───

def test_the_world_exposes_an_occupancy_report(world):
    _set_budget(world, 16)
    _add(world, "Ogre", size="huge")
    report = world.area_occupancy(AREA)
    assert report["used"] == 16
    assert report["budget"] == 16
    assert report["full"] is True


def test_would_fit_answers_for_the_active_player(world):
    _set_budget(world, 1)
    _add(world, "Ogre", size="huge")
    world.player_manager.set_active_player("Kaelen Voss")
    assert world.would_fit(AREA) is False


def test_the_area_description_reports_a_packed_room(world):
    """The consumer: a room that is full says so, in the sentence the reader
    already reads for who is present."""
    from engine.area_description import AreaDescription

    _set_budget(world, 8)
    viewer = _add(world, "Viewer")
    _add(world, "Ogre", size="huge")           # 16 of 8 — over capacity
    world.player_manager.set_active_player("Viewer")

    system = AreaDescription(world.graph, world.lighting, world,
                            world.item_actions)
    text = system.get_area_description()
    assert any(phrase in text for phrase in (
        "crowded", "full", "busy", "cannot properly hold", "packed")), text


def test_a_quiet_room_adds_nothing_to_the_description(world):
    from engine.area_description import AreaDescription

    node = world.graph.get_node(_area_id(world))
    node.properties["max_occupancy"] = 10000
    viewer = _add(world, "Viewer")
    _add(world, "Ogre", size="huge")
    world.player_manager.set_active_player("Viewer")

    system = AreaDescription(world.graph, world.lighting, world, world.item_actions)
    text = system.get_area_description()
    for phrase in ("The room is busy", "The room is crowded",
                   "The room is full", "packed past its limits"):
        assert phrase not in text, phrase
