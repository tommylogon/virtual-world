---
type: task
status: done
area: ui
priority: normal
wiki: "[[LLM Inspector]]"
related: ["task-910", "task-911"]
---

# task-912: OpenRouter extended telemetry, cost, latency, and provider routing in LLM inspector

**Filed:** 2026-10-30
**Related:** task-910, task-911, task-405

## What

Capture and display extended metadata provided by OpenRouter's `/api/v1/chat/completions` and `/api/v1/responses` endpoints:

1. **Response Metadata Capture:**
   - Extract response headers and payload extensions from OpenRouter:
     - `x-openrouter-provider` (underlying backend host, e.g. Together, DeepInfra, Fireworks).
     - Upstream model resolution (actual deployed checkpoint).
     - Token counts: prompt tokens, completion tokens, reasoning tokens.
     - Generation cost in USD (`usage.total_cost` or derived rate).
     - Total request latency and upstream generation time.

2. **UI Presentation:**
   - Surface provider routing and cost badges in the LLM Inspector (`llm-raw-exchanges` viewer).
   - In the event stream raw LLM line summary, show provider origin and cost when available (e.g. `[Together | $0.0004 | 1.2s]`).

## Why

OpenRouter routes requests across diverse hardware providers with varying quantization, speed, and pricing. Currently, this telemetry is discarded by the client parser. Exposing it allows transparent tracking of costs, backend latency, and model quantization differences.

## How

- In `static/js/llm-client.ts`, store response headers and OpenRouter usage extensions in exchange records.
- In `static/js/inspector/raw-exchanges-view.ts` (or LLM inspector component), render the metadata card alongside prompt/completion diffs.
- Add regression test verifying header extraction does not fail on non-OpenRouter providers.
