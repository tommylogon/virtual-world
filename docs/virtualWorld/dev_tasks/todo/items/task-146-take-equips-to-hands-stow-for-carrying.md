---
group: Items & Inventory
---
# Take Equips to Hands, Stow/Put Stores Items

**Filed**: 2026-07-30
**Priority**: Medium
**Status**: Design

---

## Problem

Currently `take <item>` always puts the item into carrying (inventory). This is unintuitive — if you pick up a sword, you're holding it in your hand, not stuffing it in a bag.

## Rules

- **`take <item>`** → always puts the item in your hand (`hand_left` or `hand_right`). Every item goes to a hand first — no exception. This makes it visible to others in the room.
- Items without explicit `equip_slots` still occupy a hand slot (you're holding it). The equipment system needs a generic "held" capability for any item.
- **Two-handed items** (`two_handed` tag) — require both `hand_left` and `hand_right` to be free. If either is occupied, return `"Your hands are full — you can't take that."`
- **`equip_all_slots` tag** — items with this tag fill ALL their defined `equip_slots` when equipped, not just the first. Like `two_handed` but for any set of slots (e.g., a full-body outfit fills `torso`, `arms`, `legs`, `feet` at once). Uses the existing `__multi_slot_` marker pattern from `two_handed`.
- **`stow <item>`** → moves from hand to carrying (inventory, out of sight).
- **`stow <item> in <container>`** → puts it into a specific container.
- **`stow <item>`** (new command, synonym for `put <item>`) — moves an item from hands to carrying or into a container.
- **`equip <item>`** — works as currently: takes from carrying and equips to the item's default slot. If already in hand, moves to the specified slot.

## Considerations

- What if `take` is used on a hat or necklace? Should it go to hand or directly to the head/neck slot? Design says hand first — you pick it up, then equip it.
- The command parser needs `stow` as an alias for `put`.
- Backpack/bag items with container support — `stow` into an open container if one is available and has space, otherwise into generic carrying.

## Files

- `engine/item_actions.py` — `take_item()` handler
- `routes/action.py` — command parser, add `stow` alias
- `engine/equipment.py` — hand-slot checks, two-handed logic
- `static/js/agent/prompt-builder.js` — command table update for `stow`
