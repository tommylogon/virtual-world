---
type: task
status: done
area: ui
priority: high
wiki: "[[UI & Settings/Settings & Configuration]]"
related: [task-934, task-941]
---

# task-945: Settings modal: full-viewport responsive canvas, SVG iconography, unified Model Hub with dynamic reasoning and uncapped token budget

**Filed:** 2026-11-12
**Completed:** 2026-11-12
**Related:** task-934, task-941

<!-- deps:start -->
**Related:** [[task-934-benchmark-output-ratings-and-model-metadata-tagging]], [[task-941-settings-modal-overhaul-layout-model-capabilities-and-cleanup]]
<!-- deps:end -->

## What

Comprehensive transformation of the Settings modal into a full-viewport, responsive command center (`templates/index.html`, `static/css/style.css`, `static/js/ui-controller.ts`, `static/js/ui/settings-view.ts`, and `routes/benchmark.py`):
1. **Full-Viewport Responsive Canvas:** Eliminate the 38% dead backdrop moat on widescreen displays. Expand the modal to fluid viewport sizing (`width: min(calc(100vw - 32px), 1640px); height: calc(100vh - 32px);`), adapting seamlessly across 16:9 widescreen (e.g. 4K at 250% zoom = 1536x864 logical viewport), 12:9 (4:3) square-ish displays, and zoomed viewports (e.g. 80% browser zoom).
2. **SVG Iconography:** Retire OS emojis and mojibake HTML entities across modal tabs, group headers, and status chips in favor of crisp monochrome vector SVGs from the repository's 4,180 icons in `static/icons/ffffff/`.
3. **Unified Model Hub on Tab 1 (End the Tab-Hopping Fracture):** Consolidate all model-specific inspection and configuration into the dominant right-hand canvas of Tab 1.
4. **Active Model Inspector & Dynamic Tuning Card:**
   - **Uncap Output Tokens (Hard & Soft Limits):** Eliminate the 2023-era hardcoded `max="32768"` constraint in HTML. Display both **Hard Max Tokens** (API ceiling) and **Soft Max Tokens** (system prompt instruction constraint) side-by-side. Dynamically set ceiling and presets up to the model's true `max_output_tokens` (e.g. 921,600 for Baidu ERNIE, 131,072 for Nemotron) with quick presets (`Auto: 4K`, `Balanced: 8K`, `Full Model Max`).
   - **Complete Reasoning Controls:**
     * Auto-detect whether reasoning is `mandatory` or optional.
     * Full effort levels spectrum from `none` to `max` (`none`, `minimal`, `low`, `medium`, `high`, `max`). The dropdown dynamically highlights and filters by the active model's `supported_efforts`.
     * Preserve and cleanly expose the "Suppress Local Reasoning (LM Studio)" bypass toggle (for zero token waste on models that reason natively).
   - **Sampling Parameters with Compatibility Warnings:**
     * Expose both **Temperature** (0.0 to 2.0) and **Top-P** (0.0 to 1.0).
     * Inspect the model's `supported_parameters`. If a parameter (e.g. `temperature` or `top_p`) is not supported by the model (common in strict reasoning models), clearly dim/disable the input and display a visible warning badge: `[⚠️ Not supported]`.
   - **Extensible Parameter Registry:** Define a clean, declarative registry in both `routes/benchmark.py` and `ui-controller.ts` so future parameters (`min_p`, `top_k`, `frequency_penalty`, `presence_penalty`, `seed`) can be registered and surfaced with zero architectural refactoring.
   - **Capabilities & Schema Protocol Matrix:** Explicitly display and respect `tools` (function calling) and `structured_outputs` (native JSON schema support) based on `supported_parameters`.
   - **Pricing & Vendor Intelligence:** Display official provider description, prompt/completion pricing per 1M tokens (`Free` badge or `$X.XX / $Y.YY`), and Artificial Analysis benchmark intelligence scores.
5. **DOM ID Alignment & Dual-Layer Persistence (Backend Sync):**
   - Permanently resolve the `thinking-options` vs `thinking-effort-row` ID mismatch so programmatic configuration loading in `SettingsView.populateForm()` cleanly un-hides options on initial render.
   - Ensure the modal's primary "Save" button automatically syncs the active profile directly to the backend (`ApiClient.saveProfile`) alongside IndexedDB, maintaining 100% server-client lockstep.
6. **Clean MVC Separation:** Cleanly delineate the Model layer (`routes/benchmark.py`), View layer (`templates/index.html` & `style.css`), and Controller layer (`ui-controller.ts` & `settings-view.ts`).

---

## Why

1. **Wasted Screen Real Estate:** A user on a 55-inch 4K TV or high-res monitor has ~38% of their screen drowned in a black backdrop while dense lists and options fight for space in a cramped modal. Settings is a modal overlay where nothing behind it needs to be seen; it should fully utilize the available viewport.
2. **Fractured User Journey:** Selecting a model happens in Tab 1, but tuning its output tokens, reasoning effort, and temperature requires navigating to Tab 2. When users switch models, they have no visibility into whether the active model requires reasoning or supports large output buffers.
3. **The 32,768 Token Trap:** Modern frontier models output between 65K and 921K tokens. A hardcoded `<input max="32768">` silently prevents users from utilizing the full context generation capabilities of models they selected.
4. **Reasoning Runtime Failures:** Sending unsupported reasoning efforts (e.g. `low` to a model that only accepts `high`, or omitting reasoning for a model where `mandatory: true`) results in HTTP 400 Bad Request errors. Reasoning controls must be driven dynamically by model metadata.
5. **Vector Assets Left Idle:** The repo contains 4,180 vector icons in `static/icons/ffffff/`, yet the UI was using inconsistent emoji glyphs that render with unpredictable colors and sizing across different operating systems.

---

## Acceptance Criteria

- [x] **Canvas Sizing:** `#settings-modal .modal-content` expands to `width: min(calc(100vw - 32px), 1640px); height: calc(100vh - 32px);`. No horizontal scrollbars on 12:9 or 16:9 displays; vertical body flexes smoothly with fixed header and footer.
- [x] **SVG Integration:** Modal navigation tabs (`Connection`, `Engine Defaults`, `Behavior & Automation`, `Graph`, `Engine Config`) and status badges utilize crisp vector SVGs from `static/icons/ffffff/`.
- [x] **Tab 1 Architecture:**
  - Left rail (~380px to 420px): Stacks Primary API Connection, Dedicated Memory Worker (Task-909), Semantic Memory Embeddings, and Dedicated Action Interpreter (Task-943).
  - Right canvas (`1fr`): Dominant Model Hub containing Search, Sort, Filter Chips, the Model Browser, and the Active Model Inspector.
- [x] **Model Browser Density:** `#model-list` displays models comfortably with fluid height without badge wrapping.
- [x] **Token Budget Uncapped:** `#max-tokens-input` and `#hub-max-tokens` support modern token scales (>32K up to 1,048,576 tokens). Includes quick presets: `[4K Output]`, `[8K Output]`, and `[Full Max: X]`.
- [x] **Dynamic Reasoning Controls:**
  - When a model with `reasoning.mandatory === true` is selected, the reasoning toggle is locked active with a "Mandatory" indicator.
  - The reasoning effort dropdown is dynamically populated with only the model's `supported_efforts` (or full spectrum `none` to `max`).
  - Bypass Local Reasoning (LM Studio) / Qwen bypass toggle is prominent and functional.
- [x] **Capabilities & Cost Display:** The Active Model Inspector card renders:
  - Official provider description.
  - Pricing badge (`Free Tier` or exact prompt/completion rates).
  - Capability badges: `[✓ Tools]`, `[✓ Structured JSON]`, `[✓ Vision]`.
  - Upstream benchmark score (e.g. Artificial Analysis index) when available.
- [x] **Sampling with Compatibility Warnings:**
  - Temperature (0.0 to 2.0) and Top-P (0.0 to 1.0) with dynamic warning badges `⚠️ Not supported` and `.param-unsupported` when not supported.
- [x] **DOM ID Alignment:** `SettingsView.populateForm()` correctly addresses `#thinking-options`, ensuring that pre-saved `config.thinking === true` renders reasoning effort immediately without requiring manual checkbox toggling.
- [x] **Zero Em-Dashes:** Strictly 0 em-dash characters (Unicode U+2014) in code, templates, and documentation.
- [x] **Clean TypeScript Compilation & Tests:** `npm run build:ts` exits with 0 errors; all route tests pass cleanly (15/15).

---

## Architecture & Data Flow

```
+-----------------------------------------------------------------------------------+
| MODEL LAYER (routes/benchmark.py)                                                 |
| - Normalizes provider descriptors (OpenRouter, Gemini, Groq, LM Studio):          |
|   id, name, description, context_length, max_output_tokens                         |
|   pricing: { is_free, prompt, completion }                                        |
|   capabilities: { tools, structured_outputs, vision }                             |
|   reasoning: { mandatory, supported_efforts, default_effort }                     |
|   benchmarks: { artificial_analysis: ... }                                        |
+-----------------------------------------------------------------------------------+
                                          |
                                          v  GET /api/models
+-----------------------------------------------------------------------------------+
| CONTROLLER LAYER (static/js/ui-controller.ts & settings-view.ts)                  |
| - Manages active model selection, uncaps maxTokens based on model capacity        |
| - Populates dynamic reasoning effort dropdown from model.supported_efforts        |
| - Synchronizes token budget quick presets and auto-vision detection                |
| - Binds form inputs without ID mismatches (thinking-options)                     |
+-----------------------------------------------------------------------------------+
                                          |
                                          v  Renders to DOM
+-----------------------------------------------------------------------------------+
| VIEW LAYER (templates/index.html & static/css/style.css)                          |
| - Full-viewport responsive modal container (inset: 16px, min-width: 760px)        |
| - Crisp monochrome SVG icons for tabs and badges (static/icons/ffffff/)           |
| - Tab 1 Widescreen Split:                                                         |
|   * Left Rail (380-420px): Endpoints, Workers, Embeddings, Action Interpreter      |
|   * Right Canvas (1fr): Model Hub List + Active Model Inspector & Tuning Card     |
| - Tab 2 Focused View: Engine-wide sampling fallbacks, streaming, and rate limits  |
+-----------------------------------------------------------------------------------+
```

---

## File Targets

1. `docs/virtualWorld/dev_tasks/todo/ui/task-945-settings-modal-fullscreen-dashboard-and-model-hub.md`: This specification file.
2. `routes/benchmark.py`: Enrich OpenRouter and provider model ingestion to normalize `supported_parameters` (`tools`, `structured_outputs`), detailed `reasoning` object (`mandatory`, `supported_efforts`), `description`, `pricing`, and `benchmarks`.
3. `templates/index.html`:
   - Expand `#settings-modal .modal-content` into full-viewport layout.
   - Replace emoji navigation tab icons with `static/icons/ffffff/` SVGs.
   - Embed the Active Model Inspector and Token Budget directly into the Model Hub on Tab 1.
   - Uncap `#max-tokens-input` from `max="32768"`.
   - Clean up Tab 2 (`#tab-agent`) to house global engine sampling and streaming settings.
4. `static/css/style.css`:
   - Full-viewport responsive grid and flex rules (`width: min(calc(100vw - 32px), 1600px); height: calc(100vh - 32px);`).
   - SVG icon utility classes (`.modal-tab-icon-svg`, mask-image or filter styling).
   - High-density Model Browser list and styled Active Model Inspector card.
5. `static/js/ui-controller.ts`:
   - Update `ModelDescriptor` interface with enriched fields (`description`, `pricing`, `capabilities`, `reasoning_details`).
   - Implement dynamic reasoning effort dropdown generation on model click.
   - Implement uncapped token budget syncing and quick presets (`Auto: 4K`, `Balanced: 8K`, `Model Max`).
6. `static/js/ui/settings-view.ts`:
   - Fix `#thinking-options` container visibility check during `populateForm()`.
