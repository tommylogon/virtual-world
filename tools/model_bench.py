#!/usr/bin/env python3
"""
tools/model_bench.py — LLM benchmark harness for VirtualWorld turn prompts.

Runs a single character's turn prompt across all models of a selected provider
(default LM Studio), with per-model metrics (TTFT, TPS, total latency, token
counts), JSON validity validation, hallucination detection against /api/state
ground truth, JSONL run records, and an HTML dashboard.

The prompt is captured from the live browser via Playwright, calling the exact
same PromptBuilder functions the agent engine uses — never reimplemented in
Python. The app runs on a scratch port (never 4444); no turn is committed and
no world state is mutated by the benchmark itself.

Usage:
    python tools/model_bench.py --scenario kraktooth_goblin_camp --character Zikka
    python tools/model_bench.py --scenario apartment --character "Player One" --size-limit 10 --max-models 5
    python tools/model_bench.py --character Zikka --provider lmstudio --api-base http://localhost:1234/v1

Requires: pip install playwright requests  (and `python -m playwright install chromium`)
"""

import argparse
import html
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
BENCH_DIR = DATA_DIR / "model_bench"
RUNS_DIR = BENCH_DIR / "runs"
DASHBOARD_DIR = BENCH_DIR / "dashboard"

DEFAULT_PROVIDER = "lmstudio"
DEFAULT_API_BASE = "http://localhost:1234/v1"
DEFAULT_PORT = 4455  # scratch port, never 4444
DEFAULT_SIZE_LIMIT = 10  # billion parameters
DEFAULT_MAX_TOKENS = 512


def log(msg):
    print(f"[model_bench] {msg}", flush=True)


def start_app(port):
    """Start the Flask app on a scratch port. Returns the Popen handle."""
    env = os.environ.copy()
    env["VW_PORT"] = str(port)
    env["VW_DEBUG"] = "0"
    log(f"Starting Flask app on port {port}...")
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://localhost:{port}"
    for _ in range(60):
        if proc.poll() is not None:
            out = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(f"Flask app exited early (code {proc.returncode}):\n{out}")
        try:
            r = requests.get(f"{base}/api/health", timeout=2)
            if r.status_code == 200:
                log(f"App ready on port {port}")
                return proc
        except Exception:
            pass
        time.sleep(1)
    proc.kill()
    raise RuntimeError(f"App on port {port} did not become healthy")


def stop_app(proc):
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def load_scenario(base, scenario_path):
    """Load a scenario JSON via POST /api/load (ephemeral, no persist)."""
    with open(scenario_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    r = requests.post(f"{base}/api/load", json=data, timeout=60)
    r.raise_for_status()
    log(f"Loaded scenario: {scenario_path}")


CAPTURE_PROMPT_JS = """
(async (charName) => {
    try {
        const state = window.worldState && window.worldState.data;
        if (!state || !state.players) {
            return { error: 'worldState.data.players not available yet' };
        }
        const player = state.players[charName];
        if (!player) {
            const names = Object.keys(state.players).slice(0, 10).join(', ');
            return { error: 'Player not found: ' + charName + '. Known: ' + names };
        }
        const areaName = player.current_area;
        const area = areaName ? state.areas && state.areas[areaName] : null;
        if (!area) {
            return { error: 'Area not found: ' + areaName };
        }

        const roomParts = PromptBuilder.buildRoomContextParts(state, charName, player, area);
        const vitalsNL = PromptBuilder.describeVitals(player, state, charName);
        const emotionNL = PromptBuilder.buildEmotionContext(player);
        const relationshipNL = PromptBuilder.buildRelationshipContext(player, charName);
        const memoryNL = await PromptBuilder.buildMemoryContext(charName, { preview: true });

        const systemPrompt = PromptBuilder.buildCharacterSystemPrompt(charName, player, config.softMaxTokens);
        const userPrompt = PromptBuilder.buildReactionPrompt(
            player, roomParts, vitalsNL, emotionNL, relationshipNL, memoryNL, '', true, true
        );

        return {
            systemPrompt,
            userPrompt,
            charName,
            areaName,
            systemChars: systemPrompt.length,
            userChars: userPrompt.length,
        };
    } catch (e) {
        return { error: 'Exception in prompt capture: ' + String(e) };
        }
})
"""


def capture_prompt(base, char_name):
    """Use Playwright to capture the exact turn prompt from the live browser."""
    if sync_playwright is None:
        raise RuntimeError(
            "Playwright not installed. Run: pip install playwright && python -m playwright install chromium"
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{base}/", wait_until="domcontentloaded")

        # Wait for worldState to be populated by the frontend boot
        log("Waiting for world state to load in browser...")
        page.wait_for_function(
            "() => window.worldState && window.worldState.data && window.worldState.data.players",
            timeout=30000,
        )

        # Wait for PromptBuilder to be available
        page.wait_for_function(
            "() => window.PromptBuilder && typeof window.PromptBuilder.buildReactionPrompt === 'function'",
            timeout=10000,
        )

        # Capture the prompt via page.evaluate
        result = page.evaluate(CAPTURE_PROMPT_JS, char_name)
        browser.close()

    if isinstance(result, dict) and "error" in result:
        raise RuntimeError(result["error"])

    log(
        f"Captured prompt for {char_name} "
        f"(system: {result.get('systemChars', 0)} chars, user: {result.get('userChars', 0)} chars)"
    )
    return result


def discover_models(api_base):
    """Discover models from GET /v1/models (LM Studio / OpenAI-compatible)."""
    url = api_base.rstrip("/") + "/models"
    log(f"Discovering models from {url}...")
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()
    models = []
    for item in data.get("data", []):
        mid = item.get("id") or item.get("name") or ""
        if mid:
            models.append(mid)
    models.sort()
    return models


def parse_model_size(model_name):
    """Extract parameter count in billions from a model name.

    Returns None if the size can't be determined (e.g. embedding models).
    Handles patterns like: 9b, 4.5b, 0.8b, 8x3b (MoE: 8 experts x 3B = 24B).
    """
    name = model_name.lower()
    if "embedding" in name:
        return None
    # MoE: 8x3b => 8 * 3 = 24B
    moe = re.search(r'(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*b', name)
    if moe:
        return int(moe.group(1)) * float(moe.group(2))
    m = re.search(r'(\d+(?:\.\d+)?)\s*b', name)
    if m:
        return float(m.group(1))
    return None


def filter_models(models, size_limit):
    """Filter to models strictly below size_limit billion parameters."""
    result = []
    skipped = []
    for m in models:
        size = parse_model_size(m)
        if size is None:
            skipped.append((m, "unknown size"))
        elif size < size_limit:
            result.append(m)
        else:
            skipped.append((m, f"{size:g}B >= {size_limit}B limit"))
    for m, reason in skipped:
        log(f"  SKIP ({reason}): {m}")
    return result


def call_llm(api_base, model, system_prompt, user_prompt, temperature=0.7, max_tokens=DEFAULT_MAX_TOKENS):
    """Call /v1/chat/completions with streaming. Returns metrics + content."""
    url = api_base.rstrip("/") + "/chat/completions"
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    started = time.time()
    first_token = None
    chunks = []
    error = None

    try:
        resp = requests.post(url, json=body, stream=True, timeout=120)
        resp.raise_for_status()
        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8", "replace") if isinstance(raw_line, bytes) else raw_line
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if data_str == "[DONE]":
                break
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            delta = (data.get("choices") or [{}])[0].get("delta", {}) or {}
            content = delta.get("content", "") or ""
            if content:
                if first_token is None:
                    first_token = time.time()
                chunks.append(content)
    except Exception as e:
        error = str(e)

    total_time = time.time() - started
    ttft = (first_token - started) if first_token is not None else None
    full_content = "".join(chunks)

    # Token estimation (chars / 4)
    input_chars = len(system_prompt) + len(user_prompt)
    output_chars = len(full_content)
    input_tokens = input_chars / 4
    output_tokens = output_chars / 4
    tps = (output_tokens / total_time) if total_time > 0 else 0

    # JSON validity check (strip markdown fences first)
    json_valid = False
    json_error = None
    cleaned = full_content.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
        json_valid = isinstance(parsed, dict)
    except json.JSONDecodeError as e:
        json_error = str(e)

    return {
        "model": model,
        "content": full_content,
        "ttft": round(ttft, 3) if ttft is not None else None,
        "total_time": round(total_time, 3),
        "input_chars": input_chars,
        "output_chars": output_chars,
        "input_tokens_est": round(input_tokens, 1),
        "output_tokens_est": round(output_tokens, 1),
        "tps": round(tps, 2),
        "json_valid": json_valid,
        "json_error": json_error,
        "error": error,
    }


def hallucination_check(content, state, char_name):
    """Compare model output claims against /api/state ground truth.

    Checks action/target/item fields against the current area's exits, items,
    and people. Returns a list of flag dicts (empty = no flags).
    """
    flags = []
    cleaned = content.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return [{"type": "parse_error", "message": "Model output is not valid JSON"}]
    if not isinstance(parsed, dict):
        return [{"type": "not_object", "message": "Model output is not a JSON object"}]

    players = state.get("players", {}) or {}
    areas = state.get("areas", {}) or {}
    player = players.get(char_name, {}) or {}
    current_area = player.get("current_area", "")
    area = areas.get(current_area, {}) or {}

    area_items = area.get("items") or []
    area_people = area.get("people") or []
    area_exits = area.get("exits") or {}

    def _item_names(items):
        names = []
        for it in items or []:
            if isinstance(it, dict):
                names.append(str(it.get("name", it.get("id", ""))))
            else:
                names.append(str(it))
        return names

    def _exit_names(exits):
        names = []
        ids = []
        if isinstance(exits, dict):
            for k, v in exits.items():
                ids.append(k)
                names.append(str(v.get("name", k)) if isinstance(v, dict) else str(v))
        elif isinstance(exits, list):
            for e in exits:
                if isinstance(e, dict):
                    ids.append(str(e.get("id", "")))
                    names.append(str(e.get("name", "")))
        return ids, names

    exit_ids, exit_names = _exit_names(area_exits)
    item_names = _item_names(area_items)
    people_names = _item_names(area_people)
    inv_names = _item_names(player.get("inventory") or [])

    action = parsed.get("action")
    target = parsed.get("target")
    item = parsed.get("item")

    # Movement actions: target should be a known exit
    if action in ("go", "approach", "dash") and target:
        if target not in exit_ids and target not in exit_names:
            flags.append({
                "type": "invalid_exit",
                "field": "target",
                "claimed": target,
                "valid_exits": exit_names[:10],
                "message": f"Action '{action}' targets '{target}' which is not a known exit",
            })

    # Item field: item should exist in area or inventory
    if item:
        all_item_names = item_names + inv_names
        if item not in all_item_names:
            flags.append({
                "type": "nonexistent_item",
                "field": "item",
                "claimed": item,
                "available_items": all_item_names[:10],
                "message": f"Item '{item}' is not in the room or inventory",
            })

    # Target as a person (non-movement actions): should be present in the room
    if target and action not in ("go", "approach", "dash", "wait", None):
        if target not in people_names:
            flags.append({
                "type": "nonexistent_person",
                "field": "target",
                "claimed": target,
                "people_here": people_names[:10],
                "message": f"Target '{target}' is not present in the room",
            })

    return flags


def write_jsonl(run_id, provider, api_base, char_name, scenario, results, prompt_meta):
    """Write a JSONL run file."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_file = RUNS_DIR / f"{run_id}.jsonl"
    record = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "api_base": api_base,
        "character": char_name,
        "scenario": scenario,
        "prompt_meta": prompt_meta,
        "results": results,
    }
    with open(run_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    log(f"Wrote JSONL run: {run_file}")
    return run_file


def write_dashboard(run_id, results, provider):
    """Write an HTML dashboard comparing models across the run."""
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

    rows = ""
    for r in results:
        if r.get("error"):
            status = "❌ error"
            status_class = "bad"
        elif r.get("json_valid"):
            status = "✅ ok"
            status_class = "ok"
        else:
            status = "⚠️ invalid-json"
            status_class = "warn"

        ttft = f"{r['ttft']:.3f}s" if r.get("ttft") is not None else "n/a"
        total = f"{r['total_time']:.3f}s"
        tps = f"{r['tps']:.1f}" if r.get("tps") else "n/a"
        in_tok = r.get("input_tokens_est", 0)
        out_tok = r.get("output_tokens_est", 0)
        json_ok = "yes" if r.get("json_valid") else "no"
        error = html.escape(str(r.get("error") or ""))[:120]
        flags = r.get("hallucination_flags", []) or []
        flag_count = len(flags)
        flag_summary = "; ".join(f.get("message", "") for f in flags[:3])
        if len(flags) > 3:
            flag_summary += f" (+{len(flags) - 3} more)"
        content_preview = html.escape(r.get("content", "")[:200])

        rows += f"""
        <tr>
            <td>{html.escape(r['model'])}</td>
            <td class="{status_class}">{status}</td>
            <td>{ttft}</td>
            <td>{total}</td>
            <td>{tps}</td>
            <td>{in_tok}</td>
            <td>{out_tok}</td>
            <td>{json_ok}</td>
            <td>{flag_count}</td>
            <td>{html.escape(flag_summary)}</td>
            <td>{error}</td>
            <td>{content_preview}</td>
        </tr>"""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Model Bench — {provider}</title>
<style>
body {{ font-family: system-ui, -apple-system, sans-serif; margin: 2rem; }}
h1 {{ font-size: 1.5rem; }}
.meta {{ color: #666; margin-bottom: 1rem; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
th, td {{ border: 1px solid #ccc; padding: 0.5rem 0.75rem; text-align: left; font-size: 0.9rem; }}
th {{ background: #eee; position: sticky; top: 0; }}
tr:nth-child(even) {{ background: #f9f9f9; }}
.ok {{ color: #166534; font-weight: bold; }}
.bad {{ color: #b91c1c; font-weight: bold; }}
.warn {{ color: #92400e; font-weight: bold; }}
code {{ background: #f3f4f6; padding: 0 0.25rem; border-radius: 3px; }}
</style>
</head>
<body>
<h1>Model Bench — {html.escape(provider)}</h1>
<div class="meta">
<p><strong>Run:</strong> <code>{html.escape(run_id)}</code></p>
<p><strong>Generated:</strong> {datetime.now(timezone.utc).isoformat()}</p>
<p><strong>Models tested:</strong> {len(results)}</p>
</div>
<table>
<thead>
<tr>
<th>Model</th><th>Status</th><th>TTFT</th><th>Total</th><th>TPS</th><th>In Tokens</th><th>Out Tokens</th><th>Valid JSON</th><th>Hallucination Flags</th><th>Flag Details</th><th>Error</th><th>Content Preview</th>
</tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
<p><em>TTFT = time to first token. TPS = estimated tokens per second (chars/4). Token counts are estimates.</em></p>
</body>
</html>"""

    dash_file = DASHBOARD_DIR / f"{run_id}.html"
    with open(dash_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    log(f"Wrote dashboard: {dash_file}")
    return dash_file


def main():
    ap = argparse.ArgumentParser(
        description="Benchmark turn prompts across LLM provider models"
    )
    ap.add_argument("--scenario", help="Scenario name (data/scenarios/<name>.json) or path")
    ap.add_argument("--character", required=True, help="Character name to benchmark")
    ap.add_argument("--provider", default=DEFAULT_PROVIDER, help="Provider name (default: lmstudio)")
    ap.add_argument("--api-base", default=DEFAULT_API_BASE, help="Provider API base URL")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Scratch app port (default: {DEFAULT_PORT})")
    ap.add_argument("--size-limit", type=float, default=DEFAULT_SIZE_LIMIT, help=f"Max model size in billions (default: {DEFAULT_SIZE_LIMIT})")
    ap.add_argument("--max-models", type=int, default=0, help="Max models to benchmark (0 = all sub-limit)")
    ap.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature")
    ap.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS, help="Max output tokens per call")
    args = ap.parse_args()

    # Resolve scenario path
    scenario_path = None
    scenario_name = None
    if args.scenario:
        candidate = ROOT / "data" / "scenarios" / args.scenario
        if not candidate.exists():
            candidate = candidate.with_suffix(".json") if candidate.suffix != ".json" else candidate
        if not candidate.exists():
            candidate = Path(args.scenario)
        if not candidate.exists():
            log(f"ERROR: Scenario not found: {args.scenario}")
            sys.exit(1)
        scenario_path = candidate
        scenario_name = scenario_path.stem

    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    proc = None
    try:
        proc = start_app(args.port)
        base = f"http://localhost:{args.port}"

        # Load scenario if specified (before browser connects, so initial state fetch gets it)
        if scenario_path:
            load_scenario(base, scenario_path)

        # Capture the exact turn prompt via Playwright-driven browser
        prompt = capture_prompt(base, args.character)

        # Ground truth from /api/state
        log("Fetching ground truth from /api/state...")
        state = requests.get(f"{base}/api/state", timeout=60).json()

        # Discover models from the provider
        all_models = discover_models(args.api_base)
        log(f"Found {len(all_models)} models total from provider")
        models = filter_models(all_models, args.size_limit)
        log(f"Sub-{args.size_limit:g}B models to benchmark: {len(models)}")
        if not models:
            log("No models to benchmark (none under the size limit).")
            sys.exit(1)

        if args.max_models and len(models) > args.max_models:
            models = models[:args.max_models]
            log(f"Limited to {args.max_models} models")

        # Benchmark each model
        results = []
        for i, model in enumerate(models, 1):
            log(f"[{i}/{len(models)}] {model} ...")
            r = call_llm(
                args.api_base,
                model,
                prompt["systemPrompt"],
                prompt["userPrompt"],
                temperature=args.temperature,
                max_tokens=args.max_tokens,
            )
            if r.get("content") and not r.get("error"):
                r["hallucination_flags"] = hallucination_check(r["content"], state, args.character)
            else:
                r["hallucination_flags"] = []
            results.append(r)

            status = "❌" if r.get("error") else ("✅" if r.get("json_valid") else "⚠️")
            flags = len(r.get("hallucination_flags", []))
            ttft = r.get("ttft")
            ttft_str = f"{ttft:.3f}s" if ttft is not None else "n/a"
            log(
                f"  {status} ttft={ttft_str} total={r['total_time']:.3f}s "
                f"tps={r.get('tps')} json={r.get('json_valid')} flags={flags}"
            )

        # Write outputs
        write_jsonl(
            run_id,
            args.provider,
            args.api_base,
            args.character,
            scenario_name,
            results,
            {
                "system_chars": prompt.get("systemChars", 0),
                "user_chars": prompt.get("userChars", 0),
            },
        )
        write_dashboard(run_id, results, args.provider)

        ok = sum(1 for r in results if r.get("json_valid") and not r.get("error"))
        log(f"Done: {ok}/{len(models)} models returned valid JSON")
        log(f"JSONL: {RUNS_DIR / (run_id + '.jsonl')}")
        log(f"Dashboard: {DASHBOARD_DIR / (run_id + '.html')}")

    finally:
        stop_app(proc)


if __name__ == "__main__":
    main()
