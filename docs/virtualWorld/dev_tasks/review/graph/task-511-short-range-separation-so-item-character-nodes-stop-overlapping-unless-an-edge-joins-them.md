---
type: task
status: review
area: graph
priority: medium
---

# task-511: Short-range separation so item/character nodes stop overlapping unless an edge joins them

**Filed:** 2026-09-24
**Related:** task-485

> **Narrowed (2026-10-01).** The module and its settings are unchanged and still run, but it is now a
> **seed pass only**: it de-overlaps the ring `layoutPositions` derives. The live half is gone — the
> acceptance items below about `follow()` running a pass and about smoothed live easing no longer
> describe the code, because contents are in the vis solver again (`centralGravity: 0`, see the
> task-485 supersession note) and ordinary repulsion is what keeps them apart. Measured after that
> change on kraktooth_goblin_camp: **0** content pairs overlapping, contents a median 134 px from
> their room. The rationale in the Goal below ("the global solver is not the answer") was true when
> written and is now false — it was `centralGravity`, not the solver, that was the problem.

## Goal

Items/characters piled into a room and nested containers layered on top of the
items around them, so the graph was hard to read. The global solver is not the
answer (task-485: its `centralGravity` is a graph-wide field that drags children
to the middle). Give contents a bounded **short-range separation** instead: a node
no edge joins is pushed off its neighbours, and pairs are ignored beyond a max
distance so the pass stays cheap.

## Acceptance

- [x] `static/js/graph/separation.js` (`window.GraphSeparation`) resolves overlaps: a pair closer than `min` pushes apart, a pair joined by **any** edge is exempt, and a pair further than `max` is ignored.
- [x] Areas and ways are anchors and never move; a frozen node keeps its place; only anchored children are nudged live.
- [x] Bounded and deterministic: a uniform grid keyed by `max`-sized cells makes it ~linear, ids are walked in sorted order, coincident nodes split on a fixed axis, and total displacement is capped.
- [x] `layoutPositions` applies it when enabled, and `follow()` runs one live pass after a parent actually moved, folding the result into the offsets so the next tick reproduces it.
- [x] Settings: `graph_repel_enabled` (default on), `graph_repel_min` (default 55), `graph_repel_max` (default 220), `graph_repel_strength` (default 0.6), `graph_repel_pull` (default 0.12), with a **Separation** group in the graph settings tab.
- [x] The **Parent Pull** restoring force only acts on nodes repulsion displaced and pulls them back to their own ring position (never the parent's centre, which would suck a crowded node onto its parent), without shrinking rooms that are not crowded.
- [x] Live separation is **smoothed**: a damped velocity eases a displaced node toward its resolved spot, pumped at frame rate while in flight, and the node is dropped from the easing once its speed and gap fall below the settle floors — so the motion eases in and stops instead of snapping or jittering.
- [x] `tools/unit/test_separation.js` covers push-apart, edge exemption, the max cutoff, anchors, frozen nodes, determinism, radii, the enable flag, the parent pull, and the `layoutPositions` integration.

## Files Changed

- `static/js/graph/separation.js` (new)
- `static/js/graph/relative-layout.js`
- `static/js/config.js`
- `static/js/ui/settings-view.js`
- `templates/index.html`
- `tools/unit/run.cjs`, `tools/unit/test_separation.js` (new)
- `docs/virtualWorld/World Building/Graph System.md`, `docs/design/js-module-index.md`

