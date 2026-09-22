# Bug 36 — `moveNode` called for nodes not in the DataSet: console spam + silent layout-restore failure

**Status:** Done — fixed 2026-09-22.

## Found

Two loops restore a saved position snapshot and call `network.moveNode(id, x, y)`
for **every** id in the snapshot, with no check that the node still exists in the
current DataSet:

- `static/js/graph/graph-background.js` `_applyPositions`, called from
  `setLocked(true)` and `_onWorldRefetched()`.
- `static/js/graph/focus.js` `_unCluster`, replaying `GraphFocus._savedPositions`
  (a snapshot of all nodes taken when the cluster was formed).

vis-network's `NodesHandler.moveNode` **logs** the problem rather than throwing,
so the `try { net.moveNode(...) } catch (e) { /* node gone */ }` wrapper never
silenced it, and `focus.js` had no guard at all. The snapshots can contain ids no
longer in the rendered node set — after a world refetch, a projection change, or
a filtered view.

## Fix (2026-09-22)

Both loops now filter against the live DataSet before moving, matching the
already-correct `network-manager.js` pattern:

- `graph-background.js:_applyPositions` builds
  `new Set(net.body?.data?.nodes?.getIds?.() || [])` and skips absent ids.
- `focus.js:_unCluster` does the same for `_savedPositions`.

`network.body?.data` is optional-chained, so it is safe before init. The move is
skipped rather than wrapped, because the failure is a `console.error`, not an
exception.

## Verification

- `npm run lint` and `npm run typecheck` clean.
- Manual: open the goblin camp, lock the background layout, trigger a world
  refetch and a cluster/un-cluster → no `moveNode does not exist` lines; positions
  still restore for present nodes; cluster round-trip returns nodes to prior
  positions.
