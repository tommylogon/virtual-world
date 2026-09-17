---
type: task
status: todo
area: testing
priority: medium
---

# task-402: Large-world projection and indexing benchmark

**Filed:** 2026-09-08  
**Depends on:** task-397. Extend after task-401 when real chunk loading exists.

## Goal

Prove the scale claims with generated fixture data before treating a
million-node world as supported. A passing Pines slice proves user semantics;
it does not test transport, memory, or asymptotic behavior.

## Benchmark fixture

Build a deterministic synthetic world generator for tests/tools, not a browser
render test. It should create at least 100,000 nodes across many scopes with
areas, ways, ordinary items, and a small number of characters. It must support
later expansion toward one million nodes without changing test semantics.

## Measurements

- Projection endpoint payload size and response time at world, settlement, and
  building scope depths.
- Number of nodes/edges loaded or returned for every request.
- Index lookup versus full-edge-list scans for scope-local queries.
- Memory use and elapsed time for save/load or chunk-load operations that are
  actually implemented at the time of the test.
- Confirmation that the browser does not request/render the complete fixture
  when navigating a small scope.

## Guardrails

- Run this as an explicit benchmark/marked test, not the ordinary unit suite.
- Use fixed seeds and publish fixture counts in the output so regressions are
  comparable.
- Do not call external LLMs.
- A benchmark must fail loudly if a scoped endpoint returns out-of-scope graph
  nodes, even if its latency happens to be acceptable.

## Acceptance

The task produces a repeatable command and a checked-in baseline report. It
does not set arbitrary universal performance targets before the host budget is
chosen, but it must establish bounded-payload behavior and catch accidental
whole-world graph responses.

