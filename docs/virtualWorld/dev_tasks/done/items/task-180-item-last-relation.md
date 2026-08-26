---
group: Items & Inventory
---

# Item `last_relation` Property (Use Returns to Origin)

**Filed**: 2026-08-10
**Priority**: Medium
**Status**: Done — implemented 2026-08-10, tests pass

---

## Problem

When you `use` an unequipped item (one that's in your inventory/carrying), it stays in inventory after use. There's no memory of where it came from, so you can't return it to its original spot. Knife on table → take → use → stays in hand/inventory instead of going back to the table.

The graph edges that track location (`on`, `under`, `behind`, `beside`, `at`, `in`, `carrying`, `equipped`) are **removed** on pickup, so the "last known spot" is lost.

## Goal

Stamp the item's last spatial relation on pickup, so `use` / `drop` can return it to that origin.

## Design

- **Property**: `last_relation` dict on the item node:
  ```
  {
    "relation": "on",          # EDGE_ON / EDGE_UNDER / EDGE_BEHIND / EDGE_BESIDE / EDGE_AT / EDGE_IN / EDGE_CARRYING / EDGE_EQUIPPED
    "target_id": "table_01",   # the node it was on/under/etc.
    "target_name": "table",    # human-readable fallback
    "slot": "hand_right"       # only for EDGE_EQUIPPED
  }
  ```
- **Set on take**: `take_item` writes `last_relation` before removing the spatial edge.
- **Read on use**: if the item is in carrying (not equipped) and `use` completes successfully, re-create the spatial edge using `last_relation`.
- **Read on drop**: if `last_relation` exists and the target node is still in the same area, drop back to that relation instead of generic "on floor" / carrying.
- **Clear on equip**: when the item is equipped, clear `last_relation` (the item is now in hand, not "on table").
- **Degrade gracefully**: if the target node no longer exists (table was destroyed), fall back to current behavior (carrying / floor).

## Implementation

- `engine/item_actions.py` — `take_item()` stamps `last_relation`; `use_item()` returns to origin after use; `drop_item()` returns to origin; helper methods `_stamp_last_relation`, `_restore_last_relation`, `_clear_last_relation`
- `engine/equipment.py` — `equip_item()` clears `last_relation` on equip
- `tests/test_item_actions.py` — tests pass

## Notes

- Pairs with the spatial tracking added in the 2026-08-10 take-item refactor.
- Not a new system — just a property write + edge recreation.
- Does NOT affect equipped items in hand (they stay in hand on use, per the current design).
