"""Tests for template variants and override tracking (task-290).

Tests engine/sync.py and routes/library_ops.py integration for:
1. resolve_template: inheritance (parent_template), variants map, deep merge.
2. link & template_ref: flat library_id + structured template_ref normalization.
3. override_fields & syncable_fields: union of locked_fields and overrides.
4. break_template_link: flattening overrides into node properties.
5. Live refresh integration: refreshing nodes with variants and overrides.
"""
import pytest
from engine import sync
from graph import Node
from app import create_app
import tempfile
import json
from pathlib import Path


def test_resolve_template_base():
    registry = {
        "lab_area": {
            "name": "Laboratory",
            "description": "A high-tech testing lab.",
            "tags": ["interior", "clean"],
        }
    }
    resolved = sync.resolve_template(registry, "lab_area")
    assert resolved is not None
    assert resolved["name"] == "Laboratory"
    assert resolved["description"] == "A high-tech testing lab."
    assert resolved["tags"] == ["interior", "clean"]


def test_resolve_template_with_parent():
    registry = {
        "base_room": {
            "name": "Base Room",
            "description": "A generic room.",
            "environment": {"lighting": "normal", "temperature": 20},
            "tags": ["indoor"],
        },
        "cold_storage": {
            "parent_template": "base_room",
            "name": "Cold Storage",
            "environment": {"temperature": -5},
            "tags": ["freezer"],
        }
    }
    resolved = sync.resolve_template(registry, "cold_storage")
    assert resolved is not None
    assert resolved["name"] == "Cold Storage"
    assert resolved["description"] == "A generic room."
    # Dicts merge key by key
    assert resolved["environment"] == {"lighting": "normal", "temperature": -5}
    # Lists replace rather than concatenate
    assert resolved["tags"] == ["freezer"]
    # Authoring metadata stripped
    assert "parent_template" not in resolved


def test_resolve_template_variants():
    registry = {
        "door_way": {
            "name": "Door",
            "current_state": "closed",
            "pass_message": "You step through the door.",
            "variants": {
                "open_door": {
                    "name": "Open Door",
                    "current_state": "open",
                },
                "locked_door": {
                    "name": "Reinforced Locked Door",
                    "current_state": "locked",
                    "tags": ["heavy", "locked"],
                }
            }
        }
    }
    # Base
    base = sync.resolve_template(registry, "door_way")
    assert base["current_state"] == "closed"
    assert "variants" not in base

    # Variant: open_door
    open_var = sync.resolve_template(registry, "door_way", variant="open_door")
    assert open_var is not None
    assert open_var["name"] == "Open Door"
    assert open_var["current_state"] == "open"
    assert open_var["pass_message"] == "You step through the door."
    assert "variants" not in open_var

    # Variant: locked_door
    locked_var = sync.resolve_template(registry, "door_way", variant="locked_door")
    assert locked_var is not None
    assert locked_var["name"] == "Reinforced Locked Door"
    assert locked_var["current_state"] == "locked"
    assert locked_var["tags"] == ["heavy", "locked"]

    # Unknown variant returns None
    assert sync.resolve_template(registry, "door_way", variant="missing_var") is None


def test_resolve_template_cycle_guard():
    registry = {
        "cycle_a": {"parent_template": "cycle_b", "name": "A"},
        "cycle_b": {"parent_template": "cycle_a", "name": "B"},
    }
    # Must terminate without infinite loop
    resolved = sync.resolve_template(registry, "cycle_a")
    assert resolved is not None


def test_link_and_template_ref_normalization():
    node = Node(id="test_node", type="item", name="Dagger")
    node.properties = {}

    # Initial state: not linked
    assert not sync.is_linked(node)
    ref = sync.template_ref(node)
    assert ref["library_id"] == ""
    assert ref["variant"] == ""
    assert ref["overrides"] == {}

    # Link with variant and overrides
    sync.link(node, "iron_dagger", variant="serrated", overrides={"weight": 1.5, "damage": 8})
    assert sync.is_linked(node)
    assert node.properties["library_id"] == "iron_dagger"
    assert node.properties["template_ref"] == {
        "variant": "serrated",
        "overrides": {"weight": 1.5, "damage": 8},
    }

    # template_ref returns normalized dict
    ref = sync.template_ref(node)
    assert ref["library_id"] == "iron_dagger"
    assert ref["variant"] == "serrated"
    assert ref["overrides"] == {"weight": 1.5, "damage": 8}


def test_override_fields_and_syncable_fields():
    node = Node(id="item_sword", type="item", name="Iron Sword")
    node.properties = {
        "library_id": "iron_sword",
        "locked_fields": ["description"],
        "template_ref": {
            "variant": "tempered",
            "linked_fields": ["name", "description", "damage", "weight"],
            "overrides": {"damage": 12},
        }
    }

    # override_fields unions locked_fields and template_ref.overrides
    overrides = sync.override_fields(node)
    assert "description" in overrides
    assert "damage" in overrides

    # syncable_fields respects linked_fields whitelist minus override_fields
    syncable = sync.syncable_fields(node)
    assert "name" in syncable
    assert "weight" in syncable
    assert "description" not in syncable
    assert "damage" not in syncable
    assert "defense" not in syncable  # not in linked_fields


def test_break_template_link_flattens_overrides():
    node = Node(id="item_armor", type="item", name="Leather Vest")
    node.properties = {
        "library_id": "leather_vest",
        "defense": 2,
        "template_ref": {
            "variant": "reinforced",
            "overrides": {"defense": 5, "description": "Custom patched vest."},
        }
    }

    report = sync.break_template_link(node)
    assert report["was_linked"] is True
    assert report["template_id"] == "leather_vest"
    assert report["variant"] == "reinforced"
    assert "defense" in report["flattened_overrides"]
    assert "description" in report["flattened_overrides"]

    # Flattened onto node properties
    assert node.properties["defense"] == 5
    assert node.properties["description"] == "Custom patched vest."
    # Link markers removed
    assert "library_id" not in node.properties
    assert "template_ref" not in node.properties
    assert node.properties["template_broken_from"] == "leather_vest"
    assert not sync.is_linked(node)


def test_refresh_item_with_variant_and_overrides():
    tmpdir = tempfile.mkdtemp()
    try:
        app = create_app({'TESTING': True, 'DATA_DIR': tmpdir})
        client = app.test_client()

        # Authored library item with variants
        lib_dir = Path(tmpdir) / 'library' / 'items'
        lib_dir.mkdir(parents=True, exist_ok=True)
        with open(lib_dir / 'potion_flask.json', 'w', encoding='utf-8') as f:
            json.dump({
                "id": "potion_flask",
                "name": "Potion Flask",
                "description": "A glass flask.",
                "weight": 0.5,
                "uses": 1,
                "variants": {
                    "health_potion": {
                        "name": "Health Potion",
                        "description": "Red bubbling liquid.",
                        "tags": ["potion", "healing"],
                    }
                }
            }, f)

        # Graph node linked to the health_potion variant, with weight overridden
        node = Node(id="item_flask_1", type="item", name="Flask")
        node.properties = {
            "library_id": "potion_flask",
            "weight": 1.2,
            "template_ref": {
                "variant": "health_potion",
                "overrides": {"weight": 1.2},
            }
        }
        app.world.graph.add_node(node)

        # Refresh
        resp = client.post('/api/library/refresh-to-world', json={
            "node_id": "item_flask_1"
        })
        assert resp.status_code == 200

        # Variant properties were applied
        assert node.name == "Health Potion"
        assert node.properties["description"] == "Red bubbling liquid."
        assert "healing" in node.properties.get("tags", [])
        # Overridden field was preserved (not reset to 0.5)
        assert node.properties["weight"] == 1.2

        # Break link endpoint
        break_resp = client.post('/api/library/break-template-link', json={
            "node_id": "item_flask_1"
        })
        assert break_resp.status_code == 200
        assert break_resp.get_json()["status"] == "unlinked"
        assert "library_id" not in node.properties
        assert "template_ref" not in node.properties
        assert node.properties["weight"] == 1.2
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
