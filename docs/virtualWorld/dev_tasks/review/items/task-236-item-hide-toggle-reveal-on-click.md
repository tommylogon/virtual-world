# Task-236: "Hide Items" Toggle — Reveal Items on Click

**Status:** In Review — implemented 2026-08-16, syntax-checked, pending live browser E2E.
**Source:** New feature request. The show/hide items toggle existed, but hiding items fully hid every item node with no way to peek at a node's contents. Desired: in hide mode, clicking a node still reveals that node's items.

## What changed

In **hide items mode** (`_showItems === false`), item nodes are normally filtered out of the vis.js graph. Now clicking a node temporarily reveals the items directly tied to it, and clicking away (empty space) hides them again:

- Click an **area** → reveals the items placed there (`in`/`on`/`at` relations).
- Click a **character** → reveals carried + equipped items (`carrying`/`equipped`).
- Click an **item** → reveals the items inside that container (`in` relation to the item).
- Click **empty space** → hides the revealed items again.
- Click a **different node** → swaps which items are revealed.

Turning the toggle back to "show items" clears any temporarily revealed nodes.

## Implementation

- `static/js/graph/network-manager.js`
  - Extracted the per-node label/tooltip/color styling out of `loadGraphData()` into a reusable `buildNodeConfig(nodeData)` helper, so revealed nodes render identically to normal ones.
  - Added `revealItemsForNode(nodeId)` — scans `_graphEdgesArr` for ownership/placement edges (`in`, `on`, `under`, `behind`, `beside`, `at`, `carrying`, `equipped`) whose target is the clicked node, adds those item nodes to the network dataset, and tracks them in `_revealedItemIds`. Non-ownership edge types (`connection`, `unlocks`, `triggers`, `requires`) are skipped.
  - Added `hideRevealedItems()` — removes the tracked revealed item nodes from the network dataset.
  - Clears stale `_revealedItemIds` on graph reload.
- `static/js/graph-manager.js` — new `_revealedItemIds` state (a `Set`).
- `static/js/graph/event-handlers.js` — on node click calls `GraphNetwork.revealItemsForNode(...)`; on empty click calls `GraphNetwork.hideRevealedItems()`.

Note: the relation edges to hidden item nodes are already rendered in the graph (only the item *nodes* are filtered out), so adding the item nodes back reuses the existing edges — no edge surgery needed.

## Verification

- `node --check` passes on all three modified JS files.
- Live browser check in the map editor pending: click an area / character / item in hide mode reveals its items; clicking empty space hides them.