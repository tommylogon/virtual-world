---
type: task
status: todo
area: testing
priority: medium
wiki: "[[Developer Tooling]]"
related: [task-894, task-934]
---

# task-937: Agentic Playwright image generation authoring pipeline for web ChatGPT and Gemini accounts

**Filed:** 2026-11-09
**Related:** task-894, task-934

<!-- deps:start -->
**Related:** [[task-894-llm-benchmark-harness-capture-a-turn-prompt-for-one-character-run-across-selected-models-providers-score-speed-format-hallucinations-surface-a-run-dashboard]], [[task-934-benchmark-output-ratings-and-model-metadata-tagging]]
<!-- deps:end -->

## What

Implement an automated authoring pipeline that drives a local browser session via Playwright to generate high-resolution character portraits, item icons, and area illustrations through existing ChatGPT and Gemini web subscriptions:

1. **Dedicated Authoring Workflow (Out-of-Sim)**:
   - Provide an authoring assistant script (`tools/image_gen/web_authoring.py`) and UI action trigger in the Entity Inspector / Character Sheet.
   - Strictly isolated as an authoring tool; never called inside the background simulation tick loop or autonomous turn execution.
2. **Browser Profile & Session Reuse**:
   - Launches Playwright connected to an existing user browser profile or persistent context directory (`--user-data-dir`) where the user is already authenticated to ChatGPT (Plus) or Gemini (Advanced).
   - Bypasses API token costs and runs complex generation models without burdening local GPU resources.
3. **Automated Prompt Formulation & Asset Binding**:
   - Constructs visual image prompts directly from the node's authored properties:
     - Characters: `appearance`, `clothing`, `emotion`, `tags`, `base_description`.
     - Items: `description`, `material`, `visual_aspects`.
     - Areas: `biome`, `weather`, `features`, `lighting`.
   - Sends the prompt to the web interface, monitors the DOM for generation completion, downloads the resulting high-res image file to `static/assets/images/generated/<slug>.png`.
   - Automatically writes the relative asset path to the target entity's `image` property in the scenario or library.

## Why

High-fidelity diffusion models (such as Imagen 3, DALL-E 3, or Flux) require substantial VRAM or costly per-generation cloud API tokens. Authors often maintain active personal web subscriptions (ChatGPT Plus, Gemini Advanced) that produce fast, high-quality images, but manually copying entity descriptions, prompting the web interface, downloading files, moving them into the repo, and binding paths to nodes is a tedious, multi-step process. Automating this as an authoring tool provides high-res visuals on resource-constrained PCs with zero extra API expense.

## How

1. In `tools/image_gen/web_authoring.py`:
   - Implement CLI driver: `python tools/image_gen/web_authoring.py --provider chatgpt|gemini --node-id <id> --profile-dir <path>`.
   - Read entity properties from the scenario or `data/library/` to assemble a concise visual depiction prompt.
   - Use Playwright with persistent context to open ChatGPT/Gemini, locate the message textarea, submit the prompt, and wait for image element generation.
   - Extract the generated image URL or stream, save locally to `static/assets/images/generated/<id>_<timestamp>.png`.
   - Update scenario or library JSON with the relative asset path.
2. In `routes/authoring_ops.py` (or Entity Inspector UI):
   - Add a lightweight trigger endpoint `POST /api/authoring/generate-web-image` accepting `{ node_id, provider }` that kicks off the script and returns progress status.
3. In `static/js/inspector/agent-view.ts`:
   - In the Images tab, add a button: *"🎨 Generate via Web (Playwright)"* offering ChatGPT or Gemini targets.

## Browser UI and intended live verification

Intended UI home: Character Inspector -> Images tab, and Item/Area Inspector header.

Current availability: Entity inspectors allow uploading local images or typing URLs manually into the `image` field. No automated web-session generation affordance exists.

Live steps when available:
1. Open the Character Inspector in the browser UI for a character lacking portrait art (e.g. `Sammy Lopez`).
2. Navigate to the Images tab.
   - expected: Displays current portrait preview and a *"🎨 Generate via Web"* button with options for ChatGPT and Gemini.
3. Click *"🎨 Generate via Web (Gemini)"*.
   - expected: Launches the generation task. The UI displays an active progress indicator: *"Submitting visual prompt to Gemini..."*.
4. Once generation completes, inspect the character card.
   - expected: The newly generated image is downloaded into `static/assets/images/generated/`, bound to Sammy's node, and displayed immediately in the portrait preview box.
5. Save or commit the scenario.
   - expected: Scenario file on disk stores the relative path to the new generated asset.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. In browser UI, inspect Character Inspector Images tab.
   - expected: Shows button to trigger web-assisted image generation.
   - observed: Only manual URL input and file browse controls exist.
2. Run tool dry-run: `python tools/image_gen/web_authoring.py --help`.
   - expected: Shows options for `--provider`, `--node-id`, `--profile-dir`.
   - observed: Tool does not exist yet.
3. Generate image for a test item node and check file system.
   - expected: File exists in `static/assets/images/generated/` and is linked to node.
   - observed: No automated generation pipeline exists.

## Acceptance

- [ ] Command-line tool `tools/image_gen/web_authoring.py` automates prompt input and image download using Playwright persistent browser context.
- [ ] Character Inspector Images tab provides a one-click affordance to trigger web generation for the selected entity.
- [ ] Generated images are saved into `static/assets/images/generated/` and bound directly to the target node's `image` property.
- [ ] Pipeline is strictly authoring-time and completely decoupled from background simulation ticks.
- [ ] Zero em-dashes anywhere in task cards, code, or documentation.

## Files

- `tools/image_gen/web_authoring.py`
- `routes/authoring_ops.py`
- `static/js/inspector/agent-view.ts`
- `static/js/inspector/item-view.ts`
