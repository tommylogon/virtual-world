---
type: task
status: review
area: testing
priority: medium
---

# task-543: Soak telemetry — presence intervals and action stream capture

**Filed:** 2026-09-27
**Related:** task-542 (naming/boundary), task-544 (the view), task-537 (`why` vocabulary)

## Problem

A soak run currently cannot answer **"who did what, where, and when"** — not
because the data is too big, but because it is never written down. The
information is collapsed at write time and cannot be recovered by recording more.

What the soak runner keeps today (`engine/soak_runner.py`):

- **samples** — per tick, *aggregate* vitals only (`avg`/`min`/`max` across the
  cast). No actions, no areas, no per-character presence.
- **events** — run-level milestones (deaths, promotions) with wall-clock time.
- **character_series** — per-character *vitals* over time.

The per-character record (`lived_log`, task-542) has `area`, `kind` and `why` —
but it is capped at ~200 entries and rolled up, which is correct for its purpose
and destroys it for this one. So a seven-day run **cannot** be replayed as
occupancy even at a million entries: the data is gone.

## Measured: this is not a memory problem

A `lived_log` entry is **189 B as JSON but 1,106 B in Python** — a 5.8×
object-graph overhead (dict, eight strings, list). So volume is the thing people
intuit wrongly about. Actual costs:

| what | size |
|---|---|
| busy character, 30 days of `lived_log` entries (3,600) | 3.8 MB |
| typical character, 30 days (1,350) | 1.4 MB |
| 999,999 entries × 1 character | 1.0 GB |
| 999,999 entries × 68 library characters | 70 GB (12 GB as JSON) |

The 999,999 figure is a non-starter, but only because it is arbitrary. The
**real** requirement is far smaller than it looks, because of the data structure.

## Design: presence intervals, not samples

Record **one line per area change**, not one line per tick:

```json
{
  "character": "Jake",
  "area": "Kraktooth Camp, Storehouse",
  "from_tick": 41200,
  "to_tick": 41480
}
```

The cost is therefore bounded by **moves**, not ticks, and it renders at any
zoom — a swimlane at one-minute resolution and a whole week at hourly resolution
are the same records. Sampling per tick cannot do that: a 7-day soak at
1 min/tick is 10,080 samples per character per tick-axis, and any stored
subsample is a permanent loss of resolution.

At 120 moves/day/char × 7 days × 20 characters = 16,800 intervals ≈ **1.9 MB**.
That is the same order as a 30-day `lived_log` and about 11,000× smaller than the
999,999 proposal. **Memory is not the constraint; resolution is.**

Also worth capturing, at the same event-driven moment:

- **state crossings** — condition gained/lost, vital tier crossings. Event-driven,
  so cheap.
- **deaths** with cause, and the tick they occurred on.

The action stream needs one more design decision than the others, and it is
settled below: what `why` means in telemetry is not the same as what it means in
the `lived_log`, and that has to be decided *before* capture rather than
discovered by a dashboard.

## `why` — decided, settled in task-537

Telemetry **carries `why`**, because it is the core of the view task-544 exists
to serve: *who did what, why, where.* Without it the run can only report "Jake
moved 47 times", which is not a finding.

The vocabulary is **reused from the `lived_log`**, with two rules:

- Keep `needs:` / `goal:` / `plan:` / `social:` / `threat:` / `order:` / `env:`,
  **closed and prefix-groupable**, so `plan:provision` and `plan:patrol` bucket
  under `plan:*` and a bar chart can rank the rules.
- **Exclude `llm:`** — see below.

In the `lived_log` `why` is diagnostic prose (help a reader or an LLM understand a
life). In telemetry it is the measurement. Same field, different job, which is why
it has to be a grouping key here and need not be one there.

**Why `llm:` is excluded, structurally.** A soak makes no LLM calls by
construction: `engine/soak_runner.py` says so in its own docstring, and
`background_all` forces every character to `simulation_mode = "background"`. A
soak is the measurement of the *deterministic* tier, so an LLM reason is
impossible, not merely rare. Keeping it would leave a permanently empty category
that invites "why is this always zero?" every time someone reads the breakdown.

This makes reuse nearly free — telemetry uses a **strict subset** of a vocabulary
that already exists, so there is one writer and no drift.

## Two record shapes, one recorder

The dashboard's quadruple needs two different things, and they are genuinely
different rather than redundant:

- **Presence intervals** — *state* over time: `character`, `area`, `from_tick`,
  `to_tick`. A character sitting in a room for six hours produces **one** interval
  and no further events, so this is the only way occupancy is knowable. This is
  the swimlane substrate.
- **Events** — *transitions*: `character`, `kind`, `what`, `why`, `area`, `tick`.
  What was done, and why. A character that never moves still eats, sleeps and
  gets ill.

A move emits both at the same instant. One recorder, two projections — not two
independent writers that can drift.

**Field names are words.** `character`, not `c`; `from_tick` / `to_tick`, not
`f` / `t`. Longer keys cost nothing measurable — the cost is the ~5.8× Python
object-graph overhead, and single-character strings are interned singletons
anyway — so there is no trade-off to make. Readability is free here, so take it.

One inconsistency to close: the `lived_log` format uses `t` for the tick, and
`trace-format.md` uses words for all seven of its other fields. Telemetry should
not inherit the odd one out. Whether `lived_log`'s `t` becomes `tick` is a
migration on an already-shipped format, so it belongs with task-542's rename
rather than here — but it should be decided, not left as the one cryptic key in
an otherwise readable format.

## Boundaries (from task-542)

- **Owned by the run.** Not on the player, not in the save, discarded with the run.
- **Never written to `player.lived_log`.** If telemetry reached the memory bridge,
  promoting a soak character would summarise *measurement data* as lived
  experience. `engine/promotion.py` already refuses to let the wrong span into a
  memory summary; a soak is a far bigger wrong-content source.
- **Retention:** a hot window in memory for the live dashboard, plus an
  append-only JSONL on disk for the full run. Reading a 7-day audit should never
  be gated on what fit in RAM.

## Acceptance criteria

- [x] A run exposes, per character, the ordered presence intervals covering the
      whole run with no gaps and no overlaps.
- [x] Intervals are emitted on **area change**, not per tick — proven by asserting
      the record count scales with moves, not with run length.
- [x] Action and condition-crossing events are captured with the agreed `why`
      vocabulary — reused prefixes, closed set, no `llm:` — and the agreement is
      recorded in code comments and asserted by a test that rejects an unknown tag.
- [x] Telemetry is reachable through the soak API and is **absent from a save** —
      assert that a save taken after a soak round-trips without it.
- [x] `player.lived_log` is byte-identical before and after a soak, proving the
      capture does not touch it.
- [x] Memory stays flat as run length grows; a 7-day and a 30-day run at equal
      move-rate differ by the interval count only.
- [x] The full run is exportable as JSONL independent of what is held in memory.
- [x] Per the standing rule, documented in code comments and the technical docs.
- [x] `python tools/tasks.py validate` clean.

## Non-goals

- The visualisation — task-544.
- Renaming anything — task-542.
- Recording **everything** per tick. Full-fidelity per-tick capture is the thing
  that made this look expensive; the interval structure is what makes it cheap.
  Per-tick detail is available where it already exists (the vitals samples).
- Changing what the soak *measures* about survival. This adds an orthogonal
  stream, it does not alter the existing summaries.
