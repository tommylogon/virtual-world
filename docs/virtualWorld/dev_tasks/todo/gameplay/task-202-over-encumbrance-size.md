---
group: Gameplay & Combat
---

# Over-Encumbrance Counts as One Size Larger

**Filed**: 2026-08-10
**Priority**: Low
**Status**: Todo

---

## Problem

Carrying too much should make a character count as one size larger for passage, but there is no connection between carried weight and size gating.

## Design

- Items already have a `weight` property.
- When total carried weight exceeds a threshold, the character counts as one size larger for movement and size gating (crawl / climb / jump).
- Slot into existing movement gating, which is being built in task-187 character-size-passage-movement.

## Files

- engine/movement.py — apply encumbrance-driven size bump in crawl/climb/jump gating
- engine/item_actions.py — expose total carried weight for the encumbrance threshold
