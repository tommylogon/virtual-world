"""HTTP endpoints for LLM backend provider profiles and env credentials.

@module profiles_routes
@contributes provider profile listing, saving, deleting, and env credentials inspection
@powers backend provider profile switching and credentials configuration
@relates static/js/ui/settings-view.ts
@docs docs/virtualWorld/dev_tasks/done/ui/task-910-backend-provider-profiles-and-env-credentials-persistence.md
"""
import os
import json
import logging
from flask import request, jsonify
from dotenv import dotenv_values

logger = logging.getLogger(__name__)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(REPO_ROOT, ".env")
CONFIG_DIR = os.path.join(REPO_ROOT, "data", "config")
PROFILES_FILE = os.path.join(CONFIG_DIR, "profiles.json")


def _ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def _load_persisted():
    _ensure_config_dir()
    if not os.path.exists(PROFILES_FILE):
        return {"profiles": {}, "lastProfile": None}
    try:
        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return {
                    "profiles": data.get("profiles", {}),
                    "lastProfile": data.get("lastProfile")
                }
    except Exception as e:
        logger.warning(f"Could not load persisted profiles: {e}")
    return {"profiles": {}, "lastProfile": None}


def _save_persisted(data):
    _ensure_config_dir()
    try:
        tmp_file = f"{PROFILES_FILE}.tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_file, PROFILES_FILE)
    except Exception as e:
        logger.error(f"Failed to save persisted profiles: {e}")


def _get_env_profiles():
    env = {}
    if os.path.exists(ENV_FILE):
        try:
            env = dotenv_values(ENV_FILE)
        except Exception as e:
            logger.warning(f"Could not parse .env file: {e}")
    # Also fallback to os.environ for container/environment setups
    for k, v in os.environ.items():
        if k not in env:
            env[k] = v

    defaults = {
        "LM Studio (Local)": {
            "apiKey": "not-needed",
            "apiBase": env.get("VW_LLM_BASE") or "http://localhost:1234/v1",
            "model": env.get("VW_LLM_MODEL") or "glm-4-9b-0414",
            "provider": "openai",
            "apiFormat": "lmstudio",
            "streaming": True,
            "showLogs": False,
            "turnBased": False,
            "turnOrder": "sequential"
        },
        "Groq": {
            "apiKey": env.get("GROQ_API_KEY") or "",
            "apiBase": env.get("GROQ_BASE") or "https://api.groq.com/openai/v1",
            "model": env.get("GROQ_MODEL") or "llama-3.3-70b-versatile",
            "provider": "groq",
            "apiFormat": "openai",
            "streaming": True,
            "showLogs": False,
            "turnBased": False,
            "turnOrder": "sequential"
        },
        "Mistral": {
            "apiKey": env.get("MISTRAL_API_KEY") or "",
            "apiBase": env.get("MISTRAL_BASE") or "https://api.mistral.ai/v1",
            "model": env.get("MISTRAL_MODEL") or "mistral-large-latest",
            "provider": "mistral",
            "apiFormat": "openai",
            "streaming": True,
            "showLogs": False,
            "turnBased": False,
            "turnOrder": "sequential"
        },
        "NVIDIA NIM": {
            "apiKey": env.get("NVIDIA_NIM_API_KEY") or "",
            "apiBase": env.get("NVIDIA_NIM_BASE") or "https://integrate.api.nvidia.com/v1",
            "model": env.get("NVIDIA_NIM_MODEL") or "llama-3.3-70b-instruct",
            "provider": "nvidia",
            "apiFormat": "openai",
            "streaming": True,
            "showLogs": False,
            "turnBased": False,
            "turnOrder": "sequential"
        },
        "Google Gemini": {
            "apiKey": env.get("GOOGLE_GEMINI_API_KEY") or "",
            "apiBase": env.get("GOOGLE_GEMINI_BASE") or "https://generativelanguage.googleapis.com/v1",
            "model": env.get("GOOGLE_GEMINI_MODEL") or "gemini-1.5-flash",
            "provider": "google",
            "apiFormat": "openai",
            "streaming": True,
            "showLogs": False,
            "turnBased": False,
            "turnOrder": "sequential"
        },
        "OpenRouter": {
            "apiKey": env.get("OPENROUTER_API_KEY") or "",
            "apiBase": env.get("OPENROUTER_BASE") or "https://openrouter.ai/api/v1",
            "model": env.get("OPENROUTER_MODEL") or "deepseek/deepseek-r1",
            "provider": "openrouter",
            "apiFormat": "openai",
            "streaming": True,
            "showLogs": False,
            "turnBased": False,
            "turnOrder": "sequential"
        },
        "Alibaba": {
            "apiKey": env.get("ALIBABA_API_KEY") or "",
            "apiBase": env.get("ALIBABA_BASE") or "https://ws-xrqsm1akc5u5zhsu.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
            "model": env.get("ALIBABA_MODEL") or "deepseek-v4.1-flash-1017",
            "provider": "alibaba",
            "apiFormat": "openai",
            "streaming": True,
            "showLogs": False,
            "turnBased": False,
            "turnOrder": "sequential"
        },
        "Z.ai": {
            "apiKey": env.get("Z_AI_GLM_KEY") or "",
            "apiBase": env.get("Z_AI_GLM_BASE") or "https://api.z.ai/v1",
            "model": env.get("Z_AI_GLM_MODEL") or "glm-4-9b-0414",
            "provider": "z_ai",
            "apiFormat": "openai",
            "streaming": True,
            "showLogs": False,
            "turnBased": False,
            "turnOrder": "sequential"
        },
        "OpenAI": {
            "apiKey": env.get("OPENAI_API_KEY") or "",
            "apiBase": env.get("OPENAI_BASE_URL") or env.get("OPENAI_API_BASE") or "https://api.openai.com/v1",
            "model": env.get("OPENAI_MODEL") or "gpt-4o",
            "provider": "openai",
            "apiFormat": "openai",
            "streaming": False,
            "showLogs": False,
            "turnBased": False,
            "turnOrder": "sequential"
        },
        "DeepSeek": {
            "apiKey": env.get("DEEPSEEK_API_KEY") or "",
            "apiBase": env.get("DEEPSEEK_BASE") or "https://api.deepseek.com/v1",
            "model": env.get("DEEPSEEK_MODEL") or "deepseek-chat",
            "provider": "openai",
            "apiFormat": "openai",
            "streaming": True,
            "showLogs": False,
            "turnBased": False,
            "turnOrder": "sequential"
        }
    }
    return defaults


def register_profiles_routes(app):
    """Register server-side profile persistence and .env credential management routes."""

    @app.route("/api/profiles", methods=["GET"])
    def get_profiles():
        """Get merged profiles: built-ins from .env and user custom profiles."""
        persisted = _load_persisted()
        env_profiles = _get_env_profiles()

        # Merge order: env defaults first, then user persisted custom profiles override/supplement
        merged = dict(env_profiles)
        merged.update(persisted.get("profiles", {}))

        last_profile = persisted.get("lastProfile")
        if not last_profile or last_profile not in merged:
            last_profile = "LM Studio (Local)" if "LM Studio (Local)" in merged else list(merged.keys())[0]

        return jsonify({
            "status": "ok",
            "profiles": merged,
            "lastProfile": last_profile
        })

    @app.route("/api/profiles", methods=["POST"])
    def save_profile():
        """Create or update a custom profile."""
        payload = request.get_json() or {}
        name = (payload.get("name") or "").strip()
        data = payload.get("data")
        if not name:
            return jsonify({"error": "Profile name is required"}), 400
        if not isinstance(data, dict):
            return jsonify({"error": "Profile data must be an object"}), 400

        persisted = _load_persisted()
        persisted.setdefault("profiles", {})[name] = data
        persisted["lastProfile"] = name
        _save_persisted(persisted)

        logger.info(f"Saved custom profile: {name}")
        return jsonify({"status": "ok", "name": name})

    @app.route("/api/profiles/<path:name>", methods=["DELETE"])
    def delete_profile(name):
        """Delete a custom profile."""
        name = (name or "").strip()
        persisted = _load_persisted()
        profiles = persisted.get("profiles", {})
        if name in profiles:
            del profiles[name]
            if persisted.get("lastProfile") == name:
                persisted["lastProfile"] = None
            _save_persisted(persisted)
            logger.info(f"Deleted custom profile: {name}")

        return jsonify({"status": "ok"})

    @app.route("/api/profiles/active", methods=["POST"])
    def set_active_profile():
        """Set the active profile name."""
        payload = request.get_json() or {}
        name = (payload.get("name") or "").strip()
        if not name:
            return jsonify({"error": "Profile name is required"}), 400

        persisted = _load_persisted()
        persisted["lastProfile"] = name
        _save_persisted(persisted)

        return jsonify({"status": "ok", "lastProfile": name})
