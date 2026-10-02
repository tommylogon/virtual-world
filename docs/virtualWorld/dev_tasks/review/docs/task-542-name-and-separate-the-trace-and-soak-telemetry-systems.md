---
type: task
status: review
area: docs
priority: medium
---

# task-542: Name and separate the `lived_log` and soak telemetry systems

**Filed:** 2026-09-27
**Related:** task-543 (telemetry capture), task-544 (space-time view), task-537

## Problem

There are **two different record systems** in this codebase and they are not the
same thing, but nothing says so. The result is that merging them looks entirely
reasonable — and someone already has.

The load-bearing evidence is one line. `docs/design/trace-format.md` lists the
trace's purposes as:

> - first-person **memory** (the LLM summarizes a trace window into memory),
> - **"what have you been up to?"** when you click a background character,
> - **reversibility** on promote/demote,
> - and debugging long runs (an auditable objective record).

Three of those are the fidelity-boundary system's job. The fourth — "debugging
long runs" — is a *soak* concern, and it is the one that invites the merge.
Because it is also **true** (a trace genuinely is useful for debugging), the merge
looks harmless. It is not: a trace and a soak want opposite fidelity.

## The two systems

| | `lived_log` (today: `trace`) | soak telemetry (does not exist) |
|---|---|---|
| scope | per **character** | per **run** |
| stored | **in the save**, on the player | **out of the save**, on the run |
| grain | salience-filtered, runs collapsed | complete, every move |
| test applied | "a person would remember this" | "measure exactly this" |
| lifetime | ~200 entries, rolled up | the whole run, then archived |
| consumer | LLM summarisation on promote/demote | dashboard, export, benchmark |
| if it leaks | an LLM "remembers" a life it never lived | the benchmark becomes fiction |

The rollup that makes the trace *good* for memory is precisely what destroys it
for measurement. That is not a tuning difference — the two requirements are
incompatible, which is why they cannot be one store.

## What is already correct (do not "fix" it)

Verified 2026-09-27 — the code separates these properly today:

- `engine/serialization.py` treats `soak_order` as **transient**, explicitly not
  part of the save.
- `engine/soak_runner.py` only *counts* `len(trace_log)` for a summary statistic.
  It never writes to it.
- `engine/promotion.py` is the memory half of the seam, and it is careful: it
  stamps boundary ticks so foreground actions between two background spans are
  never summarised, and its own contract says a later LLM pass may only *read*
  the trace.

So the merge has not happened yet. This task is about making the boundary
**legible**, not about repairing damage.

## Naming

The rule: **each name must say its own retention and ownership in one word**, so
the wrong store is obviously wrong at a call site.

| | rename to | because |
|---|---|---|
| `player.trace_log` / `engine/trace.py` | **`lived_log`** / `engine/lived_log.py` | it is what was *experienced*, and it is bounded precisely because nobody remembers every minute |
| new soak store | **`telemetry`** | instrumentation of a running system; not narrative by definition |

**Why the rename is worth it.** `trace` is the word that invited this merge — it
is the word in "an auditable objective record" and "debugging long runs", sitting
in the same list as memory. `lived` is the word that prevents it, and it already
pairs with the vocabulary the format doc already uses (memory is "subjective",
the record is "objective"). It also makes the granularity asymmetry
self-documenting: *"why does this only keep 200?"* answers itself — because it is
lived, and nobody remembers every minute. Under `trace`, the same question
invites "just raise the cap", which is how this conversation started.

`trace` is additionally an overloaded word in Python (the stdlib `trace` module,
`traceback`), and this repo already imports `traceback` in `soak_runner.py`.

**Cost:** ~29 references — `trace_log` in 8 files, `engine.trace` imports in 10,
and 11 references to `trace-format.md`. A mechanical rename plus a doc title
change.

**Zero-churn fallback:** keep `trace`, name the new store `telemetry`, and write
the boundary doc. `trace`/`telemetry` is contrastive enough. Take this option
only if the rename lands in a batch that is already touching those files.

## One naming collision to note

`docs/design/presence-gap-analysis-2026-08.md` has a heading "Presentation is
telemetry, not scene" — using *telemetry* for UI instrumentation. Different
domain, so not a blocker, but the word would then carry two senses. Either add a
line to that doc distinguishing them, or retitle it to "instrumentation".

## Acceptance criteria

- [x] `trace_log` → `lived_log` (or the fallback is taken and documented), with
      every reference updated including the deserialiser, so **old saves still
      load**. `engine/trace.py` `load()` must accept the old key.
- [x] `docs/design/trace-format.md` → a doc named for the new system, with the
      purposes list corrected: the trace serves **debugging within its retention
      window**, and a soak's telemetry is a **separate store owned by the run**.
- [x] **`t` → `tick`, decided 2026-09-27 — do it.** The entry schema uses a word
      for every field except the tick, which is `t`. It is the one cryptic key in
      an otherwise readable format, and task-543 is deliberately not inheriting it
      (new telemetry uses `tick` / `from_tick` / `to_tick`). Reviewer: rename it,
      migrations dealt with afterwards if needed.
      The change itself is small — **7 sites in 3 files**, measured:
      `engine/trace.py` writes the key twice (`record`, `rollup`) and reads it
      three times (`_trim`'s sort, `since`, `summarize_window`);
      `engine/promotion.py` reads it once; `docs/design/trace-format.md`
      documents it.
      **One trap, and it makes the back-compat fallback load-bearing rather than
      polish.** `engine/trace.py` `load()` does
      `player.trace_log = [dict(e) for e in data]` — it copies entries verbatim,
      so entries from old saves keep the key `t` and are *not* rewritten. If the
      readers become `.get("tick", 0)` and nothing else, every old entry silently
      reads as **tick 0**: `rollup`'s sort scrambles them and `since(since_tick)`
      stops finding them. That is silent data corruption, not a load error, so
      nothing would fail loudly. Hence: `load()` must read both keys
      (`{"tick": e.get("tick", e.get("t"))}`) in the same change. It is a few
      lines and cheaper to add while the code is open than to reconstruct later.
      Reviewer's note was "rename it, deal with migrations afterwards if need be"
      — agreed on the rename, but the `load()` shim is the one piece that should
      not be deferred, because the failure mode is invisible.
      A third, unrelated `t` exists: `engine/soak_runner.py` stores `"t"` as
      **elapsed wall-clock seconds** in its run-level event log. That is a
      different store with a different unit, and renaming it is task-543's
      business, not this task's.
- [x] The corrected doc states the one-way rule explicitly and unmissably:
      **telemetry is never written to a `lived_log`**, and the `lived_log` is
      never the dashboard's data source. If you want "what happened" in a soak,
      derive it from telemetry.
- [x] A short section records *why* they are separate, so the next reader
      understands the incompatibility rather than just the rule. Rules without
      reasons get "optimised" away.
- [x] `engine/promotion.py`'s memory bridge is unchanged, and its tests still
      pass — this task renames, it does not alter the seam.
- [x] Per the standing rule, documented in code comments as well as the doc.
- [x] Full suite compared against the baseline.

## Non-goals

- Building the telemetry store — that is task-543.
- Building the view — task-544.
- Changing what the `lived_log` records or how it rolls up. This is a rename and
  a boundary, nothing else.
- Deciding the telemetry `why` vocabulary. Deliberately left to task-537's notes
  so it is decided before capture, not after.

## Verification pass (2026-10-02)

Re-checked the rename end to end. `engine/lived_log.py`,
`engine/soak_telemetry.py`, `docs/design/lived-log-format.md` and the
`lived_log` save key all exist; `engine/trace.py` and
`docs/design/trace-format.md` do not. Two stale path references survived the
rename and are now fixed:

- `engine/promotion.py:15` docstring pointed at `engine/trace.py` ->
  `engine/lived_log.py`.
- `engine/background_simulation.py:22` docstring pointed at
  `docs/design/trace-format.md` -> `docs/design/lived-log-format.md`.

Targeted run: `python -m pytest tests -k "lived_log or promotion or soak_telemetry"
--ignore=tests/test_tick_time_scaling.py` -> 51 passed, 1 failed. The failure,
`test_promotion.py::test_observe_route_queues_residents_and_404s_unknown_scope`,
is on the repo's known pre-existing baseline (AGENTS.md), and the edits here are
docstring-only. Full-suite A/B was not re-run for a path-only change.
