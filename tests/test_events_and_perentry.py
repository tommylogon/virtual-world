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


def test_hub_subscriber_cap_and_overflow(tmp_path):
    client, app, _ = _fresh_app(tmp_path)
    initial_subs = hub.subscribers_count()
    created = []
    try:
        while len(created) + initial_subs < hub.MAX_SUBSCRIBERS:
            sub = hub.subscribe()
            assert sub is not None
            created.append(sub)

        assert hub.subscribe() is None

        r = client.get('/api/events')
        assert r.status_code == 429
        data = r.get_json()
        assert data.get('cap') == hub.MAX_SUBSCRIBERS
    finally:
        for sub in created:
            hub.unsubscribe(sub)


def test_hub_queue_overflow_enqueues_resync():
    import queue
    q = queue.Queue(maxsize=2)
    with hub._lock:
        hub._subscribers.append(q)
    try:
        hub.publish({'type': 'test_ev_1'})
        hub.publish({'type': 'test_ev_2'})
        hub.publish({'type': 'test_ev_3'})

        items = []
        while not q.empty():
            items.append(q.get_nowait())

        resync = next((item for item in items if item.get('type') == 'resync_required'), None)
        assert resync is not None, 'resync_required event was not enqueued on overflow'
        assert resync.get('reason') == 'queue_overflow'
    finally:
        hub.unsubscribe(q)


def test_hub_since_and_reconnect():
    hub.publish({'type': 'reconnect_1'})
    hub.publish({'type': 'reconnect_2'})
    rec = hub.recent(2)
    s1 = rec[-2]['seq']
    s2 = rec[-1]['seq']

    since_s1 = hub.since(s1)
    assert since_s1 is not None
    assert len(since_s1) >= 1
    assert any(e['seq'] == s2 for e in since_s1)

    assert hub.since(-999999) is None


def test_state_etag_and_304(tmp_path):
    client, app, _ = _fresh_app(tmp_path)
    r = client.get('/api/state')
    assert r.status_code == 200
    etag = r.headers.get('ETag')
    assert etag is not None, 'ETag header is missing on /api/state'

    r_cached = client.get('/api/state', headers={'If-None-Match': etag})
    assert r_cached.status_code == 304

    client.post('/api/build/area', json={'name': 'ETag Area', 'description': 'desc'})
    r_after = client.get('/api/state', headers={'If-None-Match': etag})
    assert r_after.status_code == 200
    assert r_after.headers.get('ETag') != etag


def test_node_update_broadcasts_delta(tmp_path):
    client, app, _ = _fresh_app(tmp_path)
    client.post('/api/graph/node', json={'id': 'test_gem', 'type': 'item', 'name': 'Ruby Gem'})
    r = client.patch('/api/graph/node/test_gem', json={'properties': {'value': 500}})
    assert r.status_code == 200

    rec = hub.recent(10)
    matching = [e for e in rec if e.get('delta', {}).get('node_id') == 'test_gem']
    assert len(matching) > 0, 'delta event for test_gem not broadcast'
    delta = matching[-1]['delta']
    assert delta['kind'] == 'node_update'
    assert delta['node']['properties']['value'] == 500
