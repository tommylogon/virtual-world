"""Tests for the item move endpoint (routes/graph.py move_item_node).

Covers the character (carrying) target added alongside area/container so
the item inspector's Move To selector can hand an item to a character.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app


def _fresh_client():
    app = create_app({'TESTING': True})
    return app.test_client(), app


def _first_of_type(app, node_type):
    return next(
        (n for n in app.world.graph.nodes.values() if n.type == node_type),
        None
    )


def test_move_item_to_character_adds_carrying_edge():
    client, app = _fresh_client()
    item = _first_of_type(app, 'item')
    character = _first_of_type(app, 'character')
    assert item is not None and character is not None

    resp = client.post(f'/api/graph/item/{item.id}/move', json={
        'character': character.id,
    })
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'success'

    assert any(e.source == item.id and e.target == character.id and e.type == 'carrying'
               for e in app.world.graph.edges)


def test_move_item_to_character_removes_old_placement():
    client, app = _fresh_client()
    item = _first_of_type(app, 'item')
    character = _first_of_type(app, 'character')
    area = _first_of_type(app, 'area')

    # Place in an area first, then hand to the character
    client.post(f'/api/graph/item/{item.id}/move', json={'area': area.name})
    assert any(e.source == item.id and e.type == 'in' for e in app.world.graph.edges)

    resp = client.post(f'/api/graph/item/{item.id}/move', json={'character': character.id})
    assert resp.status_code == 200

    # Old placement edges removed; only the carrying edge remains
    assert not any(e.source == item.id and e.type == 'in' for e in app.world.graph.edges)
    assert any(e.source == item.id and e.target == character.id and e.type == 'carrying'
               for e in app.world.graph.edges)


def test_move_item_to_unknown_character_404():
    client, _ = _fresh_client()
    item = _first_of_type(client.application, 'item')
    resp = client.post(f'/api/graph/item/{item.id}/move', json={
        'character': 'player_nobody_here',
    })
    assert resp.status_code == 404


def test_move_unknown_item_error_names_destination_and_suggests():
    client, app = _fresh_client()
    resp = client.post('/api/graph/item/item_totally_bogus/move', json={
        'area': 'Living Area',
    })
    assert resp.status_code == 404
    err = resp.get_json()['error']
    assert 'item_totally_bogus' in err
    assert "area 'Living Area'" in err
    # Closest-match suggestion present (any real item id is fine).
    item_ids = [nid for nid, n in app.world.graph.nodes.items() if n.type == 'item']
    assert item_ids
    assert any(iid in err for iid in item_ids)


def test_move_item_requires_target():
    client, app = _fresh_client()
    item = _first_of_type(app, 'item')
    resp = client.post(f'/api/graph/item/{item.id}/move', json={})
    assert resp.status_code == 400
