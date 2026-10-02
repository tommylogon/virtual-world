---
type: task
status: review
area: graph
priority: medium
---

# task-527: Graph steady-state performance on a large painted map (profile + fix)

**Filed:** 2026-09-26
**Related:** task-400 task-523

## Goal

With a compiled zone loaded in Map mode (physics off), the surrounding UI panels (scope picker, inspector, WorldPainter) become very slow. Backend endpoints measured fast (scope subgraph ~32ms/1.1MB, grid ~1ms), so the cost is browser main-thread work: building ~1k vis nodes/edges, and rendering their labels/edges. Node/edge generation itself is quick; the drag is steady-state. Profile with the browser Performance panel on a large scope, find the per-frame or per-interaction hot path (redraws, hover, relative-layout tick, afterDrawing sync, tooltips), and fix it. Label LOD (graphLabelMaxNodes/graphLabelMinScale) and the 🔤 Names toggle have landed and should be measured first. Note: an earlier hypothesis (GraphRelativeLayout's 120ms follow timer) was wrong and reverted - do not re-suspend it in grid mode, that strands coords-less items/characters at the origin.

## Acceptance

- TODO

## Resolved 2026-10-02 (wt/graph-render)

**Profile (before).** `kraktooth_goblin_camp` (658 nodes / 821 edges) on port
4464, Map layout, Chrome DevTools CPU profile (`Profiler.start/stop` via CDP)
over hover + wheel-zoom + pan:

- Idle was **~20fps**: 41 `requestAnimationFrame`s in 2s with **82
  `afterDrawing`** events — vis was redrawing non-stop.
- `network.physics.options.enabled === true`, `simulatorRunning === true`,
  `graphManager._physicsEnabled === true` **in Map mode**.
- Interaction profile: 19178 samples; 75.6% in vis's canvas draw
  (`value @ vis-network.min.js:33`), `fill`/`stroke`/`save`/`clearRect` next.
- Forced `loadGraphData()` rebuild: 1026 / 1726 / 2066 ms.

**Root cause.** `GraphManager.toggleCardinalLayout()` set
`this._physicsEnabled = true` (and persisted it) on **entering Map**, and
`loadGraphData` restores physics when that flag is set (network-manager.js
~711). So Map ran the solver continuously on 658 nodes, which forced a redraw
every physics tick and starved the inspector / scope picker / WorldPainter —
exactly the steady-state drag reported. (It also let nodes drift off the painted
cells, the drift task-618's edge fix had to compensate for.)

**Fix** (`static/js/graph-manager.js`): entering Map now defaults physics
**off** (`this._physicsEnabled = !this._cardinalLayout`) and no longer persists
that mode-default; Graph mode re-enables it. An explicit toolbar toggle still
wins and is what gets persisted, so a reload starts in Graph with the user's own
preference. The painted lattice already owns positions; the derived relative
layout still seeds coordinate-less items (verified separately — 52 orphans, 0 at
the origin, both layouts).

**Profile (after).**

| metric | before | after |
|---|---|---|
| idle rAF frames / 2s | 41 (~20fps) | 117 (~58fps) |
| idle `afterDrawing` / 2s | 82 | 19 |
| map `physicsEnabled` | true | false |
| interaction CPU samples | 19178 | 5191 (−73%) |
| forced `loadGraphData()` (median) | ~1.7s | ~0.9s |

The remaining 19 redraws/2s are the deliberate `GraphRelativeLayout` follow
timer; the task's warning not to suspend it in grid mode is respected. JS unit
tests: 486 passed / 0 failed.
