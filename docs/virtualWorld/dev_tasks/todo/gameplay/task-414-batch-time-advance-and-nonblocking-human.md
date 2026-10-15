---
type: task
status: todo
area: gameplay
priority: medium
blocked_by: [task-399, task-409, task-411, task-412]
---

# task-414: Server-side batch time advance and non-blocking human

**Filed:** 2026-09-19  
**Related:** task-464 (player-facing Fast-forward / Wait mode) builds the UX, human
freeze, and "while you waited" summary on top of this transport.  
**Depends on:** task-399 / task-409 (deterministic plan layer), task-411
(attended set), task-412 (promotion boundary).  
**Evidence:** `static/js/agent-engine.js:862–869`, `static/js/agent/turn-queue.js:151–158`,
`routes/action_handlers.py:1129–1132`, `tools/soak_sim.py:232`.

<!-- deps:start -->
**Blocked by:** [[task-399-background-character-simulation-and-reactivation]], [[task-409-background-schedules-work-and-coarse-social]], [[task-411-attention-budget-and-fidelity-tiers]], [[task-412-promotion-demotion-and-trace-consolidation]]
<!-- deps:end -->

## What

Let the **server** advance N in-game minutes in one request, so a long run does
not need the browser as metronome — without changing turn ordering or action
rules.

## Why (the real bottleneck)

The browser drives the whole world today:

1. `agent-engine.js:862–869` — `while (config.running)` calls `step()` for one
   character, then `await setTimeout(2000)` (800 ms in simultaneous mode).
2. `turn-queue.js:151–158` — `advance()` increments the index; wrapping to 0
   calls `endTurn()`.
3. `endTurn()` → `POST /api/turn/apply` → `handle_apply_turn_decay` →
   `world.tick_turn()` (`routes/action_handlers.py:1129–1132`).

So one `tick_turn()` = one in-game minute **and** only fires once all ~23
characters have acted, with a hardcoded pause per step. A week is
10,080 wraps × 23 steps × 2 s ≈ 128 h of wall clock *before any LLM call*.
That, not model cost, is why a week cannot run interactively.

Two loops are currently fused:

| Loop | Owner | Cost | Contents |
|---|---|---|---|
| **Time** — `tick_turn()` | server | cheap | decay, vitals, environment, triggers, conditions, background sim |
| **Action** — decide + act | browser today | expensive | LLM / human / simple_npc action |

## Model (decided)

Add `POST /api/world/advance {ticks: N}` that runs `tick_turn()` N times
server-side in one request and returns a **bounded summary** (clock, deaths,
notable trace), not the full log. `soak_sim.py:232` already proves the
library-level loop; this lifts it into the app.

- **Backgrounded characters** are run by the deterministic plan/schedule layer
  (task-399 / task-409) — no LLM.
- **Attended characters continue their current server-side plan** during the
  batch (decided). The plan executor acts; the LLM is consulted only at the next
  decision boundary or on promotion (task-412). No LLM call per tick.
- The interactive per-character loop is unchanged; batch is an additional path.

## Pacing

The 2000 ms step sleep (`agent-engine.js:868`) is **legacy UI pacing**, present
since the initial public release (`170d5f1`); the 800 ms simultaneous branch was
added in `314d74b` (1.2.0, off by default) with no design note. It is separate
from the real throttle, `static/js/agent/rate-limiter.js`, enforced inside
`step()` at `agent-engine.js:412–425` from `config.rpmLimit`. Keep it for
readability, but make it **configurable**; the batch path uses no delay rather
than removing the sleep. It is **not needed** for correctness (each `step()` is
awaited) or for rate limiting. Two refinements: skip the delay when the step
already took longer than it (an LLM call is its own pacing), and expose it as a
setting (default ~2s, `0` = fast-forward).

## Non-blocking human

`HumanTurnComposer.request()` (`agent-engine.js:270`) waits indefinitely for
input. A batch needs a no-human roster option or a turn timeout that
resolves/defers the human turn.

## How

1. `POST /api/world/advance {ticks: N}` with a bounded summary response.
2. Attended-character **plan continuation** during batch (LLM only at
   boundaries).
3. Configurable step delay (interactive default keeps 2 s; batch uses 0).
4. Non-blocking human policy (no-human roster or timeout).
5. Do not change clock, `turn_number`, or `tick_turn` semantics.

## Acceptance

- `advance(N)` advances the clock by N ticks and returns a bounded summary.
- With attended characters, their current plan continues through the batch; no
  LLM call per tick, and the LLM is re-consulted at the next decision boundary.
- A present human does not stall a batch beyond the chosen timeout/no-human
  policy.
- Clock, `turn_number`, and `tick_turn` semantics unchanged (one tick = one
  in-game minute, all characters processed).
- Background and foreground characters behave consistently before/after a batch.

## Non-goals

- Running LLM actions inside the batch loop.
- A UI for replay/observation (task-415).

## Steps to verify

- Unit: `advance(N)` advances the clock by N and processes each character the
  expected number of times; attended plan continuation with no LLM call; human
  timeout resolves.
- Perf: a multi-thousand-tick `advance` runs in seconds with no browser.

## Dependency reality (2026-09-24)

- **`task-399` is satisfied**; **`task-409` is mostly shipped** (clock-schedule
  traversal + coarse social), so the deterministic plan layer this task consumes exists.
  **`task-411` is the real unmet dependency** — there is no attended-set
  selector / fidelity tier yet.
- **The server-side N-minute advance already exists under other task ids**:
  `engine/timeskip.py:82 advance_world` loops `tick_turn`, the route chunks long
  spans (`routes/timeskip_ops.py`), and `task-481`'s soak orders give the
  non-blocking-human behaviour when another attended human is present. What is
  missing here is the named `POST /api/world/advance {ticks:N}` transport
  (only `/api/world/timeskip` and `/api/world/soak` are registered) and
  attended-plan continuation across the batch.

## Why

TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: the game view's clock, event stream, and Human Turn panel while a batch is requested through `POST /api/world/advance`. This card specifies a server batch endpoint, not a new player-facing time-advance button.

Current availability: the card proposes bounded server-side tick batching and a non-blocking policy for present humans. A browser control for batch advance is not specified; the observable game state remains the existing clock, plans, events, and human-turn surface.

Live steps when available:
1. Load a scratch scenario with a visible clock, one background character, one attended character with a multi-tick plan, and a present human. Record the clock and current plan states.
2. In the browser DevTools console, submit `POST /api/world/advance` with a small bounded `ticks` value, then inspect the response, `/api/state`, clock, and event stream.
   - expected: the clock advances by exactly the requested in-game minutes, the response summary is bounded, and both background and attended characters process those ticks.
3. Repeat with the human present and the configured wait/timeout policy active.
   - expected: the batch completes according to that policy without waiting for the human indefinitely; turn ordering and `turn_number`/`tick_turn` semantics remain unchanged.
4. Set the attended character's plan to cross a decision boundary during the batch and inspect LLM/plan events.
   - expected: the current plan continues without an LLM call on every tick; the next decision is requested only at the boundary.

This section is not a claim that planned UI exists or works today.
