"""Tests for the ConditionsSystem: apply, remove, tick, and backward-compatible state."""
import pytest
from player import Player, CONDITION_DEFINITIONS, CONDITION_HIERARCHY, BLOCKING_CONDITIONS, PERIODIC_CONDITIONS, CONDITION_EXCLUSIONS, CONDITION_DEFAULT_TIMERS
from graph import Node, Edge, EDGE_CARRYING, EDGE_EQUIPPED, EDGE_IN


class FakeConditionsSystem:
    """Duck-typed ConditionsSystem for player-level tests."""
    def __init__(self):
        self._conditions = {}

    def apply_condition(self, player_name, condition, duration=None):
        self._conditions.setdefault(player_name, set()).add(condition)

    def remove_condition(self, player_name, condition):
        s = self._conditions.get(player_name)
        if s:
            s.discard(condition)


class TestPlayerConditions:
    """Player-level condition methods."""

    def test_initial_conditions_awake(self):
        p = Player()
        assert "awake" in p.conditions

    def test_state_property_backward_compat(self):
        p = Player()
        assert p.state == "awake"

    def test_add_condition(self):
        p = Player()
        p.add_condition("poisoned")
        assert "poisoned" in p.conditions

    def test_remove_condition(self):
        p = Player()
        p.add_condition("poisoned")
        p.remove_condition("poisoned")
        assert "poisoned" not in p.conditions

    def test_remove_last_condition_adds_awake(self):
        p = Player()
        p.conditions.clear()
        p.remove_condition("dead")
        assert "awake" in p.conditions

    def test_has_condition(self):
        p = Player()
        assert p.has_condition("awake") is True
        assert p.has_condition("dead") is False

    def test_sleeping_removes_awake(self):
        # sleeping is gone from the catalog — sleep is an activity applying
        # unconscious (covered in test_activities); unconscious excludes awake.
        p = Player()
        p.add_condition("unconscious")
        assert "awake" not in p.conditions
        assert "unconscious" in p.conditions

    def test_unconscious_removes_awake(self):
        p = Player()
        p.add_condition("unconscious")
        assert "awake" not in p.conditions

    def test_state_setter_adds_without_wiping(self):
        p = Player()
        p.add_condition("poisoned")
        p.state = "unconscious"
        assert p.has_condition("unconscious")
        assert p.has_condition("poisoned")  # wake/energy-collapse no longer clears others

    def test_state_property_hierarchy(self):
        p = Player()
        p.add_condition("poisoned")
        p.add_condition("paralysed")
        # paralysed comes before poisoned in hierarchy
        assert p.state == "paralysed"

    def test_state_property_hierarchy_dead_wins(self):
        p = Player()
        p.add_condition("poisoned")
        p.add_condition("dead")
        assert p.state == "dead"

    def test_condition_exclusions(self):
        p = Player()
        p.add_condition("unconscious")
        p.add_condition("awake")
        assert not p.has_condition("unconscious")
        assert p.has_condition("awake")

    def test_multiple_conditions_coexist(self):
        p = Player()
        p.add_condition("awake")
        p.add_condition("poisoned")
        p.add_condition("blind")
        assert set(p.conditions) == {"awake", "poisoned", "blind"}

    def test_to_dict_includes_conditions(self):
        p = Player()
        p.add_condition("poisoned")
        d = p.to_dict()
        assert "poisoned" in d.get("conditions", [])

    def test_to_dict_includes_traits(self):
        p = Player()
        p.traits = {"dark_vision": True}
        d = p.to_dict()
        assert d.get("traits") == {"dark_vision": True}

    def test_to_dict_includes_tags(self):
        p = Player()
        p.tags = ["vampire"]
        d = p.to_dict()
        assert "vampire" in d.get("tags", [])

    def test_tags_default_empty_list(self):
        p = Player()
        assert p.tags == []

    def test_to_dict_includes_interest_tags(self):
        p = Player()
        p.interest_tags = ["magic", "documents"]
        d = p.to_dict()
        assert d.get("interest_tags") == ["magic", "documents"]

    def test_interest_tags_default_empty_list(self):
        p = Player()
        assert p.interest_tags == []


class TestConditionHierarchy:
    """CONDITION_HIERARCHY ordering."""

    def test_dead_is_first(self):
        assert CONDITION_HIERARCHY[0] == "dead"

    def test_awake_is_last(self):
        assert CONDITION_HIERARCHY[-1] == "awake"

    def test_all_conditions_in_hierarchy(self):
        expected = {"dead", "unconscious", "paralysed", "stunned",
                    "grappled", "restrained", "prone", "busy", "exhausted",
                    "sick", "poisoned",
                    "wet", "injured", "bleeding", "hypothermia",
                    "suffocating", "petrified",
                    "blind", "deaf",
                    "frightened", "charmed", "awake"}
        assert set(CONDITION_HIERARCHY) == expected


class TestBlockingConditions:
    """BLOCKING_CONDITIONS prevent acting."""

    def test_dead_blocks(self):
        assert "dead" in BLOCKING_CONDITIONS

    def test_awake_not_blocking(self):
        assert "awake" not in BLOCKING_CONDITIONS

    def test_all_blocking_conditions(self):
        expected = {"dead", "unconscious", "paralysed", "stunned", "grappled",
                    "restrained", "suffocating", "petrified"}
        assert BLOCKING_CONDITIONS == expected


class TestPeriodicConditions:
    """PERIODIC_CONDITIONS with tick effects."""

    def test_poisoned_damages_hp(self):
        assert PERIODIC_CONDITIONS["poisoned"].get("HP") == -5

    def test_sick_affects_hunger(self):
        # drives (task-337): sickness RAISES hunger/thirst
        assert PERIODIC_CONDITIONS["sick"].get("Hunger") == 2

    def test_exhausted_drains_energy(self):
        assert PERIODIC_CONDITIONS["exhausted"].get("Energy") == -3

    def test_all_periodic_have_effects(self):
        for cond, effects in PERIODIC_CONDITIONS.items():
            assert len(effects) > 0, f"{cond} has no effects"


class TestConditionExclusions:
    """CONDITION_EXCLUSIONS mapping."""

    def test_awake_excludes_unconscious(self):
        assert "unconscious" in CONDITION_EXCLUSIONS["awake"]

    def test_unconscious_excludes_awake(self):
        assert "awake" in CONDITION_EXCLUSIONS["unconscious"]

    def test_dead_excludes_everything(self):
        assert CONDITION_EXCLUSIONS["dead"] == set()


class TestConditionTimers:
    """CONDITION_DEFAULT_TIMERS."""

    def test_poisoned_timer(self):
        assert CONDITION_DEFAULT_TIMERS["poisoned"] == 10

    def test_blind_timer(self):
        assert CONDITION_DEFAULT_TIMERS["blind"] == 5


class TestConditionInstances:
    """Per-condition instance metadata (multi-instance storage, follow-up)."""

    def test_instance_duration_stored(self):
        p = Player()
        p.add_condition("poisoned", duration=10)
        assert p.conditions["poisoned"][0]["duration"] == 10

    def test_instance_source_and_level(self):
        p = Player()
        p.add_condition("frightened", duration=3, source="Butcher", level=1)
        inst = p.conditions["frightened"][0]
        assert inst["source"] == "Butcher"
        assert inst["level"] == 1

    def test_reapply_accumulate_appends_instances(self):
        p = Player()
        p.add_condition("poisoned", duration=8, source="viper")
        p.add_condition("poisoned", duration=4, source="rat")
        assert len(p.conditions["poisoned"]) == 2

    def test_reapply_refresh_extends_duration(self):
        p = Player()
        p.add_condition("stunned", duration=3)
        p.add_condition("stunned", duration=5)
        assert len(p.conditions["stunned"]) == 1
        assert p.conditions["stunned"][0]["duration"] == 5

    def test_reapply_noop_does_nothing(self):
        p = Player()
        p.add_condition("grappled", source="Mira")
        p.add_condition("grappled", source="Bob")
        assert len(p.conditions["grappled"]) == 1
        assert p.conditions["grappled"][0]["source"] == "Mira"

    def test_exhausted_reapply_bumps_level(self):
        p = Player()
        p.add_condition("exhausted", duration=5)
        assert p.conditions["exhausted"][0]["level"] == 1
        p.add_condition("exhausted", duration=5)
        assert p.conditions["exhausted"][0]["level"] == 2

    def test_extra_conditions_apply_as_separate_instances(self):
        p = Player()
        p.add_condition(
            "poisoned", duration=60,
            extra_conditions=[{"condition": "blind", "duration": 3},
                              {"condition": "paralysed", "duration": 2}],
        )
        assert p.has_condition("poisoned")
        assert p.conditions["blind"][0]["duration"] == 3
        assert p.conditions["paralysed"][0]["duration"] == 2

    def test_condition_definitions_catalog(self):
        assert "mute" in CONDITION_DEFINITIONS
        assert CONDITION_DEFINITIONS["mute"]["blocks_speech"] is True
        assert CONDITION_DEFINITIONS["blind"]["auto_fail_checks"] == ["sight"]
        assert CONDITION_DEFINITIONS["paralysed"]["auto_fail_saves"] == ["STR", "DEX"]

    def test_mute_is_not_a_state(self):
        p = Player()
        p.add_condition("mute")
        assert p.has_condition("mute")
        assert p.state == "awake"

    def test_can_speak_false_when_mute(self):
        from engine.conditions import ConditionsSystem

        class FakePM:
            players = {}

        pm = FakePM()
        p = Player()
        pm.players["Alice"] = p
        p.add_condition("mute")
        cs = ConditionsSystem(pm, None)
        assert cs.can_speak("Alice") is False
        p.remove_condition("mute")
        assert cs.can_speak("Alice") is True

    def test_load_conditions_legacy_list(self):
        p = Player()
        p.load_conditions(["awake", "poisoned", "blind"])
        assert set(p.conditions) == {"awake", "poisoned", "blind"}
        # legacy lists get default timers so timed conditions still expire
        assert p.conditions["poisoned"][0]["duration"] == 10

    def test_load_conditions_dict(self):
        p = Player()
        p.load_conditions({
            "awake": {"duration": None, "source": None, "level": 0},
            "poisoned": [{"duration": 7, "source": "viper", "level": 1}],
        })
        assert p.conditions["poisoned"][0]["duration"] == 7
        assert p.conditions["poisoned"][0]["source"] == "viper"

    def test_state_timer_compat_property(self):
        p = Player()
        p.state = "unconscious"
        p.state_timer = 5
        assert p.conditions["unconscious"][0]["duration"] == 5
        assert p.state_timer == 5

    def test_process_tick_expires_independently(self):
        from engine.conditions import ConditionsSystem

        class FakePM:
            players = {}

        pm = FakePM()
        p = Player()
        pm.players["Alice"] = p
        p.add_condition("poisoned", duration=2)
        p.add_condition("blind", duration=1)
        cs = ConditionsSystem(pm, None)
        cs.process_tick()
        # blind expired, poisoned still ticking down
        assert not p.has_condition("blind")
        assert p.has_condition("poisoned")
        assert p.conditions["poisoned"][0]["duration"] == 1

    def test_process_tick_does_not_expire_unconscious(self):
        from engine.conditions import ConditionsSystem

        class FakePM:
            players = {}

        pm = FakePM()
        p = Player()
        pm.players["Alice"] = p
        p.state = "unconscious"
        p.state_timer = 1
        cs = ConditionsSystem(pm, None)
        cs.process_tick()
        # engine-managed: tick_manager owns the wake, not process_tick
        assert p.has_condition("unconscious")

    def test_process_tick_sums_stacked_drains(self):
        from engine.conditions import ConditionsSystem

        class FakePM:
            players = {}

        pm = FakePM()
        p = Player()
        pm.players["Alice"] = p
        p.vitals["HP"] = 100
        p.add_condition("poisoned", duration=8, periodic={"HP": -5})   # viper
        p.add_condition("poisoned", duration=8, periodic={"HP": -2})   # rat
        cs = ConditionsSystem(pm, None)
        cs.process_tick()
        assert p.vitals["HP"] == 100 - 7  # drains sum across instances

    def test_end_instances_resolves_per_instance(self):
        p = Player()
        p.add_condition("prone", duration=None, source="broken_leg", ends_on=["fix"])
        p.add_condition("blind", duration=3)
        removed = p.end_instances("fix")
        assert removed == [("prone", "broken_leg")]
        assert not p.has_condition("prone")
        assert p.has_condition("blind")  # unrelated conditions untouched

    def test_end_instances_catalog_default(self):
        p = Player()
        p.add_condition("prone", duration=2, source="tackle")  # catalog ends_on: [stand]
        assert p.end_instances("stand") == [("prone", "tackle")]
        assert not p.has_condition("prone")

    def test_sleep_instance_gate_override(self):
        from engine.conditions import ConditionsSystem

        class FakePM:
            players = {}

        pm = FakePM()
        p = Player()
        pm.players["Alice"] = p
        p.add_condition(
            "unconscious", duration=None, source="sleep",
            ends_on=["wake", "damage", "loud_noise", "energy_full"],
            overrides={"blocks_speech": False},
        )
        cs = ConditionsSystem(pm, None)
        # asleep: can't act, but CAN mumble (gate override)
        assert not cs.can_act("Alice")
        assert cs.can_speak("Alice") is True


class TestConditionMods:
    """Catalog attack/defense mods (Phase 1 wiring)."""

    def test_get_condition_mods_aggregates(self):
        from engine.conditions import get_condition_mods
        p = Player()
        p.add_condition("restrained")  # attack -2, defense -2 (helpless)
        mods = get_condition_mods(p)
        assert mods["attack_mod"] == -2
        assert mods["defense_mod"] == -2

    def test_auto_fails_saves(self):
        from engine.conditions import auto_fails_saves
        p = Player()
        p.add_condition("paralysed")
        assert auto_fails_saves(p, "STR") is True
        assert auto_fails_saves(p, "DEX") is True
        assert auto_fails_saves(p, "INT") is False

    def test_auto_fails_checks(self):
        from engine.conditions import auto_fails_checks
        p = Player()
        p.add_condition("blind")
        assert auto_fails_checks(p, "sight") is True
        assert auto_fails_checks(p, "hearing") is False


class TestConditionPerception:
    """Symptom-gated agent perception (owner 2026-08-07)."""

    def test_symptom_early_poison(self):
        from engine.conditions import symptom_for
        p = Player()
        p.add_condition("poisoned", duration=8)
        inst = p.conditions["poisoned"][0]
        # highest threshold reached: 6 -> mild line
        assert symptom_for("poisoned", inst) == "A queasy twist in your stomach."

    def test_symptom_escalates_as_duration_drops(self):
        from engine.conditions import symptom_for
        p = Player()
        p.add_condition("poisoned", duration=2)
        inst = p.conditions["poisoned"][0]
        assert symptom_for("poisoned", inst) == "Everything spins. Your limbs feel wrong."

    def test_symptom_none_for_known_conditions(self):
        from engine.conditions import symptom_for
        p = Player()
        p.add_condition("blind", duration=3)
        assert symptom_for("blind", p.conditions["blind"][0]) is None

    def test_hidden_vs_known(self):
        from engine.conditions import effective_known
        p = Player()
        p.add_condition("poisoned")
        p.add_condition("grappled")
        assert effective_known("poisoned", p.conditions["poisoned"][0]) is False
        assert effective_known("grappled", p.conditions["grappled"][0]) is True

    def test_instance_override_symptoms(self):
        from engine.conditions import symptom_for
        p = Player()
        p.add_condition("poisoned", duration=6,
                        symptoms={5: "A sharp cold spreads from the wound.", 1: "Your vision doubles."})
        inst = p.conditions["poisoned"][0]
        assert symptom_for("poisoned", inst) == "A sharp cold spreads from the wound."

    def test_perceived_conditions_hides_ids(self):
        from engine.conditions import perceived_conditions
        p = Player()
        p.add_condition("poisoned", duration=8, source="viper",
                        symptoms={6: "A queasy twist in your stomach."})
        p.add_condition("blind", duration=3)
        p.add_condition("grappled", source="Mira")  # excluded — dedicated prompt nudge
        lines = perceived_conditions(p)
        assert "poisoned" not in lines  # raw ids never exposed
        assert "A queasy twist in your stomach." in lines
        assert any("Can't see" in line for line in lines)

    def test_perceived_conditions_sleep_description(self):
        from engine.conditions import perceived_conditions
        p = Player()
        p.add_condition("unconscious", duration=None, source="sleep",
                        overrides={"blocks_speech": False,
                                   "description": "You are asleep. You can't act until you wake."})
        assert perceived_conditions(p) == ["You are asleep. You can't act until you wake. (from sleep)"]

    def test_perceived_conditions_frightened_names_source(self):
        from engine.conditions import perceived_conditions
        p = Player()
        p.add_condition("frightened", duration=3, source="fleshy orifice", source_type="way")
        assert perceived_conditions(p) == ["Terrified of fleshy orifice."]


class TestExhaustionLevels:
    """Exhaustion scales with the instance level (D&D 1–6, inspiration not law)."""

    def test_level_scales_drain_and_speed(self):
        from engine.conditions import effective_periodic_for, effective_speed_mult
        p = Player()
        p.add_condition("exhausted", duration=5)   # first apply = level 1
        inst = p.conditions["exhausted"][0]
        assert inst["level"] == 1
        assert effective_periodic_for("exhausted", inst) == {"Energy": -1}
        assert effective_speed_mult("exhausted", p.conditions["exhausted"]) == 0.5
        p.add_condition("exhausted", duration=5)   # re-exhaustion bumps to 2
        assert p.conditions["exhausted"][0]["level"] == 2
        assert effective_periodic_for("exhausted", p.conditions["exhausted"][0]) == {"Energy": -2}
        p.add_condition("exhausted", duration=5)   # level 3
        assert p.conditions["exhausted"][0]["level"] == 3
        assert effective_speed_mult("exhausted", p.conditions["exhausted"]) == 0.25

    def test_process_tick_drains_level_3_energy(self):
        from engine.conditions import ConditionsSystem

        class FakePM:
            players = {}

        pm = FakePM()
        p = Player()
        pm.players["Alice"] = p
        p.vitals["Energy"] = 100
        p.add_condition("exhausted", duration=5)
        p.add_condition("exhausted", duration=5)
        p.add_condition("exhausted", duration=5)   # level 3
        ConditionsSystem(pm, None).process_tick()
        assert p.vitals["Energy"] == 100 - 3


class TestDropHeldItems:
    """drops_held_items — unconscious/dead characters let go of what they hold."""

    def test_unconscious_drops_hand_items(self):
        from virtual_world_engine import VirtualWorld
        from area import Area
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        pname = world.active_player
        world.name_matcher._set_player_area(pname, "Room A")
        p = world.player_manager.get_player(pname)
        item = Node(id="item_stick", type="item", name="Stick",
                    properties={"name": "Stick", "actions": ["examine", "take"], "weight": 0.5})
        world.graph.add_node(item)
        player_id = world._player_node_id(pname)
        world.graph.add_edge(Edge(source=item.id, target=player_id, type=EDGE_CARRYING))
        world.graph.add_edge(Edge(source=item.id, target=player_id, type=EDGE_EQUIPPED,
                                  properties={"slot": "hand_left"}))
        p.equipped["hand_left"].append(item.id)

        world.conditions.apply_condition(pname, "unconscious", duration=5)

        area_id = world._get_current_area_id()
        in_area = {e.source for e in world.graph.get_edges_for_target(area_id, EDGE_IN)}
        assert item.id in in_area
        assert p.equipped["hand_left"] == []
        assert not world.graph.get_edges_for_target(player_id, EDGE_EQUIPPED)


class TestEmotionSystem:
    """Player emotion methods."""

    def test_default_emotion_neutral(self):
        p = Player()
        assert p.emotion == "neutral"

    def test_set_emotion(self):
        p = Player()
        p.set_emotion("happy", 0.8)
        assert p.emotion == "happy"
        assert p.emotion_intensity == 0.8

    def test_emotion_intensity_clamped(self):
        p = Player()
        p.set_emotion("angry", 2.0)
        assert p.emotion_intensity == 1.0

    def test_invalid_emotion_raises(self):
        p = Player()
        with pytest.raises(ValueError):
            p.set_emotion("nonexistent", 0.5)

    def test_get_emotion_nl_empty_when_neutral(self):
        p = Player()
        assert p.get_emotion_nl() == ""

    def test_get_emotion_nl_when_happy(self):
        p = Player()
        p.set_emotion("happy", 0.6)
        nl = p.get_emotion_nl()
        assert "happy" in nl
