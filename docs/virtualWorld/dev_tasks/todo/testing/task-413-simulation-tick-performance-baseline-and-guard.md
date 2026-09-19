---
type: task
status: todo
area: testing
priority: medium
---

# task-413: Simulation tick performance baseline and regression guard

**Filed:** 2026-09-19  
**Depends on:** task-406, task-407 (the fixes this guards).  
**Related:** task-402 (world-scale projection benchmark) — different layer.

## Goal

Make per-tick simulation throughput measurable and protect it against
regressions.

## Problem

The hot-path cost was only discovered by profiling (trigger/exit plumbing, not
LLM). task-402 benchmarks **projection payload**, not the per-tick simulation
loop, and there is no committed baseline for ticks/sec, per-tick node/edge
visits, exit rebuilds, or `.lower()` calls.

## Changes

1. A repeatable benchmark command (extend `tools/soak_sim.py` or add
   `tools/bench_ticks.py`) that prints, with a fixed seed and scenario:
   ticks/s, nodes/edges visited per tick, exit rebuilds, `.lower()` calls, and
   character count.
2. A checked-in baseline report (date, host, counts).
3. A **marked** test that fails loudly when a scoped hot path regresses past an
   agreed factor.

## Acceptance

- One documented command reproduces the numbers.
- The baseline is published in the report.
- The guard fails on a deliberately reverted fix (prove it bites), then passes
  again when restored.
- It is not part of the ordinary unit suite; it runs explicitly.

## Non-goals

- Universal wall-clock targets before a host budget is chosen.
- Browser rendering benchmarks.

## Verification

- Run the command before/after task-406/task-407 and record the delta.
- Temporarily revert one fix to confirm the guard trips.
