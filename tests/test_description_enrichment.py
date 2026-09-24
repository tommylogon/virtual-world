"""task-486: auto-regenerate the stored appearance description when the
character's visible state changes (conditions/body-state), not only on
equip/unequip.

Covers the EquipmentSystem reconciliation hook, its hash/gate guards, the
conditions-system immediate refresh, and the per-turn tick safety net that
catches direct ``player.conditions`` dict writes.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from area import Area
from graph import Node, WorldGraph
from player import Player
from engine.equipment import EquipmentSystem
from engine.player_manager import PlayerManager
from engine.logging_events import GameLogger
from engine.conditions import ConditionsSystem


class MockTriggerSystem:
    def _execute_triggers(self, *args, **kwargs):
        return []


class FakeWorld:
    """Minimal world surface the equipment/conditions systems read."""

    def __init__(self, mature_content=True, auto_generate_descriptions=True):
        self.mature_content = mature_content
        self.auto_generate_descriptions = auto_generate_descriptions


def make_setup(mature_content=True, auto_generate_descriptions=True):
    graph = WorldGraph()
    pm = PlayerManager(graph)
    player = Player("Traveler")
    player.base_description = "A tall traveler with dark hair."
    pm.add_player(player)
    pm.set_active_player("Traveler")
    world = FakeWorld(mature_content, auto_generate_descriptions)
    equipment = EquipmentSystem(graph, MockTriggerSystem(), GameLogger(), pm)
    equipment.world = world
    world.equipment = equipment
    return graph, pm, equipment, player, world


# ─────────────────── EquipmentSystem reconciliation ───────────────────


class TestStateDescriptionReconciliation:
    def test_regenerates_when_visible_condition_applied(self):
        _graph, _pm, equipment, player, _world = make_setup()
        # Build a baseline description and seed the state hash.
        equipment._update_state_description(player)
        baseline = player.description

        player.add_condition("blushing")
        assert equipment._update_state_description(player) is True
        assert player.description != baseline
        assert "cheeks are flushed" in player.description

    def test_regenerates_when_visible_condition_removed(self):
        _graph, _pm, equipment, player, _world = make_setup()
        player.add_condition("blushing")
        equipment._update_state_description(player)
        assert "cheeks are flushed" in player.description

        player.remove_condition("blushing")
        assert equipment._update_state_description(player) is True
        assert "cheeks are flushed" not in player.description

    def test_no_regeneration_when_nothing_changed(self):
        _graph, _pm, equipment, player, _world = make_setup()
        equipment._update_equipment_description(player)
        # Hash was just stored, so a second pass is a no-op.
        assert equipment._update_state_description(player) is False

    def test_non_visible_condition_does_not_rebuild(self):
        _graph, _pm, equipment, player, _world = make_setup()
        equipment._update_equipment_description(player)
        baseline = player.description

        player.add_condition("stunned")
        assert equipment._update_state_description(player) is False
        assert player.description == baseline

    def test_disabled_when_auto_generate_is_off(self):
        _graph, _pm, equipment, player, world = make_setup()
        equipment._update_equipment_description(player)
        baseline = player.description
        world.auto_generate_descriptions = False

        player.add_condition("blushing")
        assert equipment._update_state_description(player) is False
        assert player.description == baseline

    def test_mature_gate_controls_body_state_block(self):
        _graph, _pm, equipment, player, world = make_setup(mature_content=False)
        player.add_condition("blushing")
        equipment._update_state_description(player)
        assert "cheeks are flushed" not in player.description

        # Turning mature content on makes the same condition visible, which the
        # hash notices even though the conditions themselves did not change.
        world.mature_content = True
        assert equipment._update_state_description(player) is True
        assert "cheeks are flushed" in player.description

    def test_item_state_change_triggers_rebuild(self):
        _graph, _pm, equipment, player, _world = make_setup()
        node = Node(id="item_lantern", type="item", name="Lantern", properties={
            "description": "A hooded lantern.", "current_state": "off"})
        equipment.graph.add_node(node)
        player.equipped["hand_right"] = ["item_lantern"]
        equipment._update_equipment_description(player)
        assert equipment._update_state_description(player) is False

        node.properties["current_state"] = "on"
        assert equipment._update_state_description(player) is True


# ─────────────────── ConditionsSystem immediate refresh ───────────────────


class TestConditionsSystemRefresh:
    def test_apply_and_remove_refresh_description_immediately(self):
        _graph, pm, equipment, player, _world = make_setup()
        cs = ConditionsSystem(pm, equipment.world)
        equipment._update_equipment_description(player)
        baseline = player.description

        cs.apply_condition("Traveler", "blushing")
        assert player.description != baseline
        assert "cheeks are flushed" in player.description

        cs.remove_condition("Traveler", "blushing")
        assert "cheeks are flushed" not in player.description

    def test_conditions_system_with_no_world_is_safe(self):
        _graph, pm, _equipment, player, _world = make_setup()
        cs = ConditionsSystem(pm, None)
        cs.apply_condition("Traveler", "blushing")
        assert "blushing" in player.conditions


# ─────────────────── Tick-manager safety net (direct dict writes) ───────────────────


def make_world():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.movement.add_area(Area("Room", "A quiet room.", []))
    world.name_matcher._set_player_area(world.active_player, "Room")
    return world


def test_tick_refreshes_description_after_direct_condition_write():
    world = make_world()
    player = world.players[world.active_player]
    player.base_description = "A weary traveler."
    world.mature_content = True
    world.auto_generate_descriptions = True
    world.equipment._update_equipment_description(player)
    baseline = player.description

    # Bypass the add_condition helpers entirely, the way several engine sites do.
    player.conditions["blushing"] = [{"duration": 5, "source": None, "level": 0}]
    world.tick_manager.tick_turn()

    assert player.description != baseline
    assert "cheeks are flushed" in player.description


def test_tick_leaves_description_alone_when_nothing_changes():
    world = make_world()
    world.mature_content = True
    world.auto_generate_descriptions = True
    player = world.players[world.active_player]
    world.equipment._update_equipment_description(player)

    before = player.description
    world.tick_manager.tick_turn()
    assert player.description == before
