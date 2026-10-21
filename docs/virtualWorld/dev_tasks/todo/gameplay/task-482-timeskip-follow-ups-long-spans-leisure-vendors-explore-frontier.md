---
type: task
status: todo
area: gameplay
priority: medium
wiki: "[[Features/timeskip]]"
---

# task-482: Timeskip follow-ups: long spans, leisure vendors, explore frontier

**Filed:** 2026-09-23
**Related:** task-464; task-467; task-398

## What

Deferred from task-464: spans beyond the 1,440-min route cap (soak-runner-style job), leisure buying from a vendor, and explore frontier preference tied to generation (task-398).

## Acceptance

- [x] A blocking request may span more than 1,440 minutes (up to
      `timeskip.MAX_MINUTES`, one in-game week), run in day-sized chunks so no
      single synchronous advance holds a worker for a whole week.
- [ ] Leisure buying from a vendor is a valid timeskip outcome.
- [ ] Explore intent prefers the generation frontier. task-398 (deterministic
      scoped generation) is now `done`, but the timeskip `explore` step still
      consumes no frontier primitive, so this item is blocked on wiring rather
      than on the generator.

## Progress - 2026-09-24 (long spans)

`routes/timeskip_ops.py`:

- The request ceiling is now the engine's `timeskip.MAX_MINUTES` (10,080) instead
  of 1,440. A blocking span runs as day-sized chunks and the results are merged
  (`_merge_results`); an interrupt in a chunk ends the skip early and hands the
  last chunk's envelope back. The shared-world branch declares a soak order for
  the full span (the turn loop carries it), and `_declared_span` uses the same
  engine ceiling.
- Tests: `tests/test_timeskip.py` - a two-day world advance reports
  `elapsed_minutes == 2880`, and 20,000 minutes is still rejected with
  `max_minutes == 10080`.

Still open: vendor leisure buying, and explore-prefers-frontier. The **task-436
Energy resolution residual was deliberately not folded
in here**: its cause is still unidentified, two prior fixes failed, and without a
reproduction harness a third blind change risks the soak baseline. The next step
is a measurement harness, not another guess.

## Why

A timeskip is a span of simulated time. The three follow-ups this card defers
are the cases where a span has to resolve a *decision* rather than just an
elapsed duration: buying something from a vendor who is only present at the
destination, and heading toward a frontier that does not exist yet and must be
generated. The long-span half was the easy half; it was a ceiling and a chunking
strategy, and it landed in 2026-09.

## How

- **Long spans** landed: the request ceiling is the engine's
  `timeskip.MAX_MINUTES` (10,080) instead of 1,440, and a blocking span runs as
  day-sized chunks whose results are merged by `_merge_results`.
- **Vendor leisure buying** needs a purchase path in the `leisure` branch of
  `_policy_step`, which today calls `sim.take_action(player, served=set(),
  remaining=remaining)` and never touches a vendor or the inventory. The string
  "vendor" does not occur anywhere in `engine/timeskip.py` (0 hits).
- **Explore frontier** needs `_explore_step` to prefer a generation frontier.
  task-398 (deterministic scoped generation) is done, so the generator exists;
  what is missing is a frontier primitive the timeskip can consume.

## Steps to verify

1. Long span runs in day-sized chunks
   - expected: a request above 1,440 minutes and up to `timeskip.MAX_MINUTES`
     (10,080) is accepted, runs as day-sized chunks with their results merged,
     and reports `elapsed_minutes` equal to the span; anything above the
     ceiling is refused with `max_minutes == 10080`.
   - observed: PASS 2026-10-20 - `python -m pytest
     tests/test_timeskip.py::test_timeskip_route_runs_a_long_span_in_chunks` and
     `tests/test_timeskip.py::test_route_helpers_report_hop_duration` both
     passed (39 passed across the four targeted files in the same run).
     `engine/timeskip.py:39` still reads `MAX_MINUTES = 10080` and
     `routes/timeskip_ops.py:29` `_merge_results()` is the merge point.
2. Leisure buying from a vendor
   - expected: a leisure timeskip where the character is at a vendor with a
     valid item buys it; the purchase shows in the character's inventory and in
     the timeskip summary, and the event stream names it.
   - observed: NOT run live. Measured 2026-10-20: the `leisure` branch of
     `engine/timeskip.py:_policy_step()` (:493) is still
     `sim.take_action(player, served=set(), remaining=remaining)` at :500 and
     touches no vendor and no inventory. `rg -i vendor` over `engine/` returns
     0 hits, so there is no vendor concept in the engine to call.
3. Explore prefers the generation frontier
   - expected: when a frontier exists, the explore step prefers it and records
     the destination; when none exists, it does not invent one.
   - observed: NOT run live. Measured 2026-10-20: `engine/timeskip.py:_explore_step()`
     (:584) picks the first undiscovered exit and never references a frontier,
     a scope, a grid or a generator. task-398 (scoped generation) is done, but
     the timeskip consumes none of it.
4. The two open items are still open together
   - expected: neither the vendor path nor the frontier primitive exists, so
     both boxes above stay unchecked.
   - observed: CONFIRMED 2026-10-20 by the same two measurements; the card's
     surviving scope is exactly these two items.

## Files

- `engine/timeskip.py` - `INTENTS` (:37), `MAX_MINUTES` (:39),
  `_policy_step()` (:493, the `leisure` branch at :499-501), `_explore_step()`
  (:584), `per_hop_minutes()` (:634)
- `routes/timeskip_ops.py` - `MAX_REQUEST_MINUTES` (:26), `_merge_results()`
  (:29), `_requested_minutes()` (:52), `handle_timeskip()` (:79),
  `handle_soak_declare()` (:211)
- `engine/soak.py` - the soak-order carrier of the same intent, target and
  heading fields
- `engine/venues.py` - the existing "a character walks to the place that has
  it" mechanism (`VENUES` :55, `choose_venue()` :225), and the closest thing
  the engine has to a vendor; it has no `buy` venue and no purchase step
- `engine/background_simulation.py` - the venue caller (:1331-1342) that a
  vendor leisure step would sit alongside
- `engine/triggers/behaviors.py` - the existing `trade` action (:1064), which
  hands an item to another character; the closest thing to a purchase, and it
  moves no ownership
- `engine/generation.py` - `GenerationPatch` (:142) and `apply_patch()` (:172),
  the generation contract a frontier primitive must call
- `engine/world_compile.py` - the scoped grid compiler that produces the areas
  a frontier would name
- `engine/world_grid.py` - the painted grid a frontier cell lives in
- `tests/test_timeskip.py` - the long-span and explore regression, to extend

## Browser UI and intended live verification

Intended UI home: game play → request a timeskip → inspect the bounded progress/result summary and resulting character event/activity records. Vendor leisure and frontier exploration must remain visible as resolved outcomes, not silent background changes.

Current availability: long timeskips beyond 1,440 minutes are recorded as implemented in day-sized chunks. Vendor leisure and generation-frontier preference are still open; frontier preference is blocked on task-398.

Live steps when available:
1. Request a timeskip of more than 1,440 minutes but no more than one week and inspect progress and the final summary.
   - expected: the request runs in day-sized chunks, returns a bounded summary, and does not hold one synchronous advance for the full week.
2. Give a character leisure intent and a reachable vendor with a valid item; request a timeskip that includes leisure.
   - expected: buying from the vendor is a valid resolved outcome, visible in the character's inventory and the event summary.
3. After task-398 provides a generation frontier, request exploration from a character with frontier preference.
   - expected: the exploration choice targets the generated frontier when eligible and records the destination; it does not invent a frontier before one exists.
4. Compare the result with character inventory, location, and event history after reload.
   - expected: resolved purchases/travel persist once and match the timeskip summary.

## Reconnaissance (2026-10-20) - partly done, still open

Re-checked on 2026-10-20. The long-span box remains accurate: `engine/timeskip.MAX_MINUTES = 10080` (one week) and INTENTS = ("idle", "leisure", "search", "explore", "travel").

Still open:
- Leisure buying from a vendor: the `leisure` branch in `_policy_step` calls `sim.take_action(player, served=set(), remaining=remaining)` and never touches a vendor or inventory. No vendor-buy path in timeskip.
- Explore frontier preference: `_explore_step` does not reference any generation frontier; task-398 (scoped generation) is done but no frontier primitive is consumed here.

Verdict: long spans done; leisure-vendor and explore-frontier remain open. Card kept in todo with surviving scope.
