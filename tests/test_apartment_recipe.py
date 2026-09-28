"""`apartment.v1`: the first real recipe behind the generation contract (task-398).

The contract in `engine/generation.py` was already implemented, so what is under
test here is the thing it exists to guarantee: that generating a scope is
deterministic, happens exactly once, physically places its items through normal
spatial edges, and never quietly substitutes something for a tag the library
could not satisfy.

The two claims most likely to rot are the boring ones, so they are pinned
directly: same seed means the *same* patch, node for node and edge for edge;
and a second generate changes nothing.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from engine.generation import apply_patch, is_generated
from engine.generation_recipes import RECIPES, apartment_v1, get_recipe
from engine.library_nodes import build_item_subtree, spatial_edge
from engine.population import LibraryIndex
from graph import EDGE_CONNECTION, EDGE_IN, Edge, Node, WorldGraph

DATA = Path(__file__).parent.parent / "data" / "library" / "items"
SCOPE = "apartment_3b"
SEED = "pines-3b-01"
HALLWAY = "area_hallway_3"


@pytest.fixture(scope="module")
def index():
    return LibraryIndex.from_directory(DATA)


@pytest.fixture
def graph():
    g = WorldGraph()
    g.add_node(Node(id=HALLWAY, type="area", name="Hallway 3", properties={}))
    return g


def _patch(index, seed=SEED, entry=HALLWAY, scope=SCOPE):
    return apartment_v1(scope, seed=seed, index=index, entry_area_id=entry)


def _signature(patch):
    return ([n.id for n in patch.nodes],
            [(e.source, e.target, e.type) for e in patch.edges])


# ── the recipe is registered and resolves by version ────────────────────


def test_the_recipe_resolves_by_its_versioned_id():
    assert "apartment.v1" in RECIPES
    assert get_recipe("apartment.v1") is apartment_v1
    assert get_recipe("apartment.v2") is None, "a future version is a new entry"


# ── determinism ─────────────────────────────────────────────────────────


def test_the_same_seed_produces_the_same_patch(index):
    assert _signature(_patch(index)) == _signature(_patch(index))


def test_a_different_seed_produces_a_different_population(index):
    """Otherwise determinism would be trivial: nothing varies at all."""
    assert _signature(_patch(index, seed="pines-3b-01")) != \
           _signature(_patch(index, seed="pines-3b-02"))


def test_generating_twice_still_gives_the_same_nodes(index):
    """The id scheme is derived, not minted, so a repeat cannot rename things."""
    first = [n.id for n in _patch(index).nodes]
    second = [n.id for n in _patch(index).nodes]
    assert first == second


# ── structure: three areas, four ways, one front door ───────────────────


def test_it_makes_three_areas_under_the_scope(index):
    patch = _patch(index)
    assert patch.report.area_ids == [
        "area_apartment_3b_living",
        "area_apartment_3b_bedroom",
        "area_apartment_3b_bathroom",
    ]


def test_every_area_belongs_to_the_scope_in_the_patch(index):
    patch = _patch(index)
    assert patch.area_scope_assignments == {
        area_id: SCOPE for area_id in patch.report.area_ids
    }


def test_the_front_door_connects_the_hallway_and_the_living_room(graph, index):
    """Bidirectional, like every other way: four edges, not two."""
    patch = _patch(index)
    door = "way_apartment_3b_front_door"
    pairs = {(e.source, e.target) for e in patch.edges
             if e.type == EDGE_CONNECTION and door in (e.source, e.target)}
    assert pairs == {(HALLWAY, door), (door, HALLWAY),
                     ("area_apartment_3b_living", door), (door, "area_apartment_3b_living")}


def test_the_internal_doors_reach_bedroom_and_bathroom(graph, index):
    patch = _patch(index)
    for label, room in (("bedroom_door", "bedroom"), ("bathroom_door", "bathroom")):
        door = f"way_apartment_3b_{label}"
        assert door in [n.id for n in patch.nodes]
        targets = {e.target for e in patch.edges
                   if e.type == EDGE_CONNECTION and e.source == door}
        assert f"area_apartment_3b_{room}" in targets


def test_without_an_entry_area_it_says_so_rather_than_inventing_a_hall(index):
    patch = apartment_v1(SCOPE, seed=SEED, index=index, entry_area_id=None)
    assert any("front door" in n for n in patch.report.notes)
    assert not [n for n in patch.nodes if n.id == "way_apartment_3b_front_door"]


# ── provenance ──────────────────────────────────────────────────────────


def test_every_generated_node_carries_provenance(index):
    patch = _patch(index)
    assert patch.nodes, "the recipe produced nothing, so this is vacuous"
    for node in patch.nodes:
        assert is_generated(node), node.id
        assert node.properties["generated"]["scope_id"] == SCOPE
        assert node.properties["generated"]["recipe_id"] == "apartment.v1"
        assert node.properties["generated"]["seed"] == SEED


# ── items are placed through normal spatial edges ───────────────────────


def test_items_are_placed_by_relation_not_by_direct_mutation(index):
    patch = _patch(index)
    item_ids = {n.id for n in patch.nodes if n.type == "item"}
    assert item_ids, "no items were generated"
    placed = [e for e in patch.edges if e.source in item_ids and e.type != "triggers"]
    assert placed, "items must hang off an area or a container by an edge"
    targets = {e.target for e in placed}
    assert targets & set(patch.report.area_ids), "at least some sit in a room"


def test_an_item_placed_in_a_room_can_be_found_by_asking_the_area(index):
    """The lookup an examine/take actually does, on the un-applied patch.

    Any spatial relation counts, not just `in`: the population planner puts
    loose items `at` the area and small ones `in` a container, and
    `engine.character_spatial._item_in_area` treats all of them as present.
    """
    patch = _patch(index)
    living = "area_apartment_3b_living"
    in_living = [n.id for n in patch.nodes if n.type == "item"
                 and any(e.source == n.id and e.target == living
                         for e in patch.edges)]
    assert in_living, "the living room has nothing in it"


def test_a_library_entry_with_missing_content_reports_it_rather_than_shipping_a_lie(index):
    nodes, _edges, missing = build_item_subtree(
        "crate", {"name": "crate", "contents": [{"id": "does_not_exist"}]},
        "item_x_crate", index.entries.get)
    assert missing == ["does_not_exist"]
    assert [n.id for n in nodes] == ["item_x_crate"], "no orphan child node"


# ── tag honesty ─────────────────────────────────────────────────────────


def test_an_unsatisfiable_tag_is_surfaced_never_substituted(index):
    """Ask for a domain the library has nothing for; the report must say so."""
    patch = apartment_v1(SCOPE, seed=SEED, index=index, entry_area_id=HALLWAY)
    # The real tags all resolve, so the report is empty and the rooms are real.
    assert patch.report.unresolved_tags == {}
    assert not patch.report.notes or all("no role-tagged furniture" in n
                                         for n in patch.report.notes)

    empty = LibraryIndex({})
    bare = apartment_v1(SCOPE, seed=SEED, index=empty, entry_area_id=HALLWAY)
    assert bare.report.unresolved_tags, "an empty library is reported, not hidden"
    assert all(v == 0 for v in bare.report.unresolved_tags.values())


def test_rooms_get_different_things_rather_than_one_flat_tag_intersection(index):
    """A bathroom is not a kitchen: budgets and tags are per room."""
    patch = _patch(index)
    def items_in(area_id):
        return {n.id.rsplit("_", 1)[-1] for n in patch.nodes
                if n.type == "item" and any(e.source == n.id and e.target == area_id
                                            for e in patch.edges)}
    bedroom = items_in("area_apartment_3b_bedroom")
    bathroom = items_in("area_apartment_3b_bathroom")
    assert bedroom != bathroom


# ── once only ───────────────────────────────────────────────────────────


def test_applying_makes_the_scope_materialized(graph, index):
    manifest = {SCOPE: {"id": SCOPE, "name": "Apartment 3B", "kind": "apartment",
                        "parent_id": "pines_floor_3", "children": [],
                        "area_ids": [], "state": "unmade",
                        "recipe": "apartment.v1", "seed": SEED}}
    report = apply_patch(graph, manifest, _patch(index))
    assert report.node_count > 0
    assert manifest[SCOPE]["state"] == "materialized"
    assert manifest[SCOPE]["area_ids"] == report.area_ids


def test_a_second_generation_is_rejected_and_changes_nothing(graph, index):
    manifest = {SCOPE: {"id": SCOPE, "name": "Apartment 3B", "kind": "apartment",
                        "parent_id": "pines_floor_3", "children": [],
                        "area_ids": [], "state": "unmade",
                        "recipe": "apartment.v1", "seed": SEED}}
    apply_patch(graph, manifest, _patch(index))
    before_nodes = set(graph.nodes)
    before_edges = {(e.source, e.target, e.type) for e in graph.edges}

    with pytest.raises(ValueError, match="already materialized"):
        apply_patch(graph, manifest, _patch(index))

    assert set(graph.nodes) == before_nodes, "a rejected apply must not half-write"
    assert {(e.source, e.target, e.type) for e in graph.edges} == before_edges


def test_a_second_generation_makes_no_duplicate_nodes(graph, index):
    manifest = {SCOPE: {"id": SCOPE, "name": "Apartment 3B", "kind": "apartment",
                        "parent_id": "pines_floor_3", "children": [],
                        "area_ids": [], "state": "unmade",
                        "recipe": "apartment.v1", "seed": SEED}}
    apply_patch(graph, manifest, _patch(index))
    first = len([n for n in graph.nodes.values() if is_generated(n)])

    with pytest.raises(ValueError):
        apply_patch(graph, manifest, _patch(index))

    assert len([n for n in graph.nodes.values() if is_generated(n)]) == first


def test_a_manual_edit_to_a_generated_item_survives_a_refused_second_generate(graph, index):
    """The acceptance case: re-running must not be able to erase hand edits."""
    manifest = {SCOPE: {"id": SCOPE, "name": "Apartment 3B", "kind": "apartment",
                        "parent_id": "pines_floor_3", "children": [],
                        "area_ids": [], "state": "unmade",
                        "recipe": "apartment.v1", "seed": SEED}}
    apply_patch(graph, manifest, _patch(index))
    edited_id = next(n.id for n in graph.nodes.values()
                     if n.type == "item" and is_generated(n))
    graph.get_node(edited_id).properties["description"] = "hand-edited"

    with pytest.raises(ValueError):
        apply_patch(graph, manifest, _patch(index))

    assert graph.get_node(edited_id).properties["description"] == "hand-edited"


# ── the graph-free promise ──────────────────────────────────────────────


def test_the_recipe_touches_no_graph_and_no_manifest(index):
    """Pure function: the patch is the only output, so preview is free."""
    g = WorldGraph()
    g.add_node(Node(id=HALLWAY, type="area", name="Hallway 3", properties={}))
    before = set(g.nodes)
    patch = _patch(index)
    assert set(g.nodes) == before, "the recipe wrote to a graph it was not given"
    assert patch.generated_manifest_updates["state"] == "materialized"


def test_the_recipe_makes_no_resident_character(index):
    """`vacant` is the default, and nothing manufactures an LLM character."""
    patch = _patch(index)
    assert not [n for n in patch.nodes if n.type in ("character", "player")], (
        "apartment.v1 generates a vacant apartment; a resident must be "
        "explicitly requested, not invented")


def test_a_spatial_edge_uses_the_existing_relation_vocabulary():
    assert spatial_edge("a", "b", "on").type == "on"
    assert spatial_edge("a", "b", "in").type == EDGE_IN
    assert spatial_edge("a", "b", "nonsense").type == EDGE_IN, "unknown falls back to in"
