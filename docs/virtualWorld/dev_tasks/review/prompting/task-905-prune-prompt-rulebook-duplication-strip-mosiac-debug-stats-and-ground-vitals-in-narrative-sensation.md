---
type: task
status: review
area: prompting
priority: high
wiki: "[[AI & Narration/Agent Engine]]"
---

# task-905: prune prompt rulebook duplication, strip mosiac debug stats, and ground vitals in narrative sensation

**Filed:** 2026-10-25
**Related:** 

## What

Prune instructional duplication across the prompt pipeline and strip internal game engine telemetry (such as raw vital percentages like thirst 80 and internal planner choice counts like Choices: activity 12, free 27, major 29, minor 21) from character turn prompts. Replace video-game imperative barks with subjective bodily sensations so characters experience physiological need without breaking the fourth wall.

## Why

In benchmark runs, reasoning models quoted internal engine telemetry word-for-word in their inner monologue (e.g. Nemotron-550B thinking 'Thirst is hitting hard - 80 on the meter', and Laguna-S noting 'I am very hungry (75) and very thirsty (80)'). Furthermore, the prompt was 17,455 characters with over 55% taken up by rulebook overhead: emote rules were printed twice, JSON rules were printed twice, action structure was printed twice, and hunger/thirst was stated four times in eight lines with imperative tutorial commands ('EAT your protein_bar').

## How

1. In character-state.ts: update buildMosiacContext to omit raw vital numbers (n.value) and omit Choices tier counters.
2. In character-state.ts: update describeVital to describe sensations qualitatively (e.g. parched throat, pounding head, hollow stomach) without imperative action commands.
3. In turn-prompts.ts: prune redundant duplicate emote rules, repeated JSON schema instructions, and duplicate action rules from the User prompt, letting the System prompt govern standing mechanics.
4. In system-prompt.ts: consolidate ACTIONS and ACTION STRUCTURE to eliminate duplicated verb and budget explanations.
5. In data/scenarios/mansion.json: clean hardcoded static 'You are thirsty.' trait_behavior strings off characters so thirst emerges dynamically from vitals.
6. Recompile TypeScript bundles via npm run build:ts.
7. Verify in Benchmark Lab (/bench) with live prompt assembly and targeted unit tests.

## Browser UI and intended live verification

- Intended UI home: /bench
- Current availability: available today
- Note: This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today.
- Live steps when available:
  1. Navigate to http://localhost:4444/bench.
  - expected: Character prompt assembled without raw vital numbers (no thirst 80) or choice counts.
  2. Inspect Assembled Prompt details.
  - expected: User prompt contains no duplicate emote rulebook, and vitals read as narrative physical sensations.
  3. Run benchmark on a character.
  - expected: Models reason naturally about their physical state without quoting integer metrics or breaking character.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: Assembled prompt contains no raw vital integers or choices tallies, and prompt length is substantially pruned.
   - observed: On /bench, selecting Elena Vance assembled a 9,940-character prompt (down from 17,455, a 43% reduction). Verified: 'thirst 80' absent, 'Choices:' absent, 'EAT your / FIND SOMETHING' absent, '=== YOUR MIND ===' present with subjective sensation.
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: /bench character select dropdown updates prompt preview.
   - observed: Navigated to http://localhost:4444/bench with Playwright Chromium, waited for #bench-character to load, selected 'elena vance', read #bench-prompt-preview inner text, and verified live assembly.
3. Run the targeted regression test for the mechanism.
   - expected: Unit tests pass.
   - observed: Ran `node tools/unit/run.cjs test_describe_vital.js` (8 passed), `node tools/unit/run.cjs test_prompt_capture.js` (4 passed), `node tools/unit/run.cjs test_turn_prompts.js` (7 passed), and `python -m pytest tests/test_benchmark_routes.py` (8 passed).

## Acceptance

- [x] No raw vital integers (e.g. 80, 75) appear in MOSIAC or turn prompts
- [x] No internal choice counts (e.g. Choices: activity 12...) appear in character prompt
- [x] Emote rules and JSON schema examples appear once in System prompt, not duplicated in User prompt
- [x] Imperative arcade barks (EAT your protein_bar) replaced with subjective physical sensations
- [x] TypeScript recompiled and targeted tests pass with zero em-dashes

## Files

- `static/js/agent/prompt-builder/character-state.ts`
- `static/js/agent/prompt-builder/character-state.js`
- `static/js/agent/prompt-builder/turn-prompts.ts`
- `static/js/agent/prompt-builder/turn-prompts.js`
- `static/js/agent/prompt-builder/system-prompt.ts`
- `static/js/agent/prompt-builder/system-prompt.js`
- `static/js/agent/prompt-builder/schema-fragments.ts`
- `static/js/agent/prompt-builder/schema-fragments.js`
- `tools/unit/test_describe_vital.js`
- `tools/unit/run.cjs`
- `data/scenarios/mansion.json`
