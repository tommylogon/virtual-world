---
type: task
status: todo
area: ui
priority: medium
wiki: "[[UI & Settings/Settings & Configuration]]"
related: [task-925, task-926, task-934]
---

# task-941: Settings modal overhaul: 2-column layout, model capabilities on hover, context window limits, emoji entity fix, and graph tab retirement

**Filed:** 2026-11-09
**Related:** task-925, task-926, task-934

<!-- deps:start -->
**Related:** [[task-925-settings-modal-clean-code-mvc-refactor-and-embedding-consolidation]], [[task-926-settings-modal-declarative-populate-scenario-sync-and-debounced-storage]], [[task-934-benchmark-output-ratings-and-model-metadata-tagging]]
<!-- deps:end -->

## What

Comprehensive overhaul of the Settings modal dialog (`templates/index.html`, `static/js/ui/settings-view.ts`, `static/js/ui-controller.ts`, and `static/css/style.css`) to improve visual presentation, auto-detect model capabilities, fix encoding errors, and eliminate obsolete duplicate tabs:

1. **2-Column Responsive Dashboard Layout**:
   - Convert `.settings-modal-inner .tab-pane` from a tall, single-column stack into a 2-column CSS grid (`grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px;`).
   - Pairs related configuration cards side by side (e.g. Sampling next to Reasoning; Protocol next to Rate Limiting), cutting vertical scroll depth by half.
2. **Semantic Memory Model Selector**:
   - Replace the bare text input `#embed-model` with an interactive dropdown populated from `/api/models` (filtered to embedding models like `nomic-embed-text`, `text-embedding-3-small`, and `bge-m3`) with custom text entry fallback.
3. **Model Information on Hover Tooltip**:
   - In `static/js/ui-controller.ts:renderModelList()`, attach a rich hover tooltip (via `title` attribute or Tippy) to every `.model-list-item`.
   - Displays model ID, context window (e.g. `128K context`), architecture, parameter count, quantization, and capability badges (Vision, Reasoning, Tools).
4. **Context Window & Max Tokens Based on Model Capabilities**:
   - Update `routes/benchmark.py` and `routes/settings.py` to preserve `context_length` from OpenRouter and OpenAI `/models` endpoints instead of dropping it on fallback.
   - In `Agent Settings -> Sampling & Token Budget`, display the active model's authoritative context window limit (e.g. `Model Context: 128,000 tokens | Suggested Max Output: 4,096`) alongside hard and soft token caps, with a *"Set to model default"* shortcut button.
5. **Fix Corrupted Emojis & Mojibake Entities**:
   - Fix corrupted hexadecimal entity codes in `templates/index.html` lines 565-595 that lacked the `x` prefix:
     - Replace `&#129e0;` with literal `🧠` (Brain emoji, was displaying as `E0;`).
     - Replace `&#129f1;` with literal `🧱` (Bricks emoji for structured output, was displaying as `F1;`).
     - Replace `&#23f1;&#65039;` with literal `⏱️` (Stopwatch emoji, was displaying as `F1;`).
6. **Auto-Detect Vision from Model**:
   - Automatically check `agent-vision-enabled` when a selected model has `vision: true` in its descriptor, displaying a status badge `(Auto-detected from model: Vision capable)` while preserving manual override.
7. **Retire Obsolete Graph Settings Tab**:
   - Remove the redundant `tab-graph` pane from the Settings modal. All physics sliders (spread force, edge rest length, snappiness, overlap guard) are already maintained live on the canvas hotbar under `⚙ Tune ▾`. Replace the tab with an informative link or button that activates `GraphToolbar.toggleTuning()`.
8. **Engine Config Tab Fix**:
   - Ensure `EngineConfigView` safely waits for `window.Lit` bootstrap before rendering, and synchronize its save action with the modal footer.

## Why

The current Settings modal has several visual and functional defects: hexadecimal entities without `x` render as unprintable character boxes with trailing `e0;` and `f1;` fragments; models in the selection list provide zero hover inspection; `Max Tokens` inputs provide no reference to the actual context window of the selected model; and Semantic Memory forces users to manually type embedding model names. Furthermore, the single-column layout forces excessive vertical scrolling, and the `Graph` tab is an exact duplicate of the canvas hotbar's `⚙ Tune ▾` menu.

## How

1. In `templates/index.html`:
   - Replace `&#129e0;`, `&#129f1;`, and `&#23f1;&#65039;` with literal UTF-8 emojis (`🧠`, `🧱`, `⏱️`).
   - In `tab-connection`, convert `#embed-model` into a combo-box with quick picks and datalist populated from embedding models.
   - In `tab-agent`, add `#active-model-context-info` displaying context limit and recommended max token button.
   - Remove obsolete `tab-graph` panel content, replacing with a single note directing users to the canvas `⚙ Tune ▾` menu.
2. In `static/css/style.css`:
   - Add `.settings-modal-inner .tab-pane { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }`.
   - Add media query for screens below 800px to collapse back to 1 column gracefully.
3. In `static/js/ui-controller.ts`:
   - In `renderModelList()`, attach formatted `title` tooltips to each `.model-list-item` containing full specs.
   - When a model is selected, check `m.vision` and update `config.visionEnabled` automatically with user feedback.
   - Update `#active-model-context-info` with the active model's context length and recommended output tokens.
4. In `routes/benchmark.py`:
   - When parsing OpenAI/OpenRouter model lists, preserve `context_length` and `architecture` fields from API payloads.

## Browser UI and intended live verification

Intended UI home: Main Settings modal (accessed via ⚙️ Settings button in the top toolbar).

Current availability: Settings modal renders in a tall single column with corrupted entity text (`E0;`, `F1;`), no hover info on models, no context window indicators in Agent Settings, and a redundant Graph tab.

Live steps when available:
1. Click `⚙️ Settings` in the top application toolbar.
   - expected: Settings modal opens in a clean 2-column layout. The tab bar no longer has a redundant Graph physics tab.
2. Click `Agent Settings` tab.
   - expected: Headings render clean emojis (🧠 Reasoning & Thinking, 🧱 Structured Output, ⏱️ Rate Limiting) without `E0;` or `F1;` artifacts.
3. Check the Sampling & Token Budget section.
   - expected: Displays the active model's context window limit (e.g. `Context: 128K tokens`) alongside the Max Tokens inputs with a button to apply recommended output tokens.
4. Click `Connection` tab and hover over a model in the model list.
   - expected: A rich tooltip appears showing model ID, context window, parameters, and capabilities.
5. In the Embedding Model section, click the Model selector.
   - expected: A dropdown opens showing detected embedding models rather than requiring manual text typing.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. In browser UI, open Settings modal and inspect Agent Settings tab.
   - expected: Renders in 2 columns with clean emojis and context window specs.
   - observed: 1-column layout with corrupted `E0;`/`F1;` entity fragments and no context window indicators.
2. Hover over a model in the Connection tab model list.
   - expected: Shows tooltip with context window, architecture, and capabilities.
   - observed: No tooltip or hover details.
3. Check Embedding Model input.
   - expected: Provides dropdown/quick-pick selector for embedding models.
   - observed: Plain text input box.
4. Run frontend tests: `node tools/unit/run.cjs`.
   - expected: All unit tests pass.

## Acceptance

- [ ] Settings modal tabs render in a 2-column responsive grid layout.
- [ ] Hexadecimal entity encoding errors in `templates/index.html` are fixed, displaying clean emojis.
- [ ] Model list items render detailed specification tooltips on hover.
- [ ] Agent Settings displays active model context limits and recommended token defaults.
- [ ] Vision mode is automatically enabled when selecting a vision-capable model.
- [ ] Semantic memory embedding model provides an interactive selection list.
- [ ] Obsolete Settings Graph tab is retired in favor of the canvas `⚙ Tune ▾` popover.
- [ ] Zero em-dashes anywhere in task cards, code, or documentation.

## Files

- `templates/index.html`
- `static/css/style.css`
- `static/js/ui-controller.ts`
- `static/js/ui/settings-view.ts`
- `routes/benchmark.py`

## Erratum / Superseded Notice (2026-11-12)

The proposal in this task to leave sampling and token budget controls exclusively on Tab 2 ("Agent Settings") while model selection lived on Tab 1 ("Connection") fractured the user flow and led to ID mismatch regressions (`thinking-options` vs `thinking-effort-row`). 

This architecture was formally superseded and resolved by task-945 (`docs/virtualWorld/dev_tasks/done/ui/task-945-settings-modal-fullscreen-dashboard-and-model-hub.md`), which consolidated the unified Model Hub and Active Model Inspector directly on Tab 1 with uncapped token budgets, dynamic reasoning controls, and SVG vector iconography.
