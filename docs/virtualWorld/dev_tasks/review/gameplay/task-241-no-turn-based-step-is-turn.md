# Task-241: No-Turn-Based Mode — Each Step Is a Turn

**Status:** In Review — implemented 2026-08-16.
**Source:** `dev_tasks/developer ideas.md` (on no turn based eash step should be a turn)

## Goal

In "no turn based" mode — where you manually select one agent and step it
(Step Once, or the loop repeats that same selected agent) — each step must
behave like turn-based mode running with only that one character:
once the stepped character's turn finishes, end the turn (`applyTurn`) so the
game clock advances and per-turn systems (vital decay, condition ticks, trait
tick effects, turn-triggered triggers) fire exactly as they do in turn-based
mode.

Example: 4 characters in a scenario, turn-based **off**. Select agent "Lyrie"
and click Step Once. Lyrie acts, then the turn is ended as if she were the only
character in the turn queue — time advances and new-turn effects play.

The bug this fixes: with turn-based off, Step Once currently runs the action but
never ends the turn, so time does not advance and anything that waits for a new
turn never fires.

## Implementation

- `static/js/agent/turn-queue.js`: extracted the wrap-complete block of
  `advance()` (`turnNumber++`, `ApiClient.applyTurn()`, `ApiClient.clearTurnEvents()`)
  into a reusable `async endTurn()`, exported on `TurnQueue`. `advance()` now
  calls `endTurn()` when a full cycle wraps.
- `static/js/agent-engine.js`:
  - `stepOnce()`: when `!config.turnBased` and a `config.controllingPlayer` is
    selected, calls `TurnQueue.endTurn()` and re-renders after the step —
    behaves like turn-based with a single-character queue.
  - `start()` loop: same — each non-turn-based step ends the turn before the
    next iteration, so the repeated loop advances the clock per step too.
- Backend unchanged: `/api/turn/apply` → `tick_turn()` already applies decay +
  ticks for all characters.

## Verification

- `node --check` passes on both edited files; 941 pytest pass.
- Browser (live, 127.0.0.1:4444): turn-based off, `controllingPlayer='rat'`,
  `stepOnce()` → `time_ticks` 21→22 and `turnNumber` 0→1. Turn ends, clock
  advances, decay tick ran.