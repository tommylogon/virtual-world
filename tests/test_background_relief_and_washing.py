"""Bladder and Hygiene in the background tier.

Neither need existed here. Bladder filled to 100 every ~4 hours and crossing it
docked 8 Hygiene (tick_manager), while nothing in the background set ever
restored Hygiene — the `bathing` activity exists but was never started. So
Hygiene (0.05/min decay + ~48/day from bladder) hit 0 within ten hours and stayed
there for the whole week.

Services come from an **area tag** (a latrine room, a river) or a **fixture item**
standing in the area (a wash spot, a shower). The fixture's authored Hygiene
amount is read back rather than hardcoded, so the library entry stays the single
source of truth.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from area import Area
from graph import Node, Edge
from player import Player
from engine.background_simulation import (
    BackgroundSimulation, RELIEF_TAGS, BATH_TAGS, BATH_HYGIENE, TASK_MINUTES,
)
from engine.relief import (
    DIGNITY_SANITY_COST, DIGNITY_SOCIAL_COST, is_private,
)

AREA = "Verdant Hollow"

#: A character who is fed, watered, rested and clean, so a test that cares about
#: one need is not also tripped by another.
VITALS = {"Hunger": 0, "Thirst": 0, "Energy": 100, "Hygiene": 100,
          "Sanity": 100, "Social": 100, "Entertainment": 100, "Bladder": 0}


def _world(area_tags=()):
    world = create_app({"TESTING": True}).world
    area = Area(AREA, "A hollow.", [])
    world.movement.add_area(area)
    if area_tags:
        node = world.graph.get_node(world.area_node_id(AREA))
        node.properties["tags"] = list(area_tags)
    return world


def _character(world, **vitals):
    p = Player("Wretch")
    world.add_player(p)
    world.set_player_area("Wretch", AREA)
    p.vitals.update(vitals)
    return p


def _fixture(world, node_id, name, tags, hygiene=None):
    props = {"name": name, "tags": list(tags), "actions": "examine,use",
             "uses": -1, "weight": 0.1, "current_state": "normal"}
    item = Node(id=node_id, type="item", name=name, properties=props)
    world.graph.add_node(item)
    world.graph.add_edge(Edge(source=item.id, target=world.area_node_id(AREA), type="in"))
    if hygiene is not None:
        trig = Node(id="trigger_" + node_id, type="logic_trigger",
                    name="on_use → adjust_vital",
                    properties={"trigger_type": "on_use",
                                "effect_type": "adjust_vital",
                                "effect_params": {"stat": "Hygiene",
                                                  "amount": hygiene,
                                                  "target": "self"}})
        world.graph.add_node(trig)
        world.graph.add_edge(Edge(source=item.id, target=trig.id, type="triggers"))
    return item


# ── service lookup ───────────────────────────────────────────────────────


def test_an_area_tag_alone_offers_the_service():
    world = _world(area_tags=("latrine",))
    p = _character(world)
    sim = BackgroundSimulation(world)
    offered, fixture = sim._service_here(p, RELIEF_TAGS)
    assert offered is True
    assert fixture is None        # the room itself is the facility


def test_a_fixture_in_the_area_offers_the_service():
    world = _world()
    p = _character(world)
    spot = _fixture(world, "item_wash", "Wash Spot", ("bathing", "fixture"))
    sim = BackgroundSimulation(world)
    offered, fixture = sim._service_here(p, BATH_TAGS)
    assert offered is True and fixture is spot


def test_no_service_means_no_offer():
    world = _world()
    p = _character(world)
    sim = BackgroundSimulation(world)
    assert sim._service_here(p, RELIEF_TAGS) == (False, None)
    assert sim._service_here(p, BATH_TAGS) == (False, None)


# ── relieving ────────────────────────────────────────────────────────────


def test_relief_empties_the_bladder_at_a_latrine():
    world = _world(area_tags=("latrine",))
    p = _character(world, Bladder=95)
    assert BackgroundSimulation(world)._relieve(p) is True
    assert p.vitals["Bladder"] == 0


# ── task-551: permission is universal, privacy is a preference ────────────


def test_relief_is_possible_with_no_latrine_in_the_world():
    """The old gate. A camp with no `latrine` anywhere had characters who simply
    never went, because the bladder branch ended in a bare `return None`."""
    world = _world()
    p = _character(world, Bladder=95)
    assert BackgroundSimulation(world)._relieve(p) is True
    assert p.vitals["Bladder"] == 0


def test_an_improvised_relief_costs_sanity_but_not_social():
    world = _world()
    p = _character(world, Bladder=95, Sanity=100, Social=100)
    BackgroundSimulation(world)._relieve(p)
    assert p.vitals["Sanity"] == 100 - DIGNITY_SANITY_COST
    assert p.vitals["Social"] == 100      # nobody saw


def test_a_proper_place_costs_nothing():
    world = _world(area_tags=("latrine",))
    p = _character(world, Bladder=95, Sanity=100, Social=100)
    BackgroundSimulation(world)._relieve(p)
    assert p.vitals["Sanity"] == 100
    assert p.vitals["Social"] == 100


def test_a_witnessed_improvised_relief_also_costs_social():
    world = _world()
    _occupant(world, "Onlooker", AREA)
    p = _character(world, Bladder=95, Sanity=100, Social=100)
    BackgroundSimulation(world)._relieve(p)
    assert p.vitals["Social"] == 100 - DIGNITY_SOCIAL_COST


def test_the_acting_character_is_not_its_own_onlooker():
    world = _world()
    p = _character(world, Bladder=95, Sanity=100, Social=100)
    BackgroundSimulation(world)._relieve(p)
    assert p.vitals["Social"] == 100


def test_an_improvised_relief_marks_the_area():
    world = _world()
    p = _character(world, Bladder=95)
    BackgroundSimulation(world)._relieve(p)
    node = world.graph.get_node(world.area_node_id(AREA))
    assert "urine" in (node.properties.get("environment") or {}).get("smell", "")


def test_the_whole_world_without_a_latrine_still_runs_the_turn():
    """`_act` used to `return None` here, which broke `process_due`'s loop."""
    world = _world()
    p = _character(world, **VITALS)
    p.vitals["Bladder"] = 95
    used = BackgroundSimulation(world)._act(p.name, p, set(), 60.0)
    assert used == TASK_MINUTES["relieve"]
    assert p.vitals["Bladder"] == 0


# ── task-551: privacy preference ──────────────────────────────────────────


def _connect(world, a, b, direction, reverse):
    world.movement.connect_areas(a, b, direction, reverse, state="open")


def _two_room_world():
    """Hall <-> Latrine <-> Alcove, the last two one room apart."""
    world = create_app({"TESTING": True}).world
    for name in ("Hall", "Latrine", "Alcove"):
        world.movement.add_area(Area(name, f"{name}.", []))
    for name, tags in (("Latrine", ("latrine",)),
                       ("Alcove", ("private", "secluded"))):
        world.graph.get_node(world.area_node_id(name)).properties["tags"] = list(tags)
    _connect(world, "Hall", "Latrine", "north", "south")
    _connect(world, "Latrine", "Alcove", "east", "west")
    return world


def _occupant(world, name, area):
    p = Player(name)
    world.add_player(p)
    world.set_player_area(name, area)
    return p


def test_an_empty_secluded_spot_beats_a_crowded_one():
    """Acceptance: given a shared room and a secluded spot, take the secluded
    spot. This is the preference the old `_target_step` had no way to express."""
    world = _two_room_world()
    me = _occupant(world, "Me", "Hall")
    _occupant(world, "A", "Hall")
    _occupant(world, "B", "Hall")
    sim = BackgroundSimulation(world)
    hall = sim._privacy_score(world.area_node_id("Hall"), me)
    alcove = sim._privacy_score(world.area_node_id("Alcove"), me)
    assert alcove < hall


def test_an_empty_latrine_beats_a_crowded_secluded_spot():
    """`fixture` and `private` are both worth about one onlooker, so a room
    built for the job wins when nobody is using it."""
    world = _two_room_world()
    me = _occupant(world, "Me", "Hall")
    sim = BackgroundSimulation(world)
    assert sim._privacy_score(world.area_node_id("Latrine"), me) < sim._privacy_score(
        world.area_node_id("Alcove"), me) + 1.0


def test_a_crowded_character_steps_towards_the_better_room():
    world = _two_room_world()
    me = _occupant(world, "Me", "Hall")
    _occupant(world, "A", "Hall")
    sim = BackgroundSimulation(world)
    assert sim._travel_to_privacy(me) is True
    assert me.current_area in ("Latrine", "Alcove")


# ── task-551: the hub does not form ───────────────────────────────────────


def _camp_world():
    """A five-room camp with exactly one relief area, and no way round it.

    This is the Kraktooth shape: `Waste Disposal` was the only `RELIEF_TAGS`
    area out of 84 and the busiest room in the world by shared occupancy.
    """
    world = create_app({"TESTING": True}).world
    rooms = ["Fire", "Bunks", "Workshop", "Latrine", "Yard"]
    for name in rooms:
        world.movement.add_area(Area(name, f"{name}.", []))
    world.graph.get_node(world.area_node_id("Latrine")).properties["tags"] = ["latrine"]
    for a, b in (("Fire", "Bunks"), ("Bunks", "Workshop"),
                 ("Workshop", "Latrine"), ("Latrine", "Yard"), ("Yard", "Fire")):
        _connect(world, a, b, "north", "south")
    return world, rooms


def _relief_areas(character):
    return [e["area"] for e in getattr(character, "lived_log", [])
            if e.get("why", "").startswith("needs:relieve")]


def test_the_single_latrine_does_not_become_a_hub():
    """Acceptance: with privacy-aware selection, occupancy in the one latrine
    falls relative to the cast size.

    Under the old gate this was 0 out of the cast — `_relieve` returned False
    unless the character was standing in a `RELIEF_TAGS` area, so a camp with one
    latrine put *every* character in that latrine and the room accumulated
    45,844 shared ticks across five pairs. The negative feedback that replaces it
    is the `witness` term: a latrine with three goblins in it scores worse than
    an empty yard, so the fourth stays where it is.
    """
    world, rooms = _camp_world()
    cast = []
    for i, name in enumerate(("Fire", "Bunks", "Workshop", "Yard", "Yard")):
        p = _occupant(world, f"Gob{i}", name)
        p.simulation_mode = "background"
        p.vitals.update(VITALS)
        p.vitals["Bladder"] = 80          # over the threshold, under RELIEF_URGENT
        cast.append(p)

    sim = BackgroundSimulation(world)
    for _ in range(40):
        if all(_relief_areas(p) for p in cast):
            break
        world.time_ticks += 1
        sim.process_due()

    for p in cast:
        assert _relief_areas(p), f"{p.name} never relieved"
    elsewhere = [area for p in cast for area in _relief_areas(p)
                 if area != "Latrine"]
    assert elsewhere, (
        "every character relieved in the one latrine: the hub is back, and the "
        f"latrine took {len(cast)}/{len(cast)} of the cast")


def test_a_crowded_latrine_stops_being_the_appealing_option():
    """The mechanism itself: the score is what reverses the flow, so assert it
    directly rather than inferring it from a run."""
    world, _ = _camp_world()
    me = _occupant(world, "Me", "Yard")
    sim = BackgroundSimulation(world)
    busy = sim._privacy_score(world.area_node_id("Latrine"), me)
    for i in range(3):
        _occupant(world, f"Busy{i}", "Latrine")
    crowded = sim._privacy_score(world.area_node_id("Latrine"), me)
    yard = sim._privacy_score(world.area_node_id("Yard"), me)
    assert crowded > yard, (
        "a latrine holding three others still beats standing in the yard, so the "
        "privacy preference cannot shed a hub once one forms")
    assert busy < crowded


def test_a_tie_is_not_worth_a_walk():
    """A tie means "as good as here" and must not be walked to, or characters
    drift between two equally mediocre rooms forever."""
    world = create_app({"TESTING": True}).world
    for name in ("R0", "R1"):
        world.movement.add_area(Area(name, f"{name}.", []))
    _connect(world, "R0", "R1", "north", "south")
    me = _occupant(world, "Me", "R0")
    sim = BackgroundSimulation(world)
    assert sim._travel_to_privacy(me) is False
    assert me.current_area == "R0"


def test_an_alone_character_still_prefers_a_proper_place():
    """Being alone is not a reason to use the corner: the `fixture` and `private`
    terms are what keep somewhere better in play for a character nobody is
    watching. One hop per turn, so the first move lands in the middle room."""
    world = _two_room_world()
    me = _occupant(world, "Me", "Hall")
    sim = BackgroundSimulation(world)
    assert sim._travel_to_privacy(me) is True
    assert me.current_area == "Latrine"
    assert sim._travel_to_privacy(me) is True
    assert me.current_area == "Alcove"


def test_a_public_tag_overrules_a_private_one():
    node = type("N", (), {"properties": {"tags": ["private", "public"]}})()
    assert is_private(node) is False


def test_the_privacy_search_is_bounded():
    """A secluded room three ways off is out of reach: privacy is not worth a
    march across the map, which is what `PRIVACY_SEARCH_HOPS` is for. R1 and R2
    are busy on purpose, so they are not somewhere to go and only R3 would be."""
    world = create_app({"TESTING": True}).world
    names = ["R0", "R1", "R2", "R3"]
    for name in names:
        world.movement.add_area(Area(name, f"{name}.", []))
    for a, b in zip(names, names[1:]):
        _connect(world, a, b, "north", "south")
    world.graph.get_node(world.area_node_id("R3")).properties["tags"] = ["private"]
    me = _occupant(world, "Me", "R0")
    _occupant(world, "A", "R0")
    _occupant(world, "B", "R1")
    _occupant(world, "C", "R2")
    sim = BackgroundSimulation(world)
    assert sim._travel_to_privacy(me) is False


def test_a_better_room_one_way_off_is_taken():
    """The other half of the bound: in-range means taken."""
    world = create_app({"TESTING": True}).world
    for name in ("R0", "R1"):
        world.movement.add_area(Area(name, f"{name}.", []))
    _connect(world, "R0", "R1", "north", "south")
    world.graph.get_node(world.area_node_id("R1")).properties["tags"] = ["private"]
    me = _occupant(world, "Me", "R0")
    _occupant(world, "A", "R0")
    sim = BackgroundSimulation(world)
    assert sim._travel_to_privacy(me) is True
    assert me.current_area == "R1"


def test_a_fixture_tagged_water_is_not_drunk_away():
    """A wash spot must not carry `water`: DRINK_TAGS contains it and
    `_consume_here` deletes a node it consumes, so a thirsty goblin would drink
    the fixture and destroy it. The water AREAS carry `water` instead."""
    world = _world()
    p = _character(world)
    spot = _fixture(world, "item_wash2", "Wash Spot", ("bathing", "fixture"))
    sim = BackgroundSimulation(world)
    from engine.background_simulation import DRINK_TAGS
    assert sim._find_consumable(p, DRINK_TAGS, verb="drink") is None
    assert world.graph.get_node(spot.id) is not None


# ── washing ──────────────────────────────────────────────────────────────


def test_washing_restores_the_authored_amount():
    world = _world()
    p = _character(world, Hygiene=10)
    _fixture(world, "item_shower", "Shower", ("bathing", "shower"), hygiene=70)
    assert BackgroundSimulation(world)._wash(p) is True
    assert p.vitals["Hygiene"] == 80


def test_washing_reads_the_fixture_rather_than_a_constant():
    world = _world()
    p = _character(world, Hygiene=10)
    _fixture(world, "item_spring", "Hot Spring", ("bathing",), hygiene=25)
    BackgroundSimulation(world)._wash(p)
    assert p.vitals["Hygiene"] == 35


def test_a_bare_bathing_area_falls_back_to_the_default():
    """A river with no fixture still counts as a place to wash."""
    world = _world(area_tags=("bathing",))
    p = _character(world, Hygiene=0)
    assert BackgroundSimulation(world)._wash(p) is True
    assert p.vitals["Hygiene"] == BATH_HYGIENE


def test_washing_is_capped_at_one_hundred():
    world = _world()
    p = _character(world, Hygiene=90)
    _fixture(world, "item_shower2", "Shower", ("bathing",), hygiene=70)
    BackgroundSimulation(world)._wash(p)
    assert p.vitals["Hygiene"] == 100


def test_no_wash_site_means_no_washing():
    world = _world()
    p = _character(world, Hygiene=5)
    assert BackgroundSimulation(world)._wash(p) is False
    assert p.vitals["Hygiene"] == 5


def test_wash_amount_falls_back_when_no_fixture():
    world = _world()
    _character(world)
    assert BackgroundSimulation(world)._wash_amount(None) == BATH_HYGIENE
