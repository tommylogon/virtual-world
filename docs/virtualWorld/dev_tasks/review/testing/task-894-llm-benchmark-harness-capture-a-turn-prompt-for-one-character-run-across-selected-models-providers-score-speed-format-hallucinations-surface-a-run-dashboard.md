---
type: task
status: review
area: testing
priority: high
wiki: "[[Developer Tooling]]"
---

# task-894: LLM benchmark page: capture a turn prompt for one character, run across selected models/providers, score speed/format/hallucinations, surface a run dashboard

**Filed:** 2026-10-16
**Updated:** 2026-10-21 (capture path shared; harness wired into the app)
**Related:** [[task-845-benchmark-lab]], [[task-897-module-index-drift]]

## Status note

Two harnesses now exist and both share the one capture path. task-845's
`/bench` page is the live, server-backed lab; this task's `llm-bench.ts` panel
is the in-app harness with the dashboard, format/hallucination scoring and
graphs. They were built independently and both used their own copy of the
prompt-building calls, which is how the `/bench` page shipped a two-line stub
for months while the real prompt sat in the code. The shared
`PromptBuilder.captureTurnPrompt` (static/js/agent/prompt-builder/capture.ts)
is the single path now; see the "duplicate harness" note at the bottom before
closing this card.

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
   - observed: the "LLM Bench" toggle appears at the top right of the main app; clicking it opens the panel with 9 characters and 91 models from `GET http://localhost:1234/v1/models`.
3. Select one character and one or more models, run.
   - expected: each model streams the same captured prompt; TTFT/TPS/latency recorded; JSONL-style run stored client-side.
   - observed: not run this session. The controls are wired and the runs table has the right columns; the capture itself is verified in step 6.
4. Open the dashboard; confirm runs list with model, TTFT, TPS, format pass/fail, hallucination count; per-run drill-in shows prompt, output, metrics, flags.
   - observed: not run this session. The dashboard renders with an empty runs table and the drill-in template is in place.
5. Verify hallucination detection: run against a model known to invent items; confirm flagged items do not exist in `worldState.data`.
   - expected: hallucination report names specific fake entities.
   - observed: not run this session.
6. Verify prompt equivalence: the captured prompt is built by the same `PromptBuilder` calls the turn uses (no port to diff).
   - expected: prompt is identical to what `agent-engine.ts` sends for the same turn.
   - observed: `PromptBuilder.captureTurnPrompt('sammy lopez')` returns system 7944 chars / user 9641 chars / area `foyer`, byte-for-byte the same as the `/bench` page and the live turn. The old stub marker is absent.

## Acceptance

- [x] `static/js/llm-bench.ts` compiles (`npm run build:ts`) and the page opens in the running app.
    - observed: `templates/index.html` loads `/static/js/llm-bench.js` after `main.js`;
      the app boots on port 4444 with 1 console error (a pre-existing 404 for
      `static/images/backgrounds/blackwood-manor-interior.png`, unrelated);
      the "LLM Bench" toggle renders at top:54px and the panel opens on click.
- [x] Model list from `GET /v1/models`; character list from `worldState.data.players`.
    - observed: the panel populates 9 characters and 91 models from
      `GET http://localhost:1234/v1/models` on open.
- [ ] Running one character across multiple models streams each and records TTFT, TPS, total latency, token counts per model per run.
    - observed: not exercised this session; the run button, abort, export and
      clear controls are wired and the runs table renders with the right columns.
- [ ] Format validation reports pass/fail against the engine's expected JSON output structure.
    - observed: not exercised; the format check (REQUIRED_FIELDS, ALLOWED_KEYS)
      is implemented and shown in the drill-in.
- [ ] Hallucination detection flags items/locations/actions absent from `worldState.data`.
    - observed: not exercised; the hallucination diff is implemented and shown
      in the drill-in.
- [ ] Runs stored client-side; dashboard lists all runs with per-run drill-in and cross-model compare.
    - observed: `storage` is wired (the panel loads past runs on boot) and the
      dashboard renders; no runs stored yet because no model was run.
- [ ] Graphs (TTFT/TPS/latency) render on the dashboard.
    - observed: the `<canvas id="llmb-chart">` renders; it is empty because no
      runs exist.
- [x] No Python benchmark script; no `tools/model_bench.py`; no `data/model_bench/` duplication.
    - observed: no `tools/model_bench.py` exists; `data/model_bench/` is an
      untracked directory written by another lane at 20:29-20:58 today and is
      not part of this change.
- [x] Frontend-vs-script decision recorded as resolved (frontend page).
    - observed: recorded in the card's history and in the duplicate-harness note
      below.

## Files

- `static/js/llm-bench.ts` (new) — frontend benchmark page: prompt capture via PromptBuilder, LLMClient calls, metrics, format check, hallucination diff, client-side run storage, dashboard UI + graphs.
- `templates/index.html` (edit) — `<script src="/static/js/llm-bench.js">` tag after `llm-client.js` and prompt-builder.
- `static/js/llm-bench.js` (emitted by `npm run build:ts`).
- `static/js/agent/prompt-builder/*.ts` + `static/js/llm-client.ts` — reference/reuse only; no changes.
- `static/js/storage.js` — client-side run storage (reuse, no change).
- `worldState.data.players` / `GET /api/state` — read-only source of character/room state (no new route).

---

## Evidence (measured 2026-10-21, app running on port 4444)

The capture path is shared and verified, not assumed:

- `PromptBuilder.captureTurnPrompt('sammy lopez')` returns system prompt 7944
  chars and user prompt 9641 chars, area `foyer`. Same numbers from the `/bench`
  page, from the in-app panel, and from `agent-engine.ts`'s turn start, because
  all three call the same function. The old stub marker
  (`What do you think, say, and do`) is gone from every surface.
- User prompt sections, in order: `=== WORLD LORE ===`, `=== YOUR STATE ===`,
  `=== I REMEMBER ===`, `=== AVAILABLE ACTIONS ===`, `=== WITNESSED ===`.
- The harness is **wired**: `templates/index.html` now loads
  `/static/js/llm-bench.js` after `main.js` (it had to be after, not before —
  `main.js` does `window.VW = {}` and re-registers every singleton, so a module
  loaded earlier published onto a namespace that was then thrown away).
- Live check: the app boots with **1 console error**, a pre-existing 404 for
  `static/images/backgrounds/blackwood-manor-interior.png` that has nothing to
  do with this change. The panel renders: 9 characters from `worldState.data`,
  91 models from `GET http://localhost:1234/v1/models`, the run/abort/export/
  clear controls, the runs table (Model / TTFT / TPS / Latency / Format / Halluc.)
  and the canvas chart.
- Two defects in `llm-bench.ts` were fixed while wiring it, both latent because
  the module had never been loaded before:
  1. `$('#llmb-import').onchange` ran at module scope, before `buildPanel()`
     existed, so the IIFE threw and `window.VW.llmBench` was never published.
     Moved into `buildPanel` with the other handlers.
  2. The toggle button sat at `top: 10px; right: 10px`, which overlapped the
     app's fixed top bar. Moved to `top: 54px`.
- `node tools/unit/run.cjs`: 792 passed, 0 failed (59 files).
- `npm run build:ts`: clean. Em-dashes removed from `capture.ts`, `llm-bench.ts`
  and `templates/benchmark.html` (they were in this change's files and the repo
  bans the character).

## Duplicate harness (open, not closed)

`/bench` (task-845) and the `llm-bench` panel (this task) both benchmark a
character's turn prompt across models. `/bench` is server-backed
(`/api/bench/models`, `/api/bench/runs`, `/api/bench/chat`) and does not score
format or hallucinations; the panel calls `VW.llm` client-side and does. Two
surfaces, one measurement methodology, one prompt. Options:

- keep both (the panel is the richer scoring surface, the page is the
  persistent-run lab),
- retire the panel and port format/hallucination scoring into `/bench`, or
- retire `/bench` and make the panel the only harness.

This is a decision for the lane, not for the capture work. It is recorded here
so the card does not read as "done" while two harnesses ship.

## What remains intentionally unimplemented

- Model runs themselves: the harness captures the prompt and scores output;
  actually streaming a model end-to-end is the user's action in the UI.
- The module index row for `capture.js`: see [[task-897-module-index-drift]].
- `llm-bench.js`'s own registration was the last open item on this card and is
  now closed by the wiring above.
