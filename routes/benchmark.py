"""
routes/benchmark.py - API routes for LLM prompt benchmarking.

Provides:
- Page view: /bench
- Model listing proxy: POST /api/bench/models (to avoid browser CORS issues)
- LLM streaming/completion proxy: POST /api/bench/chat
- Run persistence: GET/POST /api/bench/runs
"""
import os
import re
import json
import time
import logging
import requests
from datetime import datetime, timezone
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify, Response, stream_with_context, current_app

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
BENCH_DIR = ROOT / "data" / "model_bench"
RUNS_DIR = BENCH_DIR / "runs"

def register_benchmark_routes(app):
    """Register all benchmark routes on the app."""

    @app.route('/bench')
    def benchmark_page():
        """Render the standalone benchmark workbench."""
        from version import APP_VERSION
        source = getattr(app.world, '_scenario_source', None)
        scenario_name = os.path.splitext(os.path.basename(source))[0] if source else ''
        return render_template(
            'benchmark.html',
            app_version=APP_VERSION,
            scenario_name=scenario_name
        )

    @app.route('/api/bench/models', methods=['POST'])
    def fetch_provider_models():
        """Fetch model list from an external provider (with rich LM Studio native detection)."""
        data = request.get_json(silent=True) or {}
        api_base = (data.get('api_base') or 'http://localhost:1234/v1').rstrip('/')
        api_key = data.get('api_key') or ''

        headers = {'Content-Type': 'application/json'}
        if api_key and api_key not in ('not-needed', 'none'):
            headers['Authorization'] = f'Bearer {api_key}'

        # Try LM Studio native endpoint first if host root provides /api/v1/models
        host_root = re.sub(r'/v1/?$', '', api_base)
        native_url = f'{host_root}/api/v1/models'

        try:
            native_resp = requests.get(native_url, headers=headers, timeout=3)
            if native_resp.ok:
                payload = native_resp.json()
                raw_models = payload.get('models') if isinstance(payload, dict) else None
                if isinstance(raw_models, list):
                    models = []
                    for m in raw_models:
                        if not isinstance(m, dict):
                            continue
                        # Filter out embedding models
                        if m.get('type') and m.get('type') != 'llm':
                            continue
                        key = m.get('key') or m.get('id')
                        if not key:
                            continue
                        caps = m.get('capabilities') or {}
                        quant = m.get('quantization')
                        quant_name = quant.get('name') if isinstance(quant, dict) else None
                        models.append({
                            'id': key,
                            'name': m.get('display_name') or key,
                            'params': m.get('params_string'),
                            'quant': quant_name,
                            'context_length': m.get('max_context_length'),
                            'vision': bool(caps.get('vision')),
                            'tools': bool(caps.get('trained_for_tool_use')),
                            'reasoning': bool(caps.get('reasoning')),
                            'loaded': len(m.get('loaded_instances') or []) > 0,
                            'size_bytes': m.get('size_bytes'),
                        })
                    models.sort(key=lambda x: str(x['name']).lower())
                    return jsonify({'models': models, 'is_native_lmstudio': True})
        except Exception:
            pass

        # Fallback to standard OpenAI /models
        try:
            resp = requests.get(f'{api_base}/models', headers=headers, timeout=5)
            if not resp.ok:
                return jsonify({'error': f'Provider returned status {resp.status_code}', 'models': []}), resp.status_code
            payload = resp.json()
            models = []
            if isinstance(payload, dict) and 'data' in payload and isinstance(payload['data'], list):
                for m in payload['data']:
                    if isinstance(m, dict):
                        mid = m.get('id') or m.get('name')
                        if mid:
                            models.append({
                                'id': mid,
                                'name': mid,
                                'loaded': False,
                            })
            elif isinstance(payload, list):
                for m in payload:
                    mid = m.get('id') if isinstance(m, dict) else str(m)
                    if mid:
                        models.append({
                            'id': mid,
                            'name': mid,
                            'loaded': False,
                        })
            models.sort(key=lambda x: str(x['name']).lower())
            return jsonify({'models': models, 'is_native_lmstudio': False})
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Cannot reach provider at {api_base}: {str(e)}', 'models': []}), 502

    @app.route('/api/bench/unload-all', methods=['POST'])
    def unload_all_models():
        """Unload all currently loaded model instances in LM Studio."""
        data = request.get_json(silent=True) or {}
        api_base = (data.get('api_base') or 'http://localhost:1234/v1').rstrip('/')
        api_key = data.get('api_key') or ''
        host_base = re.sub(r'/v1/?$', '', api_base)
        headers = {'Content-Type': 'application/json'}
        if api_key and api_key not in ('not-needed', 'none'):
            headers['Authorization'] = f'Bearer {api_key}'

        unloaded = []
        try:
            resp = requests.get(f'{host_base}/api/v1/models', headers=headers, timeout=5)
            if resp.ok:
                models_data = resp.json().get('models', [])
                for m in models_data:
                    for inst in m.get('loaded_instances', []):
                        inst_id = inst if isinstance(inst, str) else inst.get('id') or inst.get('instance_id')
                        if inst_id:
                            try:
                                requests.post(
                                    f'{host_base}/api/v1/models/unload',
                                    headers=headers,
                                    json={'instance_id': inst_id},
                                    timeout=10
                                )
                                unloaded.append(inst_id)
                            except Exception:
                                pass
            return jsonify({'unloaded': unloaded, 'status': 'ok'})
        except Exception as e:
            return jsonify({'error': str(e), 'unloaded': unloaded}), 502

    @app.route('/api/bench/unload', methods=['POST'])
    def unload_model():
        """Unload a model instance from LM Studio native API."""
        data = request.get_json(silent=True) or {}
        api_base = (data.get('api_base') or 'http://localhost:1234/v1').rstrip('/')
        api_key = data.get('api_key') or ''
        instance_id = data.get('instance_id')
        if not instance_id:
            return jsonify({'error': 'Missing instance_id'}), 400

        host_base = re.sub(r'/v1/?$', '', api_base)
        headers = {'Content-Type': 'application/json'}
        if api_key and api_key not in ('not-needed', 'none'):
            headers['Authorization'] = f'Bearer {api_key}'

        try:
            resp = requests.post(
                f'{host_base}/api/v1/models/unload',
                headers=headers,
                json={'instance_id': instance_id},
                timeout=10
            )
            return jsonify(resp.json() if resp.ok else {'status': 'unloaded', 'instance_id': instance_id}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 502

    @app.route('/api/bench/load', methods=['POST'])
    def load_model():
        """Load a model with custom config into LM Studio native API."""
        data = request.get_json(silent=True) or {}
        api_base = (data.get('api_base') or 'http://localhost:1234/v1').rstrip('/')
        api_key = data.get('api_key') or ''
        model = data.get('model')
        if not model:
            return jsonify({'error': 'Missing model'}), 400

        host_base = re.sub(r'/v1/?$', '', api_base)
        headers = {'Content-Type': 'application/json'}
        if api_key and api_key not in ('not-needed', 'none'):
            headers['Authorization'] = f'Bearer {api_key}'

        load_payload = {
            'model': model,
            'flash_attention': True,
            'offload_kv_cache_to_gpu': True,
        }
        if data.get('context_length'):
            load_payload['context_length'] = int(data['context_length'])

        try:
            resp = requests.post(
                f'{host_base}/api/v1/models/load',
                headers=headers,
                json=load_payload,
                timeout=60
            )
            return jsonify(resp.json() if resp.ok else {'error': resp.text}), resp.status_code
        except Exception as e:
            return jsonify({'error': str(e)}), 502

    @app.route('/api/bench/chat', methods=['POST'])
    def proxy_bench_chat():
        """
        Proxy chat completions call with streaming support.
        Avoids CORS and browser networking quirks.
        """
        data = request.get_json(silent=True) or {}
        api_base = (data.get('api_base') or 'http://localhost:1234/v1').rstrip('/')
        api_key = data.get('api_key') or ''
        model = data.get('model')
        messages = data.get('messages') or []
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 1512)
        stream = data.get('stream', True)

        if not model:
            return jsonify({'error': 'Missing model parameter'}), 400

        headers = {'Content-Type': 'application/json'}
        if api_key and api_key not in ('not-needed', 'none'):
            headers['Authorization'] = f'Bearer {api_key}'

        req_payload = {
            'model': model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stream': stream,
        }
        if stream:
            req_payload['stream_options'] = {'include_usage': True}

        max_attempts = 3
        upstream = None
        for attempt in range(1, max_attempts + 1):
            try:
                upstream = requests.post(
                    f'{api_base}/chat/completions',
                    headers=headers,
                    json=req_payload,
                    stream=stream,
                    timeout=300
                )

                if upstream.status_code == 429 or upstream.status_code in (502, 503, 504):
                    if attempt < max_attempts:
                        retry_after = upstream.headers.get('Retry-After')
                        wait_sec = 2.0 ** attempt
                        if retry_after:
                            try:
                                wait_sec = min(max(float(retry_after), 0.5), 30.0)
                            except ValueError:
                                pass
                        time.sleep(wait_sec)
                        continue

                if not upstream.ok:
                    return jsonify({
                        'error': f'Provider returned HTTP {upstream.status_code}: {upstream.text[:200]}'
                    }), upstream.status_code

                if not stream:
                    return jsonify(upstream.json())

                def generate():
                    for chunk in upstream.iter_content(chunk_size=None):
                        if chunk:
                            yield chunk

                return Response(
                    stream_with_context(generate()),
                    content_type=upstream.headers.get('Content-Type', 'text/event-stream')
                )

            except requests.exceptions.RequestException as e:
                if attempt < max_attempts:
                    time.sleep(2.0 ** attempt)
                    continue
                return jsonify({'error': f'Failed calling {api_base}: {str(e)}'}), 502

    @app.route('/api/bench/runs', methods=['GET'])
    def list_bench_runs():
        """List previously saved benchmark runs."""
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        runs = []
        for file in sorted(RUNS_DIR.glob('*.jsonl'), reverse=True):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    first_line = f.readline()
                    if first_line:
                        rec = json.loads(first_line)
                        runs.append({
                            'run_id': rec.get('run_id', file.stem),
                            'timestamp': rec.get('timestamp'),
                            'character': rec.get('character'),
                            'scenario': rec.get('scenario'),
                            'provider': rec.get('provider'),
                            'model_count': len(rec.get('results', [])),
                        })
            except Exception:
                pass
        return jsonify({'runs': runs})

    @app.route('/api/bench/runs', methods=['POST'])
    def save_bench_run():
        """Save a completed benchmark sweep run."""
        payload = request.get_json(silent=True) or {}
        run_id = payload.get('run_id') or datetime.now().strftime('%Y%m%d_%H%M%S')
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        run_file = RUNS_DIR / f"{run_id}.jsonl"

        record = {
            'run_id': run_id,
            'timestamp': payload.get('timestamp') or datetime.now(timezone.utc).isoformat(),
            'provider': payload.get('provider'),
            'api_base': payload.get('api_base'),
            'character': payload.get('character'),
            'scenario': payload.get('scenario'),
            'prompt_meta': payload.get('prompt_meta', {}),
            'results': payload.get('results', []),
        }

        with open(run_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

        return jsonify({'status': 'saved', 'run_id': run_id})

    @app.route('/api/bench/runs/<run_id>', methods=['GET'])
    def get_bench_run(run_id):
        """Get the full record of a specific benchmark run."""
        safe_id = Path(run_id).name
        run_file = RUNS_DIR / f"{safe_id}.jsonl"
        if not run_file.exists():
            return jsonify({'error': 'Run not found'}), 404
        try:
            with open(run_file, 'r', encoding='utf-8') as f:
                line = f.readline()
                if line:
                    return jsonify(json.loads(line))
            return jsonify({'error': 'Empty run file'}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500

