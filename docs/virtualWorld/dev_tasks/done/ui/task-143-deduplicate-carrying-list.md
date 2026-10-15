---
area: ui
type: task
status: done
priority: medium
---

# Deduplicate Items in Carrying List

**Status**: In Review — implemented (verified 2026-08-08 code audit; moved from todo). `getInventory()` in `world-state.js:151-155` deduplicates by edge source id via a `seenIds` Set before name collection. Pending: visual verification of the inventory list.

**Filed**: 2026-07-30
**Priority**: High
**Status**: Design

---

## Why

The `Carrying:` list in prompts shows duplicate entries. Items equipped and carried (or items with multiple edge types) appear once per edge:

```
Carrying: Reinforced Wool Trousers, Reinforced Wool Trousers, Wool Blend Undershirt & Drawers, Wool Blend Undershirt & Drawers, ...
```

This wastes tokens and makes the LLM think there are two of each item.

## Cause

`worldState.getInventory()` iterates all edges matching the character node ID and pushes `itemNode.name` for each match. If an item has both a `carrying` and `equipped` edge to the same character, its name is added twice.

## How

Deduplicate by item node ID, not by name. `getInventory()` should track seen source IDs and skip duplicates:

```js
const seen = new Set();
for (const edge of ...) {
    if (seen.has(edge.source)) continue;
    seen.add(edge.source);
    ...
}
```

## Files

- `static/js/world-state.js` — `getInventory()`
- `static/js/agent/prompt-builder.js` — downstream consumer
- `static/js/agent-engine.js` — downstream consumer

## What

TODO

## Steps to verify

1. Load a scratch scenario where one item has both `carrying` and `equipped`
   edges to a character; select that character and expand Agent Lens → `Room
   context (observe / decide)`.
   - expected: the same item node appears once in the `Carrying` list.
   - observed: the task records ID-based deduplication in `worldState.getInventory()`;
     visual verification is still pending.
2. Add a second, distinct item node with the same display name and refresh the
   preview.
   - expected: both distinct item nodes remain represented; only the duplicate
     edge for one node is collapsed.

## Browser UI and intended live verification

Intended UI home: Graph → select a character → Agent Lens → inventory/context
preview; Character Inspector → Inventory for the visible item list.

Current availability: `worldState.getInventory()` deduplicates by source item
ID before returning names. The card explicitly leaves visual verification
pending; the UI should still preserve two different item IDs that share a name.

Live steps when available:
1. Load a disposable scenario with one item connected to the character by both
   `carrying` and `equipped`; select the character and inspect Agent Lens →
   `Room context (observe / decide)` and Inspector → Inventory.
   - expected: that item appears once in each list.
2. Add a second item node with the same display name but a different ID, refresh
   the state, and inspect the same two surfaces again.
   - expected: two same-named physical items remain visible, while the
     carried-and-equipped item remains a single entry.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.

## Acceptance

- [ ] TODO
