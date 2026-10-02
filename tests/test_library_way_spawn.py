"""task-659: the corrected way keys must survive the library spawn and refresh.

`tools/way_property_index.py --check` proves the four hand-maintained lists
agree with the declaration, but that is list comparison. This exercises the real
route against the authored `draft_door` template, which is what makes the fix
observable rather than asserted.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from graph import Node


def test_library_way_spawn_carries_insulation_and_sound_barrier():
    app = create_app({"TESTING": True})
    graph = app.world.graph
    a_name, b_name = "Draft Room A", "Draft Room B"
    for name in (a_name, b_name):
        graph.add_node(Node(id=app.world._area_node_id(name), type="area", name=name))

    client = app.test_client()
    resp = client.post("/api/library/import/way/draft_door",
                       json={"area_from": a_name, "area_to": b_name})
    assert resp.status_code == 200, resp.get_json()
    node = graph.get_node(resp.get_json()["way_node_id"])
    assert node is not None
    assert node.properties["insulation"] == 0.4
    assert node.properties["sound_barrier"] == 0.5


def test_library_way_refresh_applies_insulation_and_sound_barrier():
    app = create_app({"TESTING": True})
    graph = app.world.graph
    node = Node(id="way_draft_door_live", type="way", name="Draft door",
                properties={"current_state": "open"})
    graph.add_node(node)

    client = app.test_client()
    resp = client.post(f"/api/ways/{node.id}/refresh-from-library",
                       json={"sections": ["insulation", "sound_barrier"]})
    assert resp.status_code == 200, resp.get_json()
    updated = graph.get_node(node.id)
    assert updated.properties["insulation"] == 0.4
    assert updated.properties["sound_barrier"] == 0.5
