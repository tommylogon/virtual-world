"""Tests for the delayed event queue (task-90).

Coverage:
- ``schedule_trigger`` effect queues an ``on_delayed`` fire on a target node
- delayed fires only after the requested number of tick_turn() steps
- ``on_delayed`` triggers reuse normal effects (message/damage)
- default target = the node the scheduling trigger lives on
- queue survives save/load (to_dict / load_from_dict)
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from virtual_world_engine import VirtualWorld
from area import Area
from graph import Node, Edge, EDGE_TRIGGERS, EDGE_IN


@pytest.fixture
def delayed_world():
    """A world with a cursed ring: take → schedule 3 ticks → on_delayed fires."""
    world = VirtualWorld()
    world.movement.add_area(Area("Room A", "First room.", []))
    world.name_matcher._set_player_area(world.active_player, "Room A")
    aid = world._area_node_id("Room A")

    ring = Node(
        id="item_cursed_ring",
        type="item",
        name="Cursed Ring",
        properties={"current_state": "normal", "actions": "examine,take,use"},
    )
    world.graph.add_node(ring)
    world.graph.add_edge(Edge(source=ring.id, target=aid, type=EDGE_IN))

    # on_take → schedule an on_delayed fire 3 ticks from now
    t1 = Node(id="trig_sched", type="logic_trigger", name="sched", properties={"trigger_type": "on_take"})
    world.graph.add_node(t1)
    world.graph.add_edge(Edge(
        source=ring.id, target=t1.id, type=EDGE_TRIGGERS,
        properties={"trigger_type": "on_take",
                    "effects": [{"type": "schedule_trigger",
                                 "params": {"delay_ticks": 3, "target": "Cursed Ring"}}]},
    ))

    # on_delayed → what actually happens when the delay elapses
    delay = Node(id="trig_delayed", type="logic_trigger", name="delayed", properties={"trigger_type": "on_delayed"})
    world.graph.add_node(delay)
    world.graph.add_edge(Edge(
        source=ring.id, target=delay.id, type=EDGE_TRIGGERS,
        properties={"trigger_type": "on_delayed",
                    "effects": [
                        {"type": "message", "params": {"message": "The cursed ring pulses with dark energy!"}},
                        {"type": "damage", "params": {"amount": 5, "target": "self"}},
                    ]},
    ))
    return world


class TestDelayedEventQueue:
    def test_take_schedules_delayed_event(self, delayed_world):
        delayed_world.item_actions.take_item(delayed_world, "Cursed Ring")
        assert len(delayed_world.delayed_events) == 1
        event = delayed_world.delayed_events.events[0]
        assert event["fire_tick"] == 3          # tick 0 + 3
        assert event["target_node_id"] == "item_cursed_ring"
        assert event["trigger_type"] == "on_delayed"

    def test_does_not_fire_early(self, delayed_world):
        delayed_world.item_actions.take_item(delayed_world, "Cursed Ring")
        hp = delayed_world.player.vitals["HP"]
        delayed_world.tick_turn()
        delayed_world.tick_turn()
        assert delayed_world.player.vitals["HP"] == hp      # 3 ticks needed, only 2 passed
        assert len(delayed_world.delayed_events) == 1

    def test_fires_after_delay_ticks(self, delayed_world):
        delayed_world.item_actions.take_item(delayed_world, "Cursed Ring")
        hp = delayed_world.player.vitals["HP"]
        delayed_world.tick_turn()
        delayed_world.tick_turn()
        delayed_world.tick_turn()
        assert delayed_world.player.vitals["HP"] == hp - 5   # damage effect ran
        assert len(delayed_world.delayed_events) == 0        # queue drained

    def test_pending_event_survives_save_load(self, delayed_world):
        delayed_world.item_actions.take_item(delayed_world, "Cursed Ring")
        data = json.loads(json.dumps(delayed_world.to_dict()))
        reloaded = VirtualWorld()
        reloaded.load_from_dict(data)
        assert len(reloaded.delayed_events) == 1
        hp = reloaded.player.vitals["HP"]
        for _ in range(3):
            reloaded.tick_turn()
        assert reloaded.player.vitals["HP"] == hp - 5

    def test_queue_persisted_in_scenario_dict_stripped(self, delayed_world):
        delayed_world.item_actions.take_item(delayed_world, "Cursed Ring")
        scenario = delayed_world.to_scenario_dict()
        assert "delayed_events" not in scenario


class TestScheduleTriggerEffect:
    def test_default_target_is_trigger_parent(self):
        """No `target` param → the trigger's own item is scheduled."""
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        world.name_matcher._set_player_area(world.active_player, "Room A")
        aid = world._area_node_id("Room A")
        stone = Node(id="item_cursed_stone", type="item", name="Cursed Stone",
                     properties={"current_state": "normal", "actions": "examine,take,use"})
        world.graph.add_node(stone)
        world.graph.add_edge(Edge(source=stone.id, target=aid, type=EDGE_IN))
        t = Node(id="trig_stone", type="logic_trigger", name="t", properties={"trigger_type": "on_use"})
        world.graph.add_node(t)
        world.graph.add_edge(Edge(
            source=stone.id, target=t.id, type=EDGE_TRIGGERS,
            properties={"trigger_type": "on_use",
                        "effects": [{"type": "schedule_trigger", "params": {"delay_ticks": 2}}]},
        ))
        from engine.trigger_system import TriggerSystem
        out = world.triggers._execute_triggers(stone, "on_use", game_state=world)
        assert out == []
        assert len(world.delayed_events) == 1
        event = world.delayed_events.events[0]
        assert event["target_node_id"] == "item_cursed_stone"
        assert event["fire_tick"] == 2

    def test_missing_game_state_is_safe(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        stone = Node(id="item_plain_stone", type="item", name="Stone", properties={})
        world.graph.add_node(stone)
        assert world.effects.handle_schedule_trigger(
            {"delay_ticks": 5}, {}, item_node=stone, game_state=None
        ) == []

    def test_dead_target_node_is_skipped(self, delayed_world):
        """If the target node is deleted before the fire, the event is dropped."""
        delayed_world.item_actions.take_item(delayed_world, "Cursed Ring")
        delayed_world.graph.remove_node("item_cursed_ring")
        delayed_world.tick_turn()
        delayed_world.tick_turn()
        delayed_world.tick_turn()
        assert len(delayed_world.delayed_events) == 0