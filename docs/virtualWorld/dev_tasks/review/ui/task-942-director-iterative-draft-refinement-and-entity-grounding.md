---
type: task
status: review
area: ui
priority: high
wiki: "[[Gameplay/Turn Queue & Human Turns]]"
related: [task-933, task-728]
---

# task-942: Director AI iterative draft refinement (currentDraft context), steering note priority, and entity grounding

**Filed:** 2026-11-09
**Related:** task-933, task-728

<!-- deps:start -->
**Related:** [[task-933-character-controller-selector-and-director-turn-composer]], [[task-728-directed-control-mode-a-director-reviews-and-edits-an-llm-character-s-turn-before-it-acts]]
<!-- deps:end -->

## What

Improve `AgentEngine.draftTurnForCharacter()` and `HumanTurnComposer.askDirector()` so that the AI Director:
1. **Supports Iterative "Take 2" Refinement (`currentDraft`)**:
   - When the user clicks **🎬 Ask Director** while composer fields (`#htc-do`, `#htc-speech`, `#htc-emote`, `#htc-thought`, `#htc-emotion`, `#htc-memory`) already contain text, pass `currentDraft` into `draftTurnForCharacter()`.
   - Inject a `[CURRENT DRAFT IN COMPOSER]` block so follow-up notes like *"keep the action, just make the line shorter and whisper it to Kayla"* modify the existing draft in place instead of starting over from scratch.
2. **Places `[MANDATORY DIRECTOR STEERING NOTE]` Above the JSON Schema With Override Priority**:
   - Inject the Director's Note directly before the final `"Respond with ONLY a single raw JSON object..."` instruction with explicit authority (`"MANDATORY STAGE DIRECTION FROM THE DIRECTOR (overrides default schedule/motivation for this beat)"`) so 8B local models follow the user's stage direction instead of getting distracted by background schedule text.
3. **Grounds Drafted Item / Way / Person Names Against the Character's Actual Surroundings**:
   - After parsing the LLM's structured action (`{ action, item, target }`), resolve fuzzy noun phrases (e.g. `"phone case"` or `"phone"` -> `"Jake's phone"`, `"kayla"` -> `"kayla jenkins"`) against the character's carried/worn items, visible room items, people present, and ways out so `#htc-do` and `#htc-say-target` receive valid canonical names.

## Why

Live Playwright testing of `task-933` on `http://localhost:4444` revealed two UX friction points:
1. When told *"examine Jake's phone and mutter sarcastically about the cracked screen"*, the 8B local model output `do: "examine phone case"` (an un-grounded substring that fails on execution) and rambled about its `08:00` schedule because `[DIRECTOR STEERING NOTE]` was appended after the JSON schema block without override priority.
2. Clicking **🎬 Ask Director** a second time to refine a draft had no memory of Take 1 because `askDirector()` did not pass the current input values to `draftTurnForCharacter()`.

## How

1. In `static/js/agent/human-turn-composer.ts` (`askDirector()`):
   - Collect current composer input values into `currentDraft` (`action`, `speech`, `speechVolume`, `target`, `emote`, `inner`, `emotion`, `memory`) and pass them to `VW.agent.draftTurnForCharacter()`.
2. In `static/js/agent-engine.ts` (`draftTurnForCharacter()`):
   - Accept `currentDraft` in `opts`.
   - Format `[CURRENT DRAFT IN COMPOSER]` and `[MANDATORY DIRECTOR STEERING NOTE]` and insert them immediately before `"Respond with ONLY a single raw JSON object"` in `decidePrompt` / `reactPrompt`.
   - Add `_groundDirectorDraft(charName, state, player, currentArea, draft)` to match fuzzy item/person/way references against the character's inventory, equipped items, visible room items, people in the room, and exits.

## Browser UI and intended live verification

Intended UI home: Human Turn Composer modal (`#htc-director-bar` -> `🎬 Ask Director` and `#htc-director-note`).

Live steps:
1. Open `jake halloway`'s turn in the Human Turn Composer on `http://localhost:4444`.
2. Enter *"examine Jake's phone and whisper a sarcastic comment to Kayla"* in `#htc-director-note` and click **🎬 Ask Director**.
   - expected: `#htc-do` populates with grounded `"examine Jake's phone"` (never `"examine phone case"`).
3. Enter a follow-up refinement note *"keep the action, just make the whisper shorter"* and click **🎬 Ask Director** again.
   - expected: `#htc-do` keeps `"examine Jake's phone"` while `#htc-speech` updates to a shorter line.

## Steps to verify

1. Run unit tests: `node tools/unit/run.cjs test_directed_mode`.
   - expected: All tests pass, including `currentDraft` forwarding and entity grounding.
2. Verify live in Playwright on `http://localhost:4444`.

## Acceptance

- [x] `askDirector()` passes `currentDraft` from composer inputs to `draftTurnForCharacter()`.
- [x] `[MANDATORY DIRECTOR STEERING NOTE]` is injected before the closing JSON schema instruction with explicit override priority.
- [x] Drafted actions and targets are grounded against the character's inventory, room items, people, and ways.
- [x] Zero em-dashes in code, task, or documentation.

## Files

- `static/js/agent-engine.ts`
- `static/js/agent/human-turn-composer.ts`
- `tools/unit/test_directed_mode.js`
