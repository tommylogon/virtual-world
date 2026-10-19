import pytest
import json
from app import create_app

@pytest.fixture
def client():
    app = create_app({'TESTING': True})
    with app.test_client() as client:
        yield client

def test_benchmark_page_renders(client):
    response = client.get('/bench')
    assert response.status_code == 200
    assert b"Benchmark Lab" in response.data

def test_benchmark_runs_list(client):
    response = client.get('/api/bench/runs')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'runs' in data
    assert isinstance(data['runs'], list)

def test_benchmark_models_validation(client):
    # Missing/invalid remote base should gracefully fail
    response = client.post('/api/bench/models', json={'api_base': 'http://127.0.0.1:9999/v1'})
    assert response.status_code == 502
    data = json.loads(response.data)
    assert 'error' in data

def test_benchmark_save_and_get_run(client):
    save_resp = client.post('/api/bench/runs', json={
        'run_id': 'test_run_123',
        'character': 'Tester',
        'results': [{'model': 'mock-model', 'metrics': {'tps': 25.0}}]
    })
    assert save_resp.status_code == 200

    get_resp = client.get('/api/bench/runs/test_run_123')
    assert get_resp.status_code == 200
    run_data = json.loads(get_resp.data)
    assert run_data.get('run_id') == 'test_run_123'
    assert run_data.get('character') == 'Tester'

