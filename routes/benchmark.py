"""
routes/benchmark.py - API routes for LLM prompt benchmarking.

Provides:
- Page view: /bench
- Model listing proxy: POST /api/bench/models (to avoid browser CORS issues)
- LLM streaming/completion proxy: POST /api/bench/chat
- Run persistence: GET/POST /api/bench/runs

@module benchmark
@contributes register_benchmark_routes
@docs none - HTTP API route handler
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
REGISTRY_FILE = BENCH_DIR / "model_registry.json"


def load_model_registry() -> dict:
    """Load the persistent model metadata registry."""
    if not REGISTRY_FILE.exists():
        return {}
    try:
        with open(REGISTRY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read model_registry.json: {e}")
        return {}


def save_model_registry(registry: dict) -> bool:
    """Atomically save the persistent model metadata registry."""
    BENCH_DIR.mkdir(parents=True, exist_ok=True)
    tmp_file = BENCH_DIR / "model_registry.json.tmp"
    try:
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
        tmp_file.replace(REGISTRY_FILE)
        return True
    except Exception as e:
        logger.error(f"Failed to write model_registry.json: {e}")
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except Exception:
                pass
        return False


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

    @app.route('/api/models', methods=['POST'])
    @app.route('/api/bench/models', methods=['POST'])
    def fetch_provider_models():
        """Fetch model list from an external provider (with rich native detection for LM Studio, OpenRouter, Groq, Mistral, Gemini)."""
        data = request.get_json(silent=True) or {}
        api_base = (data.get('api_base') or 'http://localhost:1234/v1').rstrip('/')
        if 'generativelanguage.googleapis.com' in api_base and not api_base.endswith('/openai'):
            gemini_root = re.sub(r'/v1(?:beta)?/?$', '', api_base)
            api_base = f'{gemini_root}/v1beta/openai'
        api_key = data.get('api_key') or ''

        headers = {'Content-Type': 'application/json'}
        if api_key and api_key not in ('not-needed', 'none'):
            headers['Authorization'] = f'Bearer {api_key}'
            headers['x-goog-api-key'] = api_key

        registry = load_model_registry()
        registry_dirty = False

        def apply_registry_overlay(model_dict):
            nonlocal registry_dirty
            mid = model_dict['id']
            if mid in registry:
                entry = registry[mid]
                if 'status' in entry:
                    model_dict['status'] = entry['status']
                if 'reason' in entry:
                    model_dict['reason'] = entry['reason']
                if 'notes' in entry:
                    model_dict['notes'] = entry['notes']
                if 'is_free' in entry:
                    model_dict['is_free'] = bool(entry['is_free'])
                if 'ratings' in entry:
                    model_dict['ratings'] = entry['ratings']
                for cap_key in ('vision', 'tools', 'reasoning', 'structured_outputs'):
                    if cap_key in entry and entry[cap_key] is not None:
                        model_dict[cap_key] = bool(entry[cap_key])
                if 'context_length' in entry and entry['context_length']:
                    model_dict['context_length'] = entry['context_length']
            else:
                # Seed auto-detected flags into registry for cross-system awareness
                cur_status = model_dict.get('status', 'active')
                is_free = bool(model_dict.get('is_free', False))
                if cur_status != 'active' or is_free:
                    registry[mid] = {
                        'display_name': model_dict.get('name') or mid,
                        'status': cur_status,
                        'reason': model_dict.get('reason'),
                        'notes': model_dict.get('notes'),
                        'is_free': is_free,
                        'context_length': model_dict.get('context_length'),
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }
                    registry_dirty = True
            return model_dict

        # 1. Google Gemini native models endpoint
        # Note: Google's native REST API (/v1beta/models) rejects requests that
        # carry `Authorization: Bearer <API_KEY>` with 401 UNAUTHORIZED because
        # it treats Bearer tokens strictly as OAuth2 tokens. Use only `?key=`
        # and `x-goog-api-key`, and normalize `/v1` or `/v1beta/openai` to
        # `/v1beta/models`.
        if 'generativelanguage.googleapis.com' in api_base:
            try:
                gemini_root = re.sub(r'/v1(?:beta)?(?:/openai)?/?$', '', api_base)
                gemini_url = f"{gemini_root}/v1beta/models"
                gemini_headers = {'Content-Type': 'application/json'}
                params = {}
                if api_key and api_key not in ('not-needed', 'none'):
                    params['key'] = api_key
                    gemini_headers['x-goog-api-key'] = api_key
                resp = requests.get(gemini_url, headers=gemini_headers, params=params, timeout=10)
                if not resp.ok:
                    return jsonify({'error': f'Google Gemini returned status {resp.status_code}', 'models': []}), resp.status_code
                payload = resp.json()
                raw_models = payload.get('models', [])
                models = []
                for m in raw_models:
                    if not isinstance(m, dict):
                        continue
                    full_name = m.get('name', '')
                    mid = full_name.replace('models/', '') if full_name.startswith('models/') else full_name
                    if not mid:
                        continue
                    methods = m.get('supportedGenerationMethods') or []
                    is_chat = 'generateContent' in methods
                    is_embed = 'embedContent' in methods and not is_chat
                    models.append(apply_registry_overlay({
                        'id': mid,
                        'name': m.get('displayName') or mid,
                        'description': m.get('description') or '',
                        'context_length': m.get('inputTokenLimit'),
                        'max_output_tokens': m.get('outputTokenLimit'),
                        'vision': 'gemini' in mid.lower() and any(k in mid.lower() for k in ['flash', 'pro', 'ultra']),
                        'tools': is_chat,
                        'structured_outputs': is_chat,
                        'supports_temperature': is_chat,
                        'supports_top_p': is_chat,
                        'reasoning': bool(m.get('thinking')),
                        'loaded': False,
                        'is_free': False,
                        'status': 'do_not_use' if is_embed else 'active',
                        'reason': 'embeddings' if is_embed else None,
                    }))
                models.sort(key=lambda x: str(x['name']).lower())
                if registry_dirty:
                    save_model_registry(registry)
                return jsonify({'models': models, 'is_native_lmstudio': False})
            except requests.exceptions.RequestException as e:
                return jsonify({'error': f'Cannot reach Google Gemini at {api_base}: {str(e)}', 'models': []}), 502

        # 2. Try LM Studio native endpoint first if host root provides /api/v1/models
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
                        # Filter out embedding models from standard chat list
                        if m.get('type') and m.get('type') != 'llm':
                            continue
                        key = m.get('key') or m.get('id')
                        if not key:
                            continue
                        caps = m.get('capabilities') or {}
                        quant = m.get('quantization')
                        quant_name = quant.get('name') if isinstance(quant, dict) else None
                        models.append(apply_registry_overlay({
                            'id': key,
                            'name': m.get('display_name') or key,
                            'description': m.get('description') or '',
                            'params': m.get('params_string'),
                            'quant': quant_name,
                            'context_length': m.get('max_context_length'),
                            'vision': bool(caps.get('vision')),
                            'tools': bool(caps.get('trained_for_tool_use')),
                            'structured_outputs': True,
                            'supports_temperature': True,
                            'supports_top_p': True,
                            'reasoning': bool(caps.get('reasoning')),
                            'loaded': len(m.get('loaded_instances') or []) > 0,
                            'size_bytes': m.get('size_bytes'),
                            'is_free': True,  # Local models are zero-cost
                            'status': 'active',
                        }))
                    models.sort(key=lambda x: str(x['name']).lower())
                    if registry_dirty:
                        save_model_registry(registry)
                    return jsonify({'models': models, 'is_native_lmstudio': True})
        except Exception:
            pass

        # 3. Fallback to standard OpenAI-compatible /models endpoint
        try:
            resp = requests.get(f'{api_base}/models', headers=headers, timeout=8)
            if not resp.ok:
                return jsonify({'error': f'Provider returned status {resp.status_code}', 'models': []}), resp.status_code
            payload = resp.json()
            raw_list = []
            if isinstance(payload, dict) and 'data' in payload and isinstance(payload['data'], list):
                raw_list = payload['data']
            elif isinstance(payload, list):
                raw_list = payload

            models = []
            is_openrouter = 'openrouter.ai' in api_base
            is_groq = 'groq.com' in api_base
            is_mistral = 'mistral.ai' in api_base

            for m in raw_list:
                if not isinstance(m, dict):
                    mid = str(m)
                    m = {'id': mid, 'name': mid}
                mid = m.get('id') or m.get('name')
                if not mid:
                    continue

                m_obj = {
                    'id': mid,
                    'name': m.get('name') or mid,
                    'loaded': False,
                    'status': 'active',
                    'reason': None,
                    'is_free': False
                }

                if is_openrouter:
                    m_obj['context_length'] = m.get('context_length')
                    top_prov = m.get('top_provider')
                    if isinstance(top_prov, dict):
                        m_obj['max_output_tokens'] = top_prov.get('max_completion_tokens')
                    pricing = m.get('pricing') or {}
                    if isinstance(pricing, dict):
                        m_obj['pricing'] = pricing
                        if str(pricing.get('prompt')) == '0' and str(pricing.get('completion')) == '0':
                            m_obj['is_free'] = True
                    arch = m.get('architecture') or {}
                    if isinstance(arch, dict):
                        in_mod = arch.get('input_modalities') or []
                        out_mod = arch.get('output_modalities') or []
                        m_obj['vision'] = 'image' in in_mod
                        if len(out_mod) > 0 and 'text' not in out_mod:
                            m_obj['status'] = 'do_not_use'
                            m_obj['reason'] = 'audio_video'

                    # OpenRouter Extended Parameters & Capabilities
                    params = m.get('supported_parameters') or []
                    m_obj['supported_parameters'] = params
                    m_obj['tools'] = 'tools' in params
                    m_obj['structured_outputs'] = 'structured_outputs' in params or 'response_format' in params
                    m_obj['supports_temperature'] = 'temperature' in params
                    m_obj['supports_top_p'] = 'top_p' in params
                    m_obj['description'] = m.get('description') or ''

                    reasoning_obj = m.get('reasoning')
                    if isinstance(reasoning_obj, dict):
                        m_obj['reasoning'] = True
                        m_obj['reasoning_details'] = {
                            'mandatory': bool(reasoning_obj.get('mandatory')),
                            'supported_efforts': reasoning_obj.get('supported_efforts') or ['high'],
                            'default_effort': reasoning_obj.get('default_effort') or 'high'
                        }
                    elif m.get('reasoning'):
                        m_obj['reasoning'] = True
                        m_obj['reasoning_details'] = {
                            'mandatory': False,
                            'supported_efforts': ['none', 'low', 'medium', 'high'],
                            'default_effort': 'medium'
                        }

                    bench = m.get('benchmarks') or {}
                    aa = bench.get('artificial_analysis') if isinstance(bench, dict) else None
                    if isinstance(aa, dict) and aa.get('intelligence_index') is not None:
                        m_obj['score'] = aa.get('intelligence_index')

                elif is_groq:
                    m_obj['context_length'] = m.get('context_window') or m.get('context_length')
                    m_obj['max_output_tokens'] = m.get('max_completion_tokens')
                    m_obj['pricing'] = m.get('pricing')
                    m_obj['tools'] = True
                    m_obj['structured_outputs'] = True
                    m_obj['supports_temperature'] = True
                    m_obj['supports_top_p'] = True
                    in_mod = m.get('input_modalities') or []
                    out_mod = m.get('output_modalities') or []
                    m_obj['vision'] = 'image' in in_mod
                    if any(x in out_mod for x in ['transcription', 'speech']):
                        m_obj['status'] = 'do_not_use'
                        m_obj['reason'] = 'audio_video'
                    elif (m.get('context_window') or 0) <= 512 and 'guard' in mid.lower():
                        m_obj['status'] = 'do_not_use'
                        m_obj['reason'] = 'broken'

                elif is_mistral:
                    m_obj['context_length'] = m.get('max_context_length')
                    caps = m.get('capabilities') or {}
                    m_obj['tools'] = bool(caps.get('function_calling'))
                    m_obj['structured_outputs'] = True
                    m_obj['supports_temperature'] = True
                    m_obj['supports_top_p'] = True
                    m_obj['vision'] = bool(caps.get('vision'))
                    m_obj['reasoning'] = bool(caps.get('reasoning'))
                    if caps.get('completion_chat') is False:
                        m_obj['status'] = 'do_not_use'
                        m_obj['reason'] = 'embeddings' if 'embed' in mid.lower() else 'broken'

                # Generic non-chat heuristics
                mid_lower = mid.lower()
                if m_obj['status'] == 'active':
                    if 'embed' in mid_lower or 'nomic-embed' in mid_lower:
                        m_obj['status'] = 'do_not_use'
                        m_obj['reason'] = 'embeddings'
                    elif any(k in mid_lower for k in ['realtime', 'whisper', 'tts', 'flux', 'sdxl', 'dall-e']):
                        m_obj['status'] = 'do_not_use'
                        m_obj['reason'] = 'audio_video'

                # Parameter size regex inference if not explicit
                p_match = re.search(r'[\-_](\d+(?:\.\d+)?)b\b', mid, re.IGNORECASE) or re.search(r'\b(\d+(?:\.\d+)?)b\b', mid, re.IGNORECASE)
                if p_match:
                    m_obj['params'] = f"{p_match.group(1)}B"

                models.append(apply_registry_overlay(m_obj))

            models.sort(key=lambda x: str(x['name']).lower())
            if registry_dirty:
                save_model_registry(registry)
            return jsonify({'models': models, 'is_native_lmstudio': False})

        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Cannot reach provider at {api_base}: {str(e)}', 'models': []}), 502

    @app.route('/api/bench/unload-all', methods=['POST'])
    def unload_all_models():
        """Unload all currently loaded model instances in LM Studio."""
        data = request.get_json(silent=True) or {}
        api_base = (data.get('api_base') or 'http://localhost:1234/v1').rstrip('/')
        if 'generativelanguage.googleapis.com' in api_base and not api_base.endswith('/openai'):
            gemini_root = re.sub(r'/v1(?:beta)?/?$', '', api_base)
            api_base = f'{gemini_root}/v1beta/openai'
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
        if 'generativelanguage.googleapis.com' in api_base and not api_base.endswith('/openai'):
            gemini_root = re.sub(r'/v1(?:beta)?/?$', '', api_base)
            api_base = f'{gemini_root}/v1beta/openai'
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
        if 'generativelanguage.googleapis.com' in api_base and not api_base.endswith('/openai'):
            gemini_root = re.sub(r'/v1(?:beta)?/?$', '', api_base)
            api_base = f'{gemini_root}/v1beta/openai'
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
        if 'generativelanguage.googleapis.com' in api_base and not api_base.endswith('/openai'):
            gemini_root = re.sub(r'/v1(?:beta)?/?$', '', api_base)
            api_base = f'{gemini_root}/v1beta/openai'
        api_key = data.get('api_key') or ''
        model = data.get('model')
        messages = data.get('messages') or []
        temperature = data.get('temperature', 0.7)
        raw_max_tokens = data.get('max_tokens', None)
        max_tokens = None
        if raw_max_tokens not in (None, '', 0, '0'):
            try:
                parsed_max = int(raw_max_tokens)
                if parsed_max > 0:
                    max_tokens = parsed_max
            except (TypeError, ValueError):
                max_tokens = None
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
            'stream': stream,
        }
        if max_tokens is not None:
            req_payload['max_tokens'] = max_tokens
        reasoning_effort = data.get('reasoning_effort')
        raw_reasoning_max = data.get('reasoning_max_tokens')
        reasoning_max_tokens = None
        if raw_reasoning_max is not None and str(raw_reasoning_max).strip() != '':
            try:
                parsed_rm = int(raw_reasoning_max)
                if parsed_rm > 0:
                    reasoning_max_tokens = parsed_rm
            except (TypeError, ValueError):
                pass
        is_openrouter = 'openrouter.ai' in api_base
        is_local = 'localhost' in api_base or '127.0.0.1' in api_base
        is_deepseek = 'deepseek.com' in api_base
        supports_reasoning_effort = is_openrouter or is_local or is_deepseek or 'generativelanguage.googleapis.com' in api_base or 'api.openai.com' in api_base
        if reasoning_effort == 'none':
            if is_local or is_deepseek:
                req_payload['extra_body'] = {'thinking': {'type': 'disabled'}}
                req_payload['enable_thinking'] = False
            if is_openrouter or is_local:
                req_payload['reasoning'] = {'exclude': True}
        elif reasoning_max_tokens is not None:
            if is_openrouter or is_local:
                req_payload['reasoning'] = {'max_tokens': reasoning_max_tokens}
            elif supports_reasoning_effort and reasoning_effort and reasoning_effort != 'default':
                req_payload['reasoning_effort'] = reasoning_effort
            if is_local or is_deepseek:
                req_payload['extra_body'] = {'thinking': {'type': 'enabled', 'budget_tokens': reasoning_max_tokens}}
        elif reasoning_effort and reasoning_effort != 'default':
            if supports_reasoning_effort:
                req_payload['reasoning_effort'] = reasoning_effort
            if is_local or is_deepseek:
                req_payload['extra_body'] = {'thinking': {'type': 'enabled'}}
            if is_openrouter or is_local:
                req_payload['reasoning'] = {'effort': reasoning_effort}

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
                        'error': f'Provider returned HTTP {upstream.status_code}: {upstream.text}'
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

    @app.route('/api/llm/proxy', methods=['POST'])
    def proxy_llm_request():
        """Transparent passthrough proxy for browser LLMClient calls to providers without CORS headers."""
        data = request.get_json(silent=True) or {}
        endpoint_url = (data.get('endpoint_url') or '').strip()
        req_headers = data.get('headers') or {}
        req_body = data.get('body') or {}
        if not endpoint_url or not (endpoint_url.startswith('https://') or endpoint_url.startswith('http://')):
            return jsonify({'error': 'Invalid endpoint_url'}), 400
        stream = bool(isinstance(req_body, dict) and req_body.get('stream'))
        try:
            upstream = requests.post(
                endpoint_url,
                headers=req_headers,
                json=req_body,
                stream=stream,
                timeout=300
            )
            if not upstream.ok:
                try:
                    return jsonify(upstream.json()), upstream.status_code
                except Exception:
                    return Response(
                        upstream.text,
                        status=upstream.status_code,
                        content_type=upstream.headers.get('Content-Type', 'text/plain')
                    )
            if not stream:
                return Response(
                    upstream.content,
                    status=upstream.status_code,
                    content_type=upstream.headers.get('Content-Type', 'application/json')
                )

            def generate():
                for chunk in upstream.iter_content(chunk_size=None):
                    if chunk:
                        yield chunk

            return Response(
                stream_with_context(generate()),
                status=upstream.status_code,
                content_type=upstream.headers.get('Content-Type', 'text/event-stream')
            )
        except requests.exceptions.RequestException as e:
            return jsonify({'error': {'message': f'Upstream LLM request failed: {str(e)}'}}), 502

    @app.route('/api/bench/runs', methods=['GET'])
    def list_bench_runs():
        """List previously saved benchmark runs with rich summary metadata."""
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        runs = []
        for file in sorted(RUNS_DIR.glob('*.jsonl'), reverse=True):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    first_line = f.readline()
                    if first_line:
                        rec = json.loads(first_line)
                        results = rec.get('results') or []
                        completed_count = 0
                        failed_count = 0
                        top_model = None
                        top_score = -1
                        for r in results:
                            if not isinstance(r, dict):
                                continue
                            has_err = bool(r.get('error')) or r.get('status') in ('error', 'failed')
                            if has_err:
                                failed_count += 1
                            else:
                                completed_count += 1
                                sc = r.get('score')
                                if isinstance(sc, (int, float)) and sc > top_score:
                                    top_score = sc
                                    top_model = {'model': r.get('model'), 'score': sc}
                        cfg = rec.get('config') if isinstance(rec.get('config'), dict) else {}
                        runs.append({
                            'run_id': rec.get('run_id', file.stem),
                            'timestamp': rec.get('timestamp'),
                            'character': rec.get('character'),
                            'scenario': rec.get('scenario'),
                            'area': cfg.get('area') or rec.get('area'),
                            'provider': rec.get('provider'),
                            'api_base': rec.get('api_base'),
                            'model_count': len(results),
                            'completed_count': completed_count,
                            'failed_count': failed_count,
                            'config': cfg,
                            'top_model': top_model,
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
            'area': payload.get('area'),
            'config': payload.get('config', {}),
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

    @app.route('/api/bench/models/metadata', methods=['GET'])
    def get_models_metadata():
        """Get the full dictionary of stored model metadata and operational statuses."""
        registry = load_model_registry()
        return jsonify({'metadata': registry})

    @app.route('/api/bench/models/metadata', methods=['POST'])
    def update_model_metadata():
        """Update operational status, reason, notes, or is_free flag for a model."""
        payload = request.get_json(silent=True) or {}
        model_id = payload.get('model_id')
        if not model_id:
            return jsonify({'error': 'Missing model_id'}), 400

        registry = load_model_registry()
        entry = registry.setdefault(model_id, {})
        if 'display_name' in payload:
            entry['display_name'] = payload['display_name']
        if 'status' in payload:
            entry['status'] = payload['status']
        if 'reason' in payload:
            entry['reason'] = payload['reason']
        if 'notes' in payload:
            entry['notes'] = payload['notes']
        if 'is_free' in payload:
            entry['is_free'] = bool(payload['is_free'])
        for cap_key in ('vision', 'tools', 'reasoning', 'structured_outputs'):
            if cap_key in payload and payload[cap_key] is not None:
                entry[cap_key] = bool(payload[cap_key])
        if 'context_length' in payload:
            try:
                ctx_val = int(payload['context_length']) if payload['context_length'] not in (None, '') else None
                if ctx_val and ctx_val > 0:
                    entry['context_length'] = ctx_val
            except (ValueError, TypeError):
                pass
        if 'rating' in payload and payload['rating'] not in (None, ''):
            try:
                r_val = float(payload['rating'])
                if 1.0 <= r_val <= 5.0:
                    ratings_obj = entry.setdefault('ratings', {'total_reviews': 0, 'average_score': 0.0, 'common_tags': []})
                    old_total = ratings_obj.get('total_reviews', 0)
                    old_avg = ratings_obj.get('average_score', 0.0)
                    new_total = old_total + 1
                    ratings_obj['total_reviews'] = new_total
                    ratings_obj['average_score'] = round(((old_avg * old_total) + r_val) / new_total, 2)
            except (ValueError, TypeError):
                pass
        if 'tags' in payload and isinstance(payload['tags'], list):
            entry['tags'] = payload['tags']
        entry['updated_at'] = datetime.now(timezone.utc).isoformat()

        if save_model_registry(registry):
            return jsonify({'status': 'saved', 'model_id': model_id, 'metadata': entry})
        return jsonify({'error': 'Failed to save model registry'}), 500

    @app.route('/api/bench/runs/<run_id>/rate', methods=['POST'])
    def rate_bench_run_result(run_id):
        """Attach a 1-5 star rating and feedback note to a model result in a run, and rollup to registry."""
        safe_id = Path(run_id).name
        run_file = RUNS_DIR / f"{safe_id}.jsonl"
        if not run_file.exists():
            return jsonify({'error': 'Run not found'}), 404

        payload = request.get_json(silent=True) or {}
        model_id = payload.get('model')
        rating = payload.get('rating')
        feedback = payload.get('feedback', '')
        tags = payload.get('tags') or []

        if not model_id or rating is None:
            return jsonify({'error': 'Missing model or rating'}), 400

        try:
            rating_val = float(rating)
            if not (1.0 <= rating_val <= 5.0):
                return jsonify({'error': 'Rating must be between 1 and 5'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid numeric rating'}), 400

        # Update JSONL run record
        updated_result = None
        records = []
        try:
            with open(run_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    results = rec.get('results', [])
                    for res in results:
                        if res.get('model') == model_id:
                            res['rating'] = rating_val
                            res['feedback'] = feedback
                            if tags:
                                res['tags'] = tags
                            updated_result = res
                    records.append(rec)

            if not updated_result and records:
                fallback_entry = {
                    'model': model_id,
                    'rating': rating_val,
                    'feedback': feedback,
                }
                if tags:
                    fallback_entry['tags'] = tags
                records[0].setdefault('results', []).append(fallback_entry)
                updated_result = fallback_entry

            if not updated_result:
                return jsonify({'error': f'Model {model_id} not found in run'}), 404

            with open(run_file, 'w', encoding='utf-8') as f:
                for rec in records:
                    f.write(json.dumps(rec, ensure_ascii=False) + '\n')

        except Exception as e:
            return jsonify({'error': f'Failed updating run record: {str(e)}'}), 500

        # Rollup aggregate rating into model_registry.json
        try:
            registry = load_model_registry()
            entry = registry.setdefault(model_id, {})
            ratings_obj = entry.setdefault('ratings', {'total_reviews': 0, 'average_score': 0.0, 'common_tags': []})
            old_total = ratings_obj.get('total_reviews', 0)
            old_avg = ratings_obj.get('average_score', 0.0)
            new_total = old_total + 1
            new_avg = round(((old_avg * old_total) + rating_val) / new_total, 2)
            ratings_obj['total_reviews'] = new_total
            ratings_obj['average_score'] = new_avg
            if tags:
                existing_tags = set(ratings_obj.get('common_tags', []))
                existing_tags.update(tags)
                ratings_obj['common_tags'] = sorted(list(existing_tags))
            entry['updated_at'] = datetime.now(timezone.utc).isoformat()
            save_model_registry(registry)
        except Exception as e:
            logger.warning(f"Failed rolling up rating to registry: {e}")

        return jsonify({
            'status': 'rated',
            'run_id': safe_id,
            'model': model_id,
            'rating': rating_val,
            'feedback': feedback
        })

