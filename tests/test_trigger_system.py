"""Integration and system tests for TriggerSystem, way triggers, templates, and event indexing."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import MagicMock
from graph import Node, Edge, EDGE_TRIGGERS, EDGE_EQUIPPED, EDGE_CONNECTION
from engine.trigger_system import TriggerSystem
from engine.effects import Effects


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ Fixtures â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@pytest.fixture
def graph():
    """Create a bare WorldGraph."""
    from graph import WorldGraph
    return WorldGraph()


@pytest.fixture
def skills():
    """Create a SkillSystem with mock dependencies."""
    from engine.skills import SkillSystem
    from engine.player_manager import PlayerManager
    from engine.logging_events import GameLogger
    pm = PlayerManager(None)  # graph can be None for basic tests
    return SkillSystem(pm, GameLogger())


@pytest.fixture
def logging_events():
    """Create a GameLogger."""
    from engine.logging_events import GameLogger
    return GameLogger()


@pytest.fixture
def trigger_system(graph, skills, logging_events):
    """Create a TriggerSystem with all dependencies."""
    return TriggerSystem(graph, skills, logging_events)


@pytest.fixture
def sample_item(graph):
    """Create a basic item node in the graph."""
    item = Node(
        id="item_test_item",
        type="item",
        name="Test Item",
        properties={
            "description": "A test item.",
            "uses": 1,
            "current_state": "normal",
            "actions": ["examine", "take", "use"],
        }
    )
    graph.add_node(item)
    return item




class TestTemplateRendering:
    """Template variable substitution in trigger messages."""

    def test_render_template_player_name(self, trigger_system):
        """{player_name} is replaced with the player's name."""
        result = trigger_system._render_template(
            "Hello {player_name}!",
            {"player_name": "Traveler"}
        )
        assert result == "Hello Traveler!"

    def test_render_template_area_name(self, trigger_system):
        """{area_name} is replaced with the area name."""
        result = trigger_system._render_template(
            "You are in {area_name}.",
            {"area_name": "Dungeon"}
        )
        assert result == "You are in Dungeon."

    def test_render_template_item_name(self, trigger_system):
        """{item_name} is replaced with the item name."""
        result = trigger_system._render_template(
            "The {item_name} glows.",
            {"item_name": "Magic Sword"}
        )
        assert result == "The Magic Sword glows."

    def test_render_template_unknown_variable(self, trigger_system):
        """Unknown variables are left as-is."""
        result = trigger_system._render_template(
            "The {unknown_var} is here.",
            {"player_name": "Traveler"}
        )
        assert result == "The {unknown_var} is here."

    def test_render_template_multiple_variables(self, trigger_system):
        """Multiple variables are all replaced."""
        result = trigger_system._render_template(
            "{player_name} uses the {item_name} in {area_name}.",
            {"player_name": "Hero", "item_name": "Key", "area_name": "Hall"}
        )
        assert result == "Hero uses the Key in Hall."

    def test_render_template_no_variables(self, trigger_system):
        """Plain text without variables is returned unchanged."""
        result = trigger_system._render_template(
            "Nothing happens.",
            {"player_name": "Traveler"}
        )
        assert result == "Nothing happens."

    def test_render_template_item_properties(self, trigger_system):
        """{prop:key} resolves to item property values."""
        result = trigger_system._render_template(
            "The item has {prop:current_state} state.",
            {"item_properties": {"current_state": "open"}}
        )
        assert result == "The item has open state."

    def test_render_template_item_params(self, trigger_system):
        """{param:key} resolves to item parameter values."""
        result = trigger_system._render_template(
            "Parameter value: {param:dose}",
            {"item_params": {"dose": "5mg"}}
        )
        assert result == "Parameter value: 5mg"

    def test_render_template_strips_unknown_prop(self, trigger_system):
        """{prop:unknown} is left as-is when the key doesn't exist."""
        result = trigger_system._render_template(
            "Value: {prop:missing}",
            {"item_properties": {"exists": "yes"}}
        )
        assert result == "Value: {prop:missing}"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ TestIntegration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestTriggerIntegration:
    """End-to-end trigger execution pipeline."""

    def test_message_trigger_on_take(self, graph, logging_events, skills, sample_item):
        """An on_take trigger with message effect returns the message."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        # Create trigger node
        trigger_node = Node(
            id="trigger_test_message",
            type="logic_trigger",
            name="on_take â†’ message",
            properties={
                "trigger_type": "on_take",
                "effect_type": "message",
                "effect_params": {"message": "The item vibrates as you pick it up!"}
            }
        )
        graph.add_node(trigger_node)

        # Link item to trigger
        graph.add_edge(Edge(
            source=sample_item.id,
            target=trigger_node.id,
            type=EDGE_TRIGGERS,
            properties={"trigger_type": "on_take",
                        "effects": [{"type": "message", "params": {"message": "The item vibrates as you pick it up!"}}]}
        ))

        outputs = trigger_system._execute_triggers(
            sample_item, "on_take",
            game_state=None
        )
        assert len(outputs) > 0
        assert "vibrates" in outputs[0]

    def test_on_enter_set_state_self_locks_door(self, graph, skills, logging_events):
        """Door-lock pattern: on_enter on a way + set_state node_id 'self' locks it.

        Mirrors the UI-authored trigger (node_id 'self' = the host door) and
        the movement call site firing on_enter on the way node.
        """
        trigger_system = TriggerSystem(graph, skills, logging_events)

        door = Node(id="way_test_door", type="way", name="Test Door",
                    properties={"current_state": "open"})
        graph.add_node(door)

        trigger_node = Node(
            id="trigger_test_door_lock",
            type="logic_trigger",
            name="on_enter â†’ set_state",
            properties={
                "trigger_type": "on_enter",
                "effects": [
                    {"type": "set_state",
                     "params": {"node_id": "self", "state": "locked",
                                "message": "the door locks behind you"}}
                ],
            },
        )
        graph.add_node(trigger_node)
        graph.add_edge(Edge(
            source=door.id,
            target=trigger_node.id,
            type=EDGE_TRIGGERS,
            properties={"trigger_type": "on_enter",
                        "effects": trigger_node.properties["effects"]},
        ))

        outputs = trigger_system._execute_triggers(door, "on_enter", game_state=None)
        assert any("locks behind you" in o for o in outputs)
        assert door.properties["current_state"] == "locked"

    def test_keycard_on_use_on_clearance_unlocks_way(self, graph, skills, logging_events):
        """Keycard pattern: on_use_on + has_tag (target) + unlock_way target.

        Using the card on a door tagged clearance-4 unlocks THAT door; the
        way_id 'target' resolves to the used-on way via exit-direction matching.
        """
        trigger_system = TriggerSystem(graph, skills, logging_events)

        area = Node(id="area_secure", type="area", name="Secure Wing")
        graph.add_node(area)
        door = Node(id="way_vault", type="way", name="Vault Door",
                    properties={"current_state": "locked", "tags": ["clearance-4"]})
        graph.add_node(door)
        graph.add_edge(Edge(source=area.id, target=door.id, type=EDGE_CONNECTION,
                            properties={"direction": "north"}))
        card = Node(id="item_keycard", type="item", name="Keycard",
                    properties={"actions": ["use"], "tags": ["clearance-4"]})
        graph.add_node(card)

        trigger_node = Node(
            id="trigger_keycard_clearance",
            type="logic_trigger",
            name="on_use_on â†’ unlock_way",
            properties={
                "trigger_type": "on_use_on",
                "conditions": [{"type": "has_tag", "target": "target", "value": ["clearance-4"]}],
                "effects": [
                    {"type": "message",
                     "params": {"success_message": "Access granted.",
                                "fail_message": "Access denied â€” insufficient clearance."}},
                    {"type": "unlock_way",
                     "params": {"way_id": "target"}},
                ],
            },
        )
        graph.add_node(trigger_node)
        graph.add_edge(Edge(source=card.id, target=trigger_node.id, type=EDGE_TRIGGERS,
                            properties={"trigger_type": "on_use_on",
                                        "conditions": [{"type": "has_tag", "target": "target", "value": ["clearance-4"]}],
                                        "effects": trigger_node.properties["effects"]}))

        gs = type("FakeGS", (), {})()
        gs.get_current_time = lambda: "10:00"
        gs.time_ticks = 1
        gs.turn_number = 1
        gs.active_player = "TestPlayer"
        gs.player = None
        gs.current_area = None
        gs.get_current_area_id = lambda: "area_secure"
        gs._match_exit_direction = lambda area_id, name: "north"

        outputs = trigger_system._execute_triggers(
            card, "on_use_on", target_name="the vault door", game_state=gs
        )
        assert any("Access granted" in o for o in outputs)
        assert not any("denied" in o for o in outputs)
        assert door.properties["current_state"] == "closed"

    def test_message_effect_prefers_message_over_legacy_success_message(self, graph, skills, logging_events):
        """bug-532: a message effect carrying both `message` and the legacy
        `success_message` must narrate `message`  -  the old execution override
        overwrote it with `success_message` and silently dropped the authored text."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        item = Node(id="item_note", type="item", name="Note",
                    properties={"actions": ["examine"]})
        graph.add_node(item)
        trigger_node = Node(
            id="trigger_read_note",
            type="logic_trigger",
            name="on_examine -> message",
            properties={
                "trigger_type": "on_examine",
                "effects": [
                    {"type": "message",
                     "params": {"message": "The authored line.",
                                "success_message": "The legacy line."}},
                ],
            },
        )
        graph.add_node(trigger_node)
        graph.add_edge(Edge(source=item.id, target=trigger_node.id, type=EDGE_TRIGGERS,
                            properties={"trigger_type": "on_examine",
                                        "effects": trigger_node.properties["effects"]}))

        gs = type("FakeGS", (), {})()
        gs.get_current_time = lambda: "10:00"
        gs.time_ticks = 1
        gs.turn_number = 1
        gs.active_player = "TestPlayer"
        gs.player = None
        gs.current_area = None

        outputs = trigger_system._execute_triggers(item, "on_examine", game_state=gs)
        assert any("The authored line." in o for o in outputs), outputs
        assert not any("The legacy line." in o for o in outputs), outputs

    def test_message_effect_legacy_success_message_still_narrates_when_message_empty(self, graph, skills, logging_events):
        """bug-532: the legacy alias still works  -  `success_message` narrates when
        no `message` is present, so migrated/adjust_vital-style effects keep wording."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        item = Node(id="item_note2", type="item", name="Note",
                    properties={"actions": ["examine"]})
        graph.add_node(item)
        trigger_node = Node(
            id="trigger_read_note2",
            type="logic_trigger",
            name="on_examine -> message",
            properties={
                "trigger_type": "on_examine",
                "effects": [
                    {"type": "message", "params": {"success_message": "The legacy line."}},
                ],
            },
        )
        graph.add_node(trigger_node)
        graph.add_edge(Edge(source=item.id, target=trigger_node.id, type=EDGE_TRIGGERS,
                            properties={"trigger_type": "on_examine",
                                        "effects": trigger_node.properties["effects"]}))

        gs = type("FakeGS", (), {})()
        gs.get_current_time = lambda: "10:00"
        gs.time_ticks = 1
        gs.turn_number = 1
        gs.active_player = "TestPlayer"
        gs.player = None
        gs.current_area = None

        outputs = trigger_system._execute_triggers(item, "on_examine", game_state=gs)
        assert any("The legacy line." in o for o in outputs), outputs

    def test_keycard_clearance_mismatch_fails_with_message(self, graph, skills, logging_events):
        """Wrong clearance tag â†’ condition fails, door stays locked, fail message shown."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        area = Node(id="area_secure", type="area", name="Secure Wing")
        graph.add_node(area)
        door = Node(id="way_lab", type="way", name="Lab Door",
                    properties={"current_state": "locked", "tags": ["clearance-2"]})
        graph.add_node(door)
        graph.add_edge(Edge(source=area.id, target=door.id, type=EDGE_CONNECTION,
                            properties={"direction": "west"}))
        card = Node(id="item_keycard", type="item", name="Keycard",
                    properties={"actions": ["use"], "tags": ["clearance-4"]})
        graph.add_node(card)

        trigger_node = Node(
            id="trigger_keycard_lab",
            type="logic_trigger",
            name="on_use_on â†’ unlock_way",
            properties={
                "trigger_type": "on_use_on",
                "conditions": [{"type": "has_tag", "target": "target", "value": ["clearance-4"]}],
                "effects": [
                    {"type": "message",
                     "params": {"success_message": "Access granted.",
                                "fail_message": "Access denied â€” insufficient clearance."}},
                    {"type": "unlock_way", "params": {"way_id": "target"}},
                ],
            },
        )
        graph.add_node(trigger_node)
        graph.add_edge(Edge(source=card.id, target=trigger_node.id, type=EDGE_TRIGGERS,
                            properties={"trigger_type": "on_use_on",
                                        "conditions": [{"type": "has_tag", "target": "target", "value": ["clearance-4"]}],
                                        "effects": trigger_node.properties["effects"]}))

        gs = type("FakeGS", (), {})()
        gs.get_current_time = lambda: "10:00"
        gs.time_ticks = 1
        gs.turn_number = 1
        gs.active_player = "TestPlayer"
        gs.player = None
        gs.current_area = None
        gs.get_current_area_id = lambda: "area_secure"
        gs._match_exit_direction = lambda area_id, name: "west"

        outputs = trigger_system._execute_triggers(
            card, "on_use_on", target_name="the lab door", game_state=gs
        )
        assert any("Access denied" in o for o in outputs)
        assert not any("Access granted" in o for o in outputs)
        assert door.properties["current_state"] == "locked"

    def test_trigger_array_fires_for_each_type(self, graph, skills, logging_events, sample_item):
        """A trigger with trigger_type array fires for any of the listed types."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        trigger_node = Node(
            id="trigger_multi",
            type="logic_trigger",
            name="multi â†’ message",
            properties={
                "trigger_type": ["on_use", "on_examine"],
                "effect_type": "message",
                "effect_params": {"message": "The drawer rattles."}
            }
        )
        graph.add_node(trigger_node)

        graph.add_edge(Edge(
            source=sample_item.id,
            target=trigger_node.id,
            type=EDGE_TRIGGERS,
            properties={"trigger_type": ["on_use", "on_examine"],
                        "effects": [{"type": "message", "params": {"message": "The drawer rattles."}}]}
        ))

        outputs = trigger_system._execute_triggers(sample_item, "on_use", game_state=None)
        assert len(outputs) > 0
        assert "rattles" in outputs[0]

        outputs = trigger_system._execute_triggers(sample_item, "on_examine", game_state=None)
        assert len(outputs) > 0
        assert "rattles" in outputs[0]

    def test_trigger_array_does_not_fire_for_unlisted_type(self, graph, skills, logging_events, sample_item):
        """A trigger with trigger_type array is skipped for types not in the list."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        trigger_node = Node(
            id="trigger_multi_skip",
            type="logic_trigger",
            name="multi â†’ message",
            properties={
                "trigger_type": ["on_use", "on_examine"],
                "effect_type": "message",
                "effect_params": {"message": "The drawer rattles."}
            }
        )
        graph.add_node(trigger_node)

        graph.add_edge(Edge(
            source=sample_item.id,
            target=trigger_node.id,
            type=EDGE_TRIGGERS,
            properties={"trigger_type": ["on_use", "on_examine"],
                        "effects": [{"type": "message", "params": {"message": "The drawer rattles."}}]}
        ))

        outputs = trigger_system._execute_triggers(sample_item, "on_take", game_state=None)
        assert outputs == []

    def test_speech_matches_condition_contains(self, graph, skills, logging_events, sample_item):
        """speech_matches with contains mode fires when phrase is in the speech."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        trigger_node = Node(
            id="trigger_speech",
            type="logic_trigger",
            name="open sesame â†’ message",
            properties={
                "trigger_type": "on_speech",
                "effect_type": "message",
                "effect_params": {"message": "The wall grinds open!"},
                "conditions": [{"type": "speech_matches", "phrase": "open sesame", "mode": "contains"}]
            }
        )
        graph.add_node(trigger_node)

        graph.add_edge(Edge(
            source=sample_item.id,
            target=trigger_node.id,
            type=EDGE_TRIGGERS,
            properties={
                "trigger_type": "on_speech",
                "conditions": [{"type": "speech_matches", "phrase": "open sesame", "mode": "contains"}],
                "effects": [{"type": "message", "params": {"message": "The wall grinds open!"}}]
            }
        ))

        outputs = trigger_system._execute_triggers(
            sample_item, "on_speech",
            context={"speech": "please say open sesame now", "speaker": "Miki"},
            game_state=None)
        assert len(outputs) > 0
        assert "grinds open" in outputs[0]

    def test_speech_matches_condition_exact_no_fire(self, graph, skills, logging_events, sample_item):
        """speech_matches with exact mode requires the whole phrase, not a substring."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        trigger_node = Node(
            id="trigger_speech_exact",
            type="logic_trigger",
            name="exact â†’ message",
            properties={
                "trigger_type": "on_speech",
                "effect_type": "message",
                "effect_params": {"message": "It worked!"},
                "conditions": [{"type": "speech_matches", "phrase": "open sesame", "mode": "exact"}]
            }
        )
        graph.add_node(trigger_node)

        graph.add_edge(Edge(
            source=sample_item.id,
            target=trigger_node.id,
            type=EDGE_TRIGGERS,
            properties={
                "trigger_type": "on_speech",
                "conditions": [{"type": "speech_matches", "phrase": "open sesame", "mode": "exact"}],
                "effects": [{"type": "message", "params": {"message": "It worked!"}}]
            }
        ))

        outputs = trigger_system._execute_triggers(
            sample_item, "on_speech",
            context={"speech": "please open sesame", "speaker": "Miki"},
            game_state=None)
        assert outputs == []

        outputs = trigger_system._execute_triggers(
            sample_item, "on_speech",
            context={"speech": "open sesame", "speaker": "Miki"},
            game_state=None)
        assert len(outputs) > 0
        assert "It worked" in outputs[0]

    def test_speech_matches_condition_absent_speech_no_fire(self, graph, skills, logging_events, sample_item):
        """speech_matches with no speech in context never fires."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        trigger_node = Node(
            id="trigger_speech_nospeech",
            type="logic_trigger",
            name="no speech â†’ message",
            properties={
                "trigger_type": "on_speech",
                "effect_type": "message",
                "effect_params": {"message": "Should not fire"},
                "conditions": [{"type": "speech_matches", "phrase": "open sesame", "mode": "contains"}]
            }
        )
        graph.add_node(trigger_node)

        graph.add_edge(Edge(
            source=sample_item.id,
            target=trigger_node.id,
            type=EDGE_TRIGGERS,
            properties={
                "trigger_type": "on_speech",
                "conditions": [{"type": "speech_matches", "phrase": "open sesame", "mode": "contains"}],
                "effects": [{"type": "message", "params": {"message": "Should not fire"}}]
            }
        ))

        outputs = trigger_system._execute_triggers(sample_item, "on_speech", game_state=None)
        assert outputs == []

    def test_trigger_with_condition(self, graph, skills, logging_events, sample_item):
        """Trigger with condition only fires when condition is met."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        sample_item.properties["uses"] = 0

        trigger_node = Node(
            id="trigger_conditional",
            type="logic_trigger",
            name="uses exhausted â†’ message",
            properties={
                "trigger_type": "on_use",
                "effect_type": "message",
                "effect_params": {"message": "The item is depleted!"},
                "conditions": [{"type": "uses_reached", "value": "0"}]
            }
        )
        graph.add_node(trigger_node)

        graph.add_edge(Edge(
            source=sample_item.id,
            target=trigger_node.id,
            type=EDGE_TRIGGERS,
            properties={
                "trigger_type": "on_use",
                "conditions": [{"type": "uses_reached", "value": "0"}],
                "effects": [{"type": "message", "params": {"message": "The item is depleted!"}}]
            }
        ))

        outputs = trigger_system._execute_triggers(sample_item, "on_use")
        assert len(outputs) > 0
        assert "depleted" in outputs[0]

    def test_trigger_condition_not_met(self, graph, skills, logging_events, sample_item):
        """Trigger with unmet condition does not fire."""
        trigger_system = TriggerSystem(graph, skills, logging_events)

        sample_item.properties["uses"] = 5  # not <= 0

        trigger_node = Node(
            id="trigger_no_fire",
            type="logic_trigger",
            name="wont fire",
            properties={
                "trigger_type": "on_use",
                "effect_type": "message",
                "effect_params": {"message": "Should not fire."},
                "conditions": [{"type": "uses_reached", "value": "0"}]
            }
        )
        graph.add_node(trigger_node)

        graph.add_edge(Edge(
            source=sample_item.id,
            target=trigger_node.id,
            type=EDGE_TRIGGERS,
            properties={
                "trigger_type": "on_use",
                "conditions": [{"type": "uses_reached", "value": "0"}],
                "effects": [{"type": "message", "params": {"message": "Should not fire."}}]
            }
        ))

        outputs = trigger_system._execute_triggers(sample_item, "on_use")
        assert len(outputs) == 0

    def test_available_actions_includes_use(self, graph, skills, logging_events, sample_item):
        """Items with 'use' action have use in available actions."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        actions = trigger_system._get_available_actions(sample_item)
        action_labels = [a["action"] for a in actions]
        assert "use" in action_labels

    def test_available_actions_includes_take(self, graph, skills, logging_events, sample_item):
        """Items with 'take' action have take in available actions."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        actions = trigger_system._get_available_actions(sample_item)
        action_labels = [a["label"] for a in actions]
        assert "Pick up" in action_labels

    def test_contextual_failure_message(self, graph, skills, logging_events):
        """_contextual_failure returns a descriptive failure message."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        msg = trigger_system._contextual_failure(
            "eat", "Rock",
            [{"action": "examine", "label": "Examine", "enabled": True}]
        )
        assert "not food" in msg.lower()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ TestAddRemoveTagEffect â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestWayTriggerFiring:
    """Ways fire on_examine (via the door examine path) and on_use_on
    (when an item is used on them and the item's own trigger is silent)."""

    @staticmethod
    def _make_way_area(graph, door_name="Vault Door", door_state="locked", see_through=False, view=""):
        area = Node(id="area_secure", type="area", name="Secure Wing",
                    properties={"environment": {"light": 80}})
        graph.add_node(area)
        props = {"current_state": door_state}
        if see_through:
            props["see_through"] = True
        door = Node(id="way_vault", type="way", name=door_name, properties=props)
        graph.add_node(door)
        graph.add_edge(Edge(source=area.id, target=door.id, type=EDGE_CONNECTION,
                            properties={"direction": "north", "visible_in_direction": view}))
        return area, door

    @staticmethod
    def _wire_message_trigger(graph, node, trigger_type, message):
        trigger_node = Node(
            id=f"trigger_{node.id}_{trigger_type}",
            type="logic_trigger",
            name=f"{trigger_type} → message",
            properties={
                "trigger_type": trigger_type,
                "effects": [{"type": "message", "params": {"message": message}}],
                "success_message": "",
                "fail_message": "",
            },
        )
        graph.add_node(trigger_node)
        graph.add_edge(Edge(
            source=node.id, target=trigger_node.id, type=EDGE_TRIGGERS,
            properties={"trigger_type": trigger_type,
                        "effects": trigger_node.properties["effects"]},
        ))

    @staticmethod
    def _make_item_actions(graph, skills, logging_events):
        from engine.item_actions import ItemActions
        from engine.matching import NameMatching
        from unittest.mock import MagicMock
        trigger_system = TriggerSystem(graph, skills, logging_events)
        ia = ItemActions.__new__(ItemActions)
        ia.graph = graph
        real_matcher = NameMatching(graph, None)
        ia.matching = MagicMock()
        ia.matching._match_item_name = MagicMock(return_value=None)
        ia.matching._match_exit_direction = MagicMock(side_effect=real_matcher._match_exit_direction)
        ia.matching._match_character_name = MagicMock(return_value=(None, []))
        ia.matching.way_handle = MagicMock(side_effect=real_matcher.way_handle)
        ia.matching.resolve_exit = MagicMock(side_effect=real_matcher.resolve_exit)
        ia.trigger_system = trigger_system
        ia.equipment = MagicMock()
        ia.ghost_system = MagicMock()
        ia.ghost_system.check_ghost_action = MagicMock(return_value=None)
        ia.world = None
        return ia

    @staticmethod
    def _make_player_manager():
        from unittest.mock import MagicMock
        pm = MagicMock()
        pm.active_player = "Hero"
        pm.current_area = MagicMock()
        pm.current_area.name = "Secure Wing"
        pm.ghost_mode = False
        pm.lighting = MagicMock()
        pm.lighting.can_see_in_dark = MagicMock(return_value=True)
        pm.lighting.get_ambient_light = MagicMock(return_value=80)
        pm._get_current_area_id = MagicMock(return_value="area_secure")
        pm._player_node_id = MagicMock(side_effect=lambda n: f"player_{n}")
        pm.players = {}
        return pm

    def test_way_on_examine_fires(self, graph, skills, logging_events):
        """Examining a door fires its on_examine triggers."""
        _, door = self._make_way_area(graph)
        self._wire_message_trigger(graph, door, "on_examine", "A faint hum comes from the lock.")
        ia = self._make_item_actions(graph, skills, logging_events)
        pm = self._make_player_manager()

        desc = ia.get_item_desc(pm, "north")
        assert "faint hum" in desc

    def test_way_on_examine_peephole(self, graph, skills, logging_events):
        """A closed see_through door with a view reveals the room on examine."""
        _, door = self._make_way_area(graph, see_through=True,
                                      view="the lab bench glows faintly beyond")
        ia = self._make_item_actions(graph, skills, logging_events)
        pm = self._make_player_manager()

        desc = ia.get_item_desc(pm, "north")
        assert "lab bench glows" in desc
        assert "currently locked" in desc

    def test_way_on_use_fires_when_item_silent(self, graph, skills, logging_events):
        """Using a passive item on a door fires the door's on_use trigger
        (target side), matching the item-target fallback semantics."""
        area, door = self._make_way_area(graph)
        self._wire_message_trigger(graph, door, "on_use",
                                   "The lock rejects the item with a dull thunk.")
        card = Node(id="item_rock", type="item", name="Rock",
                    properties={"actions": ["use"]})
        graph.add_node(card)
        graph.add_edge(Edge(source=card.id, target=area.id, type="in"))
        ia = self._make_item_actions(graph, skills, logging_events)
        pm = self._make_player_manager()

        def _find_item_node(name):
            return graph.get_node(f"item_{name}")
        pm.find_item_node = _find_item_node

        result = ia.use_item_on(pm, "Rock", target_name="north")
        assert "dull thunk" in result

    def test_way_on_use_not_fired_when_item_has_on_use_on(self, graph, skills, logging_events):
        """A source item with a working on_use_on wins  -  the way's on_use
        does not also fire."""
        area, door = self._make_way_area(graph)
        self._wire_message_trigger(graph, door, "on_use",
                                   "The lock rejects the item with a dull thunk.")
        card = Node(id="item_keycard", type="item", name="Keycard",
                    properties={"actions": ["use"]})
        graph.add_node(card)
        graph.add_edge(Edge(source=card.id, target=area.id, type="in"))

        trigger_node = Node(
            id="trigger_keycard_use_on",
            type="logic_trigger",
            name="on_use_on → message",
            properties={
                "trigger_type": "on_use_on",
                "effects": [{"type": "message",
                             "params": {"message": "The keycard slot beeps."}}],
                "success_message": "",
                "fail_message": "",
            },
        )
        graph.add_node(trigger_node)
        graph.add_edge(Edge(
            source=card.id, target=trigger_node.id, type=EDGE_TRIGGERS,
            properties={"trigger_type": "on_use_on",
                        "effects": trigger_node.properties["effects"]},
        ))
        ia = self._make_item_actions(graph, skills, logging_events)
        pm = self._make_player_manager()

        def _find_item_node(name):
            return graph.get_node(f"item_{name}")
        pm.find_item_node = _find_item_node

        result = ia.use_item_on(pm, "Keycard", target_name="north")
        assert "slot beeps" in result
        assert "dull thunk" not in result


    def test_area_on_examine_fires(self, graph, skills, logging_events):
        """Examining the current area fires its on_examine triggers."""
        area = Node(id="area_secure", type="area", name="Secure Wing",
                    properties={"environment": {"light": 80},
                                "description": "White tile, humming lights."})
        graph.add_node(area)
        self._wire_message_trigger(graph, area, "on_examine",
                                   "A voice announces: 'Bay 7 clearance required.'")
        ia = self._make_item_actions(graph, skills, logging_events)
        pm = self._make_player_manager()

        desc = ia.get_item_desc(pm, "the room")
        assert "White tile" in desc
        assert "Bay 7" in desc

    def test_area_on_enter_fires(self, graph, skills, logging_events, trigger_system):
        """Moving into an area fires its on_enter triggers."""
        from engine.movement import MovementSystem
        area_a = Node(id="area_hall", type="area", name="Hall",
                      properties={"environment": {"light": 80}})
        area_b = Node(id="area_secure", type="area", name="Secure Wing",
                      properties={"environment": {"light": 80}})
        graph.add_node(area_a)
        graph.add_node(area_b)
        door = Node(id="way_door", type="way", name="Door",
                    properties={"current_state": "open"})
        graph.add_node(door)
        graph.add_edge(Edge(source=area_a.id, target=door.id, type=EDGE_CONNECTION,
                            properties={"direction": "north"}))
        graph.add_edge(Edge(source=door.id, target=area_b.id, type=EDGE_CONNECTION,
                            properties={"direction": "south"}))
        graph.add_edge(Edge(source=area_b.id, target=door.id, type=EDGE_CONNECTION,
                            properties={"direction": "south"}))
        graph.add_edge(Edge(source=door.id, target=area_a.id, type=EDGE_CONNECTION,
                            properties={"direction": "north"}))
        self._wire_message_trigger(graph, area_b, "on_enter",
                                   "The room lights snap on as you enter.")

        gs = type("FakeGS", (), {})()
        gs.player = MagicMock()
        gs.player.state = "awake"
        gs.player.has_condition = MagicMock(return_value=False)
        gs.player.vitals = {"Entertainment": 50}
        gs.players = {}
        gs.active_player = "Hero"
        gs.current_area = MagicMock()
        gs.current_area.name = "Hall"
        gs.current_area.environment = {"light": 80}
        gs.time_ticks = 1
        gs.turn_number = 1
        gs.get_current_time = lambda: "10:00"
        gs.get_current_area_id = lambda: area_a.id
        gs._get_current_area_id = gs.get_current_area_id
        gs.apply_action = lambda *a, **k: None
        log_entries = []
        gs.add_log_entry = lambda *a, **k: log_entries.append(a[0])
        gs.record_turn_event = lambda *a, **k: None
        gs.speech_log = []
        gs.area_node_id = lambda name: f"area_{name.lower().replace(' ', '_')}"
        gs.player_node_id = lambda name: f"player_{name}"
        gs._player_node_id = gs.player_node_id
        gs._area_node_id = gs.area_node_id
        gs._set_player_area = lambda *a, **k: None
        gs._match_exit_direction = lambda area_id, name: "north" if "north" in name.lower() else None
        gs.name_matcher = MagicMock()
        gs.name_matcher._match_exit_direction = MagicMock(return_value="north")
        name_matcher = MagicMock()
        name_matcher._match_exit_direction = MagicMock(return_value="north")
        name_matcher.resolve_exit = MagicMock(
            side_effect=lambda area_id, name: (
                graph.get_edges_for_source(area_id, EDGE_CONNECTION)[0],
                graph.get_node("way_door"),
                "north",
            ) if "north" in name.lower() else (None, None, "")
        )
        gs.npc_behaviors = MagicMock()
        gs.npc_behaviors.process_simple_npcs = MagicMock()

        movement = MovementSystem(
            graph, gs, trigger_system,
            toggleable_items=MagicMock(),
            name_matcher=name_matcher,
            game_state=gs,
        )
        result = movement.move_to_area("north")
        assert "Secure Wing" in result
        assert any("lights snap on" in entry for entry in log_entries)


class TestTriggerTestHelper:
    """The editor's trigger test endpoint (TriggerSystem.test_trigger)."""

    def test_dry_run_reports_conditions_and_outputs(self, graph, skills, logging_events, sample_item):
        """Dry run reports per-condition pass/fail and dry-run outputs, no side effects."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        trigger_def = {
            "trigger_type": "on_use",
            "conditions": [{"type": "uses_reached", "value": "0"}],
            "effects": [{"type": "message", "params": {"message": "The item is depleted!"}}],
        }

        sample_item.properties["uses"] = 0
        result = trigger_system.test_trigger(trigger_def, item_node=sample_item, dry_run=True)

        assert result["conditions_pass"] is True
        assert all(c["passed"] for c in result["conditions"])
        assert result["fireable"] is True
        assert len(result["outputs"]) == 1
        assert "dry-run" in result["outputs"][0]
        assert "depleted" in result["outputs"][0]
        assert result["side_effects"] == []

    def test_dry_run_flags_failed_condition(self, graph, skills, logging_events, sample_item):
        """A failed condition is reported as failed and blocks the dry-run output list."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        trigger_def = {
            "trigger_type": "on_use",
            "conditions": [{"type": "uses_reached", "value": "0"}],
            "effects": [{"type": "message", "params": {"message": "Should not fire."}}],
        }

        sample_item.properties["uses"] = 5
        result = trigger_system.test_trigger(trigger_def, item_node=sample_item, dry_run=True)

        assert result["conditions_pass"] is False
        assert result["conditions"][0]["passed"] is False
        assert result["fireable"] is True

    def test_live_run_executes_message_effect(self, graph, skills, logging_events, sample_item):
        """Live run executes effects and returns real output messages."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        trigger_def = {
            "trigger_type": "on_use",
            "conditions": [],
            "effects": [{"type": "message", "params": {"message": "It crackles and lights up!"}}],
        }

        result = trigger_system.test_trigger(trigger_def, item_node=sample_item, dry_run=False)

        assert result["conditions_pass"] is True
        assert len(result["outputs"]) == 1
        assert "crackles" in result["outputs"][0]
        assert "dry-run" not in result["outputs"][0]

    def test_fireable_false_when_item_required_but_missing(self, graph, skills, logging_events):
        """Trigger types that need an item report fireable=false when no item is provided."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        trigger_def = {
            "trigger_type": "on_examine",
            "conditions": [],
            "effects": [{"type": "message", "params": {"message": "Hi."}}],
        }

        result = trigger_system.test_trigger(trigger_def, item_node=None, dry_run=True)
        assert result["fireable"] is False

    def test_undefined_trigger_type_reports_clear_reason(self, graph, skills, logging_events):
        """No trigger type selected is reported distinctly from missing item context."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        trigger_def = {
            "trigger_type": "",
            "conditions": [],
            "effects": [{"type": "message", "params": {"message": "Hi."}}],
        }

        result = trigger_system.test_trigger(trigger_def, item_node=None, dry_run=True)
        assert result["fireable"] is False
        assert "no trigger type selected" in result["fireable_reason"]

    def test_dry_run_apply_trait_reports_character_target(self, graph, skills, logging_events, sample_item):
        """apply_trait dry-run describes the character target, not 'modify node'."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        trigger_def = {
            "trigger_type": "on_use",
            "conditions": [],
            "effects": [{"type": "apply_trait", "params": {"trait": "hostile", "target": "Bob", "param": True}}],
        }

        result = trigger_system.test_trigger(trigger_def, item_node=sample_item, dry_run=True)
        assert result["side_effects"]
        msg = result["side_effects"][0]
        assert "would apply trait" in msg
        assert "hostile" in msg
        assert "Bob" in msg
        assert "modify node" not in msg

    def test_array_trigger_type_normalized(self, graph, skills, logging_events, sample_item):
        """The editor stores trigger_type as an array â€” test_trigger must accept it."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        trigger_def = {
            "trigger_type": ["on_use"],
            "conditions": {},
            "effects": [{"type": "apply_trait", "params": {"trait": "hostile", "target": "Bob", "param": True}}],
        }

        result = trigger_system.test_trigger(trigger_def, item_node=sample_item, dry_run=True)
        assert result["trigger_type"] == "on_use"
        assert result["fireable"] is True
        assert result["conditions_pass"] is True
        assert "would apply trait" in result["side_effects"][0]

    def test_item_trigger_without_context_not_fireable(self, graph, skills, logging_events):
        """An itemful trigger with no item context reports fireable=false."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        trigger_def = {
            "trigger_type": ["on_use"],
            "conditions": {},
            "effects": [{"type": "message", "params": {"message": "Hi."}}],
        }

        result = trigger_system.test_trigger(trigger_def, item_node=None, dry_run=True)
        assert result["fireable"] is False
        assert "needs an item/way context" in result["fireable_reason"]

    def test_speech_context_reaches_condition(self, graph, skills, logging_events, sample_item):
        """test_trigger passes context (speech) through to condition evaluation."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        trigger_def = {
            "trigger_type": "on_speech",
            "conditions": [{"type": "speech_matches", "phrase": "open sesame", "mode": "contains"}],
            "effects": [{"type": "message", "params": {"message": "The wall grinds open!"}}],
        }

        result = trigger_system.test_trigger(
            trigger_def, item_node=sample_item, dry_run=True,
            context={"speech": "please open sesame now", "speaker": "Miki"},
        )
        assert result["conditions_pass"] is True
        assert result["conditions"][0]["passed"] is True


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ TestUnifiedEffectTargeting â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestTriggerEventIndex:
    """task-406: event-indexed dispatch, standing-item ticks, lazy context.

    These cover the acceptance criteria that the implementation commit
    (961b286) shipped without tests for: a standing item fires on_tick exactly
    once, carried/lit items are not double-fired, item turn/time triggers now
    fire, a no-match call builds no context (and never reads the legacy
    ``current_area`` property), and the graph index stays correct across
    add/remove/load/clear.
    """

    MARK = "TASK406_PROBE"

    @staticmethod
    def _world():
        from app import create_app
        app = create_app({'TESTING': True})
        return app.world, app.test_client()

    @staticmethod
    def _item(world, name, **props):
        from graph import Node
        item = Node(id=f'item_task406_{name}', type='item', name=name,
                    properties={'uses': -1, 'actions': 'examine', **props})
        world.graph.add_node(item)
        return item

    @staticmethod
    def _message_trigger(world, item, trigger_type, text):
        from graph import Node, Edge
        tid = f'trig_task406_{item.id}_{trigger_type}'
        props = {
            'trigger_type': [trigger_type],
            'effects': [{'type': 'message', 'params': {'message': text}}],
        }
        world.graph.add_node(Node(id=tid, type='logic_trigger', name='probe',
                                  properties=props))
        world.graph.add_edge(Edge(source=item.id, target=tid, type=EDGE_TRIGGERS,
                                  properties=props))
        return tid

    def _count(self, world, needle):
        return sum(1 for line in world.game_logger.game_log if needle in line)

    def test_standing_item_on_tick_fires_once_per_tick(self):
        world, _ = self._world()
        world.set_active_player('Kaelen Voss')
        item = self._item(world, 'shrine', current_state='idle')
        self._message_trigger(world, item, 'on_tick', self.MARK)
        world.tick_turn()
        assert self._count(world, self.MARK) == 1

    def test_carried_item_on_tick_not_double_fired(self):
        from graph import Edge
        world, _ = self._world()
        world.set_active_player('Kaelen Voss')
        item = self._item(world, 'amulet', current_state='hidden')
        world.graph.add_edge(Edge(source=item.id, target='player_Kaelen_Voss',
                                  type='carrying'))
        self._message_trigger(world, item, 'on_tick', self.MARK)
        world.tick_turn()
        assert self._count(world, self.MARK) == 1

    def test_lit_area_item_on_tick_not_double_fired(self):
        from graph import Edge, EDGE_IN
        world, _ = self._world()
        world.set_active_player('Kaelen Voss')
        item = self._item(world, 'lantern', current_state='lit', uses=50)
        world.graph.add_edge(Edge(source=item.id, target=world.get_current_area_id(),
                                  type=EDGE_IN))
        self._message_trigger(world, item, 'on_tick', self.MARK)
        world.tick_turn()
        assert self._count(world, self.MARK) == 1

    def test_item_on_turn_start_trigger_now_fires(self):
        world, _ = self._world()
        item = self._item(world, 'totem', current_state='idle')
        self._message_trigger(world, item, 'on_turn_start', self.MARK)
        world._fire_turn_triggers('on_turn_start')
        assert self._count(world, self.MARK) == 1

    def test_no_match_returns_empty_without_reading_current_area(self):
        world, _ = self._world()
        item = self._item(world, 'plain', current_state='idle')
        # Edge exists but the type cannot match the requested trigger type.
        self._message_trigger(world, item, 'on_examine', self.MARK)

        class Exploding:
            @property
            def current_area(self):
                raise AssertionError('current_area read on no-match path')

            def get_current_area_id(self):
                raise AssertionError('get_current_area_id read on no-match path')

        assert world.triggers._execute_triggers(
            item, 'on_tick', game_state=Exploding()) == []
        assert self._count(world, self.MARK) == 0

    def test_trigger_index_tracks_add_remove_load_clear(self, graph):
        from graph import Node, Edge
        graph.add_node(Node(id='item_a', type='item', name='a', properties={}))
        graph.add_node(Node(id='trig_a', type='logic_trigger', name='t', properties={}))
        graph.add_edge(Edge(source='item_a', target='trig_a', type=EDGE_TRIGGERS,
                            properties={'trigger_type': ['on_tick', 'on_turn_start']}))
        assert set(graph.get_trigger_sources('on_tick')) == {'item_a'}
        assert set(graph.get_trigger_sources('on_turn_start')) == {'item_a'}
        assert graph.get_trigger_sources('on_examine') == []

        # An edge with no trigger_type is a legacy shape that never matched;
        # the index must not invent a match for it.
        graph.add_edge(Edge(source='item_a', target='trig_a', type=EDGE_TRIGGERS,
                            properties={}))
        assert graph.get_trigger_sources('on_tick') == ['item_a']

        graph.remove_edge('item_a', 'trig_a', EDGE_TRIGGERS)
        assert graph.get_trigger_sources('on_tick') == []

        graph.add_edge(Edge(source='item_a', target='trig_a', type=EDGE_TRIGGERS,
                            properties={'trigger_type': ['on_tick']}))
        graph.load_from_dict(graph.to_dict())
        assert set(graph.get_trigger_sources('on_tick')) == {'item_a'}

        graph.clear()
        assert graph.get_trigger_sources('on_tick') == []


# ─── TestTask705Leaves ───


class TestTask705Leaves:
    """task-705: ``owns`` (ownership as a property) and ``known`` (the authored
    knowledge registry) - the two leaves that were genuinely missing. The other
    leaves the card named already existed: ``has_tag``/``target_has_tag``/
    ``character_has_tag``/``player_has_tag`` carry their subject in the leaf name
    plus a ``target`` param, ``flag_equals`` is the flag leaf, and
    ``proximity``/``in_area`` are co-location. Both new leaves fail closed.
    """

    @staticmethod
    def _gs(players, active="TestPlayer"):
        gs = type("FakeGameState", (), {})()
        gs.players = players
        gs.active_player = active
        gs.player = players.get(active)
        from engine.player_manager import PlayerManager
        pm = PlayerManager(None)
        for name, player in players.items():
            pm.players[name] = player
        gs.player_manager = pm
        return gs

    def test_owns_reads_the_owner_property_not_inventory(self, graph, trigger_system, sample_item):
        """`owns` is a claim, not a carry: the item is not held and not equipped,
        yet it is hers. That is the whole difference from has_item/is_equipped."""
        from player import Player
        player = Player("TestPlayer")
        sample_item.properties["owner"] = "TestPlayer"
        gs = self._gs({"TestPlayer": player})

        assert trigger_system._evaluate_trigger_condition(
            {"type": "owns", "node_id": sample_item.id}, sample_item, game_state=gs
        ) is True

    def test_owns_is_false_for_another_players_claim(self, graph, trigger_system, sample_item):
        from player import Player
        player = Player("TestPlayer")
        other = Player("Other")
        sample_item.properties["owner"] = "Other"
        gs = self._gs({"TestPlayer": player, "Other": other})

        assert trigger_system._evaluate_trigger_condition(
            {"type": "owns", "node_id": sample_item.id}, sample_item, game_state=gs
        ) is False

    def test_owns_fails_closed(self, graph, trigger_system, sample_item):
        """Unowned, a node that does not exist, and no node_id at all all read
        False - never an exception, never an invented claim."""
        from player import Player
        player = Player("TestPlayer")
        gs = self._gs({"TestPlayer": player})

        assert trigger_system._evaluate_trigger_condition(
            {"type": "owns", "node_id": sample_item.id}, sample_item, game_state=gs
        ) is False
        assert trigger_system._evaluate_trigger_condition(
            {"type": "owns", "node_id": "item_does_not_exist"}, sample_item, game_state=gs
        ) is False
        assert trigger_system._evaluate_trigger_condition(
            {"type": "owns"}, sample_item, game_state=gs
        ) is False

    def test_known_reads_player_known(self, graph, trigger_system, sample_item):
        from player import Player
        player = Player("TestPlayer")
        player.known = ["area_food_storage", "Water Source"]
        gs = self._gs({"TestPlayer": player})

        assert trigger_system._evaluate_trigger_condition(
            {"type": "known", "value": "area_food_storage"}, sample_item, game_state=gs
        ) is True
        assert trigger_system._evaluate_trigger_condition(
            {"type": "known", "value": "area_training_pit"}, sample_item, game_state=gs
        ) is False

    def test_known_fails_closed(self, graph, trigger_system, sample_item):
        from player import Player
        player = Player("TestPlayer")
        gs = self._gs({"TestPlayer": player})

        assert trigger_system._evaluate_trigger_condition(
            {"type": "known", "value": "area_food_storage"}, sample_item, game_state=gs
        ) is False
        assert trigger_system._evaluate_trigger_condition(
            {"type": "known"}, sample_item, game_state=gs
        ) is False

    def test_both_leaves_are_declared_for_the_validator(self):
        """The validator rejects an undeclared type, so a leaf that evaluates but
        is not declared is a leaf no author can use."""
        from engine.trigger_validator import CONDITION_TYPES
        assert "owns" in CONDITION_TYPES
        assert "known" in CONDITION_TYPES


class TestPropertyBasedTriggers:
    """task-886: Triggers stored directly in node.properties['triggers']."""

    def test_property_trigger_fires_without_graph_nodes(self, graph, trigger_system, sample_item):
        sample_item.properties["triggers"] = [
            {
                "id": "trig_eat_apple",
                "trigger_type": "on_eat",
                "effects": [
                    {"type": "message", "params": {"message": "Crisp and juicy."}},
                ],
            }
        ]
        # Assert no logic_trigger nodes or triggers edges exist
        assert not any(n.type == "logic_trigger" for n in graph.nodes.values())
        assert not graph.get_edges_by_type(EDGE_TRIGGERS)

        outputs = trigger_system._execute_triggers(sample_item, "on_eat")
        assert any("Crisp and juicy" in o for o in outputs)

    def test_property_trigger_once_marks_fired(self, graph, trigger_system, sample_item):
        sample_item.properties["triggers"] = [
            {
                "id": "trig_secret_note",
                "trigger_type": "on_examine",
                "once": True,
                "effects": [
                    {"type": "message", "params": {"message": "A hidden glyph is revealed."}},
                ],
            }
        ]
        outputs1 = trigger_system._execute_triggers(sample_item, "on_examine")
        assert any("hidden glyph" in o for o in outputs1)
        assert sample_item.properties["triggers"][0]["fired"] is True

        # Second examination: once prevents re-firing
        outputs2 = trigger_system._execute_triggers(sample_item, "on_examine")
        assert not any("hidden glyph" in o for o in outputs2)

    def test_property_trigger_condition_gating(self, graph, trigger_system, sample_item):
        sample_item.properties["uses"] = 0
        sample_item.properties["triggers"] = [
            {
                "id": "trig_empty_flask",
                "trigger_type": "on_use",
                "conditions": [{"type": "uses_reached", "value": "0"}],
                "effects": [
                    {"type": "message", "params": {"message": "It is completely dry."}},
                ],
            }
        ]
        outputs = trigger_system._execute_triggers(sample_item, "on_use")
        assert any("completely dry" in o for o in outputs)

        # Uses reset to 5 -> condition fails -> does not fire
        sample_item.properties["uses"] = 5
        outputs2 = trigger_system._execute_triggers(sample_item, "on_use")
        assert not any("completely dry" in o for o in outputs2)
