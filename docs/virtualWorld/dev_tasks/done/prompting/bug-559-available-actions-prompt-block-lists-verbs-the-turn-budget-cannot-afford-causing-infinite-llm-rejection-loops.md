---
type: bug
status: done
area: prompting
priority: high
related: ['task-352', 'task-491', 'bug-539']
wiki: "[[AI & Narration/Agent Engine]]"
---

# bug-559: available actions prompt block lists verbs the turn budget cannot afford causing infinite llm rejection loops

**Filed:** 2026-10-21  
**Area:** prompting / agent engine  
**Priority:** High  

## What

When an agent character expends their major action budget (`major: 0`), `PromptBuilder.buildRoomContext` (`static/js/agent/prompt-builder/room-context.ts`) continues to list major action verbs under `=== AVAILABLE ACTIONS ===` (such as `attack`, `grab`, `lead`, `go`). The LLM selects one of these visible actions, which the engine immediately rejects with `"You have no major action left this turn."` In the subsequent decision retry, the same prompt block is rebuilt with the same major verbs, causing a recursive rejection loop that consumes tens of thousands of tokens on a single tick.

## Steps to Reproduce

1. Start a turn with an AI character (e.g. Arix in Food Storage).
2. Character executes a major action (e.g. `examine Glowing Mushroom Pouch`).
3. Note that `player.turn_slots.major` is now `0`.
4. Observe the prompt for the next action: `=== AVAILABLE ACTIONS ===` still includes `attack`, `grab`, `lead`, and directional exits like `go`.
5. Character selects `go into camp`.
6. Engine rejects with `"You have no major action left this turn."`
7. Loop re-runs repeatedly.

## Acceptance

- [x] `PromptBuilder` filters `=== AVAILABLE ACTIONS ===` against `turnSlots(player)`: when `major <= 0`, major actions are omitted or explicitly marked unavailable.
- [x] If all action budgets (`major` and `minor`) are exhausted, the prompt explicitly instructs the LLM that only free actions, speech, or `wait` remain.
- [x] Unit tests in `tools/unit/test_turn_prompts.js` assert that exhausted budgets omit major verbs.

## Verified 2026-10-21 (working tree, uncommitted)

- `keep()` (`static/js/agent/prompt-builder/contextual-actions.ts:343-345`) drops
  any suggested verb `affordable()` says the remaining slots cannot pay for.
  Every major verb goes through it: `attack`, `grab`, `lead`, `give`, `steal`,
  `escape`, `stand`, `examine`, `make`, and the requirement-gated
  crawl/climb/jump. `wait` is appended unconditionally so the turn can always end.
- The exhausted-budget note is emitted at `contextual-actions.ts:398-404` for
  both the major-only and major+minor cases.
- Exit lines gate too: `room-context.ts:472-503` only offers `go`/`dash`/`examine`
  when `major > 0` and `approach` when `minor > 0`.
- Wiring: `room-context.ts:885` passes `turnSlots(player)`, and `turn_slots` is in
  the player payload (`engine/serialization.py:197`), so the values the prompt
  filters on come from the same `/api/state` the gate enforces against.
- `node tools/unit/run.cjs` - 782 passed, 0 failed, including the three bug-559
  assertions in `tools/unit/test_turn_prompts.js`.
- **Remaining:** the change is uncommitted. Live browser check on 2026-10-21:
  confirmed working by the user, so the filter is observed in a real prompt and
  no rejection loop was produced.

## Browser UI and intended live verification

UI home: the `📤` raw request chip in the event stream, which prints the full
prompt body, plus the budget pips in the human turn composer (`#htc-modal`).

1. Settings -> Agent Settings -> enable `⏭️ Turn-Based Mode` and
   `🔬 Show Raw LLM`; set Turn mode to `Sequential`. An API key is required,
   because the prompt only exists when an agent calls the model.
2. Load a scenario and let the composer open for the controlled character.
3. Spend the major action through `Act` (one `go`, `attack`, `grab` or `steal`
   tier action), then use `⏭ end turn` without spending anything else. The
   closing beat is an LLM call for that character with `major` at 0.
4. Expand the `📤` chip for that call and find `=== AVAILABLE ACTIONS ===`.
   - expected: no major verbs (`go`, `dash`, `attack`, `grab`, `lead`, `give`,
     `steal`, `escape`, `stand`, `make`, or requirement-gated `crawl`/`climb`/
     `jump`); the note `(Major actions exhausted this turn. You can still use
     minor/free actions, speak, or wait.)` when minor remain, or the
     major-and-minor wording when both are gone; and `wait - wait or hold
     still` still present.
   - If the closing beat does not fire, watch a second LLM call for the same
     character in the same turn (the react phase) instead, and say which phase
     you read.
5. Read-only console extraction of the last such block:
   ```js
   [...document.querySelectorAll('.msg-bubble-rawllm')]
     .map(b => b.querySelector('.rawllm-chip-body').innerText)
     .filter(t => t.includes('=== AVAILABLE ACTIONS ==='))
     .pop()
     .split('=== AVAILABLE ACTIONS ===')[1]
     .split('\n===')[0]
   ```

