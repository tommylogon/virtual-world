"""Route tests for the WorldPainter grid authoring API (task-495)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app


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
    assert vocab["layers"] == ["biome", "road", "elevation"]
    assert set(vocab["modes"]) == {"world", "town", "interior"}


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


def _paint(client, scope_id, cells):
    for (x, y), biome in cells.items():
        resp = client.post(f"/api/world/scopes/{scope_id}/grid/paint",
                           json={"layer": "biome", "x": x, "y": y, "value": biome})
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
