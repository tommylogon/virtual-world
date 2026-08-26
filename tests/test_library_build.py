"""Tests for the library-to-world place endpoint (routes/library_routes.py).

Regression: item placement raised NameError: name 'item' is not defined when
building the node id — the variable it referenced never existed, so every
placement 500'd and no node was created.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app


def _fresh_client():
    app = create_app({'TESTING': True})
    return app.test_client(), app


def test_build_item_from_library_creates_node_in_area():
    client, app = _fresh_client()
    area_name = sorted(app.world.areas)[0]

    resp = client.post('/api/library/items/jumpsuit/place', json={
        'area': area_name,
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('status') == 'success'
    node_id = data.get('node_id')
    assert node_id and node_id.startswith('item_jumpsuit_')

    node = app.world.graph.get_node(node_id)
    assert node is not None
    assert node.type == 'item'

    area_node_id = next(
        (n.id for n in app.world.graph.nodes.values()
         if n.type == 'area' and n.name == area_name),
        None
    )
    assert any(e.source == node_id and e.target == area_node_id and e.type == 'in'
               for e in app.world.graph.edges)


def test_build_item_from_library_creates_distinct_nodes_per_placement():
    client, app = _fresh_client()
    area_name = sorted(app.world.areas)[0]

    node_ids = set()
    for _ in range(2):
        resp = client.post('/api/library/items/jumpsuit/place', json={
            'area': area_name,
        })
        assert resp.status_code == 200
        node_ids.add(resp.get_json()['node_id'])

    assert len(node_ids) == 2


def test_build_item_from_library_missing_item_404():
    client, _ = _fresh_client()
    resp = client.post('/api/library/items/definitely_not_a_library_item/place', json={
        'area': 'Living Area',
    })
    assert resp.status_code == 404
