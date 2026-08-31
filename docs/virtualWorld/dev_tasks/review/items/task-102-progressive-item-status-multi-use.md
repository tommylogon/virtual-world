---
group: Equipment & Inventory
wiki: "[[Items & Inventory/Item States & Toggleables]]"
---
# Task 102: Progressive Item Status — Multi-Use Activation

**Status**: todo
**Priority**: Medium
**Filed**: 2026-07-24

## Summary

Some items need multiple uses to activate (like a generator requiring 15 successful repairs). This is already achievable with the existing trigger system by stacking `on_use` triggers that check a counter condition. This task formalizes the pattern as a first-class feature with UI feedback.

## What Already Exists

- Items have `uses` and `max_uses` fields
- Triggers can fire on `on_use` with conditions
- Items have `state` field (current status)
- The trigger system supports condition checks

## The Pattern (Already Possible)

A generator item with 15 uses:
1. Item has `max_uses: 15, uses: 0`
2. Trigger `on_use` with condition `uses >= 15` → effect `set_state: "on"`
3. Trigger `on_use` with condition `uses < 15` → effect `message: "You turn the crank. ${15 - uses} more turns needed."`
4. Each `use` increments `uses` counter
5. At 15, the state flips to "on"

## What This Task Adds

### 1. Formalize Progressive State UI
In the item inspector:
- Show current uses vs max as a progress bar
- Display current state + next state at threshold
- Visual indicator when item is "charging" vs "charged"
- ETA: "15 more turns until powered on"

### 2. New Trigger Condition: `on_use_progressive`
- Fires repeatedly as item is used
- Passes current progress as context
- Can have different effects at different thresholds:
  - `threshold: 5` → message "The generator hums..."
  - `threshold: 10` → message "Lights flicker..."
  - `threshold: 15` → effect `set_state: "on"`

### 3. Persistence
- Uses/progress survives save/load
- Status persists across room changes
- Visual state reflects progress even when inspector is closed

## Implementation

### Backend
- Add `progress_to_state` map to items: `{10: "humming", 15: "on"}`
- Add `on_use_progressive` to trigger types
- Trigger system passes current uses count to condition checks

### Frontend
- Progress bar in item inspector (current_uses / max_uses)
- Status indicator based on threshold
- Message feedback per use increment

## Files Affected

- `item.py` — progress_to_state field?
- `engine/trigger_system.py` — on_use_progressive type
- `engine/effects.py` — threshold-based effects
- `static/js/inspector/item-view.js` — progress bar UI
- `static/js/inspector/trigger-helpers.js` — new trigger type in editor

## Tests
- Item with 15 max_uses, verify state changes at threshold
- Progress survives save/load
- Visual progress bar updates on each use
