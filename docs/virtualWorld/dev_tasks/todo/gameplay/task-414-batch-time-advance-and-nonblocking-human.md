---
type: task
status: todo
area: gameplay
priority: medium
---

# task-414: Server-side batch time advance and non-blocking human

**Filed:** 2026-09-19  
**Depends on:** task-399 / task-409 (deterministic plan layer), task-411
(attended set), task-412 (promotion boundary).  
**Evidence:** `static/js/agent-engine.js:862–869`, `static/js/agent/turn-queue.js:151–158`,
`routes/action_handlers.py:1129–1132`, `tools/soak_sim.py:232`.

## Goal

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
than removing the sleep.

## Non-blocking human

`HumanTurnComposer.request()` (`agent-engine.js:270`) waits indefinitely for
input. A batch needs a no-human roster option or a turn timeout that
resolves/defers the human turn.

## Changes

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

## Verification

- Unit: `advance(N)` advances the clock by N and processes each character the
  expected number of times; attended plan continuation with no LLM call; human
  timeout resolves.
- Perf: a multi-thousand-tick `advance` runs in seconds with no browser.
