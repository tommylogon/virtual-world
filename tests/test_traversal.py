"""Soak-tier traversal checks (task-475).

Routine ground takes 10 and never rolls; risky ground rolls the right skill, and
a refusal costs the turn (plus at most one minor condition) and is routed around
instead of being retried forever.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import EDGE_CONNECTION
from player import Player
from engine import traversal
from engine.background_simulation import BackgroundSimulation


def _world():
    from app import create_app
    w = create_app({"TESTING": True}).world
    w.time_per_tick_minutes = 1
    return w


def _hero(w, area=None):
    p = w.get_active_player_obj() or next(iter(w.players.values()))
    p.vitals.update({"HP": 100, "Thirst": 0, "Hunger": 0, "Bladder": 0,
                     "Energy": 100, "Hygiene": 100, "Sanity": 100,
                     "Social": 100, "Entertainment": 100})
    p.conditions.clear()
    p.state = "idle"
    p.activity = None
    p.simulation_mode = "active"
    p.skills = {}
    p.stats = {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}
    if area:
        w.set_player_area(p.name, area)
        p.current_area = area
    try:
        w.player_manager.set_active_player(p.name)
    except Exception:
        pass
    return p


def _area(w, name, tags=()):
    from area import Area
    w.movement.add_area(Area(name, "Empty.", []))
    node = w.graph.get_node(w.area_node_id(name))
    if node is not None:
        node.properties["tags"] = list(tags)
    return name


def _connect(w, a, b, direction, reverse="south", state="open", requires=None):
    w.movement.connect_areas(a, b, direction, reverse, state=state)
    if requires:
        for edge in w.graph.get_edges_for_source(w.area_node_id(a), EDGE_CONNECTION):
            if edge.properties.get("direction") == direction:
                w.graph.get_node(edge.target).properties["requires"] = requires
                break


def _boom():
    raise AssertionError("routine ground must not roll")


# ───────────────────────────── the mapping ────────────────────────────────

def test_way_kind_reads_the_requirement():
    w = _world()
    _area(w, "Bottom")
    _area(w, "Top")
    _connect(w, "Bottom", "Top", "north", requires="climb")
    exits = w.build_exits_for_area("Bottom", include_hidden=True)
    assert traversal.way_kind(w, exits["north"]["way_id"]) == "climb"
    assert traversal.way_kind(w, None) == "go"


def test_hazard_ground_maps_to_the_skill_that_carries_you():
    w = _world()
    cases = {"river": "Athletics", "swamp": "Survival",
             "narrow": "Acrobatics", "guarded": "Stealth"}
    for tag, skill in cases.items():
        name = f"Ground {tag}"
        _area(w, name, tags=(tag,))
        assert traversal.hazard(w, name) == (tag, skill, traversal.HAZARD_DC)
    _area(w, "Plain Room")
    assert traversal.hazard(w, "Plain Room") is None


def test_every_mapped_skill_is_a_real_skill():
    from engine.checks import SKILL_ABILITY
    for action, skill in traversal.SOAK_ACTIONS.items():
        assert skill in SKILL_ABILITY, f"{action} -> unknown skill {skill}"
    for tag, skill in traversal.HAZARD_SKILLS.items():
        assert skill in SKILL_ABILITY, f"{tag} -> unknown skill {skill}"


def test_routine_maintenance_has_no_skill_and_no_dice():
    assert traversal.is_routine("eat")
    assert traversal.skill_for("eat") == ""
    assert traversal.skill_for("walk") == ""
    assert not traversal.is_routine("climb")
    assert traversal.skill_for("climb") == "Athletics"
    assert traversal.skill_for("sneak") == "Stealth"


def test_routine_ground_takes_ten_and_never_rolls():
    w = _world()
    hero = _hero(w)
    _area(w, "Corridor")
    result = traversal.attempt(w, hero, dest="Corridor", roll_fn=_boom)
    assert result.ok and result.tier == "routine" and not result.checked
    assert result.why == "traversal:routine"


def test_risky_ground_rolls_and_its_failure_leaves_one_minor_condition():
    w = _world()
    hero = _hero(w)
    _area(w, "Ford", tags=("river",))

    failed = traversal.attempt(w, hero, dest="Ford", roll_fn=lambda: 1)
    assert not failed.ok and failed.skill == "Athletics"
    assert failed.condition == "wet" and failed.checked

    passed = traversal.attempt(w, hero, dest="Ford", roll_fn=lambda: 20)
    assert passed.ok and passed.checked and passed.why == "traversal:ok"


def test_a_cliff_failure_injures_rather_than_merely_wets():
    w = _world()
    hero = _hero(w)
    _area(w, "Ledge", tags=("cliff",))
    failed = traversal.attempt(w, hero, dest="Ledge", roll_fn=lambda: 1)
    assert not failed.ok and failed.condition == "injured"


# ───────────────────────────── hopping ────────────────────────────────────

def test_hop_uses_the_verb_the_way_needs():
    w = _world()
    _area(w, "Bottom")
    _area(w, "Top")
    _connect(w, "Bottom", "Top", "north", requires="climb")
    hero = _hero(w, area="Bottom")

    seen = {}
    original = w.movement.move_to_area

    def fake(direction, kind="go", _allow_approach=True):
        seen["kind"], seen["direction"] = kind, direction
        w.set_player_area(hero.name, "Top")
        hero.current_area = "Top"
        return "You climb through the north."

    w.movement.move_to_area = fake
    try:
        result = traversal.hop(w, hero, "north")
    finally:
        w.movement.move_to_area = original

    assert result.ok and seen == {"kind": "climb", "direction": "north"}
    assert hero.current_area == "Top"


def test_a_locked_way_returns_blocked_instead_of_raising():
    w = _world()
    _area(w, "Hall")
    _area(w, "Vault")
    _connect(w, "Hall", "Vault", "north", state="locked")
    hero = _hero(w, area="Hall")

    result = traversal.hop(w, hero, "north")
    assert not result.ok and result.blocked and not result.condition
    assert hero.current_area == "Hall"


# ───────────────────────── refusal memory ────────────────────────────────

def test_a_refusal_is_remembered_then_expires():
    w = _world()
    hero = _hero(w)
    traversal.note_refusal(w, hero, "Hall", "north")
    assert traversal.avoid_key("Hall", "north") in traversal.avoid(w, hero)

    w.time_ticks += 10 ** 6
    assert traversal.avoid(w, hero) == set()


def test_a_blocked_way_is_routed_around_on_the_spot():
    """The direct way is locked, so the character takes the other first hop."""
    w = _world()
    hero = _hero(w)
    _area(w, "Home")
    _area(w, "Detour")
    _area(w, "Wild")
    _connect(w, "Home", "Wild", "north", state="locked")
    _connect(w, "Home", "Detour", "east", "west")
    _connect(w, "Detour", "Wild", "north", "south")
    w.set_player_area(hero.name, "Home")
    hero.current_area = "Home"

    sim = BackgroundSimulation(w)
    assert sim._travel_to_area(hero, "Wild", "timeskip") is True
    assert hero.current_area == "Detour"
    assert traversal.avoid_key("Home", "north") in traversal.avoid(w, hero)


def test_travel_still_refuses_without_a_second_route():
    w = _world()
    hero = _hero(w)
    _area(w, "Home")
    _area(w, "Wild")
    _connect(w, "Home", "Wild", "north", state="locked")
    w.set_player_area(hero.name, "Home")
    hero.current_area = "Home"

    sim = BackgroundSimulation(w)
    assert sim._travel_to_area(hero, "Wild", "timeskip") is False
    assert hero.current_area == "Home"
    assert traversal.avoid_key("Home", "north") in traversal.avoid(w, hero)
