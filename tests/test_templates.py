"""Template item tests (trigger-effect templates, tools/gen_effect_templates.py):

- on_use trigger wires from the library JSON and fires the effect
- the generator covers every EFFECT_TYPES entry
"""

import os
import pytest

from area import Area
from engine.triggers.constants import EFFECT_TYPES


def make_world():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.movement.add_area(Area("Kitchen", "A test kitchen.", []))
    pname = world.active_player
    world.name_matcher._set_player_area(pname, "Kitchen")
    return world, pname


def template_path(effect):
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..",
        "data", "library", "items", f"template_{effect}.json",
    )


def test_generator_covers_every_effect_type():
    for effect in EFFECT_TYPES:
        assert os.path.exists(template_path(effect)), f"missing template_{effect}.json"


def test_template_message_fires_on_use():
    world, pname = make_world()
    node, _lib = world.effects._hydrate_item("template_message", {}, always_fresh=True)
    assert node is not None
    outs = world.triggers._execute_triggers(node, "on_use", game_state=world)
    assert any("the template spoke" in o for o in outs)


def test_template_scry_fires_against_real_area():
    world, pname = make_world()
    world.movement.add_area(Area("Taco Bell", "An echoing dining room.", []))
    node, _lib = world.effects._hydrate_item("template_scry", {}, always_fresh=True)
    outs = world.triggers._execute_triggers(node, "on_use", game_state=world)
    assert any("Taco Bell" in o for o in outs)


def test_template_damage_fires():
    world, pname = make_world()
    before = world.player.vitals["HP"]
    node, _lib = world.effects._hydrate_item("template_damage", {}, always_fresh=True)
    outs = world.triggers._execute_triggers(node, "on_use", game_state=world)
    assert any("takes 1 damage" in o for o in outs)
    assert world.player.vitals["HP"] == max(0, before - 1)
