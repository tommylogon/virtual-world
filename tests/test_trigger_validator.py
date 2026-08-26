"""Tests for the TriggerValidator: broken trigger reference detection."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from graph import Node, Edge, EDGE_TRIGGERS
from engine.trigger_validator import TriggerValidator


@pytest.fixture
def graph():
    from graph import WorldGraph
    return WorldGraph()


@pytest.fixture
def validator(graph, tmp_path):
    return TriggerValidator(graph, library_dir=str(tmp_path))


def add_item(graph, node_id="item_button_18", name="button 18"):
    node = Node(id=node_id, type="item", name=name, properties={"tags": [], "current_state": "normal"})
    graph.add_node(node)
    return node


def add_way(graph, node_id="way_task_18_door_3", name="Door 3"):
    node = Node(id=node_id, type="way", name=name, properties={})
    graph.add_node(node)
    return node


def add_trigger(graph, source_id, trigger_id, props, target_type="logic_trigger"):
    tnode = Node(id=trigger_id, type=target_type, name=trigger_id, properties=props)
    graph.add_node(tnode)
    graph.add_edge(Edge(source=source_id, target=trigger_id, type=EDGE_TRIGGERS, properties=props))
    return tnode


def only(issues, code):
    matches = [i for i in issues if i.get("code") == code]
    assert matches, f"expected issue code '{code}', got: {issues}"
    return matches[0]


class TestTriggerEdgeValidation:
    def test_dangling_trigger_edge(self, graph, validator):
        item = add_item(graph)
        graph.add_edge(Edge(source=item.id, target="trigger_gone_on_use_1", type=EDGE_TRIGGERS))
        issues = validator.validate()
        issue = only(issues, "dangling_trigger_edge")
        assert issue["severity"] == "error"
        assert issue["source_node_id"] == item.id

    def test_trigger_edge_wrong_target_type(self, graph, validator):
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {"trigger_type": "on_use", "effects": []},
                    target_type="way")
        issues = validator.validate()
        issue = only(issues, "trigger_edge_wrong_target_type")
        assert issue["severity"] == "error"

    def test_stale_trigger_copy_detected(self, graph, validator):
        item = add_item(graph, "item_button_18", "button 18")
        add_trigger(graph, item.id, "trigger_item_button 7_1786282772255_138_['on_use']_849",
                    {"trigger_type": "on_use", "effects": []})
        issues = validator.validate()
        issue = only(issues, "stale_trigger_copy")
        assert issue["severity"] == "warning"

    def test_healthy_trigger_no_stale_flag(self, graph, validator):
        item = add_item(graph, "item_button_18", "button 18")
        add_trigger(graph, item.id, "trigger_item_button_18_on_use_1234_567",
                    {"trigger_type": "on_use", "effects": []})
        assert not [i for i in validator.validate() if i.get("code") == "stale_trigger_copy"]

    def test_random_suffix_trigger_not_flagged_stale(self, graph, validator):
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1786286403193_pkvw",
                    {"trigger_type": "on_use", "effects": []})
        assert not [i for i in validator.validate() if i.get("code") == "stale_trigger_copy"]

    def test_shared_trigger_not_flagged_stale(self, graph, validator):
        way_a = add_way(graph, "way_task_18_room_4", "Door 4")
        way_b = add_way(graph, "way_task_18_jump", "Jump")
        trigger_id = "trigger_way_task_18_jump_1786480505822_jsd0"
        add_trigger(graph, way_a.id, trigger_id, {"trigger_type": "on_examine", "effects": []})
        add_trigger(graph, way_b.id, trigger_id, {"trigger_type": "on_examine", "effects": []})
        issues = validator.validate()
        assert not [i for i in issues if i.get("code") == "stale_trigger_copy"]

    def test_node_filter(self, graph, validator):
        a = add_item(graph, "item_a", "A")
        b = add_item(graph, "item_b", "B")
        add_trigger(graph, a.id, "trigger_a_on_use_1", {"trigger_type": "on_use", "effects": []})
        add_trigger(graph, b.id, "trigger_gone", {"trigger_type": "on_use", "effects": []},
                    target_type="way")
        issues = validator.validate(node_id="item_b")
        assert [i for i in issues if i.get("source_node_id") == "item_b"]
        assert not [i for i in issues if i.get("source_node_id") == "item_a"]


class TestEffectNodeReferences:
    def test_set_state_missing_node(self, graph, validator):
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {
            "trigger_type": "on_use",
            "effects": [{"type": "set_state", "params": {"node_id": "way_task_18__door_2__closed", "state": "locked"}}],
        })
        issue = only(validator.validate(), "missing_effect_node")
        assert issue["severity"] == "error"
        assert issue["target_node_id"] == "way_task_18__door_2__closed"

    def test_set_state_self_is_valid(self, graph, validator):
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {
            "trigger_type": "on_use",
            "effects": [{"type": "set_state", "params": {"node_id": "self", "state": "locked"}}],
        })
        assert not [i for i in validator.validate() if i.get("code") == "missing_effect_node"]

    def test_unlock_way_missing_way(self, graph, validator):
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {
            "trigger_type": "on_use",
            "effects": [{"type": "unlock_way", "params": {"way_id": "way_task_18__door_3__locked"}}],
        })
        issue = only(validator.validate(), "missing_effect_node")
        assert issue["target_node_id"] == "way_task_18__door_3__locked"

    def test_unlock_way_target_is_valid(self, graph, validator):
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {
            "trigger_type": "on_use_on",
            "effects": [{"type": "unlock_way", "params": {"way_id": "target"}}],
        })
        assert not [i for i in validator.validate() if i.get("code") == "missing_effect_node"]

    def test_teleport_missing_area(self, graph, validator):
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {
            "trigger_type": "on_use",
            "effects": [{"type": "teleport", "params": {"area": "the void"}}],
        })
        issue = only(validator.validate(), "teleport_missing_area")
        assert issue["severity"] == "warning"

    def test_teleport_existing_area_ok(self, graph, validator):
        item = add_item(graph)
        graph.add_node(Node(id="area_void", type="area", name="the void", properties={}))
        add_trigger(graph, item.id, "trigger_1", {
            "trigger_type": "on_use",
            "effects": [{"type": "teleport", "params": {"area": "the void"}}],
        })
        assert not [i for i in validator.validate() if i.get("code") == "teleport_missing_area"]

    def test_legacy_effect_shape(self, graph, validator):
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {
            "trigger_type": "on_use",
            "effect_type": "set_state",
            "effect_params": {"node_id": "way_missing", "state": "open"},
        })
        assert only(validator.validate(), "missing_effect_node")


class TestEffectItemReferences:
    def test_spawn_item_missing_everywhere(self, graph, validator):
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {
            "trigger_type": "on_use",
            "effects": [{"type": "spawn_item", "params": {"item_id": "item_missing"}}],
        })
        issue = only(validator.validate(), "missing_effect_item")
        assert issue["severity"] == "error"

    def test_spawn_item_from_library_ok(self, graph, validator, tmp_path):
        lib = tmp_path / "items"
        lib.mkdir()
        (lib / "item_keycard.json").write_text('{"name": "keycard"}', encoding="utf-8")
        from engine.trigger_validator import TriggerValidator
        validator = TriggerValidator(graph, library_dir=str(tmp_path))
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {
            "trigger_type": "on_use",
            "effects": [{"type": "spawn_item", "params": {"item_id": "item_keycard"}}],
        })
        assert not [i for i in validator.validate() if i.get("code") == "missing_effect_item"]

    def test_remove_item_missing_is_warning(self, graph, validator):
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {
            "trigger_type": "on_use",
            "effects": [{"type": "remove_item", "params": {"item_id": "item_runtime_spawned"}}],
        })
        issue = only(validator.validate(), "missing_effect_item")
        assert issue["severity"] == "warning"


class TestConditionReferences:
    def test_has_tag_no_node_has_tag(self, graph, validator):
        keycard = add_item(graph, "item_keycard", "keycard")
        add_trigger(graph, keycard.id, "trigger_1", {
            "trigger_type": "on_use_on",
            "conditions": {"operator": "and", "conditions": [
                {"type": "has_tag", "target": "target", "value": ["clearance"]}
            ]},
            "effects": [{"type": "unlock_way", "params": {"way_id": "target"}}],
        })
        issue = only(validator.validate(), "tag_not_in_world")
        assert issue["severity"] == "warning"
        assert "clearance" in issue["message"]
        assert issue["source_node_id"] == keycard.id

    def test_has_tag_satisfied_ok(self, graph, validator):
        door = add_way(graph, "way_door", "Door")
        door.properties["tags"] = ["clearance"]
        keycard = add_item(graph, "item_keycard", "keycard")
        add_trigger(graph, keycard.id, "trigger_1", {
            "trigger_type": "on_use_on",
            "conditions": [{"type": "has_tag", "target": "target", "value": ["clearance"]}],
            "effects": [],
        })
        assert not [i for i in validator.validate() if i.get("code") == "tag_not_in_world"]

    def test_flat_has_tag_string_value(self, graph, validator):
        keycard = add_item(graph, "item_keycard", "keycard")
        add_trigger(graph, keycard.id, "trigger_1", {
            "trigger_type": "on_use",
            "conditions": [{"type": "has_tag", "value": "blessed"}],
            "effects": [],
        })
        assert only(validator.validate(), "tag_not_in_world")

    def test_has_item_missing(self, graph, validator):
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {
            "trigger_type": "on_use",
            "conditions": [{"type": "has_item", "value": "magic_sword"}],
            "effects": [],
        })
        issue = only(validator.validate(), "condition_missing_item")
        assert "magic_sword" in issue["message"]

    def test_has_items_partial_missing(self, graph, validator):
        graph.add_node(Node(id="item_torch", type="item", name="torch", properties={}))
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {
            "trigger_type": "on_use",
            "conditions": [{"type": "has_items", "value": ["torch", "nonexistent_key"]}],
            "effects": [],
        })
        issues = [i for i in validator.validate() if i.get("code") == "condition_missing_item"]
        assert len(issues) == 1
        assert "nonexistent_key" in issues[0]["message"]

    def test_state_equals_missing_target(self, graph, validator):
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {
            "trigger_type": "on_use",
            "conditions": [{"type": "state_equals", "target": "old_console", "value": "on"}],
            "effects": [],
        })
        assert only(validator.validate(), "condition_missing_node")


class TestUnknownTypesAndRecursion:
    def test_unknown_condition_type(self, graph, validator):
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {
            "trigger_type": "on_use",
            "conditions": [{"type": "quantum_flux", "value": "42"}],
            "effects": [],
        })
        issue = only(validator.validate(), "unknown_condition_type")
        assert issue["severity"] == "warning"

    def test_unknown_effect_type(self, graph, validator):
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {
            "trigger_type": "on_use",
            "effects": [{"type": "summon_cthulhu", "params": {}}],
        })
        assert only(validator.validate(), "unknown_effect_type")

    def test_unknown_trigger_type(self, graph, validator):
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {
            "trigger_type": "on_wibble",
            "effects": [],
        })
        assert only(validator.validate(), "unknown_trigger_type")

    def test_save_sub_effects_validated(self, graph, validator):
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {
            "trigger_type": "on_use",
            "effects": [{"type": "save", "params": {
                "stat": "WIS", "dc": 12,
                "on_fail": [{"type": "set_state", "params": {"node_id": "way_missing", "state": "open"}}],
                "on_success": [{"type": "message", "params": {"message": "ok"}}],
            }}],
        })
        issue = only(validator.validate(), "missing_effect_node")
        assert issue["target_node_id"] == "way_missing"

    def test_clean_trigger_no_issues(self, graph, validator):
        item = add_item(graph)
        graph.add_node(Node(id="area_main", type="area", name="Main Hall", properties={}))
        graph.add_node(Node(id="item_torch", type="item", name="torch", properties={"tags": ["lit"]}))
        add_trigger(graph, item.id, "trigger_item_button_18_on_use_1_2", {
            "trigger_type": "on_use",
            "conditions": [{"type": "has_tag", "value": ["lit"]}],
            "effects": [
                {"type": "message", "params": {"message": "click"}},
                {"type": "teleport", "params": {"area": "Main Hall"}},
                {"type": "set_state", "params": {"node_id": "self", "state": "on"}},
            ],
        })
        assert validator.validate() == []


class TestEmptyTriggerWarnings:
    def test_trigger_with_no_effects(self, graph, validator):
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {"trigger_type": "on_use", "effects": []})
        issue = only(validator.validate(), "empty_trigger")
        assert issue["severity"] == "warning"

    def test_message_effect_with_empty_text(self, graph, validator):
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {
            "trigger_type": "on_use",
            "effects": [{"type": "message", "params": {"message": "  "}}],
        })
        issue = only(validator.validate(), "empty_effect_message")
        assert issue["severity"] == "warning"

    def test_message_effect_with_success_message_clean(self, graph, validator):
        item = add_item(graph)
        add_trigger(graph, item.id, "trigger_1", {
            "trigger_type": "on_examine",
            "effects": [{"type": "message", "params": {
                "message": "",
                "success_message": "titled The Valerius Family, dated 1583.",
            }}],
        })
        assert not [i for i in validator.validate() if i["code"] == "empty_effect_message"]


class TestWayAuthoringWarnings:
    def test_way_missing_all_fields(self, graph, validator):
        way = add_way(graph)
        graph.add_node(Node(id="area_a", type="area", name="A", properties={}))
        graph.add_node(Node(id="area_b", type="area", name="B", properties={}))
        graph.add_edge(Edge(source="area_a", target=way.id, type="connection", properties={"direction": "north"}))
        graph.add_edge(Edge(source=way.id, target="area_b", type="connection", properties={}))
        codes = {i["code"] for i in validator.validate()}
        assert {"way_missing_description", "way_missing_pass_message",
                "way_missing_cardinal", "way_missing_view_direction"} <= codes

    def test_way_with_fields_clean(self, graph, validator):
        way = add_way(graph)
        way.properties = {
            "description": "a heavy oak door",
            "pass_message": "you push it open",
        }
        graph.add_node(Node(id="area_a", type="area", name="A", properties={}))
        graph.add_node(Node(id="area_b", type="area", name="B", properties={}))
        graph.add_edge(Edge(source="area_a", target=way.id, type="connection",
                            properties={"direction": "north", "cardinal": "north",
                                        "visible_in_direction": "south"}))
        # Reverse "enter" edges only carry a direction — must not warn
        # (cardinal/view live on the area→way edges, not here).
        graph.add_edge(Edge(source=way.id, target="area_b", type="connection",
                            properties={"direction": "enter"}))
        assert not [i for i in validator.validate() if i["code"].startswith("way_missing")]


class TestMechanicalTagWarnings:
    def test_mechanical_tag_missing_props(self, graph, validator):
        graph.add_node(Node(id="item_lamp", type="item", name="Lamp",
                            properties={"tags": ["light_source", "toggleable"]}))
        issues = validator.validate()
        mech = [i for i in issues if i["code"] == "mechanical_tag_missing_props"]
        codes = {i["message"].split(" has mechanical tag '")[1].split("'")[0] for i in mech}
        assert codes == {"light_source", "toggleable"}

    def test_mechanical_tag_with_values_clean(self, graph, validator):
        graph.add_node(Node(id="item_lamp", type="item", name="Lamp",
                            properties={"tags": ["light_source"], "light_level": "dim",
                                        "current_state": "on"}))
        assert not [i for i in validator.validate() if i["code"] == "mechanical_tag_missing_props"]


class TestLibrarySyncWarnings:
    def test_library_entry_missing(self, graph, validator):
        graph.add_node(Node(id="item_sword", type="item", name="Sword",
                            properties={"tags": [], "library_id": "sword_v1"}))
        issue = only(validator.validate(), "library_entry_missing")
        assert issue["severity"] == "warning"

    def test_library_mismatch_detected(self, graph, validator, tmp_path):
        lib = tmp_path / "items"
        lib.mkdir()
        (lib / "torch.json").write_text(
            '{"id": "torch", "name": "Torch", "description": "a torch", '
            '"actions": "examine,take", "tags": ["light_source"], '
            '"light_level": "dim"}', encoding="utf-8")
        graph.add_node(Node(id="item_torch", type="item", name="Old Name",
                            properties={"tags": ["light_source"], "library_id": "torch",
                                        "actions": ["examine", "take"], "light_level": "bright"}))
        issue = only(validator.validate(), "library_mismatch")
        assert "name" in issue["message"] and "light_level" in issue["message"]

    def test_in_sync_item_clean(self, graph, validator, tmp_path):
        lib = tmp_path / "items"
        lib.mkdir()
        (lib / "torch.json").write_text(
            '{"name": "Torch", "description": "a torch", "actions": "examine,take", '
            '"tags": ["light_source"], "light_level": "dim"}', encoding="utf-8")
        graph.add_node(Node(id="item_torch", type="item", name="Torch",
                            properties={"tags": ["light_source"], "library_id": "torch",
                                        "actions": ["examine", "take"], "light_level": "dim",
                                        "description": "a torch"}))
        assert not [i for i in validator.validate() if i["code"].startswith("library_")]
