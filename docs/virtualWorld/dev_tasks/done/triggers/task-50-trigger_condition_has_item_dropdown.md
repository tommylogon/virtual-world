---
group: Trigger System
wiki: "[[Rules Engine/Triggers & Effects]]"
---

# Trigger Conditions: Dropdown for "has_item in Inventory"

**Filed**: 2026-07-15
**Priority**: Medium
**Status**: In Review — implemented (code-verified 2026-08-11). `has_item` condition with dropdown of world/library items in trigger editor (`static/js/inspector.js:287/386`, `item-library.js:40/940-945`).

---

## Summary

When creating a trigger condition of type `has_item`, the user currently selects from a multi-select element. This should be a proper dropdown with a searchable list of all known items (from world).

## Current State

In `item-library.js:_addTrigger()` (lines 693-712), when the condition type changes to `has_item`, the UI shows a hidden `<select id="trigger-cond-extra">` element populated with library items via `Object.entries(this.data)`. 

The problem: this select only shows library items, not world items. It also requires the user to know the exact item ID, and there's no search/filter.

## Proposed Change

1. **Replace the `<select>` with a searchable `<input>` + `<datalist>`** (consistent with other trigger target fields in the same modal)
2. **Include world items** in the options list
3. **Show display names with IDs** for clarity

### UX Flow

When user selects "Has item in inventory" from condition dropdown:
1. A searchable input appears with a datalist
2. Datalist includes all library items (with their names) and all world items currently in the graph
3. User types to search, picks an item
4. The value stored is the item ID

## Audit

**Status**: Ready to test
**How to test**:
- Open the Item Library trigger editor for any item. Add a condition, select "Has item in inventory". Verify a searchable text input with datalist appears (not a plain `<select>`).
- Start typing an item name — verify matching items from the library appear as suggestions.
- Save the trigger, verify the condition stores the correct item ID.

## Files Affected

- `static/js/item-library.js` — replace the `trigger-cond-extra` select with searchable input+datalist
