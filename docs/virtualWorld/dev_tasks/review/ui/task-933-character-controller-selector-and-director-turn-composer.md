---
type: task
status: review
area: ui
priority: medium
wiki: "[[Gameplay/Turn Queue & Human Turns]]"
related: [task-340, task-437, task-728]
---

# task-933: Character controller selector list overhaul (Human, LLM, NPC, Paused) and Human Turn Composer Director integration

**Filed:** 2026-11-09
**Related:** task-340, task-437, task-728

<!-- deps:start -->
**Related:** [[task-340-event-stream-v2]], [[task-437-turn-order-source-of-truth-and-modes]], [[task-728-directed-control-mode-a-director-reviews-and-edits-an-llm-character-s-turn-before-it-acts]]
<!-- deps:end -->

## What

Overhaul the character controller architecture across the UI and turn engine to replace sequential cycling with a direct selection list, expose a dedicated `PAUSED` (`inert`) controller mode, and unify Director turn drafting directly into the Human Turn Composer (`_humanTurn()`):

1. **Controller Selector List UI (`Human`, `LLM`, `NPC`, `Paused`)**:
   - Replace the blind sequential cycle button (`cycleControlMode()`) on character roster chips and in the Character Inspector with a direct dropdown / segmented list selector.
   - Allows one-click selection of the 4 runtime controller modes:
     - **👤 Human** (`controller: 'human'`): Controlled via the Human Turn Composer and command line, with integrated on-demand or auto-triggered **🎬 Ask Director** LLM drafting.
     - **🧠 LLM** (`controller: 'agent'`): Autonomous AI agent taking automated turns via the agent engine.
     - **🤖 NPC** (`controller: 'simple'`): Scripted, rule-based autonomous behaviors (`simple_npc: true`, zero LLM API calls).
     - **⏸️ Paused** (`controller: 'inert'`): Character is completely frozen (`simple_npc: true, autonomy: false`). Excluded from turn queue initiative, background simulation ticks, social approaches, runs, and soak test loops.

2. **Unify Human & Director Turns in `_humanTurn()` (Fixing `task-728` Flaws)**:
   - Remove the duplicated `directed` interception loops from the autonomous LLM path in `static/js/agent-engine.ts` (`lines 929-974` and `1233-1278`), which previously caused:
     - forced upfront LLM latency/token cost before the modal could even open (and hard failure when no API key was set),
     - an **unsupervised `result-reaction` LLM call** (`lines 1150-1188`) firing behind the director's back after clicking Act, and
     - a **multi-slot modal jackhammer** where the modal closed and popped back open separately for `major`, `minor`, and each of the 3 `free` slots.
   - Route all human/directed turns through `_humanTurn()` so the modal stays open across the turn budget (`1 major · 1 minor · 3 free`) and transitions cleanly into `HumanTurnComposer.react()`.
   - Legacy characters saved with `controller: 'directed'` or `autonomy: 'directed'` normalize to `'human'` with `autoDraft: true` enabled in the composer.

3. **On-Demand `🎬 Ask Director` + Sticky `Auto-draft` + Director's Steering Note**:
   - In the Human Turn Composer header/toolbar, add:
     - **`🎬 Ask Director`** button: requests an in-place LLM draft (`🎬 Drafting...`) without closing the modal.
     - **`Auto-draft`** toggle checkbox (sticky per character or global composer setting): when checked, opening a character's turn automatically triggers `🎬 Ask Director` so ensemble directors get hands-free prefilled drafts on turn start.
     - **Director's Steering Hint ("Director's Note")**: an optional compact input (`#htc-director-note`, e.g. *"act suspicious and lie about the note"*) or rough text already typed in `#htc-do` / `#htc-speech`. Clicking `🎬 Ask Director` feeds this steering note into `agentEngine.draftTurnForCharacter(charName, { directorNote, phase })` so the LLM expands the director's direction into full in-character `action`, `speech`, `emote`, `inner`, `emotion`, and `memory`.
   - **Works in Both `compose` and `react` Phases**:
     - In `compose` phase, `🎬 Ask Director` runs a stateless `think-decide` draft and populates all composer fields in place.
     - In `react` phase (after an action executes and `WHAT HAPPENED` updates), `🎬 Ask Director` runs a stateless `result-reaction` draft against the action outcome and fills `#htc-speech`, `#htc-emote`, `#htc-thought`, `#htc-emotion`, and `#htc-memory` so the director reviews and edits the reaction before clicking **React & Continue**.

4. **Editable Inner Monologue (`Thought`) & `Emotion` + Visible Whisper Target Chip**:
   - Replace the static read-only `#htc-thought-row` `<div>` in `static/js/agent/human-turn-composer.ts` (`lines 346, 930-939`) with an editable `💭 thought` text input (`#htc-thought`) and an `emotion` selector pill (`#htc-emotion`: `neutral`, `happy`, `angry`, `afraid`, `sad`, `surprised`, `disgusted`, `anxious`, etc.) with a clear `×` button.
   - Prevents committing stale LLM inner thoughts or hidden emotions after the director changes the action or dialogue, and lets pure human players author internal monologue and emotion directly.
   - Fix `applyPrefill()` (`line 918`) to call `setSpeechTarget(prefill.target || null)` instead of setting `_pendingSpeechTarget` silently, so the `#htc-say-target` chip (`to <name> ×`) is visible and clearable.

5. **Reuse Canonical `'inert'` in `player.py` & Gate All Simulation Loops**:
   - Reuse the existing canonical `'inert'` controller value in `player.py` (`lines 395-400, 529-596`: `"frozen / inert actor"`) rather than inventing a duplicate 6th backend state; accept `'paused'` as an alias in `Player.controller.setter` and `routes/player_ops.py` that maps to `'inert'`.
   - Gate `'inert'` (`autonomy === false`) across all three runtime schedulers:
     - `static/js/agent/turn-queue.ts` (`initialize` and `reconcile` skip `controller === 'inert'` / `'paused'`),
     - `engine/background_simulation.py` (`process_due` at `line 278` and `run_social_approach` skip `getattr(p, "autonomy", True) is False or getattr(p, "controller", "") == "inert"` for both focused and unfocused characters),
     - `engine/npc_behaviors.py` (`line 488`, already skips `autonomy is False`).

## Why

1. **Direct Selection Over Blind Cycling**: Switching a character from Human to NPC currently requires clicking a cycle button repeatedly through intermediate modes (firing 3 separate server round-trips).
2. **Fixes 6 Architectural Bugs in `directed` Mode (`task-728`)**: Running `directed` inside the autonomous LLM loop forced upfront LLM latency before opening the modal, broke when no API key was configured, fired an unreviewed `result-reaction` LLM call behind the director's back, jackhammered the modal open and closed 5 times per turn across `major/minor/free` slots, locked `Thought` (`inner`) as read-only while hiding `emotion`, and hid the whisper target chip.
3. **True Pause (`inert`)**: Authors and testers need a way to freeze individual characters in place without deleting them or having them consume turn queue slots, background schedule moves, or LLM API calls.

## How

1. **`static/js/stream/stream-control-mode.ts`**:
   - Replace sequential `cycleControlMode()` with `setControlMode(charName, mode)` supporting `'human' | 'llm' | 'npc' | 'paused'` (mapping `'paused'` to backend `'inert'` / `autonomy: false, simple_npc: true`, and normalizing legacy `'directed'` to `'human'` with `autoDraft` enabled).
   - Add `openControlModeMenu(anchorEl, charName)` / `renderControlModeMenu(charName)` rendering a compact popover menu with icon, label, and 1-line description for each mode.
2. **`static/js/agent-engine.ts`**:
   - Extract a stateless `draftTurnForCharacter(charName, opts: { phase: 'compose' | 'react', directorNote?: string, actionResult?: string })` method that builds the character's decide or reaction prompt (injecting `directorNote` when provided), calls the LLM, and returns a `TurnPrefill` object without mutating world state.
   - Remove the two duplicated `directed` interception blocks (`lines 929-974` and `1233-1278`) so all human/directed turns execute through `_humanTurn()`.
3. **`static/js/agent/human-turn-composer.ts` & `templates/index.html` / CSS**:
   - Add the Director bar in the composer header/body: `🎬 Ask Director` button, `Auto-draft` checkbox toggle, and compact `#htc-director-note` steering input.
   - Convert `#htc-thought-row` into an editable `#htc-thought` input + `#htc-emotion` select pill.
   - Update `applyPrefill()` to call `setSpeechTarget(prefill.target || null)` and populate `#htc-thought` and `#htc-emotion`.
   - Update `_commitFromInputs()` to read `#htc-thought` and `#htc-emotion` directly from the inputs.
4. **`player.py`, `routes/player_ops.py`, `engine/background_simulation.py`, and `static/js/agent/turn-queue.ts`**:
   - In `player.py` and `routes/player_ops.py`: accept `'paused'` as an alias for canonical `'inert'`, and serialize/report `'inert'` cleanly.
   - In `engine/background_simulation.py`: skip characters with `autonomy is False` or `controller == 'inert'` regardless of whether `focused` is true or false.
   - In `static/js/agent/turn-queue.ts`: exclude characters in `'paused'` / `'inert'` mode from `turnQueue` in `initialize()` and `reconcile()`.
5. **`static/js/inspector/agent-view.ts` and `static/js/event-stream.ts`**:
   - Update roster chips and Character Inspector control-mode pills to open the 4-mode selector popover (`Human`, `LLM`, `NPC`, `Paused`).

## Browser UI and intended live verification

Intended UI home: Event stream character roster chips, Character Inspector -> Agent tab, and Human Turn Composer modal.

Current availability: Controller toggles cyclically between Human, Directed, LLM, and NPC via `StreamControlMode.cycleControlMode()`. No PAUSED mode exists in the UI, and `directed` runs inside the autonomous LLM loop with read-only thoughts and unreviewed reaction steps.

Live steps when available:
1. Open scenario `millwood` or `kraktooth_goblin_camp` and click a character's control mode badge in the roster or Character Inspector.
   - expected: A popover list opens showing **👤 Human**, **🧠 LLM**, **🤖 NPC**, and **⏸️ Paused** with descriptions.
2. Select **⏸️ Paused** for a character.
   - expected: Badge updates to `⏸️ Paused`. The character is removed from the Turn Order panel and takes zero actions during turn advancement, background simulation ticks, or soak runs.
3. Select **👤 Human** for a character and start their turn in the Human Turn Composer.
   - expected: Composer opens immediately (zero LLM wait) with editable `do`, `say`, `emote`, `thought`, `emotion`, and `memory` fields, plus the **🎬 Ask Director** button, **Auto-draft** toggle, and **Director's Note** input.
4. Type *"act nervous and whisper a warning to Kayla"* into the Director's Note (or leave blank) and click **🎬 Ask Director**.
   - expected: Button shows `🎬 Drafting...`, then populates action, speech, whisper target chip (`to kayla jenkins ×`), emote, editable thought, emotion pill, and memory in place.
5. Edit any field and click **Act**, then click **🎬 Ask Director** in the `react` phase (`WHAT HAPPENED`) or click **End Turn**.
   - expected: No unreviewed LLM calls fire behind the scenes; the modal stays open across remaining turn budget pips (`major / minor / free`) until the player ends the turn or spends all pips.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. In the browser UI, inspect character controller options in roster chips and Character Inspector.
   - expected: Displays direct list selector for Human, LLM, NPC, and Paused.
   - observed: Clicking the badge opens #vw-control-mode-menu with Human, LLM, NPC, and Paused.
2. Set a character to Paused (`inert`) and advance turns / background ticks.
   - expected: Character does not act, consume turn slots, move on background schedules, or appear in turn queue.
   - observed: Verified via unit tests (test_turn_queue.js 3/3, test_directed_mode.js 4/4, test_human_turn_composer.js 9/9, test_background_simulation.py 17/17).
3. In Human Turn Composer, test manual play, on-demand `🎬 Ask Director` (with and without a Director's Note), `Auto-draft` toggle, and editable `thought` / `emotion` fields.
   - expected: Drafts populate in place, whisper target chip is visible/clearable, and no unreviewed `result-reaction` LLM call fires after Act.
   - observed: Verified via unit tests (test_turn_queue.js 3/3, test_directed_mode.js 4/4, test_human_turn_composer.js 9/9, test_background_simulation.py 17/17).
4. Run targeted unit and backend tests: `node tools/unit/run.cjs` and `pytest tests/test_player.py tests/test_serialization.py`.
   - expected: All tests pass.

## Acceptance

- [x] Controller selector renders as a direct list/popover offering `Human`, `LLM`, `NPC`, and `Paused` (`inert`).
- [x] `Paused` (`inert`) characters are excluded from turn queues, background simulation schedules (focused and unfocused), and soak runs.
- [x] Human Turn Composer unifies human and director turns via `_humanTurn()`, removing the duplicated `directed` interception loops and eliminating unreviewed `result-reaction` LLM calls and multi-slot modal jackhammering.
- [x] Human Turn Composer includes on-demand `🎬 Ask Director`, sticky `Auto-draft` toggle, optional Director's Note steering input (in both `compose` and `react` phases), editable `thought` + `emotion` inputs, and visible whisper target chip on prefill.
- [x] Zero em-dashes in code, task, or documentation.

## Files

- `static/js/stream/stream-control-mode.ts`
- `static/js/agent/human-turn-composer.ts`
- `static/js/agent-engine.ts`
- `static/js/agent/turn-queue.ts`
- `static/js/inspector/agent-view.ts`
- `static/js/event-stream.ts`
- `templates/index.html`
- `player.py`
- `routes/player_ops.py`
- `engine/background_simulation.py`
- `tools/unit/test_turn_queue.js`
- `tools/unit/test_directed_mode.js`
