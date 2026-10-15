---
area: ui
type: task
status: done
priority: medium
---

# Equipment Slot Detail Modal

**Filed**: 2026-07-30  
**Priority**: Medium  
**Status**: Review  

---

## What

When clicking on an equipment slot in the paperdoll inspector (e.g. "Torso", "Head", "Legs"), open a modal/popup that shows the full layer stack for that slot, the bonuses each item provides, and allows unequip/reorder actions — making character design and gear inspection easier.

---

## Why

Currently, clicking a filled equipment slot in the paperdoll inspects the **outermost** item node. To see what's beneath layers, you hover over tiny `↳` indicators or click a `📋 layers` badge. There's no consolidated view of a slot's entire layer stack with bonuses, and unequipping inner layers requires multiple steps.

---

## Requirements

### 1. Slot Click → Modal
- Clicking a filled paperdoll slot opens a **slot detail modal** (not the item inspector)
- The modal is anchored near the clicked slot or centered
- Clicking an empty slot does nothing (or shows "nothing equipped here")

### 2. Modal Content
- **Header**: Slot label + slot graphic
- **Layer list**: Items listed innermost (closest to skin) → outermost, with:
  - Item name (clickable to inspect the item node)
  - Item description preview
  - Per-item **bonus summary** (defense, insulation, damage, resistances, etc.)
  - Layer depth indicator (e.g. "Layer 1/5", "Layer 3/5")
- **Totals**: Aggregated bonuses for the slot (summed defense, insulation, etc.)
- **Slot capacity**: "X / Y equipped" (max_depth from EQUIP_SLOTS)

### 3. Actions
- **Unequip** button per item — pops that specific item (not just outermost)
- **Move up / Move down** buttons — reorders layers within the slot
- **Unequip all** button — clears the entire slot
- **Equip item** button — opens the existing equip picker filtered to this slot

### 4. Bonus Display
Show all relevant aggregate bonuses from the slot's items:

| Bonus | Display |
|-------|---------|
| `defense` | 🛡️ +X Defense (per item + total) |
| `insulation` | 🌡️ +X°C Insulation (per item + total) |
| `resistances` | ⚡ Fire: X, Cold: Y (per type) |
| `damage` (weapon slots) | ⚔️ X + YdZ damage |
| `weight` | ⚖️ Total weight |

### 5. Integration
- Modal data sourced from `worldState.players[name].equipped[slot]`
- Item details resolved via `worldState.graph.nodes[itemId].properties`
- After unequip/reorder, refresh via `worldState.fetch()` then re-render the paperdoll
- Works for both left-hand (`hand_left`) and right-hand (`hand_right`) slots

---

## Implementation Sketch

### Files to create/modify

| File | Change |
|------|--------|
| `static/js/inspector/paperdoll-view.js` | Add `showSlotModal(charName, slot)` function. Replace slot-click handler. |
| `templates/index.html` | Add slot detail modal HTML (can use existing modal pattern). |
| `static/js/ui/settings-view.js` or new file | Modal rendering/bonus aggregation logic. |

### Data flow

```
Click "Torso" slot
  → paperdoll-view.js: showSlotModal("Lyrie", "torso")
    → Reads player.equipped.torso = ["item_undershirt", "item_vest", "item_coat"]
    → For each item ID, looks up worldState.graph.nodes[id].properties
    → Aggregates bonuses (defense, insulation, resistances)
    → Renders modal with layers + bonuses
    → User clicks "Unequip" on "vest"
      → runAction('unequip vest')
      → worldState.fetch() → re-render paperdoll + modal
```

### Bonus aggregation

Reuse the logic from `engine/equipment_bonuses.py`'s `aggregate_bonuses()` — but do it client-side from `worldState` data:

```js
function getSlotBonuses(nodeProperties) {
    return {
        defense: nodeProperties.defense || 0,
        insulation: nodeProperties.insulation || 0,
        resistances: nodeProperties.resistances || {},
        damage: nodeProperties.damage || 0,
        damage_dice: nodeProperties.damage_dice || null,
    };
}
```

---

## Related

- [[done/prompting/task-123-equipment-description-in-prompts|task-123: Equipment description in prompts]]
- `engine/equipment.py` — EQUIP_SLOTS config with max_depth
- `engine/equipment_bonuses.py` — aggregate_bonuses() for server-side bonus calc
- `static/js/inspector/paperdoll-view.js` — existing paperdoll rendering

## How

**Completed**: 2026-07-31

### Changes

| File | Change |
|------|--------|
| `routes/settings.py` | Added `/api/settings/equip_slots` endpoint to expose EQUIP_SLOTS config |
| `static/js/world-state.js` | Added `equipSlots` property and `fetchEquipSlots()` method |
| `static/js/main.js` | Fetch equip slots config on app init |
| `static/js/inspector/paperdoll-view.js` | Added `showSlotModal()` function with layer list, bonuses, totals, and actions |

### Features

- Clicking a filled equipment slot opens a modal showing the full layer stack
- Modal displays: slot label, layer count vs max_depth (or ∞ for unlimited), per-item bonuses, aggregated totals
- Actions: unequip individual items, move layers up/down, unequip all, equip new item
- Bonus display: defense, insulation, damage, weight, resistances
- Layer reordering via `_moveLayer()` helper (client-side array swap)
- Item names are clickable to open the item inspector
- Accessories section now clickable — opens the same modal for the accessory slot (unlimited capacity)

## Steps to verify

1. Open a character's Inventory tab, click a filled Torso slot, and read the
   slot detail modal from the innermost item through the outermost item.
   - expected: each layer shows its item, depth, bonus summary, and slot total;
     the header reports used/max capacity.
   - observed: the 2026-07-31 implementation record lists these controls; no
     live browser observation is recorded here.
2. Move an inner layer up, unequip a different inner item, equip a replacement,
   and reopen the slot modal after each refresh.
   - expected: the selected item changes position or is removed without
     removing a neighboring layer; the paperdoll and modal show the updated
     stack.
3. Click an item name, then repeat for `hand_left`, `hand_right`, and the
   unlimited Accessories slot.
   - expected: item names open their item inspector and each slot uses its own
     capacity/action rules.

## Browser UI and intended live verification

Intended UI home: Character Inspector → Inventory → Paperdoll → click a filled
equipment slot.

Current availability: The card records `showSlotModal()` with layer order,
bonus totals, capacity, unequip/reorder/equip actions, and clickable item names
as implemented on 2026-07-31. It does not record a browser run.

Live steps when available:
1. Open a character with at least three layers in Torso, click Torso, and read
   each layer and the total row.
   - expected: order runs skin-to-outer layer, each bonus is attributed to its
     item, and the modal shows the slot's total and `X / Y equipped`.
2. Move the second layer down, unequip the innermost item, then equip another
   torso item from the filtered picker.
   - expected: only the chosen layer changes; the refreshed paperdoll and modal
     agree on the new stack.
3. Repeat the slot click on left hand, right hand, and Accessories.
   - expected: hand slots remain separate and Accessories reports unlimited
     capacity.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.

## Acceptance

- [ ] TODO

## Files

- TODO
