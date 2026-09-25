"""Grid→graph compiler (task-496) and the generation-patch contract (task-398)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from graph import EDGE_CONNECTION, Node, WorldGraph
from engine import generation, world_compile, world_grid as wg, world_scopes


def _manifest(biomes=None, *, w=2, h=2, region_merge_scope="wild"):
    """A manifest with one gridded scope and a painted biome layer."""
    m = {"root": {"id": "root", "name": "Root", "children": [region_merge_scope]},
         region_merge_scope: {"id": region_merge_scope, "name": "Wild"}}
    wg.ensure_grid(m[region_merge_scope], w, h, mode="world")
    if biomes:
        for (x, y), biome in biomes.items():
            wg.paint(m[region_merge_scope], "biome", x, y, biome)
    return m


FOUR = {(0, 0): "sparse_forest", (1, 0): "dense_forest",
        (0, 1): "hills", (1, 1): "farmland"}


# ───────────────────────────── contract ──────────────────────────────────


def test_apply_patch_materializes_once_and_sets_scope_state():
    m = _manifest(FOUR)
    patch = world_compile.compile_grid(m, "wild")
    g = WorldGraph()
    report = generation.apply_patch(g, m, patch)

    assert m["wild"]["state"] == "materialized"
    assert set(m["wild"]["area_ids"]) == set(report.area_ids)
    for area_id in report.area_ids:
        node = g.get_node(area_id)
        assert node is not None and node.type == "area"
        assert node.properties["generated"]["scope_id"] == "wild"


def test_second_apply_is_rejected_and_a_manual_edit_survives():
    m = _manifest(FOUR)
    patch = world_compile.compile_grid(m, "wild")
    g = WorldGraph()
    generation.apply_patch(g, m, patch)

    area_id = sorted(patch.area_scope_assignments)[0]
    g.get_node(area_id).properties["note"] = "hand-edited"

    with pytest.raises(ValueError):
        generation.apply_patch(g, m, patch)
    assert g.get_node(area_id).properties["note"] == "hand-edited"


def test_apply_refuses_to_clobber_a_hand_authored_node():
    m = _manifest(FOUR)
    patch = world_compile.compile_grid(m, "wild")
    g = WorldGraph()
    area_id = sorted(patch.area_scope_assignments)[0]
    g.add_node(Node(id=area_id, type="area", name="Hand Authored"))
    with pytest.raises(ValueError):
        generation.apply_patch(g, m, patch)


# ───────────────────────────── compiler ──────────────────────────────────


def test_compile_makes_an_area_per_cell_and_a_way_per_adjacency():
    m = _manifest(FOUR)
    patch = world_compile.compile_grid(m, "wild")
    areas = [n for n in patch.nodes if n.type == "area"]
    ways = [n for n in patch.nodes if n.type == "way"]
    assert len(areas) == 4
    assert len(ways) == 6            # 2x2: four orthogonal + two diagonal edges
    assert len(patch.edges) == len(ways) * 4   # four connection edges each


def test_compiled_areas_and_ways_carry_the_expected_properties():
    m = _manifest(FOUR)
    patch = world_compile.compile_grid(m, "wild")
    area = next(n for n in patch.nodes if n.type == "area")
    assert area.properties["world_scope_id"] == "wild"
    assert area.properties["floor"] == "dirt"
    assert "forest" in area.properties["tags"]
    assert isinstance(area.properties["environment"], dict)
    assert area.properties["description"].endswith(".")

    way = next(n for n in patch.nodes if n.type == "way")
    for key in ("area_from", "area_to", "area_from_id", "area_to_id",
                "direction", "see_through", "floor"):
        assert key in way.properties, key
    conns = [e for e in patch.edges
             if e.source == way.id and e.type == EDGE_CONNECTION]
    assert len(conns) == 2   # the way points at both areas

    # Every connection edge carries the map-layout cardinal as well as the
    # direction, so the way inspector's compass and the cardinal map fallback
    # see the painter's 8-wind value (build_exits_for_area reads `cardinal`).
    for edge in patch.edges:
        if edge.type != EDGE_CONNECTION:
            continue
        assert edge.properties.get("cardinal") == edge.properties.get("direction")
    area_side = next(e for e in patch.edges
                     if e.source.startswith("area_") and e.target == way.id)
    assert area_side.properties["cardinal"] in world_compile.DIRECTIONS


def test_compiled_nodes_carry_canvas_positions_from_the_painted_cells():
    m = _manifest(FOUR)
    patch = world_compile.compile_grid(m, "wild")
    unit = world_compile.CELL_CANVAS_UNITS
    area = next(n for n in patch.nodes if n.id == "area_wild_1_0")
    assert area.properties["cell"] == {"x": 1, "y": 0}
    assert area.properties["x"] == 1 * unit
    assert area.properties["y"] == 0
    for way in (n for n in patch.nodes if n.type == "way"):
        assert "x" in way.properties and "y" in way.properties


def test_descriptions_are_deterministic_and_mention_exits():
    m1 = _manifest(FOUR)
    m2 = _manifest(FOUR)
    p1 = world_compile.compile_grid(m1, "wild")
    p2 = world_compile.compile_grid(m2, "wild")
    d1 = {n.id: n.properties["description"] for n in p1.nodes if n.type == "area"}
    d2 = {n.id: n.properties["description"] for n in p2.nodes if n.type == "area"}
    assert d1 == d2
    assert any("Paths lead" in text for text in d1.values())


def test_painting_a_road_adds_the_feature_tag_and_prose():
    m = _manifest({(0, 0): "sparse_forest", (1, 0): "sparse_forest"}, w=2, h=1)
    wg.paint(m["wild"], "road", 0, 0, "road")
    patch = world_compile.compile_grid(m, "wild")
    road_area = next(n for n in patch.nodes
                     if n.type == "area" and n.id.endswith("_0_0"))
    assert "road" in road_area.properties["tags"]
    assert "road" in road_area.properties["description"].lower()


def test_region_merge_collapses_contiguous_same_biome_cells():
    m = _manifest({(0, 0): "sparse_forest", (1, 0): "sparse_forest"}, w=2, h=1)

    split = world_compile.compile_grid(m, "wild", region_merge=False)
    assert len([n for n in split.nodes if n.type == "area"]) == 2
    assert len([n for n in split.nodes if n.type == "way"]) == 1

    merged = world_compile.compile_grid(m, "wild", region_merge=True)
    assert len([n for n in merged.nodes if n.type == "area"]) == 1
    assert len([n for n in merged.nodes if n.type == "way"]) == 0


def test_region_merge_keeps_a_way_between_different_biomes():
    m = _manifest({(0, 0): "sparse_forest", (1, 0): "dense_forest"}, w=2, h=1)
    patch = world_compile.compile_grid(m, "wild", region_merge=True)
    assert len([n for n in patch.nodes if n.type == "area"]) == 2
    assert len([n for n in patch.nodes if n.type == "way"]) == 1


def test_diagonal_neighbours_are_connected():
    # 8-neighbour adjacency: a diagonal-only pair still gets a way, in the
    # diagonal compass direction.
    m = _manifest({(0, 0): "sparse_forest", (1, 1): "hills"})
    patch = world_compile.compile_grid(m, "wild")
    ways = [n for n in patch.nodes if n.type == "way"]
    assert len(ways) == 1
    assert ways[0].properties["direction"] == "southeast"
    assert not any("no exits" in note for note in patch.report.notes)


def test_distant_islands_are_linked_to_the_nearest_cell_once():
    # Two cells that touch nothing are two disconnected components; each is
    # joined to the main landmass (here, the first) by a single way in the
    # compass direction of the closest cells.
    m = _manifest({(0, 0): "sparse_forest", (0, 5): "hills"}, w=3, h=6)
    patch = world_compile.compile_grid(m, "wild")
    ways = [n for n in patch.nodes if n.type == "way"]
    assert len(ways) == 1
    assert ways[0].properties["direction"] == "north"
    assert any("linked to the nearest region" in note for note in patch.report.notes)
    assert not any("no exits" in note for note in patch.report.notes)


def test_link_islands_can_be_disabled():
    m = _manifest({(0, 0): "sparse_forest", (0, 5): "hills"}, w=3, h=6)
    patch = world_compile.compile_grid(m, "wild", link_islands=False)
    assert [n for n in patch.nodes if n.type == "way"] == []
    assert any("no exits" in note for note in patch.report.notes)


def test_a_lone_painted_cell_has_no_exits_to_link_to():
    m = _manifest({(0, 0): "sparse_forest"})
    patch = world_compile.compile_grid(m, "wild")
    assert [n for n in patch.nodes if n.type == "way"] == []
    assert any("no exits" in note for note in patch.report.notes)


def test_compile_rejects_missing_grid_and_empty_paint():
    m = {"wild": {"id": "wild", "name": "Wild"}}
    with pytest.raises(ValueError):
        world_compile.compile_grid(m, "wild")
    with pytest.raises(ValueError):
        world_compile.compile_grid(m, "ghost")

    empty = _manifest()
    with pytest.raises(ValueError):
        world_compile.compile_grid(empty, "wild")


def test_a_baked_zone_compiles_once_then_refuses():
    m = _manifest(FOUR)
    m["wild"]["paint_policy"] = world_compile.PAINT_POLICY_BAKED
    patch = world_compile.compile_grid(m, "wild")
    g = WorldGraph()
    generation.apply_patch(g, m, patch)
    with pytest.raises(ValueError):
        world_compile.compile_grid(m, "wild")


# ───────────────────────── child-scope gateways ──────────────────────────


def _town_with_inn():
    """A town grid with an inn scope placed on its (0,0) cell."""
    m = {"root": {"id": "root", "name": "Root", "children": ["town", "inn"]},
         "town": {"id": "town", "name": "Town"},
         "inn": {"id": "inn", "name": "The Inn"}}
    wg.ensure_grid(m["town"], 2, 1, mode="world")
    wg.ensure_grid(m["inn"], 1, 1, mode="town")
    for x in (0, 1):
        wg.paint(m["town"], "biome", x, 0, "sparse_forest")
    wg.paint(m["inn"], "biome", 0, 0, "sparse_forest")
    wg.place(m, "town", "inn", 0, 0)
    return m


def test_compiling_a_scope_records_its_entry_area():
    m = _town_with_inn()
    generation.apply_patch(WorldGraph(), m, world_compile.compile_grid(m, "inn"))
    assert m["inn"]["entry_area_id"] == "area_inn_0_0"
    assert m["inn"]["entry_area_name"].startswith("Sparse Forest")


def test_child_compiled_first_then_parent_emits_the_gateway():
    m = _town_with_inn()
    g = WorldGraph()
    child_patch = world_compile.compile_grid(m, "inn")
    # The parent has no compiled area yet, so the child cannot link itself.
    assert not [n for n in child_patch.nodes if n.id.startswith("way_gateway_")]
    generation.apply_patch(g, m, child_patch)

    parent_patch = world_compile.compile_grid(m, "town")
    gateways = [n for n in parent_patch.nodes if n.id.startswith("way_gateway_")]
    assert len(gateways) == 1
    gw = gateways[0]
    assert gw.properties["area_from_id"] == "area_town_0_0"
    assert gw.properties["area_to_id"] == "area_inn_0_0"
    assert gw.properties["direction"] == world_compile.GATEWAY_IN
    assert gw.properties["return_direction"] == world_compile.GATEWAY_OUT
    # The entrance sits on the parent cell it opens from.
    assert gw.properties["x"] == 0 and gw.properties["y"] == 0
    generation.apply_patch(g, m, parent_patch)
    # The parent cell remembers what it compiled to, for later reloads.
    assert m["town"]["placements"]["inn"]["area_id"] == "area_town_0_0"


def test_parent_compiled_first_then_child_emits_the_gateway():
    m = _town_with_inn()
    g = WorldGraph()
    parent_patch = world_compile.compile_grid(m, "town")
    # The child is not materialized yet, so the parent links nothing.
    assert not [n for n in parent_patch.nodes if n.id.startswith("way_gateway_")]
    generation.apply_patch(g, m, parent_patch)
    assert m["town"]["placements"]["inn"]["area_id"] == "area_town_0_0"

    child_patch = world_compile.compile_grid(m, "inn")
    gateways = [n for n in child_patch.nodes if n.id.startswith("way_gateway_")]
    assert len(gateways) == 1
    assert gateways[0].properties["area_from_id"] == "area_town_0_0"
    assert gateways[0].properties["area_to_id"] == "area_inn_0_0"


def test_gateway_appears_as_engine_exits_with_no_engine_change():
    """Apply gateways to a real VirtualWorld and read the exits dict."""
    from app import create_app
    world = create_app({"TESTING": True}).world
    m = _town_with_inn()
    generation.apply_patch(world.graph, m, world_compile.compile_grid(m, "inn"))
    generation.apply_patch(world.graph, m, world_compile.compile_grid(m, "town"))
    town_name = world.graph.get_node("area_town_0_0").name
    inn_name = world.graph.get_node("area_inn_0_0").name
    assert "in" in world.area_description.build_exits_for_area(town_name)
    assert "out" in world.area_description.build_exits_for_area(inn_name)


def test_gateway_is_walkable_in_and_out():
    m = _town_with_inn()
    g = WorldGraph()
    generation.apply_patch(g, m, world_compile.compile_grid(m, "inn"))
    generation.apply_patch(g, m, world_compile.compile_grid(m, "town"))

    gw_id = "way_gateway_town_inn"
    assert g.get_node(gw_id) is not None
    into_gateway = {e.target: e.properties["direction"]
                    for e in g.get_edges_for_source("area_town_0_0")}
    assert into_gateway[gw_id] == world_compile.GATEWAY_IN
    out_of_gateway = {e.target: e.properties["direction"]
                      for e in g.get_edges_for_source("area_inn_0_0")}
    assert out_of_gateway[gw_id] == world_compile.GATEWAY_OUT


def test_regenerating_the_parent_does_not_duplicate_the_gateway():
    m = _town_with_inn()
    g = WorldGraph()
    generation.apply_patch(g, m, world_compile.compile_grid(m, "inn"))
    generation.apply_patch(g, m, world_compile.compile_grid(m, "town"))
    generation.apply_patch(g, m, world_compile.compile_grid(m, "town"),
                           allow_regenerate=True)
    gw_ids = [nid for nid in g.nodes if nid.startswith("way_gateway_")]
    assert gw_ids == ["way_gateway_town_inn"]


def test_a_placement_on_an_unpainted_cell_does_not_link():
    m = _town_with_inn()
    wg.place(m, "town", "inn", 1, 0)   # cell (1,0) is painted, so move off it
    wg.paint(m["town"], "biome", 1, 0, None)   # erase the paint under the inn
    generation.apply_patch(WorldGraph(), m, world_compile.compile_grid(m, "inn"))
    parent_patch = world_compile.compile_grid(m, "town")
    assert not [n for n in parent_patch.nodes if n.id.startswith("way_gateway_")]
    assert "area_id" not in m["town"]["placements"]["inn"]


# ───────────────────── integration with the scope layer ──────────────────


def test_generated_ways_show_up_as_boundary_ways():
    m = _manifest(FOUR)
    patch = world_compile.compile_grid(m, "wild")
    g = WorldGraph()
    generation.apply_patch(g, m, patch)

    one_area = {"area_wild_0_0"}
    boundaries = world_scopes.boundary_ways(g, one_area)
    # (0,0) borders (1,0) east, (0,1) south and (1,1) south-east; all three
    # ways leave the one-area scope (8-neighbour adjacency).
    assert len(boundaries) == 3
    assert all(b["outside"].startswith("area_wild_") for b in boundaries)


def test_compiled_world_is_walkable_with_no_engine_change():
    """Apply a patch to a real VirtualWorld and read its exits."""
    from app import create_app
    world = create_app({"TESTING": True}).world
    m = _manifest(FOUR)
    patch = world_compile.compile_grid(m, "wild")
    generation.apply_patch(world.graph, m, patch)

    area_name = next(n.name for n in patch.nodes if n.id == "area_wild_0_0")
    exits = world.area_description.build_exits_for_area(area_name)
    assert "east" in exits      # to Dense Forest (1,0)
    assert "south" in exits     # to Hills (0,1)
