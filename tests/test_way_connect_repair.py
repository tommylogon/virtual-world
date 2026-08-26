"""Tests for way connection repair routes.

Covers:
- reconnect preserving view/cardinal props when the stored edge ids are
  mixed-case (legacy ids predating the lowercase-id convention) — the
  previous case-sensitive matching silently dropped those props.
- build_connect being idempotent — connecting an already-wired way must
  remove stale edges instead of accumulating a third side.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from graph import EDGE_CONNECTION, Edge


def _fresh_client():
    app = create_app({'TESTING': True})
    return app.test_client(), app


def _first_way(app):
    return next(
        (n for n in app.world.graph.nodes.values() if n.type == 'way'),
        None
    )


def _conn_areas(app, way_id):
    """Distinct areas wired to the way (both edge directions collapsed)."""
    return sorted({
        e.source if e.target == way_id else e.target
        for e in app.world.graph.edges
        if e.type == EDGE_CONNECTION
        and (e.source == way_id or e.target == way_id)
    })


def test_reconnect_preserves_props_with_mixed_case_edge_ids():
    """Reconnect must keep view/cardinal even when stored edge endpoints
    use legacy mixed-case ids that differ from the requested lowercase ids."""
    client, app = _fresh_client()
    way = _first_way(app)
    assert way is not None

    # Take the two areas currently wired to the way.
    areas = sorted(
        {e.source if e.target == way.id else e.target
         for e in app.world.graph.edges
         if e.type == EDGE_CONNECTION
         and (e.source == way.id or e.target == way.id) and e.source != way.id}
    )
    area_a, area_b = areas[0], areas[1]

    # Corrupt the canonical area -> way edges to mixed case, mimicking
    # legacy data, and stamp a distinctive view/cardinal onto side A.
    app.world.graph.remove_edge(area_a, way.id, EDGE_CONNECTION)
    mixed = area_a[0].upper() + area_a[1:]
    app.world.graph.add_edge(Edge(
        source=mixed, target=way.id, type=EDGE_CONNECTION,
        properties={"direction": "north",
                    "visible_in_direction": "the study beyond",
                    "cardinal": "east"},
    ))
    app.world.graph.add_edge(Edge(
        source=way.id, target=mixed, type=EDGE_CONNECTION,
        properties={"direction": "north"},
    ))

    # Reconnect to the SAME two areas (lowercase ids).
    resp = client.post('/api/graph/way/reconnect', json={
        'way_id': way.id,
        'area_a': area_a,
        'area_b': area_b,
        'dir_a': 'north',
        'dir_b': 'south',
    })
    assert resp.status_code == 200

    # Exactly 4 edges, both sides intact.
    edges = [e for e in app.world.graph.edges
             if e.type == EDGE_CONNECTION
             and (e.source == way.id or e.target == way.id)]
    assert len(edges) == 4

    a_to_way = next(e for e in edges if e.source == area_a and e.target == way.id)
    assert a_to_way.properties.get("visible_in_direction") == "the study beyond"
    assert a_to_way.properties.get("cardinal") == "east"
    b_to_way = next(e for e in edges if e.source == area_b and e.target == way.id)
    assert b_to_way.properties.get("direction") == "south"


def test_build_connect_removes_stale_edges():
    """Connecting a way that already has edges must not leave stale sides."""
    client, app = _fresh_client()
    way = _first_way(app)
    assert way is not None

    before = _conn_areas(app, way.id)
    assert len(before) == 2

    area_a, area_b = before
    from graph import Node
    area_node_a = app.world.graph.get_node(area_a)
    area_node_b = app.world.graph.get_node(area_b)

    # Call build_connect with the same pair + way_id — should rebuild, not
    # accumulate (only 2 areas remain wired).
    resp = client.post('/api/build/connect', json={
        'room1': area_node_a.name,
        'room2': area_node_b.name,
        'dir1': 'north',
        'dir2': 'south',
        'way_id': way.id,
        'state': 'open',
    })
    assert resp.status_code == 200

    after = _conn_areas(app, way.id)
    assert len(after) == 2
    assert set(after) == set(before)


def test_build_connect_replaces_old_side():
    """Connecting a way to a NEW pair drops the stale old side entirely."""
    client, app = _fresh_client()
    way = _first_way(app)
    assert way is not None

    areas = _conn_areas(app, way.id)
    assert len(areas) == 2
    keep, old = areas[0], areas[1]

    # Build a spare area to connect to.
    client.post('/api/build/area', json={'name': 'Repair Test Spare Room'})
    spare = next(n for n in app.world.graph.nodes.values()
                 if n.type == 'area' and n.name == 'Repair Test Spare Room')

    keep_name = app.world.graph.get_node(keep).name
    resp = client.post('/api/build/connect', json={
        'room1': keep_name,
        'room2': spare.name,
        'dir1': 'north',
        'dir2': 'south',
        'way_id': way.id,
        'state': 'open',
    })
    assert resp.status_code == 200

    after = _conn_areas(app, way.id)
    assert len(after) == 2
    assert spare.id in after
    assert old not in after
    assert keep in after


def test_build_connect_no_way_id_generates_unique_id():
    """With no manual way_id, two ways from the same room+dir must NOT
    clobber each other (bug-16): the second gets a numeric suffix."""
    client, app = _fresh_client()

    for name in ['Bug16 Room A', 'Bug16 Room B', 'Bug16 Room C']:
        client.post('/api/build/area', json={'name': name})
    a = next(n for n in app.world.graph.nodes.values()
             if n.type == 'area' and n.name == 'Bug16 Room A')
    b = next(n for n in app.world.graph.nodes.values()
             if n.type == 'area' and n.name == 'Bug16 Room B')
    c = next(n for n in app.world.graph.nodes.values()
             if n.type == 'area' and n.name == 'Bug16 Room C')

    # Same (room1, dir1) twice, no way_id — must produce two distinct ways.
    resp1 = client.post('/api/build/connect', json={
        'room1': a.name, 'room2': b.name,
        'dir1': 'north', 'dir2': 'south', 'state': 'open',
    })
    resp2 = client.post('/api/build/connect', json={
        'room1': a.name, 'room2': c.name,
        'dir1': 'north', 'dir2': 'south', 'state': 'open',
    })
    assert resp1.status_code == 200
    assert resp2.status_code == 200

    ways = sorted(n.id for n in app.world.graph.nodes.values() if n.type == 'way')
    # The shared base id is generated once; the second way gets a suffix.
    first = "way_bug16_room_a_north"
    assert first in ways
    assert any(wid.startswith("way_bug16_room_a_north_")
               for wid in ways)
    # Both ways survive and each connects only its own two areas.
    assert len(_conn_areas(app, first)) == 2
    assert all(len(_conn_areas(app, wid)) == 2
               for wid in ways if wid != first)


def test_load_normalizes_mixed_case_edge_endpoints():
    """load_from_dict rewrites edge endpoints whose case differs from the
    stored node id (legacy mixed-case ids) to the canonical key."""
    _, app = _fresh_client()
    way = _first_way(app)
    areas = _conn_areas(app, way.id)
    assert len(areas) == 2
    area_a = areas[0]

    data = app.world.to_dict()
    # Corrupt one edge endpoint to mixed case, as legacy saves would.
    mixed = area_a[0].upper() + area_a[1:]
    for e in data["graph"]["edges"]:
        if e["type"] == EDGE_CONNECTION and e["source"] == area_a \
                and e["target"] == way.id:
            e["source"] = mixed
        if e["type"] == EDGE_CONNECTION and e["source"] == way.id \
                and e["target"] == area_a:
            e["target"] = mixed

    app.world.graph.load_from_dict(data["graph"])
    # No edge may reference the legacy mixed-case id anymore.
    assert not any(e.source == mixed or e.target == mixed
                   for e in app.world.graph.edges)
    # The canonical area_a -> way edge survived with its source intact.
    assert any(e.source == area_a and e.target == way.id
               for e in app.world.graph.edges if e.type == EDGE_CONNECTION)
