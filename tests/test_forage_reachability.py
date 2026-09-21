"""What a background forager can reach, and what counts as food.

Three bugs lived here, all invisible until a plant tried to feed the camp:

1. `_find_consumable` only looked at items with an `in` edge to the area, so food
   in a container (berries on a bush, a larder, a basket) could not be found and
   the background tier starved beside a full store.
2. `_areas_with` — which decides the area a forager *travels to* — had the same
   blind spot, so nobody ever walked to where the renewed supply actually was.
3. The action fallback in `_is_consumable` accepted an item with EITHER an `eat`
   or a `drink` action, so a hungry character ate a water skin and Hunger was
   satisfied.

Positives are asserted against TEST_FOOD rather than the real FOOD_TAGS because
the boot template ships junk food items with generated ids and names
("Bread_b4080839"), which makes a shared-world search ambiguous.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from area import Area
from graph import Node, Edge
from player import Player
from engine.background_simulation import (
    BackgroundSimulation, FOOD_TAGS, DRINK_TAGS,
)

#: Not a boot-template area name, so the fixture cannot collide with template
#: content (the template already has a populated Deep Forest).
AREA = "Test Grove"

#: No boot-template item carries this tag.
TEST_FOOD = ("testgrub",)


def _world():
    world = create_app({"TESTING": True}).world
    world.movement.add_area(Area(AREA, "Somewhere wooded.", []))
    return world


def _item(world, node_id, name, tags=(), actions="examine"):
    node = Node(id=node_id, type="item", name=name, properties={
        "name": name, "tags": list(tags), "actions": actions,
        "weight": 1.0, "current_state": "normal",
    })
    world.graph.add_node(node)
    return node


def _hold(world, item_id, holder_id, relation="in"):
    world.graph.add_edge(Edge(source=item_id, target=holder_id, type=relation))


def _forager(world):
    p = Player("Forager")
    world.add_player(p)
    world.set_player_area("Forager", AREA)
    return p, BackgroundSimulation(world)


# ── reaching through spatial relations ───────────────────────────────────


def test_food_on_the_floor_is_found():
    world = _world()
    bread = _item(world, "item_bread", "Bread", TEST_FOOD, "eat")
    _hold(world, bread.id, world.area_node_id(AREA))
    p, sim = _forager(world)
    # Identity, not id: the graph renames a node whose id/name already exists
    # elsewhere, so the id it ends up with is not the one we asked for.
    assert sim._find_consumable(p, TEST_FOOD, verb="eat") is bread


def test_food_on_a_surface_behind_or_under_something_is_found():
    """`on`/`under`/`behind`/`beside`/`at` are reachable, not just `in`."""
    for relation in ("on", "under", "behind", "beside", "at"):
        world = _world()
        table = _item(world, "item_table", "Table")
        _hold(world, table.id, world.area_node_id(AREA), "in")
        stew = _item(world, "item_stew", "Stew", TEST_FOOD, "eat")
        _hold(world, stew.id, table.id, relation)
        p, sim = _forager(world)
        assert sim._find_consumable(p, TEST_FOOD, verb="eat") is stew, relation


def test_food_inside_a_bush_is_found():
    """One level of containment: berries on a bush (task-410)."""
    world = _world()
    bush = _item(world, "item_bush", "Berry Bush", ["vegetation", "plant"])
    _hold(world, bush.id, world.area_node_id(AREA), "in")
    berries = _item(world, "item_berries", "Berries", TEST_FOOD, "eat")
    _hold(world, berries.id, bush.id, "in")
    p, sim = _forager(world)
    assert sim._find_consumable(p, TEST_FOOD, verb="eat") is berries


def test_the_bush_itself_is_not_food():
    """The tag trap: an untagged plant must never be eaten."""
    world = _world()
    bush = _item(world, "item_bush2", "Berry Bush", ["vegetation", "plant"])
    _hold(world, bush.id, world.area_node_id(AREA), "in")
    p, sim = _forager(world)
    assert sim._find_consumable(p, TEST_FOOD, verb="eat") is None


def test_a_carried_item_wins_over_the_room():
    world = _world()
    _hold(world, _item(world, "item_floor_food", "Bread", TEST_FOOD, "eat").id,
          world.area_node_id(AREA))
    p, sim = _forager(world)
    held = _item(world, "item_held_food", "Rations", TEST_FOOD, "eat")
    world.graph.add_edge(Edge(source=held.id,
                              target=world._player_node_id(p.name),
                              type="carrying"))
    assert sim._find_consumable(p, TEST_FOOD, verb="eat") is held


# ── intent: food is not drink ────────────────────────────────────────────


def test_a_water_skin_is_not_food():
    """The fallback used to accept either action, so a hungry character ate one."""
    world = _world()
    _hold(world, _item(world, "item_skin", "Water Skin", ["container"],
                       "examine,drink,fill").id, world.area_node_id(AREA))
    p, sim = _forager(world)
    assert sim._find_consumable(p, FOOD_TAGS, verb="eat") is None
    assert sim._find_consumable(p, DRINK_TAGS, verb="drink").id == "item_skin"


def test_a_meal_is_not_drink():
    world = _world()
    stew = _item(world, "item_stew2", "Stew", TEST_FOOD, "examine,eat")
    _hold(world, stew.id, world.area_node_id(AREA))
    p, sim = _forager(world)
    assert sim._find_consumable(p, DRINK_TAGS, verb="drink") is None
    assert sim._find_consumable(p, TEST_FOOD, verb="eat") is stew


# ── travel targeting ─────────────────────────────────────────────────────


def test_an_area_holding_food_in_a_container_counts_as_a_food_area():
    """Otherwise nobody walks to the forest where the bushes are."""
    world = _world()
    bush = _item(world, "item_bush3", "Berry Bush", ["vegetation", "plant"])
    _hold(world, bush.id, world.area_node_id(AREA), "in")
    _hold(world, _item(world, "item_berries2", "Berries", TEST_FOOD, "eat").id,
          bush.id, "in")
    _forager(world)
    assert AREA in BackgroundSimulation(world)._areas_with(TEST_FOOD, verb="eat")


def test_an_empty_forest_is_not_a_food_area():
    world = _world()
    bush = _item(world, "item_bush4", "Berry Bush", ["vegetation", "plant"])
    _hold(world, bush.id, world.area_node_id(AREA), "in")
    _forager(world)
    assert AREA not in BackgroundSimulation(world)._areas_with(TEST_FOOD, verb="eat")
