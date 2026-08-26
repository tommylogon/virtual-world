"""Tests for the unified memory API (retrieve/reflect/spatial) + serialization round-trip."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app


def _client():
    app = create_app({'TESTING': True})
    return app.test_client()


def _active_player(client):
    data = client.get('/api/state').get_json()
    return data['active_player']


def test_retrieve_returns_ranked_memories():
    client = _client()
    name = _active_player(client)
    client.post(f'/api/players/{name}/memories/clear')
    client.post(f'/api/players/{name}/memories/entry', json={
        'text': 'Found a rusty key in the kitchen drawer.',
        'importance': 6, 'type': 'action', 'tick': 3,
    })
    client.post(f'/api/players/{name}/memories/entry', json={
        'text': 'Saw a black cat in the garden.',
        'importance': 3, 'type': 'observation', 'tick': 1,
    })

    resp = client.post(f'/api/players/{name}/memories/retrieve', json={
        'query': 'key kitchen', 'max_results': 5
    })
    assert resp.status_code == 200
    memories = resp.get_json()['memories']
    assert len(memories) >= 1
    assert memories[0]['text'] == 'Found a rusty key in the kitchen drawer.'


def test_retrieve_entity_boost():
    client = _client()
    name = _active_player(client)
    client.post(f'/api/players/{name}/memories/clear')
    area_id = 'area_living_area'
    client.post(f'/api/players/{name}/memories/entry', json={
        'text': 'Examined the fireplace in the living area.',
        'importance': 4, 'type': 'action', 'tick': 2, 'entity_ids': [area_id],
    })
    client.post(f'/api/players/{name}/memories/entry', json={
        'text': 'Somewhere far away there is a lighthouse.',
        'importance': 9, 'type': 'thought', 'tick': 1,
    })

    resp = client.post(f'/api/players/{name}/memories/retrieve', json={
        'query': 'fireplace', 'max_results': 2, 'entity_boost': True,
        'current_area_id': area_id,
    })
    memories = resp.get_json()['memories']
    assert memories[0]['text'].startswith('Examined the fireplace')


def test_reflect_stores_reflection_memories():
    client = _client()
    name = _active_player(client)
    client.post(f'/api/players/{name}/memories/clear')

    resp = client.post(f'/api/players/{name}/memories/reflect', json={
        'insights': ['The house holds many secrets.', 'short'],
        'tick': 42,
    })
    assert resp.status_code == 200
    assert resp.get_json()['stored'] == 1

    data = client.get(f'/api/players/{name}/memories').get_json()
    stored = data['memories']
    assert len(stored) == 1
    assert stored[0]['type'] == 'reflection'
    assert stored[0]['importance'] == 8
    assert stored[0]['tick'] == 42


def test_memory_entry_includes_entity_ids_and_source():
    client = _client()
    name = _active_player(client)
    resp = client.post(f'/api/players/{name}/memories/entry', json={
        'text': 'Found a note.',
        'entity_ids': ['item_note'],
    })
    assert resp.status_code == 201
    entry = resp.get_json()['entry']
    assert entry['entity_ids'] == ['item_note']
    assert entry['source'] == 'auto'


def test_serialization_roundtrips_memory_fields():
    """Memories keep entity_ids/source through a save/load cycle; legacy
    _memory/world_knowledge/knowledge fields are gone."""
    client = _client()
    name = _active_player(client)
    client.post(f'/api/players/{name}/memories/entry', json={
        'text': 'The cellar door is locked.',
        'entity_ids': ['area_cellar'],
        'source': 'auto',
        'importance': 7,
    })

    data = client.get('/api/state').get_json()
    player = data['players'][name]
    # legacy fields no longer serialized
    assert 'world_knowledge' not in player
    assert 'knowledge' not in player
    assert 'memory' not in player
    mem = player['memories'][-1]
    assert mem['entity_ids'] == ['area_cellar']
    assert mem['source'] == 'auto'
