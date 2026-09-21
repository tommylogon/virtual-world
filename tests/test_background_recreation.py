"""Background recreation — Entertainment's recurring source (task-425).

Entertainment had none. Novelty paid once per area and once per item, ever, and
`ACTIVITY_REGEN` has nothing recreational in it, so a settled goblin's
Entertainment decayed to 0 within a day and stayed there for the rest of the
week: the soak ended pinned at 0.

Recreation is a **fixture** — the same shape as the wash spot: a standing item
tagged `recreation` with an authored `on_use → adjust_vital Entertainment`, never
depleting. The background tier seeks one when Entertainment is low, and the need
gate is also the anti-spam: after using it, Entertainment sits above the
threshold for the better part of a day.

These fixtures must never be tagged `food` or `drink`: `_consume_here` deletes a
node it consumes, so a hungry goblin would eat the drum.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from area import Area
from graph import Node, Edge
from player import Player
from engine.background_simulation import (
    BackgroundSimulation, RECREATION_TAGS, ENTERTAINMENT_RESTORE,
    ENTERTAINMENT_THRESHOLD, FOOD_TAGS, DRINK_TAGS,
)
from routes.helpers import load_registry

ROOT = Path(__file__).parent.parent
DATA_DIR = str(ROOT / "data")
AREA = "Verdant Hollow"


def _library_items():
    return load_registry(DATA_DIR, "items.json")


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


def _fixture(world, node_id, name, tags, stat=None, amount=None):
    props = {"name": name, "tags": list(tags), "actions": "examine,use",
             "uses": -1, "weight": 0.1, "current_state": "normal"}
    item = Node(id=node_id, type="item", name=name, properties=props)
    world.graph.add_node(item)
    world.graph.add_edge(Edge(source=item.id, target=world.area_node_id(AREA), type="in"))
    if stat is not None:
        trig = Node(id="trigger_" + node_id, type="logic_trigger",
                    name="on_use → adjust_vital",
                    properties={"trigger_type": "on_use",
                                "effect_type": "adjust_vital",
                                "effect_params": {"stat": stat,
                                                  "amount": amount,
                                                  "target": "self"}})
        world.graph.add_node(trig)
        world.graph.add_edge(Edge(source=item.id, target=trig.id, type="triggers"))
    return item


# ── the authored amount is the single source of truth ────────────────────


def test_a_fixture_amount_is_read_from_its_authored_trigger():
    world = _world()
    _fixture(world, "item_drum", "War Drum", ("recreation", "fixture"),
             stat="Entertainment", amount=18)
    sim = BackgroundSimulation(world)
    assert sim._fixture_amount(world.graph.get_node("item_drum"),
                               "Entertainment", 0) == 18


def test_the_amount_falls_back_when_a_fixture_authors_nothing():
    world = _world()
    drum = _fixture(world, "item_drum", "War Drum", ("recreation",))
    sim = BackgroundSimulation(world)
    assert sim._fixture_amount(drum, "Entertainment", ENTERTAINMENT_RESTORE) == ENTERTAINMENT_RESTORE
    assert sim._fixture_amount(None, "Entertainment", ENTERTAINMENT_RESTORE) == ENTERTAINMENT_RESTORE


def test_the_wash_path_still_reads_hygiene():
    """Generalising the reader must not break washing."""
    world = _world()
    _fixture(world, "item_wash", "Wash Spot", ("bathing",),
             stat="Hygiene", amount=70)
    sim = BackgroundSimulation(world)
    assert sim._wash_amount(world.graph.get_node("item_wash")) == 70


# ── recreating ───────────────────────────────────────────────────────────


def test_recreation_restores_entertainment_in_place():
    world = _world()
    p = _character(world, Entertainment=10)
    _fixture(world, "item_drum", "War Drum", ("recreation", "fixture"),
             stat="Entertainment", amount=18)
    sim = BackgroundSimulation(world)

    assert sim._recreate(p) is True
    assert p.vitals["Entertainment"] == 28


def test_recreation_is_clamped_at_100():
    world = _world()
    p = _character(world, Entertainment=95)
    _fixture(world, "item_drum", "War Drum", ("recreation",),
             stat="Entertainment", amount=18)
    sim = BackgroundSimulation(world)

    sim._recreate(p)
    assert p.vitals["Entertainment"] == 100


def test_no_fixture_means_no_recreation():
    world = _world()
    p = _character(world, Entertainment=10)
    sim = BackgroundSimulation(world)
    assert sim._recreate(p) is False
    assert p.vitals["Entertainment"] == 10


def test_an_area_tagged_recreation_offers_the_service():
    """A gathering place can be the recreation, with no fixture at all."""
    world = _world(area_tags=("recreation",))
    p = _character(world, Entertainment=10)
    sim = BackgroundSimulation(world)
    assert sim._service_here(p, RECREATION_TAGS) == (True, None)
    assert sim._recreate(p) is True
    assert p.vitals["Entertainment"] == 10 + ENTERTAINMENT_RESTORE


def test_a_bored_character_seeks_recreation():
    world = _world()
    p = _character(world, Hunger=0, Thirst=0, Energy=100, Bladder=0,
                   Hygiene=100, Entertainment=ENTERTAINMENT_THRESHOLD - 1)
    _fixture(world, "item_drum", "War Drum", ("recreation",),
             stat="Entertainment", amount=18)
    sim = BackgroundSimulation(world)

    sim._act("Wretch", p)
    assert p.vitals["Entertainment"] == ENTERTAINMENT_THRESHOLD - 1 + 18


def test_hunger_outranks_boredom():
    """Boredom is the only need here that does not kill you, so it goes last."""
    world = _world()
    p = _character(world, Hunger=90, Thirst=0, Energy=100, Bladder=0,
                   Hygiene=100, Entertainment=0)
    _fixture(world, "item_drum", "War Drum", ("recreation",),
             stat="Entertainment", amount=18)
    food = _fixture(world, "item_stew", "Stew", ("food",), stat="Hunger", amount=-45)
    sim = BackgroundSimulation(world)

    sim._act("Wretch", p)
    assert p.vitals["Entertainment"] == 0  # ate instead
    assert p.vitals["Hunger"] < 90


def test_recreation_fixtures_are_never_edible_or_drinkable():
    """A drum tagged `food` would be eaten and deleted by `_consume_here`."""
    items = _library_items()
    for item_id in ("camp_drum", "knucklebones", "story_fire"):
        entry = items.get(item_id)
        assert entry is not None, f"{item_id} missing from the library"
        tags = {str(t).lower() for t in (entry.get("tags") or [])}
        assert "recreation" in tags, f"{item_id} is not tagged recreation"
        assert not (set(FOOD_TAGS) & tags), f"{item_id} is edible"
        assert not (set(DRINK_TAGS) & tags), f"{item_id} is drinkable"


def test_every_recreation_fixture_authors_an_entertainment_amount():
    items = _library_items()
    for item_id in ("camp_drum", "knucklebones", "story_fire"):
        entry = items[item_id]
        amounts = [
            (t.get("effect_params") or {}).get("amount")
            for t in (entry.get("triggers") or [])
            if t.get("effect_type") == "adjust_vital"
            and str((t.get("effect_params") or {}).get("stat", "")).lower()
            == "entertainment"
        ]
        assert amounts, f"{item_id} authors no Entertainment"
        assert all(isinstance(a, int) and a > 0 for a in amounts)


def test_the_fixtures_are_placed_in_the_camp():
    import json
    scenario = ROOT / "data" / "scenarios" / "kraktooth_goblin_camp.json"
    with open(scenario, encoding="utf-8-sig") as fh:
        data = json.load(fh)
    nodes = data["graph"]["nodes"]
    by_id = {n["id"]: n for n in nodes} if isinstance(nodes, list) else nodes
    for node_id in ("camp_drum_chiefs_pit_1",
                    "knucklebones_camp_entrance_1",
                    "story_fire_cooking_area_1"):
        assert node_id in by_id, f"{node_id} was never placed"
        tags = {str(t).lower() for t in (by_id[node_id].get("properties") or {}).get("tags", [])}
        assert "recreation" in tags
