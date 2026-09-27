"""Save-repair migrations run by ``WorldGraph.load_from_dict``.

Both are "the save was written by an older recipe" repairs, not gameplay: the
legacy ``door`` node type, and an area whose ``floor`` holds a ground *material*
because the ``grid.v1`` WorldPainter compiler put it there. ``floor`` is a
**storey index** (0 ground, 1 up, -1 down, unbounded) and the material belongs
on ``surface``.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import WorldGraph


def _graph_with(nodes):
    graph = WorldGraph()
    graph.load_from_dict({"nodes": nodes, "edges": []})
    return graph


def test_a_legacy_door_still_becomes_a_way():
    graph = _graph_with({"d1": {"id": "d1", "type": "door", "name": "Door",
                                "properties": {}}})
    assert graph.get_node("d1").type == "way"


def test_a_material_floor_is_repaired_to_a_storey():
    graph = _graph_with({"a1": {
        "id": "a1", "type": "area", "name": "Clearing",
        "properties": {"floor": "dirt", "world_scope_id": "wild"},
    }})
    props = graph.get_node("a1").properties
    assert props["floor"] == 0, "a storey, not a material"
    assert props["surface"] == "dirt", "the material is kept, under its own name"


def test_a_numeric_floor_is_left_alone():
    """Any storey the author chose, including one far outside ±10: the save is the
    truth, so the repair must not round-trip it through a default."""
    for value in (0, 1, -1, 80, -900):
        graph = _graph_with({"a1": {
            "id": "a1", "type": "area", "name": "Deck",
            "properties": {"floor": value, "surface": "steel"},
        }})
        assert graph.get_node("a1").properties["floor"] == value


def test_the_repair_never_overwrites_an_existing_surface():
    graph = _graph_with({"a1": {
        "id": "a1", "type": "area", "name": "Cellar",
        "properties": {"floor": "stone", "surface": "gravel"},
    }})
    props = graph.get_node("a1").properties
    assert props["surface"] == "gravel", "an explicit surface wins"
    assert props["floor"] == 0


def test_only_areas_and_ways_are_touched():
    """An item or trigger carrying a string `floor` is not a place and is left
    exactly as it was — the repair is about area/way storeys."""
    graph = _graph_with({"i1": {
        "id": "i1", "type": "item", "name": "Torn page",
        "properties": {"floor": "dirt"},
    }})
    assert graph.get_node("i1").properties["floor"] == "dirt"


def test_a_way_is_repaired_too():
    """The `grid.v1` recipe put the material on ways as well, and a way's floor
    is a storey too (the lower of the two it joins)."""
    graph = _graph_with({"w1": {
        "id": "w1", "type": "way", "name": "Path",
        "properties": {"floor": "stone", "direction": "north"},
    }})
    props = graph.get_node("w1").properties
    assert props["floor"] == 0
    assert props["surface"] == "stone"
    assert props["direction"] == "north", "the rest of the way is untouched"


def test_an_area_with_no_floor_is_left_alone():
    graph = _graph_with({"a1": {
        "id": "a1", "type": "area", "name": "Field",
        "properties": {"tags": ["farm"]},
    }})
    assert "floor" not in graph.get_node("a1").properties
