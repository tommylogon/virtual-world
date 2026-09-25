"""WorldPainter scope-grid model (task-495): paint, placements, validation."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from engine import world_grid as wg
from engine import world_scopes


def _manifest():
    return {
        "root": {"id": "root", "name": "Root", "children": ["forest"]},
        "forest": {"id": "forest", "name": "Forest"},
        "village": {"id": "village", "name": "Village"},
        "ruin": {"id": "ruin", "name": "Ruin"},
    }


def _gridded_manifest(w=4, h=3):
    m = _manifest()
    wg.ensure_grid(m["forest"], w, h, cell_scale=10, mode="world")
    return m


# ───────────────────────────── identities ────────────────────────────────


def test_cell_id_round_trips():
    cid = wg.cell_id("forest", 3, 2)
    assert cid == "forest:3,2"
    assert wg.parse_cell_id(cid) == ("forest", 3, 2)
    assert wg.parse_cell_id("garbage") is None


def test_cell_id_is_stable_across_unrelated_edits():
    m = _gridded_manifest()
    before = wg.cell_id("forest", 1, 1)
    wg.paint(m["forest"], "biome", 0, 0, "dense_forest")
    wg.place(m, "forest", "village", 2, 2)
    assert wg.cell_id("forest", 1, 1) == before


# ──────────────────────────── ensure_grid ────────────────────────────────


def test_ensure_grid_sets_size_scale_and_mode():
    m = _gridded_manifest(5, 2)
    forest = m["forest"]
    assert wg.has_grid(forest)
    assert wg.grid_size(forest) == (5, 2)
    assert forest["grid"]["cell_scale"] == 10
    assert forest["mode"] == "world"


def test_ensure_grid_rejects_bad_size_and_mode():
    forest = _manifest()["forest"]
    with pytest.raises(ValueError):
        wg.ensure_grid(forest, 0, 3)
    with pytest.raises(ValueError):
        wg.ensure_grid(forest, 3, -1)
    with pytest.raises(ValueError):
        wg.ensure_grid(forest, 3, 3, mode="galaxy")


def test_ensure_grid_resize_drops_out_of_bounds_paint_and_placements():
    m = _gridded_manifest(4, 4)
    forest = m["forest"]
    wg.paint(forest, "biome", 3, 3, "dense_forest")
    wg.paint(forest, "biome", 0, 0, "sparse_forest")
    wg.place(m, "forest", "village", 3, 3)

    wg.ensure_grid(forest, 2, 2)
    assert wg.painter_at(forest, "biome", 0, 0) == "sparse_forest"
    assert wg.painter_at(forest, "biome", 3, 3) is None
    assert wg.placements(forest) == {}


# ─────────────────────────────── paint ───────────────────────────────────


def test_paint_and_erase():
    forest = _gridded_manifest()["forest"]
    wg.paint(forest, "biome", 1, 2, "dense_forest")
    assert wg.painter_at(forest, "biome", 1, 2) == "dense_forest"
    wg.paint(forest, "biome", 1, 2, None)
    assert wg.painter_at(forest, "biome", 1, 2) is None
    assert forest["layers"] == {}


def test_paint_rejects_unknown_layer_no_grid_and_out_of_bounds():
    m = _gridded_manifest()
    with pytest.raises(ValueError):
        wg.paint(m["forest"], "weather", 0, 0, "rain")
    with pytest.raises(ValueError):
        wg.paint(m["forest"], "biome", 9, 9, "dense_forest")
    with pytest.raises(ValueError):
        wg.paint(m["village"], "biome", 0, 0, "dense_forest")  # no grid


# ────────────────────────────── placement ────────────────────────────────


def test_place_move_remove_and_feature_layer():
    m = _gridded_manifest()
    assert wg.place(m, "forest", "village", 1, 1) == "placed"
    assert wg.cell_of(m["forest"], "village") == (1, 1)
    assert wg.feature_layer(m["forest"]) == {"1,1": "village"}

    assert wg.move(m, "forest", "village", 2, 0) == "moved"
    assert wg.cell_of(m["forest"], "village") == (2, 0)
    assert wg.occupant_at(m["forest"], 1, 1) is None

    assert wg.remove(m, "forest", "village") is True
    assert wg.placements(m["forest"]) == {}
    assert wg.remove(m, "forest", "village") is False


def test_place_forbids_overlap_by_default_and_can_displace():
    m = _gridded_manifest()
    wg.place(m, "forest", "village", 1, 1)
    with pytest.raises(ValueError):
        wg.place(m, "forest", "ruin", 1, 1)
    assert wg.occupant_at(m["forest"], 1, 1) == "village"

    assert wg.place(m, "forest", "ruin", 1, 1, on_overlap="displace") == "displaced"
    assert wg.occupant_at(m["forest"], 1, 1) == "ruin"
    assert wg.feature_layer(m["forest"]) == {"1,1": "ruin"}


def test_place_rejects_missing_parent_child_no_grid_and_off_grid():
    m = _gridded_manifest()
    with pytest.raises(ValueError):
        wg.place(m, "nope", "village", 0, 0)
    with pytest.raises(ValueError):
        wg.place(m, "forest", "ghost", 0, 0)
    with pytest.raises(ValueError):
        wg.place(m, "village", "ruin", 0, 0)          # parent has no grid
    with pytest.raises(ValueError):
        wg.place(m, "forest", "village", 4, 0)        # width is 4 -> x max 3
    with pytest.raises(ValueError):
        wg.place(m, "forest", "village", 0, 0, on_overlap="merge")


def test_move_requires_an_existing_placement():
    m = _gridded_manifest()
    with pytest.raises(ValueError):
        wg.move(m, "forest", "village", 1, 1)


# ────────────────────────────── validate ─────────────────────────────────


def test_validate_clean_grid():
    m = _gridded_manifest()
    wg.paint(m["forest"], "biome", 0, 0, "dense_forest")
    wg.place(m, "forest", "village", 1, 1)
    assert wg.validate(m) == []


def test_validate_flags_problems():
    m = _gridded_manifest()
    forest = m["forest"]
    forest["placements"]["village"] = {"x": 9, "y": 0}       # out of bounds
    forest["placements"]["ghost"] = {"x": 0, "y": 0}         # unknown scope
    forest["placements"]["ruin"] = {"x": 9, "y": 0}          # same cells as village
    forest.setdefault("layers", {})["weather"] = {"0,0": "rain"}  # unknown layer
    problems = wg.validate(m)
    joined = " | ".join(problems)
    assert "out of bounds" in joined
    assert "not a scope" in joined
    assert "unknown paint layer" in joined


def test_validate_flags_paint_without_a_grid():
    m = _manifest()
    m["forest"]["layers"] = {"biome": {"0,0": "dense_forest"}}
    assert any("no grid" in p for p in wg.validate(m))


# ──────────────────────── normalise + round-trip ─────────────────────────


def test_normalise_grid_is_tolerant():
    rec = {"grid": {"w": "4", "h": 3, "cell_scale": "2.5"},
           "mode": "town",
           "layers": {"biome": {"1,1": "dense_forest", "bad": "x"}},
           "placements": {"a": {"x": 1, "y": 2}, "b": "nope"}}
    wg.normalise_grid(rec)
    assert rec["grid"] == {"w": 4, "h": 3, "cell_scale": 2.5}
    assert rec["layers"] == {"biome": {"1,1": "dense_forest"}}
    assert rec["placements"] == {"a": {"x": 1, "y": 2}}


def test_normalise_grid_keeps_placement_link_fields():
    # task-496: a generated parent records the area a placed cell compiled to,
    # so a child generated later can still find its gateway. Normalise must
    # keep those fields rather than stripping them to x/y.
    rec = {"grid": {"w": 2, "h": 2},
           "placements": {"inn": {"x": 0, "y": 0,
                                  "area_id": "area_town_0_0",
                                  "area_name": "Sparse Forest (0,0)"}}}
    wg.normalise_grid(rec)
    assert rec["placements"]["inn"] == {
        "x": 0, "y": 0, "area_id": "area_town_0_0",
        "area_name": "Sparse Forest (0,0)"}


def test_grid_round_trips_through_manifest_and_json():
    m = _gridded_manifest()
    wg.paint(m["forest"], "biome", 0, 0, "dense_forest")
    wg.place(m, "forest", "village", 1, 1)

    # The scope manifest is persisted as-is on the world; normalise must not
    # drop grid fields, and a JSON round-trip must preserve them.
    normalised = world_scopes.normalise_manifest(json.loads(json.dumps(m)))
    forest = normalised["forest"]
    assert forest["grid"] == {"w": 4, "h": 3, "cell_scale": 10.0}
    assert wg.painter_at(forest, "biome", 0, 0) == "dense_forest"
    assert wg.cell_of(forest, "village") == (1, 1)
    assert wg.validate(normalised) == []


def test_normalise_manifest_leaves_a_gridless_scope_untouched():
    normalised = world_scopes.normalise_manifest({
        "forest": {"id": "forest", "name": "Forest"},
    })
    forest = normalised["forest"]
    assert "grid" not in forest
    assert "layers" not in forest
    assert "placements" not in forest


def test_normalise_manifest_cleans_a_malformed_grid():
    normalised = world_scopes.normalise_manifest({
        "forest": {"id": "forest", "name": "Forest",
                   "grid": {"w": 0, "h": 3},
                   "placements": {"village": {"x": 1, "y": 1}}},
    })
    forest = normalised["forest"]
    assert "grid" not in forest          # zero size is not a grid
    assert forest["placements"] == {"village": {"x": 1, "y": 1}}


# ----------------------------- reference image ----------------------------


def test_reference_stores_and_defaults_rect_and_crop():
    m = _gridded_manifest()
    rec = m["forest"]
    wg.set_reference(rec, "/static/images/backgrounds/map.png", opacity=0.4)
    ref = wg.reference(rec)
    assert ref["image"].endswith("map.png")
    # No rect = auto-fit; no crop = the whole image.
    assert wg.reference_rect(rec) is None
    assert wg.reference_crop(rec) == wg.REFERENCE_CROP_DEFAULT


def test_reference_rect_and_crop_round_trip_in_cell_units():
    m = _gridded_manifest()
    rec = m["forest"]
    wg.set_reference(rec, "/static/images/backgrounds/map.png")
    wg.set_reference(rec, "/static/images/backgrounds/map.png",
                     rect={"x": -1.5, "y": 2.0, "w": 8.0, "h": 6.0},
                     crop={"x": 0.1, "y": 0.2, "w": 0.7, "h": 0.6})
    assert wg.reference_rect(rec) == {"x": -1.5, "y": 2.0, "w": 8.0, "h": 6.0}
    assert wg.reference_crop(rec) == {"x": 0.1, "y": 0.2, "w": 0.7, "h": 0.6}
    # A later opacity-only save keeps the layout.
    wg.set_reference(rec, "/static/images/backgrounds/map.png", opacity=0.9)
    assert wg.reference_rect(rec) is not None
    assert wg.reference(rec)["opacity"] == 0.9


def test_reference_reset_and_new_image_drop_the_layout():
    m = _gridded_manifest()
    rec = m["forest"]
    wg.set_reference(rec, "/static/images/backgrounds/one.png",
                     rect={"x": 0, "y": 0, "w": 4, "h": 3})
    wg.set_reference(rec, "/static/images/backgrounds/one.png", reset=True)
    assert wg.reference_rect(rec) is None, "reset returns to auto-fit"

    wg.set_reference(rec, "/static/images/backgrounds/one.png",
                     rect={"x": 0, "y": 0, "w": 4, "h": 3})
    wg.set_reference(rec, "/static/images/backgrounds/two.png")
    assert wg.reference_rect(rec) is None, "a new image auto-fits"


def test_reference_rejects_nonsense_rect_and_clamps_crop():
    m = _gridded_manifest()
    rec = m["forest"]
    wg.set_reference(rec, "/static/images/backgrounds/map.png",
                     rect={"x": 0, "y": 0, "w": 0, "h": 3})       # zero width
    assert wg.reference_rect(rec) is None
    wg.set_reference(rec, "/static/images/backgrounds/map.png",
                     rect={"x": 0, "y": 0, "w": 4, "h": 3},
                     crop={"x": -1, "y": 0, "w": 5, "h": 1})
    assert wg.reference_crop(rec) == {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}


# -------------------------- map offset (task-523) ------------------------


def test_map_offset_defaults_to_zero_and_is_absent():
    m = _gridded_manifest()
    rec = m["forest"]
    assert wg.map_offset(rec) == {"x": 0.0, "y": 0.0}
    assert "map_offset" not in rec, "an unmoved scope stores no offset"


def test_set_map_offset_round_trips_and_zero_clears_it():
    m = _gridded_manifest()
    rec = m["forest"]
    wg.set_map_offset(rec, 3, -2.5)
    assert rec["map_offset"] == {"x": 3.0, "y": -2.5}
    assert wg.map_offset(rec) == {"x": 3.0, "y": -2.5}
    # Back to the painted position = absence, so the manifest stays minimal.
    wg.set_map_offset(rec, 0, 0)
    assert "map_offset" not in rec
    wg.set_map_offset(rec, 1, 1)
    wg.set_map_offset(rec, reset=True)
    assert "map_offset" not in rec


def test_set_map_offset_rejects_nonsense():
    m = _gridded_manifest()
    rec = m["forest"]
    with pytest.raises(ValueError):
        wg.set_map_offset(rec, "left", 0)
    with pytest.raises(ValueError):
        wg.set_map_offset(rec, float("inf"), 0)
    with pytest.raises(ValueError):
        wg.set_map_offset(rec, wg.MAP_OFFSET_LIMIT + 1, 0)


def test_map_offset_survives_manifest_normalisation():
    normalised = world_scopes.normalise_manifest({
        "forest": {"id": "forest", "name": "Forest",
                   "grid": {"w": 4, "h": 3},
                   "map_offset": {"x": 2.5, "y": -1}},
        "bad": {"id": "bad", "name": "Bad", "map_offset": {"x": "nope", "y": 0}},
    })
    assert normalised["forest"]["map_offset"] == {"x": 2.5, "y": -1.0}
    assert "map_offset" not in normalised["bad"]
