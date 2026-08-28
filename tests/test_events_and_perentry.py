# Tests for the live world-event hub + per-entry refresh apply.
#
# Covers:
# - engine/world_events.py hub broadcast + rolling buffer.
# - app.py after_request hook broadcasting world_changed for mutating /api/ calls.
# - /api/events/recent snapshot endpoint.
# - /api/library/refresh-to-world with an entries body doing a partial apply.
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app import create_app
from engine.world_events import hub

def _fresh_app(tmp_path):
    data_dir = str(tmp_path)
    os.makedirs(os.path.join(data_dir, 'library', 'characters'), exist_ok=True)
    from routes.helpers import save_registry
    save_registry(data_dir, 'characters.json', {})
    app = create_app({'TESTING': True, 'DATA_DIR': data_dir})
    return app.test_client(), app, data_dir

def _char_node_id(app, player_name):
    for nid in app.world.graph.nodes:
        node = app.world.graph.get_node(nid)
        if not node:
            continue
        if node.type == 'character' and (node.name == player_name or (node.properties or {}).get('name') == player_name):
            return node.id
    return None

def test_hub_publish_recent_and_no_leak():
    before = hub.subscribers_count()
    hub.publish({'type': 'world_changed', 'method': 'POST', 'path': '/api/build/area', 'editor': 'agent-x'})
    hub.publish({'type': 'world_changed', 'method': 'PATCH', 'path': '/api/graph/node/n1', 'editor': 'app'})
    rec = hub.recent(50)
    assert rec
    assert rec[-1]['editor'] == 'app'
    assert rec[-2]['editor'] == 'agent-x'
    assert rec[-2]['seq'] < rec[-1]['seq']
    assert hub.subscribers_count() >= before

def test_api_mutation_broadcasts_event(tmp_path):
    client, app, _ = _fresh_app(tmp_path)
    client.post('/api/build/area', json={'name': 'Broadcast Test', 'description': 'x'})
    rec = hub.recent(200)
    assert any(e.get('path', '').startswith('/api/build') for e in rec)

def test_events_recent_endpoint(tmp_path):
    client, app, _ = _fresh_app(tmp_path)
    r = client.get('/api/events/recent')
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, dict)
    assert 'events' in data
    assert isinstance(data['events'], list)

def test_refresh_character_per_entry_memories(tmp_path):
    client, app, data_dir = _fresh_app(tmp_path)
    card = {
        'id': 'MemChar', 'name': 'Mem Char',
        'personality': 'quiet',
        'vitals': {'HP': 70},
        'memories': [
            {'id': 'm1', 'text': 'lib memory one', 'tick': 1},
            {'id': 'm2', 'text': 'lib memory two', 'tick': 1},
            {'id': 'm3', 'text': 'lib memory three', 'tick': 1},
        ],
    }
    r = client.post('/api/library/characters', json={'id': 'MemChar', 'data': card})
    assert r.status_code == 200, r.get_data(as_text=True)
    r = client.post('/api/library/import/character/MemChar', json={'active': True})
    assert r.status_code == 200, r.get_data(as_text=True)
    p = app.world.player_manager.players.get('Mem Char')
    assert p is not None
    node_id = _char_node_id(app, 'Mem Char')
    assert node_id, "character node not found"
    p.memories = [{'id': 'm2', 'text': 'lib memory two', 'tick': 1}]  # m1 and m3 were dropped
    r = client.post('/api/library/refresh-to-world', json={
        'node_id': node_id, 'template_id': 'MemChar',
        'sections': ['memories'], 'entries': {'memories': ['m1']},
    })
    assert r.status_code == 200, r.get_data(as_text=True)
    texts = {m.get('id'): m.get('text') for m in p.memories}
    assert texts.get('m1') == 'lib memory one', 'selected entry m1 should be restored from library'
    assert texts.get('m2') == 'lib memory two', 'm2 was already in the world and must be preserved'
    assert 'm3' not in texts, 'unselected lib-only memory m3 must NOT be added'
    r = client.post('/api/library/refresh-to-world', json={
        'node_id': node_id, 'template_id': 'MemChar', 'sections': ['memories'],
    })
    assert r.status_code == 200, r.get_data(as_text=True)
    assert {m.get('id') for m in p.memories} == {'m1', 'm2', 'm3'}

def test_apply_entry_selection_dict():
    from routes.library_ops import _apply_entry_selection
    cur = {'jake': {'closeness': 3}, 'miki': {'closeness': 9}}
    src = {'jake': {'closeness': 5}, 'other': {'closeness': 2}}
    out = _apply_entry_selection(cur, src, ['jake'])
    assert out['jake']['closeness'] == 5
    assert out['miki']['closeness'] == 9
    assert 'other' not in out
