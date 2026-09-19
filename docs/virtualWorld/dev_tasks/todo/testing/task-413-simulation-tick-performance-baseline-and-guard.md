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

## Baseline — 2026-09-19 (after tasks 406/407)

- Command: `python tools/soak_sim.py --ticks 10080 --background-all --progress-seconds 1`
- Result: **10,080 ticks (7 in-game days) in 9m49s → 17.1 ticks/s**, 23/23 alive,
  0 deaths. Trace 4,459 entries; memories 17; graph 130 nodes.
- Pre-fix reference: ~6–9 ticks/s, with the trigger/exit path responsible for
  ~187s of 247s in a 100-tick profile (~876 exit rebuilds and ~1M `str.lower()`
  per tick).
- Post-fix profile top costs: `lighting.get_ambient_light` (trimmed),
  `get_edges_for_target` call volume, background `move_to_area`,
  `Player.state`. The trigger/exit cost is gone from the hot path.
- Full suite: 2831 passing (0 failures) excluding pre-existing `test_mcp_*`.

Follow-ups spotted by the profile (candidates for a next pass): memoise
`_item_light_stats`/`get_ambient_light` with explicit lit-state invalidation,
reduce `Player.state` cost, and stop `remove_edge` from triggering a full edge
index rebuild.
