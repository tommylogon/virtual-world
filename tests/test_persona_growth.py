"""Persona growth wiring (task-829): every 828 field changes at runtime.

A static sheet is dead authoring — growth is the feature. Lenses change eye
color, scissors cut hair, a kit gives a tattoo, a leg becomes a prosthetic,
and kinks / fears / traumas / interests add AND remove, all through the
same four trigger effects, all persisting on the node's ONE block.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from area import Area
from player import Player

from engine import character_appearance as ca

AREA = "Verdant Hollow"


def _world():
    world = create_app({"TESTING": True}).world
    world.movement.add_area(Area(AREA, "A hollow.", []))
    return world


def _character(world, name="Arix"):
    player = Player(name)
    world.add_player(player)
    world.set_player_area(name, AREA)
    return player


def _node(world, name="Arix"):
    return world.graph.get_node(world._player_node_id(name))


def _fx(world, kind, params, name="Arix"):
    world.active_player = name
    return world.effects.execute(kind, params, {"actor": name},
                                 game_state=world)


class TestMutators:

    def test_set_persona_field_writes_a_dotted_path(self):
        world = _world()
        _character(world)
        node = _node(world)
        ca.set_record(node, {"appearance": {"eyes": {"color": "grey"}}})
        ca.set_persona_field(node, "appearance.eyes.color", "blue")
        assert ca.appearance(node)["eyes"]["color"] == "blue"
        assert ca.prose_is_stale(node) is True

    def test_set_persona_field_rejects_outside_sections(self):
        world = _world()
        _character(world)
        node = _node(world)
        try:
            ca.set_persona_field(node, "vitals.hp", 10)
        except ca.StructuredError:
            pass
        else:
            raise AssertionError("wrote outside the block")
        assert ca.get_record(node) == {}

    def test_set_persona_field_rejects_a_bad_value(self):
        world = _world()
        _character(world)
        node = _node(world)
        try:
            ca.set_persona_field(node, "identity.age", "old")
        except ca.StructuredError:
            pass
        else:
            raise AssertionError("bad age accepted")
        assert ca.get_record(node) == {}

    def test_add_and_remove_round_trip(self):
        world = _world()
        _character(world)
        node = _node(world)
        assert ca.add_persona_id(node, "fears", "deep-water") is True
        assert ca.add_persona_id(node, "fears", "deep-water") is False
        assert ca.personality(node)["fears"] == ["deep-water"]
        assert ca.remove_persona_id(node, "fears", "deep-water") is True
        assert ca.remove_persona_id(node, "fears", "deep-water") is False
        assert ca.personality(node).get("fears", []) == []

    def test_add_rejects_non_id_fields(self):
        world = _world()
        _character(world)
        node = _node(world)
        try:
            ca.add_persona_id(node, "traits", "Brave")
        except ca.StructuredError:
            pass
        else:
            raise AssertionError("prose field took an id add")

    def test_advance_age_bumps_authored_years(self):
        world = _world()
        _character(world)
        node = _node(world)
        ca.set_persona_field(node, "identity.age", 30)
        assert ca.advance_age(node, 5) == 35
        assert ca.identity(node)["age"] == 35


class TestEffectDispatch:

    def test_lenses_change_eye_color_through_an_effect(self):
        world = _world()
        player = _character(world)
        world.active_player = player.name
        ca.set_record(_node(world),
                      {"appearance": {"eyes": {"color": "grey"}}})
        _fx(world, "set_persona_field",
            {"path": "appearance.eyes.color", "value": "blue"})
        assert ca.appearance(_node(world))["eyes"]["color"] == "blue"

    def test_add_mirrors_fear_onto_the_player(self):
        world = _world()
        player = _character(world)
        world.active_player = player.name
        _fx(world, "add_persona_id", {"field": "fears", "id": "deep-water"})
        assert "deep-water" in ca.personality(_node(world))["fears"]
        assert "deep-water" in player.fear_tags

    def test_remove_mirrors_off_the_player(self):
        world = _world()
        player = _character(world)
        world.active_player = player.name
        _fx(world, "add_persona_id", {"field": "interests", "id": "smithing"})
        assert "smithing" in player.interest_tags
        _fx(world, "remove_persona_id",
            {"field": "interests", "id": "smithing"})
        assert "smithing" not in player.interest_tags
        assert ca.personality(_node(world)).get("interests", []) == []

    def test_set_never_drops_a_foreign_tag(self):
        world = _world()
        player = _character(world)
        world.active_player = player.name
        player.fear_tags.append("goblin")  # another source's tag
        _fx(world, "set_persona_field",
            {"path": "personality.fears", "value": ["deep-water"]})
        assert "goblin" in player.fear_tags
        assert "deep-water" in player.fear_tags

    def test_advance_age_through_an_effect(self):
        world = _world()
        player = _character(world)
        world.active_player = player.name
        ca.set_persona_field(_node(world), "identity.age", 30)
        _fx(world, "advance_age", {"years": 5})
        assert ca.identity(_node(world))["age"] == 35

    def test_unknown_effect_params_are_no_ops(self):
        world = _world()
        player = _character(world)
        world.active_player = player.name
        _fx(world, "add_persona_id", {"field": "fears", "id": ""})
        _fx(world, "set_persona_field", {"path": "", "value": "x"})
        _fx(world, "advance_age", {})
        assert ca.get_record(_node(world)) == {}


class TestGrowthCompileRoundTrip:

    def test_grow_then_compile_projects_the_change(self):
        world = _world()
        _character(world)
        node = _node(world)
        ca.set_record(node, {"appearance": {"eyes": {"color": "grey"}},
                             "personality": {"traits": ["blunt"]}})
        before = ca.compile_persona(node)["base_description"]
        assert "grey eyes" in before.lower()
        ca.set_persona_field(node, "appearance.eyes.color", "blue")
        ca.add_persona_id(node, "fears", "deep-water")
        compiled = ca.compile_persona(node)
        assert "blue eyes" in compiled["base_description"].lower()
        assert "grey eyes" not in compiled["base_description"].lower()
        assert "deep-water" in compiled["fear_tags"]

    def test_template_item_grows_through_on_use(self):
        """The library template is the content proof: use it, sheet changes.

        Item hooks carry persona effects with no extra code — a lens item
        is authoring, not engine work.
        """
        world = _world()
        player = _character(world)
        world.active_player = player.name
        ca.set_record(_node(world),
                      {"appearance": {"eyes": {"color": "grey"}}})
        node, _lib = world.effects._hydrate_item(
            "template_set_persona_field", {}, always_fresh=True)
        assert node is not None
        outs = world.triggers._execute_triggers(node, "on_use",
                                                game_state=world)
        assert any("shift colour" in o for o in outs)
        assert ca.appearance(_node(world))["eyes"]["color"] == "blue"
