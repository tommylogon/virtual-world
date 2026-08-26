---
group: Prompt & Narrative Quality
wiki: "[[Characters/Characters Overview]]"
---
# Character Inspector Polish

**Filed**: 2026-07-21
**Updated**: 2026-07-30
**Priority**: Low
**Status**: Done — superseded by organic improvements

---

## Summary

Remaining polish items from task-17 (Editable Characters). All superseded by organic improvements — the equip picker works via `+` button and right-click context menus, inventory has its own tab, container inspection works via right-click → Open Container, and the dedicated paperdoll task covers the rest.

### What's actually in place
- ✅ Right-click context menus on inventory items (Inspect, Equip, Drop, Open Container, Put in Container)
- ✅ Right-click context menus on paperdoll slots (Inspect, Open Container, Unequip)
- ✅ `+` button on each paperdoll slot opens equip picker filtered by compatible items
- ✅ Stack expansion popup for layered slots (+N more badge)
- ✅ Inventory grid with its own tab
- ✅ Open Container via right-click navigates to item inspector

### What was deferred/superseded
- Container contents inline expand in inventory — not needed, right-click → Open Container covers it
- Click empty slot → equip picker — `+` button does this
- Swap option — unequip + re-equip from inventory works, paperdoll task will improve this
- Drag-and-drop — not important, paperdoll task covers future UX improvements

## Items

### 1. Container contents expandable in inventory

**Deferred:** Right-click → Open Container on any container item navigates to the item inspector instead. Inline expand not needed.

### 2. Click empty paperdoll slot → open equip picker

**Superseded:** The `+` button on each slot does this. The dedicated paperdoll task will improve the UX.

### 3. Swap option on equipped items

**Superseded:** Right-click context menu has Unequip. Quick unequip + re-equip from inventory covers the use case. Paperdoll task handles future improvements.

### 4. Drag-and-drop from inventory to paperdoll

**Deferred:** Not a priority. Paperdoll task covers future drag-and-drop if needed.

## Files Affected

- `static/js/inspector.js` — all four items
- `static/css/style.css` — drag-and-drop visual feedback (if implemented)

**Deferred**: Post-merge feature branch. This branch is refactoring/testing only.


## Refactoring Impact (July 2026)

Inspector is 10+ files in static/js/inspector/. Container contents display modifies item-view.js and inventory-view.js. Empty slot picker and swap/drag-drop modify paperdoll-view.js. Each change scoped to its view module.
