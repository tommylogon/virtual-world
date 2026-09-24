---
type: task
status: todo
area: gameplay
priority: medium
---

# task-482: Timeskip follow-ups: long spans, leisure vendors, explore frontier

**Filed:** 2026-09-23
**Related:** task-464; task-467; task-398

## Goal

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
