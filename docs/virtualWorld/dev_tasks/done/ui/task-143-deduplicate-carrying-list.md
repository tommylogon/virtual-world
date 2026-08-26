---
group: Prompt & Narrative Quality
---
# Deduplicate Items in Carrying List

**Status**: In Review — implemented (verified 2026-08-08 code audit; moved from todo). `getInventory()` in `world-state.js:151-155` deduplicates by edge source id via a `seenIds` Set before name collection. Pending: visual verification of the inventory list.

**Filed**: 2026-07-30
**Priority**: High
**Status**: Design

---

## Problem

The `Carrying:` list in prompts shows duplicate entries. Items equipped and carried (or items with multiple edge types) appear once per edge:

```
Carrying: Reinforced Wool Trousers, Reinforced Wool Trousers, Wool Blend Undershirt & Drawers, Wool Blend Undershirt & Drawers, ...
```

This wastes tokens and makes the LLM think there are two of each item.

## Cause

`worldState.getInventory()` iterates all edges matching the character node ID and pushes `itemNode.name` for each match. If an item has both a `carrying` and `equipped` edge to the same character, its name is added twice.

## Fix

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
