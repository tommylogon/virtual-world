---
type: task
status: todo
area: gameplay
priority: medium
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
- [ ] Explore intent prefers the generation frontier (blocked on task-398, which
      is still `todo`, so there is no frontier primitive to prefer yet).

## Progress — 2026-09-24 (long spans)

`routes/timeskip_ops.py`:

- The request ceiling is now the engine's `timeskip.MAX_MINUTES` (10,080) instead
  of 1,440. A blocking span runs as day-sized chunks and the results are merged
  (`_merge_results`); an interrupt in a chunk ends the skip early and hands the
  last chunk's envelope back. The shared-world branch declares a soak order for
  the full span (the turn loop carries it), and `_declared_span` uses the same
  engine ceiling.
- Tests: `tests/test_timeskip.py` — a two-day world advance reports
  `elapsed_minutes == 2880`, and 20,000 minutes is still rejected with
  `max_minutes == 10080`.

Still open: vendor leisure buying, and explore-preferences-frontier (blocked on
task-398). The **task-436 Energy resolution residual was deliberately not folded
in here**: its cause is still unidentified, two prior fixes failed, and without a
reproduction harness a third blind change risks the soak baseline. The next step
is a measurement harness, not another guess.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

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

This section is not a claim that the remaining timeskip outcomes are implemented today.
