"""Compiled ways carry tags (bug-529).

A way is a node, and tags are the generic seam every system reads: matching,
plans, observation, hazards, fear, search. The compiler stamped tags on areas
but not on ways, so an open-air path read "[path] is open" instead of "is clear"
and a way was invisible to tag search.

The writer is ``engine/world_compile.py::emit_passage``; the vocabulary is the
biome/feature records in ``data/worldpainter/biomes.json``. See
``docs/design/way-tags.md``.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import world_compile as wc  # noqa: E402
from engine import world_grid as wg  # noqa: E402
from engine.area_tags import is_open_sky  # noqa: E402


def _painted(w, h, biome="sparse_forest", mode="world", paint_cells=()):
    """One gridded scope, every cell painted a biome; optional per-cell overrides
    as (layer, x, y, value)."""
    manifest = {"root": {"id": "root", "name": "Root", "children": ["wild"]},
                "wild": {"id": "wild", "name": "Wild"}}
    wg.ensure_grid(manifest["wild"], w, h, mode=mode)
    for x in range(w):
        for y in range(h):
            wg.paint(manifest["wild"], "biome", x, y, biome)
    for layer, x, y, value in paint_cells:
        wg.paint(manifest["wild"], layer, x, y, value)
    return manifest


def _ways(patch):
    return [n for n in patch.nodes if n.type == "way"]


def test_a_compiled_forest_path_carries_the_biome_and_open_sky_tags():
    patch = wc.compile_grid(_painted(4, 4), "wild", seed="s")
    ways = _ways(patch)
    assert ways, "a 4x4 grid compiles ways"
    for node in ways:
        tags = node.properties.get("tags") or []
        # sparse_forest declares ["forest", "woods"] (data/worldpainter/biomes.json).
        assert "forest" in tags and "woods" in tags, (node.id, tags)
        assert "outdoor" in tags, (node.id, tags)


def test_the_open_sky_tag_is_the_one_the_reader_accepts():
    """The writer/reader loop: the canonical tag the compiler emits must satisfy
    the predicate ``area_description`` uses to choose "is clear" over "is open".
    """
    patch = wc.compile_grid(_painted(3, 3), "wild", seed="s")
    way = _ways(patch)[0]
    tags = way.properties.get("tags") or []
    assert is_open_sky(tags) is True, (way.id, tags)


def test_an_interior_way_is_not_open_sky():
    # Interior mode is built space: no `outdoor`, and the predicate agrees.
    patch = wc.compile_grid(_painted(3, 3, biome="bank", mode="interior"),
                            "wild", seed="s")
    ways = _ways(patch)
    assert ways, "a 3x3 interior grid compiles ways"
    for node in ways:
        tags = node.properties.get("tags") or []
        assert "outdoor" not in tags, (node.id, tags)
        assert is_open_sky(tags) is False, (node.id, tags)


def test_a_road_cell_writes_its_route_tag_onto_the_way():
    # A road is a *feature* cell; a way along it carries the feature's tags
    # (`road`), so a route is taggable independently of the biome under it.
    patch = wc.compile_grid(
        _painted(3, 1, paint_cells=[("road", x, 0, "road") for x in range(3)]),
        "wild", seed="s")
    road_ways = [n for n in _ways(patch)
                 if "road" in (n.properties.get("tags") or [])]
    assert road_ways, "a painted road should tag the ways along it"


def test_a_stair_way_carries_the_stairs_tag():
    # Two biomes that do not merge, one storey apart: the way between them
    # crosses a storey step, so its kind is `stairs` and it is tagged `stairs`.
    grid = _painted(2, 1, paint_cells=[("biome", 1, 0, "farmland"),
                                       ("floor", 1, 0, 1)])
    patch = wc.compile_grid(grid, "wild", seed="s")
    stairs = [n for n in _ways(patch) if n.properties.get("kind") == "stairs"]
    assert stairs, "a one-storey step between regions should mint a stairs way"
    for node in stairs:
        assert "stairs" in (node.properties.get("tags") or []), node.id
