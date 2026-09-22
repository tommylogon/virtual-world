"""Character expression packs (SillyTavern-style) — backend tests.

A character node can hold `expressions = { key: {profile, full} }`, keyed by an
emotion or action name. `image` / `profile_image` remain the neutral fallbacks.
"""
import io
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from player import Player
from app import create_app


def _setup(tmp_path):
    app = create_app({"TESTING": True})
    app.config['IMAGES_DIR'] = str(tmp_path)
    world = app.world
    p = Player("Kaelen")
    world.add_player(p)
    node_id = world.player_manager.get_player_node_id("Kaelen")
    return app, world, node_id


def _upload(client, node_id, kind=None, expression=None, filename="art.png"):
    data = {"file": (io.BytesIO(b"fake-image-bytes"), filename)}
    if kind:
        data["kind"] = kind
    if expression:
        data["expression"] = expression
    return client.post(f"/api/graph/node/{node_id}/image", data=data,
                       content_type="multipart/form-data")


def _remove(client, node_id, kind, expression):
    return client.post(f"/api/graph/node/{node_id}/image/remove",
                       json={"kind": kind, "expression": expression})


class TestExpressionUpload:

    def test_legacy_upload_still_sets_image(self, tmp_path):
        app, world, node_id = _setup(tmp_path)
        node = world.graph.get_node(node_id)
        with app.test_client() as c:
            res = _upload(c, node_id)
            assert res.status_code == 200
        assert node.properties["image"].startswith("/static/images/nodes/")
        assert node.properties["expressions"]["neutral"]["full"] == node.properties["image"]

    def test_profile_expression_slot(self, tmp_path):
        app, world, node_id = _setup(tmp_path)
        node = world.graph.get_node(node_id)
        with app.test_client() as c:
            res = _upload(c, node_id, kind="profile", expression="angry")
            assert res.get_json()["expression"] == "angry"
        slot = node.properties["expressions"]["angry"]
        assert slot["profile"].startswith("/static/images/nodes/")
        assert "full" not in slot
        # A non-neutral slot must not clobber the neutral fallbacks.
        assert not node.properties.get("image")
        assert not node.properties.get("profile_image")

    def test_neutral_profile_sets_profile_fallback(self, tmp_path):
        app, world, node_id = _setup(tmp_path)
        node = world.graph.get_node(node_id)
        with app.test_client() as c:
            _upload(c, node_id, kind="profile", expression="neutral")
        assert node.properties["profile_image"].startswith("/static/images/nodes/")

    def test_reupload_replaces_and_deletes_old_file(self, tmp_path):
        app, world, node_id = _setup(tmp_path)
        node = world.graph.get_node(node_id)
        with app.test_client() as c:
            _upload(c, node_id, kind="full", expression="happy")
            first = node.properties["expressions"]["happy"]["full"]
            _upload(c, node_id, kind="full", expression="happy")
            second = node.properties["expressions"]["happy"]["full"]
        assert first != second
        assert not os.path.isfile(os.path.join(str(tmp_path), os.path.basename(first)))
        assert os.path.isfile(os.path.join(str(tmp_path), os.path.basename(second)))

    def test_bad_kind_rejected(self, tmp_path):
        app, world, node_id = _setup(tmp_path)
        with app.test_client() as c:
            res = _upload(c, node_id, kind="sideways", expression="happy")
        assert res.status_code == 400


class TestExpressionRemove:

    def test_remove_slot_and_file(self, tmp_path):
        app, world, node_id = _setup(tmp_path)
        node = world.graph.get_node(node_id)
        with app.test_client() as c:
            _upload(c, node_id, kind="profile", expression="sad")
            url = node.properties["expressions"]["sad"]["profile"]
            res = _remove(c, node_id, "profile", "sad")
            assert res.status_code == 200
        assert "sad" not in node.properties.get("expressions", {})
        assert not os.path.isfile(os.path.join(str(tmp_path), os.path.basename(url)))

    def test_remove_neutral_clears_fallback(self, tmp_path):
        app, world, node_id = _setup(tmp_path)
        node = world.graph.get_node(node_id)
        with app.test_client() as c:
            _upload(c, node_id, kind="full", expression="neutral")
            _remove(c, node_id, "full", "neutral")
        assert "image" not in node.properties
        assert "neutral" not in node.properties.get("expressions", {})


class TestSpawnCarriesExpressions:
    """The library template's pack must land on the spawned character node."""

    def test_spawn_copies_pack(self):
        world = create_app({"TESTING": True}).world
        p = Player("Zed")

        lib_pack = {"angry": {"profile": "/static/images/nodes/z-profile.png"},
                    "happy": {"full": "/static/images/nodes/z-full.png"}}
        world.effects._hydrate_character = lambda cid, params, gs: (
            p, {"image": "/static/images/nodes/z-full.png",
                "profile_image": "/static/images/nodes/z-profile.png",
                "expressions": lib_pack})
        world.effects._render_template_fn = lambda msg, ctx: msg

        world.effects.handle_spawn_character({"character_id": "zed"}, {}, game_state=world)

        node = world.graph.get_node(world.player_manager.get_player_node_id("Zed"))
        assert node is not None
        assert node.properties["expressions"] == lib_pack
        assert node.properties["profile_image"] == "/static/images/nodes/z-profile.png"

    def test_spawn_without_pack_is_fine(self):
        world = create_app({"TESTING": True}).world
        p = Player("Plain")
        world.effects._hydrate_character = lambda cid, params, gs: (p, {})
        world.effects._render_template_fn = lambda msg, ctx: msg
        world.effects.handle_spawn_character({"character_id": "plain"}, {}, game_state=world)
        node = world.graph.get_node(world.player_manager.get_player_node_id("Plain"))
        assert node is not None
        assert "expressions" not in node.properties


class TestLibraryImportCarriesExpressions:

    def test_import_copies_pack(self, monkeypatch):
        app = create_app({"TESTING": True})
        pack = {"happy": {"profile": "/static/images/nodes/lib-happy.png"}}
        cdata = {"name": "Libra", "expressions": pack,
                 "profile_image": "/static/images/nodes/lib-profile.png",
                 "inventory": []}
        monkeypatch.setattr(
            "routes.library_ops.load_registry",
            lambda data_dir, name: ({"libra": cdata} if name == "characters.json" else {}),
        )
        with app.test_client() as c:
            res = c.post("/api/library/import/character/libra", json={"active": False})
            assert res.status_code == 200

        node = app.world.graph.get_node(
            app.world.player_manager.get_player_node_id("Libra"))
        assert node is not None
        assert node.properties["expressions"] == pack
        assert node.properties["profile_image"] == "/static/images/nodes/lib-profile.png"
