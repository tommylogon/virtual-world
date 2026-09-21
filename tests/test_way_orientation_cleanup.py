"""`clear_way_fix_fields` removes only the exact minted templates (task-395).

The rework deleted the bulk "fix_way_orientation" fill that had written invented
`cardinal: north`, `"You pass through <name>."` pass messages and
`"A glimpse of <area> beyond."` direction text onto every way. Remediation is now
on demand, and the whole point is that it must never touch *authored* prose — so
this pins both directions: minted values go, author-written values stay.

The op had no test at all when the task was closed (the task's own verification
listed unrelated test files), which is why this exists.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from graph import Node, Edge, EDGE_CONNECTION

WAY_NAME = "Dusty Passage"


def _client():
    app = create_app({"TESTING": True})
    return app.test_client(), app


def _seed(app):
    """The property layout the real data uses: `pass_message` is a **way node**
    property, while `direction`, `visible_in_direction` and `cardinal` live on the
    **connection edge** (60 edges carry a cardinal in the camp; no way node does)."""
    graph = app.world.graph
    graph.add_node(Node(id="area_north_yard", type="area", name="North Yard",
                        properties={"description": "A yard."}))
    # A way carrying the exact minted pass message.
    graph.add_node(Node(id="way_minted", type="way", name=WAY_NAME,
                        properties={"pass_message": f"You pass through {WAY_NAME}."}))
    # A way carrying author-written prose.
    graph.add_node(Node(id="way_authored", type="way", name="Old Oak Door",
                        properties={"pass_message": "The old oak door groans open."}))
    graph.add_edge(Edge(source="area_north_yard", target="way_minted",
                        type=EDGE_CONNECTION, properties={
                            "direction": "north trail",   # not a real cardinal
                            "visible_in_direction": "A glimpse of area_north_yard beyond.",
                            "cardinal": "north",
                        }))
    graph.add_edge(Edge(source="area_north_yard", target="way_authored",
                        type=EDGE_CONNECTION, properties={
                            "direction": "north",         # a real cardinal
                            "visible_in_direction": "A glimpse of the yard beyond.",
                            "cardinal": "north",
                        }))
    return graph


def _run_clear(client, way_ids):
    resp = client.post("/api/graph/batch", json={"ops": [
        {"type": "clear_way_fix_fields", "payload": {"way_ids": way_ids}},
    ]})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["status"] == "success"
    return data["applied"][0]


def _edge(graph, way_id):
    return next(e for e in graph.edges
                if e.type == EDGE_CONNECTION and e.target == way_id)


def test_minted_templates_are_removed():
    client, app = _client()
    graph = _seed(app)

    result = _run_clear(client, ["way_minted"])

    assert result["count"] >= 2
    minted = graph.get_node("way_minted")
    assert "pass_message" not in minted.properties, "minted pass_message survived"
    edge = _edge(graph, "way_minted")
    assert "visible_in_direction" not in edge.properties
    assert "cardinal" not in edge.properties, (
        "a 'north' cardinal on a non-cardinal direction survived"
    )


def test_authored_values_survive():
    """The exact-string match is the safety property: author prose must not go."""
    client, app = _client()
    graph = _seed(app)

    _run_clear(client, ["way_authored"])

    authored = graph.get_node("way_authored")
    assert authored.properties["pass_message"] == "The old oak door groans open."
    edge = _edge(graph, "way_authored")
    assert edge.properties["visible_in_direction"] == "A glimpse of the yard beyond."
    # Its direction really is a cardinal, so the cardinal is not a mint.
    assert edge.properties["cardinal"] == "north"


def test_scoping_by_way_ids_leaves_other_ways_alone():
    client, app = _client()
    graph = _seed(app)

    _run_clear(client, ["way_authored"])  # deliberately NOT way_minted

    assert graph.get_node("way_minted").properties["pass_message"] == f"You pass through {WAY_NAME}."


def test_no_way_ids_means_every_way():
    client, app = _client()
    graph = _seed(app)

    result = _run_clear(client, [])

    assert result["count"] >= 2
    assert "pass_message" not in graph.get_node("way_minted").properties
    assert graph.get_node("way_authored").properties["pass_message"] == "The old oak door groans open."


def test_it_is_idempotent():
    """A second run touches nothing — the UI runs it on every click."""
    client, app = _client()
    graph = _seed(app)

    first = _run_clear(client, [])
    second = _run_clear(client, [])

    assert first["count"] >= 2
    assert second["count"] == 0
    assert graph.get_node("way_authored").properties["pass_message"] == "The old oak door groans open."
