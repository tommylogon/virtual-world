---
type: task
status: review
area: items
priority: medium
---

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

## How

- `static/js/graph/network-manager.js`
  - Extracted the per-node label/tooltip/color styling out of `loadGraphData()` into a reusable `buildNodeConfig(nodeData)` helper, so revealed nodes render identically to normal ones.
  - Added `revealItemsForNode(nodeId)` — scans `_graphEdgesArr` for ownership/placement edges (`in`, `on`, `under`, `behind`, `beside`, `at`, `carrying`, `equipped`) whose target is the clicked node, adds those item nodes to the network dataset, and tracks them in `_revealedItemIds`. Non-ownership edge types (`connection`, `unlocks`, `triggers`, `requires`) are skipped.
  - Added `hideRevealedItems()` — removes the tracked revealed item nodes from the network dataset.
  - Clears stale `_revealedItemIds` on graph reload.
- `static/js/graph-manager.js` — new `_revealedItemIds` state (a `Set`).
- `static/js/graph/event-handlers.js` — on node click calls `GraphNetwork.revealItemsForNode(...)`; on empty click calls `GraphNetwork.hideRevealedItems()`.

Note: the relation edges to hidden item nodes are already rendered in the graph (only the item *nodes* are filtered out), so adding the item nodes back reuses the existing edges — no edge surgery needed.

## Steps to verify

- `node --check` passes on all three modified JS files.
- Live browser check in the map editor pending: click an area / character / item in hide mode reveals its items; clicking empty space hides them.

## What

TODO

## Why

TODO

## Acceptance

- [ ] TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Graph toolbar → turn **Show items** off → click an area, character, or container node → click empty space → switch **Show items** back on.

Current availability: the card records the implementation of temporary reveal behavior and is pending live browser E2E. This section describes the exact interaction still to verify.

Live steps when available:
1. With **Show items** off, click an area containing one `in` item and one `on` item.
   - expected: those directly placed items appear and unrelated items remain hidden.
2. Click a character carrying and equipping items, then click an item container.
   - expected: character click reveals its `carrying`/`equipped` items; container click reveals only contents connected by ownership/placement edges.
3. Click empty graph space, then click a different node.
   - expected: empty space hides the temporary reveal; selecting another node swaps the revealed set to that node's items.
4. Turn **Show items** on and inspect the graph.
   - expected: temporary reveals clear and all item nodes appear through the normal show-items mode.

This section is not a claim that the live browser E2E is complete today.
