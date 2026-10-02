"""task-489 / task-215: environmental clothing — prop defaults, and wetness that
actually reaches the description.

**These two tasks contradict each other, and the disagreement is dated.** task-215
was re-scoped on 2026-09-22 with an explicit decision that the numeric `opacity`
and `friction` properties are **cancelled** and layer visibility belongs on the
item's own description. task-489 was filed the next day and asks for exactly those
properties to be added and surfaced.

That decision is not merely documented — it is **enforced by a test**:
`tests/test_equipment_system.py::test_detail_lines_carry_description_not_opacity_or_friction`
asserts `"opacity" not in joined` and `"friction" not in joined` *even when the
item authors them*. Adding them back would break a live assertion of a standing
user decision, so this file implements the part of task-489 that does not
contradict it and pins the refusal so a later reader does not "fix" it back.

What is implemented here:
- `coverage` defaults to **0.8** when absent (task-489), through one resolver.
- A soaked garment gets a `current_state`, which is task-215's own stated
  mechanism for making it read as wet.
- The state change regenerates the appearance description — the item task-215
  lists as **still open**.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import Node
from player import Player

AREA = "Blizzard Forest Clearing"


@pytest.fixture()
def world():
    from app import create_app
    return create_app({"TESTING": True}).world


def _garment(world, name="Linen Dress", item_id="item_linen_dress", **props):
    props.setdefault("equip_slots", ["torso"])
    props.setdefault("description", "Light linen, almost sheer in the sun.")
    node = Node(id=item_id, type="item", name=name, properties=dict(props))
    world.graph.add_node(node)
    return node


def _wearing(world, who, node):
    world.set_equipped_payload(who, {"torso": [node.id]})
    return node


def _soak(world, who, node=None, wet=True):
    """The real effect path, not a hand-set property.

    Uses the world's own wired `effects` object, so this goes through the same
    dispatcher a template or an item would.
    """
    world.player_manager.set_active_player(who.name)
    params = {"wet": wet}
    if node is not None:
        params["node_id"] = node.id
    return world.triggers._effects.execute(
        "set_wet", params, {}, game_state=world, item_node=node)


# ── 1. the coverage default ──────────────────────────────────────────────

def test_coverage_defaults_to_the_exposed_threshold():
    """task-489 asks for 0.8, and that is exactly
    `body_parts.COVERAGE_EXPOSED_THRESHOLD` — so an item that says nothing is
    read as a *covering* garment, the same way `is_exposed()` reads it."""
    from engine.body_parts import COVERAGE_EXPOSED_THRESHOLD
    from engine.equipment import EquipmentSystem

    node = Node(id="c1", type="item", name="Plain", properties={})
    assert EquipmentSystem.coverage_of(node) == COVERAGE_EXPOSED_THRESHOLD
    assert EquipmentSystem.coverage_of(node) == 0.8


def test_an_authored_coverage_wins():
    from engine.equipment import EquipmentSystem
    node = Node(id="c2", type="item", name="Sheer", properties={"coverage": 0.2})
    assert EquipmentSystem.coverage_of(node) == 0.2


def test_a_junk_coverage_falls_back_rather_than_propagating():
    """A garment whose coverage is "sheer" is written wrong; refusing to describe
    it helps nobody."""
    from engine.equipment import EquipmentSystem
    for junk in ("sheer", None, 5, -1):
        node = Node(id="c3", type="item", name="Odd", properties={"coverage": junk})
        assert EquipmentSystem.coverage_of(node) == 0.8, junk


def test_the_default_is_surfaced_by_the_detail_lines(world):
    node = _garment(world, "Plain Shift", "item_plain_shift")
    p = Player("Wearer")
    world.add_player(p)
    _wearing(world, p, node)

    lines = world.equipment._equipment_detail_lines(p, {})
    joined = "\n".join(lines)
    assert "coverage 0.8" in joined, joined
    assert "Plain Shift" in joined


def test_an_authored_coverage_is_still_shown_as_authored(world):
    node = _garment(world, "Sheer Wrap", "item_sheer_wrap", coverage=0.3)
    p = Player("Wearer2")
    world.add_player(p)
    _wearing(world, p, node)
    joined = "\n".join(world.equipment._equipment_detail_lines(p, {}))
    assert "coverage 0.3" in joined, joined


# ── 2. the refusal, pinned ───────────────────────────────────────────────

def test_numeric_opacity_and_friction_are_still_not_advertised(world):
    """task-215's decision, enforced. task-489 asked for these; they are refused
    because a standing user decision cancelled them and a test already asserts
    it. This test exists so a later reader does not reinstate them as a bug."""
    node = _garment(world, "Gossamer", "item_gossamer",
                    opacity=0.2, friction=3, coverage=0.4)
    p = Player("Wearer3")
    world.add_player(p)
    _wearing(world, p, node)

    joined = "\n".join(world.equipment._equipment_detail_lines(p, {}))
    assert "opacity" not in joined, joined
    assert "friction" not in joined, joined
    assert "coverage 0.4" in joined, "coverage is the one that survives"


def test_coverage_of_reads_neither_of_them(world):
    """The refusal is not only about the description line: the resolver the task
    asked for does not exist, on purpose."""
    from engine.equipment import EquipmentSystem
    assert not hasattr(EquipmentSystem, "opacity_of")
    assert not hasattr(EquipmentSystem, "friction_of")


# ── 3. wet reaches the description (task-215's still-open item) ──────────

def test_a_soaked_garment_gets_a_current_state(world):
    node = _garment(world)
    p = Player("Soaked")
    world.add_player(p)
    _wearing(world, p, node)

    _soak(world, p, node, wet=True)
    assert node.properties["wet"] is True
    assert node.properties["current_state"] == "soaked"


def test_drying_does_not_wipe_a_state_the_author_set(world):
    """A garment that was already torn reads torn, not soaked.

    `current_state` is a *single* field, so there is no room for both, and a
    soak that overwrote `"torn"` and a dry that deleted it would lose an
    authored state to a change of weather. The `wet` property is what the
    insulation penalty reads, so wetness is still visible to the engine.
    """
    node = _garment(world, "Torn Coat", "item_torn_coat", current_state="torn")
    p = Player("Weathered")
    world.add_player(p)
    _wearing(world, p, node)

    _soak(world, p, node, wet=True)
    assert node.properties["current_state"] == "torn", \
        "a soak overwrote a state the author set"
    assert node.properties["wet"] is True, "wetness still reads as a property"

    _soak(world, p, node, wet=False)
    assert node.properties["current_state"] == "torn"
    assert node.properties["wet"] is False


def test_a_garment_with_no_state_takes_the_wet_one(world):
    node = _garment(world, "Rain Coat", "item_rain_coat2")
    p = Player("Rainy")
    world.add_player(p)
    _wearing(world, p, node)
    assert "current_state" not in node.properties
    _soak(world, p, node, wet=True)
    assert node.properties["current_state"] == "soaked"

    _soak(world, p, node, wet=False)
    assert "current_state" not in node.properties, \
        "drying must remove the state the soak wrote"


def test_a_soak_with_no_node_named_soaks_everything_equipped(world):
    node = _garment(world, "Rain Coat", "item_rain_coat")
    p = Player("Caught")
    world.add_player(p)
    _wearing(world, p, node)

    _soak(world, p, None, wet=True)
    assert node.properties["wet"] is True


def test_wetness_is_readable_in_the_detail_lines(world):
    """The point of doing it through `current_state`: it reaches the prompt
    through the mechanism that already exists."""
    node = _garment(world)
    p = Player("Soaked2")
    world.add_player(p)
    _wearing(world, p, node)
    _soak(world, p, node, wet=True)

    joined = "\n".join(world.equipment._equipment_detail_lines(p, {}))
    assert "soaked" in joined, joined


# ── 4. the description regenerates ───────────────────────────────────────

def test_a_soak_regenerates_the_appearance_description(world):
    """task-215 lists this as still open: "Rain -> clothing wet -> description
    regenerates". Without it a character stays described as dry until something
    unrelated happens to rewrite the text."""
    node = _garment(world)
    p = Player("Described")
    world.add_player(p)
    _wearing(world, p, node)
    world.equipment._maybe_update_equipment_description(p)

    before = getattr(p, "description", "")
    _soak(world, p, node, wet=True)
    after = getattr(p, "description", "")
    assert after != before, (
        "the description did not change when the garment was soaked")
    assert "soaked" in after or "soak" in after, after


def test_regeneration_respects_auto_generate_descriptions(world):
    """The acceptance criterion's condition, and the one that keeps this off by
    default in a world that does not want it."""
    node = _garment(world)
    p = Player("Undescribed")
    world.add_player(p)
    _wearing(world, p, node)
    world.auto_generate_descriptions = False
    world.equipment._maybe_update_equipment_description(p)
    before = getattr(p, "description", "")

    _soak(world, p, node, wet=True)
    assert getattr(p, "description", "") == before, \
        "regenerated despite auto_generate_descriptions being off"


def test_a_soak_does_not_regenerate_for_someone_not_wearing_it(world):
    """Only the wearer changes."""
    node = _garment(world, "Someone Elses", "item_someone_elses")
    wearer = Player("Wearer4")
    bystander = Player("Bystander")
    world.add_player(wearer)
    world.add_player(bystander)
    _wearing(world, wearer, node)
    world.equipment._maybe_update_equipment_description(bystander)
    before = getattr(bystander, "description", "")

    _soak(world, wearer, node, wet=True)
    assert getattr(bystander, "description", "") == before


# ── 5. maturity stays out of it ──────────────────────────────────────────

def test_wetness_is_not_mature_gated(world):
    """task-489: "wetness/transparency itself is generic". Only the arousal
    coupling is mature-gated, and that is task-208's separate path."""
    world.mature_content = False
    node = _garment(world)
    p = Player("Dry")
    world.add_player(p)
    _wearing(world, p, node)

    _soak(world, p, node, wet=True)
    assert node.properties["wet"] is True
    assert node.properties["current_state"] == "soaked"
    assert "Arousal" not in p.vitals, "wetness must not conjure a pleasure vital"
