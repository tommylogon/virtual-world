"""Tests for Tab-Completion for Commands (task-6).

Covers:
- get_autocomplete_options method on VirtualWorld
- Verb-based item/target categorization (take, examine, use, open, drop, eat, attack, go)
- Prefix filtering
- /api/autocomplete HTTP endpoint
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from graph import Node, Edge, EDGE_IN
from player import Player


def _fresh_client():
    app = create_app({'TESTING': True})
    client = app.test_client()
    return client, app


def _setup_world(app):
    world = app.world

    # Clear players dict and setup clean test world state
    world.player_manager.players.clear()

    # Clear template graph so pre-existing nodes/edges (carried items, NPCs,
    # areas, ways, doors) don't leak into the synthetic test world.
    world.graph.clear()

    world.player_manager.add_player(Player('Kaelen Voss'))
    p1 = world.player_manager.get_player('Kaelen Voss')
    p1.current_area = 'Test Room'

    area_id = 'area_test_room'
    area_node = Node(id=area_id, type='area', name='Test Room', properties={'name': 'Test Room'})
    world.graph.add_node(area_node)
    world.player_manager._set_player_area('Kaelen Voss', 'Test Room')

    # Add room items
    key_item = Node(id='item_brass_key', type='item', name='Brass Key', properties={
        'name': 'Brass Key', 'actions': ['take', 'examine', 'use'], 'takeable': True
    })
    apple_item = Node(id='item_red_apple', type='item', name='Red Apple', properties={
        'name': 'Red Apple', 'actions': ['take', 'eat'], 'tags': ['food'], 'takeable': True
    })
    fixed_table = Node(id='item_stone_table', type='item', name='Stone Table', properties={
        'name': 'Stone Table', 'actions': ['examine'], 'takeable': False
    })
    world.graph.add_node(key_item)
    world.graph.add_node(apple_item)
    world.graph.add_node(fixed_table)

    world.graph.add_edge(Edge(source=key_item.id, target=area_id, type=EDGE_IN))
    world.graph.add_edge(Edge(source=apple_item.id, target=area_id, type=EDGE_IN))
    world.graph.add_edge(Edge(source=fixed_table.id, target=area_id, type=EDGE_IN))

    # Add door way node
    door_way = Node(id='way_iron_door', type='way', name='Iron Door', properties={
        'name': 'Iron Door', 'actions': ['open', 'close', 'unlock']
    })
    world.graph.add_node(door_way)
    world.graph.add_edge(Edge(source=area_id, target=door_way.id, type='way', properties={'direction': 'north'}))

    # Add carried item
    potion_item = Node(id='item_health_potion', type='item', name='Health Potion', properties={
        'name': 'Health Potion', 'actions': ['drink', 'use'], 'tags': ['drink']
    })
    world.graph.add_node(potion_item)
    player_id = world.player_manager.get_player_node_id('Kaelen Voss')
    world.graph.add_edge(Edge(source=potion_item.id, target=player_id, type='carrying'))

    # Add NPC in area
    world.player_manager.add_player(Player('Guard NPC'))
    p2 = world.player_manager.get_player('Guard NPC')
    p2.current_area = 'Test Room'
    world.player_manager._set_player_area('Guard NPC', 'Test Room')

    # Ensure active player is Kaelen Voss
    world.set_active_player('Kaelen Voss')

    return world


def test_autocomplete_take():
    client, app = _fresh_client()
    world = _setup_world(app)

    opts = world.get_autocomplete_options('take')
    assert 'Brass Key' in opts
    assert 'Red Apple' in opts
    assert 'Health Potion' not in opts  # Carried item not in room take


def test_autocomplete_drop():
    client, app = _fresh_client()
    world = _setup_world(app)

    opts = world.get_autocomplete_options('drop')
    assert opts == ['Health Potion']


def test_autocomplete_prefix_filter():
    client, app = _fresh_client()
    world = _setup_world(app)

    opts = world.get_autocomplete_options('take', prefix='b')
    assert opts == ['Brass Key']

    opts_r = world.get_autocomplete_options('take', prefix='red')
    assert opts_r == ['Red Apple']


def test_autocomplete_examine():
    client, app = _fresh_client()
    world = _setup_world(app)

    opts = world.get_autocomplete_options('examine')
    assert 'Brass Key' in opts
    assert 'Red Apple' in opts
    assert 'Stone Table' in opts
    assert 'Health Potion' in opts
    assert 'Iron Door' in opts
    assert 'Guard NPC' in opts


def test_autocomplete_open():
    client, app = _fresh_client()
    world = _setup_world(app)

    opts = world.get_autocomplete_options('open')
    assert 'Iron Door' in opts or 'north' in opts


def test_autocomplete_attack():
    client, app = _fresh_client()
    world = _setup_world(app)

    opts = world.get_autocomplete_options('attack')
    assert 'Guard NPC' in opts
    assert 'Kaelen Voss' not in opts


def test_autocomplete_api_endpoint():
    client, app = _fresh_client()
    _setup_world(app)

    res = client.post('/api/autocomplete', json={'verb': 'take', 'prefix': 'brass'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['verb'] == 'take'
    assert data['prefix'] == 'brass'
    assert data['options'] == ['Brass Key']
