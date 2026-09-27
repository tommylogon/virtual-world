---
type: task
status: todo
area: testing
priority: high
---

# task-572: Integration test layer

**Filed:** 2026-09-27
**Related:** 

## Goal

3239 unit tests, but NO integration or E2E layer: no save/load round-trip, no timeskip determinism, no trigger fan-out, no scope load/unload, no perf baseline. The unit tests are strong; the seams between systems are untested, and the seams are where the remaining bugs are. Add a harness covering at minimum: save/load round-trip preserving two same-named areas in different scopes (the task-446 defect), same-seed trace equality (the 17 bare random call sites), and a compiled-region generation benchmark (task-402).

## Acceptance

- TODO
