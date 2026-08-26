# Task: Agent Validation, Feedback & Emote Gating

**Status**: Done
**Completed**: 2026-08-03

## Goal

Stop the frontend agent loop from silently dropping actions and contradicting
reality. Two concrete failures from `event_log_2026-08-02T12-00-06.txt`:

1. **`drink water` → `invalid action: "drink water" — skipping`** (line 3945) — the
   COMMANDS table tells the model "also supports eat and drink for consumables",
   but `_validateAction`'s verb whitelist (`agent-engine.js:617`) omits `eat`/`drink`
   (and `dash`, `scream`). The action is dropped, the model never learns why, and it
   repeats the same attempt.
2. **Emotes contradict failures** — after `wear short forest cape` fails
   (`The torso slot is full`), the emote still plays "bundles it around her
   shoulders with a relieved sigh" (line 11540). Same for Kaelen "arranging the
   kindling inside" while `use kindling on stove` failed. The model stores these as
   sensory memories and keeps re-trying.

## Changes

### 1. `static/js/agent-engine.js` — `_validateAction` whitelist (line 617)
- Add verbs the backend actually supports and the COMMANDS table advertises:
  `eat`, `drink`, `dash`, `scream`, `put`, `get`, `pickup`, `steal`, `undo`,
  `sit` (if supported). Audit `validVerbs` against the command table in
  `prompt-builder.js`/system prompt so they match 1:1.

### 2. No silent drops — surface validation feedback
- When `_validateAction` rejects an action (lines 281-284 and 416-419), instead of
  just `finalAction = ''`:
  - set `config.lastActionResult[charName]` to something like
    `[System] "drink water" is not a valid action. Use 'use <item>' for consuming.`
  - write a high-importance memory entry (`AgentMemory.storeMemory(..., 7, 'system')`)
    so the next observe prompt shows the rejection.
- This guarantees the react phase / next observe teaches the model the correct form.

### 3. `static/js/agent/prompt-builder.js` — DECIDE sees last result
- `buildDecisionPrompt` (line 770) omits `lastResult`. Add an optional param and
  include `=== LAST ACTION RESULT ===\n{lastResult}` so the decide phase knows what
  just happened (observe already includes it via line 738, but decide is where the
  choice is made). Wire it in `agent-engine.js:272`.

### 4. Emote gating on action success
- In `agent-engine.js` decision emote (lines 331-343) and reaction emote
  (lines 378-390): only execute the emote when the action result does **not**
  indicate failure. Heuristic: skip emote (or pass a "the action didn't work" note)
  when `actionResult` matches failure signals (`can't`, `don't have`, `cannot`,
  `full`, `nothing happens`, `isn't`, `isn't here`, `not a`, `can't find`, `purely decorative`).
- Also store the **raw failure** to memory with high importance so future turns
  don't replay the false success ("wore the cape" memory).

### 5. (Optional) Hardening
- When the same *action string* fails twice in a row, inject a one-line nudge into
  the next observe prompt: `"You already tried '<action>' and it failed — pick a
  different approach."`

## Files Modified
- `static/js/agent-engine.js`
- `static/js/agent/prompt-builder.js`
- `docs/virtualWorld/AI & Narration/` (agent loop doc if present)

## Status Notes

- **Changes 1-3 landed in commit `4d87248`** ("fix: implement event-log fixes
  F1-F8", 2026-08-02): whitelist synced to the backend/COMMANDS table
  (`eat`/`drink`/`dash`/`scream`/`get`/`pickup`/`put`/`steal`), rejections
  surfaced via `lastActionResult` + a high-importance `system` memory
  (`_surfaceRejectedAction`), and `buildDecisionPrompt` gained the
  `=== LAST ACTION RESULT ===` block. No `invalid action` drops remain in the
  latest event logs.
- **Change 4 (decision emote) also landed in `4d87248`** via the
  `_isFailureResult` heuristic gate at `agent-engine.js:339`.
- **Remaining gap closed 2026-08-03**: the **non-reactive (combined-phase)
  emote** at `agent-engine.js:449` was ungated — it's speculative (emitted in
  the same LLM call as the action, before the action resolves), so it could
  still narrate success the world never granted. Now gated on
  `!this._isFailureResult(output)`.
- **Change 4 reaction emote** (`agent-engine.js:386`, react phase) left ungated
  intentionally: the react-phase LLM already sees `=== WHAT HAPPENED ===`, so
  its emote is informed; gating would suppress legitimate failure reactions
  (e.g. "frowns").
- **Change 5 (hardening)** already covered by the failure-aware repeat
  warnings in `buildMemoryContext` (`prompt-builder.js:285-294`) — flags any
  failed action attempted 3+ times.
