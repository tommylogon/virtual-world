---
type: task
status: todo
area: gameplay
priority: medium
blocked_by: [task-399, task-409, task-411, task-412]
wiki: "[[Features/timeskip]]"
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
not need the browser as metronome - without changing turn ordering or action
rules.

## Why (the real bottleneck)

The browser drives the whole world today:

1. `agent-engine.js:862–869` - `while (config.running)` calls `step()` for one
   character, then `await setTimeout(2000)` (800 ms in simultaneous mode).
2. `turn-queue.js:151–158` - `advance()` increments the index; wrapping to 0
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
| **Time** - `tick_turn()` | server | cheap | decay, vitals, environment, triggers, conditions, background sim |
| **Action** - decide + act | browser today | expensive | LLM / human / simple_npc action |

## Model (decided)

Add `POST /api/world/advance {ticks: N}` that runs `tick_turn()` N times
server-side in one request and returns a **bounded summary** (clock, deaths,
notable trace), not the full log. `soak_sim.py:232` already proves the
library-level loop; this lifts it into the app.

- **Backgrounded characters** are run by the deterministic plan/schedule layer
  (task-399 / task-409) - no LLM.
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

## Current scope (2026-10-20)

The server-side batch time advance and the non-blocking human policy this card
asks for are **implemented** - under `/api/world/timeskip` and the soak-order
mechanism, not under the `POST /api/world/advance {ticks: N}` transport this
card originally named. The surviving scope is the named transport itself.

Current state (measured 2026-10-20):

| Card ask | Where it lives now | Status |
|---|---|---|
| Server advances N in-game minutes in one request | `engine/timeskip.py:179 advance_world(gs, minutes, ...)` loops `tick_turn`; `routes/action.py:108` registers `POST /api/world/timeskip` | done (task-464) |
| Bounded summary response, not the full log | `routes/timeskip_ops.py` chunks long spans and returns a summary; `static/js/ui/timeskip.ts` renders it | done (task-464) |
| Backgrounded characters run by the deterministic plan layer, no LLM | `engine/timeskip.py` `advance`/`advance_world` use the background sim | done (task-399/409) |
| Attended plan continuation, LLM only at decision boundaries | `engine/timeskip.py:273 advance(...)`; task-466's interrupt/relevance evaluator gates LLM re-consultation | done (task-466) |
| Non-blocking human (no-human roster or timeout) | `routes/timeskip_ops.py` `world: true` forces a no-subject world advance; task-481's per-character soak orders let another attended human stand in | done (task-481) |
| `POST /api/world/advance {ticks: N}` | **not registered** | **missing** |

Measured: `rg -n "world/advance" .` returns zero code hits outside this card and
the generated `docs_combined.md`; the only registered world routes are
`/api/world/timeskip` (`routes/action.py:108`) and `/api/world/soak`
(`routes/timeskip_ops.py:212, 237`). `engine/timeskip.py:179` and `:273` are
the two entry points, both taking `minutes` (the same unit as the card's
`ticks`, since one tick = one in-game minute).

## How

Either:

1. Add `POST /api/world/advance {ticks: N}` as a thin wrapper over
   `timeskip.advance_world(gs, minutes=N)` returning the same bounded summary,
   with the same chunking and streaming behaviour `routes/timeskip_ops.py`
   already has; or
2. Close the transport ask by documenting `/api/world/timeskip` as the canonical
   batch endpoint and deleting this card's named-route acceptance item.

Do not add a second tick loop: `advance_world` is the loop, and the interactive
per-character path in `static/js/agent/turn-queue.ts` (326 lines) must keep
owning the cursor. `turn_order` is still client-side only - that is task-437's
scope, not this card's.

## Acceptance

- [ ] `POST /api/world/advance {ticks: N}` is registered and advances the clock
      by N in-game minutes in one request, returning a bounded summary.
- [ ] The new route reuses `timeskip.advance_world` and its existing chunking,
      streaming (`routes/timeskip_ops.py:64-78`), and no-human/timeout policy -
      no second implementation of the tick loop.
- [ ] Clock, `turn_number`, and `tick_turn` semantics remain unchanged (one tick
      = one in-game minute, all characters processed), as measured before and
      after.
- [ ] The route is reachable from the existing `ApiClient` path that already
      posts `/api/world/timeskip`, so the browser needs no new control.

## Steps to verify

1. `rg -n "world/advance" routes/ app.py` returns the new route, and
   `rg -n "advance_world" engine/timeskip.py` still shows exactly one loop.
   - expected: one new route registration; the loop count is unchanged.
   - observed: not run (2026-10-20 measurement only).
2. Submit `POST /api/world/advance {ticks: 60}` against a scratch scenario and
   compare the clock and `/api/state` before and after.
   - expected: the clock advances by exactly 60 in-game minutes; the summary is
     bounded; background and attended characters process those ticks.
   - observed: not run.
3. Repeat with a present human and the soak-order policy active.
   - expected: the batch completes per the existing policy without waiting for
     the human indefinitely.
   - observed: not run.
4. Unit: `advance(N)` advances the clock by N and processes each character the
   expected number of times; attended plan continuation runs with no LLM
   call; a human timeout resolves.
   - expected: the asserted clock delta and the branch taken match the
     contract, and the attended character issues no LLM call inside the batch.
   - observed: not run for the new route. Measured 2026-10-20: the loop this
     route would delegate to is `engine/timeskip.py:179` `advance_world`,
     covered by `tests/test_timeskip.py`; the named route itself does not
     exist yet.
5. Perf: a multi-thousand-tick `advance` runs in seconds with no browser.
   - expected: the batch completes server-side in seconds, with no per-tick
     client round trip.
   - observed: not run for the new route. Measured 2026-10-20: the same work
     already runs server-side through `/api/world/timeskip`
     (`routes/timeskip_ops.py:79`), so the perf property is a property of
     the existing loop rather than of the missing route.

## Non-goals

- Running LLM actions inside the batch loop.
- A UI for replay/observation (task-415).

## Dependency reality (2026-09-24)

- **`task-399` is satisfied**; **`task-409` is mostly shipped** (clock-schedule
  traversal + coarse social), so the deterministic plan layer this task consumes exists.
  **`task-411` is the real unmet dependency** - there is no attended-set
  selector / fidelity tier yet.
- **The server-side N-minute advance already exists under other task ids**:
  `engine/timeskip.py:82 advance_world` loops `tick_turn`, the route chunks long
  spans (`routes/timeskip_ops.py`), and `task-481`'s soak orders give the
  non-blocking-human behaviour when another attended human is present. What is
  missing here is the named `POST /api/world/advance {ticks:N}` transport
  (only `/api/world/timeskip` and `/api/world/soak` are registered) and
  attended-plan continuation across the batch.

## Why

The bottleneck this card was filed against is measured in the section above,
and the fix for it has shipped: the server advances the clock itself
(`engine/timeskip.py:179` `advance_world`), the batch returns a bounded
summary, background characters run on the deterministic plan layer, attended
characters continue their current plan with the LLM consulted only at a
decision boundary, and the no-human policy exists. What did not ship is the
transport this card named - `POST /api/world/advance {ticks: N}` is not
registered, so the batch is reachable only under the name
`/api/world/timeskip`. That leaves a reader of this card, of
`routes/action.py` and of the client unable to tell that the documented
endpoint and the implemented endpoint are the same operation under two names,
and it leaves the card's own named-route acceptance item permanently
unchecked. Closing that gap - by registering the named route as a thin
wrapper over the existing loop, or by recording the timeskip route as the
canonical one and striking the named-route acceptance item - is what is
left, and it is what keeps the documented surface and the implemented surface
from drifting apart.

## Files

- `routes/action.py:108` - where `POST /api/world/timeskip` is registered, and
  therefore where `POST /api/world/advance` would be registered
- `routes/timeskip_ops.py:79` - `handle_timeskip`, the handler a new route
  delegates to; `:64` `_publish_tick` is the streaming/chunking path that
  must be reused unchanged, and `:211` / `:236` are the existing soak
  declare/cancel routes
- `engine/timeskip.py:179` - `advance_world`, the single tick loop; `:273`
  `advance` is the per-turn entry point. Both take `minutes`, which is the
  same unit as the card's `ticks` (one tick is one in-game minute)
- `static/js/api.ts:69` - the `ApiClient` path that already posts to the
  world routes; `static/js/ui/timeskip.ts:233` and `:290` are the two
  existing clients of `/api/world/timeskip`, and the reachability
  acceptance item means the new route is added to this path, not a new one
- `static/js/agent/turn-queue.ts:188` - `advance()`, the interactive cursor
  that must keep owning the turn order (task-437's scope, not this card's)
- `static/js/agent-engine.ts:1155` - the per-step pacing sleep the card's
  "Pacing" section discusses (2000 ms, 800 ms in simultaneous mode, 250 ms
  in per-room simultaneous)
- `tests/test_timeskip.py` - the suite covering the tick loop and the
  interrupt/threat rules a batch must not change

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
 cross a decision boundary during the batch and inspect LLM/plan events.
   - expected: the current plan continues without an LLM call on every tick; the next decision is requested only at the boundary.

This section is not a claim that planned UI exists or works today.
