"""Tests for child-scope procedural generators and corner door compilation (task-884).

Covers settlement, ruin/dungeon, and wilderness child scope generators,
as well as the 45-degree chamfered corner door compilation rule.
"""

from engine import world_grid as wg
from engine import world_compile
from engine.scope_generators import (
    GenerationConfig,
    get_generator,
    SettlementGenerator,
    RuinDungeonGenerator,
    WildernessGenerator,
)


def _make_scope(width: int, height: int, layers: dict, mode: str = "settlement") -> dict:
    scope_id = "test_child_scope"
    m = {
        "root": {"id": "root", "name": "Root", "children": [scope_id]},
        scope_id: {"id": scope_id, "name": "Test Child Scope", "mode": mode}
    }
    wg.ensure_grid(m[scope_id], width, height, mode=mode)
    m[scope_id]["layers"] = layers
    return m


def test_settlement_generator():
    gen = get_generator("settlement")
    assert isinstance(gen, SettlementGenerator)

    config = GenerationConfig(seed=123, budget=50000)
    result = gen.generate((16, 16), {}, config)

    assert result.cells_painted > 0
    assert "biome" in result.layers
    assert "road" in result.layers
    assert "town_square" in result.landmarks_placed

    # Compile the generated layers through world compiler
    m = _make_scope(16, 16, result.layers, mode="settlement")
    patch = world_compile.compile_grid(m, "test_child_scope")
    areas = [n for n in patch.nodes if n.type == "area"]
    ways = [n for n in patch.nodes if n.type == "way"]

    assert len(areas) > 5
    assert len(ways) > 5


def test_ruin_dungeon_generator_mst_and_catastrophe():
    gen = RuinDungeonGenerator()
    config_collapse = GenerationConfig(seed=42, catastrophe="collapse", decay_rate=0.2)
    res_collapse = gen.generate((20, 20), {}, config_collapse)

    assert "grand_gate" in res_collapse.landmarks_placed
    assert "great_forge" in res_collapse.landmarks_placed
    assert res_collapse.report["catastrophe"] == "collapse"
    assert res_collapse.report["decayed_cells"] > 0
    assert any(b == "dwarven_collapsed_shaft" for b in res_collapse.layers["biome"].values())

    # Flood catastrophe
    config_flood = GenerationConfig(seed=99, catastrophe="flood", decay_rate=0.2)
    res_flood = gen.generate((20, 20), {}, config_flood)
    assert res_flood.report["catastrophe"] == "flood"
    assert any(b == "deep_water" for b in res_flood.layers["biome"].values())

    # Compile ruin through world compiler
    m = _make_scope(20, 20, res_collapse.layers, mode="interior")
    patch = world_compile.compile_grid(m, "test_child_scope")
    areas = [n for n in patch.nodes if n.type == "area"]
    assert len(areas) > 0


def test_wilderness_generator_channel_and_buffers():
    gen = WildernessGenerator()
    config = GenerationConfig(seed=777)
    result = gen.generate((15, 15), {"ford": (7, 7)}, config)

    assert "river" in result.layers["biome"].values()
    assert "dense_forest" in result.layers["biome"].values()
    assert "ford" in result.landmarks_placed

    # Verify world compilation
    m = _make_scope(15, 15, result.layers, mode="world")
    patch = world_compile.compile_grid(m, "test_child_scope")
    areas = [n for n in patch.nodes if n.type == "area"]
    assert len(areas) > 0


def test_corner_door_compilation_with_chamfer_rule():
    # Diagonal door at (1, 1) joining tavern at (0, 0) and warehouse at (2, 2).
    # Flank 1: (1, 0) and (2, 1) are solid walls.
    # Flank 2: (0, 1) and (1, 2) are open space or other cells.
    painted_with_solid_flank = {
        (0, 0): "tavern",
        (1, 0): "wall",      # flank 1a
        (2, 1): "wall",      # flank 1b
        (1, 1): "door",      # diagonal chamfered door
        (2, 2): "warehouse",
    }
    scope_id = "test_chamfer"
    m_valid = {
        "root": {"id": "root", "name": "Root", "children": [scope_id]},
        scope_id: {"id": scope_id, "name": "Chamfer Scope", "mode": "settlement"}
    }
    wg.ensure_grid(m_valid[scope_id], 5, 5, mode="settlement")
    for (x, y), b in painted_with_solid_flank.items():
        wg.paint(m_valid[scope_id], "biome", x, y, b)

    patch_valid = world_compile.compile_grid(m_valid, scope_id)
    areas_valid = {tuple(a.properties["cell"].values()): a
                   for a in patch_valid.nodes if a.type == "area"}
    assert (0, 0) in areas_valid and (2, 2) in areas_valid

    def connected(patch, a_cell, b_cell):
        a_id = areas_valid[a_cell].id
        b_id = areas_valid[b_cell].id
        return any({w.properties["area_from_id"], w.properties["area_to_id"]} == {a_id, b_id}
                   for w in patch.nodes if w.type == "way")

    assert connected(patch_valid, (0, 0), (2, 2)), "chamfered corner door joins diagonal rooms"

    # Counter-test: without solid wall flanks, diagonal door does NOT join the rooms
    painted_without_solid_flank = {
        (0, 0): "tavern",
        (1, 0): "clearing",  # not solid!
        (2, 1): "clearing",  # not solid!
        (1, 1): "door",
        (2, 2): "warehouse",
    }
    m_invalid = {
        "root": {"id": "root", "name": "Root", "children": [scope_id]},
        scope_id: {"id": scope_id, "name": "Chamfer Scope", "mode": "settlement"}
    }
    wg.ensure_grid(m_invalid[scope_id], 5, 5, mode="settlement")
    for (x, y), b in painted_without_solid_flank.items():
        wg.paint(m_invalid[scope_id], "biome", x, y, b)

    patch_invalid = world_compile.compile_grid(m_invalid, scope_id)
    door_ways = [w for w in patch_invalid.nodes if w.type == "way" and w.properties.get("kind") == "door"]
    assert len(door_ways) == 0, "door without solid wall flanks does not mint accidental diagonal way"
