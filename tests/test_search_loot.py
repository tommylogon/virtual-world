"""Skill-driven search finds (task-471).

A search's yield depends on the skill used and the area: Survival finds plants
and game, History old things, Religion relics; a forest favours Survival and a
ruin favours History/Religion, and an area with no such tag yields nothing.
"""

import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from area import Area
from player import Player
from engine import foraging
from engine.background_simulation import BackgroundSimulation, TASK_MINUTES

FORAGE_TAGS = {"herb", "medicinal", "berry", "fruit", "food", "root",
               "grub", "bait", "bug"}


def _world():
    from app import create_app
    w = create_app({"TESTING": True}).world
    w.time_per_tick_minutes = 1
    return w


def _area(w, name, tags):
    w.movement.add_area(Area(name, "test area", []))
    node = w.graph.get_node(w.area_node_id(name))
    node.properties["tags"] = list(tags)
    return name


def _searcher(w, area, **skills):
    p = Player("Vekka")
    w.add_player(p)
    p.current_area = area
    w.set_player_area("Vekka", area)
    p.skills.update(skills)
    p.vitals.update({"Hunger": 0, "Thirst": 0, "Energy": 100, "Bladder": 0})
    return p


def test_survival_search_in_a_forest_finds_something():
    w = _world()
    area = _area(w, "Test Woods", ["forest"])
    p = _searcher(w, area, Survival=10)
    w.skill_check = lambda *a, **k: (True, 20, "")
    node = foraging.find_or_spawn(w, p, area, skill="survival",
                                  rng=random.Random(1))
    assert node is not None
    tags = {str(t).lower() for t in (node.properties.get("tags") or [])}
    assert tags & (FORAGE_TAGS | {"junk", "scrap", "debris", "tinder", "wood", "stone"})
    assert any(e.source == node.id and e.target == w.area_node_id(area)
               for e in w.graph.edges), "the find was not placed in the area"


def test_a_bare_success_can_turn_up_junk():
    entries = foraging._candidate_entries("survival", ("food",), strong=False)
    assert any("junk" in {str(t).lower() for t in e["tags"]} for e in entries)


def test_a_strong_result_delivers_what_was_asked_for():
    entries = foraging._candidate_entries("survival", ("food",), strong=True)
    assert entries
    assert all({"food"} & {str(t).lower() for t in e["tags"]} for e in entries)


def test_the_forage_tag_curates_the_item_pool():
    """A `tool` entry picks a findable tool, not a random fixture."""
    assert foraging._pick_item(["tool"], set(), random.Random(0)) == "dwarf_chisel"


def test_forage_curation_keeps_food_finds_edible():
    """A `food` find must be something you can actually eat.

    This used to assert membership in a hardcoded triple
    (`wild_berries`, `edible_root`, `fat_grub`), which was the entire food pool
    when it was written. The 2026-09-29 content pass took the library to 1,370
    items and the seeded pick became `plover_egg` — so the test was asserting a
    *pool* that no longer exists rather than the *property* it exists to protect.
    The property is what matters: whatever is drawn from the food pool must be
    tagged `food` **and** author a real `on_eat` that relieves Hunger downward, so
    a character who forages something is nourished and not merely holding a
    mushroom. That is the same rule `tools/lint_library.py` enforces over the
    whole library, checked here on the one item the sim actually hands a player.
    """
    from tools.lint_library import load_registry
    import os
    items = load_registry(
        os.path.join(str(Path(__file__).resolve().parent.parent),
                     "data", "library"),
        "items")
    picked = foraging._pick_item(["food"], set(), random.Random(0))
    assert picked, "a food entry drew nothing from the food pool"

    record = items.get(picked)
    assert record is not None, f"{picked!r} was drawn but is not in the library"
    tags = {str(t).lower() for t in (record.get("tags") or [])}
    assert "food" in tags, f"{picked!r} was drawn as a food find but is not tagged food"

    # …and the tag is backed by an effect, which is the half that actually feeds
    # somebody. A drive fills upward, so relief is a *negative* amount.
    fed = False
    for trigger in (record.get("triggers") or []):
        if not isinstance(trigger, dict):
            continue
        raw = trigger.get("trigger_type")
        types = raw if isinstance(raw, list) else [raw]
        if "on_eat" not in [str(t) for t in types]:
            continue
        for effect in (trigger.get("effects") or []):
            params = (effect or {}).get("params") or {}
            if (effect or {}).get("type") == "adjust_vital" \
                    and str(params.get("stat", "")).lower() == "hunger":
                try:
                    fed = float(params.get("amount")) < 0
                except (TypeError, ValueError):
                    fed = False
    assert fed, (f"{picked!r} is tagged food but authors no on_eat that relieves "
                 f"Hunger, so foraging it would leave a character starving")


def test_an_untagged_interior_yields_nothing():
    w = _world()
    area = _area(w, "Test Hall", [])
    p = _searcher(w, area, Survival=10)
    w.skill_check = lambda *a, **k: (True, 20, "")
    assert foraging.find_or_spawn(w, p, area, skill="survival") is None


def test_a_failed_check_finds_nothing():
    w = _world()
    area = _area(w, "Test Woods", ["forest"])
    p = _searcher(w, area, Survival=10)
    w.skill_check = lambda *a, **k: (False, 0, "")
    assert foraging.find_or_spawn(w, p, area, skill="survival") is None


def test_the_area_cap_stops_a_loot_pinata():
    w = _world()
    area = _area(w, "Test Woods", ["forest"])
    p = _searcher(w, area, Survival=10)
    w.skill_check = lambda *a, **k: (True, 20, "")
    rng = random.Random(2)
    found = [foraging.find_or_spawn(w, p, area, skill="survival", rng=rng)
             for _ in range(foraging.MAX_FINDS_PER_AREA_PER_DAY + 2)]
    assert sum(1 for n in found if n is not None) == \
        foraging.MAX_FINDS_PER_AREA_PER_DAY


def test_religion_search_in_a_ruin_finds_a_relic():
    w = _world()
    area = _area(w, "Test Ruin", ["ruin"])
    p = _searcher(w, area, Religion=10)
    w.skill_check = lambda *a, **k: (True, 20, "")
    node = foraging.find_or_spawn(w, p, area, skill="religion",
                                  rng=random.Random(3))
    assert node is not None
    tags = {str(t).lower() for t in (node.properties.get("tags") or [])}
    assert tags & {"relic", "religious", "idol"}


def test_soak_forages_when_the_area_has_no_food():
    w = _world()
    area = _area(w, "Test Woods", ["forest"])
    p = _searcher(w, area, Survival=10)
    p.simulation_mode = "background"
    p.vitals["Hunger"] = 80
    w.skill_check = lambda *a, **k: (True, 20, "")
    # What the area holds, read from the library: the find is eaten and therefore
    # gone by the time the assertion below runs, so the relief has to be known
    # beforehand. This asserted a literal `80 - 45` — the relief of the wild
    # berries it happened to draw when the food pool was three items. The
    # 2026-09-29 content pass (1,370 items) made the draw a 12-relief root, and
    # the test broke on the *number* while the thing it protects — "the sim eats
    # what it foraged, and the engine applies that item's authored effect" — was
    # still true. So the property is asserted against the library, not a number.
    available = _food_reliefs(w, "Test Woods")
    used = BackgroundSimulation(w).take_action(p, served=set(), remaining=10.0)
    assert used == TASK_MINUTES["eat"], (
        f"did not eat the find: used={used} hunger={p.vitals['Hunger']} "
        f"activity={getattr(p, 'activity', None)} "
        f"log={list(w.game_logger.game_log)[-3:]}")
    if not available:
        return
    # Signed the way the engine writes it: a drive fills upward, so an `on_eat`
    # relieves Hunger by a *negative* amount and Hunger moves down by that much.
    moved = p.vitals["Hunger"] - 80
    assert moved in set(available.values()), (
        f"Hunger moved {moved}, which is not the relief of any edible the "
        f"library holds: {sorted(set(available.values()))}")


def _food_reliefs(world, area_name):
    """``{item_id: hunger_effect}`` for every edible the library holds for *area_name*.

    Read from the item's own `on_eat`, so an assertion built on it survives the
    library changing under it — which is the point of a content-driven world.
    """
    from tools.lint_library import load_registry
    items = load_registry(
        os.path.join(str(Path(__file__).resolve().parent.parent),
                     "data", "library"),
        "items")
    area = world.areas.get(area_name)
    out = {}
    for tag in sorted(FORAGE_TAGS | {"food"}):
        for item_id in foraging._library_items_by_tag().get(tag, []):
            record = items.get(item_id)
            if not record or "food" not in {
                    str(t).lower() for t in (record.get("tags") or [])}:
                continue
            for trigger in (record.get("triggers") or []):
                if not isinstance(trigger, dict):
                    continue
                raw = trigger.get("trigger_type")
                types = raw if isinstance(raw, list) else [raw]
                if "on_eat" not in [str(t) for t in types]:
                    continue
                for effect in (trigger.get("effects") or []):
                    params = (effect or {}).get("params") or {}
                    if (effect or {}).get("type") == "adjust_vital" \
                            and str(params.get("stat", "")).lower() == "hunger":
                        try:
                            amount = float(params.get("amount"))
                        except (TypeError, ValueError):
                            continue
                        if amount < 0:
                            out[item_id] = amount
    return out

    # The find's own authored relief, read back from the item that was eaten — not
    # a literal. This asserted `80 - 45`, which was the relief of the wild berries
    # it happened to draw when the food pool was three items; the 2026-09-29
    # content pass (1,370 items) made the draw a 12-relief root instead, and the
    # test broke on the *number* while the thing it protects — "the sim eats what it
    # foraged, and the engine applies that item's authored effect" — was still true.
    found = _eaten_find(w, "Test Woods")
    assert found is not None, "the find was eaten but nothing food-like is in the area"
    item_id, relief = found
    assert relief < 0, (
        f"{item_id!r} was eaten as a meal but authors no negative Hunger effect")
    assert p.vitals["Hunger"] == 80 + relief, (
        f"ate {item_id!r}, which relieves {relief}, but Hunger moved "
        f"{p.vitals['Hunger'] - 80}")


def _eaten_find(world, area_name):
    """``(item_id, hunger_effect)`` for the food in *area_name*, or ``None``.

    Reads the item's own `on_eat` effect rather than a constant, so the assertion
    survives the library changing under it — which is the whole point of a
    content-driven world.
    """
    from tools.lint_library import load_registry
    import os
    items = load_registry(
        os.path.join(str(Path(__file__).resolve().parent.parent),
                     "data", "library"),
        "items")
    area = world.areas.get(area_name)
    if area is None:
        return None
    for node in getattr(area, "items", []) or []:
        item_id = str(getattr(node, "id", "") or "")
        record = items.get(item_id)
        if not record:
            continue
        for trigger in (record.get("triggers") or []):
            if not isinstance(trigger, dict):
                continue
            raw = trigger.get("trigger_type")
            types = raw if isinstance(raw, list) else [raw]
            if "on_eat" not in [str(t) for t in types]:
                continue
            for effect in (trigger.get("effects") or []):
                params = (effect or {}).get("params") or {}
                if (effect or {}).get("type") == "adjust_vital" \
                        and str(params.get("stat", "")).lower() == "hunger":
                    try:
                        return item_id, float(params.get("amount"))
                    except (TypeError, ValueError):
                        continue
    return None
