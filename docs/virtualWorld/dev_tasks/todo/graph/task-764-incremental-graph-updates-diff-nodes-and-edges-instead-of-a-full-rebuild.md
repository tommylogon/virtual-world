---
type: task
status: todo
area: graph
priority: high
---

# task-764: Incremental graph updates: diff nodes and edges instead of a full rebuild

**Filed:** 2026-10-10
**Related:** 

## What

When a node or edge is added, removed, or retargeted (a character moving area changes its IN edge target), update the vis.js DataSet via nodes.update/edges.update and DataSet add/remove instead of nodes.clear() plus network.setData() rebuilding every node and edge. The structural diff feeds incremental updates so the solver eases the change instead of re-simulating the whole graph.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO
