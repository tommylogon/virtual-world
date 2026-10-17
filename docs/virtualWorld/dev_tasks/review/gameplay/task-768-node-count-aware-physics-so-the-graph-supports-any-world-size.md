---
related: [task-437]
type: task
status: review
area: gameplay
priority: medium
---

# task-768: Node-count-aware physics so the graph supports any world size

**Filed:** 2026-10-10
**Related:** 

<!-- deps:start -->
**Related:** [[task-437-turn-order-source-of-truth-and-modes]]
<!-- deps:end -->

## What

The solver constants are tuned to one world of about 638 nodes. Physics must scale: disable or switch to a static/saved layout above a node-count threshold so a 10-node scene and a very large world both behave. The graph layer must not assume a few hundred nodes.

## Why

TODO

## How

`GraphNetwork.PHYSICS_NODE_LIMIT` (8000) is a **safety valve**, checked in
`applyModePhysics` and `buildOptions` via `nodesOverPhysicsLimit()`. Above the
limit physics is forced off regardless of the user's setting; below it the
user's default-on physics is untouched. This stops the "1M nodes" catastrophe
without changing normal worlds.

This is deliberately a valve, not full scaling. A larger world still needs a
rendering strategy vis-network cannot give for free (clustering, LOD, culling) —
that remains open and is a separate, bigger effort.

## Progress (2026-10-10)

Implemented: `PHYSICS_NODE_LIMIT` + `nodesOverPhysicsLimit()`, folded into
`applyModePhysics` and `buildOptions`. **Adjustable** via the
`graph_physics_node_limit` config key (default 8000), so a big world can be
re-enabled deliberately. Live check: 2763-node camp → limit 8000, `over=false`,
physics still on (user's default preserved). Still open: a *visible* indicator
when physics is auto-suppressed, so it is never silent.

## Steps to verify

1. Load a world with > 8000 nodes.
   - expected: physics off automatically; graph still renders.
   - observed: valve present (not yet exercised at scale).
2. Load a normal world (< 8000).
   - expected: physics on, per the user's setting.
   - observed: 2763 nodes → physics on. OK.

## Acceptance

- [ ] Above the limit, physics is off; below it, honored.
- [ ] The threshold is documented as a valve, not a tuned constant.

## Files

- `static/js/graph/network-manager.ts` (`PHYSICS_NODE_LIMIT`,
  `nodesOverPhysicsLimit`, `applyModePhysics`, `buildOptions`)

