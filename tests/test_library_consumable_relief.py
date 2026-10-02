"""Library food and drink actually feed you, on the player's own path (task-506).

`ConsumeActionsMixin._consume_item` has **no fallback**. It runs the item's
`on_eat`/`on_drink` triggers and that is the whole of what eating does. The
`MEAL_RESTORE`/`DRINK_RESTORE` constants live only in
`BackgroundSimulation._consume_here`, on the deterministic background path.

So for any library item that carried a `food` tag but no relieving
`adjust_vital`, the two tiers silently disagreed:

- a **background** goblin ate it and got the hardcoded 45 Hunger back;
- the **player** ate it, heard `"You eat the Bread. It tastes good"`, and got
  **nothing**. `bread.json` shipped exactly that — an `on_eat` whose only effect
  was a `message` — and so did 40-odd others.

These tests build the real engine, drop the shipped library item into a real
area, and eat it as the player. The assertion is the vital, not the prose: a
character who eats and stays starving is the bug.

`tools/lint_library.py --check unauthored_consumables` is what stops this
creeping back across the other 500-odd items; see
`tests/test_library_lint_consumables.py`.
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from graph import EDGE_IN, Node  # noqa: E402
from player import Player  # noqa: E402

LIB = ROOT / "data" / "library" / "items"
AREA = "Test Kitchen"

#: A representative spread. The first is the one that was quietly broken.
FOOD = ["bread", "berries", "apple", "dried_meat", "canned_peaches", "granola_bar",
        "jerky", "mushrooms", "protein_bar", "wild_berries"]
DRINK = ["water_skin", "water_bottle", "wine", "candy_jar", "energy_drink"]


def _library(name):
    with open(LIB / f"{name}.json", encoding="utf-8") as handle:
        return json.load(handle)


def _world_with_item(item_id, area_name=AREA):
    """A real world with the shipped library item sitting in a real area.

    Both the `name` and the node `id` are made unique, because the fixture
    already ships items called `Bread` with the id `item_bread`. A colliding
    *name* makes `find_item_node` resolve the fixture's copy instead of this
    one. A colliding *id* is **not** destructive — `graph.add_node` suffixes an
    item id (and name) rather than replacing it (graph.py:162-170) — but the
    suffix would make the asserted id unpredictable, so this test picks its own.
    Only `name` and `id` differ; every tag, trigger and `uses` value is the
    shipped data.
    """
    app = create_app({"TESTING": True})
    world = app.world
    from area import Area
    world.movement.add_area(Area(area_name, "A test kitchen.", []))
    area_id = world.area_node_id(area_name)
    entry = _library(item_id)
    display = f"{entry.get('name', item_id)} sample {item_id}"
    node_id = f"item_sample_{item_id}"
    node = Node(id=node_id, type="item", name=display,
                properties=dict(entry, name=display))
    world.graph.add_node(node)
    world.graph.add_edge(_Edge(node_id, area_id))
    player = Player("Taster")
    world.add_player(player)
    world.set_player_area("Taster", area_name)
    world.player_manager.set_active_player("Taster")
    return world, player, node, display


def _Edge(source, target):
    from graph import Edge
    return Edge(source=source, target=target, type=EDGE_IN)


def _wire_triggers(world, item_id, entry):
    """Library entries carry triggers; the graph needs them as trigger nodes.

    The trigger body goes on the **edge properties**, not just the node. That is
    not a stylistic choice: `engine/triggers/execution.py:324-346` reads
    `e.properties.get("trigger_type")` off the edge when deciding whether
    anything can fire, so a trigger node carrying the body with an empty edge
    silently never runs. Every real authoring path does it this way — the
    template's own bread has `trigger_type` and `effects` duplicated onto the
    edge — and getting it wrong makes the assertion below vacuous rather than
    failing, which is why this is spelled out.

    The route layer does the same in `_spawn_library_item_node`; the test does
    it directly so the assertion is about the *data*, not the placement helper.
    """
    from graph import Edge
    node = world.graph.get_node(f"item_sample_{item_id}")
    assert node is not None, "the sample node was replaced by an id collision"
    for i, trigger in enumerate(entry.get("triggers") or []):
        tid = f"trigger_sample_{item_id}_{i}"
        world.graph.add_node(Node(id=tid, type="logic_trigger",
                                  name=f"{trigger.get('trigger_type')} {i}",
                                  properties=dict(trigger)))
        world.graph.add_edge(Edge(source=node.id, target=tid, type="triggers",
                                  properties=dict(trigger)))


def test_every_sampled_library_food_feeds_the_player():
    for item_id in FOOD:
        world, player, node, name = _world_with_item(item_id)
        _wire_triggers(world, item_id, _library(item_id))
        player.vitals["Hunger"] = 80
        world.eat_item(name)
        assert player.vitals["Hunger"] < 80, (
            f"eating {item_id} left Hunger at 80: the library item authors no "
            f"relieving adjust_vital, so eating it did nothing")


def test_every_sampled_library_drink_quenches_the_player():
    for item_id in DRINK:
        if item_id == "candy_jar":      # tagged food, not drink; see FOOD-adjacent set
            continue
        world, player, node, name = _world_with_item(item_id)
        _wire_triggers(world, item_id, _library(item_id))
        player.vitals["Thirst"] = 80
        world.drink_item(name)
        assert player.vitals["Thirst"] < 80, (
            f"drinking {item_id} left Thirst at 80: the library item authors no "
            f"relieving adjust_vital")


def test_bread_used_to_be_the_cosmetic_case():
    """`bread.json` shipped an `on_eat` whose only effect was a `message`. It read
    as authored, passed a casual read of the file, and did nothing. Pin the
    specific item so the example stays true."""
    entry = _library("bread")
    on_eat = [t for t in entry["triggers"]
              if "on_eat" in (t["trigger_type"] if isinstance(t["trigger_type"], list)
                              else [t["trigger_type"]])]
    assert on_eat, "bread must author an on_eat"
    relieves = [e for t in on_eat for e in (t.get("effects") or [])
                if e.get("type") == "adjust_vital"
                and str((e.get("params") or {}).get("stat", "")).lower() == "hunger"
                and float((e.get("params") or {}).get("amount", 0)) < 0]
    assert relieves, "bread's on_eat must relieve Hunger"


def test_consuming_a_library_item_still_spends_its_charge():
    """task-508 made depletion the engine's job. Authoring the restore must not
    have reintroduced a hand-written `adjust_uses` anywhere in the pass."""
    for item_id in FOOD:
        entry = _library(item_id)
        for trigger in entry.get("triggers") or []:
            for effect in trigger.get("effects") or []:
                assert str(effect.get("type")) != "adjust_uses", (
                    f"{item_id} hand-writes adjust_uses; task-508 spends the charge")


def test_no_library_consumable_authors_a_positive_drive_amount():
    """Positive amounts are legacy *satiation* semantics. Under drive semantics
    they feed the fire instead of the character — the exact failure task-424
    caught in the camp data."""
    for item_id in FOOD + DRINK:
        entry = _library(item_id)
        for trigger in entry.get("triggers") or []:
            for effect in trigger.get("effects") or []:
                if str(effect.get("type")) != "adjust_vital":
                    continue
                params = effect.get("params") or {}
                if str(params.get("stat", "")).lower() not in ("hunger", "thirst"):
                    continue
                assert float(params.get("amount", 0)) < 0, (
                    f"{item_id} adjusts {params.get('stat')} by "
                    f"+{params.get('amount')}, which starves rather than feeds")
