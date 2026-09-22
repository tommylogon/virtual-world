"""NL-editor staged-op validation and library template editing (task-460/461).

Validation must catch the silent no-ops before Apply (unknown trait, dangling
edge endpoint, wrong shape) while the default permissive path stays unchanged;
library_upsert/library_delete must write the registries the editor can reach.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app


def _client(tmp_path):
    app = create_app({'TESTING': True, 'DATA_DIR': str(tmp_path)})
    return app.test_client(), app


def _seed_character(client, node_id='character_miki', name='Miki'):
    resp = client.post('/api/graph/batch', json={'ops': [
        {'type': 'create_node', 'payload': {'node': {
            'id': node_id, 'type': 'character', 'name': name, 'properties': {}}}},
    ]})
    assert resp.status_code == 200


def test_validate_flags_unknown_trait(tmp_path):
    client, _ = _client(tmp_path)
    _seed_character(client)

    resp = client.post('/api/graph/batch/validate', json={'ops': [
        {'type': 'update_node', 'payload': {
            'node_id': 'character_miki', 'patch': {'traits': {'drak_vision': True}}}},
    ]})
    body = resp.get_json()
    assert body['status'] == 'invalid'
    assert body['error_count'] == 1
    assert body['validation'][0]['severity'] == 'error'
    assert 'drak_vision' in body['validation'][0]['message']


def test_validate_accepts_known_trait_and_reports_warnings(tmp_path):
    client, _ = _client(tmp_path)
    _seed_character(client)

    ok = client.post('/api/graph/batch/validate', json={'ops': [
        {'type': 'update_node', 'payload': {
            'node_id': 'character_miki', 'patch': {'traits': {'dark_vision': True}}}},
    ]}).get_json()
    assert ok['status'] == 'valid' and ok['error_count'] == 0

    warn = client.post('/api/graph/batch/validate', json={'ops': [
        {'type': 'update_node', 'payload': {
            'node_id': 'character_miki', 'patch': {'actions': ['frobnicate']}}},
    ]}).get_json()
    assert warn['status'] == 'valid'
    assert warn['warning_count'] == 1


def test_validate_flags_dangling_endpoint_and_empty_bulk_patch(tmp_path):
    client, _ = _client(tmp_path)
    _seed_character(client)

    body = client.post('/api/graph/batch/validate', json={'ops': [
        {'type': 'attach', 'payload': {'from_id': 'item_ghost', 'to_id': 'character_miki'}},
        {'type': 'update_matching_nodes', 'payload': {'selector': {}, 'patch': {}}},
    ]}).get_json()
    messages = ' | '.join(i['message'] for i in body['validation'])
    assert body['error_count'] == 3, messages
    assert 'item_ghost' in messages
    assert 'selector' in messages
    assert 'patch' in messages


def test_strict_batch_refuses_invalid_ops_without_applying(tmp_path):
    client, app = _client(tmp_path)

    resp = client.post('/api/graph/batch', json={'strict_validation': True, 'ops': [
        {'type': 'create_node', 'payload': {'node': {'id': 'area_nl_ok', 'type': 'area', 'name': 'NL OK'}}},
        {'type': 'update_node', 'payload': {'node_id': 'does_not_exist', 'patch': {'description': 'x'}}},
    ]})
    assert resp.status_code == 422
    assert resp.get_json()['status'] == 'invalid'
    assert app.world.graph.get_node('area_nl_ok') is None, 'nothing applies when the gate blocks'


def test_non_strict_batch_stays_permissive(tmp_path):
    client, app = _client(tmp_path)
    resp = client.post('/api/graph/batch', json={'ops': [
        {'type': 'update_node', 'payload': {'node_id': 'does_not_exist', 'patch': {'description': 'x'}}},
    ]})
    assert resp.status_code == 207
    assert resp.get_json()['validation'], 'advisory issues still returned'


def test_library_upsert_writes_a_trait_template(tmp_path):
    client, _ = _client(tmp_path)
    resp = client.post('/api/graph/batch', json={'strict_validation': True, 'ops': [
        {'type': 'library_upsert', 'payload': {
            'registry_type': 'traits', 'id': 'sturdy',
            'data': {'name': 'Sturdy', 'description': 'Hard to knock down.',
                     'effects': {'save_bonus': {'amount': 1}}}}},
    ]})
    assert resp.status_code == 200
    assert resp.get_json()['applied'][0]['id'] == 'sturdy'

    traits = client.get('/api/library/traits').get_json()
    assert 'sturdy' in traits
    assert traits['sturdy']['effects']['save_bonus'] == {'amount': 1}

    path = os.path.join(str(tmp_path), 'library', 'traits', 'sturdy.json')
    assert os.path.exists(path)
    with open(path, encoding='utf-8') as handle:
        assert json.load(handle)['name'] == 'Sturdy'


def test_library_upsert_rejects_bad_registry_and_bad_id(tmp_path):
    client, _ = _client(tmp_path)

    bad_registry = client.post('/api/graph/batch', json={'strict_validation': True, 'ops': [
        {'type': 'library_upsert', 'payload': {'registry_type': 'bogus', 'id': 'x', 'data': {'name': 'X'}}},
    ]})
    assert bad_registry.status_code == 422
    assert 'not writable' in bad_registry.get_json()['errors'][0]['message']

    bad_id = client.post('/api/graph/batch', json={'strict_validation': True, 'ops': [
        {'type': 'library_upsert', 'payload': {'registry_type': 'traits', 'id': 'Bad Id', 'data': {'name': 'X'}}},
    ]})
    assert bad_id.status_code == 422
    assert 'lowercase slug' in bad_id.get_json()['errors'][0]['message']


def test_library_upsert_mature_gate(tmp_path):
    client, app = _client(tmp_path)
    entry = {'type': 'library_upsert', 'payload': {
        'registry_type': 'traits', 'id': 'risque', 'data': {'name': 'Risque', 'mature': True}}}

    blocked = client.post('/api/graph/batch', json={'strict_validation': True, 'ops': [entry]})
    assert blocked.status_code == 422
    assert 'mature' in blocked.get_json()['errors'][0]['message'].lower()

    app.world.mature_content = True
    allowed = client.post('/api/graph/batch', json={'strict_validation': True, 'ops': [entry]})
    assert allowed.status_code == 200


def test_library_delete_removes_entry(tmp_path):
    client, _ = _client(tmp_path)
    client.post('/api/graph/batch', json={'ops': [
        {'type': 'library_upsert', 'payload': {'registry_type': 'traits', 'id': 'temporary', 'data': {'name': 'Temp'}}},
    ]})
    assert 'temporary' in client.get('/api/library/traits').get_json()

    resp = client.post('/api/graph/batch', json={'strict_validation': True, 'ops': [
        {'type': 'library_delete', 'payload': {'registry_type': 'traits', 'id': 'temporary'}},
    ]})
    assert resp.status_code == 200
    assert 'temporary' not in client.get('/api/library/traits').get_json()

    missing = client.post('/api/graph/batch', json={'strict_validation': True, 'ops': [
        {'type': 'library_delete', 'payload': {'registry_type': 'traits', 'id': 'temporary'}},
    ]})
    assert missing.status_code == 207
    assert 'not found' in missing.get_json()['errors'][0]['error']
