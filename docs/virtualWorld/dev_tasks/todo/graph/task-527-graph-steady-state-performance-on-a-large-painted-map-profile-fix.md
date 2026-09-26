---
type: task
status: todo
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
