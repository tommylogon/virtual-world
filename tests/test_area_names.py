"""Tests for area display names and clean way messages (task-638, task-624).

Verifies that compiled areas emit a human-facing display_name property,
way pass_messages strip internal grid coordinates, and repeated bridge
structures carry distinct contextual display names.
"""

import json
from pathlib import Path

from engine import matching
from engine import world_grid as wg
from engine import world_compile


def test_compiled_area_emits_display_name():
    scope_id = "test_display_name_scope"
    m = {
        "root": {"id": "root", "name": "Root", "children": [scope_id]},
        scope_id: {"id": scope_id, "name": "Test Scope", "mode": "settlement"}
    }
    wg.ensure_grid(m[scope_id], 4, 4, mode="settlement")
    wg.paint(m[scope_id], "biome", 0, 0, "tavern")
    wg.paint(m[scope_id], "biome", 1, 0, "cobblestone_road")

    patch = world_compile.compile_grid(m, scope_id)
    areas = [n for n in patch.nodes if n.type == "area"]
    assert len(areas) >= 2

    for a in areas:
        props = a.properties or {}
        assert "display_name" in props, f"area {a.id} must carry display_name"
        assert props["display_name"], f"area {a.id} display_name must not be empty"
        assert "(" not in props["display_name"], f"display_name must not contain coordinates: {props['display_name']}"


def test_compiled_way_pass_message_cleans_grid_coordinates():
    scope_id = "test_clean_pass_msg"
    m = {
        "root": {"id": "root", "name": "Root", "children": [scope_id]},
        scope_id: {"id": scope_id, "name": "Test Scope", "mode": "world"}
    }
    wg.ensure_grid(m[scope_id], 4, 4, mode="world")
    wg.paint(m[scope_id], "biome", 0, 0, "clearing")
    wg.paint(m[scope_id], "biome", 1, 0, "dense_forest")

    patch = world_compile.compile_grid(m, scope_id)
    ways = [n for n in patch.nodes if n.type == "way"]
    assert len(ways) >= 1

    for w in ways:
        msg = w.properties.get("pass_message") or ""
        assert msg, f"way {w.id} must have a pass_message"
        assert "(test_clean_pass_msg" not in msg, f"pass_message must not leak scope coordinates: {msg}"


def test_kraktooth_bridge_areas_have_distinct_display_names():
    scenario_path = Path("data/scenarios/kraktooth_goblin_camp.json")
    with open(scenario_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    nodes = data.get("graph", {}).get("nodes", {})
    bridge_areas = [
        n for n in nodes.values()
        if n.get("type") == "area" and "bridge" in n.get("name", "").lower()
    ]
    assert len(bridge_areas) >= 7, f"expected at least 7 bridge areas, found {len(bridge_areas)}"

    display_names = []
    for ba in bridge_areas:
        props = ba.get("properties") or {}
        dn = props.get("display_name")
        assert dn, f"bridge area {ba.get('id')} must carry an authored display_name"
        assert "(" not in dn and ")" not in dn, f"bridge display_name must not embed coordinates: {dn}"
        display_names.append(dn)

    # Verify that bridge display names are distinct and not identical repetitions of "Bridge"
    unique_names = set(display_names)
    assert len(unique_names) == len(display_names), (
        f"all bridge display names must be unique and contextualised, got duplicates: {display_names}"
    )
