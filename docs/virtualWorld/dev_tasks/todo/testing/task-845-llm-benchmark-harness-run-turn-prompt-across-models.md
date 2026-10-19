---
type: task
status: todo
area: testing
priority: medium
wiki: "[[AI & Narration/Agent Engine]]"
---

# task-845: Frontend LLM benchmark page: run a character's turn prompt across selectable providers and models with metrics, hallucination checks, and side-by-side comparison

**Filed:** 2026-10-15  
**Updated:** 2026-10-19 (re-scoped from headless CLI to dedicated frontend tool page)

## What

A dedicated in-app benchmarking page (e.g. `/bench` or `/tools/benchmark`) that takes a character's live turn prompt, lets the author select any reachable provider and check off specific models, runs the identical prompt across all selected models, and displays live streaming cards, latency/throughput metrics, schema validity, fuzzy hallucination checks against ground truth, and side-by-side prose comparison.

## Acceptance

- [ ] Dedicated UI page accessible via route (e.g. `/bench`) with a clean link/button from the main editor navigation.
- [ ] Provider selector supporting configurable endpoints (LM Studio, Ollama, OpenRouter, custom OpenAI-compatible API base).
- [ ] Dynamic model multiselect: fetches available models via `GET /v1/models` (or provider equivalent) and lets the user select/unselect any combination.
- [ ] Turn prompt capture: loads or pulls the exact prompt assembled by `static/js/agent/prompt-builder/turn-prompts.ts` for the selected scenario character (same context as play mode).
- [ ] Safe execution: benchmark runs do not mutate world state, advance turns, or dirty persisted saves.
- [ ] Cancellation: an active benchmark sweep or single model run can be stopped immediately via a Cancel button (reusing standard `AbortController` / `agent.cancel()` patterns).
- [ ] Output verification:
  - Valid output check: validates JSON structure, action schema, and required turn fields.
  - Fuzzy hallucination detection: matches declared items, targets, people, and exits against room ground truth from `/api/state`. Valid entities pass (fuzzy matching allowed); invalid entities/exits/actions receive clear red flags.
  - Prose inspection: displays internal monologue, reasoning, and roleplay dialogue side-by-side for human qualitative review.
- [ ] Metrics reported per model: TTFT (time-to-first-token), TPS (tokens-per-second), total latency, token count, JSON status.

## Why

Prompt quality and model behavior cannot be effectively tuned through headless scripts and static terminal logs. Authors need a dedicated visual tool to evaluate prose style, check spatial compliance, and compare multiple models side-by-side on the exact prompt their characters see in live play.

## How

1. Route & View: Add a dedicated template (`templates/benchmark.html`) and route (`routes/tools.py` or `routes/benchmark.py`), linked from the app menu.
2. Client Logic: Create `static/js/benchmark/` to handle provider discovery, model checklist selection, queueing calls, and rendering live streaming responses.
3. Proxy Endpoint: Provide a lightweight backend proxy (`/api/bench/proxy` or `/api/bench/models`) to avoid browser CORS issues when reaching local/remote provider endpoints.
4. Prompt Bridge: Reuse client-side `PromptBuilder` directly on the loaded scenario state to extract the real turn prompt for any selected character.
5. Hallucination Evaluator: Implement fuzzy entity matching against the active area nodes (items, occupants, exits) and flag unrecognized claims.
6. Result Matrix: Render interactive comparison cards with metrics badges, schema pass/fail indicators, and full expandable prompt/reply logs.

## Steps to verify

1. Navigate to the benchmark page in the browser.
2. Select a scenario and character; confirm the previewed prompt matches the character's live turn prompt.
3. Pick a provider (e.g. LM Studio); confirm the model list populates from `GET /v1/models`.
4. Select 2 or more models and click Run.
5. Verify tokens stream into their respective panels and latency/TPS metrics update live.
6. Verify Cancel immediately halts pending and in-flight requests.
7. Verify fuzzy matching correctly tags valid room items/exits green and flags non-existent ones with red badges.
8. Verify scenario state on `/api/state` remains untouched after runs.

## Files

- `templates/benchmark.html` - Dedicated benchmark interface
- `static/js/benchmark/` - Frontend controller, provider client, and comparison view
- `routes/benchmark.py` - Route definition, model discovery proxy, and runner endpoints
- `static/js/agent/prompt-builder/turn-prompts.ts` - Shared prompt assembly source of truth
- `tools/model_bench.py` - Legacy/headless CLI script (retained for headless test suites)
