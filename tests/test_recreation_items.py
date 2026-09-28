"""Carried recreation and performance items (task-517).

Companion to `test_background_recreation.py` (task-425), which owns the
*fixture* path. Recreation used to be area-fixture only: `_recreate` looked for a
stand with the `recreation` tag and found nothing else, so a goblin carrying
Rikka's kit in their pack had no way to spend a bored hour unless the camp
happened to contain a drum as well.

The area is still checked **first**, deliberately, and three things are pinned
here because they are the three ways this could quietly go wrong:

1. the fixture path must not move — an existing soak cannot shift;
2. a carried item must not be a free infinite top-up;
3. a spent one must stop being used, or a long soak beats an empty drum forever.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from area import Area
from graph import EDGE_CARRYING, EDGE_IN, Edge, Node
from player import Player
from engine.background_simulation import (
    BackgroundSimulation,
    ENTERTAINMENT_RESTORE,
    ENTERTAINMENT_THRESHOLD,
    RECREATION_ENERGY_COST,
    RECREATION_TAGS,
)

ROOT = Path(__file__).parent.parent
LIB = ROOT / "data" / "library" / "items"
AREA = "Kraktooth Camp"

RIKKA_KIT = ["juggling_stones", "little_drum", "string_puppet", "nested_cups"]


def _lib(item_id):
    return json.loads((LIB / f"{item_id}.json").read_text(encoding="utf-8-sig"))


def _world():
    world = create_app({"TESTING": True}).world
    world.movement.add_area(Area(AREA, "Stones and cookfires.", []))
    return world


def _character(world, **vitals):
    p = Player("Wretch")
    world.add_player(p)
    world.set_player_area("Wretch", AREA)
    p.vitals.update({"Entertainment": 10, "Energy": 100, "Hunger": 0,
                     "Thirst": 0, "Bladder": 0, "Hygiene": 100})
    p.vitals.update(vitals)
    return p


def _carry(world, library_id, p):
    node, _lib = world.effects._hydrate_item(library_id, {}, always_fresh=True)
    world.graph.add_edge(Edge(source=node.id,
                              target=world._player_node_id(p.name),
                              type=EDGE_CARRYING))
    return node


def _fixture(world, node_id="item_war_drum", stat="Entertainment", amount=20):
    """A standing recreation fixture, shaped like the ones task-425 authored."""
    props = {"name": "War Drum", "tags": list(RECREATION_TAGS) + ["fixture"],
             "actions": "examine,use", "uses": -1, "weight": 2,
             "current_state": "normal"}
    item = Node(id=node_id, type="item", name=props["name"], properties=props)
    world.graph.add_node(item)
    world.graph.add_edge(Edge(source=item.id, target=world.area_node_id(AREA), type="in"))
    if stat:
        trig = Node(id="trigger_" + node_id, type="logic_trigger",
                    name="on_use → adjust_vital",
                    properties={"trigger_type": "on_use",
                                "effect_type": "adjust_vital",
                                "effect_params": {"stat": stat, "amount": amount,
                                                  "target": "self"}})
        world.graph.add_node(trig)
        world.graph.add_edge(Edge(source=item.id, target=trig.id, type="triggers"))
    return item


def _hero(world):
    """The world's own active character, for the foreground `use` tests.

    `world.use_item` acts on whoever is active, so a test that stages items for
    a newly added "Wretch" would quietly exercise someone else. The background
    tests use `_character` instead, which is unaffected.
    """
    return world.player_manager.active_player, \
        world.player_manager.get_player(world.player_manager.active_player)


def _give_hero(world, library_id):
    name, _p = _hero(world)
    node, _lib = world.effects._hydrate_item(library_id, {}, always_fresh=True)
    world.graph.add_edge(Edge(source=node.id,
                              target=world._player_node_id(name),
                              type=EDGE_CARRYING))
    return node


# ── Rikka's kit is authored on the model (criterion 4) ─────────────────────


def test_the_whole_kit_is_authored():
    for item_id in RIKKA_KIT:
        assert (LIB / f"{item_id}.json").exists(), item_id


def test_every_kit_item_is_tagged_recreation():
    """The tag IS the contract — `_carried_recreation` finds nothing else."""
    for item_id in RIKKA_KIT:
        assert "recreation" in _lib(item_id).get("tags", []), item_id


def test_every_kit_item_is_usable_and_carryable():
    for item_id in RIKKA_KIT:
        actions = _lib(item_id).get("actions", "")
        assert "use" in actions, item_id
        assert "take" in actions and "drop" in actions, item_id


def test_every_kit_item_restores_entertainment():
    """Foreground use must reach `adjust_vital Entertainment` — nothing routed
    `use` to that vital before this task."""
    for item_id in RIKKA_KIT:
        stats = {(e.get("params") or {}).get("stat")
                 for t in _lib(item_id).get("triggers") or []
                 for e in (t.get("effects") or [])
                 if e.get("type") == "adjust_vital"}
        assert "Entertainment" in stats, f"{item_id} authors no Entertainment: {stats}"


def test_the_drum_is_finite_and_the_rest_are_not():
    """A drum has a skin that wears out; pebbles, cups and a puppet do not."""
    assert _lib("little_drum")["uses"] == 40
    for item_id in ("juggling_stones", "string_puppet", "nested_cups"):
        assert _lib(item_id)["uses"] == -1, item_id


def test_the_fallback_amount_is_read_from_the_authored_effect():
    """Same rule as a fixture: the library entry is the source of truth."""
    world = _world()
    p = _character(world, Entertainment=0)
    stones = _carry(world, "juggling_stones", p)
    assert BackgroundSimulation(world)._fixture_amount(stones, "Entertainment", 0) == 15


# ── foreground use (criterion 1) ──────────────────────────────────────────


def test_using_a_carried_item_raises_entertainment():
    world = _world()
    _name, p = _hero(world)
    p.vitals["Entertainment"] = 10
    _give_hero(world, "juggling_stones")
    world.use_item("juggling stones")
    assert p.vitals["Entertainment"] > 10


def test_foreground_use_spends_a_finite_charge():
    world = _world()
    _name, p = _hero(world)
    p.vitals["Entertainment"] = 10
    drum = _give_hero(world, "little_drum")
    drum.properties["uses"] = 2
    world.use_item("little drum")
    assert drum.properties["uses"] == 1
    world.use_item("little drum")
    assert drum.properties["uses"] == 0


def test_a_permanent_item_is_not_decremented():
    world = _world()
    _name, p = _hero(world)
    p.vitals["Entertainment"] = 10
    stones = _give_hero(world, "juggling_stones")
    world.use_item("juggling stones")
    assert stones.properties["uses"] == -1


# ── the background fallback (criterion 2) ─────────────────────────────────


def test_a_npc_with_no_fixture_can_recreate():
    """The headline case: kit in the pack, nothing recreational in the area."""
    world = _world()
    p = _character(world, Entertainment=10)
    _carry(world, "little_drum", p)
    assert BackgroundSimulation(world)._recreate(p) is True
    assert p.vitals["Entertainment"] == 10 + 18


def test_no_fixture_and_no_carried_item_means_nothing_happens():
    world = _world()
    p = _character(world, Entertainment=10)
    assert BackgroundSimulation(world)._recreate(p) is False
    assert p.vitals["Entertainment"] == 10


def test_an_unrelated_carried_item_is_never_an_entertainment_source():
    world = _world()
    p = _character(world, Entertainment=10)
    _carry(world, "iron_key", p)
    assert BackgroundSimulation(world)._recreate(p) is False


def test_the_fallback_costs_energy():
    world = _world()
    p = _character(world, Entertainment=10, Energy=100)
    _carry(world, "juggling_stones", p)
    BackgroundSimulation(world)._recreate(p)
    assert p.vitals["Energy"] == 100 - RECREATION_ENERGY_COST


def test_the_fallback_spends_a_finite_charge():
    world = _world()
    p = _character(world, Entertainment=10)
    drum = _carry(world, "little_drum", p)
    drum.properties["uses"] = 3
    BackgroundSimulation(world)._recreate(p)
    assert drum.properties["uses"] == 2


def test_a_spent_item_is_not_used_again():
    """The one that matters in a long soak: at zero charges the fallback must
    report False rather than top the character up from an empty drum."""
    world = _world()
    p = _character(world, Entertainment=10)
    drum = _carry(world, "little_drum", p)
    drum.properties["uses"] = 0
    assert BackgroundSimulation(world)._recreate(p) is False
    assert p.vitals["Entertainment"] == 10


def test_a_worn_out_item_is_marked_not_deleted():
    """A used-up drum is still a drum. Deleting it would quietly remove a
    keepsake out of a character's pack."""
    world = _world()
    p = _character(world, Entertainment=10)
    drum = _carry(world, "little_drum", p)
    drum.properties["uses"] = 1
    BackgroundSimulation(world)._recreate(p)
    assert world.graph.get_node(drum.id) is not None
    assert drum.properties["current_state"] == "used_up"


def test_a_hidden_carried_item_is_not_used():
    world = _world()
    p = _character(world, Entertainment=10)
    stones = _carry(world, "juggling_stones", p)
    stones.properties["current_state"] = "hidden"
    assert BackgroundSimulation(world)._recreate(p) is False


def test_it_does_not_spam_itself():
    """The need gate is the anti-spam, and it is a *threshold*, not a
    once-per-tick rule: an 18-point kit takes a few rounds to lift a character
    off zero, then stops. What must hold is that it does not keep firing once
    the character is above the line — otherwise a goblin beats a drum forever.

    The drum is finite so the number of rounds is countable, which is also the
    case where a bug would actually bite in a long soak."""
    world = _world()
    p = _character(world, Entertainment=0)
    drum = _carry(world, "little_drum", p)
    sim = BackgroundSimulation(world)
    start = drum.properties["uses"]

    rounds = 0
    while p.vitals["Entertainment"] <= ENTERTAINMENT_THRESHOLD and rounds < 50:
        sim._recreate(p)
        rounds += 1
    assert p.vitals["Entertainment"] > ENTERTAINMENT_THRESHOLD
    spent = start - drum.properties["uses"]
    assert spent == rounds, "one charge per round, no more"
    assert 1 < rounds < 50, f"a {ENTERTAINMENT_THRESHOLD}-point climb takes a few rounds, got {rounds}"

    # Above the threshold the gate is what stops it, and nothing else touches
    # the kit: a further `_act` must not spend another charge.
    for _ in range(5):
        sim._act("Wretch", p)
    assert drum.properties["uses"] == start - spent, "no use above the threshold"


def test_a_bored_character_reaches_for_their_own_kit():
    """The end-to-end path: `_act` picks it up, not just `_recreate` directly."""
    world = _world()
    p = _character(world, Entertainment=ENTERTAINMENT_THRESHOLD - 1)
    _carry(world, "juggling_stones", p)
    before = p.vitals["Entertainment"]
    BackgroundSimulation(world)._act("Wretch", p)
    assert p.vitals["Entertainment"] > before


# ── the fixture path is unchanged (criterion 3) ───────────────────────────


def test_a_fixture_still_wins_over_a_carried_item():
    """The area is checked FIRST, deliberately. A camp with a drum must behave
    exactly as it did, and the drum must not lose a charge to a goblin who
    happens to be carrying a puppet."""
    world = _world()
    p = _character(world, Entertainment=0, Energy=100)
    stones = _carry(world, "juggling_stones", p)
    before_uses = stones.properties["uses"]
    _fixture(world, amount=20)

    assert BackgroundSimulation(world)._recreate(p) is True
    assert p.vitals["Entertainment"] == 20, "the fixture's own authored amount is used"
    assert p.vitals["Energy"] == 100, "the fixture path stays free, as it always was"
    assert stones.properties["uses"] == before_uses, "the carried item is not touched"


def test_the_fixture_only_path_is_untouched():
    world = _world()
    p = _character(world, Entertainment=0, Energy=100)
    _fixture(world, amount=20)
    assert BackgroundSimulation(world)._recreate(p) is True
    assert p.vitals["Entertainment"] == 20
    assert p.vitals["Energy"] == 100


def test_an_area_tagged_recreation_still_counts_and_stays_free():
    world = _world()
    node = world.graph.get_node(world.area_node_id(AREA))
    node.properties["tags"] = [RECREATION_TAGS[0]]
    p = _character(world, Entertainment=0, Energy=100)
    assert BackgroundSimulation(world)._recreate(p) is True
    assert p.vitals["Entertainment"] == ENTERTAINMENT_RESTORE
    assert p.vitals["Energy"] == 100


def test_the_kit_never_makes_a_goblin_edible():
    """A recreation item tagged `food` would be eaten and deleted by
    `_consume_here` (task-425's standing constraint, still true for a carried
    one)."""
    from engine.background_simulation import DRINK_TAGS, FOOD_TAGS

    for item_id in RIKKA_KIT:
        tags = {str(t).lower() for t in _lib(item_id).get("tags", [])}
        assert not (set(FOOD_TAGS) & tags), f"{item_id} is edible"
        assert not (set(DRINK_TAGS) & tags), f"{item_id} is drinkable"
