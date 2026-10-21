---
type: task
status: inprogress
area: testing
priority: high
wiki: "[[Developer Tooling]]"
---

# task-894: LLM benchmark page: capture a turn prompt for one character, run across selected models/providers, score speed/format/hallucinations, surface a run dashboard

**Filed:** 2026-10-16
**Related:**

## What

An in-app dev page (no Python script, no second source of truth) that, for a single selected character, builds the exact turn prompt the simulation would send — system prompt + room context + vitals + emotion + memory + reaction prompt — using the existing `PromptBuilder`, then sends it to every model the user selects via the existing `LLMClient` (`VW.llm`, same OpenAI-compatible path the sim uses, LM Studio default `http://localhost:1234/v1`). Each run is scored in the UI: time-to-first-token, tokens-per-second, total latency, input/output token counts, context-window fit, whether the output matches the engine's expected JSON format, and whether the model hallucinated items, locations, or actions not present in `worldState.data`. Runs are stored client-side and surfaced in an in-app dashboard with per-run drill-in, cross-model comparison, and graphs (TTFT/TPS/latency).

The frontend-vs-script question is resolved: this builds as a frontend page reusing `PromptBuilder` + `LLMClient` + in-memory `worldState.data`, so prompt equivalence is by construction and there is no Python port to drift.

## Why

The simulation sends rich, stateful prompts to the LLM every turn, but there is no repeatable way to see how different models handle the same prompt, or whether a model's output conforms to the format the engine expects, or whether it invents items, rooms, or actions that don't exist in the world state. Benchmarking models against a real turn prompt is the only way to pick a good model for LM Studio (or any OpenAI-compatible provider) and to know when an upgrade regresses format compliance or raises the hallucination rate.

A Python port was considered and rejected: it duplicates `PromptBuilder` and `LLMClient`, requires a drift check against the browser's actual output, and adds a second source of truth. The frontend already has all three pieces wired, so the page reuses them directly.

## How

1. **Module:** New `static/js/llm-bench.ts` (+ emitted `.js`), registered as a `<script>` tag in `templates/index.html` after `llm-client.js` and the `prompt-builder/` scripts so `window.PromptBuilder` and `VW.llm` are available.
2. **UI surface:** model select (enumerate via `GET /v1/models` on the configured base, plus the configured default model), character select (from `worldState.data.players`), run button, per-run results table, per-run drill-in (prompt / output / metrics / hallucination flags), cross-model comparison view, graphs (TTFT/TPS/latency bars), JSON export. Placement (settings button / header button / inspector tab) is a decision captured here, not a second build.
3. **Prompt capture (frontend, no port):** Call `PromptBuilder.buildCharacterSystemPrompt(charName, player, softMaxTokens)` for the system message and `PromptBuilder.buildRoomContextParts` + `buildReactionPrompt` / `assembleMessageHead` for the user message — the exact same calls `agent-engine.ts` makes each turn. Read character + room state from `worldState.data` (in memory); `GET /api/state` is the read-only fallback.
4. **Provider:** Reuse `VW.llm.chat([{role:'system', content}, {role:'user', content}], {model, streaming: true, onChunk})`. `LLMClient` handles base URL, API key, retries, streaming, JSON repair. Run each selected model against the same captured prompt.
5. **Metrics per run:** TTFT (time of first `onChunk`), TPS (output tokens / elapsed), total latency, input/output token counts, context-window utilization (input tokens vs model context), per-chunk stream timings.
6. **Format validation:** Parse the generated output as JSON; check required fields, allowed keys, no duplicate/repeated keys against the engine's expected assistant message shape (`inner_monologue`, `action`, `item`, `target`, `speech`, `volume`, `emote`, ...). Report pass/fail per model.
7. **Hallucination detection:** Diff item, location, and action names referenced in the output against `worldState.data` (graph nodes, player inventory, exits, area entities) for the same character/room. Flag anything referenced that does not exist in state.
8. **Storage:** Runs stored client-side via the existing `storage` module (`static/js/storage.js`), keyed per run with prompt, model, metrics, format result, hallucination flags, and raw output. JSON export for portability. No new backend route.
9. **Dashboard:** In-app page listing all runs, sortable by model/metric, with per-run drill-in and a compare view across models for the same prompt. Graphs drawn with canvas/CSS (no new charting library unless one is already vendored).

## Steps to verify

1. Start the app (`python app.py`, port 4444) with a scenario loaded and an LM Studio instance reachable at the configured base URL.
2. Open the benchmark page from its entry point (settings/header button).
   - expected: model list populated from `GET /v1/models`, character list from `worldState.data.players`.
   - observed: TODO
3. Select one character and one or more models, run.
   - expected: each model streams the same captured prompt; TTFT/TPS/latency recorded; JSONL-style run stored client-side.
   - observed: TODO
4. Open the dashboard; confirm runs list with model, TTFT, TPS, format pass/fail, hallucination count; per-run drill-in shows prompt, output, metrics, flags.
   - observed: TODO
5. Verify hallucination detection: run against a model known to invent items; confirm flagged items do not exist in `worldState.data`.
   - expected: hallucination report names specific fake entities.
   - observed: TODO
6. Verify prompt equivalence: the captured prompt is built by the same `PromptBuilder` calls the turn uses (no port to diff).
   - expected: prompt is identical to what `agent-engine.ts` sends for the same turn.
   - observed: TODO

## Acceptance

- [ ] `static/js/llm-bench.ts` compiles (`npm run build:ts`) and the page opens in the running app.
- [ ] Model list from `GET /v1/models`; character list from `worldState.data.players`.
- [ ] Running one character across multiple models streams each and records TTFT, TPS, total latency, token counts per model per run.
- [ ] Format validation reports pass/fail against the engine's expected JSON output structure.
- [ ] Hallucination detection flags items/locations/actions absent from `worldState.data`.
- [ ] Runs stored client-side; dashboard lists all runs with per-run drill-in and cross-model compare.
- [ ] Graphs (TTFT/TPS/latency) render on the dashboard.
- [ ] No Python benchmark script; no `tools/model_bench.py`; no `data/model_bench/` duplication.
- [ ] Frontend-vs-script decision recorded as resolved (frontend page).

## Files

- `static/js/llm-bench.ts` (new) — frontend benchmark page: prompt capture via PromptBuilder, LLMClient calls, metrics, format check, hallucination diff, client-side run storage, dashboard UI + graphs.
- `templates/index.html` (edit) — `<script src="/static/js/llm-bench.js">` tag after `llm-client.js` and prompt-builder.
- `static/js/llm-bench.js` (emitted by `npm run build:ts`).
- `static/js/agent/prompt-builder/*.ts` + `static/js/llm-client.ts` — reference/reuse only; no changes.
- `static/js/storage.js` — client-side run storage (reuse, no change).
- `worldState.data.players` / `GET /api/state` — read-only source of character/room state (no new route).
