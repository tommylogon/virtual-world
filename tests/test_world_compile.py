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


def _painted(biomes=None, roads=None, floors=None, w=6, h=3, merge=False):
    """A one-scope manifest painted across all three layers (task-496).

    *floors* holds **storey indices** — 0 ground, 1 up, -1 down, unbounded — not
    heights and not materials (see `engine/world_grid.PAINT_LAYERS`).
    """
    m = _manifest(biomes or {}, w=w, h=h)
    for (x, y), value in (roads or {}).items():
        wg.paint(m["wild"], "road", x, y, value)
    for (x, y), value in (floors or {}).items():
        wg.paint(m["wild"], "floor", x, y, value)
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
    # `floor` is a STOREY index (0 ground, 1 up, -1 down, unbounded) — never the
    # ground material. The material is `surface`.
    assert area.properties["floor"] == 0
    assert isinstance(area.properties["floor"], int)
    assert area.properties["surface"] == "dirt"
    assert "elevation" not in area.properties
    assert "forest" in area.properties["tags"]
    assert isinstance(area.properties["environment"], dict)
    assert area.properties["description"].endswith(".")

    way = next(n for n in patch.nodes if n.type == "way")
    for key in ("area_from", "area_to", "area_from_id", "area_to_id",
                "direction", "see_through", "floor", "surface"):
        assert key in way.properties, key
    assert isinstance(way.properties["floor"], int)
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


def test_a_multi_storey_step_turns_a_gentle_slope_into_a_rockface():
    """Prose only — a 2+ storey step reads as a cliff outdoors (task-525 gates it)."""
    painted = {(2, 1): "farmland", (2, 2): "sparse_forest"}
    flat = _painted(painted, roads={(2, 1): "road"})
    assert "forest line" in _character(world_compile.compile_grid(flat, "wild"))

    steep = _painted(painted, roads={(2, 1): "road"},
                     floors={(2, 0): "4"})
    assert "rockface" in _character(world_compile.compile_grid(steep, "wild"))

    gentle = _painted(painted, roads={(2, 1): "road"},
                      floors={(2, 0): "1"})
    assert "forest line" in _character(world_compile.compile_grid(gentle, "wild"))


def test_a_storey_step_is_not_a_cliff_inside_a_building():
    """A storey step in a town/interior is a staircase, not a rockface.

    The same painting as the test above *does* read as a rockface in a `world`
    scope, so this pins the mode gate rather than the absence of a step.
    """
    painted = {(2, 1): "farmland", (2, 2): "sparse_forest"}
    for mode in ("town", "interior"):
        m = _painted(painted, roads={(2, 1): "road"}, floors={(2, 0): "4"})
        wg.ensure_grid(m["wild"], 6, 3, mode=mode)   # same size: paint survives
        assert "rockface" not in _character(world_compile.compile_grid(m, "wild")), mode


# ── storey semantics (recipe grid.v2) ─────────────────────────────────────


def test_an_author_name_is_the_display_name_a_painted_place_compiles_to():
    """Task-560: naming a cell is what makes a painted town addressable.

    Without it a 19-location town is 19 coordinate names, and a building is
    "Building 3,4" forever.
    """
    m = _painted({(0, 0): "tavern", (1, 0): "temple", (2, 0): "shop"})
    m["wild"]["names"] = {"0,0": "The Stag Inn", "1,0": "The Shrine"}
    patch = world_compile.compile_grid(m, "wild")
    by_cell = {n.properties["cell"]["x"]: n.name
               for n in patch.nodes if n.type == "area"}
    assert by_cell[0] == "The Stag Inn", "the author's name wins"
    assert by_cell[1] == "The Shrine"
    assert "(Wild" in by_cell[2], "an unnamed cell keeps the generated form"


def test_a_repeated_name_inside_one_scope_falls_back_so_no_area_offers_two():
    """`go <name>` collects the current area's exits first, so one area must never
    offer two exits with the same name. Ids stay the authoritative key."""
    m = _painted({(0, 0): "tavern", (1, 0): "shop", (2, 0): "inn"})
    m["wild"]["names"] = {"0,0": "The Stag Inn", "1,0": "The Stag Inn"}
    patch = world_compile.compile_grid(m, "wild")
    names = [n.name for n in patch.nodes if n.type == "area"]
    assert names.count("The Stag Inn") == 1, "only the first keeps the name"
    assert len(set(names)) == len(names), "and every area is still uniquely named"


def test_a_region_takes_the_name_of_a_cell_in_it():
    """A merged region is one place, and naming the middle of a High Street is the
    natural thing to do — so the first named cell in the run speaks for all of it,
    rather than the author having to know the anchor is the top-left-most one."""
    m = _painted(roads={(0, 0): "road", (1, 0): "road", (2, 0): "road"},
                 merge=True)
    m["wild"]["names"] = {"1,0": "Millbrook High Street"}
    patch = world_compile.compile_grid(m, "wild", region_merge=True)
    roads = [n.name for n in patch.nodes if n.type == "area"]
    assert roads == ["Millbrook High Street"], roads


def test_a_wall_separates_two_rooms_a_door_joins_them():
    """The clearest statement of the model, with real taxonomy ids so nothing here
    depends on an unknown-id fallback:

        tavern | wall | temple
        shop   | door | warehouse

    The wall is not a way between the tavern and the temple. The door is a way
    between the shop and the warehouse — occupying the same cell a wall would.
    """
    painted = {(0, 0): "tavern", (1, 0): "wall", (2, 0): "temple",
               (0, 1): "shop", (1, 1): "door", (2, 1): "warehouse"}
    patch = world_compile.compile_grid(_painted(painted), "wild")
    areas = {tuple(a.properties["cell"].values()): a
             for a in patch.nodes if a.type == "area"}
    assert (1, 0) not in areas and (1, 1) not in areas, "structure is never a place"
    assert set(areas) == {(0, 0), (2, 0), (0, 1), (2, 1)}

    def connected(a, b):
        return any({w.properties["area_from_id"], w.properties["area_to_id"]}
                   == {a.id, b.id} for w in patch.nodes if w.type == "way")

    tavern, temple = areas[(0, 0)], areas[(2, 0)]
    shop, warehouse = areas[(0, 1)], areas[(2, 1)]
    assert not connected(tavern, temple), "a wall is not a way"
    assert connected(tavern, shop), "open ground is a way"
    assert connected(temple, warehouse), "open ground is a way"
    assert connected(shop, warehouse), "a door is a way"
    door_ways = [w for w in patch.nodes if w.type == "way"
                 and w.properties["kind"] == "door"]
    assert len(door_ways) == 1, "and exactly one kind of door way"


def test_a_void_is_not_a_place_either():
    painted = {(0, 0): "tavern", (1, 0): "void", (2, 0): "temple"}
    # `link_islands=False` so what is left reflects *only* what was painted: a void
    # between two places is not a route, rather than being rescued by the island
    # linker (which has its own test below).
    patch = world_compile.compile_grid(_painted(painted), "wild", link_islands=False)
    areas = [n for n in patch.nodes if n.type == "area"]
    assert len(areas) == 2, [a.properties["cell"] for a in areas]
    assert not [n for n in patch.nodes if n.type == "way"]


def test_structure_cells_are_not_places():
    """Task-562: a wall, a void, a window and a door are not places.

    Before edge semantics every painted cell became an area, so a wall *was* a
    room and the gap it left read as the way between two rooms — the exact inverse
    of what a floor plan means.
    """
    painted = {(0, 0): "tavern", (1, 0): "wall", (2, 0): "temple",
               (1, 1): "void"}
    patch = world_compile.compile_grid(_painted(painted), "wild")
    cells = {tuple(n.properties["cell"].values())
             for n in patch.nodes if n.type == "area"}
    assert (1, 0) not in cells, "no area on a wall"
    assert (1, 1) not in cells, "no area on a void"
    assert any("structure cell" in note for note in patch.report.notes), \
        patch.report.notes


def test_a_passable_cell_between_two_storeys_is_a_stairwell_not_a_door():
    """The storey is the stronger signal about what you do crossing it. A "door" that
    quietly climbs a floor would be a lie in the pass message."""
    painted = {(0, 0): "tavern", (0, 1): "door", (0, 2): "library"}
    m = _painted(painted, floors={(0, 2): "1"})
    ways = [n for n in world_compile.compile_grid(m, "wild", link_islands=False).nodes
            if n.type == "way"]
    assert len(ways) == 1
    assert ways[0].properties["kind"] == "stairs", "it climbs"
    assert ways[0].properties["floor_step"] == 1
    assert "climb" in ways[0].properties["pass_message"].lower()


def test_a_door_with_places_all_round_it_joins_the_two_on_opposite_sides():
    """The opposite pair is what decides, and it is always the right reading: with
    four cardinal neighbours, any three contain an opposite pair, so a door with
    places all around it is a door in a wall with a room either side."""
    painted = {(0, 0): "tavern", (1, 0): "door", (2, 0): "temple",
               (0, 1): "shop", (1, 1): "warehouse", (2, 1): "library"}
    patch = world_compile.compile_grid(_painted(painted), "wild", link_islands=False)
    door_ways = [w for w in patch.nodes if w.type == "way"
                 and w.properties.get("kind") in ("door", "stairs")]
    assert len(door_ways) == 1, [w.name for w in door_ways]
    way = door_ways[0]
    assert {way.properties["area_from_id"], way.properties["area_to_id"]} == {
        "area_wild_0_0", "area_wild_2_0"}, "west and east, across the door"
    assert any("threshold" in note for note in patch.report.notes), patch.report.notes


def test_a_door_with_a_place_on_one_side_leads_nowhere_and_says_so():
    """Invisible in the node counts, so the report has to mention it — a door that
    goes nowhere is nearly always a mis-painted one."""
    painted = {(0, 0): "tavern", (1, 0): "door", (2, 0): "wall"}
    patch = world_compile.compile_grid(_painted(painted), "wild", link_islands=False)
    assert any("lead nowhere" in note for note in patch.report.notes), \
        patch.report.notes
    assert not [n for n in patch.nodes if n.type == "way"]


def test_a_window_with_places_on_both_sides_is_a_passage_in_disguise():
    """A window with a place either side is a doorway, and treating it as a window
    would hide a route the author drew — or invent one, if it were treated as a
    door. So it is neither: a window is a window."""
    painted = {(0, 0): "tavern", (1, 0): "window", (2, 0): "temple"}
    patch = world_compile.compile_grid(_painted(painted), "wild", link_islands=False)
    assert not [n for n in patch.nodes if n.type == "way"], \
        "a window is not a route, however tempting it looks"
    assert not [n for n in patch.nodes
                if n.type == "area" and n.properties.get("windows")], \
        "and it is not claimed by either place"


def test_a_sealed_room_is_rescued_by_island_linking_and_that_is_stated():
    """A wall can leave a room unreachable, and `link_islands` (on by default) joins
    it to the nearest place with a single way. Worth a test, because "a wall is not
    a way" and "the room is reachable" are both true, and the second is a deliberate
    rescue rather than something the author painted.

    Making a sealed room genuinely unreachable is a different decision and belongs
    with entering a building (task-563), not here.
    """
    painted = {(0, 0): "tavern", (1, 0): "wall", (2, 0): "temple"}
    patch = world_compile.compile_grid(_painted(painted), "wild")
    assert any("island" in note for note in patch.report.notes), patch.report.notes
    ways = [n for n in patch.nodes if n.type == "way"]
    assert len(ways) == 1, "exactly one rescue way, not a way through the wall"
    assert ways[0].properties["kind"] == "open", "and it is an open rescue"


def test_a_window_is_not_a_route_but_its_place_knows_about_it():
    """You can see through a window; you cannot walk through it. So it mints no
    way, and the room it belongs to records it."""
    painted = {(0, 0): "classroom", (1, 0): "window"}
    patch = world_compile.compile_grid(_painted(painted), "wild")
    assert not [n for n in patch.nodes if n.type == "way"], "a window is not a route"
    room = next(n for n in patch.nodes if n.type == "area")
    assert room.properties["windows"] == [{"x": 1, "y": 0, "facing": "west"}]


def test_a_storey_step_is_a_climb_not_a_stride():
    """The floor layer finally does something at the edges (task-562). A step is a
    climb; *blocking* a big one is still task-525's decision."""
    painted = {(0, 0): "hallway", (1, 0): "classroom"}
    m = _painted(painted, floors={(0, 0): "2"})
    ways = [n for n in world_compile.compile_grid(m, "wild").nodes
            if n.type == "way"]
    assert len(ways) == 1
    assert ways[0].properties["kind"] == "stairs"
    assert ways[0].properties["floor_step"] == 2, "the number a gate will read"
    assert "climb" in ways[0].properties["pass_message"].lower()

    # Same storey: a plain open step, and the property says so.
    flat = [n for n in world_compile.compile_grid(_painted(painted), "wild").nodes
            if n.type == "way"]
    assert flat[0].properties["kind"] == "open"
    assert flat[0].properties["floor_step"] == 0


def test_a_region_never_spans_two_storeys():
    """Found by compiling a two-storey plan: merging is 8-neighbour and was
    storey-blind, so a classroom above a classroom of the same kind became one
    place with a staircase inside it.

    Painted with a *room*, not a tavern: a building cell is ``merge: never``
    (task-564 — two adjacent cottages are two cottages), so three tavern cells
    would be three areas and the test would pass without testing anything. A
    classroom is a kind that does merge, which is what this is about.
    """
    painted = {(0, 0): "classroom", (1, 0): "classroom", (0, 1): "classroom"}
    m = _painted(painted, floors={(0, 1): "1"}, merge=True)
    below = [n for n in world_compile.compile_grid(m, "wild", region_merge=True).nodes
             if n.type == "area"]
    # Two on the ground (merged), one above on its own storey.
    assert len(below) == 2, [a.properties["cell"] for a in below]
    assert sorted(a.properties["floor"] for a in below) == [0, 1]


def test_a_building_is_never_merged_with_its_neighbour():
    """The other half of task-564, and the reason the test above is painted with
    a room: a building cell is a *plot*, so a terrace of cottages is three houses
    with three doors, not one house with one."""
    painted = {(0, 0): "cottage", (1, 0): "cottage", (2, 0): "cottage"}
    m = _painted(painted, merge=True)
    areas = [n for n in world_compile.compile_grid(m, "wild", region_merge=True).nodes
             if n.type == "area"]
    assert len(areas) == 3, [a.properties["cell"] for a in areas]


def test_a_high_school_plan_end_to_end():
    """The plan that exposed the gap: a corridor, two classrooms that merge, a
    blank between two more, a window that only sees, and a storey above."""
    painted = {
        (0, 0): "hallway", (0, 1): "hallway", (0, 2): "stairway",
        (1, 1): "classroom", (2, 1): "classroom",   # same kind: they merge
        (3, 1): "wall", (4, 1): "classroom",        # the blank blocks the row
        (5, 1): "window",                            # sees out of (4,1)
        (1, 2): "classroom",                         # the storey above
        (0, 3): "hallway",                          # and one more up the stair
    }
    m = _painted(painted, floors={(0, 2): "1", (1, 2): "1", (0, 3): "1"},
                 merge=True, h=4)
    patch = world_compile.compile_grid(m, "wild", region_merge=True)
    areas = [n for n in patch.nodes if n.type == "area"]
    ways = [n for n in patch.nodes if n.type == "way"]

    def at(x, y):
        return next((a for a in areas
                     if a.properties["cell"] == {"x": x, "y": y}), None)

    # Nothing on structure is ever a place.
    assert at(3, 1) is None, "a wall is not a room"
    assert at(5, 1) is None, "a window is not a room"
    # …and a **stairway** is structure too (task-568 gave it a real id and a
    # `passable` kind), so it is a threshold between two places rather than a
    # place of its own. Before that id existed this cell was an unknown biome and
    # compiled to a room called "Stairway", which is exactly the gap task-568
    # closed — so the assertion below is the fix, stated as a test.
    assert at(0, 2) is None, "a stairway is a way between rooms, not a room"
    # The two adjacent classrooms merged into one place, anchored at the first.
    assert at(1, 1) is not None, "the merged classroom keeps its first cell"
    assert at(2, 1) is None, "and the second cell is part of it, not a place"
    # The upper storey is its own place, not part of the classroom below it.
    assert at(1, 2) is not None and at(1, 2).properties["floor"] == 1

    # The window is recorded on the room it faces, and mints no way.
    behind = at(4, 1)
    assert behind.properties["windows"] == [{"x": 5, "y": 1, "facing": "west"}]

    # A storey step is a climb; once on the upper storey the way is level again,
    # which is the whole point of the storey model.
    stairs = [w for w in ways if w.properties.get("kind") == "stairs"]
    assert stairs, [w.properties.get("kind") for w in ways]
    assert all(w.properties["floor_step"] == 1 for w in stairs)
    # The stairs are the **threshold itself** now, not a way between two rooms:
    # the stairway cell joins the hallway below it to the hallway above it, and
    # that single way is the climb. (The two hallways are one region, anchored at
    # its first cell, so (0,0) is the lower one.)
    below, upper = at(0, 0), at(0, 3)
    climb = next(w for w in ways
                 if {w.properties["area_from_id"], w.properties["area_to_id"]}
                 == {below.id, upper.id})
    assert climb.properties["kind"] == "stairs", "the storey step is the climb"
    assert climb.properties["handle"] == "stairs", "and it is nameable"
    assert climb.properties["aliases"] == ["stairs", "stairway", "up", "down",
                                           "in", "out"]
    # A storey step of one between *rooms* on either side of it is a climb too,
    # even though neither room is a hallway — the storey, not the kind, decides.
    across = next(w for w in ways
                  if {w.properties["area_from_id"], w.properties["area_to_id"]}
                  == {at(1, 1).id, at(1, 2).id})
    assert across.properties["kind"] == "stairs"
    assert across.properties["floor_step"] == 1

    # Every way is one of the three kinds the model knows, never an accident.
    assert {w.properties["kind"] for w in ways} <= {"open", "door", "stairs"}
    # And the report says what the structure did, since it is invisible in the
    # node counts.
    assert any("structure cell" in note for note in patch.report.notes), \
        patch.report.notes
    assert any("window" in note for note in patch.report.notes), patch.report.notes


def test_a_road_painted_over_a_wall_is_still_a_road():
    """The road layer replaces the biome, exactly as it does everywhere else — a
    road is a place even where the thing under it is a wall."""
    m = _painted({(0, 0): "wall", (1, 0): "wall"}, roads={(1, 0): "road"})
    areas = [n for n in world_compile.compile_grid(m, "wild").nodes
             if n.type == "area"]
    assert [a.properties["cell"] for a in areas] == [{"x": 1, "y": 0}]


def test_a_name_is_metadata_not_paint():
    """Names survive the eraser and an unnamed scope loads byte-identically."""
    record = {"id": "s", "name": "S", "kind": "scope", "state": "unmade",
              "grid": {"w": 2, "h": 2, "cell_scale": 1.0}, "layers": {}}
    wg.normalise_grid(record)
    assert "names" not in record, "no empty container is invented"

    assert wg.set_name(record, 1, 0, "The Stag Inn") == "The Stag Inn"
    assert record["names"] == {"1,0": "The Stag Inn"}
    assert wg.name_at(record, 1, 0) == "The Stag Inn"
    assert wg.name_at(record, 0, 0) is None

    # A name is not paint: clearing the cell keeps it.
    wg.paint(record, "road", 1, 0, None)
    assert wg.name_at(record, 1, 0) == "The Stag Inn"

    assert wg.set_name(record, 1, 0, "  ") is None, "whitespace clears"
    assert "names" not in record, "and the container goes with the last name"


def test_a_bad_name_costs_one_name_not_the_map():
    record = {"id": "s", "name": "S", "kind": "scope", "state": "unmade",
              "grid": {"w": 2, "h": 2, "cell_scale": 1.0}, "layers": {},
              "names": {"1,0": "The Stag Inn", "not a cell": "nope", "2,2": ""}}
    wg.normalise_grid(record)
    assert record["names"] == {"1,0": "The Stag Inn"}


def test_a_storey_is_a_storey_index_and_is_unbounded():
    """0 ground, 1 up, -1 down — and as far as an author wants to go.

    The old mapping wrote the ground *material* onto `floor` and had no way to
    say "eighty floors up"; a 0..1 height fraction cannot, and a ±10 clamp in the
    inspector could not either.
    """
    painted = {(0, 0): "farmland", (1, 0): "farmland", (2, 0): "farmland"}
    m = _painted(painted, floors={(0, 0): "1", (1, 0): "80", (2, 0): "-900"})
    patch = world_compile.compile_grid(m, "wild")

    by_cell = {n.properties["cell"]["x"]: n
               for n in patch.nodes if n.type == "area"}
    assert by_cell[0].properties["floor"] == 1
    assert by_cell[1].properties["floor"] == 80
    assert by_cell[2].properties["floor"] == -900
    # The material is still there, under its own name.
    for cell in (0, 1, 2):
        assert by_cell[cell].properties["surface"] == "tilled_soil"


def test_an_unpainted_cell_is_ground_and_never_raises():
    """A plain cell needs no number: unpainted means storey 0, and paint that
    isn't a number reads as ground rather than crashing the compile."""
    m = _painted({(0, 0): "farmland", (1, 0): "farmland"},
                 floors={(1, 0): "not-a-number"})
    patch = world_compile.compile_grid(m, "wild")
    by_cell = {n.properties["cell"]["x"]: n
               for n in patch.nodes if n.type == "area"}
    assert by_cell[0].properties["floor"] == 0
    assert by_cell[1].properties["floor"] == 0


def test_a_way_takes_the_lower_of_the_two_storeys_it_joins():
    """Order-independent: a corridor is on its storey, a climb on the one it
    leaves — so the way must not depend on which side emitted it first."""
    painted = {(0, 0): "farmland", (1, 0): "farmland"}
    m = _painted(painted, floors={(0, 0): "5"})
    patch = world_compile.compile_grid(m, "wild")
    ways = [n for n in patch.nodes if n.type == "way"
            and n.properties["area_from_id"].endswith("_0_0")]
    assert ways and all(w.properties["floor"] == 0 for w in ways)
    assert all(w.properties["surface"] == "tilled_soil" for w in ways)


def test_a_legacy_elevation_layer_still_reads_as_storeys():
    """A scope painted under the old layer name keeps its numbers.

    `sanitize_record` migrates the key, so the compiler needs no special case —
    this pins the migration, because dropping the layer would silently lose it.
    """
    m = _manifest({(0, 0): "farmland", (1, 0): "farmland"})
    m["wild"]["layers"]["elevation"] = {"0,0": "3"}
    wg.normalise_grid(m["wild"])
    assert "elevation" not in m["wild"]["layers"]
    assert m["wild"]["layers"]["floor"] == {"0,0": "3"}

    patch = world_compile.compile_grid(m, "wild")
    area = next(n for n in patch.nodes if n.type == "area"
                and n.properties["cell"] == {"x": 0, "y": 0})
    assert area.properties["floor"] == 3


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
    # The record owns its own seam (task-529), so `tunnel` says "go down the
    # tunnel" and the derived "enter the tunnel" is now the *fallback*, not the
    # answer. The three sources are checked in the order they are consulted:
    # placement override, then record, then derived from the placement's name.
    assert world_compile._entry_phrases("the mine", "tunnel", None)[0] == (
        "go down the tunnel")
    assert world_compile._entry_phrases("the crossing", "ford", None)[0] == (
        "wade across the ford")
    assert world_compile._entry_phrases("the gatehouse", "gate", None)[0] == (
        "pass through the gate")
    assert world_compile._entry_phrases("the mine", "bridge", None)[0] == (
        "cross the bridge")
    # …and an override beats both, verbatim, because a mine with two adits has two
    # ways in and only the author knows which is which.
    assert world_compile._entry_phrases("the mine", "tunnel", None,
                                        override="crawl down the old adit")[0] == (
        "crawl down the old adit")
    # A plain placement with nothing painted says what it is.
    assert world_compile._entry_phrases("Inn", None, None) == (
        "enter inn", "leave", ["in", "out"], "enter inn")


def test_entry_phrases_read_the_floor_step():
    assert world_compile._entry_phrases("cave", None, -3.0)[0] == "climb down into cave"
    assert world_compile._entry_phrases("cave", None, 3.0)[0] == "climb up into cave"
    assert world_compile._entry_phrases("cave", None, 1.0)[0] == "enter cave"


def test_every_entry_phrase_keeps_the_short_handles_as_aliases():
    # Four values back, not three: the inward phrase is returned twice, once as
    # the `direction` movement resolves by and once as the `entry_phrase` the
    # area description offers (task-529).
    for feature in (None, "road", "tunnel", "ford", "bridge", "gate"):
        _, _, aliases, _ = world_compile._entry_phrases("inn", feature, 2.0)
        assert "in" in aliases and "out" in aliases, feature


def test_an_override_keeps_the_short_handles():
    """An author's own wording must not take a command away (task-529): "go in"
    still works even when the phrase is theirs."""
    _, _, aliases, phrase = world_compile._entry_phrases(
        "the mine", "tunnel", None, override="crawl down the old adit")
    assert "in" in aliases and "out" in aliases
    assert phrase == "crawl down the old adit"


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


def test_a_road_only_island_links_without_a_biome():
    """A cell is a place if it has a biome *or a road*
    (``cells = set(biome_of) | set(road_of)``), so an island whose closest cell
    is road-only has no ``biome_of`` entry at all.

    The island-linker read ``biome_of[ca]`` as a bare subscript and raised
    KeyError on exactly that cell, which is a 500 from Generate for a perfectly
    ordinary map — a main landmass plus a road running out to a lone outpost. The
    sibling region-boundary emitter has always used the safe accessor, and every
    other read of ``biome_of`` in the module uses ``.get``; this was the lone
    exception and it crashed the WorldPainter flow.

    The road island is deliberately the *smaller* component: the linker picks
    ``main`` as the largest, so only a road cell that is the linked island has no
    biome. A road island larger than the landmass links the landmass instead and
    never touches the missing key, which is why the shape has to be pinned this
    way rather than left to the tie-break.
    """
    m = _painted(biomes={(0, 0): "sparse_forest", (0, 1): "dense_forest",
                         (0, 2): "hills"},
                 roads={(0, 5): "cobblestone"},
                 w=3, h=6)
    patch = world_compile.compile_grid(m, "wild")
    ways = [n for n in patch.nodes if n.type == "way"]
    # The road cell exists as a place, and the outpost is linked to the landmass
    # rather than dropped as an unreachable dead end.
    road_areas = [n for n in patch.nodes
                  if n.type == "area" and n.properties.get("road")]
    assert road_areas, "a road-painted cell must compile to a place"
    assert ways, "the disconnected road island must be linked, not dropped"
    assert not any("no exits" in note for note in patch.report.notes)
    assert any("linked to the nearest region" in note for note in patch.report.notes)


def test_a_lone_painted_cell_has_no_exits_to_link_to():
    m = _manifest({(0, 0): "sparse_forest"})
    patch = world_compile.compile_grid(m, "wild")
    assert [n for n in patch.nodes if n.type == "way"] == []
    assert any("no exits" in note for note in patch.report.notes)


def test_every_generated_node_marks_its_position_as_painted():
    """Areas *and* ways must carry ``cell`` next to their coords.

    ``properties.x``/``y`` is an overloaded field: the compiler writes engine
    units (``cell * 40``) that the map layout scales by the map pitch and
    translates by the scope's ``map_offset``, while a node dragged in the graph
    stores canvas pixels in the same field. ``cell`` is the only thing telling
    them apart (``GraphLayoutEngine.hasPaintedCoords``).

    Areas stamped it; ways did not, so a way was indistinguishable from a dragged
    node. Saving a layout then wrote canvas pixels over its engine units, and the
    next layout scaled them again *and* re-added the scope offset — the way
    walked further out of place on every save. A character's stored position is a
    canvas pixel by definition, so it is re-placed raw, never scaled.
    """
    m = _painted(biomes={(0, 0): "sparse_forest", (0, 1): "dense_forest",
                         (0, 2): "hills"},
                 roads={(1, 0): "cobblestone"},
                 w=3, h=3)
    patch = world_compile.compile_grid(m, "wild")
    areas = [n for n in patch.nodes if n.type == "area"]
    ways = [n for n in patch.nodes if n.type == "way"]
    assert areas and ways, "the fixture must compile both areas and ways"

    for node in areas + ways:
        props = node.properties
        cell = props.get("cell")
        assert cell is not None, f"{node.id} is painted but carries no cell marker"
        assert isinstance(cell.get("x"), (int, float))
        assert isinstance(cell.get("y"), (int, float))
        # The coords are engine units, so they must equal cell * CELL_CANVAS_UNITS.
        # A way sits on the midpoint of two cells, so its cell is a half-integer.
        assert props["x"] == pytest.approx(cell["x"] * world_compile.CELL_CANVAS_UNITS)
        assert props["y"] == pytest.approx(cell["y"] * world_compile.CELL_CANVAS_UNITS)


def test_a_compiled_way_sits_on_a_half_cell_midpoint():
    """The way between two orthogonally adjacent cells (0,0)-(0,1) is painted on
    the midpoint (0, 0.5), so the flag does not misrepresent it as owning a cell."""
    m = _painted(biomes={(0, 0): "sparse_forest", (0, 1): "dense_forest"},
                 w=2, h=2)
    patch = world_compile.compile_grid(m, "wild")
    ways = [n for n in patch.nodes if n.type == "way"]
    assert len(ways) == 1
    cell = ways[0].properties["cell"]
    assert cell["y"] == pytest.approx(0.5)
    assert cell["x"] == pytest.approx(0.0)
    assert ways[0].properties["y"] == pytest.approx(0.5 * world_compile.CELL_CANVAS_UNITS)


def test_compile_rejects_missing_grid_and_empty_paint():
    m = {"wild": {"id": "wild", "name": "Wild"}}
    with pytest.raises(ValueError):
        world_compile.compile_grid(m, "wild")
    with pytest.raises(ValueError):
        world_compile.compile_grid(m, "ghost")

    empty = _manifest()
    with pytest.raises(ValueError):
        world_compile.compile_grid(empty, "wild")


def test_a_baked_zone_compiles_the_paint_it_has():
    """`baked` freezes the *canon*; it does not seal the scope.

    This was "compiles once then refuses", on the belief that a baked scope never
    carries paint. It does: the flag is set by promoting areas the author already
    wrote, and the paint route creates a grid on demand, so an author who promotes
    a selection and then paints the rest of the room lands exactly here. The
    refusal told them to delete the scope and start again.

    What is still true after compiling is that the **hand-authored** areas are
    untouched: they carry no provenance, so ``apply_patch`` does not replace them
    and a second compile leaves them alone.
    """
    m = _manifest(FOUR)
    m["wild"]["paint_policy"] = world_compile.PAINT_POLICY_BAKED
    patch = world_compile.compile_grid(m, "wild")
    areas = [n for n in patch.nodes if n.type == "area"]
    assert areas, "a baked scope with paint must compile it"

    g = WorldGraph()
    hand = Node(id="area_authored", type="area", name="Authored",
                properties={"world_scope_id": "wild"})
    g.add_node(hand)
    generation.apply_patch(g, m, patch)
    assert g.get_node("area_authored") is not None, (
        "a hand-authored area must survive compiling a baked scope")
    assert not (g.get_node("area_authored").properties or {}).get("generated")

    # And it is idempotent: a second compile replaces the compiled areas, not the
    # author's.
    again = world_compile.compile_grid(m, "wild")
    generation.apply_patch(g, m, again, allow_regenerate=True)
    assert g.get_node("area_authored") is not None


# ───────────────────── buildings: entered with 'in' (task-563) ─────────────────────


def _town_with_building(biome="inn", h=1, w=3):
    """A one-row town: street | building | alley.

    Both outer cells are roads so the building has two *cardinal* sides that have
    a way and no diagonal neighbour to muddy the count.
    """
    m = {"root": {"id": "root", "name": "Root", "children": ["town"]},
         "town": {"id": "town", "name": "Town"}}
    wg.ensure_grid(m["town"], w, h, mode="town")
    for x in (0, w - 1):
        wg.paint(m["town"], "biome", x, 0, "farmland")
        wg.paint(m["town"], "road", x, 0, "road")
    wg.paint(m["town"], "biome", 1, 0, biome)
    return m


def _enter_ways(patch):
    return [n for n in patch.nodes if n.id.startswith("way_enter_")]


def _town_with_inn_building():
    """The same street, with an interior scope placed on the inn's cell."""
    m = _town_with_building()
    m["root"]["children"].append("inn")
    m["inn"] = {"id": "inn", "name": "The Inn"}
    wg.ensure_grid(m["inn"], 1, 1, mode="interior")
    wg.paint(m["inn"], "biome", 0, 0, "cottage")
    wg.place(m, "town", "inn", 1, 0)
    return m


def test_a_building_with_no_interior_gets_a_shut_in_way():
    patch = world_compile.compile_grid(_town_with_building(), "town")
    ways = _enter_ways(patch)
    # One per side that has a way: the street to the west, the alley to the east.
    assert len(ways) == 2
    street_door = next(w for w in ways
                       if w.properties["area_from_id"] == "area_town_0_0")
    assert street_door.properties["aliases"] == ["in"]
    assert street_door.properties["direction"] == "enter the inn"
    assert street_door.properties["current_state"] == "closed"
    assert "inn" in street_door.properties["refusal_message"]
    # It leads to the building's own cell — the doorstep — and is one-way *in*,
    # because the place beside a building already has a compass way onto the
    # plot: a way back would be a second connection for the same pair, and two
    # ways both answering to `out` on the plot means "out" picks one at random.
    assert street_door.properties["area_to_id"] == "area_town_1_0"
    assert len([e for e in patch.edges
                if e.source == "area_town_0_0" and e.target == street_door.id]) == 1
    assert any(e.source == street_door.id and e.target == "area_town_1_0"
               for e in patch.edges)
    assert not [e for e in patch.edges
                if e.source == "area_town_1_0" and e.target == street_door.id]
    # The plot's own way out is the compass one, so `out` is not ambiguous there.
    plot_exits = {e.properties.get("direction")
                  for e in patch.edges if e.source == "area_town_1_0"}
    assert plot_exits == {"east", "west"}
    # A painted door cell and a building's front door are different facts.
    assert street_door.properties["kind"] == "entrance"


def test_the_building_cell_is_still_a_place():
    """The plot remains an area; it is the doorstep, not the inside.

    Dropping it would break the `out` side of every interior and the placement
    record that a parent gateway points at.
    """
    patch = world_compile.compile_grid(_town_with_building(), "town")
    area = next(n for n in patch.nodes if n.id == "area_town_1_0")
    assert area.properties["building"] == "inn"


def test_a_building_with_an_interior_is_entered_with_in():
    m = _town_with_inn_building()
    generation.apply_patch(WorldGraph(), m, world_compile.compile_grid(m, "inn"))
    patch = world_compile.compile_grid(m, "town")
    ways = _enter_ways(patch)
    assert len(ways) == 2
    street_door = next(w for w in ways
                       if w.properties["area_from_id"] == "area_town_0_0")
    # It leads to the interior's entry area, and it is already open.
    assert street_door.properties["area_to_id"] == "area_inn_0_0"
    assert street_door.properties["current_state"] == "open"
    assert "refusal_message" not in street_door.properties
    # One-way on purpose: inside, `out` must keep meaning the doorstep the child
    # gateway points at, and a second way out would make the word ambiguous.
    assert not [e for e in patch.edges if e.source == "area_inn_0_0"
                and e.target == street_door.id]
    # Cleanup ownership, so ungenerating the interior takes the way with it.
    assert street_door.properties["child_scope_id"] == "inn"


def test_the_parent_first_order_still_emits_the_in_ways():
    """Generate the town, *then* draw the interior — the common flow.

    The parent could not mint the ways then (there was no entry area to point at),
    so the child mints them from the door sides the parent recorded.
    """
    m = _town_with_inn_building()
    g = WorldGraph()
    generation.apply_patch(g, m, world_compile.compile_grid(m, "town"))
    # The interior is placed but not generated, so there is nothing to go into and
    # nothing to refuse: a shut door here would be a lie about the world.
    assert not [nid for nid in g.nodes if nid.startswith("way_enter_")]
    sides = m["town"]["placements"]["inn"]["sides"]
    assert {s["area_id"] for s in sides} == {"area_town_0_0", "area_town_2_0"}

    child_patch = world_compile.compile_grid(m, "inn")
    ways = _enter_ways(child_patch)
    assert len(ways) == 2
    assert {w.properties["area_to_id"] for w in ways} == {"area_inn_0_0"}
    # Provenance says the parent (it owns the neighbour areas) but the way names
    # the child, which is how ungenerate finds and removes it.
    assert all(w.properties["world_scope_id"] == "town" for w in ways)
    assert all(w.properties["child_scope_id"] == "inn" for w in ways)


def test_a_walled_side_gets_no_door():
    """A side with no way gets no door — you cannot knock on a blank wall."""
    m = _town_with_building(w=4)
    wg.paint(m["town"], "biome", 2, 0, "wall")
    patch = world_compile.compile_grid(m, "town", link_islands=False)
    ways = _enter_ways(patch)
    assert [w.properties["area_from_id"] for w in ways] == ["area_town_0_0"]


def test_a_building_is_not_reached_through_a_wall_or_a_diagonal():
    """A diagonal neighbour is a corner of the plot, not a door in it."""
    m = _town_with_building(w=3, h=2)
    wg.paint(m["town"], "biome", 0, 1, "farmland")
    patch = world_compile.compile_grid(m, "town", link_islands=False)
    ways = _enter_ways(patch)
    assert {w.properties["area_from_id"] for w in ways} == {
        "area_town_0_0", "area_town_2_0"}


def test_wilderness_cells_get_no_doors():
    """A plain field is not a building: nothing changes for every existing world."""
    m = _painted(FOUR)
    assert not _enter_ways(world_compile.compile_grid(m, "wild"))


def test_a_road_painted_over_a_building_is_not_a_building():
    m = _town_with_building()
    wg.paint(m["town"], "road", 1, 0, "road")
    patch = world_compile.compile_grid(m, "town")
    assert not _enter_ways(patch)


def test_refusals_are_drawn_from_the_building_category():
    lines = {biome: world_compile.building_refusal(biome)
             for biome in ("inn", "smithy", "watch_house", "barn", "cottage")}
    for biome, line in lines.items():
        assert line.endswith("."), line
        assert world_compile.building_subject(biome) in line
    # A watch house is military (barred), an inn is commercial (shut) — the point
    # of the table is that two buildings of one *kind* do not read as clones.
    assert "locked" in lines["watch_house"]
    assert "shut" in lines["inn"] or "sign" in lines["inn"]
    # Deterministic: the same id always refuses the same way.
    assert lines["inn"] == world_compile.building_refusal("inn")


def test_the_report_says_how_many_doors_are_shut():
    m = _town_with_building()
    notes = " ".join(world_compile.compile_grid(m, "town").report.notes)
    assert "2 building door(s) entered with 'in'" in notes
    assert "2 shut" in notes


def test_the_building_door_appears_in_the_streets_exits():
    """The compiled door is an exit of a real world, with no engine change.

    Same shape as the gateway test: the direction string is the exit's key, and
    the short `in` handle survives as an alias. This is the difference between
    "the compiler emitted a node" and "a character standing in the street can
    say go in".
    """
    from app import create_app
    world = create_app({"TESTING": True}).world
    m = _town_with_inn_building()
    generation.apply_patch(world.graph, m, world_compile.compile_grid(m, "inn"))
    generation.apply_patch(world.graph, m, world_compile.compile_grid(m, "town"))

    street = world.graph.get_node("area_town_0_0").name
    exits = world.area_description.build_exits_for_area(street)
    assert "enter the inn" in exits
    assert "enter the inn" in str(world.area_description.build_exits_for_area(
        world.graph.get_node("area_town_2_0").name))
    door = next(n for n in world.graph.nodes.values()
                if n.id.startswith("way_enter_")
                and n.properties["area_from_id"] == "area_town_0_0")
    assert "in" in door.properties["aliases"]


def test_ungenerate_removes_a_building_door():
    m = _town_with_inn_building()
    g = WorldGraph()
    generation.apply_patch(g, m, world_compile.compile_grid(m, "town"))
    generation.apply_patch(g, m, world_compile.compile_grid(m, "inn"))
    assert [nid for nid in g.nodes if nid.startswith("way_enter_")]
    world_scopes.ungenerate_scope(m, g, "inn")
    assert not [nid for nid in g.nodes if nid.startswith("way_enter_")]


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
    enter, leave, _, phrase = world_compile._entry_phrases("inn", None, None)
    into_gateway = {e.target: e.properties["direction"]
                    for e in g.get_edges_for_source("area_town_0_0")}
    assert into_gateway[gw_id] == enter
    out_of_gateway = {e.target: e.properties["direction"]
                      for e in g.get_edges_for_source("area_inn_0_0")}
    assert out_of_gateway[gw_id] == leave
    # The way also carries the phrase as a phrase, so the town can *offer* the
    # move instead of listing another bracket to type (task-529).
    assert g.get_node(gw_id).properties["entry_phrase"] == phrase


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


# ─── boundary ways out of a placed area (task-528) ─────────────────────────


def _placed_on_a_road(area_id="area_trail", name="Camp Entrance Trail", at=(1, 0)):
    """A 3x1 painted scope with a hand-placed area on the north side of a road.

    The road runs ``(0,1) (1,1) (2,1)``, so the placed cell at ``(1,0)`` touches
    the road directly below and the road cells either side of it diagonally — which
    is the case a south-half-only scan would silently miss.
    """
    m = _painted(roads={(0, 1): "road", (1, 1): "road", (2, 1): "road"},
                 biomes={(0, 0): "sparse_forest", (2, 0): "dense_forest"},
                 w=3, h=2)
    wg.place_area(m, "wild", area_id, *at)
    g = WorldGraph()
    g.add_node(Node(id=area_id, type="area", name=name,
                    properties={"world_scope_id": "wild",
                                "cell": {"x": at[0], "y": at[1]}}))
    return m, g


def _boundary_ways(patch, *area_ids):
    """The ways touching any of *area_ids* (default: the one placed area)."""
    placed = {str(a) for a in (area_ids or ("area_trail",))}
    return [n for n in patch.nodes if n.type == "way"
            and placed & {str(n.properties.get("area_from_id")),
                          str(n.properties.get("area_to_id"))}]


def test_a_placed_area_gets_a_way_to_every_place_touching_it():
    m, g = _placed_on_a_road()
    patch = world_compile.compile_grid(m, "wild", region_merge=False, graph=g)

    ways = {n.id: n for n in _boundary_ways(patch)}
    # All eight neighbours, from a scan that only starts at the placed cell: the
    # road below, the two roads either side, and the two forests on top row.
    assert set(ways) == {
        "way_wild_area_trail_area_wild_0_0",
        "way_wild_area_trail_area_wild_2_0",
        "way_wild_area_trail_area_wild_0_1",
        "way_wild_area_trail_area_wild_1_1",
        "way_wild_area_trail_area_wild_2_1",
    }
    # Same terms as any other boundary, so a character walks it with no special
    # casing: a compass direction, an open seam, a surface, a midpoint position.
    to_road = ways["way_wild_area_trail_area_wild_1_1"]
    assert to_road.properties["direction"] == "south"
    assert to_road.properties["kind"] == "open"
    assert to_road.properties["current_state"] == "open"
    assert to_road.properties["cell"] == {"x": 1.0, "y": 0.5}
    assert to_road.properties["surface"]
    assert to_road.properties["area_from_id"] == "area_trail"
    assert to_road.properties["area_to_id"] == "area_wild_1_1"
    # The way is named for the placed area the author wrote, not for a cell.
    assert to_road.properties["area_from"] == "Camp Entrance Trail"
    # Four connection edges, like every generated way.
    seam_edges = [e for e in patch.edges
                  if "way_wild_area_trail_area_wild_1_1" in (e.source, e.target)]
    assert len(seam_edges) == 4


def test_a_storey_step_out_of_a_placed_area_is_a_climb():
    m, g = _placed_on_a_road()
    wg.paint(m["wild"], "floor", 1, 0, 2)          # the placed cell is two up
    patch = world_compile.compile_grid(m, "wild", region_merge=False, graph=g)

    seam = [n for n in _boundary_ways(patch)
            if n.properties["area_to_id"] == "area_wild_1_1"]
    assert len(seam) == 1
    assert seam[0].properties["kind"] == "stairs"
    assert seam[0].properties["floor_step"] == 2
    assert "climb" in seam[0].properties["pass_message"]


def test_two_placed_areas_side_by_side_get_one_way_not_two():
    m = _painted(roads={(0, 1): "road"}, biomes={(1, 0): "sparse_forest"},
                 w=3, h=2)
    wg.place_area(m, "wild", "area_trail", 0, 0)
    wg.place_area(m, "wild", "area_well", 1, 0)
    g = WorldGraph()
    for area_id, name in (("area_trail", "Trail"), ("area_well", "Well")):
        g.add_node(Node(id=area_id, type="area", name=name))

    patch = world_compile.compile_grid(m, "wild", region_merge=False, graph=g)
    ids = [n.id for n in _boundary_ways(patch, "area_trail", "area_well")]
    assert ids.count("way_wild_area_trail_area_well") == 1
    # And both are joined to the road, not left as two islands beside it.
    assert "way_wild_area_trail_area_wild_0_1" in ids
    assert "way_wild_area_well_area_wild_0_1" in ids


def test_the_report_says_how_many_seams_were_minted():
    m, g = _placed_on_a_road()
    patch = world_compile.compile_grid(m, "wild", region_merge=False, graph=g)
    assert any("1 hand-placed area(s) on the grid, 5 way(s) minted" in note
               for note in patch.report.notes)


def test_a_placed_area_with_no_node_is_reported_not_given_a_nameless_way():
    """The record knows the placement; only the graph knows its name."""
    m = _painted(roads={(1, 1): "road"}, biomes={(0, 0): "sparse_forest"}, w=3, h=2)
    wg.place_area(m, "wild", "area_trail", 1, 0)

    patch = world_compile.compile_grid(m, "wild", region_merge=False, graph=WorldGraph())
    assert _boundary_ways(patch) == []
    assert any("could not be named" in note and "area_trail" in note
               for note in patch.report.notes)


def test_without_a_graph_the_boundary_pass_reports_and_the_rest_compiles():
    """`graph` is only needed to name a placement; everything else still mints."""
    m, g = _placed_on_a_road()
    patch = world_compile.compile_grid(m, "wild", region_merge=False)
    assert _boundary_ways(patch) == []
    assert [n for n in patch.nodes if n.type == "area"]     # the painted ones minted
    assert any("could not be named" in note for note in patch.report.notes)


# ─── the author owns a minted seam (task-528) ──────────────────────────────


def test_a_suppressed_seam_is_not_minted_again():
    m, g = _placed_on_a_road()
    first = world_compile.compile_grid(m, "wild", region_merge=False, graph=g)
    seam = "way_wild_area_trail_area_wild_1_1"
    assert seam in [n.id for n in first.nodes]

    wg.set_boundary_override(m["wild"], seam, "suppress")
    again = world_compile.compile_grid(m, "wild", region_merge=False, graph=g)
    assert seam not in [n.id for n in again.nodes]
    # The other seams are untouched: suppressing one is not suppressing the area.
    assert len(_boundary_ways(again)) == 4
    assert any("1 boundary way(s) left as the author set them" in note
               for note in again.report.notes)


def test_a_hand_replaced_seam_is_not_minted_again():
    m, g = _placed_on_a_road()
    wg.set_boundary_override(m["wild"], "way_wild_area_trail_area_wild_1_1",
                             "hand", hand_way_id="way_my_own_step")
    patch = world_compile.compile_grid(m, "wild", region_merge=False, graph=g)
    assert "way_wild_area_trail_area_wild_1_1" not in [n.id for n in patch.nodes]
    assert wg.boundary_override(m["wild"], "way_wild_area_trail_area_wild_1_1") == {
        "action": "hand", "way_id": "way_my_own_step"}


def test_clearing_an_override_hands_the_seam_back_to_the_compiler():
    m, g = _placed_on_a_road()
    seam = "way_wild_area_trail_area_wild_1_1"
    wg.set_boundary_override(m["wild"], seam, "suppress")
    wg.set_boundary_override(m["wild"], seam, None)

    patch = world_compile.compile_grid(m, "wild", region_merge=False, graph=g)
    assert seam in [n.id for n in patch.nodes]
    assert wg.boundary_overrides(m["wild"]) == {}


def test_an_override_only_survives_on_the_record_not_the_graph():
    """The point of the record: a regenerate must not undo the author's call."""
    m, g = _placed_on_a_road()
    patch = world_compile.compile_grid(m, "wild", region_merge=False, graph=g)
    generation.apply_patch(g, m, patch)

    seam = "way_wild_area_trail_area_wild_1_1"
    g.remove_node(seam)                      # the author deletes it
    wg.set_boundary_override(m["wild"], seam, "suppress")

    # Ungenerate + Generate is the WorldPainter's "start over" and it must not
    # resurrect a way the author removed.
    world_scopes.ungenerate_scope(m, g, "wild")
    again = world_compile.compile_grid(m, "wild", region_merge=False, graph=g)
    generation.apply_patch(g, m, again, allow_regenerate=True)
    assert g.get_node(seam) is None
    assert len([n for n in g.nodes.values()
                if n.type == "way" and "area_trail" in str(
                    (n.properties or {}).get("area_from_id"))]) == 4


# ── preflight (task-521) ────────────────────────────────────────────────────
# The compiler's own refusals, shaped as advice so the painter can say them
# *before* the click. These two are the ones that cost a real author a session:
# a scope promoted from areas they had already written, and a scope sitting on an
# unpainted cell of its parent, which silently never gets a gateway at all.


def _codes(manifest, scope_id, **kw):
    return {b["code"]: b for b in world_compile.preflight(manifest, scope_id, **kw)}


def test_preflight_reports_nothing_for_a_healthy_scope():
    m = _painted(FOUR)
    found = _codes(m, "wild")
    for code in ("baked", "no-paint", "no-grid", "orphan-placement", "unnamed"):
        assert code not in found, f"{code} should not fire on a healthy scope"


def test_a_baked_scope_with_paint_compiles():
    """A `baked` scope is not a scope that cannot be compiled.

    The flag means "the areas already in here are yours, not mine" — it came from
    promoting areas the author had already written. It does **not** mean the scope
    is closed to paint, and an author who promoted a selection and then painted the
    rest of the room was previously told to delete the scope and start again, with
    70 painted cells of their own work discarded by the advice.

    Nothing overlaps, so there is nothing to exclude: promotion clears the promoted
    area's painted cell (inside the new scope a position is canvas space), so the
    painted cells compile to areas *beside* the promoted ones. Hand-authored nodes
    carry no ``generated`` provenance, so ``apply_patch`` cannot replace them.
    """
    m = _painted(FOUR)
    m["wild"]["paint_policy"] = world_compile.PAINT_POLICY_BAKED
    m["wild"]["state"] = "materialized"

    patch = world_compile.compile_grid(m, "wild", region_merge=False)
    assert [n for n in patch.nodes if n.type == "area"], (
        "a baked scope that carries paint must still compile it")
    # And preflight agrees: the refusal is gone from both.
    assert "baked" not in _codes(m, "wild")


def test_a_baked_scope_with_nothing_to_compile_says_so():
    """The refusal survives for the case it was written for, in its own words.

    A promoted scope that was never painted has nothing to compile, and the useful
    message is the "nothing to compile" one — not "delete this scope".
    """
    m = _painted({})
    m["wild"]["paint_policy"] = world_compile.PAINT_POLICY_BAKED
    m["wild"]["state"] = "materialized"

    found = _codes(m, "wild")
    assert found["no-paint"]["severity"] == world_compile.BLOCK
    assert "baked" not in found, "a baked scope is not itself a reason to refuse"
    with pytest.raises(ValueError, match="paints no cells"):
        world_compile.compile_grid(m, "wild", region_merge=False)


def test_preflight_and_the_compiler_agree_on_what_is_uncompilable():
    """The two must not drift: a blocker that still compiles is worse than none.

    The case both still agree on is a scope with nothing painted — whatever else is
    true of it, there is nothing to compile, and preflight blocks it and the
    compiler refuses it for the same reason.
    """
    m = _painted({})
    m["wild"]["paint_policy"] = world_compile.PAINT_POLICY_BAKED
    m["wild"]["state"] = "materialized"
    assert "no-paint" in _codes(m, "wild")
    with pytest.raises(ValueError, match="paints no cells"):
        world_compile.compile_grid(m, "wild")


def test_preflight_flags_a_scope_placed_on_an_unpainted_parent_cell():
    m = _painted(FOUR)
    m["wild"]["parent_id"] = "root"
    wg.ensure_grid(m["root"], 4, 4, mode="world")
    wg.paint(m["root"], "road", 3, 3, "road")
    wg.place(m, "root", "wild", 2, 2)          # a hole in the parent's paint

    found = _codes(m, "wild")
    assert found["orphan-placement"]["severity"] == world_compile.BLOCK
    assert "(2,2)" in found["orphan-placement"]["text"]


def test_preflight_is_quiet_about_a_placement_on_a_painted_cell():
    m = _painted(FOUR)
    m["wild"]["parent_id"] = "root"
    wg.ensure_grid(m["root"], 4, 4, mode="world")
    wg.paint(m["root"], "road", 3, 3, "road")
    wg.place(m, "root", "wild", 3, 3)
    assert "orphan-placement" not in _codes(m, "wild")


def test_preflight_does_not_nag_a_wilderness_map_for_names():
    """A forest cell compiling to "Sparse Forest (world 7,4)" is named correctly."""
    m = _painted(FOUR)
    assert "unnamed" not in _codes(m, "wild")


def test_preflight_wants_names_in_a_town():
    m = _painted(FOUR)
    m["wild"]["mode"] = "town"
    found = _codes(m, "wild")
    assert found["unnamed"]["severity"] == world_compile.WARN
    assert "name field" in found["unnamed"]["remedy"]


def test_preflight_quiet_on_names_once_a_town_is_named():
    m = _painted(FOUR)
    m["wild"]["mode"] = "town"
    for (x, y) in FOUR:
        wg.set_name(m["wild"], x, y, "Place")
    assert "unnamed" not in _codes(m, "wild")


def test_preflight_warns_before_the_node_cap_with_the_switch_as_the_remedy():
    """A road run merges into one area, so the count has to follow the switch."""
    m = _manifest({}, w=6, h=3)
    for x in range(6):
        wg.paint(m["wild"], "road", x, 1, "road")

    # Six separate road cells do not merge when the switch is off, and one road
    # does when it is on. The estimate has to see that difference, or it cries
    # wolf about a map that is fine. `max_nodes` is lowered so the cap is
    # reachable without painting 20,000 cells.
    unmerged = world_compile.preflight(m, "wild", region_merge=False,
                                       max_nodes=8)
    merged = world_compile.preflight(m, "wild", region_merge=True, max_nodes=8)
    assert "node-cap" in {b["code"] for b in unmerged}
    assert "merge same-biome" in next(
        b for b in unmerged if b["code"] == "node-cap")["remedy"]
    assert "node-cap" not in {b["code"] for b in merged}


def test_preflight_explains_where_travellers_arrive():
    """The gateway opens into the top-left-most region, which is not obvious."""
    m = _manifest({}, w=4, h=4)
    m["wild"]["parent_id"] = "root"
    wg.ensure_grid(m["root"], 4, 4, mode="world")
    wg.paint(m["root"], "road", 0, 0, "road")
    wg.place(m, "root", "wild", 0, 0)
    wg.paint(m["wild"], "biome", 3, 3, "cottage")

    found = _codes(m, "wild")
    assert "entry-corner" in found
    assert "(3,3)" in found["entry-corner"]["text"]


def test_preflight_reports_a_missing_grid_and_stops_there():
    """Nothing else can be judged without a grid, so it is the only finding."""
    m = {"root": {"id": "root", "name": "Root"},
         "bare": {"id": "bare", "name": "Bare"}}
    assert [b["code"] for b in world_compile.preflight(m, "bare")] == ["no-grid"]


def test_preflight_reports_an_unknown_scope():
    m = _painted(FOUR)
    assert _codes(m, "nope")["no-scope"]["severity"] == world_compile.BLOCK

