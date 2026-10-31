---
type: task
status: done
area: ui
priority: normal
wiki: "[[Settings]]"
related: ["task-910", "task-909"]
---

# task-911: LM Studio native API, model selector, and response speed telemetry

**Filed:** 2026-10-30
**Related:** task-910, task-909, task-906

## What

Complete native LM Studio integration, upgrade the main settings model selector to match the benchmark interface, and surface inference speed:

1. **Native LM Studio Endpoint & Request Formatting:**
   - Ensure the API format toggle (`openai` vs `lmstudio`) in settings properly routes requests through LM Studio native endpoint specifications where applicable.
   - Support streaming completions with native token counting and stop reason handling.

2. **Benchmark-Grade Model Selector in Settings:**
   - Migrate the model selector UI from `static/js/benchmark/benchmark.js` into the main settings view (`static/js/ui/settings-view.ts`):
     - Filter chips by model parameter size (`all`, `fast 1-3B`, `7-14B`, `20B+`, `embed`).
     - Real-time text search filter input.
     - Sort dropdown (`name-asc`, `name-desc`, `tier`).
     - Badges indicating model weight and classification.

3. **Inference Speed Telemetry:**
   - Calculate tokens per second (t/s) and time-to-first-token (TTFT) for local completions.
   - Display the speed metric under the collapsible LLM response payload details in the event stream (e.g. `142 tokens @ 48.2 tok/s`).

## Why

Local LLM runtimes like LM Studio differ from standard hosted OpenAI endpoints in latency characteristics, reasoning token streaming, and parameter discovery. Providing tier filtering and live speed telemetry enables immediate verification of model performance and prevents silent slowdowns or misconfigurations.

## How

- In `static/js/llm-client.ts`, track request start time, first-token arrival timestamp, and token counter to compute tok/s.
- In `static/js/agent/turn-feed.ts` and `static/js/ui/event-feed.ts`, render the performance stats in the payload summary strip.
- In `static/js/ui/settings-view.ts`, port the search/filter/tier chip DOM and event listeners from `ui-controller.ts:renderModelList()` so the settings modal provides the full model list explorer.
