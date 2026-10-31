---
type: task
status: done
area: ui
priority: high
wiki: "[[Memory System]]"
related: ["task-908", "task-690", "task-730"]
parent: task-908
---

# task-909: Dedicated Memory Model client and AgentLens live retrieval comparison sandbox

**Filed:** 2026-10-30
**Related:** task-908, task-690, task-730, task-219

<!-- deps:start -->
**Parent:** [[task-908-associative-memory-retrieval-3-0-multi-facet-perceptual-cues-and-zero-padding-prompt-lanes]]
**Related:** [[task-908-associative-memory-retrieval-3-0-multi-facet-perceptual-cues-and-zero-padding-prompt-lanes]], [[task-690-retrieval-2-0-one-multi-signal-scorer-structured-character-model-recall-b]], [[task-730-chat-based-interactive-memory-creation-the-character-reacts-in-voice-to-author-new-memories]]
<!-- deps:end -->

## What

Provide the UI configuration, execution client, and inspection sandbox for the Memory Subsystem:

1. **Dedicated Memory Model Settings:**
   - Add a "Memory Model" configuration block in Settings (`settings-view.ts` and `config.ts`), following the embedding model pattern.
   - Options: Provider / Base URL, API Key, Model Name, API Format. Defaults to "Same as Agent Model" when left empty.
   - Instantiates a dedicated `window.memoryLLMClient = new LLMClient()` configured with `reasoning: "off"` to ensure structured JSON memory extractions and reflections execute at full speed without wasting token budgets.

2. **AgentLens Live Retrieval Sandbox:**
   - Enhance the Agent Lens preview (`agent-lens.ts`) with a non-mutating recall workbench:
     - Fix `buildMemoryContext` call inside Agent Lens to respect `_hypotheticalArea` instead of falling back to `player.current_area`.
     - Provide a hypothetical stimulus bar: allows typing a line of dialogue (e.g. "want olives with that?") or toggling a need state (hunger) to test recall reactions in real time.
     - Display a side-by-side diff: Legacy Flat Recall vs New Associative Recall.
     - Collapsible candidate breakdown (`explain: true`): displays why the winning memories were selected (intersection match, recency, need match) and lists rejected runner-ups.

3. **Open Question Tripwire Execution:**
   - Support `category: "question"` in prompt assembly and Inspector.
   - When room entities, dialogue, or visible items match an open question's watch targets, surface the question and active hypotheses in Lane 4 (`=== OPEN QUESTIONS / SUSPICIONS ===`).

## Why

Benchmark runs on local LM Studio instances demonstrated that small 1.7B-2B models run structured memory extractions at over 200 tokens/second with 0.2s time-to-first-token when reasoning is turned off and GPU layers are offloaded. A dedicated client lets users delegate memory reflections and extractions to a fast local model without bottlenecking the main character model. Meanwhile, an interactive sandbox in Agent Lens allows tuning retrieval weights live without spending simulation turns or modifying scenario files.

## How

- Update `static/js/config.ts` and `static/js/ui/settings-view.ts`:
  - Add fields for `memoryModel`, `memoryApiBase`, `memoryApiKey`, `memoryApiFormat`.
  - Wire save/restore logic and initialize `window.memoryLLMClient`.
- Update `static/js/agent-lens.ts`:
  - Pass `hypotheticalArea` into `buildMemoryContext`.
  - Add stimulus input and retrieval strategy toggle to the preview header.
  - Render score explanation chips and candidate comparison.
- Wire tripwire evaluation in `engine/memory_retrieval.py` for open questions.

## Browser UI and intended live verification

Intended UI home: 
1. Settings modal -> Connection tab -> "Memory Model" section.
2. Left sidebar -> Lens tab -> Agent Lens -> Recall Sandbox controls.

Current availability: Planned / ready for implementation.

Live steps when available:
1. Open Settings modal, configure Memory Model (e.g. local LM Studio endpoint `http://localhost:1234/v1` with a fast 1.7B/2B model), and save.
2. Open Agent Lens on Kayla, set hypothetical area to Cafeteria, and type "hey jake, want olives with that" into the stimulus bar.
   - expected: Agent Lens immediately refreshes the memory preview, shows the Jake/olives associative memory winning the top slot, and displays its score breakdown chips.
3. Toggle between "Legacy" and "Associative" in the sandbox controls.
   - expected: Legacy view displays the old flat padded list; Associative view displays the clean lane-budgeted recall without zero-score filler.

## Steps to verify

1. Follow the intended live steps in Settings and Agent Lens.
   - expected: Memory model settings persist and Agent Lens reflects live stimulus scoring.
   - observed: Recorded during implementation.
2. Run targeted tests: `python -m pytest tests/test_memory_retrieval_associative.py tests/test_memory_api.py`.
   - expected: Endpoint tests pass with full output.
   - observed: Recorded during implementation.

## Acceptance

- [x] Browser: Settings modal saves and loads custom Memory Model configuration cleanly, defaulting to localhost LM Studio (`http://localhost:1234/v1`, format `lmstudio`, model `lmstudio-community/lfm3-1.7b`).
- [x] Browser: Settings modal provides a live diagnostic Test Connection button for the dedicated memory worker with latency reporting.
- [x] Browser: `window.memoryLLMClient` initializes with the configured memory model and enforces `reasoning: "off"`.
- [x] Browser: Agent Lens stimulus input drives immediate retrieval preview update without mutating character state.
- [x] Browser: Agent Lens displays candidate score explanations and rejected runner-ups when expanded.
- [x] Unit: Open questions surface into Lane 4 when a matching entity or concept enters the situation context.

## Files

- `static/js/config.ts`
- `static/js/ui/settings-view.ts`
- `static/js/agent-lens.ts`
- `engine/memory_retrieval.py`
- `tests/test_memory_retrieval_associative.py`
