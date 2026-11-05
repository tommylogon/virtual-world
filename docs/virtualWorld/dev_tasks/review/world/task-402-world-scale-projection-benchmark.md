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

Every scale claim in this repo is currently an assertion. The world compiler
is written to handle scopes and chunks, the projection layer is written to
return a subgraph rather than the whole graph, and the frontend is written to
sync only what changed. None of that has been measured against a world large
enough to break it, and the failure mode is the quiet one: a scoped endpoint
that keeps returning the whole graph is *correct* and *slow*, and it will not
throw.

That is why the card exists as a separate deliverable from the scaling work
itself. A passing vertical slice - task-400's Pines - proves *user semantics*:
a character can walk into a room that was generated, a task can be completed in
a scope that was compiled. It says nothing about transport, memory, or
asymptotic behaviour, because the slice is small enough that the whole graph
fits in the response comfortably. The claim "VirtualWorld supports a
million-node world" is currently supported by a slice three orders of magnitude
smaller than that.

The card's own framing is careful about what it does *not* promise: it sets no
arbitrary universal performance target before the host budget is known. What
it does require is bounded-payload behaviour and a guardrail that catches
accidental whole-graph responses. That is the difference between a benchmark
and a performance target, and it is the part that can be built now.

## How

Two pieces, and the first is the blocker for the second.

1. **A deterministic synthetic world generator.** Not a browser render test - a
   fixture generator for tests and tools that produces at least 100,000 nodes
   across many scopes, with areas, ways, ordinary items and a small number of
   characters. Fixed seeds, published fixture counts in the output, so a run is
   comparable with a later run. It must be expandable toward a million nodes
   *without changing test semantics*, which means the generator's scope layout
   has to be parameterised from the start rather than hard-coded to a shape.
   task-572 (review) already records that this generator is **not** part of
   its scope: *"Not done here: task-402's >=100k-node synthetic generator"* -
   so this card still owns it, and task-572's E2E harness is the thing it can
   grow from.

2. **The measurement pass**, run as an explicit benchmark or marked test, never
   in the ordinary unit suite, and never calling an external LLM:
   - projection endpoint payload size and response time at world, settlement
     and building scope depths;
   - the number of nodes and edges actually loaded or returned per request;
   - index lookup versus full-edge-list scan for scope-local queries;
   - memory use and elapsed time for the save/load or chunk-load operations
     that exist at the time of the test;
   - confirmation that the browser does not request or render the complete
     fixture when navigating a small scope.

3. **The guardrail.** A benchmark must fail loudly if a scoped endpoint returns
   out-of-scope graph nodes, *even if its latency happens to be acceptable*.
   This is the assertion that carries the weight, and it is the one that turns
   a measurement into a regression test. A slow endpoint is a performance
   problem; an endpoint that quietly returns the whole graph is a correctness
   problem wearing a performance costume, and only the out-of-scope assertion
   catches it.

**Sequencing.** This card is `blocked_by: task-401`, and that ordering is
right. Without real chunk loading, a scoped projection is being measured
against a graph that is fully resident, which measures the wrong thing. The
sub-cards task-581/582/583/584 are the chunk work; the benchmark becomes
meaningful when they land.

## Files

- `tools/` - where the deterministic generator belongs, alongside the other
  scenario and world-building tools; it must be runnable without the browser
- `tests/` - the benchmark harness, marked so it does not run in the ordinary
  unit suite
- `engine/world_grid.py`, `engine/world_compile.py` - the scope and chunk
  substrate the fixture has to exercise realistically
- `routes/` - the projection endpoints whose payload size and node counts are
  the primary measurement
- `docs/design/` - where the checked-in baseline report lands, so a later run
  can be compared against it

## Steps to verify

1. Generator
   - expected: Deterministic generator produces >=100000 nodes across scopes with fixed seed.
   - observed: Not implemented; task-572 notes generator not done.
2. Measurements
   - expected: Report records payload sizes/times/index performance/memory for scoped requests; guardrail catches out-of-scope nodes.
   - observed: Not run; benchmark not implemented.
3. Reproducibility
   - expected: Repeatable command produces same baseline within host conditions.
   - observed: Not implemented.

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


## Reconnaissance (2026-10-20)
- Measured: blocked by task-401 (todo). No benchmark script/baseline found in quick scan.
- Verdict: STILL_VALID. Blocked and not implemented. Status remains todo.
