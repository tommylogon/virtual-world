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

def test_benchmark_unload_validation(client):
    response = client.post('/api/bench/unload', json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_benchmark_load_validation(client):
    response = client.post('/api/bench/load', json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_benchmark_unload_all(client, monkeypatch):
    import requests
    class MockResponse:
        ok = True
        status_code = 200
        def json(self):
            return {
                "models": [
                    {"key": "test-m", "loaded_instances": ["inst_1", "inst_2"]}
                ]
            }

    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: MockResponse())
    monkeypatch.setattr(requests, 'post', lambda *args, **kwargs: MockResponse())
    response = client.post('/api/bench/unload-all', json={'api_base': 'http://localhost:1234/v1'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data.get('status') == 'ok'
    assert len(data.get('unloaded', [])) == 2

def test_benchmark_native_lmstudio_parsing(client, monkeypatch):
    import requests
    class MockResponse:
        ok = True
        status_code = 200
        def json(self):
            return {
                "models": [
                    {
                        "type": "llm",
                        "key": "qwen3.8-27b",
                        "display_name": "Qwen3.8 27B",
                        "params_string": "27B",
                        "quantization": {"name": "Q4_K_M"},
                        "max_context_length": 262144,
                        "loaded_instances": ["inst_1"],
                        "capabilities": {
                            "vision": True,
                            "trained_for_tool_use": True,
                            "reasoning": {"default": "on"}
                        }
                    },
                    {
                        "type": "embedding",
                        "key": "text-embed",
                        "display_name": "Text Embed"
                    }
                ]
            }

    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: MockResponse())
    response = client.post('/api/bench/models', json={'api_base': 'http://localhost:1234/v1'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data.get('is_native_lmstudio') is True
    # Embedding model was filtered out, leaving exactly 1 model
    assert len(data['models']) == 1
    m = data['models'][0]
    assert m['id'] == 'qwen3.8-27b'
    assert m['vision'] is True
    assert m['tools'] is True
    assert m['reasoning'] is True
    assert m['loaded'] is True
    assert m['context_length'] == 262144

def test_benchmark_chat_retry_after(client, monkeypatch):
    import requests
    calls = []
    class MockResp429:
        ok = False
        status_code = 429
        headers = {'Retry-After': '0.01'}
        text = 'Too Many Requests'
    class MockResp200:
        ok = True
        status_code = 200
        headers = {'Content-Type': 'application/json'}
        def json(self):
            return {'choices': [{'message': {'content': 'Success after retry'}}]}

    def mock_post(*args, **kwargs):
        calls.append(len(calls) + 1)
        if len(calls) == 1:
            return MockResp429()
        return MockResp200()

    monkeypatch.setattr(requests, 'post', mock_post)
    resp = client.post('/api/bench/chat', json={
        'model': 'test-model',
        'messages': [{'role': 'user', 'content': 'hi'}],
        'stream': False,
        'api_base': 'http://localhost:1234/v1'
    })
    assert resp.status_code == 200
    assert len(calls) == 2
    data = json.loads(resp.data)
    assert data['choices'][0]['message']['content'] == 'Success after retry'



