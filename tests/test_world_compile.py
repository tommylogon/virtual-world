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


def _painted(biomes=None, roads=None, elevations=None, w=6, h=3, merge=False):
    """A one-scope manifest painted across all three layers (task-496)."""
    m = _manifest(biomes or {}, w=w, h=h)
    for (x, y), value in (roads or {}).items():
        wg.paint(m["wild"], "road", x, y, value)
    for (x, y), value in (elevations or {}).items():
        wg.paint(m["wild"], "elevation", x, y, value)
    return m


def _road_area(patch, cell):
    for n in patch.nodes:
        if n.type == "area" and n.properties.get("road"):
            if n.properties["cell"] == {"x": cell[0], "y": cell[1]}:
                return n
    return None


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


# ───────────── road as a place (task-496, observer-view model) ─────────────


def test_a_road_only_cell_compiles_to_an_area():
    """A road cell is a place in its own right, not dropped for lack of a biome."""
    m = _painted(roads={(1, 1): "road"}, w=3, h=3)
    patch = world_compile.compile_grid(m, "wild")
    road_area = _road_area(patch, (1, 1))
    assert road_area is not None
    assert road_area.properties["road"] == "road"
    assert "road" in road_area.properties["tags"]
    assert road_area.name.startswith("Road")


def test_a_road_cell_replaces_its_biome_rather_than_adding_a_second_place():
    """One place per cell: the biome underneath is context, not another area."""
    m = _painted(biomes={(1, 1): "sparse_forest"},
                 roads={(1, 1): "road"}, w=3, h=3)
    patch = world_compile.compile_grid(m, "wild")
    at_cell = [n for n in patch.nodes if n.type == "area"
               and n.properties["cell"] == {"x": 1, "y": 1}]
    assert len(at_cell) == 1, "one area per cell, not a road beside a forest"
    area = at_cell[0]
    assert area.properties["road"] == "road"
    # The biome is kept as context — that is what "a road in the woods" reads.
    assert area.properties["biome"] == "sparse_forest"
    assert "forest" in area.properties["tags"]


def test_a_road_cell_is_walkable_to_its_neighbours():
    m = _painted(biomes={(0, 1): "sparse_forest", (2, 1): "sparse_forest"},
                 roads={(1, 1): "road"}, w=3, h=3)
    patch = world_compile.compile_grid(m, "wild")
    touching = [n for n in patch.nodes if n.type == "way"
                and n.properties["world_scope_id"] == "wild"
                and "area_wild_1_1" in n.id]
    assert len(touching) == 2, "the road links to both of its neighbours"


def test_region_merge_groups_roads_separately_from_the_biome_beside_them():
    m = _painted(biomes={(0, 0): "sparse_forest", (1, 0): "sparse_forest"},
                 roads={(2, 0): "road", (3, 0): "road"}, w=4, h=1)
    patch = world_compile.compile_grid(m, "wild", region_merge=True)
    areas = [n for n in patch.nodes if n.type == "area"]
    assert len(areas) == 2, "the forest and the road each merge into one place"
    road = [n for n in areas if n.properties.get("road")]
    assert len(road) == 1
    # ...and the road is still connected to the forest it runs into.
    assert any(n.type == "way" for n in patch.nodes)


def test_road_cells_need_no_biome_paint_at_all():
    m = _painted(roads={(0, 0): "road", (1, 0): "road", (2, 0): "road"}, w=3, h=1)
    patch = world_compile.compile_grid(m, "wild")
    assert len([n for n in patch.nodes if n.type == "area"]) == 3
    assert len([n for n in patch.nodes if n.type == "way"]) == 2


# ───────────────── the place classifier (task-496) ─────────────────────────


def _character(patch, cell=(2, 1)):
    """The classified character sentence for the road at *cell*."""
    area = _road_area(patch, cell)
    assert area is not None, "expected a road area at %r" % (cell,)
    body = area.properties["description"].split(". ", 1)[1]
    return body.split(". It runs")[0].rstrip(".")


def test_road_between_woods_reads_as_a_road_in_the_woods():
    m = _painted(biomes={(2, 0): "sparse_forest", (2, 2): "sparse_forest"},
                 roads={(2, 1): "road"})
    assert _character(world_compile.compile_grid(m, "wild")) == "A road in the woods"


def test_road_beside_woods_reads_as_along_the_forest_line():
    m = _painted(biomes={(2, 0): "sparse_forest"}, roads={(2, 1): "road"})
    character = _character(world_compile.compile_grid(m, "wild"))
    assert character == "A road along the forest line, the trees close on the north"


def test_road_between_cliffs_reads_as_a_narrow_path():
    m = _painted(biomes={(2, 0): "cliff", (2, 2): "cliff"}, roads={(2, 1): "road"})
    assert _character(world_compile.compile_grid(m, "wild")) == (
        "A narrow path, rockface rising on one side and dropping away on the other")


def test_road_with_one_cliff_reads_as_cut_along_its_foot():
    m = _painted(biomes={(2, 0): "cliff"}, roads={(2, 1): "road"})
    character = _character(world_compile.compile_grid(m, "wild"))
    assert character == "A road cut along the foot of the rockface to the north"


def test_road_over_water_and_beside_water_differ():
    over = _painted(biomes={(2, 0): "lake", (2, 2): "lake"}, roads={(2, 1): "road"})
    assert _character(world_compile.compile_grid(over, "wild")) == (
        "A road carried over the water")
    beside = _painted(biomes={(2, 2): "river"}, roads={(2, 1): "road"})
    assert _character(world_compile.compile_grid(beside, "wild")) == (
        "A road running beside the water to the south")


def test_an_isolated_road_reads_as_open_country():
    m = _painted(roads={(2, 1): "road"})
    assert _character(world_compile.compile_grid(m, "wild")) == (
        "A road across open country")


def test_elevation_turns_a_gentle_slope_into_a_rockface():
    """Prose only — a large floor step reads as a cliff (traversal is task-525)."""
    painted = {(2, 1): "farmland", (2, 2): "sparse_forest"}
    flat = _painted(painted, roads={(2, 1): "road"})
    assert "forest line" in _character(world_compile.compile_grid(flat, "wild"))

    steep = _painted(painted, roads={(2, 1): "road"},
                     elevations={(2, 0): "4"})
    assert "rockface" in _character(world_compile.compile_grid(steep, "wild"))

    gentle = _painted(painted, roads={(2, 1): "road"},
                      elevations={(2, 0): "1"})
    assert "forest line" in _character(world_compile.compile_grid(gentle, "wild"))


def test_road_beside_a_biome_says_a_track_runs_through_it():
    m = _painted(biomes={(2, 1): "sparse_forest"}, roads={(2, 0): "road"})
    patch = world_compile.compile_grid(m, "wild")
    forest = [n for n in patch.nodes if n.type == "area"
              and n.properties["cell"] == {"x": 2, "y": 1}][0]
    assert "A track runs through it." in forest.properties["description"]
    # The neighbour is a *road* place, so it is covered by that line alone and
    # must not also be named as the biome hiding underneath it.
    assert "to the north" not in forest.properties["description"]


def test_a_road_neighbour_is_named_for_the_road_not_the_biome_under_it():
    """A neighbour's label is what its place IS: a road cell is a road place."""
    m = _painted(biomes={(1, 1): "sparse_forest"}, roads={(0, 1): "road"})
    patch = world_compile.compile_grid(m, "wild")
    forest = [n for n in patch.nodes if n.type == "area"
              and n.properties["cell"] == {"x": 1, "y": 1}][0]
    body = forest.properties["description"]
    assert "A track runs through it." in body
    assert "Road" not in body and "road" not in body
    # …and the road place itself is named for the road, not the forest.
    road = _road_area(patch, (0, 1))
    assert road.name.startswith("Road")


def test_a_biome_neighbour_is_still_named_when_it_is_not_a_road():
    m = _painted(biomes={(1, 1): "farmland", (0, 1): "hills"})
    patch = world_compile.compile_grid(m, "wild")
    farm = [n for n in patch.nodes if n.type == "area"
            and n.properties["cell"] == {"x": 1, "y": 1}][0]
    assert "Hills to the west." in farm.properties["description"]


# ─────────────── feature entry vocabulary (task-496) ───────────────────────


def test_entry_phrases_come_from_the_placement_not_a_hardcoded_in_out():
    assert world_compile._entry_phrases("the mine", "tunnel", None)[0] == (
        "enter the tunnel")
    assert world_compile._entry_phrases("the crossing", "ford", None)[0] == (
        "wade across the ford")
    assert world_compile._entry_phrases("the gatehouse", "gate", None)[0] == (
        "pass through the gate")
    assert world_compile._entry_phrases("the mine", "bridge", None)[0] == (
        "cross the bridge")
    # A plain placement with nothing painted says what it is.
    assert world_compile._entry_phrases("Inn", None, None) == (
        "enter inn", "leave", ["in", "out"])


def test_entry_phrases_read_the_floor_step():
    assert world_compile._entry_phrases("cave", None, -3.0)[0] == "climb down into cave"
    assert world_compile._entry_phrases("cave", None, 3.0)[0] == "climb up into cave"
    assert world_compile._entry_phrases("cave", None, 1.0)[0] == "enter cave"


def test_every_entry_phrase_keeps_the_short_handles_as_aliases():
    for feature in (None, "road", "tunnel", "ford", "bridge", "gate"):
        _, _, aliases = world_compile._entry_phrases("inn", feature, 2.0)
        assert "in" in aliases and "out" in aliases, feature


def test_the_old_go_in_still_resolves_through_the_alias_tier():
    """Widening the vocabulary must not take a command away (task-496)."""
    from engine.matching import NameMatching
    m = _town_with_inn()
    g = WorldGraph()
    generation.apply_patch(g, m, world_compile.compile_grid(m, "inn"))
    generation.apply_patch(g, m, world_compile.compile_grid(m, "town"))
    matcher = NameMatching(g, lambda: None)
    town = g.get_node("area_town_0_0")
    for probe in ("in", "enter inn", "inn", "the inn"):
        edge, way, handle = matcher.resolve_exit(town.id, probe)
        assert way is not None and way.id == "way_gateway_town_inn", probe



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
    assert gw.properties["direction"] == "enter inn"
    assert gw.properties["return_direction"] == "leave"
    # "go in" / "go out" keep working through the matcher's alias tier.
    assert gw.properties["aliases"] == ["in", "out"]
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
    """Apply gateways to a real VirtualWorld and read the exits dict.

    task-496 widened the entry direction to a narrative phrase, so the exit is
    now keyed by that phrase rather than "in"/"out". The engine is still
    unchanged — it keys movement off whatever the direction string says.
    """
    from app import create_app
    world = create_app({"TESTING": True}).world
    m = _town_with_inn()
    generation.apply_patch(world.graph, m, world_compile.compile_grid(m, "inn"))
    generation.apply_patch(world.graph, m, world_compile.compile_grid(m, "town"))
    town_name = world.graph.get_node("area_town_0_0").name
    inn_name = world.graph.get_node("area_inn_0_0").name
    into = world.area_description.build_exits_for_area(town_name)
    out_of = world.area_description.build_exits_for_area(inn_name)
    assert "enter inn" in into
    assert "leave" in out_of
    # The short handles are preserved as aliases, so nothing a character could
    # previously say stops working.
    gw = world.graph.get_node("way_gateway_town_inn")
    assert "in" in gw.properties["aliases"]


def test_gateway_is_walkable_in_and_out():
    m = _town_with_inn()
    g = WorldGraph()
    generation.apply_patch(g, m, world_compile.compile_grid(m, "inn"))
    generation.apply_patch(g, m, world_compile.compile_grid(m, "town"))

    gw_id = "way_gateway_town_inn"
    assert g.get_node(gw_id) is not None
    enter, leave, _ = world_compile._entry_phrases("inn", None, None)
    into_gateway = {e.target: e.properties["direction"]
                    for e in g.get_edges_for_source("area_town_0_0")}
    assert into_gateway[gw_id] == enter
    out_of_gateway = {e.target: e.properties["direction"]
                      for e in g.get_edges_for_source("area_inn_0_0")}
    assert out_of_gateway[gw_id] == leave


def test_regenerating_the_parent_does_not_duplicate_the_gateway():
    m = _town_with_inn()
    g = WorldGraph()
    generation.apply_patch(g, m, world_compile.compile_grid(m, "inn"))
    generation.apply_patch(g, m, world_compile.compile_grid(m, "town"))
    generation.apply_patch(g, m, world_compile.compile_grid(m, "town"),
                           allow_regenerate=True)
    gw_ids = [nid for nid in g.nodes if nid.startswith("way_gateway_")]
    assert gw_ids == ["way_gateway_town_inn"]


def test_regenerating_restamps_an_existing_generated_node():
    """A re-run refreshes an emitted node's payload instead of keeping stale data.

    Regression: a scope compiled before the recipe stored ``properties.cell``
    kept no coords after ⚙ Generate, because apply_patch only *added* missing
    nodes. Map mode then fell back to the compass layout and left physics on.
    """
    m = _manifest(FOUR)
    g = WorldGraph()
    generation.apply_patch(g, m, world_compile.compile_grid(m, "wild"))

    area_id = "area_wild_0_0"
    stale = g.get_node(area_id)
    assert stale.properties["cell"] == {"x": 0, "y": 0}
    # Simulate an old record: drop the painted coords the recipe now emits.
    for key in ("cell", "x", "y"):
        stale.properties.pop(key, None)

    generation.apply_patch(g, m, world_compile.compile_grid(m, "wild"),
                           allow_regenerate=True)
    fresh = g.get_node(area_id)
    assert fresh.properties["cell"] == {"x": 0, "y": 0}
    assert fresh.properties["x"] == 0 and fresh.properties["y"] == 0


def test_a_placement_on_an_unpainted_cell_does_not_link():
    m = _town_with_inn()
    wg.place(m, "town", "inn", 1, 0)   # cell (1,0) is painted, so move off it
    wg.paint(m["town"], "biome", 1, 0, None)   # erase the paint under the inn
    generation.apply_patch(WorldGraph(), m, world_compile.compile_grid(m, "inn"))
    parent_patch = world_compile.compile_grid(m, "town")
    assert not [n for n in parent_patch.nodes if n.id.startswith("way_gateway_")]
    assert "area_id" not in m["town"]["placements"]["inn"]


def test_ungenerate_deletes_a_zone_but_keeps_its_grid():
    """⚙ Ungenerate removes the generated nodes and resets the scope, keeping paint."""
    m = _town_with_inn()
    g = WorldGraph()
    generation.apply_patch(g, m, world_compile.compile_grid(m, "inn"))
    generation.apply_patch(g, m, world_compile.compile_grid(m, "town"))
    assert g.get_node("way_gateway_town_inn") is not None
    assert m["town"]["placements"]["inn"]["area_id"] == "area_town_0_0"

    result = world_scopes.ungenerate_scope(m, g, "inn")
    assert result["deleted_nodes"] >= 1
    assert not [nid for nid in g.nodes if nid.startswith("area_inn_")]
    # The parent's gateway into the zone dies with it, but the parent's own
    # nodes and its placement link (which points at the parent's area) stay.
    assert g.get_node("way_gateway_town_inn") is None
    assert g.get_node("area_town_0_0") is not None
    assert m["town"]["placements"]["inn"]["area_id"] == "area_town_0_0"
    # The scope keeps its grid and paint, and returns to unmade.
    assert m["inn"]["state"] == "unmade" and not m["inn"]["area_ids"]
    assert "entry_area_id" not in m["inn"]
    assert m["inn"]["layers"]["biome"]["0,0"] == "sparse_forest"

    # A clean regenerate re-creates the zone and re-links the gateway.
    generation.apply_patch(g, m, world_compile.compile_grid(m, "inn"))
    assert g.get_node("area_inn_0_0") is not None
    assert g.get_node("way_gateway_town_inn") is not None


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


# ─── placed areas (task-528) ───────────────────────────────────────────────


def test_compile_skips_a_cell_holding_a_placed_area():
    """The hand-placed area owns its cell; the biome painted under it loses."""
    m = _manifest({(0, 0): "sparse_forest", (1, 0): "dense_forest"})
    wg.place_area(m, "wild", "area_hills", 0, 0)

    patch = world_compile.compile_grid(m, "wild")
    ids = [node.id for node in patch.nodes if node.type == "area"]
    assert ids == ["area_wild_1_0"]
    # The placed area is not in the patch at all: the compiler never mints it.
    assert "area_hills" not in ids

    # Merging regions must not swallow it either — the cell leaves the compile
    # set before regions are formed.
    merged = world_compile.compile_grid(m, "wild", region_merge=True)
    assert [n.id for n in merged.nodes if n.type == "area"] == ["area_wild_1_0"]


def test_compile_reports_when_every_painted_cell_is_taken():
    m = _manifest({(0, 0): "sparse_forest"}, w=1, h=1)
    wg.place_area(m, "wild", "area_hills", 0, 0)
    with pytest.raises(ValueError, match="hand-placed area"):
        world_compile.compile_grid(m, "wild")


def test_ungenerate_leaves_a_placed_area_alone():
    """It is hand-authored: no provenance, so the delete predicate skips it."""
    from graph import WorldGraph
    m = _manifest({(0, 0): "sparse_forest", (1, 0): "dense_forest"})
    wg.place_area(m, "wild", "area_hills", 0, 0)
    g = WorldGraph()
    g.add_node(Node(id="area_hills", type="area", name="Northern Hills",
                    properties={"world_scope_id": "wild", "cell": {"x": 0, "y": 0},
                                "x": 0, "y": 0}))
    generation.apply_patch(g, m, world_compile.compile_grid(m, "wild"))

    report = world_scopes.ungenerate_scope(m, g, "wild")
    assert report is not None
    assert g.get_node("area_hills") is not None
    # The scope's own generated areas are gone, and the cell is free again.
    assert g.get_node("area_wild_0_0") is None
    assert wg.area_placement_of(m["wild"], "area_hills") == (0, 0)

