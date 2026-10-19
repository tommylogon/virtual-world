---
type: task
status: todo
area: testing
priority: medium
blocked_by: [task-401]
wiki: "[[Feature Map]]"
---

# task-402: Large-world projection and indexing benchmark

**Filed:** 2026-09-08  
**Depends on:** task-397. Extend after task-401 when real chunk loading exists.

<!-- deps:start -->
**Blocked by:** [[task-401-chunk-persistence-and-gateway-ways]]
<!-- deps:end -->

## What

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

Intended UI home: run the task's checked-in large-world benchmark command, open its generated scenario in the graph editor, select one scope, and inspect `/api/state`/scope responses in the browser Network panel.

Current availability: the task requires a repeatable command and checked-in baseline report but deliberately sets no universal performance threshold before host budget is chosen. The command and baseline are not claimed as present.

Live steps when available:
1. Run the benchmark command recorded by this task and open the generated world at whole-world and scoped settings.
   - expected: the report records world node/edge counts, requested-scope counts, response bytes, and elapsed measurements for the same fixture.
2. In the browser, select one small scope and inspect the graph request/response and visible node count.
   - expected: payload size is bounded to that requested scope; the response does not accidentally contain the whole-world graph.
3. Repeat the same command and browser request without changing the fixture.
   - expected: the checked-in baseline is reproducible within recorded host conditions and names the measurements rather than asserting an arbitrary universal speed target.
4. Compare the browser's visible graph with the report's scope node/edge counts.
   - expected: the displayed subgraph and response counts match the selected scope.

This section is not a claim that the benchmark command or baseline report exists today.
