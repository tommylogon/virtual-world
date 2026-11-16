"""
Probe all LLM providers configured in .env and save sanitized model listing
fixtures to data/model_bench/fixtures/<provider>_models.json for schema analysis.
"""

import json
import os
import re
import sys
from pathlib import Path
import requests

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
FIXTURES_DIR = ROOT_DIR / "data" / "model_bench" / "fixtures"

def load_env(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def sanitize_data(data):
    """Recursively strip credential keys or auth tokens without stripping token counts."""
    if isinstance(data, dict):
        clean = {}
        for k, v in data.items():
            k_lower = k.lower()
            if any(s in k_lower for s in ["api_key", "apikey", "secret", "password", "bearer", "access_token", "refresh_token"]) or k_lower in ("key", "token", "auth"):
                clean[k] = "[REDACTED]"
            else:
                clean[k] = sanitize_data(v)
        return clean
    if isinstance(data, list):
        return [sanitize_data(x) for x in data]
    return data

def main():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    env = load_env(ENV_PATH)

    results_summary = []

    # 1. OpenRouter
    openrouter_key = env.get("OPENROUTER_API_KEY")
    if openrouter_key:
        print("[1/8] Probing OpenRouter...")
        try:
            resp = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {openrouter_key}"},
                timeout=15
            )
            out_file = FIXTURES_DIR / "openrouter_models.json"
            if resp.ok:
                data = sanitize_data(resp.json())
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                model_count = len(data.get("data", []))
                results_summary.append(("OpenRouter", "OK (HTTP 200)", f"{model_count} models saved"))
            else:
                results_summary.append(("OpenRouter", f"HTTP {resp.status_code}", resp.text[:120]))
        except Exception as e:
            results_summary.append(("OpenRouter", "Error", str(e)[:120]))

    # 2. Groq Cloud
    groq_key = env.get("GROQ_API_KEY")
    if groq_key:
        print("[2/8] Probing Groq Cloud...")
        try:
            resp = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {groq_key}"},
                timeout=15
            )
            out_file = FIXTURES_DIR / "groq_models.json"
            if resp.ok:
                data = sanitize_data(resp.json())
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                model_count = len(data.get("data", []))
                results_summary.append(("Groq Cloud", "OK (HTTP 200)", f"{model_count} models saved"))
            else:
                results_summary.append(("Groq Cloud", f"HTTP {resp.status_code}", resp.text[:120]))
        except Exception as e:
            results_summary.append(("Groq Cloud", "Error", str(e)[:120]))

    # 3. Mistral AI
    mistral_key = env.get("MISTRAL_API_KEY")
    if mistral_key:
        print("[3/8] Probing Mistral AI...")
        try:
            resp = requests.get(
                "https://api.mistral.ai/v1/models",
                headers={"Authorization": f"Bearer {mistral_key}"},
                timeout=15
            )
            out_file = FIXTURES_DIR / "mistral_models.json"
            if resp.ok:
                data = sanitize_data(resp.json())
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                model_count = len(data.get("data", []))
                results_summary.append(("Mistral AI", "OK (HTTP 200)", f"{model_count} models saved"))
            else:
                results_summary.append(("Mistral AI", f"HTTP {resp.status_code}", resp.text[:120]))
        except Exception as e:
            results_summary.append(("Mistral AI", "Error", str(e)[:120]))

    # 4. NVIDIA NIM
    nvidia_key = env.get("NVIDIA_NIM_API_KEY")
    if nvidia_key:
        print("[4/8] Probing NVIDIA NIM...")
        try:
            resp = requests.get(
                "https://integrate.api.nvidia.com/v1/models",
                headers={"Authorization": f"Bearer {nvidia_key}"},
                timeout=15
            )
            out_file = FIXTURES_DIR / "nvidia_nim_models.json"
            if resp.ok:
                data = sanitize_data(resp.json())
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                model_count = len(data.get("data", []))
                results_summary.append(("NVIDIA NIM", "OK (HTTP 200)", f"{model_count} models saved"))
            else:
                results_summary.append(("NVIDIA NIM", f"HTTP {resp.status_code}", resp.text[:120]))
        except Exception as e:
            results_summary.append(("NVIDIA NIM", "Error", str(e)[:120]))

    # 5. Google AI Studio (Gemini)
    gemini_key = env.get("GOOGLE_GEMINI_API_KEY")
    if gemini_key:
        print("[5/8] Probing Google Gemini...")
        try:
            resp = requests.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}",
                timeout=15
            )
            out_file = FIXTURES_DIR / "google_gemini_models.json"
            if resp.ok:
                data = sanitize_data(resp.json())
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                model_count = len(data.get("models", []))
                results_summary.append(("Google Gemini", "OK (HTTP 200)", f"{model_count} models saved"))
            else:
                results_summary.append(("Google Gemini", f"HTTP {resp.status_code}", resp.text[:120]))
        except Exception as e:
            results_summary.append(("Google Gemini", "Error", str(e)[:120]))

    # 6. Alibaba (Aliyun MaaS)
    alibaba_key = env.get("ALIBABA_API_KEY")
    alibaba_base = env.get("ALIBABA_BASE", "https://ws-xrqsm1akc5u5zhsu.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1").rstrip("/")
    if alibaba_key:
        print("[6/8] Probing Alibaba...")
        try:
            resp = requests.get(
                f"{alibaba_base}/models",
                headers={"Authorization": f"Bearer {alibaba_key}"},
                timeout=15
            )
            out_file = FIXTURES_DIR / "alibaba_models.json"
            if resp.ok:
                data = sanitize_data(resp.json())
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                model_count = len(data.get("data", [])) if isinstance(data, dict) else len(data)
                results_summary.append(("Alibaba", "OK (HTTP 200)", f"{model_count} models saved"))
            else:
                results_summary.append(("Alibaba", f"HTTP {resp.status_code}", resp.text[:120]))
        except Exception as e:
            results_summary.append(("Alibaba", "Error", str(e)[:120]))

    # 7. Z.ai (GLM)
    z_ai_key = env.get("Z_AI_GLM_KEY")
    z_ai_base = env.get("Z_AI_GLM_BASE", "https://api.z.ai/api/paas/v4").rstrip("/")
    if z_ai_key:
        print("[7/8] Probing Z.ai...")
        try:
            resp = requests.get(
                f"{z_ai_base}/models",
                headers={"Authorization": f"Bearer {z_ai_key}"},
                timeout=15
            )
            out_file = FIXTURES_DIR / "z_ai_models.json"
            if resp.ok:
                data = sanitize_data(resp.json())
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                model_count = len(data.get("data", [])) if isinstance(data, dict) else len(data)
                results_summary.append(("Z.ai", "OK (HTTP 200)", f"{model_count} models saved"))
            else:
                results_summary.append(("Z.ai", f"HTTP {resp.status_code}", resp.text[:120]))
        except Exception as e:
            results_summary.append(("Z.ai", "Error", str(e)[:120]))

    # 8. Local LM Studio
    lmstudio_base = env.get("VW_LLM_BASE", "http://localhost:1234/v1").rstrip("/")
    host_root = re.sub(r"/v1/?$", "", lmstudio_base)
    print("[8/8] Probing Local LM Studio...")
    try:
        resp = requests.get(f"{host_root}/api/v1/models", timeout=3)
        out_file = FIXTURES_DIR / "lmstudio_models.json"
        if resp.ok:
            data = sanitize_data(resp.json())
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            model_count = len(data.get("models", []))
            results_summary.append(("LM Studio", "OK (HTTP 200)", f"{model_count} models saved"))
        else:
            results_summary.append(("LM Studio", f"HTTP {resp.status_code}", resp.text[:120]))
    except Exception as e:
        results_summary.append(("LM Studio", "Offline / Refused", str(e)[:60]))

    print("\n--- RESULTS SUMMARY ---")
    for prov, status, note in results_summary:
        print(f"{prov:<18} | {status:<15} | {note}")

if __name__ == "__main__":
    main()
