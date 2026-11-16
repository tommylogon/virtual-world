---
type: task
status: todo
area: testing
priority: medium
wiki: "[[Developer Tooling]]"
related: [task-845, task-894, task-906, task-907]
---

# task-934: Benchmark output ratings, model metadata tagging (Free, Blocked, Do Not Use), and backend registry persistence

**Filed:** 2026-11-09
**Related:** task-845, task-894, task-906, task-907

<!-- deps:start -->
**Related:** [[task-845-llm-benchmark-harness-run-turn-prompt-across-models]], [[task-894-llm-benchmark-harness-capture-a-turn-prompt-for-one-character-run-across-selected-models-providers-score-speed-format-hallucinations-surface-a-run-dashboard]], [[task-906-retry-after-rate-limit-backoff-across-app-and-benchmark-reroll-history]], [[task-907-engine-action-validation-dry-run-and-benchmark-reasoning-effort-control]]
<!-- deps:end -->

## What

Extend the Benchmark Lab (`templates/benchmark.html`, `static/js/benchmark/benchmark.js`, `routes/benchmark.py`) with output evaluation ratings, persistent model status tagging (`Free`, `Blocked / Credit Limits`, `Do Not Use`), and a centralized backend model registry:

1. **Output Rating & Feedback System**:
   - Add an interactive rating control (1 to 5 stars or qualitative score) to each model result card in the Benchmark matrix.
   - Include an optional quick-feedback tag or note field (e.g. "Great dialogue", "Broken JSON format", "Hallucinated inventory", "Repetitive phrasing").
   - Persist ratings and review notes directly into the saved run record (`data/model_bench/runs/<run_id>.jsonl`) so user evaluations remain visible when inspecting past benchmark runs.
2. **Model Status & Reason Tagging**:
   - Allow authors and testers to tag models with operational flags:
     - **Free**: Model is free-tier or zero-cost (e.g. OpenRouter `:free` variants, local models), prioritizing them for high-volume sweeps and simulation testing.
     - **Blocked / Credit Limits**: Model provider returned HTTP 402/429 credit exhaustion, or user flagged it as out of budget.
     - **Do Not Use**: Model is unsuitable for turn generation due to a specific reason:
       - `realtime`: Live audio, speech, or bidirectional streaming model incompatible with standard chat completion.
       - `embeddings`: Vector embedding model mistakenly returned in provider model listings.
       - `audio_video`: Audio, video, or image generation endpoint.
       - `broken`: Frequent JSON syntax failure, repetitive loops, or chronic timeouts.
       - `vision_only`: Image input model without text generation capability.
       - `custom`: Custom note describing the issue.
3. **Backend Persistence (`data/model_bench/model_registry.json`)**:
   - Provide REST API endpoints in `routes/benchmark.py`:
     - `GET /api/bench/models/metadata`: Returns metadata dictionary keyed by model ID.
     - `POST /api/bench/models/metadata`: Updates status, free flag, tags, and do-not-use reasons for a model.
     - `POST /api/bench/runs/<run_id>/rate`: Attaches output score and feedback to a specific model entry in a run file.
4. **Cross-System Awareness & Filtering**:
   - In Benchmark Lab sidebar:
     - Color-coded badges beside models in the selection list (`[FREE]`, `[BLOCKED]`, `[DO NOT USE: <reason>]`).
     - Toggles to "Hide Blocked/Do Not Use" and "Show Only Free".
     - "Select All Filtered" automatically respects exclusions, skipping blocked and unsuitable models.
   - In ViWo simulation engine and AutoSwarm:
     - AutoSwarm and character LLM router read `data/model_bench/model_registry.json` (or `/api/bench/models/metadata`) to avoid routing turns to blocked or incompatible models, preventing simulation failures and wasted API calls.

## Why

Currently, benchmark sweeps discover dozens of models from providers (such as OpenRouter, Google, or local gateways), many of which are embedding models, realtime audio models, out of credits, or produce broken outputs. Without persistent status tagging, users have to remember and manually uncheck unusable models on every refresh. Furthermore, testers have no way to record qualitative evaluations of model responses within benchmark runs to track which models produce high-quality character dialogue. Storing this metadata centrally on the backend ensures both the Benchmark Lab and ViWo runtime agents retain model status across sessions.

## How

1. In `routes/benchmark.py`:
   - Define `REGISTRY_FILE = BENCH_DIR / "model_registry.json"`.
   - Implement `GET /api/bench/models/metadata` returning stored metadata mapping.
   - Implement `POST /api/bench/models/metadata` accepting `{ model_id, is_free, status, reason, notes }` and updating `model_registry.json` atomically.
   - Implement `POST /api/bench/runs/<run_id>/rate` accepting `{ model, rating, feedback }`, loading the target JSONL file, updating the matching result entry in place, and saving.
2. In `static/js/benchmark/benchmark.js` & `templates/benchmark.html`:
   - Fetch model metadata during `init()` via `/api/bench/models/metadata`.
   - In the model selection list, render status badges and filter controls:
     - Filter checkbox: "Hide Blocked / Do Not Use".
     - Filter checkbox: "Show Only Free".
   - On each model card in the comparison grid:
     - Add star rating buttons (1 to 5) and feedback input in the card footer.
     - Add a quick-tag dropdown button in the card header allowing the user to mark the model as Free, Blocked, or Do Not Use (with a prompt for the reason).
     - When a rating or status is changed, call the respective backend API endpoint and update local state immediately.
3. In `engine/llm_client.py` and `tools/autoswarm/llm.py`:
   - Check `data/model_bench/model_registry.json` if present; skip models where `status in ('blocked', 'do_not_use')` during automated fallback routing.

## Browser UI and intended live verification

Intended UI home: Standalone Benchmark Lab at `/bench` (sidebar model list, model comparison cards, and past run inspection modal).

Current availability: Benchmark Lab runs turn prompts across models and saves runs to `data/model_bench/runs/`. No output rating widget, model status tagging, or backend model registry exists today.

Live steps when available:
1. Navigate to `/bench` in the browser and load models from a provider (e.g. OpenRouter or local LM Studio).
   - expected: Model list loads in the sidebar with filter checkboxes ("Hide Blocked / Do Not Use", "Show Only Free").
2. Click the tag button on a model item in the sidebar (or on a result card) and set its status to "Do Not Use" with reason "embeddings".
   - expected: Model displays a distinct `[DO NOT USE: embeddings]` badge. Toggling "Hide Blocked / Do Not Use" hides it from the list.
3. Select a model, set status to "Free", and run a turn prompt benchmark.
   - expected: Result card renders with a `[FREE]` badge and an interactive 1-5 star rating control in the card footer.
4. Click 5 stars and enter feedback "Crisp dialogue and valid JSON", then refresh the page and open the run from Past Runs.
   - expected: Saved run displays the 5-star rating and feedback note.
5. Inspect `data/model_bench/model_registry.json` on disk.
   - expected: The file contains the updated metadata entries for the tagged models.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. In the browser UI at `/bench`, inspect the model selection sidebar and comparison cards.
   - expected: Shows model status badges, filter toggles, output rating controls, and model tagging dropdowns.
   - observed: Models only display checkboxes and names; no ratings or metadata tags exist.
2. Tag a model as Blocked or Do Not Use via the UI and verify persistence.
   - expected: Sends POST to `/api/bench/models/metadata` and writes to `data/model_bench/model_registry.json`.
   - observed: No metadata API or registry file exists.
3. Rate an output in a benchmark run and verify run file updates.
   - expected: Sends POST to `/api/bench/runs/<run_id>/rate` and updates the matching JSONL record.
   - observed: No rating endpoint or card rater exists.
4. Run python unit tests: `pytest tests/test_benchmark_routes.py`.
   - expected: All route tests pass.

## Acceptance

- [ ] Backend endpoints `GET /api/bench/models/metadata` and `POST /api/bench/models/metadata` manage persistent model metadata in `data/model_bench/model_registry.json`.
- [ ] Backend endpoint `POST /api/bench/runs/<run_id>/rate` persists output ratings and review notes to run records.
- [ ] Benchmark Lab sidebar renders status badges (`FREE`, `BLOCKED`, `DO NOT USE`) and filter controls to exclude unusable models.
- [ ] Benchmark comparison cards render interactive rating controls and quick status tagging affordances.
- [ ] Simulation LLM router and AutoSwarm respect blocked/do-not-use flags to prevent failed requests.
- [ ] Zero em-dashes anywhere in task cards, code, or documentation.

## Files

- `routes/benchmark.py`
- `templates/benchmark.html`
- `static/js/benchmark/benchmark.js`
- `engine/llm_client.py`
- `tools/autoswarm/llm.py`
