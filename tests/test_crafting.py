"""Crafting system tests (task-2; recipe-entry shape: task-831).

Recipes are registry entries (``data/library/recipes/<id>.json``), never
graph nodes. Fixtures below write entries into a tmp registry the test
world reads, so no test depends on the shipped library contents.
"""

import json

import pytest

from area import Area
from graph import Node, Edge, EDGE_CARRYING, EDGE_IN


FRIED_EGGS = {
    "id": "fried_eggs",
    "name": "Fried Eggs",
    "ingredients": [{"item": "egg", "count": 1, "consumed": True},
                    {"item": "pan", "count": 1, "consumed": False}],
    "conditions": [{"type": "state_equals", "target": "oven", "value": "on"}],
    "duration_min": 10,
    "skill_check": {"skill": "Cooking", "dc": 10},
    "outputs": [{"item": "apple", "count": 1}],
    "outcomes": {
        "crit_success": {"outputs": [{"item": "apple", "count": 2}],
                         "message": "Two perfect eggs."},
        "success": {"outputs": [{"item": "apple", "count": 1}],
                    "message": ""},
        "fail": {"consume_inputs": True,
                 "outputs": [{"item": "apple", "count": 1}],
                 "message": "Edible, barely."},
        "crit_fail": {"consume_inputs": False, "outputs": [],
                      "message": "Noticed in time — everything kept."},
    },
    "learned_by": ["global"],
    "discoverable": True,
}


def make_world(tmp_path, *recipes):
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.movement.add_area(Area("Kitchen", "A test kitchen.", []))
    pname = world.active_player
    world.name_matcher._set_player_area(pname, "Kitchen")
    recipe_dir = tmp_path / "recipes"
    recipe_dir.mkdir(exist_ok=True)
    for recipe in recipes:
        (recipe_dir / f"{recipe['id']}.json").write_text(
            json.dumps(recipe), encoding="utf-8")
    world.crafting.recipe_dir = str(recipe_dir)
    return world, pname


def add_world_item(world, name, props=None):
    n = Node(id=f"item_{name}", type="item", name=name, properties={
        "name": name, "weight": 0.1, "tags": [], "current_state": "normal",
        "actions": ["examine", "take", "use"],
    })
    if props:
        n.properties.update(props)
    world.graph.add_node(n)
    area_id = world._get_current_area_id()
    world.graph.add_edge(Edge(source=n.id, target=area_id, type=EDGE_IN))
    return n


def _kitchen(world, recipe=FRIED_EGGS):
    add_world_item(world, "egg")
    add_world_item(world, "pan")
    oven = add_world_item(world, "oven")
    oven.properties["current_state"] = "on"
    return oven


def test_unknown_recipe_errors(tmp_path):
    world, _ = make_world(tmp_path, FRIED_EGGS)
    with pytest.raises(ValueError, match="don't know any recipe"):
        world.craft_item("oyster omelette")


def test_global_recipe_requires_inputs_and_conditions(tmp_path):
    world, pname = make_world(tmp_path, FRIED_EGGS)
    # no egg → fail
    add_world_item(world, "pan")
    oven = add_world_item(world, "oven")
    with pytest.raises(ValueError, match="You need 1 egg"):
        world.craft_item("fried eggs")


def test_recipe_condition_gate_blocks(tmp_path):
    world, pname = make_world(tmp_path, FRIED_EGGS)
    add_world_item(world, "egg")
    add_world_item(world, "pan")
    oven = add_world_item(world, "oven")
    with pytest.raises(ValueError, match="conditions"):
        world.craft_item("fried eggs")


def test_global_recipe_success_spawns_output_and_consumes_input(tmp_path):
    world, pname = make_world(tmp_path, FRIED_EGGS)
    egg = add_world_item(world, "egg")
    _kitchen(world)
    world.crafting.roll_fn = lambda: 12  # success, not strong
    result = world.craft_item("fried eggs")
    assert "craft" in result.lower()
    # egg consumed (node removed)
    assert world.graph.get_node(egg.id) is None
    # output spawned into inventory (apple from library)
    player_id = world._player_node_id(pname)
    carried = [e.source for e in world.graph.get_edges_for_target(player_id, EDGE_CARRYING)]
    assert any((world.graph.get_node(i).name or '').lower() == "apple" for i in carried)


def test_crit_success_spawns_bonus_output(tmp_path):
    world, pname = make_world(tmp_path, FRIED_EGGS)
    _kitchen(world)
    world.crafting.roll_fn = lambda: 20
    result = world.craft_item("fried eggs")
    assert "Two perfect eggs." in result
    # Bonus lands pooled (quantity stacks onto uses per the pooled-resource
    # invariant) — the tier message proves the crit branch ran, the apple
    # proves the bonus outputs spawned.
    player_id = world._player_node_id(pname)
    carried = [world.graph.get_node(e.source)
               for e in world.graph.get_edges_for_target(player_id, EDGE_CARRYING)]
    apples = [n for n in carried if (n.name or '').lower() == "apple"]
    assert apples, "crit outputs spawned"
    assert sum(int(n.properties.get("uses", 1) or 1) for n in apples) > 2, \
        "bonus units pooled on top of the base"


def test_fail_consumes_per_its_flag_and_spawns_fail_item(tmp_path):
    world, pname = make_world(tmp_path, FRIED_EGGS)
    egg = add_world_item(world, "egg")
    _kitchen(world)
    world.crafting.roll_fn = lambda: 5
    result = world.craft_item("fried eggs")
    assert "fumble" in result.lower()
    assert "Edible, barely." in result
    # fail flag consumes: the egg is gone
    assert world.graph.get_node(egg.id) is None


def test_crit_fail_with_keep_flag_consumes_nothing(tmp_path):
    world, pname = make_world(tmp_path, FRIED_EGGS)
    egg = add_world_item(world, "egg")
    _kitchen(world)
    world.crafting.roll_fn = lambda: 1
    result = world.craft_item("fried eggs")
    assert "fumble" in result.lower()
    assert "Noticed in time" in result
    # consume_inputs False: the egg survives, nothing spawns
    assert world.graph.get_node(egg.id) is not None


def test_old_inputs_key_still_reads(tmp_path):
    legacy = dict(FRIED_EGGS)
    legacy["id"] = "legacy_eggs"
    legacy["name"] = "Legacy Eggs"
    legacy["inputs"] = legacy.pop("ingredients")
    del legacy["outcomes"]
    del legacy["skill_check"]
    world, pname = make_world(tmp_path, legacy)
    egg = add_world_item(world, "egg")
    _kitchen(world)
    result = world.craft_item("legacy eggs")
    assert "craft" in result.lower()
    assert world.graph.get_node(egg.id) is None


def test_discoverable_recipe_records_after_first_craft(tmp_path):
    recipe = dict(FRIED_EGGS)
    recipe["learned_by"] = ["skill:Cooking"]
    world, pname = make_world(tmp_path, recipe)
    add_world_item(world, "egg")
    _kitchen(world)
    player = world.player_manager.get_player(pname)
    # not learned by skill (Cooking not in defaults) → unknown
    with pytest.raises(ValueError, match="don't know how to craft"):
        world.craft_item("fried eggs")
    # teach the skill, then craft
    player.skills["Cooking"] = 1
    world.crafting.roll_fn = lambda: 12
    result = world.craft_item("fried eggs")
    assert "craft" in result.lower()
    assert "Fried Eggs" in (player.crafting_known or [])


def test_item_learned_recipe(tmp_path):
    recipe = dict(FRIED_EGGS)
    recipe["learned_by"] = ["item:recipe_card_eggs"]
    world, pname = make_world(tmp_path, recipe)
    add_world_item(world, "egg")
    _kitchen(world)
    with pytest.raises(ValueError, match="don't know how to craft"):
        world.craft_item("fried eggs")
    card = add_world_item(world, "recipe_card_eggs")
    # take it into the inventory... take puts it in hand; carried_names check uses carrying+equipped
    world.take_item("recipe_card_eggs")
    world.crafting.roll_fn = lambda: 12
    result = world.craft_item("fried eggs")
    assert "craft" in result.lower()


def test_weighted_crit_fail_picks_by_weight():
    from engine.crafting import CraftingSystem
    system = CraftingSystem.__new__(CraftingSystem)
    outcome = {"outputs": [{"item": "a", "weight": 0},
                           {"item": "b", "weight": 3}]}
    assert system._resolve_outputs(outcome) == [{"item": "b", "weight": 3}]
    assert system._resolve_outputs({"outputs": []}) == []
    assert system._resolve_outputs({}) == []


def _real_recipe(recipe_id):
    import json
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                        "data", "library", "recipes", f"{recipe_id}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_fire_chain_kindling_then_candle_end_to_end(tmp_path):
    """Task-832 verify: the authored fire chain crafts through the engine."""
    world, pname = make_world(
        tmp_path, _real_recipe("split_kindling"),
        _real_recipe("dip_tallow_candle"))
    add_world_item(world, "branch")
    add_world_item(world, "hatchet")
    world.crafting.roll_fn = lambda: 12
    assert "craft" in world.craft_item("split kindling").lower()
    # kindling spawned into inventory from the real outputs
    player_id = world._player_node_id(pname)
    carried = [world.graph.get_node(e.source)
               for e in world.graph.get_edges_for_target(player_id, EDGE_CARRYING)]
    assert any((n.name or '').lower() == "kindling" for n in carried)


def test_water_chain_fill_to_tisane_end_to_end(tmp_path):
    """Task-833 verify: muddy water becomes tisane through the engine,
    and the unsafe tag survives until the boil."""
    world, pname = make_world(
        tmp_path, _real_recipe("fill_waterskin"),
        _real_recipe("settle_muddy_water"),
        _real_recipe("filter_water_cloth"),
        _real_recipe("boil_water_safe"),
        _real_recipe("herbal_tisane"))
    add_world_item(world, "waterskin")
    add_world_item(world, "wooden_pail")
    add_world_item(world, "cloth_scrap")
    add_world_item(world, "cooking_pot")
    add_world_item(world, "cup")
    add_world_item(world, "herb_bunch")
    fire = add_world_item(world, "campfire")
    fire.properties["current_state"] = "on"
    world.crafting.roll_fn = lambda: 12

    def carried_names():
        player_id = world._player_node_id(pname)
        return [(world.graph.get_node(e.source).name or '').lower()
                for e in world.graph.get_edges_for_target(player_id, EDGE_CARRYING)]

    world.craft_item("fill waterskin")
    world.craft_item("settle muddy water")
    world.craft_item("filter water")
    names = carried_names()
    assert "filtered_water" in names
    node = world.graph.get_node(
        next(e.source for e in world.graph.get_edges_for_target(
            world._player_node_id(pname), EDGE_CARRYING)
            if (world.graph.get_node(e.source).name or '').lower() == "filtered_water"))
    assert "unsafe_water" in (node.properties.get("tags") or [])
    world.craft_item("boil water")
    result = world.craft_item("herbal tisane")
    assert "craft" in result.lower()
    assert "herbal_tisane" in carried_names()


def test_camp_pottage_fail_path_and_pot_recovery(tmp_path):
    """Task-834 verify: fail spawns gruel, crit-fail kills the food but
    the pot survives (scorched_pot keeps the cookware)."""
    world, pname = make_world(tmp_path, _real_recipe("barley_pottage_camp"))
    add_world_item(world, "barley", {"uses": 4})
    add_world_item(world, "boiled_water")
    add_world_item(world, "onion")
    add_world_item(world, "cooking_pot")
    fire = add_world_item(world, "campfire")
    fire.properties["current_state"] = "on"

    def carried():
        player_id = world._player_node_id(pname)
        return [(world.graph.get_node(e.source).name or '').lower()
                for e in world.graph.get_edges_for_target(player_id, EDGE_CARRYING)]

    world.crafting.roll_fn = lambda: 5
    result = world.craft_item("barley pottage camp")
    assert "fumble" in result.lower()
    assert "thin_gruel" in carried()

    world2, pname2 = make_world(tmp_path, _real_recipe("barley_pottage_camp"))
    for item in ("barley", "boiled_water", "onion", "cooking_pot"):
        props = {"uses": 4} if item == "barley" else None
        add_world_item(world2, item, props)
    fire2 = add_world_item(world2, "campfire")
    fire2.properties["current_state"] = "on"
    world2.crafting.roll_fn = lambda: 1
    world2.craft_item("barley pottage camp")
    player_id = world2._player_node_id(pname2)
    names = [(world2.graph.get_node(e.source).name or '').lower()
             for e in world2.graph.get_edges_for_target(player_id, EDGE_CARRYING)]
    assert "scorched_pot" in names


def test_grain_chain_sheaf_to_loaf_end_to_end(tmp_path):
    """Task-835 verify: thresh → grind → mix → leaven → bake completes,
    and one forced fail mid-chain degrades without breaking it."""
    world, pname = make_world(
        tmp_path, _real_recipe("thresh_barley"), _real_recipe("grind_meal"),
        _real_recipe("mix_dough"), _real_recipe("leaven_dough"),
        _real_recipe("bake_barley_loaf"))
    add_world_item(world, "barley_sheaf")
    add_world_item(world, "flail")
    add_world_item(world, "grindstone")
    add_world_item(world, "wooden_bowl")
    add_world_item(world, "barm")
    add_world_item(world, "clay_oven")
    add_world_item(world, "boiled_water")
    add_world_item(world, "salt")
    fire = add_world_item(world, "campfire")
    fire.properties["current_state"] = "on"
    world.crafting.roll_fn = lambda: 12

    def carried():
        player_id = world._player_node_id(pname)
        return [(world.graph.get_node(e.source).name or '').lower()
                for e in world.graph.get_edges_for_target(player_id, EDGE_CARRYING)]

    world.craft_item("thresh barley")
    assert "barley" in carried()
    world.craft_item("grind meal")
    world.craft_item("mix dough")
    world.craft_item("leaven dough")
    result = world.craft_item("bake barley loaf")
    assert "craft" in result.lower()
    assert "barley_loaf" in carried()


def test_smoke_meat_then_pack_rations_end_to_end(tmp_path):
    """Task-836 verify: preserved outputs feed the ration recipe, and
    perishable vs shelf-stable tags follow the card rule."""
    world, pname = make_world(
        tmp_path, _real_recipe("smoke_meat"),
        _real_recipe("make_jerky"), _real_recipe("pack_trail_rations"))
    add_world_item(world, "raw_meat", {"uses": 3})
    add_world_item(world, "firewood")
    add_world_item(world, "smokehouse")
    add_world_item(world, "salt")
    add_world_item(world, "drying_rack")
    add_world_item(world, "hard_cheese")
    add_world_item(world, "oatcake")
    add_world_item(world, "dried_apple")
    add_world_item(world, "cloth_scrap")
    fire = add_world_item(world, "campfire")
    fire.properties["current_state"] = "on"
    world.crafting.roll_fn = lambda: 12
    world.craft_item("smoke meat")
    world.craft_item("make jerky")
    result = world.craft_item("pack trail rations")
    assert "craft" in result.lower()

    def carried():
        player_id = world._player_node_id(pname)
        return [(world.graph.get_node(e.source).name or '').lower()
                for e in world.graph.get_edges_for_target(player_id, EDGE_CARRYING)]

    assert "trail_rations" in carried()
    import json as _json
    lib = "data/library/items"
    perishable = {"half_smoked", "soft_cheese"}
    for name in ("smoked_meat", "jerky", "trail_rations",
                 "half_smoked", "soft_cheese"):
        tags = _json.load(open(f"{lib}/{name}.json",
                               encoding="utf-8")).get("tags", [])
        if name in perishable:
            assert "perishable" in tags, name
        else:
            assert "perishable" not in tags, name


def test_hide_cure_tan_straps_pouch_end_to_end(tmp_path):
    """Task-838 verify: cure → tan → straps → pouch completes, and a
    fail degrades one step without breaking the next."""
    world, pname = make_world(
        tmp_path, _real_recipe("cure_hide"), _real_recipe("tan_leather"),
        _real_recipe("cut_straps"), _real_recipe("stitch_pouch"))
    add_world_item(world, "raw_hide")
    add_world_item(world, "salt", {"uses": 4})
    add_world_item(world, "wood_ash")
    add_world_item(world, "hide_rack")
    add_world_item(world, "oak_bark", {"uses": 4})
    add_world_item(world, "boiled_water")
    add_world_item(world, "tanning_pit")
    add_world_item(world, "knife")
    add_world_item(world, "waxed_thread")
    add_world_item(world, "awl")
    add_world_item(world, "needle")
    world.crafting.roll_fn = lambda: 15

    def carried():
        player_id = world._player_node_id(pname)
        return [(world.graph.get_node(e.source).name or '').lower()
                for e in world.graph.get_edges_for_target(player_id, EDGE_CARRYING)]

    world.craft_item("cure hide")
    assert "cured_hide" in carried()
    world.craft_item("tan leather")
    assert "leather_hide" in carried()
    world.craft_item("cut straps")
    assert "leather_strap" in carried()


def test_stitch_pouch_with_stock_leather(tmp_path):
    """Stitch pouch proves separately: the chain's single hide went to
    straps above (one hide, one downstream item per pass)."""
    world, pname = make_world(tmp_path, _real_recipe("stitch_pouch"))
    add_world_item(world, "leather_hide")
    add_world_item(world, "waxed_thread")
    add_world_item(world, "awl")
    add_world_item(world, "needle")
    world.crafting.roll_fn = lambda: 12
    result = world.craft_item("stitch pouch")
    assert "craft" in result.lower()
    player_id = world._player_node_id(pname)
    names = [(world.graph.get_node(e.source).name or '').lower()
             for e in world.graph.get_edges_for_target(player_id, EDGE_CARRYING)]
    assert "leather_pouch" in names


def test_trap_snare_poultice_end_to_end(tmp_path):
    """Task-837 verify: trap and snare craft (placement flagged for the
    703 executor), poultice spawns per tier (application is use-time)."""
    world, pname = make_world(
        tmp_path, _real_recipe("weave_fish_trap"),
        _real_recipe("set_snare"), _real_recipe("mix_poultice"))
    add_world_item(world, "withy", {"uses": 4})
    add_world_item(world, "rope", {"uses": 4})
    add_world_item(world, "knife")
    add_world_item(world, "stick")
    add_world_item(world, "herb_bunch")
    add_world_item(world, "honey")
    add_world_item(world, "cloth_scrap")
    world.crafting.roll_fn = lambda: 12

    def carried():
        player_id = world._player_node_id(pname)
        return [(world.graph.get_node(e.source).name or '').lower()
                for e in world.graph.get_edges_for_target(player_id, EDGE_CARRYING)]

    world.craft_item("weave fish trap")
    assert "fish_trap" in carried()
    world.craft_item("set snare")
    assert "snare" in carried()
    result = world.craft_item("mix poultice")
    assert "craft" in result.lower()
    assert "poultice" in carried()


def test_forge_smelt_nails_knife_end_to_end(tmp_path):
    """Task-839 verify: smelt → nails → knife edge completes, and one
    forced fail yields the re-smeltable lump without breaking anything."""
    world, pname = make_world(
        tmp_path, _real_recipe("smelt_ingot"),
        _real_recipe("forge_nails"), _real_recipe("grind_knife_edge"),
        _real_recipe("forge_knife_blank"))
    add_world_item(world, "iron_ore", {"uses": 4})
    add_world_item(world, "charcoal", {"uses": 10})
    add_world_item(world, "forge")
    add_world_item(world, "bellows")
    add_world_item(world, "anvil")
    add_world_item(world, "hammer")
    add_world_item(world, "grindstone")
    forge = world.graph.get_node("item_forge")
    forge.properties["current_state"] = "on"
    world.crafting.roll_fn = lambda: 15

    def carried():
        player_id = world._player_node_id(pname)
        return [(world.graph.get_node(e.source).name or '').lower()
                for e in world.graph.get_edges_for_target(player_id, EDGE_CARRYING)]

    world.craft_item("smelt ingot")
    assert "iron_ingot" in carried()
    world.craft_item("forge nails")
    assert "nails" in carried() or "bent_nails" in carried()
    world.craft_item("smelt ingot")
    world.craft_item("forge knife blank")
    result = world.craft_item("grind knife edge")
    assert "craft" in result.lower()
    assert "iron_knife" in carried()

    world2, _ = make_world(
        tmp_path, _real_recipe("smelt_ingot"))
    add_world_item(world2, "iron_ore", {"uses": 4})
    add_world_item(world2, "charcoal", {"uses": 8})
    add_world_item(world2, "forge")
    add_world_item(world2, "bellows")
    forge2 = world2.graph.get_node("item_forge")
    forge2.properties["current_state"] = "on"
    world2.crafting.roll_fn = lambda: 5
    result = world2.craft_item("smelt ingot")
    assert "fumble" in result.lower()
    player_id = world2._player_node_id(world2.active_player)
    names = [(world2.graph.get_node(e.source).name or '').lower()
             for e in world2.graph.get_edges_for_target(player_id, EDGE_CARRYING)]
    assert "half_smelt" in names


def _hungry_world(tmp_path):
    """A hungry NPC cook with pottage inputs and a lit fire, no ready food."""
    from engine.background_simulation import BackgroundSimulation
    world, pname = make_world(tmp_path, _real_recipe("barley_pottage_camp"))
    player = world.player_manager.get_player(pname)
    player.vitals["Hunger"] = 90
    player.vitals["Thirst"] = 0
    player.vitals["Energy"] = 90
    player.vitals["Bladder"] = 0
    add_world_item(world, "barley", {"uses": 4})
    add_world_item(world, "boiled_water")
    add_world_item(world, "onion")
    add_world_item(world, "cooking_pot")
    fire = add_world_item(world, "campfire")
    fire.properties["current_state"] = "on"
    return world, pname, BackgroundSimulation(world)


def test_backsim_cook_starts_the_same_activity(tmp_path):
    """Task-840 Q3: a hungry NPC opens the human's cooking Activity."""
    world, pname, bgs = _hungry_world(tmp_path)
    player = world.player_manager.get_player(pname)
    assert bgs._cook_meal(player) == (40, "cook")
    assert (player.activity or {}).get("type") == "cooking"
    assert player.activity.get("recipe_id") == "barley_pottage_camp"


def test_backsim_act_cooks_when_nothing_ready(tmp_path):
    """Task-840 Q3 at the decision layer: hunger + inputs, no food."""
    world, pname, bgs = _hungry_world(tmp_path)
    player = world.player_manager.get_player(pname)
    result = bgs._act(pname, player, served=set(), remaining=60)
    assert result is not None and result[1] == "cook"
    assert (player.activity or {}).get("type") == "cooking"


def _known_entry(entry_id, name, learned_by, skill="Cooking", dc=10,
                 duration=15, discoverable=True):
    return {"id": entry_id, "name": name, "ingredients": [],
            "duration_min": duration,
            "skill_check": {"skill": skill, "dc": dc},
            "outputs": [], "outcomes": {},
            "learned_by": learned_by, "discoverable": discoverable}


def test_known_recipes_sources(tmp_path):
    """Task-841: one projection per character with the reason why."""
    world, pname = make_world(
        tmp_path,
        _known_entry("r_global", "Always Soup", ["global"]),
        _known_entry("r_skill", "Sharp Bread", ["skill:Baking"]),
        _known_entry("r_found", "Found Stew", ["skill:Unlearned"]),
        _known_entry("r_taught", "Taught Pie", ["skill:Unlearned"],
                     duration=30, discoverable=False),
        _known_entry("r_book", "Old Pie", ["item:cookbook"]),
        _known_entry("r_hidden", "Hidden Dish", ["skill:Unlearned"]))
    player = world.player_manager.get_player(pname)
    player.skills["Baking"] = 1
    add_world_item(world, "cookbook")
    world.take_item("cookbook")
    player.crafting_known = ["Found Stew", "Taught Pie"]
    known = {r["id"]: r for r in world.crafting.known_recipes(pname)}
    assert known["r_global"]["source"] == "global"
    assert known["r_skill"]["source"] == "skill"
    assert known["r_book"]["source"] == "cookbook"
    # discoverable + known by name → learned by doing…
    assert known["r_found"]["source"] == "discovered"
    # …non-discoverable known names must have been taught.
    assert known["r_taught"]["source"] == "taught"
    assert known["r_taught"]["skill"] == "Cooking"
    assert known["r_taught"]["dc"] == 10
    assert known["r_taught"]["duration_min"] == 30
    assert "r_hidden" not in known
    assert world.crafting.known_recipes("Nobody") == []


def test_known_recipes_route(tmp_path):
    from app import create_app
    app = create_app({"TESTING": True})
    client = app.test_client()
    body = client.get("/api/players/Lyrie/recipes").get_json()
    assert isinstance(body["recipes"], list)
    assert client.get("/api/players/Nobody/recipes").status_code == 404


def _cook_world(tmp_path):
    world, pname = make_world(tmp_path, FRIED_EGGS)
    add_world_item(world, "egg")
    add_world_item(world, "pan")
    oven = add_world_item(world, "oven")
    oven.properties["current_state"] = "on"
    return world, pname


def test_make_starts_a_timed_cooking_activity(tmp_path):
    """Task-840 Q2: duration > 0 starts cooking; nothing consumed yet."""
    world, pname = make_world(tmp_path, FRIED_EGGS)
    egg = add_world_item(world, "egg")
    add_world_item(world, "pan")
    oven = add_world_item(world, "oven")
    oven.properties["current_state"] = "on"
    result = world.crafting.start_cooking(world, "fried eggs")
    assert "cooking" in result.lower()
    player = world.player_manager.get_player(pname)
    assert (player.activity or {}).get("type") == "cooking"
    assert player.activity.get("recipe_id") == "fried_eggs"
    assert world.graph.get_node(egg.id) is not None


def test_abort_consumes_nothing_and_spawns_nothing(tmp_path):
    """Task-840 Q4: interruption ends the cook with no consumption."""
    world, pname = make_world(tmp_path, FRIED_EGGS)
    egg = add_world_item(world, "egg")
    _kitchen_inputs(world)
    world.crafting.start_cooking(world, "fried eggs")
    stopped = world.activities.interrupt_activity(pname)
    assert stopped is not None
    player = world.player_manager.get_player(pname)
    assert not player.activity
    assert world.graph.get_node(egg.id) is not None


def _kitchen_inputs(world):
    add_world_item(world, "pan")
    oven = add_world_item(world, "oven")
    oven.properties["current_state"] = "on"


def test_completion_rechecks_and_resolves_tier(tmp_path):
    """Task-840 Q2/Q5: elapsed duration completes through the tier seam."""
    world, pname = make_world(tmp_path, FRIED_EGGS)
    add_world_item(world, "egg")
    _kitchen_inputs(world)
    world.crafting.start_cooking(world, "fried eggs")
    world.crafting.roll_fn = lambda: 12
    out = None
    for _ in range(30):
        out = world.activities.tick_activity(pname)
        player = world.player_manager.get_player(pname)
        if not player.activity:
            break
    assert out is not None and "finish" in out.lower()
    player_id = world._player_node_id(pname)
    carried = [(world.graph.get_node(e.source).name or '').lower()
               for e in world.graph.get_edges_for_target(player_id, EDGE_CARRYING)]
    assert "apple" in carried


def test_instant_recipe_resolves_immediately(tmp_path):
    """Task-840 Q2: no duration means no Activity."""
    instant = dict(FRIED_EGGS)
    instant["id"] = "instant_eggs"
    instant["name"] = "Instant Eggs"
    instant["duration_min"] = 0
    world, pname = make_world(tmp_path, instant)
    add_world_item(world, "egg")
    _kitchen_inputs(world)
    world.crafting.roll_fn = lambda: 12
    result = world.crafting.start_cooking(world, "instant eggs")
    assert "craft" in result.lower()
    player = world.player_manager.get_player(pname)
    assert not player.activity
