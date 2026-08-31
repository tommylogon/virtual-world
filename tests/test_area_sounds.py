"""Area sounds route tests (task-173): GET /api/areas/<id>/sounds lists active
sound sources in that area."""

import pytest

from app import create_app
from graph import Node, Edge, EDGE_IN


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})


def _find_area_id(app):
    for n in app.world.graph.nodes.values():
        if n.type == "area":
            return n.id
    return None


def test_sounds_empty_when_quiet(app):
    area = _find_area_id(app)
    r = app.test_client().get(f"/api/areas/{area}/sounds")
    assert r.status_code == 200
    assert r.get_json()["sounds"] == []


def test_sounds_list_active_source(app):
    area = _find_area_id(app)
    jukebox = Node(id="item_jukebox", type="item", name="Jukebox", properties={
        "name": "Jukebox", "weight": 20, "tags": ["sound_source"], "current_state": "on",
        "sound_level": 2, "sound_pattern": "a tinny old tune",
    })
    app.world.graph.add_node(jukebox)
    app.world.graph.add_edge(Edge(source=jukebox.id, target=area, type=EDGE_IN))
    r = app.test_client().get(f"/api/areas/{area}/sounds")
    assert r.status_code == 200
    sounds = r.get_json()["sounds"]
    assert len(sounds) == 1
    assert sounds[0]["name"] == "Jukebox"
    assert sounds[0]["level"] == 2


def test_sounds_skip_inactive(app):
    area = _find_area_id(app)
    off = Node(id="item_bell_off", type="item", name="Bell", properties={
        "name": "Bell", "weight": 1, "tags": ["sound_source"], "current_state": "closed",
        "sound_pattern": "a dull clang",
    })
    app.world.graph.add_node(off)
    app.world.graph.add_edge(Edge(source=off.id, target=area, type=EDGE_IN))
    r = app.test_client().get(f"/api/areas/{area}/sounds")
    assert r.get_json()["sounds"] == []


def test_missing_area_404(app):
    r = app.test_client().get("/api/areas/area_nowhere/sounds")
    assert r.status_code == 404
