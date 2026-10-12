---
type: task
status: review
area: gameplay
priority: medium
---

# task-784: Dash burst: a dash costs the major AND the minor; the finish hop is the only valid follow-up

**Filed:** 2026-10-12
**Related:** task-352 (action economy), task-104 (dash->go chain), task-333/task-334 (human turn panel)

## What

A dash is a two-hop burst, and it is paid for by **both** the major (the initiate)
and the minor (the finish hop). The finish hop is the **only** valid action
directly after a dash, and a character with no minor cannot start a dash at all.
The rule is enforced once, in the engine, so humans, LLM agents and any budgeted
actor share it; the human turn panel offers Dash on a way and then offers the
finish.

## Why

`go` and `dash` are both MAJOR and the budget is `major: 1` (task-352), so a dash
spent the only major and a second hop was refused: *"You have no major action left
this turn."* That made the intended two-hop dash impossible for a human, and it
silently broke the agent's own `dash -> go` chain (`CHAIN_RULES`, task-104): the
chained `go` hit the same wall and `_runChainFollowUp` swallowed the error. `dash`
was also missing from the scene menu entirely, so a human had no way to start one.

## How

- **Engine rule** — `engine/action_tiers.apply_action_gate(slots, verb, burst)` is
  the one implementation. A dash needs a major *and* a minor
  (`can_initiate_dash`) and spends the major; the finish (`go`/`dash`/`climb`/
  `crawl`/`jump`) spends the minor and clears the burst; `wait` aborts without
  spending the minor (so a dead-end dash is never a soft-lock); any other action
  while armed is refused.
- **State** — `Player.burst_pending` (runtime only, like `turn_slots`). Armed by
  the dash handler *after* the hop succeeds (a blocked dash raises first, so it is
  left unarmed with its major spent); cleared by the finish/abort and at the turn
  boundary (`tick_manager` slot reset). Published in `/api/state`, popped from a
  scenario save.
- **Route** — `routes/action_handlers.py` `_slot_gate` calls the gate; the dash
  handler arms on success. This is the single choke point every budgeted actor
  (the human composer and the agent submit) goes through, so agents are fixed for
  free.
- **Client** — `turn-scene-view.ts`: a **Dash** entry in `buildWayMenu` (disabled
  when the minor is missing), and while armed the way menu becomes the finish
  ("Finish dash -> X") plus "Stop here (wait)", with a matching hint. The human
  composer's existing step loop re-opens after the dash and shows that menu, so
  the "second turn to choose the finish" falls out of it.
- **NPCs** — simple NPCs (`behaviors.py` dash) and the soak/background sim keep no
  slot budget (`_act` is need-driven and travels with `move_to_area`, never a
  dash), so they dash as a plain hop and are unaffected; the rule lives in the
  shared engine table, not the browser.

## Steps to verify

1. Run `python -m pytest tests/test_dash_burst.py tests/test_dash_burst_route.py`.
   - expected: 11 passed - the two-slot cost, the finish-only window, the abort,
     and the route wiring (arm / refuse / finish / clear).
   - observed: 11 passed.
2. Run `python tools/ts_convert.py check`.
   - expected: gate green.
   - observed: gate green.
3. Run `python -m pytest tests/test_dash_burst.py tests/test_dash_burst_route.py tests/test_action_tiers.py tests/test_serialization.py tests/test_movement.py`.
   - expected: 92 passed.
   - observed: 92 passed.

## Acceptance

- [x] A dash needs both a major and a minor; without the minor it cannot start.
- [x] The finish hop costs the minor and is the only valid action right after a dash.
- [x] One engine implementation shared by humans and agents; the agent `dash -> go`
  chain works again.
- [x] The human scene menu offers Dash, then the finish (or an abort).
- [ ] Live browser pass: start a human turn, dash a way, confirm the panel offers
  the finish and the budget pips drop major then minor.

## Files

- `engine/action_tiers.py` — `apply_action_gate`, `can_initiate_dash`,
  `BURST_INITIATE` / `BURST_FINISH_VERBS` / `BURST_ABORT_VERBS`.
- `player.py` — `burst_pending`.
- `engine/tick_manager.py` — clear the burst on the turn reset.
- `engine/serialization.py` — publish `burst_pending`; pop it from a save.
- `routes/action_handlers.py` — the gate call + arming on a successful dash.
- `static/js/agent/turn-scene-view.ts` (+ `.js`) — Dash entry, burst finish menu, hint.
- `tests/test_dash_burst.py`, `tests/test_dash_burst_route.py`.
