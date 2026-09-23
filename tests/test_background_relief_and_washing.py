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
    BackgroundSimulation, RELIEF_TAGS, BATH_TAGS, BATH_HYGIENE,
)

AREA = "Verdant Hollow"


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


def test_no_latrine_means_no_relief():
    """The engine's own -8 Hygiene penalty is the honest outcome then."""
    world = _world()
    p = _character(world, Bladder=95)
    assert BackgroundSimulation(world)._relieve(p) is False
    assert p.vitals["Bladder"] == 95


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
