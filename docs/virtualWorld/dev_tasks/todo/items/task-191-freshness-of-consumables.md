---
group: Items & Inventory
---

# Freshness of Consumables (fresh/cooked/spoiled)

**Filed**: 2026-08-10
**Priority**: Medium
**Status**: Todo

---

## Problem

There is no way to track the state of food — it can't be fresh, cooked, or spoiled. This matters narratively: food should go bad over time and cooking should change its state.

## Design

- Model fresh / cooked / spoiled as condition instances attached to the item, which keeps the generic item template clean and reuses the existing condition system.
- Use a periodic tick on the item to transition to spoiled after a duration.
- Use `ends_on` to end the fresh/cooked state when it spoils.
- Integrate with the existing cooking system so cooking a fresh item sets it to cooked.

## Files

- `engine/item_actions.py` — cooking transitions, spoil behavior on item use.
- `engine/conditions.py` — condition instances for freshness states on items.
