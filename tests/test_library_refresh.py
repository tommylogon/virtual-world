"""Tests for selective refresh-from-library on items and ways.

Regression: refresh used to blindly overwrite all unlocked properties
and wipe all triggers. The new flow lets the user pick which sections
to apply via DiffModal on the frontend; the backend accepts a ``sections``
array and only touches those fields.
"""
import sys
import json
import tempfile
import shutil
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from graph import Node, Edge


def _fresh_client(data_dir=None):
    cfg = {'TESTING': True}
    if data_dir:
        cfg['DATA_DIR'] = data_dir
    app = create_app(cfg)
    return app.test_client(), app


def _setup_library(tmpdir, lib_type, entry_id, entry_data):
    subdir = Path(tmpdir) / 'library' / lib_type
    subdir.mkdir(parents=True, exist_ok=True)
    with open(subdir / f'{entry_id}.json', 'w', encoding='utf-8') as f:
        json.dump(entry_data, f)


def test_refresh_way_selective_sections():
    tmpdir = tempfile.mkdtemp()
    try:
        way_name = 'Lab Door'
        way_id = re.sub(r'[^a-z0-9_]+', '_', way_name.lower())
        _setup_library(tmpdir, 'ways', way_id, {
            'id': way_id,
            'name': way_name,
            'description': 'A steel door.',
            'current_state': 'closed',
            'pass_message': 'You pass through.',
            'needs_open': {'enabled': True, 'skill': 'Athletics', 'dc': 12},
            'auto_close': True,
            'see_through': False,
            'one_way': False,
            'requires': 'crawl',
            'max_size': 'normal',
            'edge_length': 120,
            'tags': ['door'],
            'parameters': {'light2': 'green'},
            'triggers': [
                {'trigger_type': 'on_open', 'effect_type': 'message',
                 'effect_params': {'message': 'Door opens.'}}
            ]
        })

        client, app = _fresh_client(tmpdir)
        node = Node(
            id='way_test_refresh',
            type='way',
            name=way_name,
            properties={
                'description': 'OLD description',
                'current_state': 'open',
                'pass_message': 'OLD pass',
                'needs_open': {'enabled': False, 'skill': 'Acrobatics', 'dc': 20},
                'auto_close': False,
                'see_through': True,
                'one_way': True,
                'requires': 'climb',
                'max_size': 'huge',
                'edge_length': 200,
                'tags': ['entrance'],
                'parameters': {'light2': 'yellow'},
            }
        )
        app.world.graph.add_node(node)

        resp = client.post(f'/api/ways/{node.id}/refresh-from-library', json={
            'sections': ['description', 'current_state', 'parameters']
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'refreshed'
        assert set(data['applied']) == {'description', 'current_state', 'parameters'}

        updated = app.world.graph.get_node(node.id)
        assert updated.properties['description'] == 'A steel door.'
        assert updated.properties['current_state'] == 'closed'
        assert updated.properties['parameters']['light2'] == 'green'
        assert updated.properties['pass_message'] == 'OLD pass'
        assert updated.properties['auto_close'] == False
        assert updated.properties['requires'] == 'climb'
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_refresh_way_missing_library_entry():
    tmpdir = tempfile.mkdtemp()
    try:
        client, app = _fresh_client(tmpdir)
        node = Node(id='way_ghost', type='way', name='Ghost Door', properties={})
        app.world.graph.add_node(node)

        resp = client.post(f'/api/ways/{node.id}/refresh-from-library', json={
            'sections': ['description']
        })
        assert resp.status_code == 404
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_refresh_item_selective_sections():
    tmpdir = tempfile.mkdtemp()
    try:
        item_id = 'test_item_refresh'
        _setup_library(tmpdir, 'items', item_id, {
            'name': 'Flashlight',
            'description': 'A bright light.',
            'actions': 'examine,use',
            'uses': 5,
            'weight': 0.3,
            'equip_slots': ['hand_left', 'hand_right'],
            'current_state': 'lit',
            'light_level': 'bright',
            'tags': ['light_source'],
            'triggers': [
                {'trigger_type': 'on_light', 'effect_type': 'set_state',
                 'effect_params': {'state': 'lit'}}
            ]
        })

        client, app = _fresh_client(tmpdir)
        node = Node(
            id='item_test_refresh',
            type='item',
            name='Flashlight',
            properties={
                'library_id': item_id,
                'description': 'OLD desc',
                'actions': 'examine,take',
                'uses': 99,
                'weight': 0.9,
                'equip_slots': ['head'],
                'current_state': 'normal',
                'light_level': 'dim',
                'tags': ['tool'],
            }
        )
        app.world.graph.add_node(node)

        resp = client.post('/api/library/refresh-to-world', json={
            'node_id': node.id,
            'sections': ['description', 'uses', 'tags']
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'refreshed'
        assert set(data['applied']) == {'description', 'uses', 'tags'}

        updated = app.world.graph.get_node(node.id)
        assert updated.properties['description'] == 'A bright light.'
        assert updated.properties['uses'] == 5
        assert updated.properties['tags'] == ['light_source']
        assert updated.properties['actions'] == 'examine,take'
        assert updated.properties['weight'] == 0.9
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_refresh_item_no_sections_blind_refresh():
    tmpdir = tempfile.mkdtemp()
    try:
        item_id = 'test_item_blind'
        _setup_library(tmpdir, 'items', item_id, {
            'name': 'Flashlight',
            'description': 'Lib desc',
            'actions': 'examine,use',
            'uses': 3,
            'weight': 0.2,
            'equip_slots': [],
            'current_state': 'normal',
            'light_level': 'dim',
            'tags': ['light_source'],
        })

        client, app = _fresh_client(tmpdir)
        node = Node(
            id='item_test_blind',
            type='item',
            name='Flashlight',
            properties={
                'library_id': item_id,
                'description': 'OLD',
                'uses': 1,
                'weight': 0.5,
            }
        )
        app.world.graph.add_node(node)

        resp = client.post('/api/library/refresh-to-world', json={
            'node_id': node.id,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'refreshed'
        assert data['applied'] == ['all']

        updated = app.world.graph.get_node(node.id)
        assert updated.properties['description'] == 'Lib desc'
        assert updated.properties['uses'] == 3
        assert updated.properties['weight'] == 0.2
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_refresh_way_no_sections_blind_refresh():
    tmpdir = tempfile.mkdtemp()
    try:
        way_name = 'Door'
        way_id = re.sub(r'[^a-z0-9_]+', '_', way_name.lower())
        _setup_library(tmpdir, 'ways', way_id, {
            'id': way_id,
            'name': way_name,
            'description': 'Lib door',
            'current_state': 'locked',
            'tags': ['entrance'],
        })

        client, app = _fresh_client(tmpdir)
        node = Node(id='way_test_blind', type='way', name=way_name, properties={
            'description': 'OLD',
            'current_state': 'open',
            'tags': ['portal'],
        })
        app.world.graph.add_node(node)

        resp = client.post(f'/api/ways/{node.id}/refresh-from-library', json={})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'refreshed'

        updated = app.world.graph.get_node(node.id)
        assert updated.properties['description'] == 'Lib door'
        assert updated.properties['current_state'] == 'locked'
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_refresh_item_override_template_rebinds_library_id():
    """task-295: refreshing with a different template adopts that entry
    and rebinds the node's library_id to it."""
    tmpdir = tempfile.mkdtemp()
    try:
        _setup_library(tmpdir, 'items', 'template_axe', {
            'name': 'Lumber Axe',
            'description': 'Rich template description.',
            'weight': 7.0,
            'tags': ['weapon'],
            'damage': '1d6',
        })
        _setup_library(tmpdir, 'items', 'sparse_axe', {
            'name': 'Lumber Axe',
            'description': 'Sparse template description.',
            'weight': 3.0,
            'tags': ['tool'],
        })

        client, app = _fresh_client(tmpdir)
        node = Node(
            id='item_lumber_axe',
            type='item',
            name='Lumber Axe',
            properties={
                'library_id': 'sparse_axe',
                'description': 'OLD',
                'weight': 9.0,
                'tags': ['misc'],
            }
        )
        app.world.graph.add_node(node)

        resp = client.post('/api/library/refresh-to-world', json={
            'node_id': node.id,
            'template_id': 'template_axe',
            'sections': ['description', 'weight', 'tags', 'damage'],
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'refreshed'

        updated = app.world.graph.get_node(node.id)
        assert updated.properties['description'] == 'Rich template description.'
        assert updated.properties['weight'] == 7.0
        assert updated.properties['tags'] == ['weapon']
        assert updated.properties['library_id'] == 'template_axe'
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_refresh_item_template_override_keeps_current_when_missing():
    """task-295: a template_id that has no library entry is a 404."""
    tmpdir = tempfile.mkdtemp()
    try:
        _setup_library(tmpdir, 'items', 'real_entry', {
            'name': 'Real',
            'description': 'Real description.',
        })

        client, app = _fresh_client(tmpdir)
        node = Node(
            id='item_ghost',
            type='item',
            name='Ghost',
            properties={'library_id': 'real_entry', 'description': 'OLD'},
        )
        app.world.graph.add_node(node)

        resp = client.post('/api/library/refresh-to-world', json={
            'node_id': node.id,
            'template_id': 'does_not_exist',
        })
        assert resp.status_code == 404
        assert resp.get_json()['error'].startswith("Library item 'does_not_exist'")

        updated = app.world.graph.get_node(node.id)
        assert updated.properties['library_id'] == 'real_entry'
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_library_all_returns_multiple_registries_in_one_round_trip():
    """task-315: /api/library/all returns several registries at once (fast sync render)."""
    tmpdir = tempfile.mkdtemp()
    try:
        _setup_library(tmpdir, 'items', 'apple', {'name': 'Apple', 'weight': 0.2})
        _setup_library(tmpdir, 'items', 'knife', {'name': 'Knife', 'weight': 0.5})
        _setup_library(tmpdir, 'ways', 'door', {'name': 'Door', 'current_state': 'closed'})
        _setup_library(tmpdir, 'areas', 'kitchen', {'name': 'Kitchen'})

        client, _ = _fresh_client(tmpdir)

        # Narrowed to a subset.
        resp = client.get('/api/library/all?types=items,ways')
        assert resp.status_code == 200
        data = resp.get_json()
        assert set(data.keys()) == {'items', 'ways'}
        assert set(data['items'].keys()) == {'apple', 'knife'}
        assert data['ways']['door']['current_state'] == 'closed'
        assert 'areas' not in data

        # Default returns every registry type.
        resp_all = client.get('/api/library/all')
        assert resp_all.status_code == 200
        data_all = resp_all.get_json()
        for t in ('items', 'ways', 'areas', 'characters', 'tags', 'traits',
                  'conditions', 'behaviours', 'triggers'):
            assert t in data_all
        assert len(data_all['items']) == 2
        assert len(data_all['ways']) == 1
        assert len(data_all['areas']) == 1
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
