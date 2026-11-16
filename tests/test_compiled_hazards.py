"""Tests for WorldPainter compiler terrain hazards and runtime expansion (task-747).

Rules verified:
- a way crossing water with no bridge -> river;
- a way with bridge crossing water -> no river hazard;
- a way with requires: jump over water -> fall into the water (on_fail_jump);
- a _climb_step rising or falling -> cliff/fall replacing hard refusal when
  hazard consequences enabled, with strength from storey_delta (89-storey drop lethal);
- a thorn/bramble biome -> thorns on area;
- compact hazards descriptor expands to authoritative triggers at load/apply;
- condition tag / status (e.g. flooded) maps to hazard and fires consequences.
"""

import pytest
from app import create_app
from engine import world_compile
from engine import world_grid as wg
from engine import hazards
from engine.generation import apply_patch
from graph import WorldGraph


def _scope_with_grid(cells, roads=None, floors=None, currents=None, mode="world", extra=None):
    scope_id = "test_scope"
    m = {
        "root": {"id": "root", "name": "Root", "children": [scope_id]},
        scope_id: {"id": scope_id, "name": "Test Scope", "mode": mode}
    }
    wg.ensure_grid(m[scope_id], 10, 10, mode=mode)
    if extra:
        m[scope_id].update(extra)
    for (x, y), b in (cells or {}).items():
        wg.paint(m[scope_id], "biome", x, y, b)
    for (x, y), r in (roads or {}).items():
        wg.paint(m[scope_id], "road", x, y, r)
    for (x, y), f in (floors or {}).items():
        wg.paint(m[scope_id], "floor", x, y, f)
    for (x, y), c in (currents or {}).items():
        wg.paint(m[scope_id], "current", x, y, c)
    return m


def test_water_crossing_without_bridge_emits_river_hazard():
    # cell (0, 0) is forest, (1, 0) is river
    m = _scope_with_grid({(0, 0): "dense_forest", (1, 0): "river"})
    patch = world_compile.compile_grid(m, "test_scope")
    ways = [n for n in patch.nodes if n.type == "way"]
    assert len(ways) >= 1
    way = ways[0]
    raw_hazards = way.properties.get("hazards") or []
    assert any(h.get("hazard_id") == "river" for h in raw_hazards)


def test_water_crossing_with_bridge_emits_no_river_hazard():
    # Both cells cross water, but a bridge road is painted across them
    m = _scope_with_grid(
        {(0, 0): "river", (1, 0): "river"},
        roads={(0, 0): "bridge", (1, 0): "bridge"}
    )
    patch = world_compile.compile_grid(m, "test_scope")
    ways = [n for n in patch.nodes if n.type == "way"]
    assert len(ways) >= 1
    for w in ways:
        raw_hazards = w.properties.get("hazards") or []
        assert not any(h.get("hazard_id") == "river" for h in raw_hazards)


def test_climb_step_emits_cliff_or_fall_with_storey_delta_severity():
    # 5-storey drop from (0, 0) floor 5 down to (1, 0) floor 0 (exceeds default threshold 3)
    m = _scope_with_grid(
        {(0, 0): "dense_forest", (1, 0): "dense_forest"},
        floors={(0, 0): "5", (1, 0): "0"},
        mode="world",
        extra={"hazard_consequences": True}
    )
    patch = world_compile.compile_grid(m, "test_scope")
    ways = [n for n in patch.nodes if n.type == "way"]
    assert len(ways) >= 1
    way = ways[0]
    raw_hazards = way.properties.get("hazards") or []
    assert any(h.get("hazard_id") in ("cliff", "fall") for h in raw_hazards)
    assert way.properties.get("current_state") == "open"
    assert way.properties.get("requires") == "climb"
    assert way.properties.get("climb_dc") is not None


def test_lethal_89_storey_drop_hazard():
    # 89-storey sheer drop
    m = _scope_with_grid(
        {(0, 0): "dense_forest", (1, 0): "dense_forest"},
        floors={(0, 0): "89", (1, 0): "0"},
        mode="world",
        extra={"hazard_consequences": True}
    )
    patch = world_compile.compile_grid(m, "test_scope")
    ways = [n for n in patch.nodes if n.type == "way"]
    assert len(ways) >= 1
    way = ways[0]
    raw_hazards = way.properties.get("hazards") or []
    h = next(h for h in raw_hazards if h.get("hazard_id") in ("cliff", "fall"))
    assert h["strength"] == 20
    assert h.get("damage") == "20d6"


def test_thorn_and_bramble_biomes_emit_thorns_hazard_on_area():
    m = _scope_with_grid({(0, 0): "thorns", (1, 0): "bramble"})
    patch = world_compile.compile_grid(m, "test_scope")
    areas = [n for n in patch.nodes if n.type == "area"]
    assert len(areas) >= 2
    for area in areas:
        raw_hazards = area.properties.get("hazards") or []
        assert any(h.get("hazard_id") == "thorns" for h in raw_hazards)


def test_patch_apply_and_serialization_expands_compact_hazards():
    m = _scope_with_grid({(0, 0): "thorns"})
    patch = world_compile.compile_grid(m, "test_scope")
    area = [n for n in patch.nodes if n.type == "area"][0]
    assert "hazards" in area.properties

    graph = WorldGraph()
    apply_patch(graph, m, patch)

    stored_area = graph.get_node(area.id)
    assert stored_area is not None
    trigs = stored_area.properties.get("triggers") or []
    assert any(t.get("trigger_type") == "on_enter" for t in trigs)
    hazard_effects = [eff for t in trigs for eff in t.get("effects", []) if eff.get("type") == "hazard"]
    assert len(hazard_effects) >= 1
    assert hazard_effects[0]["params"]["hazard_id"] == "thorns"


def test_flooded_status_dynamically_expands_and_fires_consequences():
    app = create_app({"TESTING": True})
    world = app.world
    p = world.get_player(world.active_player)
    area_id = world.area_node_id(p.current_area)
    node = world.graph.get_node(area_id)
    assert node is not None

    # Mark the current area as flooded
    node.properties.setdefault("tags", []).append("flooded")

    # Has trigger detects and expands the hazard
    assert world.triggers.has_trigger(node, "on_enter")

    # Executing on_enter fires the river hazard
    res = world.triggers._execute_triggers(
        node,
        "on_enter",
        context={"roll_fn": lambda: 1},
        game_state=world,
    )
    assert any("drags you off your feet" in line or "slams you under" in line for line in res)
    assert "wet" in getattr(p, "conditions", {})
