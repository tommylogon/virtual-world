# Bug 36 — `moveNode` called for nodes not in the DataSet: console spam + silent layout-restore failure

**Status**: Todo — filed 2026-09-20 from browser console (live camp session).

## Found

Two loops restore a saved position snapshot and call
`network.moveNode(id, x, y)` for **every** id in the snapshot, with no check
that the node still exists in the current DataSet:

- `static/js/graph/graph-background.js:544-552` (`_applyPositions`), called from
  `setLocked(true)` (`:557`) and `_onWorldRefetched()` (`:741`).
- `static/js/graph/focus.js:220-226` (`_unCluster`), replaying
  `GraphFocus._savedPositions`, which is a snapshot of all nodes taken when the
  cluster was formed (`:196`).

Observed console output (every node in the camp graph, areas + items + ways +
players):

```
NodesHandler.js:568 Node id supplied to moveNode does not exist. Provided:  area_abandoned_farm
NodesHandler.js:568 Node id supplied to moveNode does not exist. Provided:  item_berries
NodesHandler.js:568 Node id supplied to moveNode does not exist. Provided:  player_Gribba
... ~90 entries per restore
```

## Cause

vis-network's `NodesHandler.moveNode` **logs** the problem rather than
throwing, so the `try { net.moveNode(...) } catch (e) { /* node gone */ }`
wrapper at `graph-background.js:550` never silences it, and `focus.js:226` has
no guard at all. The snapshots (saved layout, positions loaded from the
IndexedDB record at `:160`, or `_savedPositions`) can contain ids that are no
longer in the rendered node set — e.g. after a world refetch, a projection
change, or a filtered view.

`graph-manager`/`network-manager.js:300-303` already does this correctly:

```js
const newNodeIds = new Set(visNodes.map(nodeConfig => nodeConfig.id));
for (const [id, pos] of Object.entries(savedPositions)) {
    if (!newNodeIds.has(id)) continue;
    graphManager.network.moveNode(id, pos.x, pos.y);
}
```

## Impact

- Console noise that hides real errors during graph work.
- **Functional:** the layout restore silently does nothing for any id not
  currently rendered, so "lock layout" and un-cluster do not fully restore —
  the failure is invisible because it is logged as a warning rather than
  surfaced.

## Fix sketch

Guard both loops against the live DataSet before moving:

```js
const live = new Set(net.body.data.nodes.getIds());
for (const id of Object.keys(state.positions)) {
    if (!live.has(id)) continue;
    ...
}
```

Same in `focus.js:_unCluster` for `_savedPositions`. Guard `network.body?.data`
so it is safe before init. Do not rely on `try/catch` for this — the message is a
`console.error`, not an exception.

## Verify

- Open the goblin camp, lock the background layout, trigger a world refetch and
  a cluster/un-cluster: **no** `moveNode does not exist` lines.
- Positions still restore for every node that *is* present.
- `focus.js` cluster/un-cluster round-trip returns nodes to their prior
  positions.
