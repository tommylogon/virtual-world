"""Tests for the `find` command (task-98 Phase 3).

Covers:
- `find <tag>` returns items matching that tag
- bare `find` falls back to player interest_tags
- bare `find` with no interest_tags prints guidance
- empty result prints "don't sense any items"
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from graph import Node, Edge, EDGE_IN


def _fresh_client():
    app = create_app({'TESTING': True})
    return app.test_client(), app


def _set_active_player(app, name):
    app.world.set_active_player(name)
    app.world.player_manager.active_player = name


def test_find_with_explicit_tag():
    client, app = _fresh_client()
    _set_active_player(app, 'Kaelen Voss')

    magic_orb = Node(id='item_magic_orb', type='item', name='Magic Orb', properties={
        'name': 'Magic Orb',
        'weight': 0.1,
        'tags': ['magic'],
        'current_state': 'normal',
        'actions': ['examine', 'take', 'use'],
    })
    area_id = 'area_blizzard_forest_clearing'
    app.world.graph.add_node(magic_orb)
    app.world.graph.add_edge(Edge(source=magic_orb.id, target=area_id, type=EDGE_IN))

    resp = client.post('/api/action', json={'command': 'find magic'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'Magic Orb' in data['output']
    assert '1 item(s)' in data['output']


def test_find_defaults_to_interest_tags():
    client, app = _fresh_client()
    _set_active_player(app, 'Kaelen Voss')
    app.world.player_manager.players['Kaelen Voss'].interest_tags = ['magic', 'food']

    magic_orb = Node(id='item_magic_orb_2', type='item', name='Magic Orb', properties={
        'name': 'Magic Orb',
        'weight': 0.1,
        'tags': ['magic'],
        'current_state': 'normal',
        'actions': ['examine', 'take', 'use'],
    })
    apple = Node(id='item_apple_2', type='item', name='Apple', properties={
        'name': 'Apple',
        'weight': 0.1,
        'tags': ['food'],
        'current_state': 'normal',
        'actions': ['examine', 'take', 'use'],
    })
    rock = Node(id='item_rock_2', type='item', name='Rock', properties={
        'name': 'Rock',
        'weight': 0.5,
        'tags': ['stone'],
        'current_state': 'normal',
        'actions': ['examine', 'take', 'use'],
    })
    area_id = 'area_blizzard_forest_clearing'
    for node in (magic_orb, apple, rock):
        app.world.graph.add_node(node)
        app.world.graph.add_edge(Edge(source=node.id, target=area_id, type=EDGE_IN))

    resp = client.post('/api/action', json={'command': 'find'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'Magic Orb' in data['output']
    assert 'Apple' in data['output']
    assert 'Rock' not in data['output']
    assert '2 item(s)' in data['output']


def test_find_without_interest_tags_prints_guidance():
    client, app = _fresh_client()
    _set_active_player(app, 'Kaelen Voss')
    app.world.player_manager.players['Kaelen Voss'].interest_tags = []

    resp = client.post('/api/action', json={'command': 'find'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "what should I find" in data['output']
    assert "get a hobby" in data['output']


def test_find_no_matches():
    client, app = _fresh_client()
    _set_active_player(app, 'Kaelen Voss')

    resp = client.post('/api/action', json={'command': 'find magic'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "don't sense any items" in data['output']


def test_find_deduplicates_items_with_multiple_matching_tags():
    client, app = _fresh_client()
    _set_active_player(app, 'Kaelen Voss')
    app.world.player_manager.players['Kaelen Voss'].interest_tags = ['magic', 'ancient']

    magic_sword = Node(id='item_magic_sword', type='item', name='Ancient Magic Sword', properties={
        'name': 'Ancient Magic Sword',
        'weight': 0.2,
        'tags': ['magic', 'ancient'],
        'current_state': 'normal',
        'actions': ['examine', 'take', 'use'],
    })
    area_id = 'area_blizzard_forest_clearing'
    app.world.graph.add_node(magic_sword)
    app.world.graph.add_edge(Edge(source=magic_sword.id, target=area_id, type=EDGE_IN))

    resp = client.post('/api/action', json={'command': 'find'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['output'].count('Ancient Magic Sword') == 1
    assert '1 item(s)' in data['output']
