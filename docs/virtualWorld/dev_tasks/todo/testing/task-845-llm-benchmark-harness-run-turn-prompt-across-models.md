---
type: task
status: todo
area: testing
priority: medium
wiki: "[[AI & Narration/Agent Engine]]"
---

# task-845: LLM benchmark harness: run a single character's turn prompt across all models of a selected provider (primarily LM Studio), with metrics + hallucination detection + dashboard

**Filed:** 2026-10-15

## What

A Python tool `tools/model_bench.py` that, for one scenario and one controlled character, captures the exact turn prompt the frontend assembles (never a reimplementation), then sends it to every model exposed by a selected provider (default LM Studio via `GET /v1/models` + OpenAI-compatible `/v1/chat/completions`), measures TTFT/TPS/total time/context usage, validates JSON output format, runs a hallucination check against room ground truth (items, people, exits, actions), and writes JSONL runs plus an HTML dashboard under `data/model_bench/`.

## Acceptance

- [ ] `python tools/model_bench.py --scenario <name> --character <id> --provider lmstudio` runs from the repo root and exits 0 when the provider is reachable.
- [ ] The prompt sent is the exact assembled turn prompt from `static/js/agent/prompt-builder/turn-prompts.ts` (`buildReactionPrompt` / `assembleMessageHead`), captured via a driven browser or an exported snapshot — never reimplemented in Python.
- [ ] Models are enumerated from `GET /v1/models` (LM Studio) and each model receives the same prompt once.
- [ ] Metrics recorded per model: time-to-first-token, tokens-per-second, total latency, input/output token counts, context-window usage, JSON validity of the model's reply.
- [ ] Hallucination check: model output claims about the room (items present, people present, exits, available actions) are compared against `/api/state` ground truth for that character's cell; mismatches flagged in the run record.
- [ ] Outputs: one JSONL run file per provider run under `data/model_bench/runs/`, plus an HTML dashboard under `data/model_bench/dashboard/` comparing models across runs.
- [ ] Fails fast with a clear message when the provider is unreachable; does not mutate world state or consume a turn slot.

## Why

Turn-prompt quality drives NPC behavior, but there is no way to compare how different models render the same prompt. The frontend prompt builder is the source of truth; benchmarking against it requires the exact assembled prompt, not a Python approximation.

## How

1. Decide the capture path: driven browser (Playwright, reusing task-693 patterns) to read the assembled prompt from the turn card / composer, or a lightweight server-side export snapshot. Do not duplicate `turn-prompts.ts` logic in Python.
2. Implement `tools/model_bench.py` with: provider discovery (`GET /v1/models`), per-model `POST /v1/chat/completions` streaming reads, metric collection, JSON-format validation, hallucination diff vs `/api/state`, JSONL + HTML dashboard writers.
3. Author one minimal fixture scenario/character if none exists that exercises a full turn prompt with room contents, exits, and available actions.
4. Run against a local LM Studio instance (or stubbed provider for CI) and confirm the dashboard renders per-model metrics and hallucination flags.

## Steps to verify

1. `python tools/model_bench.py --scenario <fixture> --character <id> --provider lmstudio` with LM Studio running.
   - expected: enumerates models from `GET /v1/models`, sends the exact turn prompt to each, writes JSONL + dashboard, exits 0.
2. With LM Studio stopped, same command exits non-zero with a clear "provider unreachable" message.
3. Inspect `data/model_bench/dashboard/index.html`: one row per model, TTFT/TPS/total-latency columns, hallucination-flag column.
4. Confirm `/api/state` and world state are unchanged after a run (no turn committed, no autosave mutation).

## Files

- `tools/model_bench.py` — new benchmark harness (to be created)
- `static/js/agent/prompt-builder/turn-prompts.ts` — source of truth for prompt assembly (read-only reference)
- `data/model_bench/runs/*.jsonl` — run records (generated)
- `data/model_bench/dashboard/*.html` — comparison dashboard (generated)

## Browser UI and intended live verification

No new UI surfaces. Verification is CLI-driven against a running app instance; the prompt capture may use a Playwright-driven browser tab (task-693 pattern) reading the turn composer's assembled message, never mutating state.

This section is not a claim that the harness is implemented today.
