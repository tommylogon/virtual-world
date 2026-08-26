---
id: 155
title: Item Uses Affect Weight + Stackable Instances
status: todo
priority: medium
created: 2026-08-02
tags: [items, weight, containers, realism, inventory, merging]
group: Equipment & Inventory
wiki: "[[Items & Inventory/Inventory]]"
---

# Task 155: Item Uses Affect Weight & Stackable Instances

**Status**: Todo  
**Priority**: Medium  
**Updated**: 2026-08-11  

---

## Summary

Two related concerns for multi-use consumable items:

1. **Weight tracks remaining uses** — A bread with 4 uses at 0.5 kg should weigh less as it
   gets eaten. Each use consumed reduces the item's weight proportionally.
2. **Stackable instances** — When the player has multiple copies of the same consumable
   (e.g. two breads), they should be combinable / splittable rather than managed as
   separate nodes, with weight and uses correctly merged or partitioned.

## Problem

### Weight is static

`weight` is a static property on item nodes. `adjust_uses` / `drain` / `_consume_item`
change `uses` but never touch weight (`engine/effects.py:847-931`,
`engine/item_actions.py:1228`). A half-eaten loaf weighs the same as a full one, which
breaks container capacity (task-103) and encumbrance logic (task-205).

### No instance combine / split

Two identical items (e.g. two `bread` nodes, each 4 uses, 0.5 kg) are two separate graph
nodes. The player can't merge them into one 8-use 1.0 kg loaf, split one into two halves,
or destroy a partial loaf to top up another. This clutters inventory and makes weight
accounting wrong when uses are consumed on only one copy.

## Design

### A. Weight Per Unit

- Add optional `max_uses` tracking on item nodes (already exists as a concept in task-102,
  but not always populated). `base_weight` = original weight when `uses == max_uses`.
- On every use decrement (`_consume_item`, `handle_adjust_uses`, `handle_drain`), recompute:
  ```
  weight = round(base_weight * (uses_left / max_uses), 3)
  ```
  - When `max_uses` is unknown or `-1` (infinite), keep full `weight` unchanged.
  - When `uses` hits 0, the item is consumed/destroyed (existing `on_use` triggers handle removal).
- `base_weight` is a new optional property; if absent, derive it from the library entry at
  build time (or fall back to current `weight` with no scaling).

### B. Stackable Instances — Combine

When the player has two or more items with the same `library_id` (or same `name` + `tags` +
`actions` + `uses` baseline) and the same `max_uses`:

- **Combine** (e.g. `combine bread with bread`):
  - Target item's `uses += source item's uses` (clamp at `max_uses` if defined)
  - Weight is recomputed via rule A (now `uses_left` is higher → weight is higher)
  - Source item node is destroyed; its `EDGE_CARRYING` / spatial edges removed
  - Container capacity re-checked: destroying the source frees space; the combined item may
    be heavier and need a container with enough remaining capacity
- **Destroy + transfer** (special case of combine when the target is at `max_uses`):
  - If target can't absorb more uses, but you want to "pour" from source to target:
    - Destroy the source instance
    - Increase target's `uses` by the source's `uses` (beyond `max_uses` if no cap, or
      clamp and note overflow)
    - Recompute weight

### C. Stackable Instances — Split

When an item has many uses and you want to divide it:

- **Split** (e.g. `split bread` or `split bread into two`):
  - Target item's `uses` is halved (or divided by N)
  - A new item node is created with the same properties, `uses = original - target.uses`
  - `base_weight` / `weight` is partitioned proportionally to the new uses counts
  - The split-off item is placed in the same container / area / hand
  - Container capacity re-checked for the split-off item

### D. Matching & Identity

- Two items are "stackable twins" when they share the same `library_id` (if present) and
  all of: `actions`, `tags`, `current_state`, `equip_slots`, and `max_uses` (if set).
- Items with different `current_state` (e.g. "sharp" vs "dull" sword) are NOT stackable even
  if same base item.
- The existing `find_item_node` / matching system (`engine/matching.py:301`) already
  returns the first carry match — combine/split need to enumerate ALL matching carry edges
  and disambiguate (numbered take: "take bread 2").

## Implementation

### Backend

1. `engine/item_actions.py`
   - Add `_reconcile_item_weight(node)` — recompute `weight` from `base_weight`,
     `uses`, `max_uses` (rule A). Call it after every `adjust_uses` / `drain` /
     `_consume_item`.
   - Add `_get_stackable_item_nodes(player_manager, item_name)` — enumerate all
     `EDGE_CARRYING` / `EDGE_EQUIPPED` edges matching the name, return list of nodes.
   - Add `combine_items(player_manager, source_name, target_name)` — merge uses,
     recompute weight, destroy source, re-check capacity.
   - Add `split_item(player_manager, item_name, parts=2)` — partition uses + weight,
     create new node, place in same location.
2. `engine/effects.py`
   - Call `_reconcile_item_weight` inside `handle_adjust_uses` (line 847) and
     `handle_drain` (line 904) after modifying `uses`.
3. `routes/graph.py` or `routes/items_registry.py`
   - Expose `combine` / `split` as API endpoints (or reuse the action endpoint).
   - Add `base_weight` and `max_uses` to the item library editable fields.
4. `engine/matching.py` — ensure `find_item_node` disambiguates numbered requests
   (already handled by task-81; verify it returns the Nth match so combine/split can
   target specific instances).

### Frontend

- `static/js/inspector/item-view.js` — show `base_weight`, `max_uses`, computed
  `weight` (recalc on `uses` change) in the item editor.
- Inventory grid: right-click menu on stackable items → "Combine", "Split",
  "Destroy + Transfer".
- Item library contents editor: show weight per use when `max_uses` is set.

## Files to Modify

1. `engine/item_actions.py` — weight reconciliation, combine/split/stack logic
2. `engine/effects.py` — call weight reconciliation in `handle_adjust_uses` / `handle_drain`
3. `routes/graph.py` — combine/split API endpoints
4. `routes/items_registry.py` — `base_weight`, `max_uses` library fields
5. `static/js/inspector/item-view.js` — editable base_weight, computed weight display
6. `static/js/inspector/inventory-grid.js` — stack context menu (combine/split/destroy)
7. `engine/matching.py` — numbered match disambiguation for combine/split targets

## Testing

- [ ] Bread with 4 uses at 0.5kg → after eating 1 use, weight = 0.375kg
- [ ] Bread with 4/4 uses → weight = full `base_weight`
- [ ] Infinite-use item (`uses = -1`) keeps static weight (no scaling)
- [ ] `combine bread bread` → one item with 8 uses, weight = 1.0kg, source node gone
- [ ] `combine bread bread` when target at max_uses → destroy source, transfer uses
- [ ] `split bread` → two items at half uses each, weights partitioned correctly
- [ ] Container capacity re-checked after combine (heavier item may not fit)
- [ ] Items with different `current_state` are not combinable
- [ ] Container capacity respects the reduced weight after partial consumption

## Related

- [[todo/items/task-156-weight-affects-energy-decay|task-156: Weight affects energy decay]]
- [[review/items/task-103-weight-volume-container-limits|task-103: Weight/Volume Limits for Containers]]
- [[todo/items/task-205-player-carry-capacity-system|task-205: Player Carry Capacity System]]
- [[todo/items/task-102-progressive-item-status-multi-use.md|task-102: Progressive Item Status]]
