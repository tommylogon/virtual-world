"""Route tests for the WorldPainter grid authoring API (task-495, task-528)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from engine import world_scopes
from graph import Node


MANIFEST = {
    "the_pines": {"id": "the_pines", "name": "The Pines", "kind": "building",
                  "state": "materialized"},
    "apt_3b": {"id": "apt_3b", "name": "Apartment 3B", "kind": "apartment",
               "parent_id": "the_pines", "state": "unmade"},
}


def _app(tmp_path):
    app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})
    app.world.world_scopes = {k: dict(v) for k, v in MANIFEST.items()}
    return app


def test_painter_vocabulary_lists_real_ids(tmp_path):
    client = _app(tmp_path).test_client()
    vocab = client.get("/api/world/painter/vocabulary").get_json()

    biome_ids = {b["id"] for b in vocab["biomes"]}
    assert "sparse_forest" in biome_ids and "hills" in biome_ids
    # The editor's old free-text default must not be a real id.
    assert "forest" not in biome_ids
    assert all(b["name"] for b in vocab["biomes"])

    assert "road" in {f["id"] for f in vocab["features"]}
    # `floor` is the storey layer (0 ground, 1 up, -1 down, unbounded); the
    # 0..1 `elevation` height layer it replaced is gone. `climate` is the coarse
    # enum of task-557, which compiles to a per-area base_temperature.
    assert vocab["layers"] == ["biome", "road", "floor", "climate"]
    assert set(vocab["modes"]) == {"world", "town", "interior"}

    # The climates come from the same table the compiler aggregates against, so
    # the palette cannot show one base °C while the compiler writes another.
    climate_ids = {c["id"] for c in vocab["climates"]}
    assert climate_ids == {"arctic", "alpine", "temperate", "arid", "tropical"}
    assert vocab["default_climate"] == "temperate"
    assert all(isinstance(c["base"], (int, float)) for c in vocab["climates"])

    # A building carries the line its door will give, so the cell inspector can
    # show it (task-563). Built by the compiler's own function, so the preview
    # cannot drift from what the world says.
    by_id = {b["id"]: b for b in vocab["biomes"]}
    assert by_id["inn"]["refusal"].startswith("The inn's ")
    assert by_id["watch_house"]["refusal"] != by_id["inn"]["refusal"]
    # Nothing that is not a building has a door at all.
    assert by_id["sparse_forest"]["refusal"] == ""
    assert by_id["wall"]["refusal"] == ""


def test_setting_a_cell_name_round_trips_and_clears(tmp_path):
    """A name is metadata about a cell, not paint on it (task-560), so it has its
    own route: the eraser must not wipe it, and clearing must remove the entry."""
    client = _app(tmp_path).test_client()
    scope = client.post("/api/world/scopes", json={
        "name": "Downtown", "mode": "town", "w": 6, "h": 4,
    }).get_json()["scope"]["id"]

    set_name = client.post(f"/api/world/scopes/{scope}/grid/name",
                           json={"x": 3, "y": 1, "name": "The Stag Inn"})
    assert set_name.status_code == 200, set_name.get_data(as_text=True)
    payload = set_name.get_json()
    assert payload["name"] == "The Stag Inn"
    assert payload["names"] == {"3,1": "The Stag Inn"}, "the payload carries it"

    # A name is not paint: clearing the cell keeps it.
    cleared = client.post(f"/api/world/scopes/{scope}/grid/paint",
                          json={"layer": "road", "x": 3, "y": 1, "value": None})
    assert cleared.get_json()["names"] == {"3,1": "The Stag Inn"}

    gone = client.post(f"/api/world/scopes/{scope}/grid/name",
                       json={"x": 3, "y": 1, "name": "   "})
    assert gone.get_json()["names"] == {}, "whitespace clears it"
    assert gone.get_json()["name"] is None

    # A painted building with a name: both facts, independently.
    client.post(f"/api/world/scopes/{scope}/grid/paint",
                json={"layer": "biome", "x": 3, "y": 1, "value": "tavern"})
    client.post(f"/api/world/scopes/{scope}/grid/name",
                json={"x": 3, "y": 1, "name": "The Crooked Mug"})
    both = client.get(f"/api/world/scopes/{scope}/grid").get_json()
    assert both["layers"]["biome"] == {"3,1": "tavern"}
    assert both["names"] == {"3,1": "The Crooked Mug"}


def test_a_cell_name_rejects_nonsense(tmp_path):
    client = _app(tmp_path).test_client()
    scope = client.post("/api/world/scopes", json={
        "name": "Downtown", "mode": "town", "w": 4, "h": 4}).get_json()["scope"]["id"]
    for body in ({"x": 1}, {"x": "a", "y": 1, "name": "x"},
                 {"x": 1, "y": 1, "name": 7}):
        bad = client.post(f"/api/world/scopes/{scope}/grid/name", json=body)
        assert bad.status_code == 400, (body, bad.get_data(as_text=True))
    assert client.post("/api/world/scopes/nope/grid/name",
                       json={"x": 1, "y": 1, "name": "x"}).status_code == 404


def test_get_grid_reports_scope_and_breadcrumb(tmp_path):
    client = _app(tmp_path).test_client()

    root = client.get("/api/world/scopes/the_pines/grid").get_json()
    assert root["scope"]["name"] == "The Pines"
    assert root["grid"] is None and root["mode"] is None
    assert root["breadcrumb"] == [{"id": "the_pines", "name": "The Pines"}]
    assert [c["id"] for c in root["children"]] == ["apt_3b"]

    child = client.get("/api/world/scopes/apt_3b/grid").get_json()
    assert child["parent"] == {"id": "the_pines", "name": "The Pines"}
    assert [b["id"] for b in child["breadcrumb"]] == ["the_pines", "apt_3b"]

    assert client.get("/api/world/scopes/nope/grid").status_code == 404


def test_create_and_resize_grid_round_trip(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()

    resp = client.post("/api/world/scopes/the_pines/grid",
                       json={"w": 4, "h": 3, "cell_scale": 2.5, "mode": "town"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["grid"] == {"w": 4, "h": 3, "cell_scale": 2.5}
    assert data["mode"] == "town"

    # The manifest and to_dict carry it, so a save/load keeps the grid.
    saved = client.get("/api/save").get_json()
    assert saved["world_scopes"]["the_pines"]["grid"]["w"] == 4

    # Bad mode and a non-positive size are rejected.
    assert client.post("/api/world/scopes/the_pines/grid",
                       json={"w": 2, "h": 2, "mode": "dungeon"}).status_code == 400
    assert client.post("/api/world/scopes/the_pines/grid",
                       json={"w": 0, "h": 2}).status_code == 400


def test_paint_and_erase_cell(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes/the_pines/grid", json={"w": 3, "h": 3, "mode": "town"})

    painted = client.post("/api/world/scopes/the_pines/grid/paint",
                          json={"layer": "biome", "x": 1, "y": 2, "value": "forest"})
    assert painted.status_code == 200
    assert painted.get_json()["layers"]["biome"]["1,2"] == "forest"

    erased = client.post("/api/world/scopes/the_pines/grid/paint",
                         json={"layer": "biome", "x": 1, "y": 2, "value": None})
    # Erasing the last cell drops the empty layer entirely.
    assert erased.get_json()["layers"].get("biome", {}) == {}

    assert client.post("/api/world/scopes/the_pines/grid/paint",
                       json={"layer": "nope", "x": 0, "y": 0, "value": "x"}).status_code == 400
    assert client.post("/api/world/scopes/the_pines/grid/paint",
                       json={"layer": "biome", "x": 9, "y": 0, "value": "x"}).status_code == 400


def test_place_move_overlap_and_remove(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes/the_pines/grid", json={"w": 3, "h": 3, "mode": "town"})
    client.post("/api/world/scopes/apt_3b/grid", json={"w": 2, "h": 2, "mode": "interior"})

    placed = client.post("/api/world/scopes/the_pines/grid/place",
                         json={"child_id": "apt_3b", "x": 1, "y": 1})
    assert placed.status_code == 200 and placed.get_json()["status"] == "placed"
    assert placed.get_json()["feature"]["1,1"] == "apt_3b"

    moved = client.post("/api/world/scopes/the_pines/grid/place",
                        json={"child_id": "apt_3b", "x": 2, "y": 0})
    assert moved.get_json()["status"] == "moved"
    assert moved.get_json()["feature"] == {"2,0": "apt_3b"}
    # A move preserves the child record and its own grid.
    child = client.get("/api/world/scopes/apt_3b/grid").get_json()
    assert child["grid"]["w"] == 2

    # A second child cannot clobber the first unless displace is requested.
    client.post("/api/world/scopes", json={"id": "kiosk", "name": "Kiosk",
                                           "parent_id": "the_pines"})
    blocked = client.post("/api/world/scopes/the_pines/grid/place",
                          json={"child_id": "kiosk", "x": 2, "y": 0})
    assert blocked.status_code == 400 and "already holds" in blocked.get_json()["error"]
    displaced = client.post("/api/world/scopes/the_pines/grid/place",
                            json={"child_id": "kiosk", "x": 2, "y": 0, "on_overlap": "displace"})
    assert displaced.get_json()["status"] == "displaced"
    assert displaced.get_json()["feature"] == {"2,0": "kiosk"}

    removed = client.post("/api/world/scopes/the_pines/grid/remove",
                          json={"child_id": "kiosk"})
    assert removed.get_json()["status"] == "removed"
    assert removed.get_json()["feature"] == {}
    # Removing the placement never deletes the child scope.
    child_ids = [c["id"] for c in client.get("/api/world/scopes/the_pines/grid").get_json()["children"]]  # noqa: E501
    assert "kiosk" in child_ids
    assert client.post("/api/world/scopes/the_pines/grid/remove",
                       json={"child_id": "kiosk"}).status_code == 404


def test_create_scope_disambiguates_id_not_name(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()

    first = client.post("/api/world/scopes",
                        json={"id": "the_pines", "name": "The Pines"})
    assert first.status_code == 200
    body = first.get_json()
    assert body["scope"]["id"] == "the_pines_2"
    assert body["scope"]["name"] == "The Pines"

    bad_parent = client.post("/api/world/scopes",
                             json={"name": "Orphan", "parent_id": "ghost"})
    assert bad_parent.status_code == 400

    no_name = client.post("/api/world/scopes", json={})
    assert no_name.status_code == 400


def test_create_feature_with_grid_and_drill_down(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()

    made = client.post("/api/world/scopes", json={
        "name": "Village in the Forest", "parent_id": "the_pines",
        "kind": "settlement", "mode": "town", "w": 3, "h": 3,
    }).get_json()
    village = made["scope"]["id"]
    assert made["scope"]["mode"] == "town"
    assert made["grid"] == {"w": 3, "h": 3, "cell_scale": 1.0}

    # It is a child of the parent, and opens in its own mode.
    parent = client.get("/api/world/scopes/the_pines/grid").get_json()
    assert village in [c["id"] for c in parent["children"]]
    drilled = client.get(f"/api/world/scopes/{village}/grid").get_json()
    assert drilled["mode"] == "town"
    assert drilled["breadcrumb"][0]["id"] == "the_pines"
    assert drilled["breadcrumb"][-1]["id"] == village


def test_rename_scope_changes_name_not_id(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()

    made = client.post("/api/world/scopes", json={"name": "Deep Woods"}).get_json()
    sid = made["scope"]["id"]

    renamed = client.post(f"/api/world/scopes/{sid}/rename",
                          json={"name": "The Deep Woods"})
    assert renamed.status_code == 200
    assert renamed.get_json()["name"] == "The Deep Woods"
    # The id is untouched, so the scope and its grid still resolve.
    assert client.get(f"/api/world/scopes/{sid}/grid").status_code == 200

    assert client.post(f"/api/world/scopes/{sid}/rename",
                       json={"name": "   "}).status_code == 400
    assert client.post("/api/world/scopes/ghost/rename",
                       json={"name": "x"}).status_code == 404


def test_delete_scope_refuses_children_and_deletes_generated_nodes(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()

    # A scope with children cannot be deleted without cascade.
    assert client.post("/api/world/scopes/the_pines/delete",
                       json={}).status_code == 400

    made = client.post("/api/world/scopes", json={
        "name": "Grove", "mode": "town", "w": 2, "h": 1}).get_json()
    sid = made["scope"]["id"]
    _paint(client, sid, {(0, 0): "dense_forest", (1, 0): "dense_forest"})
    gen = client.post(f"/api/world/scopes/{sid}/grid/generate", json={}).get_json()
    area_ids = gen["report"]["area_ids"]
    assert area_ids
    assert all(app.world.graph.get_node(a) is not None for a in area_ids)

    out = client.post(f"/api/world/scopes/{sid}/delete", json={}).get_json()
    assert out["deleted_nodes"] >= len(area_ids)
    for aid in area_ids:
        assert app.world.graph.get_node(aid) is None
    assert client.get(f"/api/world/scopes/{sid}/grid").status_code == 404


def _paint(client, scope_id, cells, roads=None):
    for (x, y), biome in cells.items():
        resp = client.post(f"/api/world/scopes/{scope_id}/grid/paint",
                           json={"layer": "biome", "x": x, "y": y, "value": biome})
        assert resp.status_code == 200
    for (x, y), value in (roads or {}).items():
        resp = client.post(f"/api/world/scopes/{scope_id}/grid/paint",
                           json={"layer": "road", "x": x, "y": y, "value": value})
        assert resp.status_code == 200


def test_set_and_clear_reference(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes/the_pines/grid", json={"w": 4, "h": 4})

    r = client.post("/api/world/scopes/the_pines/grid/reference",
                    json={"image": "/static/images/backgrounds/map.png", "opacity": 0.3})
    assert r.status_code == 200
    ref = r.get_json()["reference"]
    assert ref["image"].endswith("map.png") and ref["visible"] is True
    assert abs(ref["opacity"] - 0.3) < 1e-6

    # Toggling visibility / opacity keeps the image; opacity clamps to [0,1].
    r2 = client.post("/api/world/scopes/the_pines/grid/reference",
                     json={"image": ref["image"], "visible": False, "opacity": 5})
    assert r2.get_json()["reference"]["visible"] is False
    assert r2.get_json()["reference"]["opacity"] == 1.0

    # Clearing removes it; a bad scheme is rejected; a grid is required.
    cleared = client.post("/api/world/scopes/the_pines/grid/reference", json={"image": None})
    assert cleared.get_json()["reference"] is None
    assert client.post("/api/world/scopes/the_pines/grid/reference",
                       json={"image": "javascript:alert(1)"}).status_code == 400
    assert client.post("/api/world/scopes/apt_3b/grid/reference",
                       json={"image": "/static/images/backgrounds/map.png"}).status_code == 400


def test_list_backgrounds_offers_scenario_and_folder_images(tmp_path):
    app = _app(tmp_path)
    app.world.graph_background = {
        "layers": [{"id": "l1", "image": "/static/images/backgrounds/scenario.png"}]}

    root = tmp_path / "approot"
    bgdir = root / "static" / "images" / "backgrounds"
    bgdir.mkdir(parents=True)
    (bgdir / "atlas.png").write_bytes(b"x")
    (bgdir / "notes.txt").write_text("not an image")
    original = app.root_path
    app.root_path = str(root)
    try:
        images = app.test_client().get("/api/world/painter/backgrounds").get_json()["images"]
    finally:
        app.root_path = original

    assert "/static/images/backgrounds/scenario.png" in images
    assert "/static/images/backgrounds/atlas.png" in images
    assert all(not url.endswith(".txt") for url in images)


def test_paint_batch_paints_many_cells_atomically(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes/the_pines/grid", json={"w": 5, "h": 5, "mode": "world"})

    edits = [{"layer": "biome", "x": x, "y": 0, "value": "sparse_forest"}
             for x in range(4)]
    resp = client.post("/api/world/scopes/the_pines/grid/paint_batch", json={"edits": edits})
    assert resp.status_code == 200
    assert resp.get_json()["count"] == 4
    biome = resp.get_json()["layers"]["biome"]
    assert sorted(biome) == ["0,0", "1,0", "2,0", "3,0"]

    # A single bad edit rejects the whole batch — no half-painted route.
    bad = [{"layer": "biome", "x": 0, "y": 1, "value": "hills"},
           {"layer": "biome", "x": 9, "y": 1, "value": "hills"}]
    rejected = client.post("/api/world/scopes/the_pines/grid/paint_batch", json={"edits": bad})
    assert rejected.status_code == 400 and "outside the grid" in rejected.get_json()["error"]
    assert "0,1" not in client.get("/api/world/scopes/the_pines/grid").get_json()["layers"]["biome"]  # noqa: E501

    assert client.post("/api/world/scopes/the_pines/grid/paint_batch",
                       json={"edits": []}).status_code == 400
    assert client.post("/api/world/scopes/nope/grid/paint_batch",
                       json={"edits": edits}).status_code == 404


def test_paint_batch_is_one_undo(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes/the_pines/grid", json={"w": 3, "h": 3})
    edits = [{"layer": "road", "x": i, "y": 0, "value": "road"} for i in range(3)]
    client.post("/api/world/scopes/the_pines/grid/paint_batch", json={"edits": edits})
    assert len(app.world.world_scopes["the_pines"]["layers"]["road"]) == 3

    # One snapshot covers the whole route.
    assert client.post("/api/undo", json={}).status_code == 200
    assert not (app.world.world_scopes["the_pines"].get("layers", {}).get("road"))


def test_generate_compiles_grid_into_walkable_nodes(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes",
                json={"id": "wild", "name": "Wild", "mode": "world", "w": 2, "h": 2})
    _paint(client, "wild", {(0, 0): "sparse_forest", (1, 0): "dense_forest",
                            (0, 1): "hills"})

    resp = client.post("/api/world/scopes/wild/grid/generate", json={})
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["status"] == "generated"
    assert body["scope"]["state"] == "materialized"
    assert body["report"]["node_count"] >= 3
    assert body["report"]["edge_count"] >= 1

    graph = app.world.graph
    area = graph.get_node("area_wild_0_0")
    assert area is not None and area.type == "area"
    assert area.properties["world_scope_id"] == "wild"
    assert area.properties["generated"]["scope_id"] == "wild"
    # The scope now lists its generated areas.
    assert "area_wild_0_0" in app.world.world_scopes["wild"]["area_ids"]

    ways = [n for n in graph.nodes.values()
            if n.type == "way" and n.properties.get("world_scope_id") == "wild"]
    assert ways, "expected at least one generated way"

    # A compiled world is walkable with no engine change.
    exits = app.world.area_description.build_exits_for_area(area.name)
    assert "east" in exits      # to Dense Forest (1,0)
    assert "south" in exits     # to Hills (0,1)


def test_generate_region_merge_collapses_same_biome(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes",
                json={"id": "wild", "name": "Wild", "mode": "world", "w": 2, "h": 2})
    _paint(client, "wild", {(0, 0): "sparse_forest", (1, 0): "sparse_forest"})

    merged = client.post("/api/world/scopes/wild/grid/generate",
                         json={"region_merge": True}).get_json()
    assert merged["report"]["node_count"] == 1
    assert merged["report"]["edge_count"] == 0


def test_generate_is_once_only_unless_regenerate(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes",
                json={"id": "wild", "name": "Wild", "mode": "world", "w": 1, "h": 1})
    _paint(client, "wild", {(0, 0): "sparse_forest"})

    assert client.post("/api/world/scopes/wild/grid/generate", json={}).status_code == 200
    again = client.post("/api/world/scopes/wild/grid/generate", json={})
    assert again.status_code == 409
    assert "already materialized" in again.get_json()["error"]

    regen = client.post("/api/world/scopes/wild/grid/generate",
                        json={"allow_regenerate": True})
    assert regen.status_code == 200
    # Re-apply did not duplicate the way/area nodes.
    areas = [n for n in app.world.graph.nodes.values()
             if n.type == "area" and n.properties.get("world_scope_id") == "wild"]
    assert len(areas) == 1


def test_generate_refuses_a_giant_patch_before_mutating(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes",
                json={"id": "big", "name": "Big", "mode": "world", "w": 60, "h": 60})
    edits = [{"layer": "biome", "x": x, "y": y, "value": "sparse_forest"}
             for x in range(60) for y in range(60)]
    assert client.post("/api/world/scopes/big/grid/paint_batch",
                       json={"edits": edits}).status_code == 200

    capped = client.post("/api/world/scopes/big/grid/generate", json={"max_nodes": 100})
    assert capped.status_code == 400 and "nodes" in capped.get_json()["error"]
    # Refused before mutating: nothing was minted and the scope is still unmade.
    assert app.world.graph.get_node("area_big_0_0") is None
    assert app.world.world_scopes["big"]["state"] != "materialized"


def test_generate_requires_painted_cells(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes",
                json={"id": "wild", "name": "Wild", "mode": "world", "w": 2, "h": 2})

    empty = client.post("/api/world/scopes/wild/grid/generate", json={})
    assert empty.status_code == 400 and "paints no cells" in empty.get_json()["error"]

    # A scope with no grid at all is also rejected (not a crash).
    app.world.world_scopes["bare"] = {"id": "bare", "name": "Bare", "state": "unmade"}
    bare = client.post("/api/world/scopes/bare/grid/generate", json={})
    assert bare.status_code == 400 and "no grid" in bare.get_json()["error"]

    assert client.post("/api/world/scopes/ghost/grid/generate", json={}).status_code == 404


def test_generate_is_undoable(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes",
                json={"id": "wild", "name": "Wild", "mode": "world", "w": 1, "h": 1})
    _paint(client, "wild", {(0, 0): "sparse_forest"})
    client.post("/api/world/scopes/wild/grid/generate", json={})
    assert app.world.graph.get_node("area_wild_0_0") is not None

    assert client.post("/api/undo", json={}).status_code == 200
    assert app.world.graph.get_node("area_wild_0_0") is None


def test_paint_is_undoable(tmp_path):
    """A grid edit pushes a pre-state snapshot so the first Undo reverts it."""
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes/the_pines/grid", json={"w": 2, "h": 2})
    client.post("/api/world/scopes/the_pines/grid/paint",
                json={"layer": "road", "x": 0, "y": 0, "value": "cobble"})
    assert app.world.world_scopes["the_pines"]["layers"]["road"]["0,0"] == "cobble"

    assert client.post("/api/undo", json={}).status_code == 200
    assert not (app.world.world_scopes["the_pines"].get("layers", {}).get("road"))


def test_set_scope_offset_round_trips_and_resets(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes/the_pines/grid", json={"w": 4, "h": 3})

    resp = client.post("/api/world/scopes/the_pines/offset",
                       json={"x": 2.5, "y": -1})
    assert resp.status_code == 200
    assert resp.get_json()["map_offset"] == {"x": 2.5, "y": -1.0}
    # It persists on the world and travels with a save.
    saved = client.get("/api/save").get_json()
    assert saved["world_scopes"]["the_pines"]["map_offset"] == {"x": 2.5, "y": -1.0}
    # The graph grid payload and the flat scope summary both carry it.
    assert client.get("/api/world/scopes/the_pines/grid").get_json()["map_offset"] == {
        "x": 2.5, "y": -1.0}
    flat = client.get("/api/world/scopes?flat=1").get_json()["scopes"]
    pine = next(s for s in flat if s["id"] == "the_pines")
    assert pine["map_offset"] == {"x": 2.5, "y": -1.0}

    reset = client.post("/api/world/scopes/the_pines/offset", json={"reset": True})
    assert reset.get_json()["map_offset"] == {"x": 0.0, "y": 0.0}
    assert "map_offset" not in app.world.world_scopes["the_pines"]

    assert client.post("/api/world/scopes/the_pines/offset",
                       json={"x": "left", "y": 0}).status_code == 400
    assert client.post("/api/world/scopes/ghost/offset", json={"x": 1}).status_code == 404


def test_ungenerate_removes_nodes_but_keeps_the_grid(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes",
                json={"id": "wild", "name": "Wild", "mode": "world", "w": 2, "h": 2})
    _paint(client, "wild", {(0, 0): "sparse_forest", (1, 0): "dense_forest"})
    assert client.post("/api/world/scopes/wild/grid/generate", json={}).status_code == 200
    assert app.world.graph.get_node("area_wild_0_0") is not None

    resp = client.post("/api/world/scopes/wild/grid/ungenerate", json={})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ungenerated" and body["deleted_nodes"] >= 2
    assert app.world.graph.get_node("area_wild_0_0") is None
    rec = app.world.world_scopes["wild"]
    assert rec["state"] == "unmade" and not rec["area_ids"]
    # The painted grid survives, so a clean regenerate works.
    assert rec["layers"]["biome"]["0,0"] == "sparse_forest"
    assert client.post("/api/world/scopes/wild/grid/generate", json={}).status_code == 200
    assert app.world.graph.get_node("area_wild_0_0") is not None

    assert client.post("/api/world/scopes/ghost/grid/ungenerate",
                       json={}).status_code == 404


# --------------------- placing existing areas (task-528) --------------------


def _authored_area(app, area_id="area_hills", name="Northern Hills", **props):
    """A hand-authored area: no ``generated`` provenance, so it can be placed."""
    app.world.graph.add_node(Node(
        id=area_id, type="area", name=name, properties=dict(props)))


def test_place_area_sets_cell_membership_and_manifest_together(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes/the_pines/grid", json={"w": 4, "h": 4})
    _authored_area(app)

    resp = client.post("/api/world/scopes/the_pines/grid/place_area",
                       json={"area_id": "area_hills", "x": 2, "y": 3})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "placed" and body["cell"] == {"x": 2, "y": 3}

    node = app.world.graph.get_node("area_hills")
    assert node.properties["world_scope_id"] == "the_pines"
    assert node.properties["cell"] == {"x": 2, "y": 3}
    # The layout reads canvas coordinates, the compiler writes cell * 40.
    assert node.properties["x"] == 80 and node.properties["y"] == 120
    assert app.world.world_scopes["the_pines"]["area_ids"] == ["area_hills"]
    assert app.world.world_scopes["the_pines"]["area_placements"] == {
        "area_hills": {"x": 2, "y": 3}}

    # The payload carries the placement, and the placed area leaves the candidate
    # list (the default world has hand-authored areas of its own in there).
    assert [(a["id"], a["x"], a["y"]) for a in body["area_placements"]] == [
        ("area_hills", 2, 3)]
    assert "area_hills" not in {a["id"] for a in body["unplaced_areas"]}


def test_place_area_moves_membership_from_the_previous_scope(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes/the_pines/grid", json={"w": 2, "h": 2})
    client.post("/api/world/scopes/apt_3b/grid", json={"w": 2, "h": 2})
    _authored_area(app, world_scope_id="apt_3b")
    app.world.world_scopes["apt_3b"]["area_ids"] = ["area_hills"]

    assert client.post("/api/world/scopes/the_pines/grid/place_area",
                       json={"area_id": "area_hills", "x": 1, "y": 1}).status_code == 200
    assert app.world.world_scopes["the_pines"]["area_ids"] == ["area_hills"]
    assert "area_hills" not in app.world.world_scopes["apt_3b"]["area_ids"]


def test_place_area_refuses_what_it_should(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes/the_pines/grid", json={"w": 2, "h": 2})
    _authored_area(app)
    _authored_area(app, area_id="area_gen", name="Generated",
                   generated={"scope_id": "apt_3b", "recipe_id": "r"})
    app.world.graph.add_node(Node(id="way_1", type="way", name="A to B"))

    def place(body):
        return client.post("/api/world/scopes/the_pines/grid/place_area", json=body)

    assert place({"x": 0, "y": 0}).status_code == 400
    assert place({"area_id": "nope", "x": 0, "y": 0}).status_code == 400
    assert "No area" in place({"area_id": "ghost", "x": 0, "y": 0}).get_json()["error"]
    assert "not an area" in place({"area_id": "way_1", "x": 0, "y": 0}).get_json()["error"]
    gen = place({"area_id": "area_gen", "x": 0, "y": 0})
    assert gen.status_code == 400 and "generated" in gen.get_json()["error"]
    assert place({"area_id": "area_hills", "x": 9, "y": 9}).status_code == 400
    assert client.post("/api/world/scopes/ghost/grid/place_area",
                       json={"area_id": "area_hills", "x": 0, "y": 0}).status_code == 404

    # A grid-less scope is refused too (not a crash).
    app.world.world_scopes["bare"] = {"id": "bare", "name": "Bare", "state": "unmade"}
    assert client.post("/api/world/scopes/bare/grid/place_area",
                       json={"area_id": "area_hills", "x": 0, "y": 0}).status_code == 400
    # Nothing was half-written by any of those refusals.
    assert "area_placements" not in app.world.world_scopes["the_pines"]


def test_place_area_occupied_cell_needs_displace(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes/the_pines/grid", json={"w": 2, "h": 2})
    _authored_area(app, area_id="area_hills", name="Northern Hills")
    _authored_area(app, area_id="area_lake", name="Murk Lake")
    assert client.post("/api/world/scopes/the_pines/grid/place_area",
                       json={"area_id": "area_hills", "x": 1, "y": 1}).status_code == 200

    # The refusal names the *occupant*, so the author knows which one to move.
    clash = client.post("/api/world/scopes/the_pines/grid/place_area",
                        json={"area_id": "area_lake", "x": 1, "y": 1})
    assert clash.status_code == 400 and "Northern Hills" in clash.get_json()["error"]

    ok = client.post("/api/world/scopes/the_pines/grid/place_area",
                     json={"area_id": "area_lake", "x": 1, "y": 1,
                           "on_overlap": "displace"})
    assert ok.status_code == 200 and ok.get_json()["status"] == "displaced"
    rec = app.world.world_scopes["the_pines"]
    assert rec["area_placements"] == {"area_lake": {"x": 1, "y": 1}}
    # The displaced area keeps its membership but loses the cell it sat on.
    displaced = app.world.graph.get_node("area_hills")
    assert "cell" not in displaced.properties
    assert "area_hills" in rec["area_ids"]


def test_place_area_is_one_undo_step(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes/the_pines/grid", json={"w": 2, "h": 2})
    _authored_area(app)
    client.post("/api/world/scopes/the_pines/grid/place_area",
                json={"area_id": "area_hills", "x": 0, "y": 1})
    assert app.world.graph.get_node("area_hills").properties.get("cell")

    assert client.post("/api/undo", json={}).status_code == 200
    node = app.world.graph.get_node("area_hills")
    assert node is not None
    assert "cell" not in node.properties
    assert "area_placements" not in app.world.world_scopes["the_pines"]
    assert not app.world.world_scopes["the_pines"]["area_ids"]


def test_unplace_area_frees_the_cell_but_keeps_the_area(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes/the_pines/grid", json={"w": 2, "h": 2})
    _authored_area(app)
    client.post("/api/world/scopes/the_pines/grid/place_area",
                json={"area_id": "area_hills", "x": 0, "y": 0})

    resp = client.post("/api/world/scopes/the_pines/grid/unplace_area",
                       json={"area_id": "area_hills"})
    assert resp.status_code == 200 and resp.get_json()["status"] == "unplaced"
    node = app.world.graph.get_node("area_hills")
    assert node is not None
    assert not {"cell", "x", "y"} & set(node.properties)
    assert node.properties["world_scope_id"] == "the_pines"
    rec = app.world.world_scopes["the_pines"]
    assert "area_placements" not in rec and rec["area_ids"] == ["area_hills"]
    # Freed, it becomes a candidate again.
    assert "area_hills" in {a["id"] for a in resp.get_json()["unplaced_areas"]}

    assert client.post("/api/world/scopes/the_pines/grid/unplace_area",
                       json={"area_id": "area_hills"}).status_code == 400


def test_generate_never_compiles_onto_a_placed_area(tmp_path):
    """The cell belongs to the hand-placed area; the biome paint under it loses."""
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes",
                json={"id": "wild", "name": "Wild", "mode": "world", "w": 2, "h": 1})
    _paint(client, "wild", {(0, 0): "sparse_forest", (1, 0): "dense_forest"})
    _authored_area(app, area_id="area_hills", name="Northern Hills")
    client.post("/api/world/scopes/wild/grid/place_area",
                json={"area_id": "area_hills", "x": 0, "y": 0})

    assert client.post("/api/world/scopes/wild/grid/generate", json={}).status_code == 200
    graph = app.world.graph
    # The hand-placed area is untouched and no second area was minted on its cell.
    assert graph.get_node("area_hills").properties.get("generated") is None
    assert graph.get_node("area_wild_0_0") is None
    assert graph.get_node("area_wild_1_0") is not None

    # Ungenerating leaves the hand-placed area alone (it has no provenance).
    assert client.post("/api/world/scopes/wild/grid/ungenerate", json={}).status_code == 200
    assert graph.get_node("area_hills") is not None


# ------------------- boundary ways and the author's call (task-528) --------


def _wild_with_a_placed_area(client, app, *, w=3, h=2):
    """A painted world scope with `Camp Entrance Trail` placed at (1,0)."""
    client.post("/api/world/scopes", json={"id": "wild", "name": "Wild",
                                           "mode": "world", "w": w, "h": h})
    _paint(client, "wild", {(0, 0): "sparse_forest", (2, 0): "dense_forest"},
           roads={(0, 1): "road", (1, 1): "road", (2, 1): "road"})
    _authored_area(app, area_id="area_trail", name="Camp Entrance Trail")
    assert client.post("/api/world/scopes/wild/grid/place_area",
                       json={"area_id": "area_trail", "x": 1, "y": 0}).status_code == 200
    return "way_wild_area_trail_area_wild_1_1"


def test_generate_mints_a_boundary_way_from_a_placed_area_to_the_road(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    seam = _wild_with_a_placed_area(client, app)

    report = client.post("/api/world/scopes/wild/grid/generate",
                         json={}).get_json()["report"]
    assert any("1 hand-placed area(s) on the grid, 5 way(s) minted" in note
               for note in report["notes"])

    node = app.world.graph.get_node(seam)
    assert node is not None and node.type == "way"
    assert node.properties["direction"] == "south"
    assert node.properties["kind"] == "open"
    assert node.properties["area_from_id"] == "area_trail"
    assert node.properties["area_to_id"] == "area_wild_1_1"
    # The way is named for the author's area, which only the graph knows.
    assert node.properties["area_from"] == "Camp Entrance Trail"


def test_suppressing_a_seam_deletes_it_and_it_stays_deleted(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    seam = _wild_with_a_placed_area(client, app)
    client.post("/api/world/scopes/wild/grid/generate", json={})
    assert app.world.graph.get_node(seam) is not None
    before = len(app._undo_stack)

    resp = client.post("/api/world/scopes/wild/grid/boundary_override",
                       json={"way_id": seam, "action": "suppress"})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "suppress"
    assert resp.get_json()["deleted_node"] is True
    # One operation, so one undo step: the node and the record go together.
    assert len(app._undo_stack) == before + 1
    assert app.world.graph.get_node(seam) is None

    # The painter can see the decision, and a regenerate respects it.
    payload = client.get("/api/world/scopes/wild/grid").get_json()
    assert [(row["way_id"], row["action"]) for row in payload["boundary_overrides"]] \
        == [(seam, "suppress")]
    assert client.post("/api/world/scopes/wild/grid/ungenerate",
                       json={}).status_code == 200
    assert client.post("/api/world/scopes/wild/grid/generate",
                       json={"allow_regenerate": True}).status_code == 200
    assert app.world.graph.get_node(seam) is None


def test_a_hand_written_replacement_is_recorded_with_its_own_way(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    seam = _wild_with_a_placed_area(client, app)
    client.post("/api/world/scopes/wild/grid/generate", json={})
    app.world.graph.add_node(Node(id="way_my_step", type="way", name="The Old Stile"))

    resp = client.post("/api/world/scopes/wild/grid/boundary_override",
                       json={"way_id": seam, "action": "hand",
                             "hand_way_id": "way_my_step"})
    assert resp.status_code == 200
    assert app.world.graph.get_node(seam) is None
    assert app.world.graph.get_node("way_my_step") is not None
    row = resp.get_json()["boundary_overrides"][0]
    assert row["action"] == "hand" and row["hand_way_id"] == "way_my_step"
    assert row["name"] == seam            # the generated one is gone, so its id

    # A 'hand' override with no way named is not actionable, so it is refused.
    assert client.post("/api/world/scopes/wild/grid/boundary_override",
                       json={"way_id": seam, "action": "hand"}).status_code == 400


def test_clearing_an_override_hands_the_seam_back(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    seam = _wild_with_a_placed_area(client, app)
    client.post("/api/world/scopes/wild/grid/generate", json={})
    client.post("/api/world/scopes/wild/grid/boundary_override",
                json={"way_id": seam, "action": "suppress"})

    resp = client.post("/api/world/scopes/wild/grid/boundary_override",
                       json={"way_id": seam, "action": "auto"})
    assert resp.status_code == 200 and resp.get_json()["status"] == "cleared"
    assert resp.get_json()["boundary_overrides"] == []
    assert client.post("/api/world/scopes/wild/grid/generate",
                       json={"allow_regenerate": True}).status_code == 200
    assert app.world.graph.get_node(seam) is not None


def test_overriding_a_way_that_is_not_a_boundary_is_refused(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    seam = _wild_with_a_placed_area(client, app)
    client.post("/api/world/scopes/wild/grid/generate", json={})
    road_way = "way_wild_area_wild_0_1_area_wild_1_1"

    # Generated, but between two compiled areas: the compiler's to own.
    assert app.world.graph.get_node(road_way) is not None
    assert client.post("/api/world/scopes/wild/grid/boundary_override",
                       json={"way_id": road_way,
                             "action": "suppress"}).status_code == 400

    app.world.graph.add_node(Node(id="way_hand", type="way", name="Hand Written"))
    assert client.post("/api/world/scopes/wild/grid/boundary_override",
                       json={"way_id": "way_hand",
                             "action": "suppress"}).status_code == 400
    assert client.post("/api/world/scopes/wild/grid/boundary_override",
                       json={"way_id": "way_nope",
                             "action": "suppress"}).status_code == 404
    assert app.world.graph.get_node(seam) is not None   # nothing else disturbed


def test_a_feature_cannot_be_placed_on_a_hand_placed_areas_cell(tmp_path):
    """The silent one: a feature on a reserved cell is read as a region, and an
    area placement *removes* the cell from the compile set, so the gateway would
    be skipped without a word. The two kinds cannot share a cell."""
    app = _app(tmp_path)
    client = app.test_client()
    _wild_with_a_placed_area(client, app)
    client.post("/api/world/scopes", json={"id": "deep_woods", "name": "Deep woods",
                                           "parent_id": "wild"})

    resp = client.post("/api/world/scopes/wild/grid/place",
                       json={"child_id": "deep_woods", "x": 1, "y": 0})
    assert resp.status_code == 400
    assert "area_trail" in resp.get_json()["error"]
    # Not even displacing gets past it.
    assert client.post("/api/world/scopes/wild/grid/place",
                       json={"child_id": "deep_woods", "x": 1, "y": 0,
                             "on_overlap": "displace"}).status_code == 400
    # A painted, unoccupied cell is still fine.
    assert client.post("/api/world/scopes/wild/grid/place",
                       json={"child_id": "deep_woods", "x": 0, "y": 1}).status_code == 200


# ------------------- scope membership only, no cell (task-539) ---------------


def test_reassign_area_moves_membership_without_a_cell(tmp_path):
    """A child scope's interiors belong to it without being parked on its grid."""
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes/the_pines/grid", json={"w": 2, "h": 2})
    _authored_area(app, world_scope_id="the_pines")
    app.world.world_scopes["the_pines"]["area_ids"] = ["area_hills"]

    resp = client.post("/api/world/scopes/apt_3b/areas",
                       json={"add": ["area_hills"]})
    assert resp.status_code == 200
    assert resp.get_json()["areas"]["area_hills"] == "assigned"

    props = app.world.graph.get_node("area_hills").properties
    assert props["world_scope_id"] == "apt_3b"
    # Membership is not placement: no cell was invented.
    assert not {"cell", "x", "y"} & set(props)
    # The manifest mirror moved too, or the counts would disagree with the graph.
    assert app.world.world_scopes["apt_3b"]["area_ids"] == ["area_hills"]
    assert "area_hills" not in app.world.world_scopes["the_pines"]["area_ids"]
    # The area now lists in the child scope's own level and not the parent's.
    assert "area_hills" in world_scopes.own_area_ids(app.world.graph, "apt_3b")
    assert "area_hills" not in world_scopes.own_area_ids(app.world.graph, "the_pines")


def test_reassign_is_one_undo_step_for_a_whole_selection(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    _authored_area(app, area_id="area_tent", name="Tent", world_scope_id="the_pines")
    _authored_area(app, area_id="area_pit", name="Pit", world_scope_id="the_pines")
    before = len(app._undo_stack)

    resp = client.post("/api/world/scopes/apt_3b/areas",
                       json={"add": ["area_tent", "area_pit"]})
    assert resp.status_code == 200
    assert app.world.world_scopes["apt_3b"]["area_ids"] == ["area_tent", "area_pit"]
    # A whole selection moves as a single edit, so one Undo puts both back.
    assert len(app._undo_stack) == before + 1
    assert client.post("/api/undo").status_code == 200
    assert app.world.graph.get_node("area_tent").properties["world_scope_id"] == "the_pines"
    assert app.world.graph.get_node("area_pit").properties["world_scope_id"] == "the_pines"


def test_reassign_out_of_a_scope_releases_the_cell_it_was_parked_on(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes/the_pines/grid", json={"w": 3, "h": 3})
    _authored_area(app)
    assert client.post("/api/world/scopes/the_pines/grid/place_area",
                       json={"area_id": "area_hills", "x": 1, "y": 2}).status_code == 200

    resp = client.post("/api/world/scopes/apt_3b/areas",
                       json={"add": ["area_hills"]})
    assert resp.status_code == 200
    body = resp.get_json()
    # The cell belonged to the scope the area just left; both ends are cleared.
    assert body["areas"]["area_hills:cell"] == "released"
    props = app.world.graph.get_node("area_hills").properties
    assert not {"cell", "x", "y"} & set(props)
    rec = app.world.world_scopes["the_pines"]
    assert not (rec.get("area_placements") or {})


def test_reassign_keeps_a_cell_the_area_already_holds_in_the_target_scope(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes/the_pines/grid", json={"w": 3, "h": 3})
    _authored_area(app)
    client.post("/api/world/scopes/the_pines/grid/place_area",
                json={"area_id": "area_hills", "x": 1, "y": 2})

    # Re-assigning to the scope it already sits on changes nothing about the cell.
    resp = client.post("/api/world/scopes/the_pines/areas",
                       json={"add": ["area_hills"]})
    assert resp.status_code == 200
    assert app.world.graph.get_node("area_hills").properties["cell"] == {"x": 1, "y": 2}
    assert app.world.world_scopes["the_pines"]["area_placements"] == {
        "area_hills": {"x": 1, "y": 2}}


def test_removing_an_area_clears_its_scope_and_cell(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes/the_pines/grid", json={"w": 2, "h": 2})
    _authored_area(app, world_scope_id="the_pines")
    client.post("/api/world/scopes/the_pines/grid/place_area",
                json={"area_id": "area_hills", "x": 0, "y": 0})

    resp = client.post("/api/world/scopes/the_pines/areas",
                       json={"remove": ["area_hills"]})
    assert resp.status_code == 200
    props = app.world.graph.get_node("area_hills").properties
    assert "world_scope_id" not in props
    assert not {"cell", "x", "y"} & set(props)
    rec = app.world.world_scopes["the_pines"]
    assert "area_hills" not in rec.get("area_ids", [])
    assert not (rec.get("area_placements") or {})


def test_reassign_refuses_generated_areas_and_unknown_ids(tmp_path):
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes",
                json={"id": "wild", "name": "Wild", "mode": "world", "w": 1, "h": 1})
    _paint(client, "wild", {(0, 0): "sparse_forest"})
    client.post("/api/world/scopes/wild/grid/generate", json={})
    generated = [n for n in app.world.graph.nodes.values()
                 if getattr(n, "type", "") == "area"
                 and (n.properties or {}).get("generated")]

    resp = client.post("/api/world/scopes/apt_3b/areas",
                       json={"add": [generated[0].id]})
    assert resp.status_code == 400
    assert "generated" in resp.get_json()["error"]

    assert client.post("/api/world/scopes/apt_3b/areas",
                       json={"add": ["area_ghost"]}).status_code == 400
    _authored_area(app, area_id="item_thing", name="Thing", kind="junk")
    app.world.graph.get_node("item_thing").type = "item"
    assert client.post("/api/world/scopes/apt_3b/areas",
                       json={"add": ["item_thing"]}).status_code == 400
    assert client.post("/api/world/scopes/ghost/areas",
                       json={"add": ["x"]}).status_code == 404
    assert client.post("/api/world/scopes/apt_3b/areas", json={}).status_code == 400


def test_grid_payload_names_the_owning_scope_of_each_candidate(tmp_path):
    """task-541: the picker groups by scope, so it needs the name, not just the id."""
    app = _app(tmp_path)
    client = app.test_client()
    _authored_area(app, area_id="area_tent", name="Tent", world_scope_id="apt_3b")
    _authored_area(app, area_id="area_orphan", name="Orphan")

    body = client.get("/api/world/scopes/the_pines/grid").get_json()
    by_id = {a["id"]: a for a in body["unplaced_areas"]}
    assert by_id["area_tent"]["scope_id"] == "apt_3b"
    assert by_id["area_tent"]["scope_name"] == "Apartment 3B"
    assert by_id["area_orphan"]["scope_id"] is None
    assert by_id["area_orphan"]["scope_name"] is None


def test_every_scope_route_is_one_undo_step(tmp_path):
    """Every WorldPainter scope handler pushes its own pre-state snapshot, so the
    route-level after_request hook must not add a second one (bug-50): a double
    push makes the first Undo a no-op, because it pops the POST state."""
    app = _app(tmp_path)
    client = app.test_client()
    client.post("/api/world/scopes",
                json={"id": "wild", "name": "Wild", "mode": "world", "w": 2, "h": 2})
    base = len(app._undo_stack)

    assert client.post("/api/world/scopes/wild/rename",
                       json={"name": "Renamed"}).status_code == 200
    assert len(app._undo_stack) == base + 1, "one entry for the rename"
    assert app.world.world_scopes["wild"]["name"] == "Renamed"
    assert client.post("/api/undo").status_code == 200
    assert app.world.world_scopes["wild"]["name"] == "Wild", "one undo reverts it"

    base = len(app._undo_stack)
    assert client.post("/api/world/scopes/wild/offset",
                       json={"x": 3, "y": 4}).status_code == 200
    assert len(app._undo_stack) == base + 1, "one entry for the zone move"
    assert client.post("/api/undo").status_code == 200
    assert (app.world.world_scopes["wild"].get("map_offset") or {}).get("x") in (0, None)

    base = len(app._undo_stack)
    _paint(client, "wild", {(0, 0): "sparse_forest"})
    assert len(app._undo_stack) == base + 1, "one entry for a paint"
    assert client.post("/api/undo").status_code == 200
    assert "0,0" not in (app.world.world_scopes["wild"].get("layers") or {}).get("biome", {})

    base = len(app._undo_stack)
    assert client.post("/api/world/scopes/wild/delete", json={}).status_code == 200
    assert len(app._undo_stack) == base + 1, "one entry for the delete"
    assert client.post("/api/undo").status_code == 200
    assert "wild" in app.world.world_scopes, "one undo brings the scope back"


# ── POST /api/world/promote (task-535) ──────────────────────────────────────

def _promote_ready(app):
    """A painted world scope with one hand-authored area parked on a cell."""
    client = app.test_client()
    client.post("/api/world/scopes",
                json={"id": "wild", "name": "Wild", "mode": "world", "w": 4, "h": 4})
    _paint(client, "wild", {(1, 1): "sparse_forest", (3, 1): "sparse_forest"})
    _authored_area(app, area_id="area_village", name="Eldenford")
    client.post("/api/world/scopes/wild/grid/place_area",
                json={"area_id": "area_village", "x": 1, "y": 1})
    return client


def test_promote_turns_a_placed_area_into_a_child_scope(tmp_path):
    app = _app(tmp_path)
    client = _promote_ready(app)

    resp = client.post("/api/world/promote", json={
        "scope_id": "village", "name": "Eldenford", "area_ids": ["area_village"],
        "parent_id": "wild", "cell": {"x": 1, "y": 1},
        "entry_area_id": "area_village", "mode": "interior"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "promoted" and body["scope_id"] == "village"
    assert body["released_from"] == {"area_village": "wild"}

    record = app.world.world_scopes["village"]
    assert record["parent_id"] == "wild" and record["paint_policy"] == "baked"
    assert app.world.graph.get_node("area_village").properties["world_scope_id"] == "village"
    assert app.world.world_scopes["wild"].get("area_placements", {}) == {}
    # The payload the painter re-reads shows the scope as a placed child.
    grid = client.get("/api/world/scopes/wild/grid").get_json()
    assert [(p["id"], p["x"], p["y"]) for p in grid["placements"]] == [("village", 1, 1)]


def test_grid_payload_carries_the_area_row_the_promote_button_reads(tmp_path):
    """The 🪜 button resolves its area from `area_placements`, not `areas`.

    The painter's promote looked for `payload.areas`, a key this payload has
    never carried, so the button silently returned and did nothing. The row
    shape it now reads is pinned here, because only the route and the browser
    know about it.
    """
    app = _app(tmp_path)
    client = _promote_ready(app)
    payload = client.get("/api/world/scopes/wild/grid").get_json()
    assert "areas" not in payload

    row = [a for a in payload["area_placements"] if a["id"] == "area_village"][0]
    assert row == {"id": "area_village", "name": "Eldenford", "x": 1, "y": 1}


def test_promote_route_mints_no_self_gateway(tmp_path):
    """The painter's one-area button promotes the area standing on the cell.

    The gateway used to resolve to that same area, so the promote answered with
    a way named "Eldenford - Eldenford" leaving and re-entering one area. The
    scope takes the cell and no way is minted.
    """
    app = _app(tmp_path)
    client = _promote_ready(app)

    body = client.post("/api/world/promote", json={
        "scope_id": "village", "name": "Eldenford", "area_ids": ["area_village"],
        "parent_id": "wild", "cell": {"x": 1, "y": 1},
        "entry_area_id": "area_village"}).get_json()
    assert body["way_id"] == ""
    assert app.world.graph.get_node("way_gateway_wild_village") is None
    ways = [n for n in app.world.graph.nodes.values()
            if getattr(n, "type", "") == "way" and "Eldenford" in str(n.name)]
    assert ways == [], f"a way naming the village on both sides: {[w.name for w in ways]}"


def test_promote_route_mints_a_gateway_from_a_doorstep_left_behind(tmp_path):
    app = _app(tmp_path)
    client = _promote_ready(app)
    _authored_area(app, area_id="area_road", name="Human Road")
    client.post("/api/world/scopes/wild/grid/place_area",
                json={"area_id": "area_road", "x": 3, "y": 1})

    body = client.post("/api/world/promote", json={
        "scope_id": "village", "name": "Eldenford", "area_ids": ["area_village"],
        "parent_id": "wild", "cell": {"x": 3, "y": 1},
        "entry_area_id": "area_village"}).get_json()
    way = app.world.graph.get_node(body["way_id"])
    assert way.name == "Human Road - Eldenford"
    assert way.properties["area_from_id"] == "area_road"
    assert way.properties["area_to_id"] == "area_village"


def test_promote_is_one_undo_step(tmp_path):
    app = _app(tmp_path)
    client = _promote_ready(app)
    base = len(app._undo_stack)

    assert client.post("/api/world/promote", json={
        "scope_id": "village", "name": "Eldenford", "area_ids": ["area_village"],
        "parent_id": "wild", "cell": {"x": 1, "y": 1},
        "entry_area_id": "area_village"}).status_code == 200
    assert len(app._undo_stack) == base + 1, "one entry for the whole promote"

    # The scope, its placement and the parent's cell reservation are one step.
    # (Node properties are left alone: the fixture area is injected straight into
    # the graph, so what survives a reload is the serialiser's business, not this
    # route's.)
    assert client.post("/api/undo", json={}).status_code == 200
    assert "village" not in app.world.world_scopes
    wild = app.world.world_scopes["wild"]
    assert "village" not in (wild.get("placements") or {})
    assert wild.get("area_placements", {}) == {"area_village": {"x": 1, "y": 1}}
    assert app.world.graph.get_node("way_gateway_wild_village") is None


def test_promote_refuses_what_it_should(tmp_path):
    app = _app(tmp_path)
    client = _promote_ready(app)
    app.world.world_scopes["taken"] = {"id": "taken", "name": "Taken",
                                       "kind": "scope", "state": "unmade"}
    app.world.graph.add_node(Node(id="way_1", type="way", name="A to B"))

    def promote(**kw):
        body = {"scope_id": "village", "name": "Eldenford",
                "area_ids": ["area_village"], "parent_id": "wild",
                "cell": {"x": 1, "y": 1}, "entry_area_id": "area_village"}
        body.update(kw)
        return client.post("/api/world/promote", json=body)

    assert promote(scope_id="taken").status_code == 400
    assert "already exists" in promote(scope_id="taken").get_json()["error"]
    assert "not an area" in promote(area_ids=["way_1"]).get_json()["error"]
    assert "not an area" in promote(area_ids=["ghost"]).get_json()["error"]
    assert "entry area" in promote(entry_area_id="area_road").get_json()["error"]
    assert "parent" in promote(parent_id="nowhere").get_json()["error"]
    assert "painted place" in promote(cell={"x": 3, "y": 3}).get_json()["error"]
    assert "village" not in app.world.world_scopes
    assert client.post("/api/world/promote", json={"name": "x"}).status_code == 400


def test_a_refused_promote_leaves_nothing_to_undo(tmp_path):
    """The handler pops the snapshot it pushed, so a refusal does not dangle."""
    app = _app(tmp_path)
    client = _promote_ready(app)
    app.world.world_scopes["taken"] = {"id": "taken", "name": "Taken",
                                       "kind": "scope", "state": "unmade"}
    base = len(app._undo_stack)

    assert client.post("/api/world/promote", json={
        "scope_id": "taken", "name": "Eldenford", "area_ids": ["area_village"],
        "parent_id": "wild", "cell": {"x": 1, "y": 1}}).status_code == 400
    assert len(app._undo_stack) == base, "a refusal adds no undo entry"

    # The next undo therefore reverts the op *before* the refusal, not nothing.
    assert client.post("/api/undo", json={}).status_code == 200
    assert app.world.world_scopes["wild"].get("area_placements") in (None, {})
    assert app.world.graph.get_node("area_village") is not None

