"""Tests for the TraitSystem: trait definitions, effect resolution, and per-tick processing."""
import pytest
from player import Player
from engine.traits import TraitSystem, TRAIT_DEFINITIONS


class FakePlayer:
    """Minimal duck-typed player for trait tests."""
    def __init__(self, traits=None, tags=None, vitals=None):
        self.traits = traits or {}
        self.tags = tags or []
        self.vitals = vitals or {"HP": 100, "Energy": 50, "Hunger": 80, "Thirst": 80,
                                 "Hygiene": 80, "Social": 50, "Bladder": 80,
                                 "Sanity": 80, "Entertainment": 50, "Temperature": 37.0}
        self.name = "TestPlayer"


class FakeRoomNode:
    """Duck-typed area node for tick effect tests."""
    def __init__(self, env=None, tags=None):
        self.properties = {
            "environment": env or {},
            "tags": tags or [],
        }


class TestTraitDefinitions:
    """All 23 trait definitions exist and have required fields."""

    def test_all_traits_have_name(self):
        for tid, tdef in TRAIT_DEFINITIONS.items():
            assert tdef.get("name"), f"Trait {tid} missing name"

    def test_all_traits_have_description(self):
        for tid, tdef in TRAIT_DEFINITIONS.items():
            assert tdef.get("description"), f"Trait {tid} missing description"

    def test_all_traits_have_category(self):
        for tid, tdef in TRAIT_DEFINITIONS.items():
            assert tdef.get("category") in ("physical", "mental", "social", "combat", "exploration", "custom"), \
                f"Trait {tid} has invalid category"

    def test_all_traits_have_effects(self):
        for tid, tdef in TRAIT_DEFINITIONS.items():
            effects = tdef.get("effects", {})
            grants = tdef.get("grants_conditions", [])
            save_on = tdef.get("save_on", [])
            assert len(effects) > 0 or len(grants) > 0 or len(save_on) > 0, \
                f"Trait {tid} has no effects, grants_conditions, or save_on"

    def test_specific_traits_exist(self):
        expected = {"glutton", "cleanfreak", "night_owl", "morning_person",
                    "fast_healer", "slow_healer", "one_armed", "small_bladder",
                    "big_bladder", "blind", "deaf", "introvert", "extrovert",
                    "apathetic", "allergic", "light_sleeper", "heavy_sleeper",
                    "immortal", "dark_vision", "slasher", "hardy",
                    "darkvision", "is_slasher"}
        assert expected.issubset(TRAIT_DEFINITIONS.keys())


class TestTraitSchemaV2:
    """Trait schema v2 — grants_conditions, behavior_prompt, conflicts, new keys."""

    def test_grants_conditions_sync(self):
        p = Player()
        p.traits["paranoid"] = True
        TraitSystem.sync_granted_conditions(p)
        assert p.has_condition("frightened")
        assert p.conditions["frightened"][0]["source"] == "trait:paranoid"

    def test_grants_conditions_removed_with_trait(self):
        p = Player()
        p.traits["paranoid"] = True
        TraitSystem.sync_granted_conditions(p)
        p.traits.pop("paranoid")
        TraitSystem.sync_granted_conditions(p)
        assert not p.has_condition("frightened")

    def test_grants_conditions_with_params(self):
        p = Player()
        p.traits["chronically_ill"] = True
        TraitSystem.sync_granted_conditions(p)
        inst = p.conditions["sick"][0]
        assert inst["periodic"] == {"Hunger": -1, "Thirst": -1}
        assert inst["source"] == "trait:chronically_ill"

    def test_blind_trait_grants_blind_condition(self):
        p = Player()
        p.traits["blind"] = True
        TraitSystem.sync_granted_conditions(p)
        assert p.has_condition("blind")
        assert p.conditions["blind"][0]["source"] == "trait:blind"

    def test_conflicting_traits(self):
        p = Player()
        p.traits["night_owl"] = True
        assert TraitSystem.conflicting_traits(p, "morning_person") == ["night_owl"]
        assert TraitSystem.conflicting_traits(p, "night_owl") == []

    def test_skill_check_mods_merge(self):
        p = Player()
        p.traits["sharp_eyed"] = True   # Perception +2
        p.traits["jittery"] = True      # all skills -1
        mods = TraitSystem.get_skill_check_mods(p)
        assert mods["Perception"] == 2
        assert mods["*"] == -1  # flat mod applies to every skill at roll time

    def test_save_bonus_per_stat(self):
        p = Player()
        p.traits["iron_will"] = True
        flat, per = TraitSystem.get_save_bonus(p)
        assert flat == 0 and per == {"WIS": 2}

    def test_move_cost_and_carry_mods(self):
        p = Player()
        p.traits["sprinter"] = True
        p.traits["strong_backed"] = True
        assert TraitSystem.get_move_cost_mods(p) == {"energy": -1}
        assert TraitSystem.get_carry_capacity_mod(p) == 2.0

    def test_behavior_prompt_defined(self):
        assert "trust no one" in TRAIT_DEFINITIONS["paranoid"]["behavior_prompt"].lower()


class TestTraitWiring:
    """Phase 2 keys actually wired into engine paths."""

    def test_move_cost_mod_reduces_energy(self):
        from virtual_world_engine import VirtualWorld
        world = VirtualWorld()
        p = world.player_manager.get_player(world.active_player)
        p.vitals["Energy"] = 50
        p.traits["sprinter"] = True
        world.apply_action("move", {"energy": 2, "time": 0}, player=p)
        assert p.vitals["Energy"] == 49  # 2 - 1 (sprinter), floor 0

    def test_carry_capacity_blocks_heavy_take(self):
        from virtual_world_engine import VirtualWorld
        from area import Area
        from graph import Node, Edge, EDGE_IN
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        pname = world.active_player
        world.name_matcher._set_player_area(pname, "Room A")
        heavy = Node(id="item_boulder", type="item", name="Boulder",
                     properties={"name": "Boulder", "actions": ["take"], "weight": 150.0})
        world.graph.add_node(heavy)
        area_id = world._get_current_area_id()
        world.graph.add_edge(Edge(source=heavy.id, target=area_id, type=EDGE_IN))
        with pytest.raises(ValueError, match="carrying capacity"):
            world.item_actions.take_item(world, "Boulder")

    def test_carry_capacity_boosted_by_trait(self):
        from virtual_world_engine import VirtualWorld
        from area import Area
        from graph import Node, Edge, EDGE_IN
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        pname = world.active_player
        world.name_matcher._set_player_area(pname, "Room A")
        p = world.player_manager.get_player(pname)
        p.traits["strong_backed"] = True  # capacity 200
        heavy = Node(id="item_boulder", type="item", name="Boulder",
                     properties={"name": "Boulder", "actions": ["take"], "weight": 150.0})
        world.graph.add_node(heavy)
        area_id = world._get_current_area_id()
        world.graph.add_edge(Edge(source=heavy.id, target=area_id, type=EDGE_IN))
        result = world.item_actions.take_item(world, "Boulder")
        assert "pick up" in result.lower()


class TestAcquiredTraits:
    """Phase 4 — scripted acquisitions + serialization of dynamic traits."""

    def test_near_death_grants_scarred(self):
        p = Player()
        p.vitals["HP"] = 5
        p.vitals["Max_HP"] = 100
        assert TraitSystem.check_scripted_acquisitions(p) == ["scarred"]
        assert p.traits.get("scarred") is True

    def test_near_death_requires_survival(self):
        p = Player()
        p.vitals["HP"] = 0
        assert TraitSystem.check_scripted_acquisitions(p) == []
        assert "scarred" not in p.traits

    def test_starvation_grants_frail(self):
        p = Player()
        p.vitals["Hunger"] = 100  # drive: maxed out = starving (task-337)
        assert TraitSystem.check_scripted_acquisitions(p) == ["frail"]
        assert p.traits.get("frail") is True

    def test_confinement_grants_claustrophobic(self):
        p = Player()
        for _ in range(5):
            p.add_condition("restrained")
            TraitSystem.check_scripted_acquisitions(p)
        assert p.traits.get("claustrophobic") is True

    def test_confinement_resets_when_free(self):
        p = Player()
        p.add_condition("restrained")
        TraitSystem.check_scripted_acquisitions(p)
        p.remove_condition("restrained")
        TraitSystem.check_scripted_acquisitions(p)   # counter resets
        p.add_condition("restrained")
        TraitSystem.check_scripted_acquisitions(p)   # back to 1 tick
        assert "claustrophobic" not in p.traits

    def test_acquired_traits_serialize_roundtrip(self):
        from virtual_world_engine import VirtualWorld
        world = VirtualWorld()
        pname = world.active_player
        p = world.player_manager.get_player(pname)
        p.traits["scarred"] = True
        p.traits["frail"] = True
        data = world.to_scenario_dict()
        world2 = VirtualWorld()
        world2.load_from_dict(data)
        reloaded = world2.player_manager.get_player(pname)
        assert reloaded.traits.get("scarred") is True
        assert reloaded.traits.get("frail") is True


class TestHasTrait:
    """TraitSystem.has_trait checks."""

    def test_has_trait_returns_true(self):
        player = FakePlayer(traits={"glutton": True})
        assert TraitSystem.has_trait(player, "glutton") is True

    def test_has_trait_returns_false(self):
        player = FakePlayer(traits={})
        assert TraitSystem.has_trait(player, "glutton") is False

    def test_has_trait_missing_key(self):
        player = FakePlayer(traits={"glutton": True})
        assert TraitSystem.has_trait(player, "nonexistent") is False

    def test_has_trait_none_traits(self):
        player = FakePlayer(traits=None)
        assert TraitSystem.has_trait(player, "glutton") is False


class TestHasEffect:
    """TraitSystem.has_effect checks."""

    def test_dark_vision_from_trait(self):
        player = FakePlayer(traits={"dark_vision": True})
        assert TraitSystem.has_effect(player, "dark_vision") is True

    def test_dark_vision_from_alternate_spelling(self):
        player = FakePlayer(traits={"darkvision": True})
        assert TraitSystem.has_effect(player, "dark_vision") is True

    def test_slasher_has_dark_vision(self):
        player = FakePlayer(traits={"slasher": True})
        assert TraitSystem.has_effect(player, "dark_vision") is True
        assert TraitSystem.has_effect(player, "is_slasher") is True

    def test_no_effect_when_no_traits(self):
        player = FakePlayer(traits={})
        assert TraitSystem.has_effect(player, "dark_vision") is False

    def test_glutton_has_vital_multiplier(self):
        player = FakePlayer(traits={"glutton": True})
        assert TraitSystem.has_effect(player, "vital_multiplier") is True

    def test_hardy_has_action_cost_mod(self):
        player = FakePlayer(traits={"hardy": True})
        assert TraitSystem.has_effect(player, "action_cost_mod") is True


class TestGetActionCostMods:
    """Action cost modifier aggregation."""

    def test_hardy_reduces_energy_cost(self):
        player = FakePlayer(traits={"hardy": True})
        mods = TraitSystem.get_action_cost_mods(player)
        assert mods.get("energy") == -1

    def test_no_traits_returns_empty(self):
        player = FakePlayer(traits={})
        assert TraitSystem.get_action_cost_mods(player) == {}


class TestGetVitalMultipliers:
    """Vital multiplier aggregation."""

    def test_glutton_multiplies_hunger(self):
        player = FakePlayer(traits={"glutton": True})
        mults = TraitSystem.get_vital_multipliers(player)
        assert mults.get("Hunger") == 2.0

    def test_cleanfreak_multiplies_hygiene(self):
        player = FakePlayer(traits={"cleanfreak": True})
        mults = TraitSystem.get_vital_multipliers(player)
        assert mults.get("Hygiene") == 1.5

    def test_small_bladder_multiplies_bladder(self):
        player = FakePlayer(traits={"small_bladder": True})
        mults = TraitSystem.get_vital_multipliers(player)
        assert mults.get("Bladder") == 1.5

    def test_big_bladder_reduces_bladder(self):
        player = FakePlayer(traits={"big_bladder": True})
        mults = TraitSystem.get_vital_multipliers(player)
        assert mults.get("Bladder") == 0.5

    def test_no_traits_returns_empty(self):
        player = FakePlayer(traits={})
        assert TraitSystem.get_vital_multipliers(player) == {}

    def test_multiple_traits_merge(self):
        player = FakePlayer(traits={"glutton": True, "cleanfreak": True})
        mults = TraitSystem.get_vital_multipliers(player)
        assert mults.get("Hunger") == 2.0
        assert mults.get("Hygiene") == 1.5


class TestGetSenseBlocked:
    """Sense blocking traits."""

    def test_blind_blocks_sight(self):
        player = FakePlayer(traits={"blind": True})
        assert TraitSystem.get_sense_blocked(player) == "sight"

    def test_deaf_blocks_hearing(self):
        player = FakePlayer(traits={"deaf": True})
        assert TraitSystem.get_sense_blocked(player) == "hearing"

    def test_no_sense_block(self):
        player = FakePlayer(traits={})
        assert TraitSystem.get_sense_blocked(player) is None


class TestGetDisabledSlots:
    """Equipment slot disabling."""

    def test_one_armed_disables_hand_right(self):
        player = FakePlayer(traits={"one_armed": True})
        slots = TraitSystem.get_disabled_slots(player)
        assert "hand_right" in slots

    def test_no_disabled_slots(self):
        player = FakePlayer(traits={})
        assert TraitSystem.get_disabled_slots(player) == set()


class TestHpRegenMultiplier:
    """HP regeneration multiplier."""

    def test_fast_healer_doubles(self):
        player = FakePlayer(traits={"fast_healer": True})
        assert TraitSystem.get_hp_regen_multiplier(player) == 2.0

    def test_slow_healer_halves(self):
        player = FakePlayer(traits={"slow_healer": True})
        assert TraitSystem.get_hp_regen_multiplier(player) == 0.5

    def test_default_is_one(self):
        player = FakePlayer(traits={})
        assert TraitSystem.get_hp_regen_multiplier(player) == 1.0


class TestImmuneToCondition:
    """Condition immunity."""

    def test_immortal_immune_to_dead(self):
        player = FakePlayer(traits={"immortal": True})
        assert TraitSystem.is_immune_to_condition(player, "dead") is True

    def test_immortal_not_immune_to_poisoned(self):
        player = FakePlayer(traits={"immortal": True})
        assert TraitSystem.is_immune_to_condition(player, "poisoned") is False

    def test_no_immunity(self):
        player = FakePlayer(traits={})
        assert TraitSystem.is_immune_to_condition(player, "dead") is False


class TestGetAllergenTag:
    """Allergic trait parameter handling."""

    def test_allergic_with_string_param(self):
        player = FakePlayer(traits={"allergic": "pollen"})
        assert TraitSystem.get_allergen_tag(player) == "pollen"

    def test_allergic_with_true_param(self):
        player = FakePlayer(traits={"allergic": True})
        assert TraitSystem.get_allergen_tag(player) is True

    def test_no_allergy(self):
        player = FakePlayer(traits={})
        assert TraitSystem.get_allergen_tag(player) is None


class TestEnergyCurve:
    """Energy curve for night_owl / morning_person."""

    def test_night_owl_peak_at_22(self):
        player = FakePlayer(traits={"night_owl": True})
        curve = TraitSystem.get_energy_curve(player)
        assert curve is not None
        assert curve.get("peak_hour") == 22
        assert curve.get("off_peak_mod") == -2

    def test_morning_person_peak_at_6(self):
        player = FakePlayer(traits={"morning_person": True})
        curve = TraitSystem.get_energy_curve(player)
        assert curve is not None
        assert curve.get("peak_hour") == 6
        assert curve.get("off_peak_mod") == -2

    def test_no_energy_curve(self):
        player = FakePlayer(traits={})
        assert TraitSystem.get_energy_curve(player) is None


class TestProcessTickEffects:
    """Per-tick trait effect processing."""

    def test_allergic_reaction_in_matching_area(self):
        player = FakePlayer(traits={"allergic": "pollen"})
        area = FakeRoomNode(env={"air": "pollen"})
        logs = TraitSystem.process_tick_effects(player, tick=100, area_node=area)
        assert len(logs) == 1
        assert "Allergic reaction" in logs[0]
        assert player.vitals["HP"] == 97

    def test_allergic_no_reaction_in_clean_area(self):
        player = FakePlayer(traits={"allergic": "pollen"})
        area = FakeRoomNode(env={"air": "fresh"})
        logs = TraitSystem.process_tick_effects(player, tick=100, area_node=area)
        assert len(logs) == 0

    def test_no_allergic_without_trait(self):
        player = FakePlayer(traits={})
        area = FakeRoomNode(env={"air": "pollen"})
        logs = TraitSystem.process_tick_effects(player, tick=100, area_node=area)
        assert len(logs) == 0

    def test_night_owl_energy_drain_during_day(self):
        player = FakePlayer(traits={"night_owl": True})
        # tick=360 => hour 6 (morning, far from peak 22)
        logs = TraitSystem.process_tick_effects(player, tick=360, area_node=None)
        assert player.vitals["Energy"] == 48

    def test_night_owl_no_drain_near_peak(self):
        player = FakePlayer(traits={"night_owl": True})
        # tick=1320 => hour 22 (peak hour)
        logs = TraitSystem.process_tick_effects(player, tick=1320, area_node=None)
        assert player.vitals["Energy"] == 50

    def test_morning_person_energy_drain_at_night(self):
        player = FakePlayer(traits={"morning_person": True})
        # tick=0 => hour 0 (night, far from peak 6)
        logs = TraitSystem.process_tick_effects(player, tick=0, area_node=None)
        assert player.vitals["Energy"] == 48

    def test_no_energy_curve_tick(self):
        player = FakePlayer(traits={})
        logs = TraitSystem.process_tick_effects(player, tick=0, area_node=None)
        assert len(logs) == 0
        assert player.vitals["Energy"] == 50


class TestNoEntertainmentDecay:
    """Apathetic trait."""

    def test_apathetic_has_no_entertainment_decay(self):
        player = FakePlayer(traits={"apathetic": True})
        assert TraitSystem.has_effect(player, "no_entertainment_decay") is True

    def test_non_apathetic_has_decay(self):
        player = FakePlayer(traits={})
        assert TraitSystem.has_effect(player, "no_entertainment_decay") is False


class TestWakeThreshold:
    """Light/heavy sleeper traits."""

    def test_light_sleeper_threshold(self):
        player = FakePlayer(traits={"light_sleeper": True})
        effects = TraitSystem.get_effects(player, "wake_threshold")
        assert 3 in effects

    def test_heavy_sleeper_threshold(self):
        player = FakePlayer(traits={"heavy_sleeper": True})
        effects = TraitSystem.get_effects(player, "wake_threshold")
        assert 1 in effects

    def test_no_sleep_trait(self):
        player = FakePlayer(traits={})
        effects = TraitSystem.get_effects(player, "wake_threshold")
        assert effects == []


class TestGetDefinition:
    """Trait definition lookup."""

    def test_get_definition_returns_dict(self):
        tdef = TraitSystem.get_definition("glutton")
        assert tdef is not None
        assert tdef["name"] == "Glutton"
        assert tdef["category"] == "physical"

    def test_get_definition_unknown(self):
        assert TraitSystem.get_definition("nonexistent") is None

    def test_get_trait_param_boolean(self):
        player = FakePlayer(traits={"glutton": True})
        assert TraitSystem.get_trait_param(player, "glutton") is True

    def test_get_trait_param_string(self):
        player = FakePlayer(traits={"allergic": "pollen"})
        assert TraitSystem.get_trait_param(player, "allergic") == "pollen"


class TestGetEffects:
    """Collecting all effect values for a given effect key."""

    def test_multiple_traits_same_effect(self):
        player = FakePlayer(traits={"fast_healer": True, "slow_healer": True})
        mults = TraitSystem.get_effects(player, "hp_regen_multiplier")
        assert 2.0 in mults
        assert 0.5 in mults
