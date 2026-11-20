import pytest
import json
from app import create_app

@pytest.fixture
def client(tmp_path, monkeypatch):
    import routes.benchmark as bench_mod
    monkeypatch.setattr(bench_mod, 'BENCH_DIR', tmp_path)
    monkeypatch.setattr(bench_mod, 'RUNS_DIR', tmp_path / 'runs')
    monkeypatch.setattr(bench_mod, 'REGISTRY_FILE', tmp_path / 'model_registry.json')
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
        'provider': 'OpenRouter',
        'area': 'Library',
        'config': {
            'temperature': 0.7,
            'max_tokens': 4096,
            'reasoning_effort': 'high',
            'reasoning_max_tokens': 2048,
            'preferred_action': 'examine desk',
        },
        'results': [
            {'model': 'mock-model', 'score': 3, 'metrics': {'tps': 25.0}},
            {'model': 'broken-model', 'error': 'HTTP 429'},
        ]
    })
    assert save_resp.status_code == 200

    list_resp = client.get('/api/bench/runs')
    assert list_resp.status_code == 200
    runs = json.loads(list_resp.data)['runs']
    assert len(runs) == 1
    assert runs[0]['completed_count'] == 1
    assert runs[0]['failed_count'] == 1
    assert runs[0]['area'] == 'Library'
    assert runs[0]['config']['reasoning_max_tokens'] == 2048
    assert runs[0]['top_model'] == {'model': 'mock-model', 'score': 3}

    get_resp = client.get('/api/bench/runs/test_run_123')
    assert get_resp.status_code == 200
    run_data = json.loads(get_resp.data)
    assert run_data.get('run_id') == 'test_run_123'
    assert run_data.get('character') == 'Tester'


def test_benchmark_chat_forwards_reasoning_max_tokens(client, monkeypatch):
    import requests
    captured = []

    class MockResp:
        ok = True
        status_code = 200
        headers = {'Content-Type': 'application/json'}
        text = '{}'
        def json(self):
            return {'choices': [{'message': {'content': 'ok'}}]}

    def fake_post(url, headers=None, json=None, stream=False, timeout=None):
        captured.append(json)
        return MockResp()

    monkeypatch.setattr(requests, 'post', fake_post)
    resp = client.post('/api/bench/chat', json={
        'api_base': 'https://openrouter.ai/api/v1',
        'api_key': 'sk-test',
        'model': 'anthropic/claude-sonnet',
        'reasoning_effort': 'high',
        'reasoning_max_tokens': 4096,
        'messages': [{'role': 'user', 'content': 'hi'}],
        'stream': False,
    })
    assert resp.status_code == 200
    assert captured[0]['reasoning'] == {'max_tokens': 4096}
    assert 'reasoning_effort' not in captured[0]

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

def test_api_action_validate_missing_target(client):
    resp = client.post('/api/action/validate', json={'action': 'take'})
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data['valid'] is False
    assert data['category'] == 'missing_target'


def test_api_action_validate_room_and_wait(client):
    resp1 = client.post('/api/action/validate', json={'action': 'examine room'})
    assert resp1.status_code == 200
    data1 = json.loads(resp1.data)
    assert data1['valid'] is True
    assert data1['category'] == 'area'

    resp2 = client.post('/api/action/validate', json={'action': 'wait'})
    assert resp2.status_code == 200
    data2 = json.loads(resp2.data)
    assert data2['valid'] is True


def test_api_action_validate_not_found(client):
    resp = client.post('/api/action/validate', json={'action': 'examine non_existent_widget_123'})
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data['valid'] is False
    assert data['category'] == 'not_found'


def test_models_metadata_endpoints(client):
    # 1. GET metadata starts cleanly
    get_resp = client.get('/api/bench/models/metadata')
    assert get_resp.status_code == 200
    data = json.loads(get_resp.data)
    assert 'metadata' in data
    assert isinstance(data['metadata'], dict)

    # 2. POST update metadata
    post_resp = client.post('/api/bench/models/metadata', json={
        'model_id': 'meta-llama/test-model-8b',
        'display_name': 'Llama Test 8B',
        'status': 'do_not_use',
        'reason': 'broken',
        'notes': 'Chronic repetition loops in testing',
        'is_free': True
    })
    assert post_resp.status_code == 200
    res_data = json.loads(post_resp.data)
    assert res_data['status'] == 'saved'
    assert res_data['model_id'] == 'meta-llama/test-model-8b'

    # 3. Verify persistence in GET
    verify_resp = client.get('/api/bench/models/metadata')
    meta = json.loads(verify_resp.data)['metadata']
    assert 'meta-llama/test-model-8b' in meta
    entry = meta['meta-llama/test-model-8b']
    assert entry['status'] == 'do_not_use'
    assert entry['reason'] == 'broken'
    assert entry['is_free'] is True


def test_rate_bench_run_and_registry_rollup(client):
    # 1. Save a run
    run_id = 'test_rate_run_999'
    client.post('/api/bench/runs', json={
        'run_id': run_id,
        'character': 'Tester',
        'results': [
            {'model': 'model-star-rate', 'output': 'hello', 'metrics': {'tps': 30.0}}
        ]
    })

    # 2. Rate the model result
    rate_resp = client.post(f'/api/bench/runs/{run_id}/rate', json={
        'model': 'model-star-rate',
        'rating': 4.5,
        'feedback': 'Crisp dialogue and valid actions',
        'tags': ['Crisp dialogue', 'Valid JSON']
    })
    assert rate_resp.status_code == 200
    res = json.loads(rate_resp.data)
    assert res['status'] == 'rated'
    assert res['rating'] == 4.5

    # 3. Verify run record updated
    run_resp = client.get(f'/api/bench/runs/{run_id}')
    assert run_resp.status_code == 200
    run_data = json.loads(run_resp.data)
    matched = next((r for r in run_data['results'] if r.get('model') == 'model-star-rate'), None)
    assert matched is not None
    assert matched.get('rating') == 4.5
    assert matched.get('feedback') == 'Crisp dialogue and valid actions'

    # 4. Verify rollup into model registry
    meta_resp = client.get('/api/bench/models/metadata')
    registry = json.loads(meta_resp.data)['metadata']
    entry = registry.get('model-star-rate')
    assert entry is not None
    assert 'ratings' in entry
    assert entry['ratings']['total_reviews'] >= 1
    assert entry['ratings']['average_score'] == 4.5


def test_fetch_provider_models_openrouter_capabilities(client, monkeypatch):
    import requests
    class MockResp:
        ok = True
        status_code = 200
        def json(self):
            return {
                "data": [
                    {
                        "id": "openrouter/free-vision-model:free",
                        "name": "Free Vision Model",
                        "context_length": 131072,
                        "pricing": {"prompt": "0", "completion": "0"},
                        "architecture": {
                            "modality": "text+image->text",
                            "input_modalities": ["text", "image"],
                            "output_modalities": ["text"]
                        },
                        "top_provider": {"max_completion_tokens": 4096},
                        "reasoning": True
                    },
                    {
                        "id": "openrouter/audio-model",
                        "name": "Audio Model",
                        "architecture": {
                            "modality": "text->audio",
                            "input_modalities": ["text"],
                            "output_modalities": ["audio"]
                        }
                    }
                ]
            }

    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: MockResp())
    resp = client.post('/api/bench/models', json={'api_base': 'https://openrouter.ai/api/v1', 'api_key': 'mock'})
    assert resp.status_code == 200
    data = json.loads(resp.data)
    models = {m['id']: m for m in data['models']}

    # Check free + vision + reasoning parsed
    m1 = models['openrouter/free-vision-model:free']
    assert m1['is_free'] is True
    assert m1['vision'] is True
    assert m1['reasoning'] is True
    assert m1['context_length'] == 131072
    assert m1['max_output_tokens'] == 4096
    assert m1['status'] == 'active'

    # Check non-chat audio model auto-flagged
    m2 = models['openrouter/audio-model']
    assert m2['status'] == 'do_not_use'
    assert m2['reason'] == 'audio_video'


