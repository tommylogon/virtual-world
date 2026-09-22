"""Multi-layer graph backgrounds (task-451) — the save contract.

The world block `graph_background` used to hold ONE image
({image, rect, rotation, crop, opacity, locked, positions}). It now holds
{layers: [...], positions, layoutLocked}, with the legacy shape still accepted
and migrated client-side.

The subtle half of this contract is the EMPTY layer list: a scenario always
serializes the key, so "no maps" arrives as an empty list, and that must survive
a round trip. Collapsing an empty block into "no record" is exactly bug-39, where
the client could not tell "this world has no map" from "a map with nothing in it"
and left the previous scenario's image on screen.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app


def _fresh_client():
    app = create_app({'TESTING': True})
    return app.test_client(), app


LAYER = {
    'id': 'bg-one',
    'label': 'Ground floor',
    'image': '/static/images/backgrounds/floor-1.png',
    'rect': {'x': -100, 'y': -50, 'width': 800, 'height': 600},
    'rotation': 12.5,
    'crop': {'x': 0.05, 'y': 0, 'w': 0.9, 'h': 1},
    'opacity': 0.5,
    'locked': True,
    'visible': True,
}
LAYER_2 = {
    'id': 'bg-two',
    'label': 'Region',
    'image': '/static/images/backgrounds/region.png',
    'rect': {'x': -2000, 'y': -1500, 'width': 4000, 'height': 3000},
    'rotation': 0,
    'crop': {'x': 0, 'y': 0, 'w': 1, 'h': 1},
    'opacity': 0.3,
    'locked': False,
    'visible': False,
}


def test_multi_layer_block_replaces_and_is_exposed_in_state():
    client, app = _fresh_client()

    resp = client.post('/api/graph/background', json={
        'layers': [LAYER, LAYER_2],
        'positions': {'area_a': {'x': 10, 'y': 20}},
        'layoutLocked': True,
    })
    assert resp.status_code == 200
    block = resp.get_json()['graph_background']
    assert [l['id'] for l in block['layers']] == ['bg-one', 'bg-two']
    assert block['positions'] == {'area_a': {'x': 10, 'y': 20}}
    assert block['layoutLocked'] is True
    # Per-layer fields survive verbatim (opacity 0 is not swallowed by a falsy check).
    assert block['layers'][0]['opacity'] == 0.5
    assert block['layers'][0]['locked'] is True
    assert block['layers'][1]['visible'] is False

    # The client reads it from /api/state, so the key has to be there too.
    state = client.get('/api/state').get_json()
    assert [l['id'] for l in state['graph_background']['layers']] == ['bg-one', 'bg-two']
    assert app.world.graph_background['layers'][1]['label'] == 'Region'


def test_empty_layer_list_persists_as_an_empty_list():
    """bug-39: "no maps" must be distinguishable from "no record"."""
    client, app = _fresh_client()

    client.post('/api/graph/background', json={'layers': [LAYER], 'layoutLocked': False})
    assert len(app.world.graph_background['layers']) == 1

    resp = client.post('/api/graph/background', json={
        'layers': [],
        'positions': {},
        'layoutLocked': False,
    })
    assert resp.status_code == 200
    block = resp.get_json()['graph_background']
    assert block == {'layers': [], 'positions': {}, 'layoutLocked': False}
    assert app.world.graph_background == {'layers': [], 'positions': {}, 'layoutLocked': False}
    # And it stays that shape through the state serialization the client reads.
    assert client.get('/api/state').get_json()['graph_background']['layers'] == []


def test_malformed_layers_are_dropped_not_merged():
    client, app = _fresh_client()

    resp = client.post('/api/graph/background', json={'layers': 'nonsense'})
    assert resp.get_json()['graph_background']['layers'] == []

    resp = client.post('/api/graph/background', json={'layers': [1, None, 'x', LAYER]})
    assert [l['id'] for l in resp.get_json()['graph_background']['layers']] == ['bg-one']

    # A missing positions dict must not wipe into something non-dict.
    resp = client.post('/api/graph/background', json={'layers': [LAYER], 'positions': 'nope'})
    assert resp.get_json()['graph_background']['positions'] == {}


def test_legacy_single_image_form_still_merges():
    """An older client (or hand-rolled request) keeps the old merge behaviour."""
    client, app = _fresh_client()

    resp = client.post('/api/graph/background', json={
        'image': '/static/images/backgrounds/old.png',
        'rect': {'x': 0, 'y': 0, 'width': 100, 'height': 100},
        'opacity': 0.4,
    })
    block = resp.get_json()['graph_background']
    assert block['image'] == '/static/images/backgrounds/old.png'
    assert block['rect']['width'] == 100

    # A later partial update must not drop what is already there.
    resp = client.post('/api/graph/background', json={'rotation': 90, 'locked': True})
    block = resp.get_json()['graph_background']
    assert block['rotation'] == 90
    assert block['locked'] is True
    assert block['image'] == '/static/images/backgrounds/old.png'


def test_clearing_the_legacy_image_keeps_the_key():
    client, app = _fresh_client()
    client.post('/api/graph/background', json={'image': '/static/images/backgrounds/old.png'})
    resp = client.post('/api/graph/background', json={'image': None})
    assert resp.get_json()['graph_background']['image'] is None
